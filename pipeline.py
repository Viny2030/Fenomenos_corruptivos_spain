"""
pipeline.py
===========
Orquestador principal del análisis de trazabilidad de fondos AECID.
Reemplaza todos los notebooks. Ejecutable desde CLI o importable como módulo.

Uso:
    # Pipeline completo
    python pipeline.py

    # Solo descarga de datos
    python pipeline.py --solo-ingesta

    # Solo análisis (datos ya descargados)
    python pipeline.py --solo-analisis

    # Año específico
    python pipeline.py --años 2022 2023 2024

    # Sin descargar datos (modo offline)
    python pipeline.py --offline
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import yaml

# ── Rutas base ────────────────────────────────────────────────────────────────
ROOT     = Path(__file__).parent
SRC      = ROOT / "src"
DATA_RAW = ROOT / "data" / "raw"
DATA_PRO = ROOT / "data" / "processed"
REPORTS  = ROOT / "reports"

for d in [DATA_RAW, DATA_PRO, REPORTS]:
    d.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(SRC))

from scraper_aecid      import run_scraper         as scrape_aecid
from scraper_bdns       import (scrape_bdns, scrape_concesiones_aecid,
                                 enriquecer_convocatorias_con_concesiones,
                                 cruzar_con_aecid as cruzar_bdns_con_aecid)
from scraper_place      import scrape_place, detectar_adjudicacion_directa, cruzar_con_aecid
from indicadores_riesgo import calcular_scores_completos, generar_resumen_global
from src.trazabilidad_score import ModeloTrazabilidad

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(ROOT / "pipeline.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


def cargar_params() -> dict:
    with open(ROOT / "config" / "params.yaml") as f:
        return yaml.safe_load(f)


# ══════════════════════════════════════════════════════════════════════════════
# PASO 1: INGESTA DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

def paso_ingesta(años: list[int], forzar: bool = False) -> dict[str, Path]:
    """
    Descarga todas las fuentes. Si el archivo ya existe y forzar=False, lo omite.
    Devuelve un dict {nombre: Path} con los archivos generados.
    """
    archivos = {}

    # 1a. Portal datos.aecid.es
    path_aecid = DATA_RAW / "aecid_intervenciones.csv"
    if not path_aecid.exists() or forzar:
        log.info("── Descargando datos.aecid.es...")
        df = scrape_aecid(output_path=path_aecid)
        log.info(f"   {len(df)} intervenciones → {path_aecid.name}")
    else:
        log.info(f"   datos.aecid.es ya existe ({path_aecid.name}) — omitido")
    archivos["aecid"] = path_aecid

    # 1b. BDNS — convocatorias + concesiones (beneficiario e importe real)
    path_bdns = DATA_RAW / "bdns_subvenciones.csv"
    path_concesiones = DATA_RAW / "bdns_concesiones.csv"
    if not path_bdns.exists() or forzar:
        log.info("── Descargando BDNS (convocatorias + concesiones)...")
        df_bdns = scrape_bdns()
        df_concesiones = scrape_concesiones_aecid()
        df_bdns = enriquecer_convocatorias_con_concesiones(df_bdns, df_concesiones)
        df_bdns.to_csv(path_bdns, index=False, encoding="utf-8-sig")
        df_concesiones.to_csv(path_concesiones, index=False, encoding="utf-8-sig")
        log.info(f"   {len(df_bdns)} convocatorias, {len(df_concesiones)} concesiones → "
                 f"{path_bdns.name}, {path_concesiones.name}")
    else:
        log.info(f"   BDNS ya existe — omitido")
    archivos["bdns"] = path_bdns
    archivos["bdns_concesiones"] = path_concesiones

    # 1c. PLACE — contratos adjudicados
    path_place = DATA_RAW / "place_contratos.csv"
    if not path_place.exists() or forzar:
        log.info("── Descargando PLACE / OCDS...")
        df_place = scrape_place(years=años)
        df_place = detectar_adjudicacion_directa(df_place)
        df_place.to_csv(path_place, index=False, encoding="utf-8-sig")
        log.info(f"   {len(df_place)} contratos → {path_place.name}")
    else:
        log.info(f"   PLACE ya existe — omitido")
    archivos["place"] = path_place

    # 1d. Respuestas LTAIBG (archivo manual — si no existe, se crea vacío)
    path_ltaibg = DATA_RAW / "ltaibg_respuestas.csv"
    if not path_ltaibg.exists():
        pd.DataFrame(columns=[
            "fecha_solicitud", "proyecto", "organismo", "descripcion",
            "fecha_respuesta", "tipo_respuesta", "tiene_justificante",
            "url_documento", "notas"
        ]).to_csv(path_ltaibg, index=False, encoding="utf-8-sig")
        log.info(f"   Creado template LTAIBG → {path_ltaibg.name} (completar manualmente)")
    archivos["ltaibg"] = path_ltaibg

    return archivos


# ══════════════════════════════════════════════════════════════════════════════
# PASO 2: LIMPIEZA Y NORMALIZACIÓN
# ══════════════════════════════════════════════════════════════════════════════

# Diccionario de normalización de entidades
ENTIDADES_NORM = {
    "UN Women": "ONU Mujeres", "UNIFEM": "ONU Mujeres",
    "UNDP": "PNUD",
    "Programa de Naciones Unidas para el Desarrollo": "PNUD",
    "UNHCR": "ACNUR",
    "Alto Comisionado de las Naciones Unidas para los Refugiados": "ACNUR",
    "WFP": "PMA - Programa Mundial de Alimentos",
    "Programa Mundial de Alimentos": "PMA - Programa Mundial de Alimentos",
    "IOM": "OIM - Organización Internacional para las Migraciones",
    "ILO": "OIT - Organización Internacional del Trabajo",
    "WHO": "OMS",
    "PAHO": "OPS/OMS",
}

CRS_A_SECTOR = {
    "72": "Acción Humanitaria",
    "14": "Agua y Saneamiento",
    "15": "Gobernabilidad Democrática",
    "11": "Educación",
    "12": "Salud",
    "31": "Desarrollo Rural y Seguridad Alimentaria",
    "41": "Medio Ambiente y Cambio Climático",
    "25": "Crecimiento Económico",
}

REGIONES = {
    "América Latina y Caribe":    ["bolivia","colombia","ecuador","guatemala","honduras",
                                    "méxico","mexico","nicaragua","perú","peru","cuba",
                                    "haití","haiti","venezuela","paraguay","brasil",
                                    "chile","argentina","costa rica","panamá","panama"],
    "África Subsahariana":         ["etiopía","etiopia","kenya","mozambique","tanzania",
                                    "uganda","malí","mali","níger","niger","senegal",
                                    "ghana","nigeria","chad","ruanda","burkina","benín"],
    "Norte de África y Oriente Medio": ["marruecos","túnez","tunez","argelia","egipto",
                                         "jordania","líbano","libano","palestina","siria",
                                         "irak","yemen","mauritania"],
    "Asia":                        ["afghanistan","bangladés","filipinas","vietnam",
                                    "myanmar","nepal","pakistan","cambodia","laos"],
}


def paso_limpieza(archivos: dict[str, Path]) -> Path:
    """Carga, normaliza y enriquece el CSV de intervenciones AECID."""
    import re

    log.info("── Limpieza y normalización...")
    df = pd.read_csv(archivos["aecid"])
    orig = len(df)

    # Normalizar entidades
    df["entidad"] = df["entidad"].map(lambda x: ENTIDADES_NORM.get(str(x).strip(), str(x).strip()))

    # Extraer código CRS principal
    def primer_crs(s):
        m = re.search(r"(\d{5})", str(s))
        return m.group(1) if m else None

    df["codigo_crs"] = df.get("sectores_crs", pd.Series(dtype=str)).apply(primer_crs)
    df["ambito"] = df["codigo_crs"].apply(
        lambda c: CRS_A_SECTOR.get(c[:2], f"Sector {c[:2]}xx") if c else "Sin clasificar"
    )

    # Clasificar región
    def region(pais):
        if pd.isna(pais):
            return "No Especificado"
        pais_l = str(pais).lower()
        for reg, paises in REGIONES.items():
            if any(p in pais_l for p in paises):
                return reg
        if any(p in pais_l for p in ["no especificado", "ne -", "países en vías"]):
            return "No Especificado"
        return "Otras Regiones"

    df["region_ocde"] = df["pais_region"].apply(region)

    # Limpieza de importes
    df["importe_eur"] = pd.to_numeric(df["importe_eur"], errors="coerce")
    nulos = df["importe_eur"].isna().sum()
    if nulos:
        log.warning(f"   {nulos} importes nulos")

    out = DATA_PRO / "intervenciones_clean.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    log.info(f"   {len(df)}/{orig} registros limpios → {out.name}")
    return out


# ══════════════════════════════════════════════════════════════════════════════
# PASO 3: TRAZABILIDAD
# ══════════════════════════════════════════════════════════════════════════════

def paso_trazabilidad(archivos: dict[str, Path], clean_path: Path) -> Path:
    """Aplica el modelo de 7 eslabones a cada intervención."""
    log.info("── Análisis de trazabilidad (7 eslabones)...")

    df = pd.read_csv(clean_path)

    # Cargar fuentes externas si existen
    df_place       = pd.read_csv(archivos["place"])            if archivos["place"].exists()            else pd.DataFrame()
    df_ltaibg      = pd.read_csv(archivos["ltaibg"])            if archivos["ltaibg"].exists()           else pd.DataFrame()
    df_concesiones = pd.read_csv(archivos["bdns_concesiones"])  if archivos.get("bdns_concesiones") and archivos["bdns_concesiones"].exists() else pd.DataFrame()

    # Cruzar AECID ↔ PLACE
    if not df_place.empty:
        df = cruzar_con_aecid(df_place, df)

    # Cruzar AECID ↔ BDNS (por entidad implementadora, ver scraper_bdns.py)
    if not df_concesiones.empty:
        df = cruzar_bdns_con_aecid(df_concesiones, df)

    modelo = ModeloTrazabilidad(
        df_place=df_place,
        df_ltaibg=df_ltaibg,
        umbral_r3=500_000,
    )

    df_out = modelo.analizar_dataframe(df)
    resumen = modelo.resumen_global(df_out)

    log.info(f"   Score medio de trazabilidad: {resumen['score_trazabilidad_medio']}")
    log.info(f"   R1 ({resumen['n_ruptura_r1']} fondos): {resumen['pct_fondos_r1']}% del total")
    log.info(f"   R2 ({resumen['n_ruptura_r2']} fondos): {resumen['pct_fondos_r2']}% del total")
    log.info(f"   R3 ({resumen['n_ruptura_r3']} fondos): {resumen['pct_fondos_r3']}% del total")

    out = DATA_PRO / "trazabilidad_por_fondo.csv"
    df_out.to_csv(out, index=False, encoding="utf-8-sig")
    log.info(f"   → {out.name}")
    return out


# ══════════════════════════════════════════════════════════════════════════════
# PASO 4: RIESGO CORRUPTIVO
# ══════════════════════════════════════════════════════════════════════════════

def paso_riesgo(traz_path: Path) -> Path:
    """Calcula ICR, SOG, RES, VIA y score integrado por entidad."""
    log.info("── Indicadores de riesgo corruptivo...")

    df = pd.read_csv(traz_path)
    df_scores = calcular_scores_completos(df)

    # Score integrado: 60% riesgo + 40% trazabilidad invertida
    df_merged = df.merge(df_scores[["entidad", "score_riesgo"]], on="entidad", how="left")
    df_merged["score_trazabilidad_inv"] = 100 - df_merged["score_trazabilidad"]
    df_merged["score_integrado"] = (
        df_merged["score_riesgo"].fillna(50) * 0.60 +
        df_merged["score_trazabilidad_inv"] * 0.40
    )
    df_merged["clasificacion"] = pd.cut(
        df_merged["score_integrado"],
        bins=[0, 25, 50, 75, 100],
        labels=["VERDE", "AMARILLO", "NARANJA", "ROJO"]
    )

    out_scores = DATA_PRO / "scores_riesgo.csv"
    out_merged = DATA_PRO / "analisis_completo.csv"

    df_scores.to_csv(out_scores, index=False, encoding="utf-8-sig")
    df_merged.to_csv(out_merged, index=False, encoding="utf-8-sig")

    rojos = (df_merged["clasificacion"] == "ROJO").sum()
    fondos_rojos = df_merged[df_merged["clasificacion"] == "ROJO"]["importe_eur"].sum()
    log.info(f"   Clasificación ROJO: {rojos} fondos | {fondos_rojos/1e6:.1f} M€")
    log.info(f"   → {out_scores.name} + {out_merged.name}")

    return out_merged


# ══════════════════════════════════════════════════════════════════════════════
# PASO 5: INFORME
# ══════════════════════════════════════════════════════════════════════════════

def paso_informe(analisis_path: Path, archivos_raw: dict) -> Path:
    """Genera el informe ejecutivo en Markdown."""
    log.info("── Generando informe ejecutivo...")

    df = pd.read_csv(analisis_path)
    total = df["importe_eur"].sum()
    params = cargar_params()

    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Distribución por eslabón
    dist_eslabon = df.groupby("eslabon_corte").agg(
        n=("importe_eur", "count"),
        fondos=("importe_eur", "sum")
    ).to_dict("index")

    # Top 10 riesgo
    top10 = df.nlargest(10, "score_integrado")[
        ["titulo", "entidad", "importe_eur", "eslabon_corte", "score_integrado", "clasificacion"]
    ]

    # Clasificación
    clasif = df.groupby("clasificacion", observed=True).agg(
        n=("importe_eur", "count"),
        fondos=("importe_eur", "sum")
    )

    md = f"""# Informe Ejecutivo — Trazabilidad de Fondos AECID
