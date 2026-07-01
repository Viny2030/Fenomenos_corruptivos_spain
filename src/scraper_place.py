"""
src/scraper_place.py
====================
Descarga contratos adjudicados a AECID desde el feed de sindicación de
PLACE (Plataforma de Contratación del Sector Público) y los cruza con los
proyectos de datos.aecid.es. Cubre el eslabón 5 del modelo (detección de
R2 — sub-contratación sin estándar OCDS).

CÓMO FUNCIONA EL FEED (importante para mantenimiento futuro)
--------------------------------------------------------------
El feed público:
    https://contrataciondelestado.es/sindicacion/sindicacion_643/
    licitacionesPerfilesContratanteCompleto3.atom
NO es un archivo histórico filtrable por órgano de contratación. Es una
ventana rodante de actualizaciones recientes de TODO el sector público
español: cada página trae ~500 entradas y cubre apenas unas horas. No
existe ningún parámetro de query en este feed para pedir "solo AECID" —
se confirmó explorando la API en vivo.

Estrategia adoptada:
  1. En cada corrida se lee la página más reciente del feed para detectar
     contratos AECID publicados desde la última vez que corrió el pipeline.
  2. Además, se sigue un "backfill" histórico: se pagina hacia atrás
     (enlace rel="next") un número acotado de páginas por corrida
     (MAX_PAGINAS_BACKFILL), guardando en disco un cursor
     (data/raw/place_cursor.json) para continuar exactamente donde se
     quedó en la corrida siguiente, hasta agotar el feed o llegar a
     FECHA_LIMITE_BACKFILL.
  3. Todos los contratos AECID encontrados se acumulan (nunca se
     sobrescriben) en el CSV de salida, deduplicados por id_contrato.

Con esto, el cruce AECID↔PLACE mejora progresivamente corrida a corrida
en vez de depender de una sola ejecución que, dado el tamaño del feed,
casi con certeza no va a contener ningún contrato de AECID.
"""
import re
import json
import logging
import requests
import pandas as pd
from pathlib import Path
from rapidfuzz import fuzz

log = logging.getLogger(__name__)
HEADERS = {"Accept": "application/atom+xml", "User-Agent": "MonitorMonteverde/1.0"}

PLACE_ATOM_ROOT = (
    "https://contrataciondelestado.es/sindicacion/sindicacion_643/"
    "licitacionesPerfilesContratanteCompleto3.atom"
)

# Páginas de backfill histórico a recorrer por corrida (~12-17 MB c/u).
# Acotado para no disparar el tiempo del job diario ni la carga sobre el
# servidor. Con este valor, en unos pocos días se cubren varias semanas
# de histórico (medido empíricamente: 15 páginas ≈ 6 días de feed).
MAX_PAGINAS_BACKFILL = 10

# No seguir el backfill más allá de esta fecha (evita paginar indefinidamente
# si el feed conserva años de historial).
FECHA_LIMITE_BACKFILL = "2018-01-01"

