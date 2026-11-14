"""Red de ASTRAL (CLAUDE.md, sección 8.2).

ResNet-18 preentrenada (5 canales) -> embedding 128 normalizado (lo que se
busca en FAISS). Para entrenar: cabeza de proyección 128 -> 128 (NT-Xent) y
discriminador de planeta 128 -> 64 -> n_bodies detrás de inversión de gradiente.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision


class GradReverse(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, lam):
        ctx.lam = lam
        return x.view_as(x)

    @staticmethod
    def backward(ctx, g):
        return -ctx.lam * g, None


def grad_reverse(x, lam):
    return GradReverse.apply(x, lam)


class Encoder(nn.Module):
    """Parche (B, 5, H, W) -> embedding (B, 128) de norma 1."""

    def __init__(self, in_ch=5, emb_dim=128, pretrained=True):
        super().__init__()
        w = torchvision.models.ResNet18_Weights.IMAGENET1K_V1 if pretrained else None
        net = torchvision.models.resnet18(weights=w)
        old = net.conv1
        net.conv1 = nn.Conv2d(in_ch, 64, 7, 2, 3, bias=False)
        with torch.no_grad():
            net.conv1.weight.copy_(old.weight.mean(dim=1, keepdim=True).repeat(1, in_ch, 1, 1))
        net.fc = nn.Identity()
        self.backbone = net
        self.head = nn.Linear(512, emb_dim)

    def forward(self, x):
        return F.normalize(self.head(self.backbone(x)), dim=1)


class MultimodalEncoder(nn.Module):
    """v3: ResNet-18 de 5 canales (forma) + MLP con las dimensiones por parche.

    tab (B, 14): 7 percentiles dentro del propio cuerpo (temperatura máx., mín. y
    rango, albedo, hielo, suelo, aridez) + 7 marcas de "sin dato". Las dos ramas se
    concatenan (512 + 64) y se proyectan al embedding de 128 de norma 1."""

    def __init__(self, in_ch=5, emb_dim=128, pretrained=True, tab_dim=14, tab_hidden=64):
        super().__init__()
        base = Encoder(in_ch, emb_dim, pretrained)
        self.backbone = base.backbone
        self.tab_mlp = nn.Sequential(nn.Linear(tab_dim, tab_hidden), nn.ReLU(inplace=True),
                                     nn.Linear(tab_hidden, tab_hidden), nn.ReLU(inplace=True))
        self.head = nn.Linear(512 + tab_hidden, emb_dim)
        self.tab_dim = tab_dim

    def forward(self, x, tab):
        h = torch.cat([self.backbone(x), self.tab_mlp(tab.to(x.dtype))], 1)
        return F.normalize(self.head(h), dim=1)


def tab_dropout(tab, p=0.2, generator=None):
    """Aumentación: oculta cada dimensión con probabilidad p (percentil 0, marca 1)."""
    n = tab.shape[1] // 2
    drop = torch.rand(tab.shape[0], n, device=tab.device, generator=generator) < p
    vals, miss = tab[:, :n].clone(), tab[:, n:].clone()
    vals[drop] = 0.0
    miss[drop] = 1.0
    return torch.cat([vals, miss], 1)


def load_any_encoder(state_dict):
    """Construye el encoder correcto (v1/v2 o multimodal v3) según sus pesos."""
    if any(k.startswith("tab_mlp.") for k in state_dict):
        tab_dim = state_dict["tab_mlp.0.weight"].shape[1]
        enc = MultimodalEncoder(pretrained=False, tab_dim=tab_dim)
    else:
        enc = Encoder(pretrained=False)
    enc.load_state_dict(state_dict)
    return enc


class AstralNet(nn.Module):
    def __init__(self, n_bodies=2, emb_dim=128, pretrained=True, n_aux=0, tab_dim=0):
        super().__init__()
        self.emb_dim = emb_dim
        self.multimodal = tab_dim > 0
        self.encoder = (MultimodalEncoder(5, emb_dim, pretrained, tab_dim) if self.multimodal
                        else Encoder(5, emb_dim, pretrained))
        self.proj = nn.Sequential(nn.Linear(emb_dim, emb_dim), nn.ReLU(inplace=True),
                                  nn.Linear(emb_dim, emb_dim))
        self.disc = nn.Sequential(nn.Linear(emb_dim, 64), nn.ReLU(inplace=True),
                                  nn.Linear(64, n_bodies))
        # cabeza auxiliar: obliga al embedding a conservar relieve y pendiente
        self.aux = (nn.Sequential(nn.Linear(emb_dim, 64), nn.ReLU(inplace=True),
                                  nn.Linear(64, n_aux)) if n_aux else None)

    def forward(self, x, lam=0.0, tab=None):
        emb = self.encoder(x, tab) if self.multimodal else self.encoder(x)
        z = self.proj(emb)
        # emb tiene norma 1 (componentes ~0.09): se reescala a componentes ~1
        # para que el discriminador pueda aprender; si no, se queda en el azar.
        logits = self.disc(grad_reverse(emb, lam) * self.emb_dim ** 0.5)
        aux = self.aux(emb * self.emb_dim ** 0.5) if self.aux is not None else None
        return emb, z, logits, aux


def nt_xent(z1, z2, temperature=0.1):
    """Pérdida SimCLR. z1, z2 (B, D): vistas emparejadas por fila."""
    z = F.normalize(torch.cat([z1, z2]), dim=1).float()
    B = z1.shape[0]
    sim = z @ z.t() / temperature
    sim.fill_diagonal_(float("-inf"))
    target = torch.cat([torch.arange(B, 2 * B), torch.arange(0, B)]).to(z.device)
    return F.cross_entropy(sim, target)
