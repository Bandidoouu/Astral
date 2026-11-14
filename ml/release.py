#!/usr/bin/env python
"""Publica un paquete para Backend en data/artifacts/release/<version>/.

Copia exactamente lo que lee ml.search.Searcher (por escala) y la capa de aptitud,
con un manifest.json (tamaños, SHA-256, versión del encoder, fecha) y un README.

  python -m ml.release --version v2-60m --encoder encoder_v2.pt --scales 60
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
from pathlib import Path

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))
ART = ROOT / "data/artifacts"
PER_SCALE = ["meta_{s}.parquet", "emb_{s}.npy", "index_{s}.faiss", "baseline_feat_{s}.npy",
             "baseline_feat_{s}.json", "features_{s}.parquet"]
SUIT = ["suitability/moon_south_{k}.tif", "suitability/moon_south_{k}.png"]
SUIT_K = ["landing", "rover", "ice", "temperature", "total"]
SUIT_EXTRA = ["suitability/suitability_moon.json", "suitability/recommended_zones.json",
              "suitability/suitability_candidates.png", "earth_landcover_005deg.tif",
              "suitability/suitability_mars.json", "suitability/suitability_mars_candidates.png",
              "suitability/mars_h2o_wt_pct.tif"]
SUIT_MARS = ["suitability/mars_{k}.tif", "suitability/mars_{k}.png"]
SUIT_MARS_K = ["landing", "rover", "elevation", "hydrogen", "total"]
GRAVITY = ["meta_1000_gravity.parquet", "emb_1000_gravity.npy", "index_1000_gravity.faiss",
           "baseline_feat_1000_gravity.npy", "baseline_feat_1000_gravity.json",
           "features_1000_gravity.parquet"]

README = """# Paquete ASTRAL para Backend: {version}

Generado: {date}. Encoder: `{encoder}`. Escalas: {scales}.

## Cómo usarlo

1. Copia esta carpeta a la máquina del backend y apunta `ASTRAL_ARTIFACTS` (o
   `Searcher(art=...)`) a ella.
2. `from ml.search import Searcher; s = Searcher(art="<esta carpeta>")`
3. `s.search(body, lat, lon, target_bodies, k, profile, method="rrf", scale_m=...)`
   devuelve el JSON del contrato (`docs/contratos.md` §3).

## Qué trae

| Archivo | Para qué |
| --- | --- |
| `meta_{{s}}.parquet` | Metadatos de cada parche (mismo orden que los embeddings) |
| `emb_{{s}}.npy`, `index_{{s}}.faiss` | Embeddings de forma (norma 1) e índice FAISS |
| `baseline_feat_{{s}}.npy/.json` | Fórmula base (para la fusión RRF y `operations`) |
| `features_{{s}}.parquet` | Temperatura, albedo, hielo, suelo y aridez por parche (`NaN` = sin dato) |
| `earth_landcover_005deg.tif` | Máscara de zonas prometedoras (MODIS MCD12C1): clase IGBP y % prometedor; la búsqueda la usa para el aviso del clic |
| `*_1000_gravity.*` | Índice para `scale_mode = gravity_scaled` (Luna con ventanas de 774 km, Marte de 338 km) |
| `suitability/` | Capas de aptitud de la Luna (polo sur) y Marte (global 0.25°) (GeoTIFF + PNG), reglas y pesos, candidatos de la NASA, `recommended_zones.json` |

`manifest.json` lista cada archivo con su tamaño y SHA-256 para verificar la copia.

## Límites que hay que mostrar

- Sin dato = `null`; nunca se rellena.
- La capa de aptitud es una sugerencia: faltan iluminación y visibilidad de la Tierra.
- {notes}
"""


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--encoder", required=True, help="nombre del encoder en data/artifacts/")
    ap.add_argument("--scales", type=int, nargs="+", default=[60])
    ap.add_argument("--extra-encoders", nargs="*", default=[], help="otros encoders (p. ej. el de 60 m)")
    ap.add_argument("--notes", default="Precipitación de la Tierra pendiente (aridez = sin dato).")
    a = ap.parse_args()
    out = ART / "release" / a.version
    out.mkdir(parents=True, exist_ok=True)
    files = [f.format(s=s) for s in a.scales for f in PER_SCALE]
    files += [f.format(k=k) for k in SUIT_K for f in SUIT] + SUIT_EXTRA + [a.encoder]
    files += [f.format(k=k) for k in SUIT_MARS_K for f in SUIT_MARS]
    if 1000 in a.scales:
        files += GRAVITY
    files += a.extra_encoders
    manifest = dict(version=a.version, encoder=a.encoder, scales=a.scales,
                    created=dt.datetime.now().isoformat(timespec="seconds"), files=[])
    missing = []
    for f in files:
        src = ART / f
        if not src.exists():
            missing.append(f)
            continue
        dst = out / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        manifest["files"].append(dict(path=f, bytes=dst.stat().st_size, sha256=sha256(dst)))
    manifest["missing"] = missing
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (out / "README.md").write_text(README.format(version=a.version, date=manifest["created"],
                                                 encoder=a.encoder, scales=a.scales, notes=a.notes))
    tot = sum(x["bytes"] for x in manifest["files"]) / 1e6
    print(f"-> {out}  ({len(manifest['files'])} archivos, {tot:.0f} MB; faltan: {missing or 'ninguno'})")


if __name__ == "__main__":
    main()
