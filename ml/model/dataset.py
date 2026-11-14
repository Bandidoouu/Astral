"""Carga de parches con lotes balanceados por cuerpo (CLAUDE.md, secciones 7-8).

Los parches viven en memmaps float16 (N x 128 x 128). Cada lote toma la misma
cantidad de parches de cada cuerpo, los lee del memmap (ordenados, para leer
el disco de forma secuencial) en un hilo de fondo y los sube a la GPU. Los 5
canales y las aumentaciones se calculan después en la GPU con
`ml.model.channels.make_views`.

Uso:
    loader = BalancedLoader(default_sources(60), per_body=64, device="cuda")
    for z, px, body in loader:         # z (B,1,128,128) en metros
        v1 = make_views(z, px); v2 = make_views(z, px)
"""
import os
import queue
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[2]))
BODY_ID = {"earth": 0, "moon": 1, "mars": 2}


@dataclass
class PatchSet:
    body: str
    patches: np.ndarray          # memmap N x H x W float16 (elevación relativa, m)
    meta: pd.DataFrame
    idx: np.ndarray              # índices usables (sin holdout si se pidió)
    scale_m: float

    @classmethod
    def load(cls, npy, parquet, exclude_holdout=True):
        patches = np.load(npy, mmap_mode="r")
        meta = pd.read_parquet(parquet)
        assert len(meta) == len(patches), (npy, len(meta), len(patches))
        keep = ~meta["holdout"].to_numpy() if exclude_holdout else np.ones(len(meta), bool)
        body = meta["body"].iloc[0]
        scale = float(meta["scale_m"].iloc[0])
        return cls(body, patches, meta, np.flatnonzero(keep), scale)


def default_sources(scale=60, exclude_holdout=True):
    """Conjuntos de ENTRENAMIENTO por escala. La Luna usa la versión con
    traslape (_train); la Tierra, la rejilla (sin los parches de Pinacate)."""
    d = ROOT / "data/patches"
    names = {60: {"earth": "earth_60", "moon": "moon_60_train"},
             500: {"earth": "earth_500", "mars": "mars_500"}}[scale]
    out = []
    for body, tag in names.items():
        npy, pq = d / f"patches_{tag}.npy", d / f"meta_{tag}.parquet"
        if npy.exists():
            out.append(PatchSet.load(npy, pq, exclude_holdout))
        else:
            print(f"[dataset] aviso: falta {npy.name}")
    return out


class BalancedLoader:
    """Iterador de lotes balanceados. Una "época" = total de parches / lote."""

    def __init__(self, sets, per_body=64, device="cuda", steps_per_epoch=None,
                 seed=0, prefetch=4):
        assert len(sets) > 0
        self.sets, self.per_body, self.device = sets, per_body, device
        total = sum(len(s.idx) for s in sets)
        self.steps = steps_per_epoch or max(1, total // (per_body * len(sets)))
        self.rng = np.random.default_rng(seed)
        self.prefetch = prefetch
        H, W = sets[0].patches.shape[1:]
        self.shape = (H, W)

    def __len__(self):
        return self.steps

    def _make_batch(self):
        zs, pxs, bodies = [], [], []
        for s in self.sets:
            ii = np.sort(self.rng.choice(s.idx, self.per_body, replace=len(s.idx) < self.per_body))
            zs.append(np.asarray(s.patches[ii]))
            pxs.append(np.full(self.per_body, s.scale_m, np.float32))
            bodies.append(np.full(self.per_body, BODY_ID[s.body], np.int64))
        z = torch.from_numpy(np.concatenate(zs)).unsqueeze(1).pin_memory()
        return z, torch.from_numpy(np.concatenate(pxs)), torch.from_numpy(np.concatenate(bodies))

    def __iter__(self):
        q = queue.Queue(maxsize=self.prefetch)
        stop = threading.Event()

        def worker():
            for _ in range(self.steps):
                if stop.is_set():
                    return
                q.put(self._make_batch())
            q.put(None)

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        try:
            while (item := q.get()) is not None:
                z, px, body = item
                yield (z.to(self.device, non_blocking=True),
                       px.to(self.device, non_blocking=True),
                       body.to(self.device, non_blocking=True))
        finally:
            stop.set()


def iter_all(pset, batch=512, device="cuda"):
    """Recorre un conjunto completo en orden (para embeber). Incluye holdout."""
    n = len(pset.patches)
    for a in range(0, n, batch):
        z = torch.from_numpy(np.asarray(pset.patches[a:a + batch])).unsqueeze(1)
        px = torch.full((len(z),), pset.scale_m)
        yield a, z.to(device), px.to(device)
