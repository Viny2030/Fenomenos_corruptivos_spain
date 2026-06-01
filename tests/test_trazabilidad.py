"""
tests/test_trazabilidad.py
"""
import sys
from pathlib import Path
import pandas as pd
import pytest

# Agregar raíz del proyecto y src al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from trazabilidad_score import ModeloTrazabilidad, ESLABON_SCORE, ESLABONES, OOII_CAJA_NEGRA
from indicadores_riesgo import (
    CalculadorICR, CalculadorSOG, CalculadorRES, CalculadorVIA,
    calcular_scores_completos, generar_resumen_global,
)


@pytest.fixture
def fondo_ooii():
    return pd.Series({
        "id": "F1", "titulo": "Programa agua Bolivia", "entidad": "PNUD",
        "importe_eur": 4_500_000, "pais_region": "Bolivia",
        "en_place": False, "adjudicacion_directa": False,
    })

@pytest.fixture
def fondo_consultora():
    return pd.Series({
        "id": "F2", "titulo": "Consultoría gobernabilidad", "entidad": "Consultoría XYZ S.L.",
        "importe_eur": 890_000, "pais_region": "Honduras",
        "en_place": False, "adjudicacion_directa": True,
    })

@pytest.fixture
def df_test():
    return pd.DataFrame([
        {"id": "F1", "titulo": "Agua Bolivia", "entidad": "PNUD",
         "importe_eur": 4_500_000, "pais_region": "Bolivia",
         "en_place": False, "adjudicacion_directa": False,
         "es_ooii": True, "ruptura_r1": True, "ruptura_r2": False, "ruptura_r3": False,
         "eslabon_corte": 3},
        {"id": "F2", "titulo": "Consultoría Honduras", "entidad": "Consultoría XYZ S.L.",
         "importe_eur": 890_000, "pais_region": "Honduras",
         "en_place": False, "adjudicacion_directa": True,
         "es_ooii": False, "ruptura_r1": False, "ruptura_r2": True, "ruptura_r3": True,
         "eslabon_corte": 4},
        {"id": "F3", "titulo": "Educación Guatemala completo", "entidad": "ONG España",
         "importe_eur": 250_000, "pais_region": "Guatemala",
         "en_place": True, "adjudicacion_directa": False,
         "es_ooii": False, "ruptura_r1": False, "ruptura_r2": False, "ruptura_r3": False,
         "eslabon_corte": 6},
    ])


def test_eslabon_score_creciente():
    scores = [ESLABON_SCORE[e] for e in sorted(ESLABON_SCORE)]
    assert scores == sorted(scores)

def test_eslabon_7_es_100():
    assert ESLABON_SCORE[7] == 100

def test_eslabon_1_es_menor_que_4():
    assert ESLABON_SCORE[1] < ESLABON_SCORE[4]

def test_todos_eslabones_definidos():
    assert set(ESLABONES.keys()) == set(ESLABON_SCORE.keys()) == set(range(1, 8))

def test_ooii_incluye_principales():
    for org in ["pnud", "unicef", "onu mujeres", "acnur", "pma", "fao"]:
        assert org in OOII_CAJA_NEGRA

def test_ooii_no_incluye_ongs():
    for org in ["medicos sin fronteras", "oxfam", "cruz roja"]:
        assert org not in OOII_CAJA_NEGRA

def test_ooii_detecta_r1(fondo_ooii):
    m = ModeloTrazabilidad()
    assert m._ruptura_r1(fondo_ooii) is True

def test_consultora_no_r1(fondo_consultora):
    m = ModeloTrazabilidad()
    assert m._ruptura_r1(fondo_consultora) is False

def test_ooii_eslabon_maximo_3(fondo_ooii):
    m = ModeloTrazabilidad()
    fondo_ooii["pais_region"] = "Bolivia"
    eslabon = m.calcular_eslabon(fondo_ooii)
    assert eslabon <= 3

def test_score_trazabilidad_rango():
    m = ModeloTrazabilidad()
    for e in range(1, 8):
        assert 0 <= m.score_trazabilidad(e) <= 100

def test_analizar_dataframe(df_test):
    m = ModeloTrazabilidad()
    df_in = df_test[["id","titulo","entidad","importe_eur","pais_region","en_place"]].copy()
    df_out = m.analizar_dataframe(df_in)
    assert "eslabon_corte"      in df_out.columns
    assert "score_trazabilidad" in df_out.columns
    assert "ruptura_r1"         in df_out.columns
    assert len(df_out) == len(df_in)

def test_resumen_global(df_test):
    m = ModeloTrazabilidad()
    df_in = df_test[["id","titulo","entidad","importe_eur","pais_region","en_place"]].copy()
    df_out = m.analizar_dataframe(df_in)
    resumen = m.resumen_global(df_out)
    assert "score_trazabilidad_medio" in resumen
    assert resumen["total_intervenciones"] == 3

def test_sog_ooii_alto():
    calc = CalculadorSOG()
    row = pd.Series({"es_ooii": True, "ruptura_r2": True, "ruptura_r3": True,
                     "adjudicacion_directa": False, "pais_region": "No Especificado"})
    assert calc.calcular_fila(row) >= 60

def test_sog_transparente_bajo():
    calc = CalculadorSOG()
    row = pd.Series({"es_ooii": False, "ruptura_r2": False, "ruptura_r3": False,
                     "adjudicacion_directa": False, "pais_region": "Bolivia"})
    assert calc.calcular_fila(row) == 0

def test_sog_maximo_100():
    calc = CalculadorSOG()
    row = pd.Series({"es_ooii": True, "ruptura_r2": True, "ruptura_r3": True,
                     "adjudicacion_directa": True, "pais_region": ""})
    assert calc.calcular_fila(row) <= 100

def test_icr_distribuido(df_test):
    calc = CalculadorICR()
    res = calc.calcular(df_test)
    assert len(res) == df_test["entidad"].nunique()
    assert (res["icr"] >= 0).all() and (res["icr"] <= 100).all()

def test_scores_completos_columnas(df_test):
    scores = calcular_scores_completos(df_test)
    for col in ["entidad","score_riesgo","nivel_riesgo","icr","sog_medio"]:
        assert col in scores.columns

def test_scores_rango(df_test):
    scores = calcular_scores_completos(df_test)
    assert (scores["score_riesgo"] >= 0).all()
    assert (scores["score_riesgo"] <= 100).all()

def test_resumen_global_keys(df_test):
    scores = calcular_scores_completos(df_test)
    resumen = generar_resumen_global(scores)
    for k in ["n_entidades","score_medio","n_critico","n_alto","n_bajo"]:
        assert k in resumen
    # Alias para compatibilidad
    ESLABONES = {
        1: "Presupuesto aprobado en España",
        2: "Transferencia AECID → entidad receptora",
        3: "Registro en OOII / BDNS",
        4: "Destino geográfico declarado",
        5: "Contratos publicados en PLACE/OCDS",
        6: "Justificantes y evaluaciones públicas",
        7: "Beneficiario final identificado",
    }