*Generado: {ahora}*

---

## Resumen ejecutivo

| Métrica | Valor |
|---------|-------|
| Total fondos analizados | {total/1e6:.1f} M€ |
| Intervenciones | {len(df):,} |
| Entidades receptoras | {df['entidad'].nunique():,} |
| Score medio de trazabilidad | {df['score_trazabilidad'].mean():.0f}/100 |

---

## Trazabilidad por eslabón de corte

| Eslabón | Etapa | Nº fondos | M€ | % total |
|---------|-------|-----------|-----|---------|
"""
    ESLABON_NOMBRE = {
        3: "OOII sin desglose (R1)",
        4: "Destino geográfico opaco",
        5: "Sub-contratación sin OCDS (R2)",
        6: "Sin justificante público (R3)",
        7: "Trazabilidad completa",
    }
    for e, datos in sorted(dist_eslabon.items()):
        nombre = ESLABON_NOMBRE.get(e, f"Eslabón {e}")
        pct = datos["fondos"] / total * 100
        md += f"| {e} | {nombre} | {datos['n']} | {datos['fondos']/1e6:.1f} | {pct:.1f}% |\n"

    md += f"""
---

## Clasificación de riesgo integrado

| Clasificación | Nº fondos | M€ | % total |
|---------------|-----------|-----|---------|
"""
    for nivel, datos in clasif.iterrows():
        pct = datos["fondos"] / total * 100
        md += f"| {nivel} | {int(datos['n'])} | {datos['fondos']/1e6:.1f} | {pct:.1f}% |\n"

    md += f"""
