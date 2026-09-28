"""
tests/test_fix_dashboard.py
===========================
Tests de los arreglos de la rama fix/dashboard. Verifican que los campos
NUEVOS existen y son coherentes, y que los campos ANTERIORES siguen igual.
"""
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from main import app, DATA_PRO, _region_de  # noqa: E402

client = TestClient(app)
requiere_datos = pytest.mark.skipif(
    not (DATA_PRO / "analisis_completo.csv").exists(), reason="sin datos procesados"
)


@requiere_datos
def test_resumen_conserva_campos_anteriores():
    d = client.get("/api/resumen").json()
    for k in ("total_fondos", "total_eur", "score_trazabilidad_medio", "pct_r1", "pct_r2",
              "pct_r3", "distribucion_eslabones", "acumulativo_anual", "top_paises", "timestamp"):
        assert k in d


@requiere_datos
def test_rupturas_exclusivas_suman_100():
    rx = client.get("/api/resumen").json()["rupturas_exclusivas"]
    assert abs(rx["r1"] + rx["r2"] + rx["r3"] + rx["trazables"] - 100) < 0.5


@requiere_datos
def test_por_region_cubre_el_total():
    d = client.get("/api/resumen").json()
    total = sum(r["importe"] for r in d["por_region"])
    assert abs(total / 1e6 - d["total_eur"]) < 0.2


@requiere_datos
def test_anios_disponibles_son_los_de_los_datos():
    d = client.get("/api/resumen").json()
    assert d["anios_disponibles"] == sorted(int(a["año"]) for a in d["acumulativo_anual"])


@requiere_datos
def test_mensual_informa_granularidad():
    d = client.get("/api/mensual").json()
    assert d["granularidad"] in ("anual", "mensual")
    assert "total" in d and "region" in d and "sector" in d


@pytest.mark.parametrize("pais,region", [
    ("Malí", "África"), ("Mali", "África"), ("Níger", "África"), ("Mauritania", "África"),
    ("Perú", "América Latina"), ("Dominicana, Rep.", "América Latina"), ("Palestina", "MENA"), ("Población Refugiada Saharaui", "MENA"),
    ("Países en Vías de Desarrollo (No Especificado)", "Multipaís/Global"),
    ("América Latina y Caribe (No Especificado)", "Multipaís/Global"),
    ("Ucrania", "Otros"),
])
def test_region_de(pais, region):
    assert _region_de(pais) == region


def test_import_db_desde_src_sin_import_circular():
    """Reproduce el contexto de pipeline.py (src/ primero en sys.path)."""
    code = (
        "import sys; sys.path.insert(0, 'src'); "
        "from db import subir_procesados, DATA_PRO; "
        "from pathlib import Path; "
        "assert Path(DATA_PRO).resolve().parent.parent == Path('.').resolve() or str(DATA_PRO).startswith('/app'), DATA_PRO; "
        "print('ok')"
    )
    r = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
