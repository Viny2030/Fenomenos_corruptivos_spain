"""
db.py
=====
Capa de persistencia en PostgreSQL (Railway) para los datos procesados.

Diseño: los CSVs en data/processed/ siguen siendo el formato de trabajo.
PostgreSQL actúa como respaldo persistente entre deploys:

  - pipeline.py  → al terminar, sube los CSVs procesados a la DB (subir_procesados)
  - main.py      → al arrancar, si faltan los CSVs (Railway resetea el
                   filesystem en cada deploy), los restaura desde la DB
                   (restaurar_procesados)

Si DATABASE_URL no está definida (entorno local sin DB), todo es no-op
y el sistema funciona exactamente igual que antes.
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
DATA_PRO = (Path("/app/data") if Path("/app").exists() else ROOT / "data") / "processed"

# Mapeo tabla SQL ←→ archivo CSV procesado
TABLAS = {
    "analisis_completo":      "analisis_completo.csv",
    "trazabilidad_por_fondo": "trazabilidad_por_fondo.csv",
    "scores_riesgo":          "scores_riesgo.csv",
    "intervenciones_clean":   "intervenciones_clean.csv",
}

_engine = None


def _database_url() -> str | None:
    url = os.getenv("DATABASE_URL")
    if not url:
        return None
    # Railway/Heroku a veces entregan postgres:// — SQLAlchemy 2.x exige postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def db_disponible() -> bool:
    return _database_url() is not None


def get_engine():
    """Engine SQLAlchemy lazy. Devuelve None si no hay DATABASE_URL."""
    global _engine
    if _engine is not None:
        return _engine
    url = _database_url()
    if url is None:
        return None
    from sqlalchemy import create_engine
    _engine = create_engine(url, pool_pre_ping=True, pool_recycle=300)
    return _engine


def subir_procesados() -> int:
    """
    Sube los CSVs de data/processed/ a PostgreSQL (replace).
    Devuelve la cantidad de tablas subidas. No-op si no hay DB.
    """
    eng = get_engine()
    if eng is None:
        log.info("DB: DATABASE_URL no definida — se omite persistencia")
        return 0

    subidas = 0
    for tabla, archivo in TABLAS.items():
        path = DATA_PRO / archivo
        if not path.exists():
            log.warning(f"DB: {archivo} no existe — se omite tabla {tabla}")
            continue
        try:
            df = pd.read_csv(path)
            df.to_sql(tabla, eng, if_exists="replace", index=False,
                      chunksize=1000, method="multi")
            log.info(f"DB: {tabla} ← {archivo} ({len(df)} filas)")
            subidas += 1
        except Exception as e:
            log.error(f"DB: error subiendo {tabla}: {e}")

    if subidas:
        _registrar_run(subidas)
    return subidas


def restaurar_procesados(solo_si_faltan: bool = True) -> int:
    """
    Restaura los CSVs de data/processed/ desde PostgreSQL.
    Si solo_si_faltan=True, solo escribe los CSVs que no existen en disco
    (caso típico: Railway acaba de redeployar y el filesystem está limpio).
    Devuelve la cantidad de archivos restaurados. No-op si no hay DB.
    """
    eng = get_engine()
    if eng is None:
        return 0

    DATA_PRO.mkdir(parents=True, exist_ok=True)
    restaurados = 0
    for tabla, archivo in TABLAS.items():
        path = DATA_PRO / archivo
        if solo_si_faltan and path.exists():
            continue
        try:
            df = pd.read_sql_table(tabla, eng)
            df.to_csv(path, index=False, encoding="utf-8-sig")
            log.info(f"DB: {archivo} ← tabla {tabla} ({len(df)} filas) restaurado")
            restaurados += 1
        except Exception as e:
            # La tabla puede no existir todavía (primera vez) — no es fatal
            log.warning(f"DB: no se pudo restaurar {tabla}: {e}")

    return restaurados


def _registrar_run(n_tablas: int) -> None:
    """Registra metadata de cada corrida del pipeline en pipeline_runs."""
    eng = get_engine()
    if eng is None:
        return
    try:
        meta = pd.DataFrame([{
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "tablas_subidas": n_tablas,
        }])
        meta.to_sql("pipeline_runs", eng, if_exists="append", index=False)
    except Exception as e:
        log.warning(f"DB: no se pudo registrar el run: {e}")


def ultimo_run() -> str | None:
    """Timestamp del último run del pipeline persistido en DB, o None."""
    eng = get_engine()
    if eng is None:
        return None
    try:
        df = pd.read_sql(
            "SELECT timestamp_utc FROM pipeline_runs ORDER BY timestamp_utc DESC LIMIT 1",
            eng,
        )
        return df.iloc[0, 0] if len(df) else None
    except Exception:
        return None