"""
backfill_place_historico.py
============================
Backfill masivo de contratos AECID en PLACE usando los ZIPs anuales
publicados por el Ministerio de Hacienda, en vez de paginar el feed
atom rolling día por día (que a ritmo medido tardaría AÑOS en cubrir
el rango de fechas de los fondos de AECID — ver diagnóstico en el
manual/nota de R2).

Fuente (confirmada en vivo):
  https://contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_643/
  licitacionesPerfilesContratanteCompleto3_<AÑO>.zip

Cada ZIP anual contiene TODAS las actualizaciones del feed de licitaciones
de TODO el sector público para ese año (no solo AECID), empaquetadas como
varios ficheros .atom encadenados (el primero es
"licitacionesPerfilesContratanteCompleto3.atom", y de ahí en más van
enlazados). Son archivos grandes: cientos de MB por año.

Este script:
  1. Descarga el ZIP de cada año pedido (streaming, con reintentos).
  2. Extrae los .atom internos.
  3. Reusa el mismo parser de scraper_place.py (_parsear_pagina) para
     filtrar solo entradas cuyo "Órgano de Contratación" matchee
     RE_AECID — exactamente el mismo criterio que usa el backfill diario.
  4. Fusiona lo encontrado con el CSV histórico ya acumulado
     (data/raw/place_contratos.csv), deduplicando por id_contrato.
  5. Borra los archivos temporales (ZIP + atoms extraídos) al terminar
     cada año, para no inflar el disco.

Uso:
    # Años por defecto (donde están los fondos AECID seed: 2021-2024)
    python backfill_place_historico.py

    # Años específicos
    python backfill_place_historico.py --years 2022 2023

    # Solo simular sin escribir el CSV (para ver cuántos matches habría)
    python backfill_place_historico.py --years 2023 --dry-run

Notas de rendimiento:
  - Cada ZIP anual puede rondar varios cientos de MB. En GitHub Actions
    debería bajar bastante más rápido que en una conexión casera, pero
    igual conviene correr esto como job manual (workflow_dispatch)
    separado del cron diario, no como parte de él — si se mete en el
    pipeline diario, va a duplicar el timeout del job.
  - Es un backfill de UNA SOLA VEZ por año. Una vez corrido para
    2021-2024, no hace falta repetirlo — el backfill incremental diario
    (scraper_place.py, basado en el cursor) se encarga de mantenerse al
    día con lo nuevo desde ahí en adelante.
"""
import argparse
import logging
import shutil
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from src.scraper_place import (  # noqa: E402
    _parsear_pagina,
    DATA_DIR,
    PATH_HISTORICO,
)

log = logging.getLogger(__name__)

ZIP_URL_TMPL = (
    "https://contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_643/"
    "licitacionesPerfilesContratanteCompleto3_{year}.zip"
)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MonitorMonteverde/1.0"}

TMP_DIR = DATA_DIR / "_tmp_backfill_historico"
MAX_REINTENTOS = 4
TIMEOUT_DESCARGA = 600  # 10 min — los ZIP anuales son grandes


# ── Descarga con reintentos ──────────────────────────────────────────────────

