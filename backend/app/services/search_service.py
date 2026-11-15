import logging
import sys
from pathlib import Path
from app.core.config import ROOT_DIR, get_artifacts_dir

logger = logging.getLogger(__name__)

searcher_instance = None
searcher_attempted = False


def reset_searcher():
    """Reinicia la instancia del Searcher (útil para pruebas o recargas)."""
    global searcher_instance, searcher_attempted
    searcher_instance = None
    searcher_attempted = False


def get_searcher():
    """
    Retorna la instancia global del Searcher de ML.
    Se carga una sola vez al arrancar para no ralentizar las peticiones.
    """
    global searcher_instance, searcher_attempted
    if searcher_instance is None and not searcher_attempted:
        searcher_attempted = True
        try:
            if str(ROOT_DIR) not in sys.path:
                sys.path.insert(0, str(ROOT_DIR))
            from ml.search import Searcher
            art_dir = get_artifacts_dir()
            searcher_instance = Searcher(art=art_dir)
            logger.info("Searcher de ML cargado exitosamente.")
        except Exception as e:
            logger.warning(f"Searcher de ML no disponible ({e}). Operando en modo Mock.")
            searcher_instance = None
    return searcher_instance
