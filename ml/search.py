#!/usr/bin/env python
"""Búsqueda de gemelos entre cuerpos (lo que usa Backend para POST /api/similar).

Requisito central: el usuario elige un punto en CUALQUIERA de los tres cuerpos y
recibe coincidencias en los otros dos (o en los que pida en `target_bodies`).

Escalas (la petición indica cuál; por defecto 1000):
  - 1000 m/px: global, los tres cuerpos, parches de 128 km;
  - 60 m/px: detalle, solo Luna ↔ Tierra y solo dentro de su cobertura
    (Luna al sur de 80° S; Tierra en la caja de México y alrededores).
    Fuera de cobertura no se inventa nada: se devuelve un aviso.

Métodos de ranking (por defecto "hybrid", la red de seguridad):
  - "hybrid":   la fórmula base preselecciona los N candidatos físicamente
                compatibles (relieve, pendientes, rugosidad) y la red los
                reordena por coseno de embeddings;
  - "net":      solo coseno de la red;
  - "baseline": solo la fórmula base;
  - "random":   control.

Solo depende de numpy, pandas y faiss (no de PyTorch).

  python -m ml.search --body moon --lat -89.76 --lon -176.19
  python -m ml.search --body moon --lat -85.93 --lon 3.34 --method baseline --k 5
"""
import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))
BODIES = ("earth", "moon", "mars")
RADIUS_KM = {"earth": 6371.0, "moon": 1737.4, "mars": 3389.5}
NOT_COMPARABLE = {"moon": ["gravity", "vacuum", "radiation"],
                  "mars": ["gravity", "atmosphere", "radiation"],
                  "earth": ["gravity", "atmosphere", "radiation"]}
PROFILES = {      # "materials" (minerales) quedó fuera de alcance; el albedo toma su lugar
    "rover": dict(terrain=0.45, operations=0.40, thermal=0.05, albedo=0.10),
    "isru": dict(terrain=0.20, operations=0.10, thermal=0.20, albedo=0.50),
    "habitat": dict(terrain=0.25, operations=0.30, thermal=0.25, albedo=0.20),
    "eva": dict(terrain=0.40, operations=0.15, thermal=0.05, albedo=0.40),
    "astrobiology": dict(terrain=0.25, operations=0.00, thermal=0.25, albedo=0.50),
}
THERMAL_SCALE_K = 50.0      # exp(-|ΔT| / 50 K), promediado en tmax, tmin y rango
ALBEDO_SCALE = 0.1          # exp(-|Δalbedo| / 0.1)
ATTR_COLS = ["tmax_k", "tmin_k", "trange_k", "albedo", "ice_distance_km"]


def _num(v):
    return None if v is None or not np.isfinite(v) else round(float(v), 3)


def thermal_score(fq, ft):
    """None ("sin dato") si falta la máxima o la mínima en cualquiera de los dos."""
    if not all(np.isfinite(f[c]) for f in (fq, ft) for c in ("tmax_k", "tmin_k")):
        return None
    d = [abs(fq[c] - ft[c]) for c in ("tmax_k", "tmin_k", "trange_k")]
    return float(np.mean(np.exp(-np.asarray(d) / THERMAL_SCALE_K)))


def albedo_score(fq, ft):
    if not (np.isfinite(fq["albedo"]) and np.isfinite(ft["albedo"])):
        return None
    return float(np.exp(-abs(fq["albedo"] - ft["albedo"]) / ALBEDO_SCALE))
OPS_FEATURES = ["slope_mean", "slope_frac_0_2", "slope_frac_2_5", "slope_frac_5_8",
                "slope_frac_8_15", "log_rough_mean"]


def gc_km(lat1, lon1, lat2, lon2, r):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    c = np.sin(p1) * np.sin(p2) + np.cos(p1) * np.cos(p2) * np.cos(np.radians(lon2 - lon1))
    return r * np.arccos(np.clip(c, -1, 1))


SCALES = (1000, 60)
DETAIL_BODIES = {"moon", "earth"}      # la escala de 60 m solo compara Luna y Tierra


@dataclass
class ScaleIndex:
    scale: int
    meta: pd.DataFrame
    emb: np.ndarray
    feat: np.ndarray
    ops: np.ndarray
    attrs: np.ndarray        # N x len(ATTR_COLS), NaN = sin dato

    @classmethod
    def load(cls, scale, tag="", art=None):
        art = Path(art or ROOT / "data/artifacts")
        meta = pd.read_parquet(art / f"meta_{scale}{tag}.parquet")
        emb = np.load(art / f"emb_{scale}{tag}.npy")
        feat = np.load(art / f"baseline_feat_{scale}.npy")
        names = json.loads((art / f"baseline_feat_{scale}.json").read_text())["names"]
        assert len(meta) == len(emb) == len(feat), "artefactos desalineados"
        ops = feat[:, [names.index(n) for n in OPS_FEATURES]]
        fp = art / f"features_{scale}{tag}.parquet"
        if fp.exists():
            f = pd.read_parquet(fp)
            assert (f.patch_id.values == meta.patch_id.values).all(), "features desalineadas"
            attrs = f[ATTR_COLS].to_numpy(np.float64)
        else:
            attrs = np.full((len(meta), len(ATTR_COLS)), np.nan)
        return cls(scale, meta, emb, feat, ops, attrs)


