#!/usr/bin/env python
"""Elige la época de un entrenamiento con la validación SIN Pinacate.

Regla fija (la misma que v2): menor promedio, sobre Marius -> campo volcánico de San
Francisco y cráteres -> Meteor Crater, del percentil mediano de la red sola.

  python -m ml.select_epoch --run main60v3 --epochs 2 4 6 8 10 12
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--epochs", type=int, nargs="+", required=True)
    ap.add_argument("--scale", type=int, default=60, choices=[60, 1000])
    a = ap.parse_args()
    art = ROOT / "data/artifacts"
    rows = []
    for e in a.epochs:
        enc = art / f"checkpoints/{a.run}/encoder_ep{e:02d}.pt"
        tag = f"{a.run}_ep{e:02d}"
        if a.scale == 1000:      # validación de 1 km (ml/CLAUDE.md §1c): 5 parejas, red sola
            subprocess.run([sys.executable, "-m", "ml.evaluate_1km", "--encoder", str(enc), "--tag", tag],
                           check=True, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            r = json.loads((art / f"val_1000_{tag}.json").read_text())
            per = {p: v["net"]["median_pct"] for p, v in r["results"].items()}
            rows.append((e, per, r["val_score"]))
            print(f"ep{e:02d}  " + "  ".join(f"{p} {v:.2f}%" for p, v in per.items())
                  + f"  promedio {r['val_score']:.3f}%", flush=True)
            continue
        subprocess.run([sys.executable, "-m", "ml.evaluate", "--encoder", str(enc), "--tag", tag,
                        "--val-only"], check=True, cwd=ROOT, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        r = json.loads((art / f"val_60_{tag}.json").read_text())["results"]
        sf, cr = r["val_sanfrancisco"]["net"]["median_pct"], r["craters"]["net"]["median_pct"]
        rows.append((e, sf, cr, (sf + cr) / 2))
        print(f"ep{e:02d}  San Francisco {sf:.3f}%  cráteres {cr:.3f}%  promedio {(sf + cr) / 2:.3f}%",
              flush=True)
    best = min(rows, key=lambda x: x[-1])
    print(f"ELEGIDA: época {best[0]} (promedio {best[-1]:.3f}%)")
    rule = ("mean of net median percentiles over the 5 1-km validation pairs" if a.scale == 1000
            else "mean of net median percentiles, SF + craters")
    (art / f"checkpoints/{a.run}/selected_epoch.json").write_text(
        json.dumps(dict(epoch=best[0], rows=rows, rule=rule)))


if __name__ == "__main__":
    main()
