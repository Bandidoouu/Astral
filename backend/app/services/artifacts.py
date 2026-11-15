"""Carga única de los artefactos de ML: crea el Searcher una sola vez."""
import logging
import sys
from functools import lru_cache

from app.core.config import REPO_ROOT, get_artifacts_dir

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

log = logging.getLogger("astral.artifacts")


@lru_cache(maxsize=1)
def get_searcher():
    """Devuelve el Searcher de ML, o None si todavía no hay artefactos."""
    from ml.search import Searcher

    art = get_artifacts_dir()
    try:
        searcher = Searcher(art=art)
    except (AssertionError, Exception) as exc:
        log.warning("Sin artefactos o error en %s (%s): /api/similar usa el ejemplo de contracts/", art, exc)
        return None
    log.info("Searcher listo con escalas %s", sorted(searcher.idx))
    return searcher