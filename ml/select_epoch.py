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
    a = ap.parse_args()
    art = ROOT / "data/artifacts"
    rows = []
    for e in a.epochs:
        enc = art / f"checkpoints/{a.run}/encoder_ep{e:02d}.pt"
        tag = f"{a.run}_ep{e:02d}"
        subprocess.run([sys.executable, "-m", "ml.evaluate", "--encoder", str(enc), "--tag", tag,
                        "--val-only"], check=True, cwd=ROOT, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        r = json.loads((art / f"val_60_{tag}.json").read_text())["results"]
        sf, cr = r["val_sanfrancisco"]["net"]["median_pct"], r["craters"]["net"]["median_pct"]
        rows.append((e, sf, cr, (sf + cr) / 2))
        print(f"ep{e:02d}  San Francisco {sf:.3f}%  cráteres {cr:.3f}%  promedio {(sf + cr) / 2:.3f}%",
              flush=True)
    best = min(rows, key=lambda x: x[3])
    print(f"ELEGIDA: época {best[0]} (promedio {best[3]:.3f}%)")
    (art / f"checkpoints/{a.run}/selected_epoch.json").write_text(
        json.dumps(dict(epoch=best[0], rows=rows, rule="mean of net median percentiles, SF + craters")))


if __name__ == "__main__":
    main()
