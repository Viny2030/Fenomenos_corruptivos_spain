"""
src/scraper_bdns.py
===================
Descarga convocatorias de subvenciones AECID desde la Base de Datos
Nacional de Subvenciones (BDNS / SNPSAP).
Cubre eslabones 2-3 del modelo de trazabilidad.

NOTA (2026-06): la URL vieja (.../bdnstrans/GE/es/convocatorias) es la ruta
del frontend Angular (SPA) -- devuelve el HTML de la app, no JSON, por eso
fallaba con "Expecting value: line 1 column 1". El backend real está en
/bdnstrans/api/convocatorias/busqueda. Ese endpoint no filtra por código de
órgano (el parámetro "organo" se ignora), así que se busca por texto libre
"AECID" y se filtra el resultado por nivel3 (organismo convocante real) para
quedarse solo con las convocatorias que de verdad emite AECID.

LIMITACIÓN CONOCIDA: no se confirmó el parámetro correcto del endpoint
/api/concesiones/busqueda para filtrar por convocatoria (idConvocatoria,
numeroConvocatoria y numConv devolvieron resultados sin filtrar). Por eso
importe_total_eur y n_beneficiarios quedan en 0 por ahora -- requiere
investigar ese endpoint más a fondo antes de poder traer montos reales.
"""
import logging
import requests
import pandas as pd
from datetime import datetime

log = logging.getLogger(__name__)
HEADERS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0 (compatible; MonitorMonteverde/2.0)"}
BASE = "https://www.infosubvenciones.es/bdnstrans/api"

# Texto que debe aparecer en el organismo convocante (nivel3) para
# confirmar que la convocatoria la emite AECID de verdad, y no que
# "AECID" solo aparece mencionada en la descripción de otro organismo.
FILTRO_ORGANISMO = ("COOPERACI", "INTERNACIONAL")


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
    log.info("Scraper BDNS iniciando...")
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
                "numero_bdns":       c.get("numeroConvocatoria", ""),
                "titulo":            c.get("descripcion", ""),
                "organo":            c.get("nivel3", "AECID"),
                "fecha_publicacion": c.get("fechaRecepcion", ""),
                # Pendiente: enlazar con /api/concesiones/busqueda una vez
                # confirmado el parámetro de filtro por convocatoria.
                "importe_total_eur": 0,
                "n_beneficiarios":   0,
                "tipo":              "Subvención",
                "estado":            "",
                "url":               f"https://www.infosubvenciones.es/bdnstrans/GE/es/convocatorias/{c.get('numeroConvocatoria', '')}",
                "fuente":            "BDNS",
            })

        if data.get("last", True):
            break

    if not rows:
        log.warning("  BDNS sin datos — usando seed")
        rows = _seed_bdns()

    df = pd.DataFrame(rows)
    df["importe_total_eur"] = pd.to_numeric(df["importe_total_eur"], errors="coerce")
    log.info(f"  BDNS: {len(df)} convocatorias")
    return df


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
    print(df)