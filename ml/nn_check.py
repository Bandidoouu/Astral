#!/usr/bin/env python
"""Lámina de prueba: sitios del polo sur lunar y sus gemelos terrestres.

Para cada sitio busca el parche lunar del índice y sus k gemelos terrestres
(coseno en FAISS), con el sombreado de cada parche y su región. Para que la
lámina muestre lugares distintos, se descarta un gemelo a menos de --min-sep-km
de otro ya elegido (si no, salen 5 parches vecinos de la misma sierra).

Los sitios se ubican con el relieve: el parche más alto en un radio alrededor
de la coordenada aproximada (bordes y macizos) o el más cercano al centro
(fondo de cráter). Coordenadas aproximadas: confirmar con Ciencia y pitch.

  python -m ml.nn_check --out data/artifacts/nn_check.png
"""
import argparse
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

from ml.model.channels import make_channels

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))
R_MOON_KM = 1737.4
R_EARTH_KM = 6371.0

# (nombre, lat, lon, modo, radio_km). modo "high" = parche más alto en el radio;
# "rim" = más alto en un anillo [0.6R, 1.4R] del centro; "near" = el más cercano.
SITES = [
    ("Shackleton rim", -89.67, 129.78, "rim", 10.5),
    ("de Gerlache rim", -88.50, -87.10, "rim", 16.0),
    ("Malapert Massif", -86.00, 3.00, "high", 25.0),
    ("Mons Mouton", -84.60, 31.00, "high", 30.0),
    ("Haworth crater floor", -87.45, -5.00, "near", 0.0),
]


def gc_km(lat1, lon1, lat2, lon2, r):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dl = np.radians(lon2 - lon1)
    c = np.sin(p1) * np.sin(p2) + np.cos(p1) * np.cos(p2) * np.cos(dl)
    return r * np.arccos(np.clip(c, -1, 1))


def pick_site(moon, lat, lon, mode, radius):
    d = gc_km(lat, lon, moon.lat.to_numpy(), moon.lon.to_numpy(), R_MOON_KM)
    if mode == "near":
        return moon.index[np.argmin(d)]
    lo, hi = (0.6 * radius, 1.4 * radius) if mode == "rim" else (0, radius)
    cand = moon[(d >= lo) & (d <= hi)]
    assert len(cand), f"sin parches cerca de {lat},{lon}"
    return cand.elev_max_m.idxmax()


def hillshade(patch, scale_m):
    z = torch.from_numpy(np.asarray(patch, np.float32))[None, None]
    return make_channels(z, torch.tensor([float(scale_m)]))[0, 4].numpy()


def load_patch(pid, cache={}):
    body, scale, i = pid.split("-")
    name = {"earth": f"earth_{scale}", "moon": f"moon_{scale}", "mars": f"mars_{scale}"}[body]
    if name not in cache:
        cache[name] = np.load(ROOT / f"data/patches/patches_{name}.npy", mmap_mode="r")
    return cache[name][int(i)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=int, default=60)
    ap.add_argument("--tag", default="")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--min-sep-km", type=float, default=20.0)
    ap.add_argument("--out", type=Path, default=ROOT / "data/artifacts/nn_check.png")
    a = ap.parse_args()

    art = ROOT / "data/artifacts"
    emb = np.load(art / f"emb_{a.scale}{a.tag}.npy")
    meta = pd.read_parquet(art / f"meta_{a.scale}{a.tag}.parquet")
    moon = meta[meta.body == "moon"]
    earth_idx = np.flatnonzero(meta.body == "earth")
    E = emb[earth_idx]

    rows = []
    for name, lat, lon, mode, rad in SITES:
        qi = pick_site(moon, lat, lon, mode, rad)
        sims = E @ emb[qi]
        order = np.argsort(-sims)
        chosen = []
        for j in order:
            m = meta.iloc[earth_idx[j]]
            if all(gc_km(m.lat, m.lon, c[0].lat, c[0].lon, R_EARTH_KM) > a.min_sep_km
                   for c in chosen):
                chosen.append((m, float(sims[j])))
            if len(chosen) == a.k:
                break
        rows.append((name, meta.iloc[qi], chosen))
        print(f"\n{name}: {meta.iloc[qi].patch_id} ({meta.iloc[qi].lat:.2f}, "
              f"{meta.iloc[qi].lon:.2f}), relieve {meta.iloc[qi].elev_max_m - meta.iloc[qi].elev_min_m:.0f} m")
        for m, s in chosen:
            print(f"   {s:.3f}  {m.patch_id}  {m.region:<28} ({m.lat:.2f}, {m.lon:.2f})"
                  f"{'  [HOLDOUT Pinacate]' if m.holdout else ''}")

    fig, ax = plt.subplots(len(rows), a.k + 1, figsize=(2.3 * (a.k + 1), 2.6 * len(rows)))
    for r, (name, q, chosen) in enumerate(rows):
        ax[r, 0].imshow(hillshade(load_patch(q.patch_id), q.scale_m), cmap="gray", vmin=0, vmax=1)
        ax[r, 0].set_title(f"MOON · {name}\n{q.lat:.2f}°, {q.lon:.2f}°\n"
                           f"relief {q.elev_max_m - q.elev_min_m:.0f} m",
                           fontsize=8, color="#1f4e9c", fontweight="bold")
        for c, (m, s) in enumerate(chosen, start=1):
            ax[r, c].imshow(hillshade(load_patch(m.patch_id), m.scale_m), cmap="gray", vmin=0, vmax=1)
            ax[r, c].set_title(f"{m.region}\n{m.lat:.2f}°, {m.lon:.2f}°\n"
                               f"cos {s:.3f} · relief {m.elev_max_m - m.elev_min_m:.0f} m",
                               fontsize=7)
    for x in ax.flat:
        x.set_xticks([]); x.set_yticks([])
    fig.suptitle(f"ASTRAL nearest Earth analogs · {a.scale} m/px patches (7.68 km) · "
                 f"encoder{a.tag or '_v1'} · hillshade, sun az 315°", fontsize=10)
    plt.tight_layout()
    plt.savefig(a.out, dpi=90)
    print("\n->", a.out)


if __name__ == "__main__":
    main()
