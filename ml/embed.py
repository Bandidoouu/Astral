#!/usr/bin/env python
"""Embeddings + índice FAISS + metadatos para Backend (docs/contratos.md §1-2).

Embebe los parches del ÍNDICE (rejilla sin traslape): Tierra completa, incluidos
los de El Pinacate (holdout: fuera del entrenamiento, dentro del índice), y Luna
al sur de 80° S. Cada embedding es el promedio de 4 rotaciones de 90° (TTA),
renormalizado a norma 1, para que no dependa de la orientación.

Salidas en data/artifacts/:
  emb_{scale}{tag}.npy      float32 N x 128, norma 1, mismo orden que meta
  meta_{scale}{tag}.parquet metadatos de todos los cuerpos (Tierra primero)
  index_{scale}{tag}.faiss  IndexFlatIP

  python -m ml.embed --encoder data/artifacts/encoder_v1.pt
  python -m ml.embed --encoder data/artifacts/checkpoints/abl60/encoder_ep25.pt --tag _abl
"""
import argparse
import os
import time
from pathlib import Path

import faiss
import numpy as np
import pandas as pd
import torch

from ml.model.channels import make_channels
from ml.model.dataset import PatchSet, iter_all
from ml.model.net import Encoder, MultimodalEncoder, load_any_encoder

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))
# earth_1000_val: parches centrados en los análogos conocidos (Mauna Loa, Scablands, ...),
# que el índice global no trae (p. ej. Hawái tiene demasiado océano para la rejilla)
INDEX_SETS = {60: ["earth_60", "moon_60"],
              1000: ["earth_1000", "earth_1000_val", "moon_1000", "mars_1000"]}
# scale_mode = gravity_scaled: ventanas de la Luna 6x y de Marte 2.6x (mismo modelo, sin reentrenar)
GRAVITY_SETS = ["earth_1000", "earth_1000_val", "moon_6050", "mars_2640"]


def load_encoder(path, device="cuda"):
    """Carga v1/v2 (solo forma) o v3 (multimodal) según los pesos."""
    enc = load_any_encoder(torch.load(path, map_location="cpu"))
    return enc.to(device).eval().to(memory_format=torch.channels_last)


def is_multimodal(enc):
    return isinstance(enc, MultimodalEncoder)


def tab_used_for(encoder_path):
    """Dimensiones que usó v3 al entrenar: <encoder>.tab_used.json o tab_used.json en
    la carpeta del checkpoint."""
    import json
    p = Path(encoder_path)
    for c in (p.with_suffix(".tab_used.json"), p.parent / "tab_used.json"):
        if c.exists():
            return json.loads(c.read_text())
    raise FileNotFoundError(f"no encuentro tab_used.json para {p}")


def prepare_tab(pset, encoder_path):
    from ml.features.reference import mask_dims
    pset.attach_tab()
    pset.tab = mask_dims(pset.tab, tab_used_for(encoder_path))
    return pset


@torch.no_grad()
def embed_set(enc, pset, batch=512, tta=4, device="cuda"):
    out = np.zeros((len(pset.patches), 128), np.float32)
    mm = is_multimodal(enc)
    assert not mm or pset.tab is not None, f"v3 necesita el vector tabular de {pset.name}"
    for a, z, px, *rest in iter_all(pset, batch, device):
        tab = rest[0] if rest else None
        acc = 0
        for k in range(tta):
            x = make_channels(torch.rot90(z.float(), k, dims=(2, 3)), px)
            x = x.contiguous(memory_format=torch.channels_last)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                acc = acc + (enc(x, tab) if mm else enc(x)).float()
        out[a:a + len(z)] = torch.nn.functional.normalize(acc, dim=1).cpu().numpy()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--encoder", type=Path, required=True)
    ap.add_argument("--scale", type=int, default=60)
    ap.add_argument("--tag", default="", help="sufijo de salida, p. ej. _abl")
    ap.add_argument("--tta", type=int, default=4)
    ap.add_argument("--gravity", action="store_true", help="índice gravity_scaled (usar con --tag _gravity)")
    ap.add_argument("--batch", type=int, default=512)
    a = ap.parse_args()

    enc = load_encoder(a.encoder)
    d = ROOT / "data/patches"
    embs, metas = [], []
    for name in (GRAVITY_SETS if a.gravity else INDEX_SETS[a.scale]):
        pset = PatchSet.load(d / f"patches_{name}.npy", d / f"meta_{name}.parquet",
                             exclude_holdout=False)
        if is_multimodal(enc):
            prepare_tab(pset, a.encoder)
        t0 = time.time()
        e = embed_set(enc, pset, a.batch, a.tta)
        print(f"{name}: {len(e)} parches ({int(pset.meta.holdout.sum())} holdout) "
              f"en {time.time() - t0:.0f}s")
        embs.append(e)
        metas.append(pset.meta)

    emb = np.concatenate(embs)
    meta = pd.concat(metas, ignore_index=True)
    if "country" not in meta:
        meta["country"] = None
    meta.loc[meta.body != "earth", "country"] = None
    if "promising" in meta:          # máscara de zonas prometedoras: solo filtra la Tierra
        meta["promising"] = meta.promising.where(meta.body == "earth", True).astype(bool)
    assert np.allclose(np.linalg.norm(emb, axis=1), 1, atol=1e-3)
    assert meta.patch_id.is_unique

    out = ROOT / "data/artifacts"
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / f"emb_{a.scale}{a.tag}.npy", emb)
    meta.to_parquet(out / f"meta_{a.scale}{a.tag}.parquet", index=False)
    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)
    faiss.write_index(index, str(out / f"index_{a.scale}{a.tag}.faiss"))

    std = emb.std(0).mean()
    print(f"-> emb {emb.shape}, std por dimensión {std:.4f}, "
          f"índice {index.ntotal} vectores; cuerpos {meta.body.value_counts().to_dict()}")


if __name__ == "__main__":
    main()
