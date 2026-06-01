"""
src/scraper_bdns.py
===================
Descarga subvenciones y convenios AECID desde la Base de Datos Nacional de Subvenciones.
Cubre eslabones 2-3 del modelo de trazabilidad.
"""
import logging
import requests
import pandas as pd
from datetime import datetime

log = logging.getLogger(__name__)
HEADERS = {"Accept": "application/json", "User-Agent": "MonitorMonteverde/1.0"}
BASE    = "https://www.pap.hacienda.gob.es/bdnstrans/GE/es"


def _buscar_convocatorias(organo="EA0029714", pagina=0, tam=50) -> list:
    """EA0029714 = código AECID en BDNS"""
    url = f"{BASE}/convocatorias"
    params = {
        "organo":   organo,
        "pagina":   pagina,
        "tamPagina": tam,
        "tipoBusqueda": "C",
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            return r.json().get("content", [])
    except Exception as e:
        log.warning(f"  BDNS convocatorias: {e}")
    return []


def _buscar_concesiones(id_conv: str) -> list:
    url = f"{BASE}/concesiones"
    try:
        r = requests.get(url, params={"idConv": id_conv}, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.json().get("content", [])
    except Exception:
        pass
    return []


def scrape_bdns(organo="EA0029714", max_paginas=5) -> pd.DataFrame:
    log.info("Scraper BDNS iniciando...")
    rows = []

    for p in range(max_paginas):
        convs = _buscar_convocatorias(organo=organo, pagina=p)
        if not convs:
            break
        for c in convs:
            id_conv = c.get("id") or c.get("idConvocatoria", "")
            concesiones = _buscar_concesiones(str(id_conv)) if id_conv else []
            n_benef = len(concesiones)
            importe_total = sum(
                float(x.get("importe", 0) or 0) for x in concesiones
            )
            rows.append({
                "id_convocatoria":   id_conv,
                "titulo":            c.get("titulo", c.get("denominacion", "")),
                "organo":            c.get("organoConvocante", "AECID"),
                "fecha_publicacion": c.get("fechaPublicacion", ""),
                "importe_total_eur": c.get("importeTotal", importe_total) or importe_total,
                "n_beneficiarios":   c.get("numBeneficiarios", n_benef) or n_benef,
                "tipo":              c.get("tipoConvocatoria", "Subvención"),
                "estado":            c.get("estado", ""),
                "url":               f"{BASE}/convocatorias?idConv={id_conv}",
                "fuente":            "BDNS",
            })

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