class Searcher:
    """Carga los índices disponibles una sola vez y responde consultas."""

    def __init__(self, tag="", art=None, scales=SCALES):
        self.idx = {}
        for s in scales:
            try:
                self.idx[s] = ScaleIndex.load(s, tag, art)
            except FileNotFoundError:
                pass
        assert self.idx, "no hay artefactos en data/artifacts"

    def query_patch(self, si, body, lat, lon):
        m = si.meta
        cand = np.flatnonzero(m.body.to_numpy() == body)
        if len(cand) == 0:
            raise ValueError(f"no hay parches de {body} a {si.scale} m")
        d = gc_km(lat, lon, m.lat.to_numpy()[cand], m.lon.to_numpy()[cand], RADIUS_KM[body])
        j = cand[np.argmin(d)]
        return j, float(d.min())

    def rank(self, si, q, target, k, method, n_candidates, rng=None):
        m = si.meta
        T = np.flatnonzero(m.body.to_numpy() == target)
        cos = si.emb[T] @ si.emb[q]
        dist = np.sqrt(((si.feat[T] - si.feat[q]) ** 2).sum(1))
        if method == "net":
            order = np.argsort(-cos)
        elif method == "baseline":
            order = np.argsort(dist)
        elif method == "hybrid":
            pre = np.argpartition(dist, min(n_candidates, len(T) - 1))[:n_candidates]
            order = pre[np.argsort(-cos[pre])]
        elif method == "random":
            order = (rng or np.random.default_rng(0)).permutation(len(T))
        else:
            raise ValueError(method)
        return T, order, cos, dist

    def search(self, body, lat, lon, target_bodies=None, k=10, profile="rover",
               method="hybrid", n_candidates=500, scale_m=1000):
        if scale_m not in SCALES:
            raise ValueError(f"scale_m debe ser uno de {SCALES}")
        targets = [t for t in (target_bodies or BODIES) if t != body]
        weights = PROFILES[profile]
        out = {"query": dict(body=body, lat=lat, lon=lon, profile=profile, scale_m=scale_m,
                             target_bodies=targets, method=method),
               "results": [], "warnings": []}
        for target in targets:
            scale = scale_m
            if scale == 60 and {body, target} != DETAIL_BODIES:
                out["warnings"].append(f"{body}->{target}: la escala de 60 m solo compara Luna y Tierra")
                continue
            if scale not in self.idx:
                out["warnings"].append(f"{body}->{target}: índice de {scale} m aún no disponible")
                continue
            si = self.idx[scale]
            if not (si.meta.body == target).any():
                out["warnings"].append(f"{body}->{target}: sin parches de {target} a {scale} m")
                continue
            q, dq = self.query_patch(si, body, lat, lon)
            window_km = 128 * scale / 1000
            if dq > window_km:
                out["warnings"].append(
                    f"{body}: el punto está a {dq:.0f} km del parche más cercano a {scale} m "
                    f"(fuera de la cobertura de esa escala)")
                if scale == 60:
                    continue
            fq = dict(zip(ATTR_COLS, si.attrs[q]))
            out["query"].setdefault("patches", {})[target] = dict(
                patch_id=si.meta.patch_id.iat[q], scale_m=scale, distance_km=round(dq, 2))
            out["query"]["attributes"] = {c: _num(v) for c, v in fq.items()}
            T, order, cos, _ = self.rank(si, q, target, k, method, n_candidates)
            for j in order[:k]:
                row = si.meta.iloc[T[j]]
                ops = float(1.0 / (1.0 + np.sqrt(((si.ops[T[j]] - si.ops[q]) ** 2).mean())))
                ft = dict(zip(ATTR_COLS, si.attrs[T[j]]))
                th, al = thermal_score(fq, ft), albedo_score(fq, ft)
                scores = dict(terrain=round(float(np.clip(cos[j], 0, 1)), 4),
                              operations=round(ops, 4),
                              thermal=None if th is None else round(th, 4),
                              albedo=None if al is None else round(al, 4))
                avail = {d: w for d, w in weights.items() if scores[d] is not None and w > 0}
                tot = sum(avail.values())
                score = sum(scores[d] * w for d, w in avail.items()) / tot if tot else 0.0
                used = {d: round(w / tot, 3) for d, w in avail.items()} if tot else {}
                out["results"].append(dict(
                    patch_id=row.patch_id, body=target, lat=round(float(row.lat), 4),
                    lon=round(float(row.lon), 4), region=row.region, scale_m=scale,
                    score=round(score, 4), scores=scores,
                    no_data=[d for d, v in scores.items() if v is None],
                    weights_used=used,
                    attributes={c: _num(v) for c, v in ft.items()},
                    not_comparable=NOT_COMPARABLE[target if body == "earth" else body]))
        return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--body", choices=BODIES, required=True)
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--targets", nargs="*", default=None)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--profile", default="rover", choices=list(PROFILES))
    ap.add_argument("--method", default="hybrid", choices=["hybrid", "net", "baseline", "random"])
    ap.add_argument("--scale", type=int, default=1000, choices=SCALES)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    s = Searcher(a.tag)
    print(json.dumps(s.search(a.body, a.lat, a.lon, a.targets, a.k, a.profile, a.method,
                              scale_m=a.scale),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
