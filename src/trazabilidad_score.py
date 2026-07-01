"""
src/trazabilidad_score.py
=========================
Modelo de 7 eslabones para evaluar la trazabilidad de fondos AECID.
Detecta las tres rupturas principales (R1, R2, R3).
"""
import logging
import pandas as pd

log = logging.getLogger(__name__)

# ── Definición de eslabones ───────────────────────────────────────────────────
ESLABONES = {
    1: "Presupuesto aprobado en España",
    2: "Transferencia AECID → entidad receptora",
    3: "Registro en OOII / BDNS",
    4: "Destino geográfico declarado",
    5: "Contratos publicados en PLACE/OCDS",
    6: "Justificantes y evaluaciones públicas",
    7: "Beneficiario final identificado",
}

# Score de trazabilidad por eslabón de corte (mayor eslabón = mejor trazabilidad)
ESLABON_SCORE = {
    1: 14,
    2: 28,
    3: 42,
    4: 56,
    5: 70,
    6: 85,
    7: 100,
}

# Organismos internacionales que agregan sin desglosar (R1)
OOII_CAJA_NEGRA = {
    "pnud", "undp", "unicef", "onu mujeres", "unifem", "acnur", "unhcr",
    "pma", "wfp", "fao", "oms", "who", "ops/oms", "paho", "oim", "iom",
    "oit", "ilo", "banco mundial", "world bank", "bid", "iadb",
    "fondo mundial", "gef", "fondo de adaptación",
}


