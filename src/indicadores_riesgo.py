"""
src/indicadores_riesgo.py
=========================
Indicadores de riesgo corruptivo para fondos AECID.
  ICR — Índice de Concentración de Receptores (HHI)
  SOG — Score de Opacidad en la Gestión
  RES — Riesgo por Eslabón de corte
  VIA — Vulnerabilidad Institucional del país receptor
"""
import logging
import pandas as pd
import numpy as np

log = logging.getLogger(__name__)

# ── Vulnerabilidad institucional por país (fuente: WGI Banco Mundial proxy) ──
# Escala 0-100 (100 = máximo riesgo)
VULNERABILIDAD_PAIS = {
    "somalia": 95, "sudan": 90, "sudán del sur": 90, "república centroafricana": 88,
    "haití": 85, "haiti": 85, "chad": 83, "yemen": 88, "siria": 90, "irak": 80,
    "afganistán": 87, "afghanistan": 87, "libia": 82, "mali": 78, "malí": 78,
    "niger": 75, "níger": 75, "burkina": 77, "mozambique": 68, "zimbabwe": 72,
    "myanmar": 76, "venezuela": 80, "nicaragua": 68, "cuba": 65,
    "honduras": 62, "guatemala": 60, "paraguay": 55, "bolivia": 52,
    "ecuador": 48, "perú": 50, "peru": 50, "colombia": 55,
    "marruecos": 45, "túnez": 42, "tunez": 42, "argelia": 58, "egipto": 62,
    "jordania": 40, "líbano": 70, "libano": 70, "palestina": 72,
    "etiopía": 65, "etiopia": 65, "kenya": 55, "tanzania": 48,
    "uganda": 55, "ruanda": 35, "ghana": 38, "senegal": 40,
    "no especificado": 70,
}
VULNERABILIDAD_DEFAULT = 55


class CalculadorICR:
    """Índice de Concentración de Receptores (HHI normalizado 0-100)."""

    def calcular(self, df: pd.DataFrame, col_entidad="entidad",
                 col_importe="importe_eur") -> pd.DataFrame:
        if df.empty or col_entidad not in df.columns:
            return pd.DataFrame(columns=["entidad", "icr", "n_contratos", "importe_total"])

        df = df.copy()
        df[col_importe] = pd.to_numeric(df[col_importe], errors="coerce").fillna(0)
        total = df[col_importe].sum()
        if total == 0:
            return pd.DataFrame(columns=["entidad", "icr", "n_contratos", "importe_total"])

        grp = df.groupby(col_entidad)[col_importe].agg(["sum", "count"]).reset_index()
        grp.columns = ["entidad", "importe_total", "n_contratos"]
        grp["cuota"] = grp["importe_total"] / total
        hhi = float((grp["cuota"] ** 2).sum())
        # Normalizar HHI (0=perfectamente distribuido, 1=monopolio) → 0-100
        n = len(grp)
        hhi_min = 1 / n if n > 0 else 0
        icr_norm = (hhi - hhi_min) / (1 - hhi_min) * 100 if (1 - hhi_min) > 0 else 0
        grp["icr"] = round(icr_norm, 1)
        log.info(f"  ICR global: {icr_norm:.1f} (HHI={hhi:.4f}, n={n} entidades)")
        return grp[["entidad", "icr", "n_contratos", "importe_total"]]


class CalculadorSOG:
    """Score de Opacidad en la Gestión (0-100, mayor = más opaco)."""

    PESOS = {
        "es_ooii":              30,
        "ruptura_r2":           25,
        "ruptura_r3":           20,
        "sin_pais":             15,
        "adjudicacion_directa": 10,
    }

    def calcular_fila(self, row: pd.Series) -> float:
        score = 0
        score += self.PESOS["es_ooii"]              if row.get("es_ooii", False)              else 0
        score += self.PESOS["ruptura_r2"]            if row.get("ruptura_r2", False)            else 0
        score += self.PESOS["ruptura_r3"]            if row.get("ruptura_r3", False)            else 0
        score += self.PESOS["adjudicacion_directa"]  if row.get("adjudicacion_directa", False)  else 0
        pais = str(row.get("pais_region", "") or "")
        if not pais or pais.lower() in ("", "nan", "no especificado"):
            score += self.PESOS["sin_pais"]
        return min(100, score)

    def calcular(self, df: pd.DataFrame) -> pd.Series:
        return df.apply(self.calcular_fila, axis=1)


