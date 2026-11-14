#!/usr/bin/env python
"""Baja NASADEM_HGT (NASA Earthdata) en una caja y arma un mosaico en metros.

Deja los .zip en data/raw/earth/analogs/{name}/dem/, extrae los .hgt en
data/raw/earth/analogs/{name}/hgt/ y arma un VRT geográfico (WGS84, 1 arcseg)
en data/raw/earth/analogs/{name}/{name}.vrt. Es reanudable: no vuelve a bajar
los .zip que ya están.

  python -m ml.data.fetch_nasadem --name arizona --bbox -112.4 34.7 -110.6 35.8
"""
import argparse
import os
import subprocess
import zipfile
from pathlib import Path

import earthaccess

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[2]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--bbox", type=float, nargs=4, metavar=("W", "S", "E", "N"), required=True)
    a = ap.parse_args()

    d = ROOT / "data/raw/earth/analogs" / a.name
    (d / "dem").mkdir(parents=True, exist_ok=True)
    (d / "hgt").mkdir(exist_ok=True)
    earthaccess.login(strategy="netrc")
    res = earthaccess.search_data(short_name="NASADEM_HGT", bounding_box=tuple(a.bbox))
    print(f"{a.name}: {len(res)} mosaicos NASADEM_HGT", flush=True)
    files = earthaccess.download(res, str(d / "dem"))
    for f in files:
        with zipfile.ZipFile(f) as z:
            for m in z.namelist():
                if m.endswith(".hgt"):
                    z.extract(m, d / "hgt")
    hgts = sorted(str(p) for p in (d / "hgt").rglob("*.hgt"))
    assert hgts, "no se extrajo ningún .hgt"
    vrt = d / f"{a.name}.vrt"
    subprocess.run(["gdalbuildvrt", "-q", "-overwrite", str(vrt), *hgts], check=True)
    print(f"-> {vrt} ({len(hgts)} .hgt)", flush=True)


if __name__ == "__main__":
    main()
