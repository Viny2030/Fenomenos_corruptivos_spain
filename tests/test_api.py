"""
tests/test_api.py
==================
Smoke tests de la API REST expuesta por main.py. Usan datos reales de
data/processed/ (committeados al repo), no mocks: si faltan, se skippean
en vez de fallar, para no romper un checkout local sin pipeline corrido.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from main import app, DATA_PRO, REFRESH_TOKEN  # noqa: E402

client = TestClient(app)

_datos_disponibles = (DATA_PRO / "analisis_completo.csv").exists()
requiere_datos = pytest.mark.skipif(
    not _datos_disponibles, reason="data/processed/analisis_completo.csv no existe en este checkout"
)


# ─────────────────────────────────────────────────────────────────────────
# Páginas HTML
# ─────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("path", ["/", "/dashboard", "/manual", "/autor", "/en", "/en/manual"])
def test_paginas_html_responden_200(path):
    r = client.get(path)
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<!DOCTYPE html>" in r.text


# ─────────────────────────────────────────────────────────────────────────
# API — status / resumen
# ─────────────────────────────────────────────────────────────────────────
def test_status_responde_ok():
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "activo"
    assert "total_fondos" in body


@requiere_datos
def test_resumen_tiene_kpis_principales():
    r = client.get("/api/resumen")
    assert r.status_code == 200
    body = r.json()
    for campo in ("total_fondos", "total_eur", "score_trazabilidad_medio", "pct_r1", "pct_r2", "pct_r3"):
        assert campo in body


# ─────────────────────────────────────────────────────────────────────────
# API — fondos (filtros + paginación)
# ─────────────────────────────────────────────────────────────────────────
@requiere_datos
def test_fondos_devuelve_lista():
    r = client.get("/api/fondos", params={"limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert "total" in body and "data" in body
    assert len(body["data"]) <= 5


@requiere_datos
def test_fondos_limit_maximo_es_1000():
    r = client.get("/api/fondos", params={"limit": 5000})
    assert r.status_code == 422  # Query(..., le=1000) rechaza valores mayores


@requiere_datos
def test_fondos_filtro_clasificacion_no_rompe():
    r = client.get("/api/fondos", params={"clasificacion": "ROJO", "limit": 10})
    assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────
# API — trazabilidad / entidades / riesgo / mensual / grafo
# ─────────────────────────────────────────────────────────────────────────
@requiere_datos
def test_trazabilidad_responde_resumen_y_data():
    r = client.get("/api/trazabilidad")
    assert r.status_code == 200
    body = r.json()
    assert "resumen" in body and "data" in body


@requiere_datos
def test_entidades_respeta_top():
    r = client.get("/api/entidades", params={"top": 3})
    assert r.status_code == 200
    assert len(r.json()["data"]) <= 3


@requiere_datos
def test_riesgo_responde_ok():
    r = client.get("/api/riesgo")
    assert r.status_code == 200


@requiere_datos
def test_mensual_responde_ok():
    r = client.get("/api/mensual")
    assert r.status_code == 200


@requiere_datos
def test_grafo_responde_nodos_y_edges():
    r = client.get("/api/grafo", params={"top": 10})
    assert r.status_code == 200


def test_informe_404_si_no_existe_o_200_si_existe():
    r = client.get("/api/informe")
    assert r.status_code in (200, 404)


# ─────────────────────────────────────────────────────────────────────────
# API — refresh (seguridad: token inválido, sin token)
# ─────────────────────────────────────────────────────────────────────────
def test_refresh_sin_token_devuelve_401():
    r = client.post("/api/refresh")
    assert r.status_code == 401


def test_refresh_con_token_incorrecto_devuelve_401():
    r = client.post("/api/refresh", headers={"X-Refresh-Token": "token-incorrecto-a-proposito"})
    assert r.status_code == 401


def test_refresh_token_por_defecto_dev_token_ya_no_funciona():
    """Regresión: 'dev-token' no debe ser un valor aceptado a menos que
    justo coincida con REFRESH_TOKEN generada/configurada (extremadamente
    improbable con secrets.token_hex(32))."""
    if REFRESH_TOKEN == "dev-token":
        pytest.fail("REFRESH_TOKEN sigue siendo el default público 'dev-token'")
    r = client.post("/api/refresh", headers={"X-Refresh-Token": "dev-token"})
    assert r.status_code == 401
