#!/usr/bin/env python
"""Texturas de los globos (equirectangulares 2:1, longitud -180 a 180, norte arriba).

Por cuerpo, en frontend/public/textures/{earth,moon,mars}/:
  color_8k.jpg, color_4k.jpg   color real (LROC WAC / Viking / Blue Marble), 8192x4096 y 4096x2048
  height_4k.png                altura en escala de grises de 8 bits (0 = mínimo, 255 = máximo)
  height.json                  min_m, max_m, fuente y notas (para desplazar el relieve)
  normal_4k.jpg                mapa de normales (espacio tangente, RGB) de esa misma altura
  hillshade_4k.jpg             sombreado (Sol al noroeste, 45°)
  topography_4k.jpg            topografía en color + topography_legend.png (metros)
  suitability_4k.png           (Luna y Marte) aptitud 0-1 en RGBA, transparente sin dato
                               + suitability_legend.png

  python -m ml.textures --body moon
"""
import argparse
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))
RAW = ROOT / "data/raw/textures"
OUT = ROOT / "frontend/public/textures"
W, H = 4096, 2048
RADIUS_M = {"earth": 6371000.0, "moon": 1737400.0, "mars": 3396190.0}
# DEM global: ruta, metros por unidad, latitudes que cubre, ¿empieza en 0° E?
DEM = {"moon": ("data/raw/moon/lola_global/ldem_64_float.lbl", 1000.0, (90, -90), True),
       "mars": ("data/raw/mars/mars_megdr.vrt", 1.0, (88, -88), True),
       "earth": ("data/raw/earth/srtmgl30/srtmgl30.vrt", 1.0, (90, -60), False)}
EXAG = {"moon": 8.0, "mars": 6.0, "earth": 20.0}       # exageración vertical de normales y sombras
CMAP = {"moon": "cividis", "mars": "magma", "earth": "terrain"}
SOURCES = {"moon": "NASA SVS CGI Moon Kit (LRO LROC WAC color mosaic, poles filled), svs.gsfc.nasa.gov/4720",
           "mars": "NASA Mars Trek, Mars_Viking_MDIM21_ClrMosaic_global_232m (Viking color mosaic), WMTS level 4",
           "earth": "NASA GIBS WMS, BlueMarble_NextGeneration (NASA Earth Observatory Blue Marble)"}
DEM_NAME = {"moon": "LRO LOLA GDR ldem_64 (64 px/deg)", "mars": "MGS MOLA MEGDR 128 px/deg",
            "earth": "NASA SRTMGL30 v002 (30 arc-sec)"}


def color(body):
    out = OUT / body
    if body == "moon":
        im = Image.open(RAW / "moon/lroc_color_poles_8k.tif").convert("RGB")
    elif body == "earth":
        im = Image.open(RAW / "earth/bluemarble_8k.jpg").convert("RGB")
    else:
        im = Image.new("RGB", (8192, 4096))
        for r in range(16):
            for c in range(32):
                im.paste(Image.open(RAW / f"mars/tiles/{r}_{c}.jpg").convert("RGB"), (c * 256, r * 256))
    assert im.size == (8192, 4096), im.size
    im.save(out / "color_8k.jpg", quality=88, optimize=True)
    im.resize((4096, 2048), Image.LANCZOS).save(out / "color_4k.jpg", quality=90, optimize=True)


