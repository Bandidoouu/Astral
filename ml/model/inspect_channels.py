"""Revisa el dataloader: estadísticas por canal y cuerpo, velocidad y PNG.

python -m ml.model.inspect_channels --steps 50 --png data/artifacts/channels_check.png
"""
import argparse, time
import numpy as np
import torch
from ml.model.dataset import BalancedLoader, default_sources, BODY_ID
from ml.model.channels import make_channels, make_views

NAMES = ["rel_elev", "slope", "roughness", "curvature", "hillshade"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=int, default=60)
    ap.add_argument("--per-body", type=int, default=128)
    ap.add_argument("--steps", type=int, default=50)
    ap.add_argument("--png", default=None)
    a = ap.parse_args()
    sets = default_sources(a.scale)
    for s in sets:
        print(f"{s.body}: {len(s.idx)} parches de entrenamiento (de {len(s.patches)})")
    loader = BalancedLoader(sets, per_body=a.per_body, steps_per_epoch=a.steps)
    acc = {}
    torch.cuda.synchronize(); t0 = time.time(); n = 0
    for z, px, body in loader:
        v1, v2 = make_views(z, px), make_views(z, px)
        n += 2 * len(z)
        for name, bid in BODY_ID.items():
            m = body == bid
            if m.any():
                x = v1[m].transpose(0, 1).flatten(1).float()
                acc.setdefault(name, []).append(x[:, torch.randint(0, x.shape[1], (50_000,), device=x.device)])
    torch.cuda.synchronize(); dt = time.time() - t0
    print(f"\n{n} vistas en {dt:.1f}s = {n/dt:.0f} vistas/s (lectura + aumentación + canales)")
    print(f"\n{'canal':<10}" + "".join(f"{b:>34}" for b in acc))
    print(" " * 10 + "".join(f"{'media  std   p1    p99  %recort':>34}" for _ in acc))
    stats = {b: torch.cat(v, 1) for b, v in acc.items()}
    for c, name in enumerate(NAMES):
        row = f"{name:<10}"
        for b, x in stats.items():
            xc = x[c]
            q = torch.quantile(xc, torch.tensor([0.01, 0.99], device=x.device))
            clip = ((xc.abs() >= 2.999).float().mean() * 100).item()
            row += f"{xc.mean():>8.3f}{xc.std():>7.3f}{q[0]:>7.3f}{q[1]:>7.3f}{clip:>5.1f}"
        print(row)
    if a.png:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        z, px, body = next(iter(BalancedLoader(sets, per_body=2, steps_per_epoch=1, seed=1)))
        clean = make_channels(z, px).cpu().numpy()
        from ml.model.channels import augment
        torch.manual_seed(0)
        za, pa, az = augment(z, px)
        aug = make_channels(za, pa, az).cpu().numpy()
        fig, ax = plt.subplots(len(z) * 2, 6, figsize=(15, 2.6 * len(z) * 2))
        for i in range(len(z)):
            for r, (x, zz, tag) in enumerate([(clean, z, "eval"), (aug, za, "aug")]):
                row = ax[2 * i + r]
                row[0].imshow(zz[i, 0].float().cpu(), cmap="terrain")
                row[0].set_title(f"{['earth','moon','mars'][body[i]]} {tag} elev (m)", fontsize=8)
                for c in range(5):
                    row[c + 1].imshow(x[i, c], cmap="gray" if c == 4 else "viridis")
                    row[c + 1].set_title(NAMES[c], fontsize=8)
        for a_ in ax.flat: a_.axis("off")
        plt.tight_layout(); plt.savefig(a.png, dpi=80); print("->", a.png)


if __name__ == "__main__":
    main()
