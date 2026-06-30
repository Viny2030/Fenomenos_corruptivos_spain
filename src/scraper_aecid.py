"""
src/scraper_aecid.py
====================
Descarga intervenciones del portal datos.aecid.es
Cubre eslabones 1-2 del modelo de trazabilidad.

NOTA (2026-06): el portal migró de un backend CKAN (API JSON en
/api/action/...) a un CMS que sirve la lista como tabla HTML paginada en
/lista-de-intervenciones. La API CKAN vieja ya no responde (404) y se deja
como fallback secundario por si en algún momento se restaura. La fuente
primaria ahora es _scrape_lista_intervenciones(), que pagina esa tabla.
"""
import re
import time
import logging
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

log = logging.getLogger(__name__)

HEADERS = {
    "Accept": "text/html,application/json",
    "User-Agent": "Mozilla/5.0 (compatible; MonitorMonteverde/2.0; +https://github.com/Viny2030/Fenomenos_corruptivos_spain)",
}
BASE = "https://datos.aecid.es"
LISTADO_URL = f"{BASE}/lista-de-intervenciones"


def _get(url, params=None, retries=3):
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r
        except Exception as e:
            log.warning(f"  intento {i+1}/{retries} fallido: {e}")
            time.sleep(2 ** i)
    return None


def _parsear_importe(texto: str):
    """'15.000.000' (formato español, punto = miles) -> 15000000.0"""
    if not texto:
        return None
    limpio = re.sub(r"[^\d]", "", texto)
    return float(limpio) if limpio else None


def _fecha_desde_slug(slug: str) -> str:
    """
    El slug de detalle tiene forma {region}-{aa}-{periodo}-{seq},
    ej. 'z11-25-01-05108' o 'z01-24-h1-01400'. El segundo bloque es el
    año en 2 dígitos. Es una aproximación (no hay día/mes exacto en el
    listado) -- se usa el 1 de enero de ese año como placeholder para
    poder agrupar por año en el dashboard.
    """
    m = re.match(r"^[a-z0-9]+-(\d{2})-", slug)
    if not m:
        return ""
    aa = int(m.group(1))
    anio = 2000 + aa
    return f"{anio}-01-01"


def _parsear_fila(tr) -> dict:
    titulo_td = tr.find("td", class_="titulo")
    a = titulo_td.find("a") if titulo_td else None
    url = a["href"] if a and a.has_attr("href") else ""
    slug = url.rstrip("/").split("/")[-1] if url else ""

    entidad_td = tr.find("td", attrs={"data-label": "Entidad"})
    sectores_td = tr.find("td", attrs={"data-label": "Sectores"})
    pais_td = tr.find("td", attrs={"data-label": "País"})
    importe_td = tr.find("td", attrs={"data-label": "Importe"})

    return {
        "id": slug,
        "titulo": a.get_text(strip=True) if a else "",
        "entidad": entidad_td.get_text(strip=True) if entidad_td else "",
        "sectores_crs": "; ".join(
            s.get_text(strip=True) for s in sectores_td.find_all("span")
        ) if sectores_td else "",
        "pais_region": ", ".join(
            s.get_text(strip=True) for s in pais_td.find_all("span")
        ) if pais_td else "",
        "importe_eur": _parsear_importe(importe_td.get_text(strip=True)) if importe_td else None,
        "fecha": _fecha_desde_slug(slug),
        "fuente": "datos.aecid.es/lista-de-intervenciones",
        "url_recurso": url,
    }


