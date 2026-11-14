"""Canales de entrada y aumentaciones, todo en GPU (CLAUDE.md, sección 8.1).

Entrada: z (B, 1, H, W) elevación en metros (relativa o absoluta da igual),
         px (B,) tamaño de píxel en metros.
Salida:  (B, 5, H, W) float32:
  0 elevación relativa  (z - media) / 500, recortada a [-3, 3]
  1 pendiente           grados / 90
  2 rugosidad           RMS 3x3 del residuo z - blur(z, 3 px), / px, recortada
  3 curvatura           laplaciano de z suavizado (σ=1.5 px) * px, escalado y recortado
  4 sombreado           hillshade [0, 1], altitud solar 45°, azimut dado

Rugosidad y curvatura se dividen/multiplican por px para que la misma forma
dé valores parecidos a 60 m y a 500 m. Las constantes de escala (ROUGH_SCALE,
CURV_SCALE) se fijaron mirando la distribución de la Luna y México a 60 m.
"""
import math

import torch
import torch.nn.functional as F

REL_SCALE_M = 500.0
REL_CLIP = 3.0
ROUGH_SCALE = 0.2     # rough/px: Tierra p99 ~0.6, Luna ~0.3 -> recorte < 1%
ROUGH_SIGMA_PX = 3.0  # el residuo z - blur(z) quita la pendiente regional
CURV_SCALE = 0.05     # lap*px típico ~±0.05
CURV_SIGMA_PX = 1.5   # la curvatura se calcula sobre z suavizado: quita las
                      # franjas de órbitas de LOLA y el ruido de píxel de
                      # NASADEM, que delatarían el planeta
CLIP = 3.0
SUN_ALT_DEG = 45.0
EVAL_AZIMUTH_DEG = 315.0


def _pad(z):
    return F.pad(z, (1, 1, 1, 1), mode="replicate")


def gaussian_blur(z, sigma=CURV_SIGMA_PX):
    """Suavizado gaussiano separable con borde replicado."""
    r = int(math.ceil(3 * sigma))
    t = torch.arange(-r, r + 1, dtype=z.dtype, device=z.device)
    k = torch.exp(-0.5 * (t / sigma) ** 2)
    k = k / k.sum()
    z = F.pad(z, (r, r, r, r), mode="replicate")
    z = F.conv2d(z, k.view(1, 1, 1, -1))
    return F.conv2d(z, k.view(1, 1, -1, 1))


def gradients(z, px):
    """Derivadas de Sobel en m/m. z (B,1,H,W), px (B,)."""
    kx = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=z.dtype, device=z.device)
    kx = (kx / 8.0).view(1, 1, 3, 3)
    ky = kx.transpose(2, 3)
    zp = _pad(z)
    p = px.view(-1, 1, 1, 1)
    dzdx = F.conv2d(zp, kx) / p
    dzdy = F.conv2d(zp, ky) / p   # positivo hacia abajo (filas crecientes = sur)
    return dzdx, dzdy


