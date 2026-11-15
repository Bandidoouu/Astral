#!/usr/bin/env python
"""Capa de aptitud para Marte (reglas transparentes, no la red). Rejilla global de 0.25°.

Recorte de alcance (mentor): solo pendiente y altitud de MOLA y el hidrógeno de Mars
Odyssey. TES, minerales, polvo y radiación quedan fuera ("sin dato").

  landing    fracción de píxeles de MOLA (~926 m) con pendiente < 2°
  rover      fracción con pendiente < 5°
             (umbrales más bajos que en la Luna, 8° y 15° a 60 m: a ~1 km de base la mediana
             de Marte es ~0.5° y solo ~2% pasa de 8°; MOLA no ve peligros a escala de módulo)
  elevation  altitud baja (más atmósfera para frenar al entrar): 1 en <= -1 km, 0 en >= +1 km
  hydrogen   agua equivalente de Mars Odyssey GRS (5x5°, suavizado): 0 en <= 2% en peso,
             1 en >= 7% (solo entre 60° N y 60° S: fuera, sin dato)
  total      media ponderada donde todos los criterios tienen dato

Pesos: landing 0.30, rover 0.20, hydrogen 0.30, elevation 0.20 (mismos que la Luna, con
la altitud en lugar de la temperatura). Es una sugerencia, no una elección final.

  python -m ml.suitability_mars
"""
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.transform import from_origin

from ml.data.make_patches_global import load_global

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))
OUT = ROOT / "data/artifacts/suitability"
GRS = ROOT / "data/raw/mars/grs/h2o_sr_5x5.tab"
CELL = 0.25
WEIGHTS = {"landing": 0.30, "rover": 0.20, "hydrogen": 0.30, "elevation": 0.20}
RULES = {"landing": "fraction of MOLA pixels (~926 m) with slope < 2 deg (km-baseline slopes are much lower than lander-scale slopes)",
         "rover": "fraction of MOLA pixels with slope < 5 deg",
         "elevation": "MOLA elevation: 1 at <= -1 km, 0 at >= +1 km (thicker atmosphere for entry)",
         "hydrogen": "Mars Odyssey GRS water-equivalent hydrogen: 0 at <= 2 wt%, 1 at >= 7 wt% "
                     "(60 N to 60 S only)",
         "total": "weighted mean where all criteria have data"}
# centros aproximados (confirmar con Ciencia); lon -180..180 este positivo
CANDIDATES = [
    ("Jezero crater (Perseverance)", 18.38, 77.58, "landed missions"),
    ("Gale crater (Curiosity)", -5.40, 137.80, "landed missions"),
    ("Utopia Planitia (Zhurong)", 25.10, 109.90, "landed missions"),
    ("Elysium Planitia (InSight)", 4.50, 135.62, "landed missions"),
    ("Meridiani Planum (Opportunity)", -1.95, -5.53, "landed missions"),
    ("Gusev crater (Spirit)", -14.57, 175.47, "landed missions"),
    ("Arcadia Planitia (shallow ice)", 40.0, -160.0, "human-exploration candidates"),
    ("Deuteronilus Mensae", 44.0, 22.0, "human-exploration candidates"),
    ("Mawrth Vallis", 22.60, -16.50, "human-exploration candidates"),
    ("Erebus Montes", 38.0, -170.0, "human-exploration candidates"),
]
RADIUS_KM = 3396.19


def ramp(x, lo, hi):
    return np.clip((x - lo) / (hi - lo), 0, 1)


def mola_grids():
    """Pendiente (fracciones < 8° y < 15°) y altitud media por celda de 0.25°."""
    z, nm, (lon0, dlon, lat0, dlat) = load_global("data/raw/mars/mars_megdr.vrt", 2)
    H, W = z.shape
    px_ns = abs(dlat) * np.pi / 180 * RADIUS_KM * 1000
    k = int(round(CELL / abs(dlat)))                      # píxeles por celda
    nr, nc = H // k, W // k
    f8, f15, elev = (np.full((nr, nc), np.nan, np.float32) for _ in range(3))
    for i in range(nr):
        r0, r1 = max(i * k - 1, 0), min((i + 1) * k + 1, H)
        blk = z[r0:r1].astype(np.float32)
        lat = lat0 + dlat * (np.arange(r0, r1) + 0.5)
        px_ew = px_ns * np.cos(np.radians(lat))[:, None]
        gy = np.gradient(blk, axis=0) / px_ns
        gx = (np.roll(blk, -1, 1) - np.roll(blk, 1, 1)) / (2 * px_ew)
        s = np.degrees(np.arctan(np.hypot(gx, gy)))
        o = i * k - r0
        s, e, bad = s[o:o + k], blk[o:o + k], nm[i * k:(i + 1) * k].astype(bool)
        s = s[:, :nc * k].reshape(k, nc, k)
        e = e[:, :nc * k].reshape(k, nc, k)
        ok = ~bad[:, :nc * k].reshape(k, nc, k)
        n = ok.sum((0, 2))
        with np.errstate(invalid="ignore"):
            f8[i] = np.where(n > 0, ((s < 2) & ok).sum((0, 2)) / n, np.nan)
            f15[i] = np.where(n > 0, ((s < 5) & ok).sum((0, 2)) / n, np.nan)
            elev[i] = np.where(n > 0, (e * ok).sum((0, 2)) / n, np.nan)
    lat_top = lat0
    lon_left = lon0
    return f8, f15, elev, lat_top, lon_left