def load_height(body):
    path, to_m, (lat_top, lat_bot), starts_at_0 = DEM[body]
    rows = int(round(H * (lat_top - lat_bot) / 180))
    with rasterio.open(ROOT / path) as ds:
        z = ds.read(1, out_shape=(rows, W), resampling=Resampling.average).astype(np.float32)
        nod = ds.nodata
    bad = ~np.isfinite(z) | (z < -1e30)
    if nod is not None:
        bad |= z == nod
    z[bad] = np.nan
    z *= to_m
    if starts_at_0:
        z = np.roll(z, W // 2, axis=1)                   # 0..360 -> -180..180
    full = np.full((H, W), np.nan, np.float32)
    r0 = int(round(H * (90 - lat_top) / 180))
    full[r0:r0 + rows] = z
    note = []
    if body == "earth":
        full[np.isnan(full) & (np.arange(H)[:, None] < r0 + rows)] = 0.0      # océano = 0 m
        note.append("ocean = 0 m (SRTMGL30); south of 60 S (Antarctica) has no SRTMGL30 data: filled with 0 m")
    else:
        note.append(f"rows beyond {lat_top} / {lat_bot} deg filled with the nearest valid row")
    # relleno de filas sin dato (polos o Antártida) con la fila válida más cercana
    valid_rows = np.flatnonzero(np.isfinite(full).any(1))
    for r in range(H):
        if not np.isfinite(full[r]).any():
            full[r] = 0.0 if body == "earth" else full[valid_rows[np.argmin(abs(valid_rows - r))]]
    full = np.where(np.isfinite(full), full, np.nanmedian(full))
    return full, note


def gradients(z, body):
    R = RADIUS_M[body]
    dy = np.pi * R / H
    lat = 90 - (np.arange(H) + 0.5) * 180 / H
    dx = 2 * np.pi * R / W * np.maximum(np.cos(np.radians(lat)), 0.2)[:, None]
    gx = (np.roll(z, -1, 1) - np.roll(z, 1, 1)) / (2 * dx)
    gy = np.zeros_like(z)
    gy[1:-1] = (z[:-2] - z[2:]) / (2 * dy)               # +y = norte
    return gx * EXAG[body], gy * EXAG[body]


def write_legend(path, cmap, vmin, vmax, label, ticks_fmt="{:,.0f}"):
    fig, ax = plt.subplots(figsize=(5, 0.9))
    fig.subplots_adjust(bottom=0.5, top=0.95, left=0.05, right=0.95)
    sm = plt.cm.ScalarMappable(norm=matplotlib.colors.Normalize(vmin, vmax), cmap=cmap)
    cb = fig.colorbar(sm, cax=ax, orientation="horizontal")
    cb.set_label(label)
    plt.savefig(path, dpi=120, transparent=True)
    plt.close(fig)


def relief(body):
    out = OUT / body
    z, notes = load_height(body)
    lo, hi = float(np.floor(z.min())), float(np.ceil(z.max()))
    Image.fromarray(np.round((z - lo) / (hi - lo) * 255).astype(np.uint8), "L").save(out / "height_4k.png", optimize=True)
    gx, gy = gradients(z, body)
    n = np.stack([-gx, -gy, np.ones_like(z)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    Image.fromarray(np.round((n * 0.5 + 0.5) * 255).astype(np.uint8), "RGB").save(out / "normal_4k.jpg", quality=92)
    az, alt = np.radians(315), np.radians(45)
    sun = np.array([np.sin(az) * np.cos(alt), np.cos(az) * np.cos(alt), np.sin(alt)])
    shade = np.clip((n * sun).sum(-1), 0, 1)
    Image.fromarray(np.round(shade * 255).astype(np.uint8), "L").save(out / "hillshade_4k.jpg", quality=90)
    # topografía en color (percentiles 1-99 para que no la dominen los extremos) con sombreado suave
    vmin, vmax = (float(np.percentile(z, 1)), float(np.percentile(z, 99)))
    if body == "earth":
        vmin, vmax = -500.0, 5000.0
    rgb = plt.get_cmap(CMAP[body])(np.clip((z - vmin) / (vmax - vmin), 0, 1))[..., :3]
    rgb *= (0.65 + 0.35 * shade)[..., None]
    Image.fromarray(np.round(rgb * 255).astype(np.uint8), "RGB").save(out / "topography_4k.jpg", quality=90)
    write_legend(out / "topography_legend.png", CMAP[body], vmin, vmax, "Elevation (m)")
    meta = dict(body=body, width=W, height=H, projection="equirectangular, lon -180..180, north up",
                min_m=lo, max_m=hi, encoding="height_m = min_m + (pixel / 255) * (max_m - min_m)",
                source=DEM_NAME[body], normal_and_hillshade_vertical_exaggeration=EXAG[body],
                normal_encoding="tangent space, RGB = (n * 0.5 + 0.5) * 255, +x east, +y north, +z up",
                topography=dict(colormap=CMAP[body], min_m=vmin, max_m=vmax, legend="topography_legend.png"),
                notes=notes)
    (out / "height.json").write_text(json.dumps(meta, indent=1))
    return meta


def suitability(body):
    out = OUT / body
    art = ROOT / "data/artifacts/suitability"
    if body == "moon":
        import subprocess
        tmp = out / "_tmp_suit.tif"
        subprocess.run(["gdalwarp", "-q", "-overwrite", "-t_srs", "+proj=longlat +R=1737400 +no_defs",
                        "-te", "-180", "-90", "180", "90", "-ts", "8192", "4096", "-r", "bilinear",
                        "-dstnodata", "nan", str(art / "moon_south_total.tif"), str(tmp)], check=True)
        with rasterio.open(tmp) as ds:
            a = ds.read(1)
        tmp.unlink()
        size = (8192, 4096)
        note = "Moon south pole only (south of ~75 S, LOLA polar grid); 8192x4096 so the polar cap keeps detail"
    else:
        with rasterio.open(art / "mars_total.tif") as ds:
            g = ds.read(1)
            lon_left = ds.transform.c
        rows88 = g.shape[0]
        a = np.full((int(round(rows88 * 180 / 176)), g.shape[1]), np.nan, np.float32)
        r0 = (a.shape[0] - rows88) // 2
        a[r0:r0 + rows88] = g
        if abs(lon_left) < 1:                              # 0..360 -> -180..180
            a = np.roll(a, a.shape[1] // 2, axis=1)
        a = np.asarray(Image.fromarray(a).resize((W, H), Image.NEAREST))
        size = (W, H)
        note = "Mars 60 N to 60 S (Mars Odyssey hydrogen coverage); 0.25 deg cells"
    rgba = plt.get_cmap("viridis")(np.nan_to_num(np.clip(a, 0, 1)))
    rgba[..., 3] = np.where(np.isfinite(a), 0.85, 0.0)
    Image.fromarray(np.round(rgba * 255).astype(np.uint8), "RGBA").save(out / "suitability_4k.png", optimize=True)
    write_legend(out / "suitability_legend.png", "viridis", 0, 1, "Base suitability score (0-1)")
    return dict(file="suitability_4k.png", size=list(size), note=note)


README = """# {title} globe textures

Equirectangular (2:1), longitude -180 to 180 (left to right), north up. Generated by
`python -m ml.textures --body {body}` (ASTRAL, NASA Space Apps 2026).

| File | Resolution | What it is | Source | License |
| --- | --- | --- | --- | --- |
| `color_8k.jpg`, `color_4k.jpg` | 8192x4096, 4096x2048 | True color | {color_src} | {color_lic} |
| `height_4k.png` + `height.json` | 4096x2048 | 8-bit grayscale height (min {min_m:,.0f} m, max {max_m:,.0f} m) for displacement | {dem} | Public domain (NASA) |
| `normal_4k.jpg` | 4096x2048 | Normal map from the same height (vertical exaggeration x{exag:g}) | derived from {dem} | Public domain (NASA) |
| `hillshade_4k.jpg` | 4096x2048 | Hillshade, sun from the NW at 45 deg | derived from {dem} | Public domain (NASA) |
| `topography_4k.jpg` + `topography_legend.png` | 4096x2048 | Color topography, legend in meters | derived from {dem} | Public domain (NASA) |
{suit_row}
Height decoding: `height_m = min_m + (pixel / 255) * (max_m - min_m)` (see `height.json`).
Notes: {notes}
"""
COLOR_LIC = "NASA imagery: no copyright, credit NASA (see nasa.gov/nasa-brand-center/images-and-media)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--body", nargs="+", default=["moon", "mars", "earth"])
    a = ap.parse_args()
    for body in a.body:
        (OUT / body).mkdir(parents=True, exist_ok=True)
        color(body)
        meta = relief(body)
        suit_row = ""
        if body in ("moon", "mars"):
            s = suitability(body)
            src = "ml/suitability_moon.py (LOLA slope, Diviner ice and temperature)" if body == "moon" \
                else "ml/suitability_mars.py (MOLA slope and elevation, Mars Odyssey GRS hydrogen)"
            suit_row = (f"| `suitability_4k.png` + `suitability_legend.png` | {s['size'][0]}x{s['size'][1]} | "
                        f"Base suitability 0-1 (viridis), transparent where there is no data. {s['note']}. "
                        f"A suggestion, not a site selection | {src} | Public domain (NASA data) |\n")
        (OUT / body / "README.md").write_text(README.format(
            title=body.capitalize(), body=body, color_src=SOURCES[body], color_lic=COLOR_LIC,
            min_m=meta["min_m"], max_m=meta["max_m"], dem=DEM_NAME[body], exag=EXAG[body],
            suit_row=suit_row, notes="; ".join(meta["notes"])))
        sizes = {p.name: round(p.stat().st_size / 1e6, 1) for p in sorted((OUT / body).iterdir())}
        print(body, f"altura {meta['min_m']:.0f}..{meta['max_m']:.0f} m", sizes, flush=True)


if __name__ == "__main__":
    main()
