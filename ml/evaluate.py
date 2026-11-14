#!/usr/bin/env python
"""Evaluación principal: ¿en qué lugar queda el análogo terrestre conocido?
(CLAUDE.md de ml/, §12)

Para cada consulta lunar se ordenan TODOS los parches terrestres candidatos
(rejilla de México y alrededores, más Arizona y Death Valley) y se mide el
lugar del mejor parche del análogo conocido. Percentil = lugar / candidatos x 100
(menor es mejor). Se reporta la mediana, el rango intercuartil y cuántas consultas
tienen el análogo en el top 50.

Pruebas (a 60 m/px, ventanas de 7.68 km):
  blind_pinacate: domos de los Montes Marius -> El Pinacate (holdout: la red NUNCA
                  lo vio en entrenamiento).
  volcanic:       Montes Marius -> El Pinacate o campo volcánico de San Francisco (AZ).
  craters:        cráteres simples de mares lunares (Tranquillitatis, Imbrium;
                  1-2.5 km) -> Meteor Crater (1.2 km).
Métodos: fórmula base sola, red sola, filtro + red (hybrid), fusión RRF de la
fórmula y la red (k = 60 fijo, sin ajustar pesos) y azar.

  python -m ml.evaluate --encoder data/artifacts/encoder_v2.pt --tag v2
"""
import argparse
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
import torch
from pyproj import Transformer

from ml.baseline import features
from ml.embed import embed_set, load_encoder
from ml.model.dataset import PatchSet
from ml.search import gc_km, RADIUS_KM

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))
P = ROOT / "data/patches"
MARIUS_CENTER, MARIUS_RADIUS_KM = (13.4, -55.6), 60.0
SF_FIELD = dict(lat_min=35.15, lon_max=-111.25)     # campo volcánico de San Francisco
METEOR = (35.0275, -111.0225)
METHODS = ["baseline", "net", "hybrid", "rrf", "random"]
LABELS = {"baseline": "Formula only (20 terrain stats)", "net": "Network only",
          "hybrid": "Formula filter + network", "rrf": "Rank fusion (formula + network)",
          "random": "Random"}
COLORS = {"net": "#2a78d6", "hybrid": "#eb6834", "baseline": "#1baf7a", "rrf": "#eda100",
          "random": "#8a8985"}
MARKERS = {"net": "o", "hybrid": "D", "baseline": "s", "rrf": "^", "random": "x"}
RRF_K = 60


def rrf_scores(cos, dist, k=RRF_K):
    """Reciprocal Rank Fusion: 1/(k + lugar en la red) + 1/(k + lugar en la fórmula)."""
    r_net = np.empty(len(cos), np.int64); r_net[np.argsort(-cos)] = np.arange(1, len(cos) + 1)
    r_base = np.empty(len(dist), np.int64); r_base[np.argsort(dist)] = np.arange(1, len(dist) + 1)
    return 1.0 / (k + r_net) + 1.0 / (k + r_base)


def load_set(name, exclude_holdout=False):
    return PatchSet.load(P / f"patches_{name}.npy", P / f"meta_{name}.parquet", exclude_holdout)


def meteor_centered():
    """Parche de 128x128 centrado en Meteor Crater, cortado de arizona_60m.tif."""
    with rasterio.open(ROOT / "data/raw/earth/regions/arizona_60m.tif") as ds:
        x, y = Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True).transform(METEOR[1], METEOR[0])
        r, c = ds.index(x, y)
        z = ds.read(1, window=((r - 64, r + 64), (c - 64, c + 64))).astype(np.float64)
    meta = pd.DataFrame([dict(patch_id="earth-60-399999", body="earth", scale_m=60, lat=METEOR[0],
                              lon=METEOR[1], region="Meteor Crater, Arizona, USA", holdout=False,
                              elev_mean_m=z.mean(), elev_min_m=z.min(), elev_max_m=z.max())])
    arr = (z - z.mean())[None].astype(np.float16)
    return PatchSet("earth", arr, meta, np.arange(1), 60.0, "meteor_centered")


@torch.no_grad()
def base_feats(pset, mu, sd):
    out = []
    for a in range(0, len(pset.patches), 1024):
        z = torch.from_numpy(np.array(pset.patches[a:a + 1024])).unsqueeze(1).float().cuda()
        out.append(features(z, torch.full((len(z),), pset.scale_m, device="cuda")).cpu().numpy())
    return (np.concatenate(out) - mu) / sd


