"""
src/scraper_place.py
====================
Descarga contratos adjudicados AECID desde PLACE/OCDS (contratación pública).
Cubre eslabón 5 del modelo — detección de R2 (sub-contratación sin estándar).
"""
import re
import logging
import requests
import pandas as pd
from datetime import datetime
from rapidfuzz import fuzz

log = logging.getLogger(__name__)
HEADERS = {"Accept": "application/json", "User-Agent": "MonitorMonteverde/1.0"}

# Atom feed de licitaciones del Estado
PLACE_ATOM = "https://contrataciondelestado.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom"
# API OCDS (si disponible)
OCDS_API   = "https://contrataciondelestado.es/wps/poc?uri=deeplink:ocds"


def scrape_place(years: list = None) -> pd.DataFrame:
    log.info("Scraper PLACE/OCDS iniciando...")
    df = _scrape_atom()
    if df.empty:
        log.warning("  PLACE Atom vacío — usando seed")
        df = pd.DataFrame(_seed_place())
    log.info(f"  PLACE: {len(df)} contratos")
    return df


def _scrape_atom() -> pd.DataFrame:
    try:
        r = requests.get(PLACE_ATOM, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return pd.DataFrame()
        entries = re.findall(r"<entry>(.*?)</entry>", r.text, re.DOTALL)
        datos = []
        for entry in entries[:200]:
            def _tag(tag):
                m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", entry, re.DOTALL)
                return re.sub(r"<[^>]+>", "", m.group(1) if m else "").strip()

            link_m = re.search(r"<link[^>]*href=['\"]([^'\"]+)['\"]", entry)
            titulo = _tag("title")
            if not titulo:
                continue
            datos.append({
                "id_contrato":      _tag("id"),
                "titulo":           titulo,
                "organismo":        _tag("summary")[:120],
                "fecha":            _tag("updated")[:10] or datetime.now().strftime("%Y-%m-%d"),
                "link":             link_m.group(1) if link_m else "",
                "tipo_procedimiento": _detectar_tipo(titulo),
                "importe_eur":      _extraer_importe(entry),
                "adjudicacion_directa": False,
                "fuente":           "PLACE/Atom",
            })
        return pd.DataFrame(datos)
    except Exception as e:
        log.error(f"  PLACE Atom error: {e}")
        return pd.DataFrame()


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


def _extraer_importe(texto: str) -> float:
    m = re.search(r"([\d\.,]+)\s*€", texto)
    if m:
        try:
            return float(m.group(1).replace(".", "").replace(",", "."))
        except Exception:
            pass
    return 0.0


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
    Cruce fuzzy entre contratos PLACE y proyectos AECID.
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
    return [
        {"id_contrato": "P1", "titulo": "Consultoría evaluación proyectos Bolivia",
         "organismo": "AECID", "fecha": "2023-05-10",
         "tipo_procedimiento": "Negociado sin publicidad",
         "importe_eur": 145_000, "adjudicacion_directa": True,
         "link": "", "fuente": "seed"},
        {"id_contrato": "P2", "titulo": "Asistencia técnica agua Guatemala",
         "organismo": "AECID", "fecha": "2023-06-20",
         "tipo_procedimiento": "Abierto",
         "importe_eur": 780_000, "adjudicacion_directa": False,
         "link": "", "fuente": "seed"},
        {"id_contrato": "P3", "titulo": "Estudio gobernabilidad Honduras",
         "organismo": "AECID", "fecha": "2023-07-05",
         "tipo_procedimiento": "Contrato menor",
         "importe_eur": 18_000, "adjudicacion_directa": True,
         "link": "", "fuente": "seed"},
    ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = scrape_place()
    df = detectar_adjudicacion_directa(df)
    print(df[["titulo", "tipo_procedimiento", "adjudicacion_directa"]].head(10))