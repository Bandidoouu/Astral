# ASTRAL neural network (`ml/`)

ASTRAL learns terrain embeddings from NASA elevation patches with a self-supervised
ResNet-18 (five terrain channels, 128-dimensional normalized embeddings). Production
uses v2: matched terrain batches, an auxiliary relief/slope objective and a planet
discriminator. Validation did **not** establish planet invariance as the reason for
transfer; v1 suppressed useful terrain information and performed poorly.

The network scores terrain. Environmental dimensions and base suitability are
computed separately from observations and explicit rules. Missing observations
remain missing. The default search rank combines neural and baseline ranks (RRF);
the displayed terrain score is the neural cosine.

Production encoders: `encoder_v2sel.pt` for 60 m Moon–Earth detail, and
`encoder_v2_1000.pt` for global 1 km searches and `gravity_scaled`.
Selection used validation pairs, excluding the Pinacate blind test. Existing results:

- 60 m blind test: Pinacate median rank 147 / 55,444 versus baseline 320.
- 1 km: Olympus → Mauna Loa neural median rank 1 / 7,669 versus baseline 1,720.
- 1 km blind test: Marius → Pinacate neural median percentile 0.48%.
- Performance is not uniform: lunar maria → terrestrial flood basalts remains weak.

## Reviewed delivery

Local package: `data/artifacts/release/v2-1km-r3/` (outside git). The manifest records
123 files and their SHA-256 hashes. Models, search indexes and suitability data are
unchanged from r2. The package adds four-rotation Grad-CAM: 72 unique figures for
102 curated-site associations, at 1 km in `same_size` mode.

Grad-CAM explains the terrain cosine approximately, not RRF rank or environmental
scores. Figures name actual indexed patches; multiple curated sites may share one
patch. Read the package's `gradcam/README.md` before using figures in the pitch.

```bash
# Run from the repository root in the existing environment.
python -m unittest discover -s ml/tests -v
python -m ml.check_delivery --release data/artifacts/release/v2-1km-r3

# First test one pair; use a new directory for each run.
python -m ml.gradcam_pairs --limit 1 --output data/artifacts/gradcam-sample-new
python -m ml.gradcam_pairs --output data/artifacts/gradcam-new
```

Team rules, model-selection history and next steps: [CLAUDE.md](CLAUDE.md).
Delivery review and handoff notes: [DELIVERY.md](DELIVERY.md).
