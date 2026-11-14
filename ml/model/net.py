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


class AstralNet(nn.Module):
    def __init__(self, n_bodies=2, emb_dim=128, pretrained=True, n_aux=0):
        super().__init__()
        self.emb_dim = emb_dim
        self.encoder = Encoder(5, emb_dim, pretrained)
        self.proj = nn.Sequential(nn.Linear(emb_dim, emb_dim), nn.ReLU(inplace=True),
                                  nn.Linear(emb_dim, emb_dim))
        self.disc = nn.Sequential(nn.Linear(emb_dim, 64), nn.ReLU(inplace=True),
                                  nn.Linear(64, n_bodies))
        # cabeza auxiliar: obliga al embedding a conservar relieve y pendiente
        self.aux = (nn.Sequential(nn.Linear(emb_dim, 64), nn.ReLU(inplace=True),
                                  nn.Linear(64, n_aux)) if n_aux else None)

    def forward(self, x, lam=0.0):
        emb = self.encoder(x)
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
