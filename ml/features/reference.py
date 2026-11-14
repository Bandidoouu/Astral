"""Distribuciones de referencia por cuerpo y vector tabular de v3.

Percentil "dentro de su propio cuerpo": un valor se compara contra la distribución de
esa variable en TODA la rejilla global del cuerpo (ponderada por área con cos(lat)),
no contra el conjunto de parches que toque. Así el mismo valor da el mismo
percentil en el índice, en el entrenamiento, en la evaluación y en ambas escalas.

Vector tabular de v3 (14 números): 7 percentiles + 7 marcas de "sin dato".
  t_max, t_min, t_range, albedo, ice, soil  -> percentil en su cuerpo
  aridity -> Tierra: 1 - percentil de la precipitación; Luna y Marte: 1.0 (aridez
             total, por definición física)
Sin dato: percentil 0 y marca 1 (la red ve explícitamente que falta).
"""
import os
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[2]))
F = ROOT / "data/features"
CACHE = F / "reference"
TAB_VARS = ["tmax_k", "tmin_k", "trange_k", "albedo", "ice_frac", "soil_raw", "aridity"]
N_TAB = 2 * len(TAB_VARS)

# (archivo, banda, escala) de la rejilla global de cada variable
SOURCES = {
    "earth": {"tmax_k": (F / "earth_climate_005deg.tif", 1, 1.0),
              "tmin_k": (F / "earth_climate_005deg.tif", 2, 1.0),
              "trange_k": (F / "earth_climate_005deg.tif", 3, 1.0),
              "albedo": (F / "earth_climate_005deg.tif", 4, 1.0),
              "ice_frac": (F / "earth_extra_005deg.tif", 1, 1.0),
              "soil_raw": (F / "earth_extra_005deg.tif", 3, 1.0),
              "precip_mm": (F / "earth_extra_005deg.tif", 4, 1.0)},
    "moon": {"tmax_k": (F / "moon_thermal_global_05deg.tif", 1, 1.0),
             "tmin_k": (F / "moon_thermal_global_05deg.tif", 2, 1.0),
             "trange_k": (F / "moon_thermal_global_05deg.tif", 3, 1.0),
             "albedo": (ROOT / "data/raw/moon/lola_albedo/ldam_10_float.lbl", 1, 1.0),
             "ice_frac": (F / "moon_thermal_global_05deg.tif", 5, 1.0),
             "soil_raw": (ROOT / "data/raw/moon/diviner_ra/dgdr_ra_avg_cyl_032_img.lbl", 1, 0.001)},
}
ARID_BY_DEFINITION = {"moon": 1.0, "mars": 1.0}


def _reference(body, var, n=200_000, seed=0):
    """Muestra ordenada de la variable en la rejilla global, ponderada por área."""
    cache = CACHE / f"{body}_{var}.npy"
    if cache.exists():
        return np.load(cache)
    path, band, scale = SOURCES[body][var]
    with rasterio.open(path) as ds:
        a = ds.read(band).astype(np.float64)
        nod = ds.nodata
        H = ds.height
    if nod is not None and np.isfinite(nod):
        a[a == nod] = np.nan
    a[a < -1e30] = np.nan
    a *= scale
    lat = np.linspace(90, -90, H, endpoint=False) - 90 / H     # equirectangular global
    w = np.repeat(np.cos(np.radians(lat))[:, None], a.shape[1], 1)
    ok = np.isfinite(a)
    if not ok.any():
        ref = np.array([])
    else:
        vals, wts = a[ok], w[ok]
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(vals), min(n, len(vals)), replace=True, p=wts / wts.sum())
        ref = np.sort(vals[idx])
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(cache, ref)
    return ref


def percentile(body, var, values):
    """Percentil (0-1) de cada valor en la distribución global de su cuerpo; NaN si falta."""
    values = np.asarray(values, np.float64)
    out = np.full(values.shape, np.nan)
    if body not in SOURCES or var not in SOURCES[body]:
        return out
    ref = _reference(body, var)
    if ref.size == 0:
        return out
    ok = np.isfinite(values)
    lo = np.searchsorted(ref, values[ok], "left")
    hi = np.searchsorted(ref, values[ok], "right")
    out[ok] = (lo + hi) / 2 / ref.size
    return out


def dims_available_everywhere(tabs, min_frac=0.5):
    """Regla: una dimensión entra a la red solo si TODOS los cuerpos la tienen en al
    menos min_frac de sus parches. Si no, su patrón de "sin dato" delataría el planeta
    sin decir nada del lugar (p. ej. suelo en el polo lunar, aridez sin GPM)."""
    n = len(TAB_VARS)
    return np.array([min(1 - t[:, n + j].mean() for t in tabs) >= min_frac for j in range(n)])


def mask_dims(tab, used):
    """Apaga las dimensiones no usadas para TODOS por igual (percentil 0, marca 1)."""
    n = len(TAB_VARS)
    tab = tab.copy()
    off = ~np.asarray(used, bool)
    tab[:, :n][:, off] = 0.0
    tab[:, n:][:, off] = 1.0
    return tab


def tab_vector(body, feats):
    """feats: DataFrame con las columnas de patch_features -> array (N, 14) float32."""
    n = len(feats)
    pct = np.full((n, len(TAB_VARS)), np.nan)
    for j, v in enumerate(TAB_VARS):
        if v == "aridity":
            if body in ARID_BY_DEFINITION:
                pct[:, j] = ARID_BY_DEFINITION[body]
            else:
                pct[:, j] = 1 - percentile(body, "precip_mm", feats["precip_mm"].to_numpy())
        else:
            pct[:, j] = percentile(body, v, feats[v].to_numpy())
    miss = ~np.isfinite(pct)
    return np.concatenate([np.nan_to_num(pct, nan=0.0), miss.astype(np.float64)], 1).astype(np.float32)