def make_channels(z, px, azimuth_deg=None):
    """z (B,1,H,W) metros, px (B,) metros, azimuth_deg (B,) o None (=315°)."""
    z = z.float()
    px = px.float().to(z.device)
    B = z.shape[0]
    mean = z.mean(dim=(2, 3), keepdim=True)
    zr = z - mean

    rel = (zr / REL_SCALE_M).clamp(-REL_CLIP, REL_CLIP)

    dzdx, dzdy = gradients(zr, px)
    grad = torch.sqrt(dzdx ** 2 + dzdy ** 2)
    slope = torch.atan(grad)                                  # rad
    slope_ch = slope * (180.0 / math.pi) / 90.0

    zp = _pad(zr)
    resid = zr - gaussian_blur(zr, ROUGH_SIGMA_PX)
    rough = torch.sqrt(F.avg_pool2d(_pad(resid ** 2), 3, stride=1))
    rough_ch = (rough / px.view(-1, 1, 1, 1) / ROUGH_SCALE).clamp(0, CLIP)

    lap_k = torch.tensor([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=z.dtype,
                         device=z.device).view(1, 1, 3, 3)
    lap = F.conv2d(_pad(gaussian_blur(zr)), lap_k) / px.view(-1, 1, 1, 1)          # (1/m) * px = adim.
    curv_ch = (lap / CURV_SCALE).clamp(-CLIP, CLIP)

    if azimuth_deg is None:
        azimuth_deg = torch.full((B,), EVAL_AZIMUTH_DEG, device=z.device)
    az = (azimuth_deg.float().to(z.device) * math.pi / 180.0).view(-1, 1, 1, 1)
    alt = SUN_ALT_DEG * math.pi / 180.0
    # normal·Sol. p = dz/dx(este), q = dz/dy(norte) = -dzdy (las filas van al sur).
    # Azimut en sentido horario desde el norte "arriba de la imagen".
    p, q = dzdx, -dzdy
    shade = (math.sin(alt) - p * math.cos(alt) * torch.sin(az)
             - q * math.cos(alt) * torch.cos(az)) / torch.sqrt(1 + p ** 2 + q ** 2)
    shade = shade.clamp(0, 1)

    return torch.cat([rel, slope_ch, rough_ch, curv_ch, shade], dim=1)


def augment(z, px, crop_min=0.8, vscale=0.15, generator=None):
    """Aumentación geométrica y vertical de un lote. Devuelve (z_aug, px_aug, azimuth).

    - rotaciones de 90° y volteos (exactos, dentro de la misma matriz afín)
    - recorte aleatorio de 80-100% del lado + reescalado a 128 (zoom ±20%);
      el tamaño de píxel efectivo pasa a px * s, para que la pendiente siga
      siendo física
    - escala vertical ±15%
    - azimut solar aleatorio en [0, 360)
    """
    B, _, H, W = z.shape
    dev = z.device
    g = dict(device=dev, generator=generator)
    k = torch.randint(0, 4, (B,), **g)
    ang = k.float() * (math.pi / 2)
    flip = torch.where(torch.rand(B, **g) < 0.5, -1.0, 1.0)
    s = crop_min + (1 - crop_min) * torch.rand(B, **g)
    tx = (torch.rand(B, **g) * 2 - 1) * (1 - s)
    ty = (torch.rand(B, **g) * 2 - 1) * (1 - s)
    c, sn = torch.cos(ang).round(), torch.sin(ang).round()
    theta = torch.zeros(B, 2, 3, device=dev)
    theta[:, 0, 0] = s * c * flip
    theta[:, 0, 1] = -s * sn
    theta[:, 1, 0] = s * sn * flip
    theta[:, 1, 1] = s * c
    theta[:, 0, 2] = tx
    theta[:, 1, 2] = ty
    grid = F.affine_grid(theta, (B, 1, H, W), align_corners=False)
    za = F.grid_sample(z.float(), grid, mode="bilinear", padding_mode="border",
                       align_corners=False)
    za = za * (1 + vscale * (torch.rand(B, 1, 1, 1, **g) * 2 - 1))
    px_a = px.float().to(dev) * s
    az = torch.rand(B, **g) * 360.0
    return za, px_a, az


def make_views(z, px, noise_std=0.03, generator=None, return_aug=False):
    """Una vista aumentada del lote, lista para la red: (B, 5, H, W).
    Con return_aug=True devuelve también (z_aug, px_aug) para objetivos auxiliares."""
    za, pa, az = augment(z, px, generator=generator)
    x = make_channels(za, pa, az)
    if noise_std > 0:
        x = x + noise_std * torch.randn(x.shape, device=x.device, generator=generator)
    return (x, za, pa) if return_aug else x


def relief_slope_targets(z, px):
    """Objetivos de la cabeza auxiliar, normalizados a ~N(0, 1):
    (log(1 + relieve) - 6) / 1.5 y (pendiente media en grados - 6) / 5."""
    z = z.float()
    flat = z.flatten(1)
    relief = flat.max(1).values - flat.min(1).values
    dzdx, dzdy = gradients(z, px.float())
    slope = torch.rad2deg(torch.atan(torch.sqrt(dzdx ** 2 + dzdy ** 2))).flatten(1).mean(1)
    return torch.stack([(torch.log1p(relief) - 6.0) / 1.5, (slope - 6.0) / 5.0], 1)
