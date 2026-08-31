"""
src/db.py
=========
DEPRECADO — este archivo era un duplicado byte a byte de db.py (raíz).
La implementación real vive en db.py (raíz), que es la que importa
pipeline.py (`from db import subir_procesados`). Nada en el repo importa
`src.db` ni `src/db.py` directamente.

Se deja este shim en vez de vaciarlo para no romper un import externo que
alguien pueda tener en un branch o script local — pero es candidato a
borrarse (`git rm src/db.py`) en la próxima limpieza.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import *  # noqa: F401,F403,E402
from db import (  # noqa: F401,E402
    db_disponible, get_engine, subir_procesados, restaurar_procesados,
    ultimo_run, TABLAS, DATA_PRO,
)
