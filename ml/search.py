#!/usr/bin/env python
"""Búsqueda de gemelos entre cuerpos (lo que usa Backend para POST /api/similar).

Requisito central: el usuario elige un punto en CUALQUIERA de los tres cuerpos y
recibe coincidencias en los otros dos (o en los que pida en `target_bodies`).

Escalas (la petición indica cuál; por defecto 1000):
  - 1000 m/px: global, los tres cuerpos, parches de 128 km;
  - 60 m/px: detalle, solo Luna ↔ Tierra y solo dentro de su cobertura
    (Luna al sur de 80° S; Tierra en la caja de México y alrededores).
    Fuera de cobertura no se inventa nada: se devuelve un aviso.

Métodos de ranking de la dimensión terreno (por defecto "rrf"):
  - "rrf":      Reciprocal Rank Fusion de la fórmula base y la red, k = 60 fijo
                (sin ajustar pesos): 1/(60 + lugar en la red) + 1/(60 + lugar en
                la fórmula);
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
# lo que nunca se puede comparar con datos orbitales (se lista en cada resultado)
NOT_COMPARABLE = {"moon": ["dust_and_wind", "subsurface", "gravity", "vacuum", "radiation"],
                  "mars": ["dust_and_wind", "subsurface", "gravity", "atmosphere", "radiation"],
                  "earth": ["dust_and_wind", "subsurface", "gravity", "atmosphere", "radiation"]}
DIMENSIONS = ["terrain", "operations", "thermal", "albedo", "ice", "soil", "aridity"]
# Ningún perfil le da más de 0.3 al terreno. "general" (por defecto): pesos iguales.
PROFILES = {
    "general": {d: 1 / len(DIMENSIONS) for d in DIMENSIONS},
    "rover": dict(terrain=0.30, operations=0.30, thermal=0.05, albedo=0.05, ice=0.05, soil=0.15, aridity=0.10),
    "isru": dict(terrain=0.10, operations=0.10, thermal=0.10, albedo=0.15, ice=0.35, soil=0.15, aridity=0.05),
    "habitat": dict(terrain=0.15, operations=0.25, thermal=0.25, albedo=0.05, ice=0.15, soil=0.10, aridity=0.05),
    "eva": dict(terrain=0.30, operations=0.20, thermal=0.05, albedo=0.15, ice=0.05, soil=0.20, aridity=0.05),
    "astrobiology": dict(terrain=0.10, operations=0.00, thermal=0.15, albedo=0.10, ice=0.30, soil=0.10, aridity=0.25),
}
assert all(abs(sum(w.values()) - 1) < 1e-9 and w["terrain"] <= 0.3 for w in PROFILES.values())
ICE_SCALE = 0.2             # exp(-|Δ fracción de hielo| / 0.2)
PRECIP_SCALE_MM = 250.0     # exp(-|Δ precipitación anual| / 250 mm)
THERMAL_SCALE_K = 50.0      # exp(-|ΔT| / 50 K), promediado en tmax, tmin y rango
ALBEDO_SCALE = 0.1          # exp(-|Δalbedo| / 0.1)
ATTR_COLS = ["tmax_k", "tmin_k", "trange_k", "albedo", "ice_distance_km",
             "ice_frac", "soil_raw", "soil_pct", "precip_mm", "h2o_wt_pct"]


def _num(v):
    return None if v is None or not np.isfinite(v) else round(float(v), 3)


def thermal_score(fq, ft):
    """None ("sin dato") si falta la máxima o la mínima en cualquiera de los dos."""
    if not all(np.isfinite(f[c]) for f in (fq, ft) for c in ("tmax_k", "tmin_k")):
        return None
    d = [abs(fq[c] - ft[c]) for c in ("tmax_k", "tmin_k", "trange_k")]
    return float(np.mean(np.exp(-np.asarray(d) / THERMAL_SCALE_K)))


def _both(fq, ft, c):
    return np.isfinite(fq[c]) and np.isfinite(ft[c])


def ice_score(fq, ft):
    return float(np.exp(-abs(fq["ice_frac"] - ft["ice_frac"]) / ICE_SCALE)) if _both(fq, ft, "ice_frac") else None


def soil_score(fq, ft):
    """Percentil de rocosidad dentro de cada cuerpo (ATI en la Tierra, rocas de Diviner
    en la Luna, inercia térmica de TES en Marte)."""
    return float(1 - abs(fq["soil_pct"] - ft["soil_pct"])) if _both(fq, ft, "soil_pct") else None


def aridity_score(fq, ft):
    if not _both(fq, ft, "precip_mm"):
        return None
    return float(np.exp(-abs(fq["precip_mm"] - ft["precip_mm"]) / PRECIP_SCALE_MM))


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
SCALE_MODES = ("same_size", "gravity_scaled")
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
        bt = tag if (art / f"baseline_feat_{scale}{tag}.npy").exists() else ""
        feat = np.load(art / f"baseline_feat_{scale}{bt}.npy")
        names = json.loads((art / f"baseline_feat_{scale}{bt}.json").read_text())["names"]
        assert len(meta) == len(emb) == len(feat), "artefactos desalineados"
        ops = feat[:, [names.index(n) for n in OPS_FEATURES]]
        fp = art / f"features_{scale}{tag}.parquet"
        if fp.exists():
            f = pd.read_parquet(fp)
            assert (f.patch_id.values == meta.patch_id.values).all(), "features desalineadas"
            attrs = f.reindex(columns=ATTR_COLS).to_numpy(np.float64)   # columnas nuevas = NaN
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
        try:      # scale_mode = gravity_scaled: Tierra 1 km, Luna x6, Marte x2.6 (mismo modelo)
            self.gidx = ScaleIndex.load(1000, tag + "_gravity", art)
        except FileNotFoundError:
            self.gidx = None
        lcp = Path(art or ROOT / "data/artifacts") / "earth_landcover_005deg.tif"
        self.landcover = None
        if lcp.exists():
            from ml.features.earth_landcover import LandCover
            self.landcover = LandCover(lcp)

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
        sel = m.body.to_numpy() == target
        if target == "earth" and "promising" in m:
            sel &= m.promising.to_numpy(bool)       # solo zonas prometedoras (MCD12C1)
        T = np.flatnonzero(sel)
        cos = si.emb[T] @ si.emb[q]
        dist = np.sqrt(((si.feat[T] - si.feat[q]) ** 2).sum(1))
        if method == "net":
            order = np.argsort(-cos)
        elif method == "baseline":
            order = np.argsort(dist)
        elif method == "hybrid":
            pre = np.argpartition(dist, min(n_candidates, len(T) - 1))[:n_candidates]
            order = pre[np.argsort(-cos[pre])]
        elif method == "rrf":
            r_net = np.empty(len(T), np.int64); r_net[np.argsort(-cos)] = np.arange(1, len(T) + 1)
            r_base = np.empty(len(T), np.int64); r_base[np.argsort(dist)] = np.arange(1, len(T) + 1)
            order = np.argsort(-(1.0 / (60 + r_net) + 1.0 / (60 + r_base)))
        elif method == "random":
            order = (rng or np.random.default_rng(0)).permutation(len(T))
        else:
            raise ValueError(method)
        return T, order, cos, dist

    def search(self, body, lat, lon, target_bodies=None, k=10, profile="general",
               method="rrf", n_candidates=500, scale_m=1000, scale_mode="same_size"):
        if scale_m not in SCALES:
            raise ValueError(f"scale_m debe ser uno de {SCALES}")
        if scale_mode not in SCALE_MODES:
            raise ValueError(f"scale_mode debe ser uno de {SCALE_MODES}")
        targets = [t for t in (target_bodies or BODIES) if t != body]
        weights = PROFILES[profile]
        out = {"query": dict(body=body, lat=lat, lon=lon, profile=profile, scale_m=scale_m,
                             scale_mode=scale_mode, target_bodies=targets, method=method),
               "results": [], "warnings": []}
        gravity = scale_mode == "gravity_scaled"
        if gravity and (scale_m != 1000 or self.gidx is None):
            out["warnings"].append("gravity_scaled is only available at scale_m = 1000"
                                   if scale_m != 1000 else "gravity_scaled index not available; using same_size")
            out["query"]["scale_mode"] = "same_size"
            gravity = False
        if body == "earth" and self.landcover is not None:
            lc = self.landcover.at(lat, lon)
            out["query"]["land_cover"] = lc
            if not lc["promising"]:
                out["warnings"].append(
                    f"earth: the clicked point is {lc['name']} (MODIS land cover class "
                    f"{lc['code']}), outside the promising analog zones; search continues")
        for target in targets:
            scale = scale_m
            if scale == 60 and {body, target} != DETAIL_BODIES:
                out["warnings"].append(f"{body}->{target}: la escala de 60 m solo compara Luna y Tierra")
                continue
            if scale not in self.idx:
                out["warnings"].append(f"{body}->{target}: índice de {scale} m aún no disponible")
                continue
            si = self.gidx if gravity else self.idx[scale]
            if not (si.meta.body == target).any():
                out["warnings"].append(f"{body}->{target}: sin parches de {target} a {scale} m")
                continue
            q, dq = self.query_patch(si, body, lat, lon)
            window_km = 128 * float(si.meta.scale_m.iat[q]) / 1000
            if dq > window_km:
                out["warnings"].append(
                    f"{body}: el punto está a {dq:.0f} km del parche más cercano a {scale} m "
                    f"(fuera de la cobertura de esa escala)")
                if scale == 60:
                    continue
            fq = dict(zip(ATTR_COLS, si.attrs[q]))
            out["query"].setdefault("patches", {})[target] = dict(
                patch_id=si.meta.patch_id.iat[q], scale_m=scale, distance_km=round(dq, 2),
                window_km=round(window_km, 1))
            out["query"]["attributes"] = {c: _num(v) for c, v in fq.items()}
            T, order, cos, _ = self.rank(si, q, target, k, method, n_candidates)
            for j in order[:k]:
                row = si.meta.iloc[T[j]]
                ops = float(1.0 / (1.0 + np.sqrt(((si.ops[T[j]] - si.ops[q]) ** 2).mean())))
                ft = dict(zip(ATTR_COLS, si.attrs[T[j]]))
                raw = dict(terrain=float(np.clip(cos[j], 0, 1)), operations=ops,
                           thermal=thermal_score(fq, ft), albedo=albedo_score(fq, ft),
                           ice=ice_score(fq, ft), soil=soil_score(fq, ft),
                           aridity=aridity_score(fq, ft))
                scores = {d: None if raw[d] is None else round(raw[d], 4) for d in DIMENSIONS}
                avail = {d: w for d, w in weights.items() if scores[d] is not None and w > 0}
                tot = sum(avail.values())
                score = sum(scores[d] * w for d, w in avail.items()) / tot if tot else 0.0
                used = {d: round(w / tot, 3) for d, w in avail.items()} if tot else {}
                out["results"].append(dict(
                    patch_id=row.patch_id, body=target, lat=round(float(row.lat), 4),
                    lon=round(float(row.lon), 4), region=row.region, scale_m=scale,
                    land_cover=(row.lc_name if target == "earth" and "lc_name" in row else None),
                    window_km=round(128 * float(row.scale_m) / 1000, 1),
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
    ap.add_argument("--profile", default="general", choices=list(PROFILES))
    ap.add_argument("--method", default="rrf", choices=["rrf", "hybrid", "net", "baseline", "random"])
    ap.add_argument("--scale", type=int, default=1000, choices=SCALES)
    ap.add_argument("--scale-mode", default="same_size", choices=SCALE_MODES)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    s = Searcher(a.tag)
    print(json.dumps(s.search(a.body, a.lat, a.lon, a.targets, a.k, a.profile, a.method,
                              scale_m=a.scale, scale_mode=a.scale_mode),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