# Patrón para reconocer a AECID como órgano de contratación.
RE_AECID = re.compile(
    r"AECID|Agencia\s+Espa[ñn]ola\s+de\s+Cooperaci[oó]n\s+Internacional\s+para\s+el\s+Desarrollo",
    re.IGNORECASE,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
CURSOR_PATH = DATA_DIR / "place_cursor.json"
PATH_HISTORICO = DATA_DIR / "place_contratos.csv"


# ── Cursor de backfill ──────────────────────────────────────────────────────

def _cargar_cursor() -> dict:
    if CURSOR_PATH.exists():
        try:
            return json.loads(CURSOR_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"  No se pudo leer el cursor de PLACE ({e}) — se reinicia")
    return {"next_url": None, "agotado": False}


def _guardar_cursor(cursor: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CURSOR_PATH.write_text(json.dumps(cursor, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Histórico acumulado ──────────────────────────────────────────────────────

def _cargar_historico() -> pd.DataFrame:
    """Lee el CSV acumulado de corridas anteriores. Si el CSV es de una
    versión anterior del scraper (sin filtrar por AECID), descarta las filas
    que no correspondan a AECID en vez de arrastrar ruido."""
    if not PATH_HISTORICO.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(PATH_HISTORICO)
    except Exception as e:
        log.warning(f"  No se pudo leer histórico previo de PLACE ({e})")
        return pd.DataFrame()
    if "organismo" in df.columns:
        mask = df["organismo"].fillna("").str.contains(RE_AECID.pattern, regex=True, na=False)
        df = df[mask]
    return df


# ── Parseo de una página del feed ────────────────────────────────────────────

def _detectar_tipo(titulo: str) -> str:
    t = titulo.upper()
    if any(k in t for k in ["NEGOCIADO SIN", "CONTRATO MENOR", "EMERGENCIA"]):
        return "Negociado sin publicidad"
    if "NEGOCIADO" in t:
        return "Negociado"
    if "ABIERTO" in t:
        return "Abierto"
    if "RESTRINGIDO" in t:
        return "Restringido"
    if "DIREC" in t:
        return "Directo"
    return "No especificado"


def _parsear_pagina(texto: str):
    """Devuelve (contratos_aecid: list[dict], next_url: str|None, fecha_min: str|None)."""
    entries = re.findall(r"<entry>(.*?)</entry>", texto, re.DOTALL)
    datos = []
    fechas = []
    for entry in entries:
        def _tag(tag):
            m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", entry, re.DOTALL)
            return re.sub(r"<[^>]+>", "", m.group(1) if m else "").strip()

        summary = _tag("summary")
        updated = _tag("updated")
        if updated:
            fechas.append(updated[:10])

        organo_m = re.search(r"Órgano de Contratación:\s*([^;]+);", summary)
        organo = organo_m.group(1).strip() if organo_m else ""
        if not organo or not RE_AECID.search(organo):
            continue  # no es un contrato de AECID — se descarta

        titulo = _tag("title")
        if not titulo:
            continue

        link_m = re.search(r"<link[^>]*href=['\"]([^'\"]+)['\"]", entry)
        idlic_m = re.search(r"Id licitación:\s*([^;]+);", summary)
        importe_m = re.search(r"Importe:\s*([\d\.,]+)\s*EUR", summary)

        datos.append({
            "id_contrato":         _tag("id"),
            "id_expediente":       idlic_m.group(1).strip() if idlic_m else "",
            "titulo":              titulo,
            "organismo":           organo,
            "fecha":               updated[:10] if updated else "",
            "link":                link_m.group(1) if link_m else "",
            "tipo_procedimiento":  _detectar_tipo(titulo),
            "importe_eur":         float(importe_m.group(1).replace(".", "").replace(",", "."))
                                    if importe_m else 0.0,
            "adjudicacion_directa": False,
            "fuente":              "PLACE/Atom",
        })

    next_m = re.search(r'<link href="([^"]+)" rel="next"/>', texto)
    next_url = next_m.group(1) if next_m else None
    fecha_min = min(fechas) if fechas else None
    return datos, next_url, fecha_min


# ── Orquestación ──────────────────────────────────────────────────────────────

def scrape_place(years: list = None) -> pd.DataFrame:
    """
    Descarga de forma ACUMULATIVA los contratos de AECID publicados en
    PLACE. Combina lo ya encontrado en corridas anteriores con la página
    más reciente del feed y un tramo acotado de backfill histórico.
    """
    log.info("Scraper PLACE/AECID iniciando...")
    previos = _cargar_historico()
    log.info(f"  Histórico previo cargado: {len(previos)} contratos AECID")

    nuevos = []

    # (a) Página más reciente del feed — siempre, para no perderse contratos nuevos
    try:
        r = requests.get(PLACE_ATOM_ROOT, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            datos, _next, _fecha = _parsear_pagina(r.text)
            nuevos.extend(datos)
            log.info(f"  Página actual del feed: {len(datos)} contratos AECID nuevos")
        else:
            log.warning(f"  PLACE feed devolvió status {r.status_code}")
    except Exception as e:
        log.error(f"  PLACE feed (página actual) error: {e}")

    # (b) Backfill histórico acotado, continuando desde el cursor guardado
    cursor = _cargar_cursor()
    if not cursor.get("agotado"):
        url = cursor.get("next_url") or PLACE_ATOM_ROOT
        paginas_recorridas = 0
        while url and paginas_recorridas < MAX_PAGINAS_BACKFILL:
            try:
                r = requests.get(url, headers=HEADERS, timeout=30)
                if r.status_code != 200:
                    log.warning(f"  Backfill: status {r.status_code} en {url} — se corta la corrida")
                    break
                datos, next_url, fecha_min = _parsear_pagina(r.text)
                nuevos.extend(datos)
                paginas_recorridas += 1

                if fecha_min and fecha_min < FECHA_LIMITE_BACKFILL:
                    log.info(f"  Backfill alcanzó {fecha_min} (< {FECHA_LIMITE_BACKFILL}) — histórico completo")
                    cursor = {"next_url": None, "agotado": True}
                    break
                if not next_url:
                    log.info("  Backfill alcanzó el final del feed — histórico completo")
                    cursor = {"next_url": None, "agotado": True}
                    break

                cursor = {"next_url": next_url, "agotado": False}
                url = next_url
            except Exception as e:
                log.error(f"  PLACE backfill error: {e}")
                break
        _guardar_cursor(cursor)
        log.info(f"  Backfill: {paginas_recorridas} páginas recorridas en esta corrida "
                 f"(agotado={cursor.get('agotado')})")
    else:
        log.info("  Backfill histórico ya completo — solo se revisa la página actual del feed")

    df_nuevos = pd.DataFrame(nuevos)
    if not df_nuevos.empty:
        df = pd.concat([previos, df_nuevos], ignore_index=True)
    else:
        df = previos
    if not df.empty and "id_contrato" in df.columns:
        df = df.drop_duplicates(subset=["id_contrato"], keep="last").reset_index(drop=True)

    if df.empty:
        log.warning("  Todavía no se encontró ningún contrato real de AECID en PLACE "
                    "(backfill en progreso) — usando seed como placeholder")
        df = pd.DataFrame(_seed_place())

    log.info(f"  PLACE/AECID acumulado total: {len(df)} contratos")
    return df


def detectar_adjudicacion_directa(df: pd.DataFrame) -> pd.DataFrame:
    """Marca contratos con indicadores de adjudicación directa (R2)."""
    if df.empty:
        return df
    KEYWORDS_DIRECTO = [
        "negociado sin publicidad", "contrato menor", "emergencia",
        "urgencia", "adjudicación directa", "directo"
    ]
    mask = df["tipo_procedimiento"].str.lower().apply(
        lambda t: any(k in t for k in KEYWORDS_DIRECTO)
    )
    df = df.copy()
    df["adjudicacion_directa"] = mask
    n = mask.sum()
    if n:
        log.info(f"  R2 detectado: {n} contratos con adjudicación directa/sin publicidad")
    return df


def cruzar_con_aecid(df_place: pd.DataFrame, df_aecid: pd.DataFrame,
                     umbral: int = 75) -> pd.DataFrame:
    """
    Cruce fuzzy entre contratos PLACE (ya filtrados a AECID como órgano de
    contratación) y proyectos AECID de datos.aecid.es.
    Agrega columna 'en_place' y 'score_cruce' al df_aecid.
    """
    if df_place.empty or df_aecid.empty:
        df_aecid = df_aecid.copy()
        df_aecid["en_place"]    = False
        df_aecid["score_cruce"] = 0
        return df_aecid

    titulos_place = df_place["titulo"].fillna("").tolist()

    def _max_score(titulo_aecid):
        if not titulo_aecid:
            return 0
        scores = [fuzz.token_sort_ratio(titulo_aecid, t) for t in titulos_place]
        return max(scores) if scores else 0

    df_aecid = df_aecid.copy()
    df_aecid["score_cruce"] = df_aecid["titulo"].apply(_max_score)
    df_aecid["en_place"]    = df_aecid["score_cruce"] >= umbral
    n = df_aecid["en_place"].sum()
    log.info(f"  Cruce AECID↔PLACE: {n}/{len(df_aecid)} proyectos encontrados en PLACE")
    return df_aecid


def _seed_place() -> list:
    """Placeholder SOLO para cuando todavía no se encontró ningún contrato
    real de AECID (p. ej. las primeras corridas mientras avanza el backfill).
    Se reemplaza automáticamente en cuanto aparecen datos reales, porque
    _cargar_historico() descarta cualquier fila cuyo 'organismo' no matchee
    RE_AECID."""
    return [
        {"id_contrato": "SEED-1", "id_expediente": "", "titulo": "[PLACEHOLDER] Consultoría evaluación proyectos Bolivia",
         "organismo": "[seed — no es un dato real, ver nota en el manual]", "fecha": "2023-05-10",
         "tipo_procedimiento": "Negociado sin publicidad",
         "importe_eur": 145_000, "adjudicacion_directa": True,
         "link": "", "fuente": "seed"},
    ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = scrape_place()
    df = detectar_adjudicacion_directa(df)
    print(df[["titulo", "organismo", "tipo_procedimiento", "adjudicacion_directa"]].head(20))
