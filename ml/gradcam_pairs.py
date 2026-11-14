#!/usr/bin/env python
"""Grad-CAM de los pares curados de la demo (3 primeros resultados por cuerpo destino).

Para cada sitio curado de `frontend/src/mocks/precomputed-results.json` (escala 1000,
same_size) y cada cuerpo destino, toma los 3 primeros resultados y calcula Grad-CAM
con un objetivo de similitud (producto punto con el embedding del otro parche: la
versión instalada de pytorch-grad-cam no trae SimilarityToConceptTarget):
  - sobre el parche resultado: qué partes lo hacen parecido a la consulta
  - sobre el parche consulta: qué partes lo hacen parecido al resultado
Capa: último bloque de la ResNet-18 (`backbone.layer4`). Figuras en inglés.

Salida: data/artifacts/gradcam/{query_patch_id}__{result_patch_id}.png + index.json
(el nombre sirve directo para GET /api/gradcam/{query_id}/{patch_id}).

  python -m ml.gradcam_pairs
"""
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from pytorch_grad_cam import GradCAM

from ml.embed import load_encoder
from ml.model.channels import make_channels

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))
ART = ROOT / "data/artifacts"
OUT = ART / "gradcam"
TOP = 3


class Similarity:
    def __init__(self, concept):
        self.concept = concept

    def __call__(self, out):
        return (out * self.concept).sum()


def main():
    doc = json.loads((ROOT / "frontend/src/mocks/precomputed-results.json").read_text())
    meta = pd.read_parquet(ART / "meta_1000.parquet").set_index("patch_id")
    enc = load_encoder(ART / "encoder_v2_1000.pt").float().eval()
    cam = GradCAM(model=enc, target_layers=[enc.backbone.layer4])
    arrays = {}

    def patch(pid):
        r = meta.loc[pid]
        if r.src not in arrays:
            arrays[r.src] = np.load(ROOT / f"data/patches/patches_{r.src}.npy", mmap_mode="r")
        z = torch.from_numpy(np.array(arrays[r.src][int(r.src_idx)], np.float32))[None, None].cuda()
        x = make_channels(z, torch.full((1,), float(r.scale_m), device="cuda"))
        return r, x

    OUT.mkdir(parents=True, exist_ok=True)
    index = []
    for site in doc["sites"]:
        resp = site["responses"]["1000"]
        for target in sorted({r["body"] for r in resp["results"]}):
            qid = resp["query"]["patches"][target]["patch_id"]
            qr, qx = patch(qid)
            with torch.no_grad():
                qe = enc(qx)[0]
            for rank, res in enumerate([r for r in resp["results"] if r["body"] == target][:TOP], 1):
                rr, rx = patch(res["patch_id"])
                with torch.no_grad():
                    re_ = enc(rx)[0]
                cos = float((qe * re_).sum())
                cam_r = cam(input_tensor=rx, targets=[Similarity(qe)])[0]
                cam_q = cam(input_tensor=qx, targets=[Similarity(re_)])[0]
                fig, ax = plt.subplots(1, 2, figsize=(8.4, 4.6))
                for a, x, c, row, title in [
                        (ax[0], qx, cam_q, qr, f"Query · {site['name']}"),
                        (ax[1], rx, cam_r, rr, f"#{rank} {target.capitalize()} · {res['region']}")]:
                    a.imshow(x[0, 4].cpu().numpy(), cmap="gray")
                    a.imshow(c, cmap="inferno", alpha=0.45, vmin=0, vmax=1)
                    a.set_title(title, fontsize=9)
                    a.set_xlabel(f"{row.lat:.2f}°, {row.lon:.2f}° · window {128 * row.scale_m / 1000:.0f} km",
                                 fontsize=8)
                    a.set_xticks([]); a.set_yticks([])
                fig.suptitle(f"Grad-CAM: what the network finds similar (cosine {cos:.2f}, "
                             f"terrain score {res['scores']['terrain']:.2f})", fontsize=10)
                fig.text(0.5, 0.015, "Bright = regions that raise the similarity. Hillshade of our "
                         "LOLA / MOLA / SRTMGL30 patches. ASTRAL model v2 (1 km).", ha="center", fontsize=7)
                f = OUT / f"{qid}__{res['patch_id']}.png"
                plt.savefig(f, dpi=110, bbox_inches="tight", facecolor="#fcfcfb")
                plt.close(fig)
                index.append(dict(site_id=site["id"], site=site["name"], query_patch_id=qid, target=target,
                                  rank=rank, result_patch_id=res["patch_id"], region=res["region"],
                                  cosine=round(cos, 4), file=f.name))
        print(f"  {site['name']}: {sum(1 for i in index if i['site_id'] == site['id'])} figuras", flush=True)
    (OUT / "index.json").write_text(json.dumps(dict(model="v2", encoder="encoder_v2_1000.pt",
                                                    layer="backbone.layer4", scale_m=1000,
                                                    pairs=index), indent=1))
    tot = sum(p.stat().st_size for p in OUT.glob("*.png")) / 1e6
    print(f"-> {OUT} ({len(index)} figuras, {tot:.1f} MB)")


if __name__ == "__main__":
    main()