---

## Top 10 intervenciones de mayor riesgo

| Título | Entidad | Importe | Eslabón | Score | Clasificación |
|--------|---------|---------|---------|-------|---------------|
"""
    for _, row in top10.iterrows():
        titulo = str(row["titulo"])[:50] + ("…" if len(str(row["titulo"])) > 50 else "")
        entidad = str(row["entidad"])[:30]
        md += f"| {titulo} | {entidad} | {row['importe_eur']/1e6:.1f}M€ | E{int(row['eslabon_corte'])} | {row['score_integrado']:.0f} | {row['clasificacion']} |\n"

    md += f"""
---

## Fuentes utilizadas

"""
    for nombre, path in archivos_raw.items():
        p = Path(path)
        if p.exists():
            df_tmp = pd.read_csv(p)
            md += f"- **{nombre}**: {len(df_tmp):,} registros (`{p.name}`)\n"
        else:
            md += f"- **{nombre}**: no disponible\n"

    md += f"""
---

## Notas metodológicas

- **R1**: Fondos a organismos internacionales (OOII) que agregan multi-donante sin desglosar la contribución española en IATI.
- **R2**: Contratos con adjudicación directa o sin publicación de sub-contratos en estándar OCDS.
- **R3**: Proyectos con importe >500.000€ sin evaluación final publicada ni respuesta favorable a solicitud LTAIBG.
- **Score integrado**: 60% riesgo corruptivo (ICR+SOG+RES+VIA) + 40% trazabilidad invertida.
- Análisis basado exclusivamente en datos públicos. No implica acusaciones de ilegalidad.

