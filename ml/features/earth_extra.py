#!/usr/bin/env python
"""Rejillas terrestres (0.05°) para hielo, tipo de suelo y aridez.

  snow_frac  fracción anual de nieve o hielo: media mensual de MOD10CM (2023), solo
             con >= 6 meses válidos (nube, noche, agua y vacío no cuentan)
  albedo_sw  albedo de onda corta (cielo blanco) medio anual, MCD43C3
  ati        inercia térmica aparente = (1 - albedo_sw) / (LST día - LST noche),
             con las medias anuales de MOD11C3; solo si la diferencia es >= 2 K.
             Más alta = suelo más rocoso/compacto; más baja = polvo/arena suelta
  precip_mm  precipitación anual 2023 de NASA GPM IMERG mensual (V07), si está
             descargada; si no, la banda queda toda en NaN

Sin dato = NaN; nunca se rellena.

  python -m ml.features.earth_extra
"""
import calendar
import glob
import os
import subprocess
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[2]))
OUT = ROOT / "data/features/earth_extra_005deg.tif"
TMP = ROOT / "data/features/tmp"


def sds(path, grid, name):
    """El GDAL de rasterio no trae HDF4: se convierte con el gdal_translate del sistema."""
    TMP.mkdir(parents=True, exist_ok=True)
    tmp = TMP / f"{Path(path).stem}_{name}.tif"
    subprocess.run(["gdal_translate", "-q", f'HDF4_EOS:EOS_GRID:"{path}":{grid}:{name}', str(tmp)],
                   check=True)
    with rasterio.open(tmp) as ds:
        a = ds.read(1)
    tmp.unlink()
    return a


def main():
    # nieve
    snow = []
    for f in sorted(glob.glob(str(ROOT / "data/raw/earth/snow/MOD10CM*.hdf"))):
        a = sds(f, "MOD_CMG_Snow_5km", "Snow_Cover_Monthly_CMG").astype(np.float32)
        a[a > 100] = np.nan
        snow.append(a / 100)
    snow = np.stack(snow)
    nvalid = np.isfinite(snow).sum(0)
    with np.errstate(all="ignore"):
        snow_frac = np.nanmean(snow, 0)
    snow_frac[nvalid < 6] = np.nan
    del snow
    print(f"nieve: {len(nvalid)} filas, meses válidos mediana {np.median(nvalid):.0f}")

    # albedo de onda corta
    alb = []
    for f in sorted(glob.glob(str(ROOT / "data/raw/earth/albedo/MCD43C3*.hdf"))):
        a = sds(f, "MCD_CMG_BRDF_0.05Deg", "Albedo_WSA_shortwave").astype(np.float32)
        a[a == 32767] = np.nan
        alb.append(a * 0.001)
    with np.errstate(all="ignore"):
        albedo_sw = np.nanmean(np.stack(alb), 0)
    del alb

    # LST media anual de día y de noche -> ATI
    day, night = [], []
    for f in sorted(glob.glob(str(ROOT / "data/raw/earth/lst/MOD11C3*.hdf"))):
        for name, lst in (("LST_Day_CMG", day), ("LST_Night_CMG", night)):
            a = sds(f, "MODIS_MONTHLY_0.05DEG_CMG_LST", name).astype(np.float32)
            a[a == 0] = np.nan
            lst.append(a * 0.02)
    with np.errstate(all="ignore"):
        dT = np.nanmean(np.stack(day), 0) - np.nanmean(np.stack(night), 0)
        ati = (1 - albedo_sw) / dT
    ati[~(dT >= 2)] = np.nan
    del day, night

    # precipitación (GPM IMERG mensual, HDF5: precipitation [time, lon, lat] en mm/h, 0.1°)
    precip = np.full((3600, 7200), np.nan, np.float32)
    files = sorted(glob.glob(str(ROOT / "data/raw/earth/precip/3B-MO*.HDF5")))
    if files:
        import h5py
        tot = np.zeros((1800, 3600), np.float64)
        for f in files:
            with h5py.File(f, "r") as h:
                p = h["Grid/precipitation"][0].T.astype(np.float64)   # (lat, lon), sur arriba
            p[p < 0] = np.nan
            ym = Path(f).name.split(".")[4][:8]
            hours = calendar.monthrange(int(ym[:4]), int(ym[4:6]))[1] * 24
            tot += p * hours
        tot = tot[::-1]                                                 # norte arriba
        precip = np.repeat(np.repeat(tot, 2, 0), 2, 1).astype(np.float32)
        print(f"precipitación: {len(files)} meses de GPM IMERG")
    else:
        print("precipitación: sin archivos de GPM IMERG -> banda en NaN (sin dato)")

    prof = dict(driver="GTiff", height=3600, width=7200, count=4, dtype="float32",
                crs="EPSG:4326", transform=from_origin(-180, 90, 0.05, 0.05), nodata=np.nan,
                compress="deflate", tiled=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(OUT, "w", **prof) as ds:
        for i, (n, a) in enumerate([("snow_frac", snow_frac), ("albedo_sw", albedo_sw),
                                    ("ati", ati), ("precip_mm", precip)], 1):
            ds.write(a.astype(np.float32), i)
            ds.set_band_description(i, n)
            v = a[np.isfinite(a)]
            if v.size:
                print(f"  {n:<10} min {v.min():9.4f}  mediana {np.median(v):9.4f}  máx {v.max():9.4f}  "
                      f"con dato {100 * v.size / a.size:4.1f}%")
            else:
                print(f"  {n:<10} sin dato")
    print("->", OUT)


if __name__ == "__main__":
    main()
