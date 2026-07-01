"""
src/scraper_bdns.py
===================
Descarga convocatorias Y concesiones de subvenciones de AECID desde la
Base de Datos Nacional de Subvenciones (BDNS / SNPSAP).
Cubre eslabones 2-3 del modelo de trazabilidad.

DOS ENDPOINTS DISTINTOS DEL MISMO API
--------------------------------------
  - /convocatorias/busqueda: la CONVOCATORIA (el llamado a presentar
    propuestas). Es un texto legal genérico ("convocatoria pública de
    concesión de subvenciones... correspondiente al año 2026") que NO
    identifica proyectos ni beneficiarios individuales.
  - /concesiones/busqueda: la CONCESIÓN (quién ganó cada convocatoria).
    Trae beneficiario, importe real y el id de la convocatoria a la que
    pertenece. Es la pieza que faltaba para (a) calcular importes reales
    por convocatoria y (b) cruzar contra los proyectos de datos.aecid.es
    por entidad implementadora.

Se confirmó explorando la API en vivo que el parámetro correcto para
ambos endpoints es "descripcion" (búsqueda de texto libre). Los
parámetros antes probados para concesiones (idConvocatoria,
numeroConvocatoria, numConv) no eran el problema real -- simplemente no
había código que llamara a /concesiones en absoluto.

CRUCE AECID↔BDNS -- por qué NO es por título
---------------------------------------------
Se probó cruzar por título/descripción (AECID: proyecto específico, BDNS
convocatoria: resolución legal genérica) contra las 834 intervenciones
reales: score máximo de fuzzy match 52.9/100, cero matches útiles. Bajar
el umbral para forzar matches habría fabricado vínculos falsos -- lo
opuesto a lo que busca una herramienta de detección de irregularidades.

El cruce que sí funciona es por ENTIDAD implementadora (AECID) contra
BENEFICIARIO (concesión BDNS), normalizando acentos/mayúsculas primero.
Sin esa normalización ("FUNDACION" vs "Fundación") el score también daba
inútil. Con normalización, sobre una muestra real: 63/88 beneficiarios
institucionales matchearon con score >= 85 contra su entidad AECID
correspondiente (ej. "FUNDACION OXFAM INTERMON FUNDACION PRIVADA" <->
"Fundación Oxfam Intermón").
"""
import re
import logging
import unicodedata
import requests
import pandas as pd
from rapidfuzz import fuzz

log = logging.getLogger(__name__)
HEADERS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0 (compatible; MonitorMonteverde/2.0)"}
BASE = "https://www.infosubvenciones.es/bdnstrans/api"

# Texto que debe aparecer en el organismo convocante (nivel3) para
# confirmar que la convocatoria/concesión la emite AECID de verdad, y no
# que "AECID" solo aparece mencionada de paso en la descripción de otro
# organismo.
FILTRO_ORGANISMO = ("COOPERACI", "INTERNACIONAL")

# Tope de páginas para /concesiones (pageSize=50). A fecha de escritura el
# universo de resultados de "AECID" en concesiones son ~106 páginas
# (~5.300 filas antes de filtrar por nivel3, ~1 min de fetch). Se corta
# antes si el API marca last=True.
MAX_PAGINAS_CONCESIONES = 130

RE_PERSONA_FISICA = re.compile(r"^\*{3}\d")           # beneficiario enmascarado: "***1234** NOMBRE"
RE_CIF_PREFIJO    = re.compile(r"^[A-Z]\d{7,8}[A-Z]?\s+")  # "G82257064 FUNDACIÓN..." -> "FUNDACIÓN..."


def _normalizar(s: str) -> str:
    """Mayúsculas + sin acentos, para comparar nombres de entidades entre
    fuentes que no siempre usan la misma tilde/capitalización (crítico:
    sin esto el fuzzy match es prácticamente inútil, ver nota del módulo)."""
    s = str(s or "")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z0-9 ]", " ", s).upper()
    return re.sub(r"\s+", " ", s).strip()


def _es_persona_fisica(beneficiario: str) -> bool:
    return bool(RE_PERSONA_FISICA.match(str(beneficiario or "")))


def _limpiar_beneficiario(beneficiario: str) -> str:
    """'G82257064 FUNDACIÓN AYUDA EN ACCIÓN' -> 'FUNDACIÓN AYUDA EN ACCIÓN'"""
    return RE_CIF_PREFIJO.sub("", str(beneficiario or "")).strip()


# ── Convocatorias ─────────────────────────────────────────────────────────────

def _buscar_convocatorias(texto="AECID", pagina=0, tam=50) -> dict:
    url = f"{BASE}/convocatorias/busqueda"
    params = {"descripcion": texto, "pageSize": tam, "page": pagina}
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning(f"  BDNS convocatorias: {e}")
        return {}


