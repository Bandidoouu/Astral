#!/usr/bin/env python
"""Rejillas globales de la Tierra (0.05°) para las dimensiones térmica y de albedo.

Temperatura (MODIS Terra MOD11C3 v061, 12 meses de 2023, LST en kelvin):
  tmax   = máximo mensual de LST_Day_CMG
  tmin   = mínimo mensual de LST_Night_CMG
  trange = tmax - tmin
Albedo (MODIS MCD43C3 v061, un día por mes de 2023): media anual del albedo de cielo
blanco (WSA) en las bandas 2 (858 nm) y 5 (1240 nm), que rodean los 1064 nm del
láser de LOLA. Es una aproximación: LOLA mide albedo normal a una sola longitud
de onda; MODIS, albedo hemisférico. Se documenta como límite.

Sin dato (océano, nubes todo el año, nieve sin retrieval) = NaN. Nunca se rellena.

  python -m ml.features.earth_climate
"""
import glob
import os
import subprocess
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[2]))
OUT = ROOT / "data/features/earth_climate_005deg.tif"


def read_sds(path, grid, name, scale, fill):
    """El GDAL de rasterio no trae HDF4: se convierte con el gdal_translate del sistema."""
    tmp = OUT.parent / "tmp" / f"{Path(path).stem}_{name}.tif"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["gdal_translate", "-q", f'HDF4_EOS:EOS_GRID:"{path}":{grid}:{name}', str(tmp)],
                   check=True)
    with rasterio.open(tmp) as ds:
        a = ds.read(1).astype(np.float32)
    tmp.unlink()
    bad = a == fill
    a *= scale
    a[bad] = np.nan
    return a


def main():
    lst = sorted(glob.glob(str(ROOT / "data/raw/earth/lst/MOD11C3*.hdf")))
    alb = sorted(glob.glob(str(ROOT / "data/raw/earth/albedo/MCD43C3*.hdf")))
    print(f"MOD11C3: {len(lst)} meses | MCD43C3: {len(alb)} días")
    g = "MODIS_MONTHLY_0.05DEG_CMG_LST"
    day = np.stack([read_sds(f, g, "LST_Day_CMG", 0.02, 0) for f in lst])
    night = np.stack([read_sds(f, g, "LST_Night_CMG", 0.02, 0) for f in lst])
    with np.errstate(all="ignore"):
        tmax = np.nanmax(day, 0)
        tmin = np.nanmin(night, 0)
    del day, night
    trange = tmax - tmin
    neg = trange < 0          # día sin meses válidos (nubes): rango no físico -> sin dato
    print(f"  rango negativo en {int(neg.sum())} celdas -> sin dato")
    trange[neg] = np.nan
    ga = "MCD_CMG_BRDF_0.05Deg"
    nir = []
    for f in alb:
        b2 = read_sds(f, ga, "Albedo_WSA_Band2", 0.001, 32767)
        b5 = read_sds(f, ga, "Albedo_WSA_Band5", 0.001, 32767)
        nir.append((b2 + b5) / 2)
    with np.errstate(all="ignore"):
        albedo = np.nanmean(np.stack(nir), 0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    prof = dict(driver="GTiff", height=3600, width=7200, count=4, dtype="float32",
                crs="EPSG:4326", transform=from_origin(-180, 90, 0.05, 0.05), nodata=np.nan,
                compress="deflate", tiled=True)
    with rasterio.open(OUT, "w", **prof) as ds:
        for i, (a, n) in enumerate([(tmax, "tmax_k"), (tmin, "tmin_k"), (trange, "trange_k"),
                                    (albedo, "albedo_nir")], 1):
            ds.write(a.astype(np.float32), i)
            ds.set_band_description(i, n)
            v = a[np.isfinite(a)]
            print(f"  {n:<11} min {v.min():7.2f}  mediana {np.median(v):7.2f}  máx {v.max():7.2f}  "
                  f"con dato {100 * v.size / a.size:4.1f}% del globo")
    print("->", OUT)


if __name__ == "__main__":
    main()
