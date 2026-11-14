#!/usr/bin/env python
"""Capa de aptitud para base en el polo sur lunar (reglas transparentes, NO la red).

Rejilla: estereográfica polar sur de LOLA a 480 m (8 x 8 píxeles de 60 m).
Criterios (cada uno de 0 a 1; pesos visibles en WEIGHTS):
  landing      fracción de la celda con pendiente < 8°  (LOLA 60 m)
  rover        fracción de la celda con pendiente < 15° (LOLA 60 m)
  ice          exp(-d / 5 km), d = distancia a hielo estable a <= 1 m (Diviner PRP)
  temperature  según la máxima anual de Diviner PRP: 0 si <= 110 K (sombra
               permanente: sin energía solar), sube lineal hasta 1 en 200 K,
               1 entre 200 y 330 K, baja lineal a 0 en 390 K
Total = media ponderada, solo donde los cuatro criterios tienen dato.

SUGERENCIA, NO ELECCIÓN FINAL: faltan la iluminación (horas de Sol) y la
visibilidad de la Tierra (comunicaciones), que no están en los portales del reto.
La temperatura máxima es solo un indicio parcial de iluminación.

Candidatos de la NASA: coordenadas APROXIMADAS (centros de los rasgos con nombre),
a confirmar con Ciencia. Para no depender de la precisión: un candidato de BORDE de
cráter se mide en el anillo entre 0.8 y 1.3 veces el radio del cráter alrededor de
su centro; un MACIZO, en un disco de 10 km. Se usa el percentil 90 del puntaje y se
compara contra zonas al azar del mismo tamaño.

  python -m ml.suitability_moon
"""
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))
LOLA = ROOT / "data/raw/moon/ldem_75s_60m_float.lbl"
DIV = ROOT / "data/features/moon_polar_south_480m.tif"
OUT = ROOT / "data/artifacts/suitability"
BLOCK = 8                                   # 8 x 60 m = 480 m
WEIGHTS = dict(landing=0.30, rover=0.20, ice=0.30, temperature=0.20)
ICE_SCALE_KM = 5.0
DISK_KM = 10.0
# (nombre, lat, lon, grupo, tipo, radio_km). Centros y diámetros APROXIMADOS de los
# rasgos con nombre; "rim" = anillo [0.8R, 1.3R] alrededor del centro del cráter,
# "massif" = disco de radio_km alrededor del punto.
CANDIDATES = [
    ("Shackleton rim", -89.67, 129.78, "named sites", "rim", 10.5),
    ("Mons Mouton", -84.60, 31.00, "Artemis III 2024", "massif", 10.0),
    ("Malapert Massif", -86.00, 3.00, "Artemis III 2024", "massif", 10.0),
    ("Haworth (rim)", -87.45, -5.00, "Artemis III 2024", "rim", 25.5),
    ("Nobile Rim", -85.20, 53.50, "Artemis III 2024", "rim", 36.5),
    ("de Gerlache Rim", -88.50, -87.10, "Artemis III 2024", "rim", 16.2),
    ("Faustini Rim", -87.30, 77.00, "Artemis III 2022", "rim", 19.5),
    ("Amundsen Rim", -84.50, 82.80, "Artemis III 2022", "rim", 51.7),
]


def slope_fractions():
    """Fracción de píxeles de 60 m con pendiente < 8° y < 15° por celda de 480 m."""
    with rasterio.open(LOLA) as ds:
        H, W, px = ds.height, ds.width, ds.res[0]
        h, w = H // BLOCK, W // BLOCK
        f8 = np.full((h, w), np.nan, np.float32)
        f15 = f8.copy()
        strip = 128                          # celdas de 480 m por franja
        for r0 in range(0, h, strip):
            r1 = min(h, r0 + strip)
            y0, y1 = max(0, r0 * BLOCK - 1), min(H, r1 * BLOCK + 1)
            z = ds.read(1, window=Window(0, y0, W, y1 - y0)).astype(np.float32)
            bad = z < -1e30
            z = z * 1000.0                   # km -> m
            gy, gx = np.gradient(z, px)
            s = np.degrees(np.arctan(np.hypot(gx, gy)))
            s[bad] = np.nan
            off = r0 * BLOCK - y0
            s = s[off:off + (r1 - r0) * BLOCK, :w * BLOCK]
            s = s.reshape(r1 - r0, BLOCK, w, BLOCK)
            valid = np.isfinite(s).all(axis=(1, 3))
            f8[r0:r1] = np.where(valid, (s < 8).mean(axis=(1, 3)), np.nan)
            f15[r0:r1] = np.where(valid, (s < 15).mean(axis=(1, 3)), np.nan)
    return f8, f15


