#!/usr/bin/env python
"""Fórmula base: 20 estadísticas de relieve por parche (CLAUDE.md §12.1).

Es el rival que la red tiene que superar. Cada parche se describe con:
  relieve (máx - mín), desviación estándar de la elevación, integral hipsométrica,
  asimetría y curtosis de la elevación, pendiente media / desviación / p90,
  histograma de pendientes en 7 rangos (0-2, 2-5, 5-8, 8-15, 15-25, 25-35, >35°),
  rugosidad media y p90 (RMS del residuo z - blur, igual que la red),
  curvatura: media del valor absoluto, desviación, fracción convexa.
Relieve, desviación y rugosidades van en log(1 + x) para que no dominen los
extremos. La distancia es euclidiana sobre las variables estandarizadas
(z-score con media y desviación de todos los parches del índice).

Salida, en el mismo orden que data/artifacts/meta_{scale}.parquet:
  data/artifacts/baseline_feat_{scale}.npy   float32 N x 20, ya estandarizado
  data/artifacts/baseline_feat_{scale}.json  nombres, media y desviación

  python -m ml.baseline --scale 60
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

from ml.model.channels import ROUGH_SIGMA_PX, CURV_SIGMA_PX, gaussian_blur, gradients, _pad

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))
SLOPE_BINS = [0, 2, 5, 8, 15, 25, 35, 90]
NAMES = (["log_relief", "log_elev_std", "hypsometric_integral", "elev_skew", "elev_kurt",
          "slope_mean", "slope_std", "slope_p90"]
         + [f"slope_frac_{a}_{b}" for a, b in zip(SLOPE_BINS[:-1], SLOPE_BINS[1:])]
         + ["log_rough_mean", "log_rough_p90", "curv_absmean", "curv_std", "curv_convex_frac"])
LOG_COLS = {"log_relief", "log_elev_std", "log_rough_mean", "log_rough_p90"}


@torch.no_grad()
def features(z, px):
    """z (B,1,H,W) metros, px (B,) metros -> (B, 20) sin estandarizar."""
    z = z.float()
    B = z.shape[0]
    flat = z.flatten(1)
    zmin, zmax = flat.min(1).values, flat.max(1).values
    mean, std = flat.mean(1), flat.std(1)
    relief = zmax - zmin
    hyps = (mean - zmin) / relief.clamp_min(1e-3)
    zc = (flat - mean[:, None]) / std.clamp_min(1e-3)[:, None]
    skew, kurt = (zc ** 3).mean(1), (zc ** 4).mean(1) - 3

    dzdx, dzdy = gradients(z, px)
    slope = torch.rad2deg(torch.atan(torch.sqrt(dzdx ** 2 + dzdy ** 2))).flatten(1)
    s_mean, s_std = slope.mean(1), slope.std(1)
    s_p90 = torch.quantile(slope, 0.9, dim=1)
    s_hist = [((slope >= a) & (slope < b)).float().mean(1)
              for a, b in zip(SLOPE_BINS[:-1], SLOPE_BINS[1:])]

    p = px.view(-1, 1, 1, 1)
    resid = z - gaussian_blur(z, ROUGH_SIGMA_PX)
    rough = torch.sqrt(F.avg_pool2d(_pad(resid ** 2), 3, stride=1)).flatten(1)
    lap_k = torch.tensor([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=z.dtype,
                         device=z.device).view(1, 1, 3, 3)
    curv = (F.conv2d(_pad(gaussian_blur(z, CURV_SIGMA_PX)), lap_k) / p ** 2).flatten(1)  # 1/m

    cols = [torch.log1p(relief), torch.log1p(std), hyps, skew, kurt, s_mean, s_std, s_p90,
            *s_hist, torch.log1p(rough.mean(1)), torch.log1p(torch.quantile(rough, 0.9, dim=1)),
            curv.abs().mean(1) * 1e3, curv.std(1) * 1e3, (curv < 0).float().mean(1)]
    return torch.stack(cols, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=int, default=60)
    ap.add_argument("--batch", type=int, default=1024)
    a = ap.parse_args()

    art = ROOT / "data/artifacts"
    meta = pd.read_parquet(art / f"meta_{a.scale}.parquet")
    out = np.zeros((len(meta), len(NAMES)), np.float32)
    # los parches están en archivos por cuerpo; meta trae el índice dentro de cada uno
    for body, g in meta.groupby("body", sort=False):
        arr = np.load(ROOT / f"data/patches/patches_{body}_{a.scale}.npy", mmap_mode="r")
        local = g.patch_id.str.split("-").str[2].astype(int).to_numpy()
        rows = g.index.to_numpy()
        for s in range(0, len(g), a.batch):
            z = torch.from_numpy(np.array(arr[local[s:s + a.batch]])).unsqueeze(1).cuda()
            px = torch.full((len(z),), float(a.scale), device="cuda")
            out[rows[s:s + a.batch]] = features(z, px).cpu().numpy()
        print(f"{body}: {len(g)} parches")

    assert np.isfinite(out).all()
    mu, sd = out.mean(0), out.std(0) + 1e-8
    std_feat = (out - mu) / sd
    np.save(art / f"baseline_feat_{a.scale}.npy", std_feat.astype(np.float32))
    (art / f"baseline_feat_{a.scale}.json").write_text(json.dumps(
        dict(names=NAMES, mean=mu.tolist(), std=sd.tolist(), slope_bins=SLOPE_BINS), indent=2))
    print(pd.DataFrame(out, columns=NAMES).groupby(meta.body.values).median().T.round(3).to_string())
    print("->", art / f"baseline_feat_{a.scale}.npy")


if __name__ == "__main__":
    main()
