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
from ml.model.net import Encoder

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))
INDEX_SETS = {60: ["earth_60", "moon_60"], 500: ["earth_500", "mars_500"]}


def load_encoder(path, device="cuda"):
    enc = Encoder(pretrained=False)
    enc.load_state_dict(torch.load(path, map_location="cpu"))
    return enc.to(device).eval().to(memory_format=torch.channels_last)


@torch.no_grad()
def embed_set(enc, pset, batch=512, tta=4, device="cuda"):
    out = np.zeros((len(pset.patches), 128), np.float32)
    for a, z, px in iter_all(pset, batch, device):
        acc = 0
        for k in range(tta):
            x = make_channels(torch.rot90(z.float(), k, dims=(2, 3)), px)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                acc = acc + enc(x.contiguous(memory_format=torch.channels_last)).float()
        out[a:a + len(z)] = torch.nn.functional.normalize(acc, dim=1).cpu().numpy()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--encoder", type=Path, required=True)
    ap.add_argument("--scale", type=int, default=60)
    ap.add_argument("--tag", default="", help="sufijo de salida, p. ej. _abl")
    ap.add_argument("--tta", type=int, default=4)
    ap.add_argument("--batch", type=int, default=512)
    a = ap.parse_args()

    enc = load_encoder(a.encoder)
    d = ROOT / "data/patches"
    embs, metas = [], []
    for name in INDEX_SETS[a.scale]:
        pset = PatchSet.load(d / f"patches_{name}.npy", d / f"meta_{name}.parquet",
                             exclude_holdout=False)
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