def scrape_bdns(texto_busqueda="AECID", max_paginas=10) -> pd.DataFrame:
    log.info("Scraper BDNS (convocatorias) iniciando...")
    rows = []

    for p in range(max_paginas):
        data = _buscar_convocatorias(texto=texto_busqueda, pagina=p)
        content = data.get("content", [])
        if not content:
            break

        for c in content:
            nivel3 = (c.get("nivel3") or "").upper()
            if not all(palabra in nivel3 for palabra in FILTRO_ORGANISMO):
                continue  # mención de paso, no es una convocatoria de AECID

            rows.append({
                "id_convocatoria":   c.get("id", ""),
                "numero_bdns":       str(c.get("numeroConvocatoria", "")),
                "titulo":            c.get("descripcion", ""),
                "organo":            c.get("nivel3", "AECID"),
                "fecha_publicacion": c.get("fechaRecepcion", ""),
                "importe_total_eur": 0,   # se completa en enriquecer_convocatorias_con_concesiones()
                "n_beneficiarios":   0,   # idem
                "tipo":              "Subvención",
                "estado":            "",
                "url":               f"https://www.infosubvenciones.es/bdnstrans/GE/es/convocatorias/{c.get('numeroConvocatoria', '')}",
                "fuente":            "BDNS",
            })

        if data.get("last", True):
            break

    if not rows:
        log.warning("  BDNS convocatorias sin datos — usando seed")
        rows = _seed_bdns()

    df = pd.DataFrame(rows)
    df["importe_total_eur"] = pd.to_numeric(df["importe_total_eur"], errors="coerce")
    log.info(f"  BDNS convocatorias: {len(df)}")
    return df


# ── Concesiones (beneficiario real + importe real) ──────────────────────────

def _buscar_concesiones(texto="AECID", pagina=0, tam=50) -> dict:
    url = f"{BASE}/concesiones/busqueda"
    params = {"descripcion": texto, "pageSize": tam, "page": pagina}
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning(f"  BDNS concesiones: {e}")
        return {}


def scrape_concesiones_aecid(texto_busqueda="AECID", max_paginas=MAX_PAGINAS_CONCESIONES,
                              tam=50) -> pd.DataFrame:
    """
    Descarga las concesiones (beneficiario + importe real) de convocatorias
    de AECID. Es la pieza que faltaba para calcular importes reales por
    convocatoria [pendiente #3] y para el cruce AECID↔BDNS por entidad
    implementadora [pendiente #2].
    """
    log.info("Scraper BDNS (concesiones) iniciando...")
    rows = []

    for p in range(max_paginas):
        data = _buscar_concesiones(texto=texto_busqueda, pagina=p, tam=tam)
        content = data.get("content", [])
        if not content:
            break

        for c in content:
            nivel3 = (c.get("nivel3") or "").upper()
            if not all(palabra in nivel3 for palabra in FILTRO_ORGANISMO):
                continue  # mención de paso, no es una concesión de AECID

            beneficiario_raw = c.get("beneficiario", "")
            rows.append({
                "id_concesion":        c.get("id", ""),
                "cod_concesion":       c.get("codConcesion", ""),
                "beneficiario":        _limpiar_beneficiario(beneficiario_raw),
                "es_persona_fisica":   _es_persona_fisica(beneficiario_raw),
                "importe_eur":         c.get("importe", 0) or 0,
                "fecha_concesion":     c.get("fechaConcesion", ""),
                "numero_convocatoria": str(c.get("numeroConvocatoria", "")),
                "id_convocatoria":     c.get("idConvocatoria", ""),
                "convocatoria_titulo": c.get("convocatoria", ""),
                "instrumento":         c.get("instrumento", ""),
                "fuente":              "BDNS/concesiones",
            })

        if data.get("last", True):
            break

    if not rows:
        log.warning("  BDNS concesiones sin datos")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["importe_eur"] = pd.to_numeric(df["importe_eur"], errors="coerce").fillna(0)
    n_institucionales = int((~df["es_persona_fisica"]).sum())
    n_personas = int(df["es_persona_fisica"].sum())
    log.info(f"  BDNS concesiones: {len(df)} "
             f"({n_institucionales} institucionales / {n_personas} personas físicas)")
    return df


def enriquecer_convocatorias_con_concesiones(df_convocatorias: pd.DataFrame,
                                              df_concesiones: pd.DataFrame) -> pd.DataFrame:
    """Completa importe_total_eur y n_beneficiarios de cada convocatoria
    agregando sus concesiones reales (resuelve el pendiente #3)."""
    if df_convocatorias.empty or df_concesiones.empty:
        return df_convocatorias

    df_concesiones = df_concesiones.copy()
    df_concesiones["numero_convocatoria"] = df_concesiones["numero_convocatoria"].astype(str)

    agg = df_concesiones.groupby("numero_convocatoria").agg(
        importe_total_eur=("importe_eur", "sum"),
        n_beneficiarios=("id_concesion", "count"),
    ).reset_index()

    df = df_convocatorias.copy()
    df["numero_bdns"] = df["numero_bdns"].astype(str)
    df = df.drop(columns=["importe_total_eur", "n_beneficiarios"], errors="ignore")
    df = df.merge(agg, how="left", left_on="numero_bdns", right_on="numero_convocatoria")
    df["importe_total_eur"] = df["importe_total_eur"].fillna(0)
    df["n_beneficiarios"] = df["n_beneficiarios"].fillna(0).astype(int)
    df = df.drop(columns=["numero_convocatoria"], errors="ignore")

    n_con_importe = int((df["importe_total_eur"] > 0).sum())
    log.info(f"  Importes reales completados: {n_con_importe}/{len(df)} convocatorias")
    return df


