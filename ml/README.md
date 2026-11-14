# ASTRAL neural network (`ml/`)

Self-supervised contrastive network (ResNet-18, 5 terrain channels) with a planet
discriminator behind a gradient-reversal layer, so that embeddings capture *terrain
type* rather than *which planet*. Earth analogs are found by cosine similarity in FAISS.

| Step | Command |
| --- | --- |
| Patches (60 m) | `python -m ml.data.make_patches --body moon` / `--body earth` |
| Train | `python -m ml.train --run main60 --epochs 40 --version 1` |
| Ablation (no discriminator) | `python -m ml.train --run abl60 --epochs 25 --no-disc` |
| Channel check | `python -m ml.model.inspect_channels --png data/artifacts/channels_check.png` |

Run from the repo root. Team rules and design decisions: [`CLAUDE.md`](CLAUDE.md).