def _scrape_lista_intervenciones(delta: int = 60, max_paginas: int = 30) -> pd.DataFrame:
    """Fuente primaria: pagina la tabla HTML real del portal (~830 registros)."""
    from bs4 import BeautifulSoup

    r = _get(LISTADO_URL, params={"delta": delta, "start": 1})
    if r is None:
        return pd.DataFrame()

    soup = BeautifulSoup(r.text, "lxml")
    tabla = soup.find("table", class_="tabla-resultados")
    if tabla is None:
        log.warning("  Lista de intervenciones: tabla no encontrada en la página")
        return pd.DataFrame()

    m = re.search(r"de\s+(\d+)\s+resultados", r.text)
    total = int(m.group(1)) if m else delta
    n_paginas = min(max_paginas, -(-total // delta))  # ceil division

    filas = [_parsear_fila(tr) for tr in tabla.find("tbody").find_all("tr")]

    for pagina in range(2, n_paginas + 1):
        time.sleep(0.4)  # cortesia con el servidor
        r = _get(LISTADO_URL, params={"delta": delta, "start": pagina})
        if r is None:
            log.warning(f"  pagina {pagina} fallo tras reintentos -- se continua con lo obtenido")
            continue
        soup = BeautifulSoup(r.text, "lxml")
        tabla = soup.find("table", class_="tabla-resultados")
        if tabla is None:
            continue
        filas.extend(_parsear_fila(tr) for tr in tabla.find("tbody").find_all("tr"))

    log.info(f"  Lista de intervenciones: {len(filas)}/{total} registros ({n_paginas} paginas)")
    return pd.DataFrame(filas)


def _scrape_api() -> pd.DataFrame:
    """Fallback: API CKAN vieja (se mantiene por si el portal vuelve a este backend)."""
    r = _get(f"{BASE}/api/action/package_search", params={"q": "cooperacion", "rows": 50})
    if r is None:
        return pd.DataFrame()
    try:
        payload = r.json()
    except Exception:
        return pd.DataFrame()
    results = payload.get("result", {}).get("results", [])
    if not results:
        return pd.DataFrame()

    rows = []
    for pkg in results:
        for res in pkg.get("resources", []):
            if res.get("format", "").upper() in ("CSV", "JSON", "XLSX"):
                rows.append({
                    "id":          pkg.get("id", ""),
                    "titulo":      pkg.get("title", ""),
                    "descripcion": pkg.get("notes", "")[:200],
                    "entidad":     pkg.get("organization", {}).get("title", "AECID"),
                    "url_recurso": res.get("url", ""),
                    "formato":     res.get("format", ""),
                    "fecha":       res.get("last_modified", datetime.now().strftime("%Y-%m-%d")),
                    "importe_eur": None,
                    "pais_region": "",
                    "sectores_crs": "",
                    "fuente":      "datos.aecid.es/API",
                })
    log.info(f"  API CKAN: {len(rows)} recursos")
    return pd.DataFrame(rows)


def _seed_datos() -> pd.DataFrame:
    """Ultimo fallback -- datos seed para que el pipeline nunca quede sin filas."""
    log.warning("  Usando datos seed (sin conexion a AECID)")
    return pd.DataFrame([
        {"id": "A1", "titulo": "Programa Agua y Saneamiento Bolivia", "entidad": "PNUD",
         "importe_eur": 4_500_000, "pais_region": "Bolivia", "sectores_crs": "14030",
         "fecha": "2023-01-15", "fuente": "seed", "url_recurso": ""},
        {"id": "A2", "titulo": "Fondo Adaptacion Climatica Africa", "entidad": "PNUD",
         "importe_eur": 15_000_000, "pais_region": "No Especificado", "sectores_crs": "41010",
         "fecha": "2023-03-20", "fuente": "seed", "url_recurso": ""},
        {"id": "A3", "titulo": "Educacion Guatemala UNICEF", "entidad": "UNICEF",
         "importe_eur": 2_800_000, "pais_region": "Guatemala", "sectores_crs": "11220",
         "fecha": "2023-05-10", "fuente": "seed", "url_recurso": ""},
        {"id": "A4", "titulo": "Seguridad Alimentaria Sahel FAO", "entidad": "FAO",
         "importe_eur": 7_200_000, "pais_region": "Mali", "sectores_crs": "31161",
         "fecha": "2023-06-01", "fuente": "seed", "url_recurso": ""},
        {"id": "A5", "titulo": "Gobernabilidad Honduras consultoria", "entidad": "Consultoria XYZ S.L.",
         "importe_eur": 890_000, "pais_region": "Honduras", "sectores_crs": "15110",
         "fecha": "2023-07-22", "fuente": "seed", "url_recurso": ""},
        {"id": "A6", "titulo": "Salud Mozambique OMS", "entidad": "OMS",
         "importe_eur": 3_100_000, "pais_region": "Mozambique", "sectores_crs": "12110",
         "fecha": "2023-08-14", "fuente": "seed", "url_recurso": ""},
        {"id": "A7", "titulo": "Refugiados Siria ACNUR", "entidad": "ACNUR",
         "importe_eur": 6_400_000, "pais_region": "Siria", "sectores_crs": "72010",
         "fecha": "2023-09-05", "fuente": "seed", "url_recurso": ""},
        {"id": "A8", "titulo": "Microfinanzas Ecuador PNUD", "entidad": "PNUD",
         "importe_eur": 1_500_000, "pais_region": "Ecuador", "sectores_crs": "25010",
         "fecha": "2023-10-18", "fuente": "seed", "url_recurso": ""},
    ])


def run_scraper(output_path: Path = None) -> pd.DataFrame:
    log.info("Scraper AECID iniciando...")

    df = _scrape_lista_intervenciones()
    if df.empty:
        log.warning("  Lista de intervenciones vacia -- probando API CKAN vieja...")
        df = _scrape_api()
    if df.empty:
        df = _seed_datos()

    # Asegurar columnas minimas
    for col in ["id", "titulo", "entidad", "importe_eur", "pais_region", "sectores_crs", "fecha", "fuente", "url_recurso"]:
        if col not in df.columns:
            df[col] = ""

    df["importe_eur"] = pd.to_numeric(df["importe_eur"], errors="coerce")

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        log.info(f"  Guardado: {output_path}")

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = run_scraper(Path("../data/raw/aecid_intervenciones.csv"))
    print(df.head())
    print(f"\nTotal: {len(df)} filas")