# ── Cruce AECID ↔ BDNS (por entidad implementadora, NO por título) ──────────

def cruzar_con_aecid(df_concesiones: pd.DataFrame, df_aecid: pd.DataFrame,
                      umbral: int = 80) -> pd.DataFrame:
    """
    Cruce fuzzy entre concesiones BDNS de AECID y proyectos AECID de
    datos.aecid.es, por nombre de ENTIDAD implementadora -- NO por título
    (ver nota al inicio del módulo sobre por qué el cruce por título no
    sirve en este caso). Solo se cruzan concesiones a personas jurídicas
    (ONGD, fundaciones, etc.); las becas a personas físicas se excluyen
    porque no tienen contraparte en datos.aecid.es.
    Agrega 'en_bdns', 'score_cruce_bdns' e 'id_bdns' a df_aecid.
    """
    if df_concesiones.empty or df_aecid.empty:
        df_aecid = df_aecid.copy()
        df_aecid["en_bdns"] = False
        df_aecid["score_cruce_bdns"] = 0
        df_aecid["id_bdns"] = ""
        return df_aecid

    institucionales = df_concesiones[~df_concesiones["es_persona_fisica"]].copy()
    if institucionales.empty:
        df_aecid = df_aecid.copy()
        df_aecid["en_bdns"] = False
        df_aecid["score_cruce_bdns"] = 0
        df_aecid["id_bdns"] = ""
        return df_aecid

    institucionales["beneficiario_norm"] = institucionales["beneficiario"].apply(_normalizar)
    beneficiarios = institucionales["beneficiario_norm"].tolist()
    cod_concesion = institucionales["cod_concesion"].fillna("").astype(str).tolist()

    def _mejor_match(entidad):
        entidad_norm = _normalizar(entidad)
        if not entidad_norm:
            return 0, ""
        mejor_score, mejor_id = 0, ""
        for i, b in enumerate(beneficiarios):
            score = fuzz.token_sort_ratio(entidad_norm, b)
            if score > mejor_score:
                mejor_score, mejor_id = score, cod_concesion[i]
        return mejor_score, mejor_id

    resultados = df_aecid["entidad"].fillna("").apply(_mejor_match)
    df_aecid = df_aecid.copy()
    df_aecid["score_cruce_bdns"] = resultados.apply(lambda x: x[0])
    df_aecid["en_bdns"] = df_aecid["score_cruce_bdns"] >= umbral
    df_aecid["id_bdns"] = [
        rid if ok else "" for (_, rid), ok in zip(resultados, df_aecid["en_bdns"])
    ]
    n = int(df_aecid["en_bdns"].sum())
    log.info(f"  Cruce AECID↔BDNS: {n}/{len(df_aecid)} intervenciones con entidad "
             f"identificada como beneficiaria en BDNS")
    return df_aecid


def _seed_bdns() -> list:
    return [
        {"id_convocatoria": "B1", "titulo": "Subvenciones ONGD 2023",
         "organo": "AECID", "fecha_publicacion": "2023-02-01",
         "importe_total_eur": 45_000_000, "n_beneficiarios": 38,
         "tipo": "Subvención", "estado": "Resuelta",
         "url": "", "fuente": "seed"},
        {"id_convocatoria": "B2", "titulo": "Convenios ONGD plurianuales",
         "organo": "AECID", "fecha_publicacion": "2023-03-15",
         "importe_total_eur": 28_000_000, "n_beneficiarios": 12,
         "tipo": "Convenio", "estado": "En ejecución",
         "url": "", "fuente": "seed"},
        {"id_convocatoria": "B3", "titulo": "Ayuda Humanitaria Emergencias",
         "organo": "AECID", "fecha_publicacion": "2023-04-10",
         "importe_total_eur": 18_500_000, "n_beneficiarios": 8,
         "tipo": "Ayuda de Emergencia", "estado": "Resuelta",
         "url": "", "fuente": "seed"},
    ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = scrape_bdns()
    df_c = scrape_concesiones_aecid()
    df = enriquecer_convocatorias_con_concesiones(df, df_c)
    print(df[["titulo", "importe_total_eur", "n_beneficiarios"]].head(10))