def temperature_score(tmax):
    t = np.asarray(tmax, np.float32)
    s = np.interp(t, [110, 200, 330, 390], [0, 1, 1, 0]).astype(np.float32)
    s[~np.isfinite(t)] = np.nan
    return s


def save_png(a, path, title):
    fig, ax = plt.subplots(figsize=(6, 6))
    cmap = plt.get_cmap("Blues").copy()
    cmap.set_bad((0, 0, 0, 0))
    im = ax.imshow(np.ma.masked_invalid(a), cmap=cmap, vmin=0, vmax=1)
    ax.set_title(title, fontsize=10)
    ax.axis("off")
    fig.colorbar(im, ax=ax, fraction=0.04, label="score (0-1)")
    plt.tight_layout()
    plt.savefig(path, dpi=100, transparent=True)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with rasterio.open(DIV) as ds:
        prof = ds.profile.copy()
        tmax, ice_km = ds.read(2), ds.read(4)
        T, crs = ds.transform, CRS.from_wkt(ds.crs.to_wkt())
    f8, f15 = slope_fractions()
    n = min(f8.shape[0], tmax.shape[0])
    f8, f15, tmax, ice_km = f8[:n, :n], f15[:n, :n], tmax[:n, :n], ice_km[:n, :n]
    crit = dict(landing=f8, rover=f15, ice=np.exp(-ice_km / ICE_SCALE_KM).astype(np.float32),
                temperature=temperature_score(tmax))
    allv = np.all([np.isfinite(v) for v in crit.values()], axis=0)
    total = sum(WEIGHTS[k] * np.nan_to_num(v) for k, v in crit.items()) / sum(WEIGHTS.values())
    total = np.where(allv, total, np.nan).astype(np.float32)
    layers = dict(crit, total=total)

    prof.update(count=1, height=n, width=n, dtype="float32", nodata=np.nan)
    for k, a in layers.items():
        with rasterio.open(OUT / f"moon_south_{k}.tif", "w", **prof) as d:
            d.write(a, 1)
            d.set_band_description(1, k)
        save_png(a, OUT / f"moon_south_{k}.png", f"Moon south pole · {k} suitability")
        v = a[np.isfinite(a)]
        print(f"  {k:<12} mediana {np.median(v):.3f}  p90 {np.percentile(v, 90):.3f}  "
              f"celdas {v.size}")

    # candidatos de la NASA contra discos al azar
    to_xy = Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True)
    rr, cc = np.mgrid[0:n, 0:n]
    px_km = T.a / 1000
    d2 = None

    def zone_p90(r, c, kind, R):
        d = np.sqrt((rr - r) ** 2 + (cc - c) ** 2) * px_km
        m = (d >= 0.8 * R) & (d <= 1.3 * R) if kind == "rim" else d <= R
        v = total[m]
        v = v[np.isfinite(v)]
        return float(np.percentile(v, 90)) if v.size > 10 else np.nan

    rng = np.random.default_rng(0)
    vr, vc = np.nonzero(np.isfinite(total))
    res, rand_by = [], {}
    for name, lat, lon, group, kind, R in CANDIDATES:
        key = (kind, R)
        if key not in rand_by:              # zonas al azar del mismo tipo y tamaño
            pick = rng.choice(len(vr), 150, replace=False)
            rz = np.array([zone_p90(vr[i], vc[i], kind, R) for i in pick])
            rand_by[key] = rz[np.isfinite(rz)]
        rand_k = rand_by[key]
        x, y = to_xy.transform(lon, lat)
        c, r = (x - T.c) / T.a, (y - T.f) / T.e
        p90 = zone_p90(r, c, kind, R)
        pct = float((rand_k < p90).mean() * 100) if np.isfinite(p90) else None
        res.append(dict(name=name, lat=lat, lon=lon, group=group, zone=kind, radius_km=R,
                        total_p90=None if not np.isfinite(p90) else round(p90, 3),
                        percentile_vs_random=None if pct is None else round(pct, 1),
                        random_median=round(float(np.median(rand_k)), 3)))
        print(f"  {name:<18} {kind:<6} R {R:5.1f} km  p90 {p90:.3f}  "
              f"percentil vs zonas al azar: {pct}")
    rand = np.concatenate(list(rand_by.values()))

    info = dict(weights=WEIGHTS, rules={
        "landing": "fraction of 60 m pixels with slope < 8 deg (LOLA)",
        "rover": "fraction of 60 m pixels with slope < 15 deg (LOLA)",
        "ice": f"exp(-d / {ICE_SCALE_KM} km), d = distance to Diviner stable ice at <= 1 m depth",
        "temperature": "Diviner annual max: 0 at <=110 K, 1 from 200 to 330 K, 0 at 390 K",
        "total": "weighted mean where all criteria have data"},
        missing=["illumination (hours of sunlight)", "Earth visibility (communications)"],
        caveat="Suggestion, not a final site selection.",
        grid=dict(crs="LOLA south polar stereographic", pixel_m=480),
        candidates=res,
        candidate_coordinates="approximate centers of named features; confirm with Science")
    (OUT / "suitability_moon.json").write_text(json.dumps(info, indent=2))

    # gráfica para el jurado (inglés)
    fig, ax = plt.subplots(figsize=(10, 4.6))
    group_color = {"Artemis III 2024": "#2a78d6", "Artemis III 2022": "#eb6834",
                   "named sites": "#1baf7a"}
    ax.boxplot(rand, vert=False, positions=[0], widths=0.5, showfliers=False,
               medianprops=dict(color="#52514e"), boxprops=dict(color="#8a8985"),
               whiskerprops=dict(color="#8a8985"), capprops=dict(color="#8a8985"))
    ok = [r for r in res if r["total_p90"] is not None]
    ok.sort(key=lambda r: r["total_p90"])
    for i, r in enumerate(ok, start=1):
        col = group_color[r["group"]]
        ax.plot(r["total_p90"], i, "o", color=col, ms=8, mec="#fcfcfb", mew=1.5,
                label=r["group"] if r["group"] not in ax.get_legend_handles_labels()[1] else None)
        ax.annotate(f"beats {r['percentile_vs_random']:.0f}% of random zones", (r["total_p90"], i), xytext=(8, -3),
                    textcoords="offset points", fontsize=8, color="#52514e")
    ax.set_yticks([0] + list(range(1, len(ok) + 1)))
    ax.set_yticklabels(["Random zones (same shapes)"] + [r["name"] for r in ok], fontsize=8)
    ax.set_xlim(right=1.08)
    ax.legend(loc="upper left", fontsize=8, frameon=False, title="Candidate list", title_fontsize=8)
    ax.set_xlabel("Suitability score (90th percentile in the rim ring or massif disk)",
                  fontsize=9, color="#52514e")
    ax.set_title("Do NASA candidate regions fall in high-suitability terrain?\n"
                 "Transparent rules: slope (LOLA), stable-ice proximity and temperature (Diviner). "
                 "Not included: illumination, Earth visibility.", fontsize=9)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="x", color="#e4e3df", lw=0.8)
    ax.set_axisbelow(True)
    plt.tight_layout()
    plt.savefig(OUT / "suitability_candidates.png", dpi=110, facecolor="#fcfcfb")
    print("->", OUT)


if __name__ == "__main__":
    main()