*Marco teórico: Fenómenos corruptivos — Economía Corruptiva (Dialnet, 2019)*
"""

    out = REPORTS / "informe_ejecutivo.md"
    out.write_text(md, encoding="utf-8")
    log.info(f"   → {out.name}")
    return out


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Pipeline de trazabilidad de fondos AECID",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python pipeline.py                          # pipeline completo
  python pipeline.py --solo-ingesta           # solo descarga datos
  python pipeline.py --solo-analisis          # solo análisis (datos ya descargados)
  python pipeline.py --años 2022 2023 2024    # filtrar años
  python pipeline.py --forzar                 # re-descargar aunque exista
        """
    )
    parser.add_argument("--solo-ingesta",   action="store_true", help="Solo descarga datos")
    parser.add_argument("--solo-analisis",  action="store_true", help="Solo análisis (sin descarga)")
    parser.add_argument("--años",           nargs="+", type=int, default=list(range(2020, 2025)))
    parser.add_argument("--forzar",         action="store_true", help="Re-descargar aunque exista")
    parser.add_argument("--sin-informe",    action="store_true", help="No generar informe Markdown")
    parser.add_argument("--log-level",      default="INFO", choices=["DEBUG", "INFO", "WARNING"])
    args = parser.parse_args()

    logging.getLogger().setLevel(getattr(logging, args.log_level))

    log.info("═" * 60)
    log.info("PIPELINE TRAZABILIDAD FONDOS AECID")
    log.info(f"Años: {args.años}")
    log.info("═" * 60)

    # ── Paso 1: ingesta ────────────────────────────────────────
    if not args.solo_analisis:
        archivos = paso_ingesta(años=args.años, forzar=args.forzar)
    else:
        archivos = {
            "aecid":            DATA_RAW / "aecid_intervenciones.csv",
            "bdns":             DATA_RAW / "bdns_subvenciones.csv",
            "bdns_concesiones": DATA_RAW / "bdns_concesiones.csv",
            "place":            DATA_RAW / "place_contratos.csv",
            "ltaibg":           DATA_RAW / "ltaibg_respuestas.csv",
        }

    if args.solo_ingesta:
        log.info("Ingesta completada. Saliendo (--solo-ingesta).")
        return

    # ── Paso 2: limpieza ───────────────────────────────────────
    clean_path = paso_limpieza(archivos)

    # ── Paso 3: trazabilidad ───────────────────────────────────
    traz_path = paso_trazabilidad(archivos, clean_path)

    # ── Paso 4: riesgo ─────────────────────────────────────────
    analisis_path = paso_riesgo(traz_path)

    # ── Paso 5: informe ────────────────────────────────────────
    if not args.sin_informe:
        paso_informe(analisis_path, archivos)

    # ── Paso 6: persistencia en PostgreSQL (Railway) ───────────
    try:
        from db import subir_procesados
        n = subir_procesados()
        if n:
            log.info(f"  Persistencia DB: {n} tablas subidas a PostgreSQL")
    except ImportError:
        log.info("  Persistencia DB: módulo db no disponible — omitido")
    except Exception as e:
        log.warning(f"  Persistencia DB falló (no fatal): {e}")

    log.info("═" * 60)
    log.info("PIPELINE COMPLETADO")
    log.info(f"  Análisis completo: {analisis_path}")
    log.info(f"  Informe:           {REPORTS / 'informe_ejecutivo.md'}")
    log.info("═" * 60)


if __name__ == "__main__":
    main()
