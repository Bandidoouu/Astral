#!/usr/bin/env python
"""Figura de validación para la diapositiva (en inglés): 60 m y 1 km, red contra fórmula
contra azar. Lee los resultados guardados (no recalcula nada):
  data/artifacts/eval_60_v2sel.json   (60 m, modelo de producción, incluye la ciega)
  data/artifacts/val_1000_v2_1000.json (1 km, incluye la ciega)
Salida: data/artifacts/figures/validation_{light,dark}.{png,svg} (16:9) + validation.json

  python -m ml.figure_validation
"""
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, NullLocator

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))
ART = ROOT / "data/artifacts"
OUT = ART / "figures"

ROWS = {
    60: [("blind_pinacate", "Montes Marius → El Pinacate", True),
         ("volcanic", "Montes Marius → Pinacate or San Francisco field", False),
         ("craters", "Mare craters → Meteor Crater", False)],
    1000: [("marius_pinacate", "Montes Marius → El Pinacate", True),
           ("olympus_hawaii", "Olympus Mons (Mars) → Mauna Loa", False),
           ("channels_scablands", "Kasei and Ares Valles (Mars) → Channeled Scablands", False),
           ("marius_sf", "Montes Marius → San Francisco volcanic field", False),
           ("dunes_sahara_namib", "Olympia Undae dunes (Mars) → Sahara / Namib", False),
           ("maria_flood_basalts", "Lunar maria → Columbia River / Deccan basalts", False)],
}
THEMES = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#8a8984", grid="#e4e3df",
                  net="#2a78d6", formula="#eb6834", random="#8a8984", band="#f0efec"),
    "dark": dict(surface="#1a1a19", ink="#f0efec", ink2="#c3c2b7", muted="#8f8e88", grid="#383835",
                 net="#3987e5", formula="#d95926", random="#8f8e88", band="#262624"),
}


def fmt(p):
    return f"{p:.2f}%" if p >= 0.1 else (f"{p:.3f}%" if p >= 0.001 else f"{p:.4f}%")


def load():
    r60 = json.loads((ART / "eval_60_v2sel.json").read_text())
    r1k = json.loads((ART / "val_1000_v2_1000.json").read_text())
    data = {}
    for scale, src in ((60, r60), (1000, r1k)):
        data[scale] = dict(n=src["n_candidates_total"], rows=[])
        for key, label, blind in ROWS[scale]:
            res = src["results"][key]
            data[scale]["rows"].append(dict(
                key=key, label=label, blind=blind,
                **{m: dict(median_pct=res[k]["median_pct"], median_rank=res[k]["median_rank"],
                           top50=res[k]["top50"], n_queries=res[k]["n_queries"])
                   for m, k in (("network", "net"), ("formula", "baseline"), ("random", "random"))}))
    return data


def draw(data, theme):
    t = THEMES[theme]
    plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": t["ink"], "axes.labelcolor": t["ink2"],
                         "xtick.color": t["ink2"], "ytick.color": t["ink"]})
    fig = plt.figure(figsize=(16, 9), facecolor=t["surface"])
    n60, n1k = len(data[60]["rows"]), len(data[1000]["rows"])
    gs = fig.add_gridspec(2, 1, height_ratios=[n60 + 0.6, n1k + 0.6], hspace=0.42,
                          left=0.33, right=0.95, top=0.80, bottom=0.10)
    fig.text(0.04, 0.93, "Our network finds known Earth analogs near the top of the ranking",
             fontsize=24, weight="bold", color=t["ink"])
    fig.text(0.04, 0.885, "Median percentile of the known analog among all Earth patches · lower is "
             "better · log scale · El Pinacate was hidden from training", fontsize=13.5, color=t["ink2"])
    for i, scale in enumerate((60, 1000)):
        ax = fig.add_subplot(gs[i])
        ax.set_facecolor(t["surface"])
        rows = data[scale]["rows"]
        for y, row in enumerate(rows):
            if row["blind"]:
                ax.axhspan(y - 0.42, y + 0.42, color=t["band"], zorder=0, lw=0)
            vals = [row[m]["median_pct"] for m in ("network", "formula", "random")]
            ax.plot([min(vals), max(vals)], [y, y], color=t["grid"], lw=2, zorder=1, solid_capstyle="round")
            ax.scatter(row["random"]["median_pct"], y + 0.17, marker="x", s=90, color=t["random"], lw=2, zorder=3)
            ax.scatter(row["formula"]["median_pct"], y, marker="s", s=110, color=t["formula"],
                       edgecolors=t["surface"], linewidths=2, zorder=4)
            ax.scatter(row["network"]["median_pct"], y - 0.17, marker="o", s=150, color=t["net"],
                       edgecolors=t["surface"], linewidths=2, zorder=5)
            net = row["network"]
            extra = (f"  rank {net['median_rank']:,.0f}" if scale == 60 or net["median_rank"] <= 5 else "")
            ax.annotate(fmt(net["median_pct"]) + extra, (net["median_pct"], y - 0.17), xytext=(0, 11),
                        textcoords="offset points", ha="center", fontsize=11.5, color=t["ink"],
                        weight="bold" if row["blind"] else "normal")
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels([("BLIND TEST  " if r["blind"] else "") + r["label"] for r in rows], fontsize=13)
        for lab, r in zip(ax.get_yticklabels(), rows):
            if r["blind"]:
                lab.set_weight("bold")
        ax.set_ylim(len(rows) - 0.5, -0.7)
        ax.set_xscale("log")
        ax.set_xlim(0.0012, 60)
        ax.xaxis.set_major_locator(FixedLocator([0.01, 0.1, 1, 10]))
        ax.xaxis.set_minor_locator(NullLocator())
        ax.set_xticklabels(["0.01%", "0.1%", "1%", "10%"], fontsize=12)
        ax.grid(axis="x", color=t["grid"], lw=1)
        ax.set_axisbelow(True)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.tick_params(length=0)
        title = (f"Detail scale · 60 m/px · Moon south pole ↔ Mexico · {data[60]['n']:,} Earth patches"
                 if scale == 60 else
                 f"Global scale · 1 km/px · Moon and Mars → whole Earth · {data[1000]['n']:,} Earth patches")
        ax.set_title(title, loc="left", fontsize=14.5, weight="bold", color=t["ink"], pad=10,
                     x=-0.40)
    # leyenda (siempre presente: 3 series)
    handles = [plt.Line2D([], [], marker="o", ls="", ms=12, color=t["net"], label="ASTRAL network (ours)"),
               plt.Line2D([], [], marker="s", ls="", ms=10, color=t["formula"], label="20-statistic terrain formula"),
               plt.Line2D([], [], marker="x", ls="", ms=10, mew=2, color=t["random"], label="Random")]
    fig.legend(handles=handles, loc="upper right", bbox_to_anchor=(0.95, 0.875), ncol=3, frameon=False,
               fontsize=13, labelcolor=t["ink"])
    fig.text(0.04, 0.035, "Lunar maria → flood basalts is a failure case we report: eroded Earth basalts "
             "do not look like flat maria at 1 km. Data: NASA LRO LOLA, MGS MOLA, NASADEM, SRTMGL30.",
             fontsize=11, color=t["ink2"])
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"validation_{theme}.{ext}", dpi=120, facecolor=t["surface"])
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = load()
    (OUT / "validation.json").write_text(json.dumps(data, indent=1))
    for theme in THEMES:
        draw(data, theme)
    print("->", OUT, sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