def ranks_for(q_emb, q_feat, C_emb, C_feat, target_mask, n_cand, rng):
    """Lugar (1 = primero) del mejor parche objetivo, para cada método."""
    N = len(C_emb)
    cos = C_emb @ q_emb
    dist = np.sqrt(((C_feat - q_feat) ** 2).sum(1))
    tgt = np.flatnonzero(target_mask)
    out = {}
    out["net"] = 1 + int(min((cos > cos[t]).sum() for t in tgt))
    out["baseline"] = 1 + int(min((dist < dist[t]).sum() for t in tgt))
    pre = np.zeros(N, bool)
    pre[np.argpartition(dist, n_cand)[:n_cand]] = True
    best = N
    for t in tgt:
        if pre[t]:
            r = 1 + (cos[pre] > cos[t]).sum()
        else:
            r = n_cand + 1 + (dist[~pre] < dist[t]).sum()
        best = min(best, int(r))
    out["hybrid"] = best
    fused = rrf_scores(cos, dist)
    out["rrf"] = 1 + int(min((fused > fused[t]).sum() for t in tgt))
    perm_best = [1 + rng.permutation(N)[tgt].min() for _ in range(20)]
    out["random"] = int(np.median(perm_best))
    return out


def summarize(R, N):
    pct = 100.0 * np.asarray(R) / N
    return dict(median_pct=float(np.median(pct)), q25_pct=float(np.percentile(pct, 25)),
                q75_pct=float(np.percentile(pct, 75)), top50=int((np.asarray(R) <= 50).sum()),
                n_queries=len(R), median_rank=float(np.median(R)))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--encoder", type=Path, required=True)
    ap.add_argument("--tag", required=True, help="nombre del modelo en las salidas")
    ap.add_argument("--n-candidates", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--plot-only", action="store_true", help="rehace la figura desde el JSON")
    ap.add_argument("--val-only", action="store_true",
                    help="solo la validación para ELEGIR época (no toca El Pinacate): "
                         "Marius -> campo volcánico de San Francisco, y cráteres")
    a = ap.parse_args()
    art = ROOT / "data/artifacts"
    if a.plot_only:
        saved = json.loads((art / f"eval_60_{a.tag}.json").read_text())
        return plot(saved["results"], saved["n_candidates_total"], a.tag, art)
    rng = np.random.default_rng(a.seed)
    bj = json.loads((art / "baseline_feat_60.json").read_text())
    mu, sd = np.array(bj["mean"], np.float32), np.array(bj["std"], np.float32)
    enc = load_encoder(a.encoder)

    # candidatos terrestres
    cand_sets = [load_set("earth_60"), load_set("earth_60_arizona"),
                 load_set("earth_60_deathvalley"), meteor_centered()]
    C_meta = pd.concat([s.meta for s in cand_sets], ignore_index=True)
    C_emb = np.concatenate([embed_set(enc, s) for s in cand_sets])
    C_feat = np.concatenate([base_feats(s, mu, sd) for s in cand_sets])
    N = len(C_meta)
    is_pinacate = C_meta.holdout.to_numpy() & C_meta.patch_id.str.startswith("earth-60-0").to_numpy()
    in_az = C_meta.region.eq("Arizona, USA").to_numpy() & (C_meta.patch_id.str[9:].astype(int) >= 300000).to_numpy()
    is_sf = in_az & (C_meta.lat >= SF_FIELD["lat_min"]).to_numpy() & (C_meta.lon <= SF_FIELD["lon_max"]).to_numpy()
    d_meteor = gc_km(METEOR[0], METEOR[1], C_meta.lat.to_numpy(), C_meta.lon.to_numpy(), RADIUS_KM["earth"])
    is_meteor = (d_meteor < 4.0) & (in_az | (C_meta.patch_id == "earth-60-399999").to_numpy())
    print(f"candidatos: {N} | Pinacate {is_pinacate.sum()} | San Francisco {is_sf.sum()} | "
          f"Meteor {is_meteor.sum()}")

    # consultas lunares
    mar = load_set("moon_60_marius")
    dm = gc_km(*MARIUS_CENTER, mar.meta.lat.to_numpy(), mar.meta.lon.to_numpy(), RADIUS_KM["moon"])
    mar.patches = np.asarray(mar.patches)[dm <= MARIUS_RADIUS_KM]
    mar.meta = mar.meta[dm <= MARIUS_RADIUS_KM].reset_index(drop=True)
    craters = [load_set("moon_60_craters_tranquillitatis"), load_set("moon_60_craters_imbrium")]
    queries = {"blind_pinacate": (mar, is_pinacate), "volcanic": (mar, is_pinacate | is_sf)}
    q_emb = {"marius": embed_set(enc, mar)}
    q_feat = {"marius": base_feats(mar, mu, sd)}
    cr_emb = np.concatenate([embed_set(enc, s) for s in craters])
    cr_feat = np.concatenate([base_feats(s, mu, sd) for s in craters])

    results, per_query = {}, {}
    tests = [("blind_pinacate", q_emb["marius"], q_feat["marius"], is_pinacate),
             ("volcanic", q_emb["marius"], q_feat["marius"], is_pinacate | is_sf),
             ("craters", cr_emb, cr_feat, is_meteor)]
    if a.val_only:
        tests = [("val_sanfrancisco", q_emb["marius"], q_feat["marius"], is_sf),
                 ("craters", cr_emb, cr_feat, is_meteor)]
    for name, QE, QF, mask in tests:
        R = {m: [] for m in METHODS}
        for qe, qf in zip(QE, QF):
            r = ranks_for(qe, qf, C_emb, C_feat, mask, a.n_candidates, rng)
            for m in METHODS:
                R[m].append(r[m])
        results[name] = {m: summarize(R[m], N) for m in METHODS}
        per_query[name] = R
        print(f"\n[{name}] {len(QE)} consultas, {int(mask.sum())} parches objetivo, {N} candidatos")
        for m in METHODS:
            s = results[name][m]
            print(f"  {m:<9} mediana {s['median_pct']:7.3f}%  (IQR {s['q25_pct']:.3f}-{s['q75_pct']:.3f})"
                  f"  lugar mediano {s['median_rank']:8.0f}  top50 {s['top50']}/{s['n_queries']}")

    out = dict(encoder=str(a.encoder), tag=a.tag, n_candidates_total=N,
               hybrid_prefilter=a.n_candidates, results=results)
    if a.val_only:
        (art / f"val_60_{a.tag}.json").write_text(json.dumps(out, indent=2))
        return
    (art / f"eval_60_{a.tag}.json").write_text(json.dumps(out, indent=2))

    plot(results, N, a.tag, art)


def plot(results, N, tag, art):
    """Figura para el jurado (inglés)."""
    titles = {"blind_pinacate": "Blind test: Marius Hills → El Pinacate\n(never seen in training)",
              "volcanic": "Volcanic: Marius Hills →\nEl Pinacate or San Francisco field",
              "craters": "Craters: lunar simple craters →\nMeteor Crater"}
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8), sharey=True)
    order = [m for m in ["rrf", "hybrid", "net", "baseline", "random"] if m in results["craters"]]
    for ax, name in zip(axes, ["blind_pinacate", "volcanic", "craters"]):
        for i, m in enumerate(order):
            s = results[name][m]
            y = len(order) - 1 - i
            ax.plot([s["q25_pct"], s["q75_pct"]], [y, y], color=COLORS[m], lw=2, solid_capstyle="round")
            if m == "random":
                ax.plot(s["median_pct"], y, "X", color=COLORS[m], ms=9, mec="#fcfcfb", mew=1.5)
            else:
                ax.plot(s["median_pct"], y, MARKERS[m], color=COLORS[m], ms=9, mec="#fcfcfb", mew=2)
            ax.annotate(f"{s['median_pct']:.2g}%  ·  top-50: {s['top50']}/{s['n_queries']}",
                        (s["median_pct"], y), xytext=(0, -15), textcoords="offset points",
                        ha="center", fontsize=8, color="#52514e")
        ax.set_xscale("log")
        ax.set_ylim(-0.75, len(order) - 0.5)
        ax.set_xlim(0.005, 100)
        ax.set_title(titles[name], fontsize=10, color="#0b0b0b")
        ax.grid(axis="x", color="#e4e3df", lw=0.8)
        ax.set_axisbelow(True)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.tick_params(colors="#52514e", labelsize=8)
        ax.set_xlabel("Rank percentile of the known Earth analog (log; lower is better)",
                      fontsize=8, color="#52514e")
    axes[0].set_yticks(range(len(order)))
    axes[0].set_yticklabels([LABELS[m] for m in reversed(order)], fontsize=9, color="#0b0b0b")
    fig.suptitle(f"Where does the known analog rank among {N:,} Earth terrain patches? "
                 f"(median and interquartile range · model {tag})", fontsize=11, color="#0b0b0b")
    fig.patch.set_facecolor("#fcfcfb")
    for ax in axes:
        ax.set_facecolor("#fcfcfb")
    plt.tight_layout()
    plt.savefig(art / f"eval_60_{tag}.png", dpi=110, facecolor="#fcfcfb")
    print("\n->", art / f"eval_60_{tag}.json", "y .png")


if __name__ == "__main__":
    main()