def _descargar_zip_anual(year: int, destino: Path) -> bool:
    url = ZIP_URL_TMPL.format(year=year)
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            log.info(f"  [{year}] Descargando (intento {intento}/{MAX_REINTENTOS}): {url}")
            with requests.get(url, headers=HEADERS, stream=True, timeout=TIMEOUT_DESCARGA) as r:
                if r.status_code == 503:
                    espera = 10 * intento
                    log.warning(f"  [{year}] 503 (rate limit probable) — esperando {espera}s")
                    time.sleep(espera)
                    continue
                if r.status_code != 200:
                    log.error(f"  [{year}] status {r.status_code} — se aborta este año")
                    return False
                destino.parent.mkdir(parents=True, exist_ok=True)
                total = 0
                with open(destino, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                            total += len(chunk)
                log.info(f"  [{year}] Descarga completa: {total / 1_048_576:.1f} MB")
                return True
        except requests.exceptions.RequestException as e:
            espera = 10 * intento
            log.warning(f"  [{year}] Error de red ({e}) — reintentando en {espera}s")
            time.sleep(espera)
    log.error(f"  [{year}] Se agotaron los reintentos — se omite este año")
    return False


# ── Procesamiento del ZIP ────────────────────────────────────────────────────

def _procesar_zip_anual(year: int, zip_path: Path) -> list:
    """Extrae y parsea todos los .atom del ZIP, devuelve lista de contratos AECID."""
    extract_dir = TMP_DIR / f"extract_{year}"
    extract_dir.mkdir(parents=True, exist_ok=True)

    contratos = []
    try:
        with zipfile.ZipFile(zip_path) as z:
            atom_files = [n for n in z.namelist() if n.endswith(".atom")]
            log.info(f"  [{year}] {len(atom_files)} ficheros .atom dentro del ZIP")
            z.extractall(extract_dir)
    except zipfile.BadZipFile as e:
        log.error(f"  [{year}] ZIP corrupto o descarga incompleta ({e}) — se omite este año")
        return []

    for i, atom_name in enumerate(atom_files, 1):
        atom_path = extract_dir / atom_name
        if not atom_path.exists():
            continue
        try:
            texto = atom_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            log.warning(f"  [{year}] no se pudo leer {atom_name}: {e}")
            continue
        datos, _next, _fecha = _parsear_pagina(texto)
        if datos:
            log.info(f"  [{year}] {atom_name}: {len(datos)} contratos AECID encontrados")
        contratos.extend(datos)
        if i % 50 == 0:
            log.info(f"  [{year}] progreso: {i}/{len(atom_files)} ficheros procesados")

    log.info(f"  [{year}] TOTAL contratos AECID en {year}: {len(contratos)}")
    return contratos


# ── Fusión con el histórico ──────────────────────────────────────────────────

def _cargar_historico_crudo() -> pd.DataFrame:
    """Como _cargar_historico() de scraper_place.py, pero sin filtrar por
    AECID (acá lo hacemos por separado) — solo lee lo que ya hay en disco."""
    if not PATH_HISTORICO.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(PATH_HISTORICO)
    except Exception as e:
        log.warning(f"  No se pudo leer el histórico previo ({e})")
        return pd.DataFrame()


def _fusionar_y_guardar(nuevos: list, dry_run: bool) -> pd.DataFrame:
    previos = _cargar_historico_crudo()
    # Sacar el placeholder seed si estaba, ya no hace falta una vez que hay datos reales
    if not previos.empty and "fuente" in previos.columns:
        previos = previos[previos["fuente"] != "seed"]

    df_nuevos = pd.DataFrame(nuevos)
    if not df_nuevos.empty:
        df_nuevos["fuente"] = "PLACE/ZIP-historico"

    if df_nuevos.empty and previos.empty:
        log.warning("  No se encontró ningún contrato AECID en los años pedidos.")
        return pd.DataFrame()

    df = pd.concat([previos, df_nuevos], ignore_index=True) if not df_nuevos.empty else previos
    if "id_contrato" in df.columns:
        antes = len(df)
        df = df.drop_duplicates(subset=["id_contrato"], keep="last").reset_index(drop=True)
        log.info(f"  Deduplicado: {antes} → {len(df)} contratos únicos")

    if dry_run:
        log.info(f"  [DRY-RUN] No se escribió el CSV. Total que se hubiera guardado: {len(df)}")
    else:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(PATH_HISTORICO, index=False, encoding="utf-8-sig")
        log.info(f"  Guardado: {PATH_HISTORICO} ({len(df)} contratos AECID totales)")

    return df


# ── Orquestación ──────────────────────────────────────────────────────────────

def backfill_masivo(years: list, dry_run: bool = False) -> pd.DataFrame:
    log.info(f"Backfill histórico masivo — años: {years} (dry_run={dry_run})")
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    todos_nuevos = []
    for year in years:
        zip_path = TMP_DIR / f"{year}.zip"
        ok = _descargar_zip_anual(year, zip_path)
        if not ok:
            continue
        contratos = _procesar_zip_anual(year, zip_path)
        todos_nuevos.extend(contratos)

        # Limpieza inmediata para no acumular cientos de MB por año
        zip_path.unlink(missing_ok=True)
        shutil.rmtree(TMP_DIR / f"extract_{year}", ignore_errors=True)

    resultado = _fusionar_y_guardar(todos_nuevos, dry_run)

    shutil.rmtree(TMP_DIR, ignore_errors=True)
    return resultado


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Backfill masivo AECID↔PLACE vía ZIPs anuales")
    parser.add_argument("--years", type=int, nargs="+", default=[2021, 2022, 2023, 2024],
                         help="Años a descargar (default: 2021 2022 2023 2024, rango de los fondos AECID)")
    parser.add_argument("--dry-run", action="store_true",
                         help="No escribe el CSV, solo informa cuántos contratos se hubieran encontrado")
    args = parser.parse_args()

    df = backfill_masivo(args.years, dry_run=args.dry_run)
    if not df.empty:
        print(df[["fecha", "titulo", "organismo", "tipo_procedimiento", "importe_eur"]].tail(20))