import logging
import sys
from pathlib import Path
from app.core.config import ROOT_DIR

logger = logging.getLogger(__name__)

searcher_instance = None

def get_searcher():
    """
    Retorna la instancia global del Searcher de ML.
    Se carga una sola vez al arrancar para no ralentizar las peticiones.
    """
    global searcher_instance
    if searcher_instance is None:
        try:
            if str(ROOT_DIR) not in sys.path:
                sys.path.insert(0, str(ROOT_DIR))
            from ml.search import Searcher
            searcher_instance = Searcher(root=ROOT_DIR)
            logger.info("Searcher de ML cargado exitosamente.")
        except Exception as e:
            logger.warning(f"Searcher de ML no disponible ({e}). Operando en modo Mock.")
            searcher_instance = None
    return searcher_instance