class ModeloTrazabilidad:
    def __init__(self, df_place: pd.DataFrame = None,
                 df_ltaibg: pd.DataFrame = None,
                 umbral_r3: float = 500_000):
        self.df_place  = df_place  if df_place  is not None else pd.DataFrame()
        self.df_ltaibg = df_ltaibg if df_ltaibg is not None else pd.DataFrame()
        self.umbral_r3 = umbral_r3

        # Índices para búsqueda rápida
        self._ids_place = set(
            self.df_place.get("id_contrato", pd.Series()).dropna().astype(str)
        ) if not self.df_place.empty else set()

        # Proyectos con respuesta positiva LTAIBG
        self._ids_ltaibg_ok = set()
        if not self.df_ltaibg.empty and "proyecto" in self.df_ltaibg.columns:
            mask = self.df_ltaibg.get("tiene_justificante", pd.Series()).astype(str).str.upper() == "SI"
            self._ids_ltaibg_ok = set(self.df_ltaibg[mask]["proyecto"].astype(str))

    # ── Detección de rupturas ─────────────────────────────────────────────────

    def _es_ooii(self, entidad: str) -> bool:
        if pd.isna(entidad):
            return False
        return any(ooii in str(entidad).lower() for ooii in OOII_CAJA_NEGRA)

    def _ruptura_r1(self, row: pd.Series) -> bool:
        """R1: fondo cargado a OOII sin desglose posterior"""
        return self._es_ooii(row.get("entidad", ""))

    def _ruptura_r2(self, row: pd.Series) -> bool:
        """R2: sub-contratación sin publicación en PLACE/OCDS"""
        if self.df_place.empty:
            return False
        en_place = row.get("en_place", False)
        adj_directa = False
        if not self.df_place.empty and "adjudicacion_directa" in self.df_place.columns:
            matches = self.df_place[
                self.df_place["titulo"].str.lower().str.contains(
                    str(row.get("titulo", ""))[:20].lower(), na=False
                )
            ]
            if not matches.empty:
                adj_directa = matches["adjudicacion_directa"].any()
        return (not en_place) or adj_directa

    def _ruptura_r3(self, row: pd.Series) -> bool:
        """R3: sin justificante auditable para importes > umbral"""
        importe = float(row.get("importe_eur", 0) or 0)
        if importe < self.umbral_r3:
            return False
        proyecto = str(row.get("id", row.get("titulo", "")))
        return proyecto not in self._ids_ltaibg_ok

    # ── Cálculo del eslabón de corte ──────────────────────────────────────────

    def calcular_eslabon(self, row: pd.Series) -> int:
        """Devuelve el último eslabón alcanzado (1-7)."""
        # Eslabón 1: siempre alcanzado si hay registro
        eslabon = 1

        # Eslabón 2: entidad receptora identificada
        if row.get("entidad") and str(row.get("entidad")).strip():
            eslabon = 2

        # Eslabón 3: la entidad implementadora aparece como beneficiaria real
        # en una concesión BDNS (ver cruzar_con_aecid en scraper_bdns.py), o
        # es un dato de demostración (seed).
        # NOTA: antes se comparaba row["fuente"] contra ("BDNS", "datos.aecid.es/API",
        # "seed") -- pero la fuente real de producción es
        # "datos.aecid.es/lista-de-intervenciones", que nunca matcheaba esa
        # lista. En la práctica esto significaba que el eslabón 3 nunca se
        # alcanzaba con datos reales. Se corrige para depender del cruce
        # real con BDNS.
        if row.get("en_bdns", False) or row.get("id_bdns", "") or row.get("fuente", "") == "seed":
            eslabon = 3

        # Eslabón 4: destino geográfico declarado
        pais = str(row.get("pais_region", "") or "")
        if pais and pais not in ("", "nan", "No Especificado", "no especificado"):
            eslabon = 4

        # Ruptura R1: OOII caja negra — no pasa de eslabón 3
        if self._ruptura_r1(row):
            return min(eslabon, 3)

        # Eslabón 5: publicado en PLACE/OCDS
        if row.get("en_place", False):
            eslabon = 5
        elif self._ruptura_r2(row):
            return min(eslabon, 4)

        # Eslabón 6: tiene justificante o es monto bajo
        importe = float(row.get("importe_eur", 0) or 0)
        if not self._ruptura_r3(row):
            eslabon = 6

        # Eslabón 7: beneficiario final identificado (proxy: tiene CUIT/NIF o sub-beneficiario)
        if row.get("beneficiario_final") or row.get("nif_beneficiario"):
            eslabon = 7

        return eslabon

    def score_trazabilidad(self, eslabon: int) -> int:
        return ESLABON_SCORE.get(eslabon, ESLABON_SCORE[1])

    # ── API pública ───────────────────────────────────────────────────────────

    def analizar_fondo(self, row: pd.Series) -> dict:
        eslabon = self.calcular_eslabon(row)
        score   = self.score_trazabilidad(eslabon)
        return {
            "eslabon_corte":         eslabon,
            "nombre_eslabon":        ESLABONES.get(eslabon, ""),
            "score_trazabilidad":    score,
            "ruptura_r1":            self._ruptura_r1(row),
            "ruptura_r2":            self._ruptura_r2(row),
            "ruptura_r3":            self._ruptura_r3(row),
            "es_ooii":               self._es_ooii(row.get("entidad", "")),
        }

    def analizar_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        resultados = df.apply(self.analizar_fondo, axis=1, result_type="expand")
        return pd.concat([df.reset_index(drop=True), resultados], axis=1)

    def resumen_global(self, df: pd.DataFrame) -> dict:
        if df.empty:
            return {}
        total_eur = df["importe_eur"].sum() if "importe_eur" in df.columns else 0

        def _pct(col):
            n = int(df.get(col, pd.Series(dtype=bool)).sum())
            fondos = df[df.get(col, False)]["importe_eur"].sum() if "importe_eur" in df.columns else 0
            pct_n = round(n / len(df) * 100, 1) if len(df) else 0
            pct_f = round(fondos / total_eur * 100, 1) if total_eur else 0
            return n, pct_n, round(fondos / 1e6, 1), pct_f

        n_r1, pct_r1, m_r1, pct_eur_r1 = _pct("ruptura_r1")
        n_r2, pct_r2, m_r2, pct_eur_r2 = _pct("ruptura_r2")
        n_r3, pct_r3, m_r3, pct_eur_r3 = _pct("ruptura_r3")

        return {
            "total_intervenciones":       len(df),
            "total_eur":                  round(total_eur / 1e6, 1),
            "score_trazabilidad_medio":   round(df["score_trazabilidad"].mean(), 1) if "score_trazabilidad" in df.columns else 0,
            "n_ruptura_r1":               n_r1,
            "pct_fondos_r1":              pct_eur_r1,
            "n_ruptura_r2":               n_r2,
            "pct_fondos_r2":              pct_eur_r2,
            "n_ruptura_r3":               n_r3,
            "pct_fondos_r3":              pct_eur_r3,
            "distribucion_eslabones":     df["eslabon_corte"].value_counts().to_dict() if "eslabon_corte" in df.columns else {},
        }


# ── Tests rápidos ─────────────────────────────────────────────────────────────
ESLABON_SCORE_REF = ESLABON_SCORE  # alias para los tests

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df_test = pd.DataFrame([
        {"id": "1", "titulo": "Agua Bolivia", "entidad": "PNUD",
         "importe_eur": 4_500_000, "pais_region": "Bolivia"},
        {"id": "2", "titulo": "Consultoría Honduras", "entidad": "Consultoría XYZ S.L.",
         "importe_eur": 890_000, "pais_region": "Honduras"},
    ])
    modelo = ModeloTrazabilidad()
    df_out = modelo.analizar_dataframe(df_test)
    print(df_out[["titulo", "entidad", "eslabon_corte", "score_trazabilidad", "ruptura_r1", "ruptura_r2", "ruptura_r3"]])
    print("\nResumen:")
    print(modelo.resumen_global(df_out))
