import os
from pathlib import Path

ARTIFACTS_DIR = Path(os.getenv("ASTRAL_ARTIFACTS", "../data/artifacts"))
SCALES = (60, 500)
EMB_DIM = 128