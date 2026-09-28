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
import importlib.util
import sys
from pathlib import Path

# FIX: pipeline.py agrega src/ al sys.path, asi que `from db import ...` resolvia
# a ESTE archivo, que a su vez hacia `from db import ...` -> import circular
# (ImportError) y la persistencia en PostgreSQL nunca se ejecutaba.
# Ahora se carga db.py de la raiz explicitamente por ruta de archivo.
_RAIZ_DB = Path(__file__).resolve().parent.parent / "db.py"
_mod = sys.modules.get("_db_raiz")
if _mod is None:
    _spec = importlib.util.spec_from_file_location("_db_raiz", _RAIZ_DB)
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules["_db_raiz"] = _mod
    _spec.loader.exec_module(_mod)

db_disponible        = _mod.db_disponible
get_engine           = _mod.get_engine
subir_procesados     = _mod.subir_procesados
restaurar_procesados = _mod.restaurar_procesados
ultimo_run           = _mod.ultimo_run
TABLAS               = _mod.TABLAS
DATA_PRO             = _mod.DATA_PRO
