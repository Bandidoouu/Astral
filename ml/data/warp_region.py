#!/usr/bin/env python
"""Reproyecta una región de un DEM a una proyección métrica local (Lambert
azimutal equivalente centrada en el sitio), lista para make_patches.

Sirve para fuentes equirectangulares (SLDEM2015, LOLA global, MOLA MEGDR,
NASADEM geográfico). Conserva las unidades de la fuente (km en LOLA/SLDEM):
la conversión a metros la hace make_patches con --to-m.

  python -m ml.data.warp_region --src data/raw/moon/sldem2015/sldem2015_512_00n_30n_270_315_float.lbl \
      --body moon --lat 14 --lon -56 --half-km 150 --res 60 --name marius
"""
import argparse
import os
import subprocess
from pathlib import Path

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[2]))
DATUM = {"moon": "+R=1737400", "mars": "+R=3396190", "earth": "+ellps=WGS84"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--body", choices=list(DATUM), required=True)
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True, help="-180 a 180, positiva al este")
    ap.add_argument("--half-km", type=float, required=True, help="media anchura de la región")
    ap.add_argument("--res", type=float, required=True, help="tamaño de píxel en metros")
    ap.add_argument("--name", required=True)
    ap.add_argument("--src-srs", default=None, help="forzar el CRS de la fuente si GDAL no lo lee bien")
    a = ap.parse_args()

    out = ROOT / f"data/raw/{a.body}/regions/{a.name}_{int(a.res)}m.tif"
    out.parent.mkdir(parents=True, exist_ok=True)
    h = a.half_km * 1000
    srs = f"+proj=laea +lat_0={a.lat} +lon_0={a.lon} {DATUM[a.body]} +units=m +no_defs"
    cmd = ["gdalwarp", "-q", "-overwrite", "-t_srs", srs, "-te", str(-h), str(-h), str(h), str(h),
           "-tr", str(a.res), str(a.res), "-r", "bilinear", "-ot", "Float32",
           "-dstnodata", "-32768", "-wm", "512", "-co", "COMPRESS=DEFLATE", "-co", "TILED=YES"]
    if a.src_srs:
        cmd += ["-s_srs", a.src_srs]
    subprocess.run(cmd + [a.src, str(out)], check=True)
    print("->", out)


if __name__ == "__main__":
    main()