def grs_grid(shape, lat_top, lon_left):
    a = np.loadtxt(GRS)
    a = a[a[:, 2] < 9999]
    g = np.full((36, 72), np.nan, np.float32)            # 5° (norte arriba, lon 0..360)
    g[((90 - a[:, 0]) // 5).astype(int), (a[:, 1] // 5).astype(int)] = a[:, 2]
    nr, nc = shape
    lat = lat_top - CELL * (np.arange(nr) + 0.5)
    lon = (lon_left + CELL * (np.arange(nc) + 0.5)) % 360
    return g[np.clip(((90 - lat) // 5).astype(int), 0, 35)][:, np.clip((lon // 5).astype(int), 0, 71)]


def disc_mean(a, lat_top, lon_left, la, lo, r_km=50):
    nr, nc = a.shape
    lat = lat_top - CELL * (np.arange(nr) + 0.5)
    lon = lon_left + CELL * (np.arange(nc) + 0.5)
    p1, p2 = np.radians(la), np.radians(lat)[:, None]
    c = np.sin(p1) * np.sin(p2) + np.cos(p1) * np.cos(p2) * np.cos(np.radians(lon[None] - lo))
    d = RADIUS_KM * np.arccos(np.clip(c, -1, 1))
    v = a[(d <= r_km) & np.isfinite(a)]
    return float(v.mean()) if v.size else None


def save_png(a, path, title, lon_left=-180.0, lat_top=88.0):
    fig, ax = plt.subplots(figsize=(12, 6.2))
    cmap = plt.get_cmap("Blues").copy()
    cmap.set_bad((0, 0, 0, 0))
    im = ax.imshow(np.ma.masked_invalid(a), cmap=cmap, vmin=0, vmax=1, extent=(lon_left, lon_left + 360, lat_top - CELL * a.shape[0], lat_top))
    ax.set_title(title)
    ax.set_xlabel("Longitude (deg E)")
    ax.set_ylabel("Latitude (deg)")
    fig.colorbar(im, ax=ax, shrink=0.7, label="score (0-1)")
    plt.savefig(path, dpi=100, transparent=True, bbox_inches="tight")
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    f8, f15, elev, lat_top, lon_left = mola_grids()
    h2o = grs_grid(f8.shape, lat_top, lon_left)
    crit = {"landing": f8, "rover": f15, "elevation": 1 - ramp(elev, -1000, 1000),
            "hydrogen": ramp(h2o, 2, 7)}
    tot = sum(WEIGHTS[k] * v for k, v in crit.items())            # NaN si falta alguno
    crit["total"] = tot
    nr, nc = f8.shape
    prof = dict(driver="GTiff", height=nr, width=nc, count=1, dtype="float32", crs=None,
                transform=from_origin(lon_left, lat_top, CELL, CELL), nodata=np.nan, compress="deflate")
    for k, v in crit.items():
        with rasterio.open(OUT / f"mars_{k}.tif", "w", **prof) as ds:
            ds.write(v.astype(np.float32), 1)
        save_png(v, OUT / f"mars_{k}.png", f"Mars base suitability: {k}", lon_left, lat_top)
        ok = v[np.isfinite(v)]
        print(f"  {k:<10} mediana {np.median(ok):.3f}  con dato {100 * ok.size / v.size:.0f}%")
    with rasterio.open(OUT / "mars_h2o_wt_pct.tif", "w", **prof) as ds:
        ds.write(h2o.astype(np.float32), 1)

    valid = tot[np.isfinite(tot)]
    cands = []
    for name, la, lo, grp in CANDIDATES:
        t = disc_mean(tot, lat_top, lon_left, la, lo)
        row = dict(name=name, lat=la, lon=lo, group=grp, total=t,
                   percentile_vs_mars=None if t is None else round(100 * float((valid < t).mean()), 1),
                   **{k: disc_mean(crit[k], lat_top, lon_left, la, lo) for k in WEIGHTS},
                   h2o_wt_pct=disc_mean(h2o, lat_top, lon_left, la, lo))
        cands.append(row)
        print(f"  {name:<34} total {t if t is None else round(t, 3)}  "
              f"percentil {row['percentile_vs_mars']}")
    meta = dict(weights=WEIGHTS, rules=RULES,
                missing=["thermal inertia and albedo (TES)", "minerals", "dust and wind",
                         "radiation", "illumination"],
                caveat="Suggestion, not a final site selection. Scope: MOLA slope and elevation "
                       "plus Mars Odyssey hydrogen only.",
                grid=dict(crs="Mars equirectangular (deg)", cell_deg=CELL, lat_top=lat_top,
                          lon_left=lon_left),
                candidates=cands, candidate_coordinates="approximate centers; confirm with Science")
    (OUT / "suitability_mars.json").write_text(json.dumps(meta, indent=1))

    fig, ax = plt.subplots(figsize=(8, 5))
    ok = [c for c in cands if c["total"] is not None]
    ok.sort(key=lambda c: c["total"])
    ax.barh([c["name"] for c in ok], [c["total"] for c in ok],
            color=["#2a78d6" if c["group"] == "landed missions" else "#eb6834" for c in ok])
    ax.axvline(np.median(valid), color="#888", ls="--", lw=1, label="Mars median (60N-60S)")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Suitability score (mean within 50 km)")
    ax.set_title("Mars sites: slope, elevation and hydrogen (MOLA + Mars Odyssey)")
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(OUT / "suitability_mars_candidates.png", dpi=110, facecolor="#fcfcfb")
    print("->", OUT)


if __name__ == "__main__":
    main()
