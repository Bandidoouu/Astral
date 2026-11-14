#!/usr/bin/env python
"""Validación de la escala global de 1 km (definida ANTES de entrenar; ml/CLAUDE.md §1c).

Parejas (consulta en la Luna o Marte → análogo terrestre conocido):

  olympus_hawaii       Olympus Mons                → Mauna Loa (Hawái)
  channels_scablands   Kasei Valles y Ares Vallis  → Channeled Scablands (Washington)
  dunes_sahara_namib   Olympia Undae               → Grand Erg Oriental/Occidental o Namib
  maria_flood_basalts  Imbrium, Serenitatis, Tranquillitatis → Columbia River o Deccan
  marius_sf            Montes Marius               → campo volcánico de San Francisco
  marius_pinacate      Montes Marius               → El Pinacate  (PRUEBA CIEGA: no elige época)

Cada sitio se corta en su centro exacto y en un anillo de 6 parches alrededor
(`--make-centers` escribe los CSV; luego `make_patches_global --centers`). Candidatos:
los 7,606 parches terrestres del índice + los parches de los sitios terrestres, SIN
la máscara de zonas prometedoras (para comparar métodos y épocas). Métrica: lugar
del mejor parche del análogo para cada parche de consulta; percentil mediano.

Regla para elegir época (la misma de v2): menor promedio, sobre las 5 parejas de
validación (sin Pinacate), del percentil mediano de la red sola.

  python -m ml.evaluate_1km --make-centers
  python -m ml.evaluate_1km --encoder data/artifacts/encoder_v2_1000.pt --tag v2_1000 [--blind]
  python -m ml.evaluate_1km ... --scale-mode gravity_scaled   # Luna x6, Marte x2.6
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from ml.baseline import features
from ml.embed import embed_set, load_encoder
from ml.evaluate import METHODS, ranks_for, summarize
from ml.model.dataset import PatchSet
from ml.search import RADIUS_KM, gc_km

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))
P = ROOT / "data/patches"
ART = ROOT / "data/artifacts"

# sitio: (cuerpo, lat, lon, radio del anillo en km). Longitudes -180..180, este positivo.
SITES = {
    "olympus_mons": ("mars", 18.65, -133.80, 60),
    "kasei_valles": ("mars", 24.00, -63.00, 60),
    "ares_vallis": ("mars", 10.00, -25.50, 50),
    "olympia_undae": ("mars", 81.00, 180.00, 60),
    "mare_imbrium": ("moon", 33.00, -16.00, 60),
    "mare_serenitatis": ("moon", 27.00, 18.40, 50),
    "mare_tranquillitatis": ("moon", 8.50, 31.40, 50),
    "montes_marius": ("moon", 14.00, -56.00, 40),
    "mauna_loa": ("earth", 19.48, -155.60, 25),
    "channeled_scablands": ("earth", 47.20, -118.80, 40),
    "grand_erg_oriental": ("earth", 30.50, 7.50, 50),
    "grand_erg_occidental": ("earth", 30.30, 0.00, 50),
    "namib_sand_sea": ("earth", -24.50, 15.30, 40),
    "columbia_river_basalts": ("earth", 46.50, -119.50, 50),
    "deccan_traps": ("earth", 19.50, 75.00, 60),
    "san_francisco_field": ("earth", 35.40, -111.60, 25),
    "el_pinacate": ("earth", 31.77, -113.50, 25),
}
PAIRS = {
    "olympus_hawaii": (["olympus_mons"], ["mauna_loa"]),
    "channels_scablands": (["kasei_valles", "ares_vallis"], ["channeled_scablands"]),
    "dunes_sahara_namib": (["olympia_undae"], ["grand_erg_oriental", "grand_erg_occidental",
                                                "namib_sand_sea"]),
    "maria_flood_basalts": (["mare_imbrium", "mare_serenitatis", "mare_tranquillitatis"],
                            ["columbia_river_basalts", "deccan_traps"]),
    "marius_sf": (["montes_marius"], ["san_francisco_field"]),
}
BLIND = {"marius_pinacate": (["montes_marius"], ["el_pinacate"])}
GRAVITY_PX = {"moon": 6050, "mars": 2640}        # g_tierra / g_cuerpo x 1000 m
GRAVITY_BLOCK = {"moon": 13, "mars": 6}          # promedio al leer (~6.2 y ~2.8 km)


def ring(lat, lon, r_km, R_km, n=6):
    """Centro + n puntos a r_km (rumbos uniformes)."""
    out = [(lat, lon)]
    d = r_km / R_km
    p1, l1 = np.radians(lat), np.radians(lon)
    for b in np.radians(np.arange(n) * 360 / n):
        p2 = np.arcsin(np.sin(p1) * np.cos(d) + np.cos(p1) * np.sin(d) * np.cos(b))
        l2 = l1 + np.arctan2(np.sin(b) * np.sin(d) * np.cos(p1), np.cos(d) - np.sin(p1) * np.sin(p2))
        out.append((float(np.degrees(p2)), float((np.degrees(l2) + 180) % 360 - 180)))
    return out


def make_centers():
    rows = {"earth": [], "moon": [], "mars": []}
    for name, (body, la, lo, r) in SITES.items():
        for a, b in ring(la, lo, r, RADIUS_KM[body]):
            rows[body].append(dict(lat=round(a, 5), lon=round(b, 5), region=name))
    for body, r in rows.items():
        f = P / f"val1km_centers_{body}.csv"
        pd.DataFrame(r).to_csv(f, index=False)
        print(f"{f}: {len(r)} centros")
    print("Luego:\n"
          "  python -m ml.data.make_patches_global --body earth --centers data/patches/val1km_centers_earth.csv "
          "--suffix _val --max-nodata-frac 0.6 --id-offset 900000\n"
          "  python -m ml.data.make_patches_global --body moon --centers data/patches/val1km_centers_moon.csv "
          "--suffix _val --id-offset 900000\n"
          "  python -m ml.data.make_patches_global --body mars --centers data/patches/val1km_centers_mars.csv "
          "--suffix _val --id-offset 900000\n"
          "  gravity_scaled: lo mismo para moon/mars con --px-m 6050 --block 13 / --px-m 2640 --block 6")


def load(name):
    return PatchSet.load(P / f"patches_{name}.npy", P / f"meta_{name}.parquet", False)


@torch.no_grad()
def feats(pset):
    out = []
    for a in range(0, len(pset.patches), 1024):
        z = torch.from_numpy(np.array(pset.patches[a:a + 1024])).unsqueeze(1).float().cuda()
        out.append(features(z, torch.full((len(z),), pset.scale_m, device="cuda")).cpu().numpy())
    return np.concatenate(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--make-centers", action="store_true")
    ap.add_argument("--encoder", type=Path)
    ap.add_argument("--tag")
    ap.add_argument("--blind", action="store_true", help="incluye la prueba ciega de Pinacate (UNA vez)")
    ap.add_argument("--scale-mode", default="same_size", choices=["same_size", "gravity_scaled"])
    ap.add_argument("--n-candidates", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    if a.make_centers:
        return make_centers()
    rng = np.random.default_rng(a.seed)
    enc = load_encoder(a.encoder)

    cands = [load("earth_1000"), load("earth_1000_val")]
    C_meta = pd.concat([s.meta for s in cands], ignore_index=True)
    C_emb = np.concatenate([embed_set(enc, s) for s in cands])
    C_raw = np.concatenate([feats(s) for s in cands])
    mu, sd = C_raw.mean(0), C_raw.std(0) + 1e-6
    C_feat = (C_raw - mu) / sd
    N = len(C_meta)
    is_val = C_meta.patch_id.str.slice(-6).astype(int).to_numpy() >= 900000

    def target_mask(names):
        m = np.zeros(N, bool)
        for t in names:
            _, la, lo, r = SITES[t]
            m |= is_val & (C_meta.region == t).to_numpy()
            # también los parches del índice cuyo centro cae dentro del anillo del sitio
            d = gc_km(la, lo, C_meta.lat.to_numpy(), C_meta.lon.to_numpy(), RADIUS_KM["earth"])
            m |= ~is_val & (d <= r + 10)
        return m

    q_sets = {}
    for body in ("moon", "mars"):
        name = f"{body}_1000_val" if a.scale_mode == "same_size" else f"{body}_{GRAVITY_PX[body]}_val"
        s = load(name)
        q_sets[body] = (s.meta, embed_set(enc, s), (feats(s) - mu) / sd)

    pairs = dict(PAIRS, **(BLIND if a.blind else {}))
    results = {}
    print(f"[{a.tag} · {a.scale_mode}] candidatos terrestres: {N:,}")
    for pname, (qs, ts) in pairs.items():
        tm = target_mask(ts)
        body = SITES[qs[0]][0]
        qm, qe, qf = q_sets[body]
        sel = np.flatnonzero(qm.region.isin(qs).to_numpy())
        R = {m: [] for m in METHODS}
        for i in sel:
            r = ranks_for(qe[i], qf[i], C_emb, C_feat, tm, a.n_candidates, rng)
            for m in METHODS:
                R[m].append(r[m])
        results[pname] = {m: summarize(R[m], N) for m in METHODS}
        results[pname]["n_targets"] = int(tm.sum())
        line = "  ".join(f"{m} {results[pname][m]['median_pct']:.2f}%" for m in METHODS)
        print(f"  {pname:<20} ({len(sel)} consultas, {tm.sum()} objetivo)  {line}", flush=True)
    val = float(np.mean([results[p]["net"]["median_pct"] for p in PAIRS]))
    print(f"VALIDACIÓN (promedio de la mediana de la red sola, 5 parejas): {val:.3f}%")
    out = ART / f"val_1000_{a.tag}{'' if a.scale_mode == 'same_size' else '_gravity'}.json"
    out.write_text(json.dumps(dict(tag=a.tag, scale_mode=a.scale_mode, n_candidates_total=N,
                                   val_score=val, results=results), indent=1))
    print("->", out)


if __name__ == "__main__":
    main()