class CalculadorRES:
    """Riesgo por Eslabón de Corte (0-100, mayor = peor trazabilidad)."""

    def calcular(self, df: pd.DataFrame) -> pd.Series:
        if "eslabon_corte" not in df.columns:
            return pd.Series([50] * len(df))
        from src.trazabilidad_score import ESLABON_SCORE
        max_score = max(ESLABON_SCORE.values())
        return df["eslabon_corte"].apply(
            lambda e: round((1 - ESLABON_SCORE.get(int(e), 0) / max_score) * 100, 1)
        )


class CalculadorVIA:
    """Vulnerabilidad Institucional del país receptor (0-100)."""

    def calcular(self, df: pd.DataFrame, col_pais="pais_region") -> pd.Series:
        def _score(pais):
            if pd.isna(pais):
                return VULNERABILIDAD_DEFAULT
            pais_l = str(pais).lower().strip()
            for k, v in VULNERABILIDAD_PAIS.items():
                if k in pais_l:
                    return v
            return VULNERABILIDAD_DEFAULT
        return df[col_pais].apply(_score) if col_pais in df.columns else pd.Series([VULNERABILIDAD_DEFAULT] * len(df))


# ── API pública ───────────────────────────────────────────────────────────────

def calcular_scores_completos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula ICR, SOG, RES, VIA y score_riesgo compuesto por entidad.
    Retorna DataFrame con una fila por entidad.
    """
    if df.empty:
        return pd.DataFrame()

    calc_icr = CalculadorICR()
    calc_sog = CalculadorSOG()
    calc_res = CalculadorRES()
    calc_via = CalculadorVIA()

    df = df.copy()
    df["sog"] = calc_sog.calcular(df)
    df["res"] = calc_res.calcular(df)
    df["via"] = calc_via.calcular(df)

    # Score integrado por fila: ICR se aplica a nivel entidad
    df["score_fila"] = (
        df["sog"] * 0.35 +
        df["res"] * 0.30 +
        df["via"] * 0.20
    )

    # Agregar por entidad
    agg = df.groupby("entidad").agg(
        n_fondos=("importe_eur", "count"),
        importe_total=("importe_eur", "sum"),
        sog_medio=("sog", "mean"),
        res_medio=("res", "mean"),
        via_medio=("via", "mean"),
        score_medio=("score_fila", "mean"),
    ).reset_index()

    # ICR por entidad
    df_icr = calc_icr.calcular(df)
    if not df_icr.empty:
        agg = agg.merge(df_icr[["entidad", "icr"]], on="entidad", how="left")
    else:
        agg["icr"] = 50

    # Score final: 85% métricas propias + 15% ICR
    agg["score_riesgo"] = (
        agg["score_medio"] * 0.85 +
        agg["icr"].fillna(50) * 0.15
    ).round(1)

    agg["nivel_riesgo"] = pd.cut(
        agg["score_riesgo"],
        bins=[0, 25, 50, 75, 100],
        labels=["Bajo", "Medio", "Alto", "Crítico"],
        right=True,
    )

    log.info(f"  Scores calculados: {len(agg)} entidades")
    return agg


def generar_resumen_global(df_scores: pd.DataFrame) -> dict:
    if df_scores.empty:
        return {}
    return {
        "n_entidades":        len(df_scores),
        "score_medio":        round(df_scores["score_riesgo"].mean(), 1),
        "n_critico":          int((df_scores["nivel_riesgo"] == "Crítico").sum()),
        "n_alto":             int((df_scores["nivel_riesgo"] == "Alto").sum()),
        "n_medio":            int((df_scores["nivel_riesgo"] == "Medio").sum()),
        "n_bajo":             int((df_scores["nivel_riesgo"] == "Bajo").sum()),
        "entidad_mayor_riesgo": df_scores.loc[df_scores["score_riesgo"].idxmax(), "entidad"]
                                 if len(df_scores) > 0 else "",
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = pd.DataFrame([
        {"entidad": "PNUD", "importe_eur": 4_500_000, "pais_region": "Bolivia",
         "es_ooii": True, "ruptura_r1": True, "ruptura_r2": False, "ruptura_r3": False,
         "eslabon_corte": 3, "en_place": False, "adjudicacion_directa": False},
        {"entidad": "Consultoría XYZ", "importe_eur": 890_000, "pais_region": "Honduras",
         "es_ooii": False, "ruptura_r1": False, "ruptura_r2": True, "ruptura_r3": True,
         "eslabon_corte": 4, "en_place": False, "adjudicacion_directa": True},
    ])
    scores = calcular_scores_completos(df)
    print(scores[["entidad", "score_riesgo", "nivel_riesgo"]])
    print(generar_resumen_global(scores))