"""
main.py — FastAPI Monitor Trazabilidad AECID
Ph.D. Monteverde — Algoritmos contra la Corrupción

Endpoints UI:
  GET  /                    → dashboard HTML

Endpoints API:
  GET  /api/status          → estado del servicio
  GET  /api/resumen         → KPIs ejecutivos
  GET  /api/fondos          → tabla de fondos con filtros
  GET  /api/trazabilidad    → análisis por eslabón
  GET  /api/entidades       → ranking de entidades receptoras
  GET  /api/riesgo          → scores de riesgo por entidad
  GET  /api/informe         → informe ejecutivo en markdown
  POST /api/refresh         → dispara pipeline (requiere token)
"""

from dotenv import load_dotenv
load_dotenv()

import glob
import os
import sys
import subprocess
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

ROOT     = Path(__file__).parent
DATA_DIR = Path("/app/data") if Path("/app").exists() else ROOT / "data"
DATA_PRO = DATA_DIR / "processed"
REPORTS  = ROOT / "reports"
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN", "dev-token")

# ─────────────────────────────────────────────────────────────────────────────
# LIFESPAN
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA_PRO.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    # Railway resetea el filesystem en cada deploy: si hay PostgreSQL
    # configurada, restauramos los CSVs procesados desde la DB.
    try:
        sys.path.insert(0, str(ROOT / "src"))
        from db import restaurar_procesados, db_disponible
        if db_disponible():
            n = restaurar_procesados(solo_si_faltan=True)
            print(f"✅ DB PostgreSQL conectada — {n} archivos restaurados")
        else:
            print("ℹ️ Sin DATABASE_URL — usando solo CSVs locales")
    except Exception as e:
        print(f"⚠️ Restauración desde DB falló (no fatal): {e}")
    print("✅ Monitor AECID arrancando")
    yield

app = FastAPI(
    title="Monitor Trazabilidad AECID — Ph.D. Monteverde",
    description="Algoritmos contra la Corrupción — Trazabilidad de Fondos AECID",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if (ROOT / "static").exists():
    app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")

# ─────────────────────────────────────────────────────────────────────────────
# CACHE Y HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_cache: dict = {"fondos": None, "traz": None, "scores": None, "ts": None}


def _cargar_fondos() -> pd.DataFrame:
    if _cache["fondos"] is not None:
        return _cache["fondos"]
    p = DATA_PRO / "analisis_completo.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p).fillna("")
    _cache["fondos"] = df
    _cache["ts"] = datetime.now().isoformat()
    return df


def _cargar_trazabilidad() -> pd.DataFrame:
    if _cache["traz"] is not None:
        return _cache["traz"]
    p = DATA_PRO / "trazabilidad_por_fondo.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p).fillna("")
    _cache["traz"] = df
    return df


def _cargar_scores() -> pd.DataFrame:
    if _cache["scores"] is not None:
        return _cache["scores"]
    p = DATA_PRO / "scores_riesgo.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p).fillna("")
    _cache["scores"] = df
    return df


def _invalidar_cache():
    _cache["fondos"] = None
    _cache["traz"]   = None
    _cache["scores"] = None
    _cache["ts"]     = None


def _parsear_monto(v) -> float:
    try:
        return float(str(v).replace(",", ".").replace(" ", ""))
    except Exception:
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD HTML
# ─────────────────────────────────────────────────────────────────────────────


DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Monitor Trazabilidad AECID</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Segoe UI',sans-serif;background:#0f1117;color:#e0e0e0}
  header{background:#1a1d2e;padding:18px 28px;border-bottom:2px solid #2d3561;display:flex;align-items:center;justify-content:space-between}
  header h1{font-size:1.3rem;color:#fff}
  header span{font-size:0.8rem;color:#7c8db5}
  .badge{background:#2d3561;color:#7eb8f7;padding:3px 10px;border-radius:12px;font-size:0.75rem}
  main{padding:20px 28px;max-width:1400px;margin:0 auto}
  .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:24px}
  .kpi{background:#1a1d2e;border:1px solid #2d3561;border-radius:10px;padding:16px}
  .kpi .val{font-size:1.8rem;font-weight:700;color:#7eb8f7}
  .kpi .lbl{font-size:0.75rem;color:#7c8db5;margin-top:4px}
  .kpi.alerta .val{color:#f87171}
  .kpi.medio .val{color:#fbbf24}
  .kpi.ok .val{color:#34d399}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:20px}
  .grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px;margin-bottom:20px}
  .card{background:#1a1d2e;border:1px solid #2d3561;border-radius:10px;padding:18px}
  .card h3{font-size:0.85rem;color:#a0aec0;margin-bottom:12px;text-transform:uppercase;letter-spacing:.05em}
  .chart-wrap{position:relative;height:220px}
  .chart-wrap.tall{height:280px}
  table{width:100%;border-collapse:collapse;font-size:0.82rem}
  th{text-align:left;padding:7px 9px;color:#7c8db5;border-bottom:1px solid #2d3561;font-weight:600}
  td{padding:7px 9px;border-bottom:1px solid #1e2235}
  tr:hover td{background:#1e2235}
  .pill{padding:2px 8px;border-radius:10px;font-size:0.72rem;font-weight:600}
  .ROJO{background:#7f1d1d;color:#fca5a5}
  .NARANJA{background:#78350f;color:#fcd34d}
  .AMARILLO{background:#713f12;color:#fde68a}
  .VERDE{background:#14532d;color:#86efac}
  .Alto{background:#7f1d1d;color:#fca5a5}
  .Crítico{background:#581c87;color:#d8b4fe}
  .Medio{background:#78350f;color:#fcd34d}
  .Bajo{background:#14532d;color:#86efac}
  .bar-wrap{margin:6px 0}
  .bar-label{display:flex;justify-content:space-between;font-size:0.75rem;color:#a0aec0;margin-bottom:3px}
  .bar-bg{background:#2d3561;border-radius:4px;height:7px}
  .bar-fill{height:7px;border-radius:4px}
  .r1{background:#f87171}
  .r2{background:#fbbf24}
  .r3{background:#fb923c}
  .filters{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
  .filters input,.filters select{background:#0f1117;border:1px solid #2d3561;color:#e0e0e0;padding:5px 10px;border-radius:6px;font-size:0.82rem}
  .tabs{display:flex;gap:4px;margin-bottom:14px}
  .tab{padding:5px 14px;border-radius:6px;border:1px solid #2d3561;cursor:pointer;font-size:0.8rem;color:#a0aec0;background:#0f1117}
  .tab.active{background:#2d3561;color:#fff}
  footer{text-align:center;padding:16px;color:#4a5568;font-size:0.75rem;border-top:1px solid #1a1d2e;margin-top:24px}
  @media(max-width:900px){.grid2,.grid3{grid-template-columns:1fr}}
</style>
</head>
<body>
<header>
  <div>
    <h1>🔍 Monitor Trazabilidad AECID</h1>
    <span>Ph.D. Vicente Humberto Monteverde — Algoritmos contra la Corrupción</span>
  </div>
  <span class="badge" id="ts">Cargando...</span>
</header>

<!-- Banner Ley de Transparencia -->
<div style="background:#1e3a5f;border-bottom:1px solid #2d5f8f;padding:9px 28px;display:flex;align-items:center;gap:10px;font-size:0.78rem;color:#93c5fd">
  <span style="font-size:1rem">⚖️</span>
  <span>
    Este análisis se ejerce bajo la <strong style="color:#7eb8f7">Ley 19/2013 de Transparencia, Acceso a la Información Pública y Buen Gobierno</strong>.
    Cualquier ciudadano puede solicitar información a la AECID en
    <a href="https://transparencia.gob.es/transparencia/transparencia_Home/index/Solicitar-Informacion.html" target="_blank" style="color:#60a5fa;font-weight:600">transparencia.gob.es</a>
    o a través del <a href="https://www.aecid.es/ES/la-aecid/transparencia" target="_blank" style="color:#60a5fa;font-weight:600">portal de transparencia AECID</a>.
  </span>
  <div style="margin-left:auto;display:flex;gap:8px;white-space:nowrap"><a href="#indicadores-internacionales" style="background:#2d5f8f;color:#e0f2fe;padding:4px 12px;border-radius:6px;font-size:0.75rem;border:1px solid #60a5fa">📊 Indicadores →</a><a href="/manual" style="background:#2d5f8f;color:#e0f2fe;padding:4px 12px;border-radius:6px;font-size:0.75rem;border:1px solid #60a5fa">📖 Manual →</a></div>
</div>

<main>

  <!-- KPIs -->
  <div class="kpis" id="kpis"></div>

  <!-- Fila 1: Rupturas + Eslabones -->
  <div class="grid2">
    <div class="card">
      <h3>🔗 Rupturas de trazabilidad</h3>
      <div id="rupturas"></div>
      <div class="chart-wrap" style="height:160px;margin-top:12px">
        <canvas id="chartRupturas"></canvas>
      </div>
    </div>
    <div class="card">
      <h3>📊 Distribución por eslabón</h3>
      <div class="chart-wrap"><canvas id="chartEslabones"></canvas></div>
    </div>
  </div>

  <!-- Fila 2: Evolución anual acumulada + por región mensual -->
  <div class="grid2">
    <div class="card">
      <h3>📈 Evolución anual acumulada (M€)</h3>
      <div class="chart-wrap tall"><canvas id="chartAnual"></canvas></div>
    </div>
    <div class="card">
      <h3>🌍 Distribución por región (M€)</h3>
      <div class="chart-wrap tall"><canvas id="chartRegion"></canvas></div>
    </div>
  </div>

  <!-- Fila 3: Top países + evolución mensual -->
  <div class="grid2">
    <div class="card">
      <h3>🗺️ Top países por importe</h3>
      <div class="chart-wrap tall"><canvas id="chartPaises"></canvas></div>
    </div>
    <div class="card">
      <h3>📆 Evolución mensual por región</h3>
      <div class="tabs" id="tabsRegion"></div>
      <div class="chart-wrap tall"><canvas id="chartMensual"></canvas></div>
    </div>
  </div>

  <!-- Fila 4: Gráficos trazabilidad adicionales -->
  <div class="grid3" style="margin-bottom:20px">
    <div class="card">
      <h3>📊 Clasificación de riesgo</h3>
      <div class="chart-wrap"><canvas id="chartClasif"></canvas></div>
    </div>
    <div class="card">
      <h3>🎯 Score trazabilidad por eslabón</h3>
      <div class="chart-wrap"><canvas id="chartScoreEslabon"></canvas></div>
    </div>
    <div class="card">
      <h3>🔬 Sector CRS — distribución</h3>
      <div class="chart-wrap"><canvas id="chartSector"></canvas></div>
    </div>
  </div>

  <!-- Fila 5: Cards de fondos con rendición de cuentas -->
  <div class="card" style="margin-bottom:20px">
    <h3>📋 Rendición de cuentas — Fondos ROJO y NARANJA</h3>
    <p style="font-size:0.78rem;color:#7c8db5;margin-bottom:14px">Todos los fondos con rupturas de trazabilidad detectadas · <span id="total-cards"></span></p>
    <div id="cards-fondos" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px"></div>
  </div>

  <!-- Panel: Indicadores Internacionales -->
  <div class="card" style="margin-bottom:20px" id="indicadores-internacionales">
    <h3>🌐 Indicadores internacionales de referencia</h3>
    <p style="font-size:0.78rem;color:#7c8db5;margin-bottom:16px">Estándares y benchmarks globales aplicados al análisis de subvenciones, subsidios y cooperación internacional</p>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px" id="panel-indicadores">

      <div style="background:#0f1117;border:1px solid #2d3561;border-radius:10px;padding:16px">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <span style="font-size:1.1rem">🏦</span>
          <strong style="font-size:0.85rem;color:#7eb8f7">OCDE — CRS Creditor Reporting</strong>
        </div>
        <p style="font-size:0.78rem;color:#c0c8d8;margin-bottom:8px">Sistema de reporte de ayuda oficial al desarrollo. Clasifica sectores (códigos CRS), canales y tipos de flujo. España reporta ~4.500M€/año.</p>
        <div style="font-size:0.75rem;color:#7c8db5;margin-bottom:8px"><strong style="color:#a0aec0">Umbrales de alerta:</strong> concentración en un canal &gt;40%, variación interanual &gt;30%</div>
        <a href="https://stats.oecd.org/Index.aspx?DataSetCode=CRS1" target="_blank" style="color:#60a5fa;font-size:0.75rem">→ Base de datos OCDE CRS</a>
      </div>

      <div style="background:#0f1117;border:1px solid #2d3561;border-radius:10px;padding:16px">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <span style="font-size:1.1rem">📡</span>
          <strong style="font-size:0.85rem;color:#7eb8f7">IATI — International Aid Transparency</strong>
        </div>
        <p style="font-size:0.78rem;color:#c0c8d8;margin-bottom:8px">Estándar XML open data para publicación de actividades de cooperación. Exige desglose por donante, receptor, actividad y geografía hasta nivel de transacción.</p>
        <div style="font-size:0.75rem;color:#7c8db5;margin-bottom:8px"><strong style="color:#a0aec0">Gap España:</strong> AECID publica a nivel de programa, no de transacción individual</div>
        <a href="https://iatistandard.org/en/" target="_blank" style="color:#60a5fa;font-size:0.75rem">→ IATI Standard</a>
      </div>

      <div style="background:#0f1117;border:1px solid #2d3561;border-radius:10px;padding:16px">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <span style="font-size:1.1rem">📋</span>
          <strong style="font-size:0.85rem;color:#7eb8f7">OCDS — Open Contracting Data Standard</strong>
        </div>
        <p style="font-size:0.78rem;color:#c0c8d8;margin-bottom:8px">Estándar abierto para publicación de contratos públicos en todas sus fases: planificación, licitación, adjudicación, contrato y ejecución.</p>
        <div style="font-size:0.75rem;color:#7c8db5;margin-bottom:8px"><strong style="color:#a0aec0">Gap España:</strong> PLACE publica adjudicación pero no ejecución ni pagos efectivos</div>
        <a href="https://standard.open-contracting.org/" target="_blank" style="color:#60a5fa;font-size:0.75rem">→ Open Contracting</a>
      </div>

      <div style="background:#0f1117;border:1px solid #2d3561;border-radius:10px;padding:16px">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <span style="font-size:1.1rem">🏛️</span>
          <strong style="font-size:0.85rem;color:#7eb8f7">WGI — Worldwide Governance Indicators</strong>
        </div>
        <p style="font-size:0.78rem;color:#c0c8d8;margin-bottom:8px">Banco Mundial. 6 dimensiones: voz/rendición, estabilidad, efectividad, calidad regulatoria, rule of law, control de corrupción. Proxy para el indicador VIA.</p>
        <div style="font-size:0.75rem;color:#7c8db5;margin-bottom:8px"><strong style="color:#a0aec0">En este sistema:</strong> VIA = 100 − WGI_control_corrupción del país receptor</div>
        <a href="https://info.worldbank.org/governance/wgi/" target="_blank" style="color:#60a5fa;font-size:0.75rem">→ WGI Banco Mundial</a>
      </div>

      <div style="background:#0f1117;border:1px solid #2d3561;border-radius:10px;padding:16px">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <span style="font-size:1.1rem">🔎</span>
          <strong style="font-size:0.85rem;color:#7eb8f7">IPC — Índice de Percepción de Corrupción</strong>
        </div>
        <p style="font-size:0.78rem;color:#c0c8d8;margin-bottom:8px">Transparency International. Escala 0 (muy corrupto) a 100 (muy limpio). Complementa el WGI para evaluar el riesgo del país receptor de los fondos.</p>
        <div style="font-size:0.75rem;color:#7c8db5;margin-bottom:8px"><strong style="color:#a0aec0">Alerta:</strong> fondos a países con IPC &lt;40 sin mecanismo de verificación adicional</div>
        <a href="https://www.transparency.org/en/cpi" target="_blank" style="color:#60a5fa;font-size:0.75rem">→ Transparency International CPI</a>
      </div>

      <div style="background:#0f1117;border:1px solid #2d3561;border-radius:10px;padding:16px">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <span style="font-size:1.1rem">🇪🇺</span>
          <strong style="font-size:0.85rem;color:#7eb8f7">OLAF — Oficina Europea Antifraude</strong>
        </div>
        <p style="font-size:0.78rem;color:#c0c8d8;margin-bottom:8px">Protege los intereses financieros de la UE. Investiga fraude, corrupción y mala conducta en fondos europeos. Publica informes anuales con estadísticas por Estado miembro.</p>
        <div style="font-size:0.75rem;color:#7c8db5;margin-bottom:8px"><strong style="color:#a0aec0">Relevancia:</strong> fondos FEDER/FSE que canalizan AECID tienen obligación adicional de auditoría OLAF</div>
        <a href="https://anti-fraud.ec.europa.eu/" target="_blank" style="color:#60a5fa;font-size:0.75rem">→ OLAF Europa</a>
      </div>

      <div style="background:#0f1117;border:1px solid #2d3561;border-radius:10px;padding:16px">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <span style="font-size:1.1rem">📊</span>
          <strong style="font-size:0.85rem;color:#7eb8f7">HHI — Índice Herfindahl-Hirschman (ICR)</strong>
        </div>
        <p style="font-size:0.78rem;color:#c0c8d8;margin-bottom:8px">Mide concentración de mercado. Adaptado aquí para concentración de receptores: suma de cuadrados de cuotas de cada entidad. Rango 0 (máx. dispersión) a 10.000 (monopolio).</p>
        <div style="font-size:0.75rem;color:#7c8db5;margin-bottom:8px"><strong style="color:#a0aec0">Umbral ICR:</strong> HHI normalizado &gt;0,25 → concentración preocupante en un receptor</div>
        <a href="https://www.justice.gov/atr/herfindahl-hirschman-index" target="_blank" style="color:#60a5fa;font-size:0.75rem">→ DOJ — HHI reference</a>
      </div>

      <div style="background:#0f1117;border:1px solid #2d3561;border-radius:10px;padding:16px">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <span style="font-size:1.1rem">⚖️</span>
          <strong style="font-size:0.85rem;color:#7eb8f7">LTAIBG — Ley 19/2013 de Transparencia</strong>
        </div>
        <p style="font-size:0.78rem;color:#c0c8d8;margin-bottom:8px">Marco legal español de acceso a la información pública. Permite a cualquier ciudadano solicitar documentos de subvenciones, evaluaciones y contratos de la AECID sin justificación.</p>
        <div style="font-size:0.75rem;color:#7c8db5;margin-bottom:8px"><strong style="color:#a0aec0">Indicador R3:</strong> proyectos &gt;500K€ sin respuesta favorable = ruptura de justificación</div>
        <a href="https://www.boe.es/buscar/act.php?id=BOE-A-2013-12887" target="_blank" style="color:#60a5fa;font-size:0.75rem">→ BOE — Ley 19/2013</a>
      </div>

    </div>
  </div>

  <!-- Fila 6: Entidades -->
  <div class="card" style="margin-bottom:18px">
    <h3>🏢 Ranking entidades por riesgo</h3>
    <div class="filters">
      <input id="busq-entidad" placeholder="Buscar..." oninput="filtrarEntidades()">
      <select id="filtro-nivel" onchange="filtrarEntidades()">
        <option value="">Todos los niveles</option>
        <option>Crítico</option><option>Alto</option><option>Medio</option><option>Bajo</option>
      </select>
    </div>
    <table id="tabla-entidades">
      <thead><tr><th>Entidad</th><th>Score</th><th>Nivel</th><th>Fondos</th><th>Importe</th><th>SOG</th><th>ICR</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>

  <!-- Fila 5: Fondos -->
  <div class="card">
    <h3>📋 Fondos analizados</h3>
    <div class="filters">
      <input id="busq-fondo" placeholder="Buscar fondo o entidad..." oninput="filtrarFondos()">
      <select id="filtro-clasif" onchange="filtrarFondos()">
        <option value="">Todas las clasificaciones</option>
        <option>ROJO</option><option>NARANJA</option><option>AMARILLO</option><option>VERDE</option>
      </select>
      <select id="filtro-eslabon" onchange="filtrarFondos()">
        <option value="">Todos los eslabones</option>
        <option value="3">E3 — OOII sin desglose</option>
        <option value="4">E4 — Destino opaco</option>
        <option value="5">E5 — Sin PLACE</option>
        <option value="6">E6 — Sin justificante</option>
        <option value="7">E7 — Completo</option>
      </select>
      <select id="filtro-año" onchange="filtrarFondos()">
        <option value="">Todos los años</option>
        <option>2021</option><option>2022</option><option>2023</option><option>2024</option>
      </select>
    </div>
    <table id="tabla-fondos">
      <thead><tr><th>Título</th><th>Entidad</th><th>País</th><th>Año</th><th>Importe</th><th>Eslabón</th><th>Trazabilidad</th><th>Clasif.</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
</main>
<footer>Monitor AECID v2.0 · github.com/Viny2030/Fenomenos_corruptivos_spain · Actualización diaria via GitHub Actions</footer>

<script>
const COLORS = ['#3b82f6','#f87171','#fbbf24','#34d399','#a78bfa','#fb923c','#60a5fa','#f472b6','#4ade80','#facc15'];
const REGION_COLORS = {
  'latam':'#34d399','multipaís':'#a78bfa','mena':'#fbbf24','africa':'#f87171',
  'asia':'#60a5fa','otros':'#fb923c',
  'América Latina':'#34d399','Multipaís/Global':'#a78bfa','MENA':'#fbbf24','África':'#f87171'
};

let _entidades=[], _fondos=[], _mensualData={}, _chartMensual=null;

function mkChart(id, type, labels, datasets, opts={}) {
  const ctx = document.getElementById(id);
  if (!ctx) return null;
  if (ctx._chart) ctx._chart.destroy();
  const c = new Chart(ctx, {
    type,
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color:'#a0aec0', font:{size:11} } } },
      scales: type !== 'pie' && type !== 'doughnut' ? {
        x: { ticks:{color:'#7c8db5',font:{size:10}}, grid:{color:'#1e2235'} },
        y: { ticks:{color:'#7c8db5',font:{size:10}}, grid:{color:'#1e2235'} }
      } : {},
      ...opts
    }
  });
  ctx._chart = c;
  return c;
}

async function cargar() {
  const [res, ent, fond, mens] = await Promise.all([
    fetch('/api/resumen').then(r=>r.json()),
    fetch('/api/entidades?top=50').then(r=>r.json()),
    fetch('/api/fondos?limit=500').then(r=>r.json()),
    fetch('/api/mensual').then(r=>r.json()),
  ]);

  document.getElementById('ts').textContent = (res.timestamp||'').substring(0,16).replace('T',' ');

  // ── KPIs ──────────────────────────────────────────────────────────────────
  document.getElementById('kpis').innerHTML = [
    {val: res.total_fondos||0,                    lbl:'Total fondos',          cls:''},
    {val: `${res.total_eur||0}M€`,                lbl:'Total analizado',       cls:''},
    {val: `${res.score_trazabilidad_medio||0}/100`,lbl:'Score trazabilidad',   cls: (res.score_trazabilidad_medio||0)<50?'alerta':'ok'},
    {val: `${res.pct_r1||0}%`,                    lbl:'R1 — OOII caja negra',  cls:'alerta'},
    {val: `${res.pct_r2||0}%`,                    lbl:'R2 — Sin PLACE/OCDS',   cls:'medio'},
    {val: `${res.pct_r3||0}%`,                    lbl:'R3 — Sin justificante', cls:'medio'},
  ].map(k=>`<div class="kpi ${k.cls}"><div class="val">${k.val}</div><div class="lbl">${k.lbl}</div></div>`).join('');

  // ── Rupturas barras ────────────────────────────────────────────────────────
  document.getElementById('rupturas').innerHTML = [
    {lbl:'R1 — OOII caja negra',  pct:res.pct_r1||0, cls:'r1'},
    {lbl:'R2 — Sin contrato OCDS',pct:res.pct_r2||0, cls:'r2'},
    {lbl:'R3 — Sin justificante', pct:res.pct_r3||0, cls:'r3'},
  ].map(r=>`<div class="bar-wrap">
    <div class="bar-label"><span>${r.lbl}</span><span>${r.pct}%</span></div>
    <div class="bar-bg"><div class="bar-fill ${r.cls}" style="width:${r.pct}%"></div></div>
  </div>`).join('');

  // ── Gráfico rupturas doughnut ──────────────────────────────────────────────
  mkChart('chartRupturas','doughnut',
    ['R1 OOII','R2 Sin PLACE','R3 Sin justif.','Trazables'],
    [{data:[res.pct_r1,res.pct_r2,res.pct_r3,Math.max(0,100-res.pct_r1)],
      backgroundColor:['#f87171','#fbbf24','#fb923c','#34d399'],borderWidth:0}],
    {plugins:{legend:{position:'bottom',labels:{color:'#a0aec0',font:{size:10}}}}}
  );

  // ── Eslabones ──────────────────────────────────────────────────────────────
  const dist = res.distribucion_eslabones||{};
  const eslLabels = Object.keys(dist).sort().map(e=>`E${e}`);
  const eslValues = Object.keys(dist).sort().map(e=>dist[e]);
  mkChart('chartEslabones','bar',eslLabels,
    [{label:'Fondos por eslabón',data:eslValues,backgroundColor:COLORS,borderRadius:4}],
    {plugins:{legend:{display:false}}}
  );

  // ── Evolución anual acumulada ──────────────────────────────────────────────
  const acum = res.acumulativo_anual||[];
  mkChart('chartAnual','bar',
    acum.map(a=>String(a.año)),
    [
      {label:'Importe año (M€)',data:acum.map(a=>+(a.importe/1e6).toFixed(1)),
       backgroundColor:'#3b82f6',borderRadius:4,yAxisID:'y'},
      {label:'Acumulado (M€)',data:acum.map(a=>+(a.importe_acum/1e6).toFixed(1)),
       type:'line',borderColor:'#34d399',borderWidth:2,pointRadius:4,
       backgroundColor:'transparent',yAxisID:'y1'},
    ],
    {scales:{
      y:{position:'left',ticks:{color:'#7c8db5',font:{size:10}},grid:{color:'#1e2235'}},
      y1:{position:'right',ticks:{color:'#34d399',font:{size:10}},grid:{display:false}},
      x:{ticks:{color:'#7c8db5'},grid:{color:'#1e2235'}}
    },plugins:{legend:{labels:{color:'#a0aec0',font:{size:10}}}}}
  );

  // ── Distribución por región (de top_paises agrupado) ──────────────────────
  const topPaises = res.top_paises||[];
  // Agrupar en 5 regiones principales
  const regiones = {};
  topPaises.forEach(p=>{
    let reg = 'Otros';
    const n = p.pais_region||'';
    if (['Bolivia','Colombia','Ecuador','Guatemala','Honduras','México','Nicaragua','Perú','Cuba','Haití','Venezuela','El Salvador','Costa Rica','Panamá','Paraguay','Brasil','Chile','Argentina'].some(x=>n.includes(x))) reg='América Latina';
    else if (['Marruecos','Túnez','Argelia','Jordania','Líbano','Palestina','Siria','Irak','Yemen','Mediterráneo'].some(x=>n.includes(x))) reg='MENA';
    else if (['Etiopía','Mozambique','Mali','Niger','Senegal','Chad','Kenya','Tanzania','Uganda','Ghana','Mauritania','Burkina','África'].some(x=>n.includes(x))) reg='África';
    else if (['Global','Especificado','Multipaís','América Latina y Caribe'].some(x=>n.includes(x))) reg='Multipaís/Global';
    regiones[reg] = (regiones[reg]||0) + p.importe;
  });
  const regKeys = Object.keys(regiones);
  mkChart('chartRegion','doughnut', regKeys,
    [{data:regKeys.map(k=>+(regiones[k]/1e6).toFixed(1)),
      backgroundColor:regKeys.map(k=>REGION_COLORS[k]||'#6b7280'),borderWidth:0}],
    {plugins:{legend:{position:'bottom',labels:{color:'#a0aec0',font:{size:10}}}}}
  );

  // ── Top países horizontal bar ──────────────────────────────────────────────
  const top15 = topPaises.slice(0,15);
  mkChart('chartPaises','bar',
    top15.map(p=>p.pais_region||'').reverse(),
    [{label:'Importe (M€)',data:top15.map(p=>+(p.importe/1e6).toFixed(1)).reverse(),
      backgroundColor:top15.map((_,i)=>COLORS[i%COLORS.length]).reverse(),borderRadius:4}],
    {indexAxis:'y',plugins:{legend:{display:false}},
     scales:{x:{ticks:{color:'#7c8db5',font:{size:10}},grid:{color:'#1e2235'}},
             y:{ticks:{color:'#7c8db5',font:{size:9}},grid:{color:'#1e2235'}}}}
  );

  // ── Mensual por región ─────────────────────────────────────────────────────
  _mensualData = mens.region||{};
  const regiones_mens = Object.keys(_mensualData);
  // Render tabs
  document.getElementById('tabsRegion').innerHTML = regiones_mens.map((r,i)=>
    `<div class="tab ${i===0?'active':''}" onclick="switchRegion('${r}',this)">${r}</div>`
  ).join('');
  if (regiones_mens.length>0) renderMensual(regiones_mens[0]);

  // ── Entidades y fondos ────────────────────────────────────────────────────
  _entidades = ent.data||[];
  renderEntidades(_entidades);
  _fondos = fond.data||[];
  renderFondos(_fondos);

  // ── Clasificación ROJO/NARANJA/etc ────────────────────────────────────────
  const clasifCount = {ROJO:0, NARANJA:0, AMARILLO:0, VERDE:0};
  (_fondos).forEach(f=>{ if(clasifCount[f.clasificacion]!==undefined) clasifCount[f.clasificacion]++; });
  mkChart('chartClasif','doughnut',
    ['ROJO','NARANJA','AMARILLO','VERDE'],
    [{data:[clasifCount.ROJO,clasifCount.NARANJA,clasifCount.AMARILLO,clasifCount.VERDE],
      backgroundColor:['#ef4444','#f97316','#eab308','#22c55e'],borderWidth:0}],
    {plugins:{legend:{position:'bottom',labels:{color:'#a0aec0',font:{size:10}}}}}
  );

  // ── Score medio de trazabilidad por eslabón ───────────────────────────────
  const byEslabon = {};
  (_fondos).forEach(f=>{
    const e = 'E'+(f.eslabon_corte||'?');
    if(!byEslabon[e]) byEslabon[e]={sum:0,n:0};
    byEslabon[e].sum += (f.score_trazabilidad||0);
    byEslabon[e].n++;
  });
  const eslKeys = Object.keys(byEslabon).sort();
  mkChart('chartScoreEslabon','bar', eslKeys,
    [{label:'Score medio',data:eslKeys.map(k=>+(byEslabon[k].sum/byEslabon[k].n).toFixed(1)),
      backgroundColor:eslKeys.map(k=>{ const s=byEslabon[k].sum/byEslabon[k].n; return s<40?'#ef4444':s<60?'#f97316':s<80?'#eab308':'#22c55e'; }),
      borderRadius:4}],
    {plugins:{legend:{display:false}},
     scales:{y:{min:0,max:100,ticks:{color:'#7c8db5'},grid:{color:'#1e2235'}},
             x:{ticks:{color:'#7c8db5'},grid:{color:'#1e2235'}}}}
  );

  // ── Sector CRS ────────────────────────────────────────────────────────────
  const sectorMap = {};
  (_fondos).forEach(f=>{
    const s = f.ambito||'Sin sector';
    sectorMap[s] = (sectorMap[s]||0) + (f.importe_eur||0);
  });
  const sectorSort = Object.entries(sectorMap).sort((a,b)=>b[1]-a[1]).slice(0,8);
  mkChart('chartSector','doughnut',
    sectorSort.map(s=>s[0]),
    [{data:sectorSort.map(s=>+(s[1]/1e6).toFixed(1)),
      backgroundColor:['#3b82f6','#f87171','#fbbf24','#34d399','#a78bfa','#fb923c','#60a5fa','#f472b6'],borderWidth:0}],
    {plugins:{legend:{position:'bottom',labels:{color:'#a0aec0',font:{size:9}}}}}
  );

  // ── Cards de rendición de cuentas ─────────────────────────────────────────
  const fondosRiesgo = (_fondos)
    .filter(f=>f.clasificacion==='ROJO'||f.clasificacion==='NARANJA')
    .sort((a,b)=>(b.score_integrado||0)-(a.score_integrado||0))
    ; // sin límite — todos los ROJO y NARANJA

  document.getElementById('total-cards').textContent = fondosRiesgo.length + ' fondos con alertas';
  document.getElementById('cards-fondos').innerHTML = fondosRiesgo.map(f=>{
    const sc = f.score_trazabilidad||0;
    const scColor = sc<40?'#ef4444':sc<60?'#f97316':sc<80?'#eab308':'#22c55e';
    const r1 = f.ruptura_r1?'<span style="background:#7f1d1d;color:#fca5a5;padding:2px 7px;border-radius:8px;font-size:0.7rem;margin-right:4px">R1 OOII</span>':'';
    const r2 = f.ruptura_r2?'<span style="background:#78350f;color:#fcd34d;padding:2px 7px;border-radius:8px;font-size:0.7rem;margin-right:4px">R2 Sin PLACE</span>':'';
    const r3 = f.ruptura_r3?'<span style="background:#78350f;color:#fb923c;padding:2px 7px;border-radius:8px;font-size:0.7rem;margin-right:4px">R3 Sin justif.</span>':'';
    const tca = f.url_recurso
      ? '<a href="'+f.url_recurso+'" target="_blank" style="color:#60a5fa;font-size:0.75rem">🔗 Fuente AECID</a>'
      : '<span style="color:#4a5568;font-size:0.75rem">Sin fuente directa</span>';
    const tribunal = '<a href="https://www.tcu.es/tribunal-de-cuentas/es/buscador/?texto=AECID" target="_blank" style="color:#a78bfa;font-size:0.75rem">⚖️ Tribunal de Cuentas</a>';
    const bdns = '<a href="https://www.infosubvenciones.es/bdnstrans/GE/es/convocatorias?descripcion=AECID" target="_blank" style="color:#34d399;font-size:0.75rem">📋 BDNS</a>';
    return '<div style="background:#0f1117;border:1px solid #2d3561;border-radius:10px;padding:16px">'
      +'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">'
      +'<strong style="font-size:0.82rem;color:#e0e0e0;flex:1;margin-right:8px">'+(f.titulo||'').substring(0,55)+'…</strong>'
      +'<span class="pill '+f.clasificacion+'">'+f.clasificacion+'</span>'
      +'</div>'
      +'<div style="font-size:0.75rem;color:#7c8db5;margin-bottom:8px">'
      +'<span>🏢 '+f.entidad+'</span>'
      +' · <span>🌍 '+f.pais_region+'</span>'
      +' · <span>📅 '+(f.año||'')+'</span>'
      +' · <span>💶 '+((f.importe_eur||0)/1e6).toFixed(2)+'M€</span>'
      +'</div>'
      +'<div style="margin-bottom:8px">'
      +'<div style="display:flex;justify-content:space-between;font-size:0.72rem;color:#a0aec0;margin-bottom:3px">'
      +'<span>Trazabilidad · E'+f.eslabon_corte+' — '+(f.nombre_eslabon||'')+'</span>'
      +'<span style="color:'+scColor+'">'+sc+'/100</span></div>'
      +'<div style="background:#2d3561;border-radius:4px;height:6px">'
      +'<div style="height:6px;border-radius:4px;background:'+scColor+';width:'+sc+'%"></div>'
      +'</div></div>'
      +'<div style="margin-bottom:10px">'+r1+r2+r3+'</div>'
      +'<div style="display:flex;gap:12px;flex-wrap:wrap">'+tca+' '+tribunal+' '+bdns+'</div>'
      +'</div>';
  }).join('');
}

function renderMensual(region) {
  const data = _mensualData[region]||[];
  if (_chartMensual) _chartMensual.destroy();
  const ctx = document.getElementById('chartMensual');
  if (!ctx) return;
  _chartMensual = new Chart(ctx, {
    type:'line',
    data:{
      labels: data.map(d=>d.mes),
      datasets:[{
        label:`${region} (M€)`,
        data: data.map(d=>+(d.importe/1e6).toFixed(2)),
        borderColor: REGION_COLORS[region]||'#3b82f6',
        backgroundColor: (REGION_COLORS[region]||'#3b82f6')+'33',
        fill:true, tension:0.3, pointRadius:3,
      }]
    },
    options:{
      responsive:true, maintainAspectRatio:false,
      plugins:{legend:{labels:{color:'#a0aec0',font:{size:11}}}},
      scales:{
        x:{ticks:{color:'#7c8db5',font:{size:9}},grid:{color:'#1e2235'}},
        y:{ticks:{color:'#7c8db5',font:{size:10}},grid:{color:'#1e2235'}}
      }
    }
  });
}

function switchRegion(region, el) {
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
  renderMensual(region);
}

function renderEntidades(data) {
  document.querySelector('#tabla-entidades tbody').innerHTML = data.slice(0,30).map(e=>`<tr>
    <td>${e.entidad||''}</td>
    <td>${(e.score_riesgo||0).toFixed(1)}</td>
    <td><span class="pill ${e.nivel_riesgo||''}">${e.nivel_riesgo||''}</span></td>
    <td>${e.n_fondos||0}</td>
    <td>${((e.importe_total||0)/1e6).toFixed(1)}M€</td>
    <td>${(e.sog_medio||0).toFixed(0)}</td>
    <td>${(e.icr||0).toFixed(0)}</td>
  </tr>`).join('');
}

function renderFondos(data) {
  document.querySelector('#tabla-fondos tbody').innerHTML = data.slice(0,100).map(f=>`<tr>
    <td title="${f.titulo||''}">${(f.titulo||'').substring(0,40)}…</td>
    <td>${(f.entidad||'').substring(0,25)}</td>
    <td>${f.pais_region||'—'}</td>
    <td>${f.año||f.fecha?.substring(0,4)||'—'}</td>
    <td>${((f.importe_eur||0)/1e6).toFixed(2)}M€</td>
    <td>E${f.eslabon_corte||'—'}</td>
    <td>${f.score_trazabilidad||0}/100</td>
    <td><span class="pill ${f.clasificacion||''}">${f.clasificacion||'—'}</span></td>
  </tr>`).join('');
}

function filtrarEntidades() {
  const busq = document.getElementById('busq-entidad').value.toLowerCase();
  const nivel = document.getElementById('filtro-nivel').value;
  renderEntidades(_entidades.filter(e=>
    (!busq||(e.entidad||'').toLowerCase().includes(busq))&&
    (!nivel||e.nivel_riesgo===nivel)
  ));
}

function filtrarFondos() {
  const busq   = document.getElementById('busq-fondo').value.toLowerCase();
  const clasif = document.getElementById('filtro-clasif').value;
  const eslab  = document.getElementById('filtro-eslabon').value;
  const año    = document.getElementById('filtro-año').value;
  renderFondos(_fondos.filter(f=>
    (!busq  ||(f.titulo||'').toLowerCase().includes(busq)||(f.entidad||'').toLowerCase().includes(busq))&&
    (!clasif||f.clasificacion===clasif)&&
    (!eslab ||String(f.eslabon_corte)===eslab)&&
    (!año   ||String(f.año||f.fecha?.substring(0,4))===año)
  ));
}

cargar();
</script>
</body>
</html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS UI
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(DASHBOARD_HTML)


MANUAL_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Manual de Uso — Monitor AECID</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Segoe UI',sans-serif;background:#0f1117;color:#e0e0e0;line-height:1.7}
  header{background:#1a1d2e;padding:18px 28px;border-bottom:2px solid #2d3561;display:flex;align-items:center;justify-content:space-between}
  header h1{font-size:1.3rem;color:#fff}
  a{color:#7eb8f7;text-decoration:none}
  a:hover{text-decoration:underline}
  main{padding:32px 28px;max-width:960px;margin:0 auto}
  h2{font-size:1.15rem;color:#7eb8f7;margin:36px 0 12px;border-bottom:1px solid #2d3561;padding-bottom:6px}
  h3{font-size:0.95rem;color:#a0aec0;margin:18px 0 7px}
  p{margin-bottom:10px;color:#c0c8d8}
  ul,ol{padding-left:22px;margin-bottom:12px;color:#c0c8d8}
  li{margin-bottom:6px}
  .card{background:#1a1d2e;border:1px solid #2d3561;border-radius:10px;padding:20px;margin-bottom:18px}
  .badge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:0.78rem;font-weight:600;margin-right:6px}
  .r1{background:#7f1d1d;color:#fca5a5}
  .r2{background:#78350f;color:#fcd34d}
  .r3{background:#78350f;color:#fb923c}
  .ok{background:#14532d;color:#86efac}
  .info{background:#1e3a5f;color:#7eb8f7}
  .warn{background:#713f12;color:#fde68a}
  table{width:100%;border-collapse:collapse;font-size:0.84rem;margin:12px 0}
  th{text-align:left;padding:8px 10px;color:#7c8db5;border-bottom:1px solid #2d3561;font-weight:600}
  td{padding:8px 10px;border-bottom:1px solid #1e2235;color:#c0c8d8}
  tr:hover td{background:#1e2235}
  code{background:#1e2235;padding:2px 7px;border-radius:4px;font-family:monospace;font-size:0.85rem;color:#7eb8f7}
  .endpoint{background:#1e2235;border-left:3px solid #3b82f6;padding:10px 14px;margin:8px 0;border-radius:0 6px 6px 0;font-family:monospace;font-size:0.84rem;color:#93c5fd}
  .step{display:flex;gap:14px;margin-bottom:14px;align-items:flex-start}
  .step-num{background:#2d3561;color:#7eb8f7;border-radius:50%;width:28px;height:28px;min-width:28px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:0.85rem}
  .ltaibg-box{background:#1e3a5f;border:1px solid #2d5f8f;border-radius:10px;padding:20px;margin-bottom:18px}
  .ltaibg-box h3{color:#7eb8f7}
  .toc{background:#1a1d2e;border:1px solid #2d3561;border-radius:10px;padding:16px 20px;margin-bottom:28px}
  .toc ul{list-style:none;padding:0}
  .toc li{margin-bottom:4px}
  .toc a{color:#a0aec0;font-size:0.85rem}
  .toc a:hover{color:#7eb8f7}
  footer{text-align:center;padding:16px;color:#4a5568;font-size:0.75rem;border-top:1px solid #1a1d2e;margin-top:32px}
  @media(max-width:700px){main{padding:20px 14px}}
</style>
</head>
<body>
<header>
  <div>
    <h1>📖 Manual de Uso — Monitor Trazabilidad AECID</h1>
    <span style="font-size:0.8rem;color:#7c8db5">Ph.D. Vicente Humberto Monteverde — Algoritmos contra la Corrupción</span>
  </div>
  <a href="/" style="background:#2d3561;color:#7eb8f7;padding:6px 16px;border-radius:6px;font-size:0.85rem">← Dashboard</a>
</header>
<main>

  <!-- Índice -->
  <div class="toc">
    <p style="font-size:0.8rem;color:#7c8db5;margin-bottom:8px;font-weight:600">CONTENIDO</p>
    <ul>
      <li><a href="#que-es">1. ¿Qué es este sistema?</a></li>
      <li><a href="#eslabones">2. El Modelo de 7 Eslabones</a></li>
      <li><a href="#rupturas">3. Las tres rupturas estructurales (R1, R2, R3)</a></li>
      <li><a href="#indicadores">4. Indicadores de riesgo (ICR, SOG, RES, VIA)</a></li>
      <li><a href="#dashboard">5. Cómo leer el dashboard</a></li>
      <li><a href="#rendicion">6. Cards de rendición de cuentas</a></li>
      <li><a href="#ltaibg">7. Ley de Transparencia — Cómo solicitar información</a></li>
      <li><a href="#api">8. Endpoints de la API</a></li>
      <li><a href="#actualizacion">9. Actualización de datos y pipeline</a></li>
      <li><a href="#archivos">10. Archivos generados</a></li>
      <li><a href="#indicadores-internacionales">11. Indicadores internacionales de referencia</a></li>
      <li><a href="#marco">12. Marco teórico</a></li>
    </ul>
  </div>

  <!-- 1 -->
  <div class="card" id="que-es">
    <h2 style="margin-top:0">1. ¿Qué es este sistema?</h2>
    <p>El <strong>Monitor de Trazabilidad AECID</strong> es una herramienta de auditoría algorítmica que analiza los fondos de cooperación internacional gestionados por la Agencia Española de Cooperación Internacional para el Desarrollo (AECID), aplicando la metodología de <em>Fenómenos Corruptivos</em> del Ph.D. Vicente Humberto Monteverde.</p>
    <p>La AECID gestiona aproximadamente <strong>1.000 millones de euros al año</strong> de cooperación internacional. Este sistema detecta automáticamente las <strong>rupturas en la cadena de trazabilidad</strong> de cada fondo — desde el presupuesto aprobado en España hasta el beneficiario final — e identifica patrones de riesgo corruptivo.</p>
    <p>El análisis se basa exclusivamente en <strong>datos públicos</strong>: AECID, OCDE, Hacienda, transparencia.gob.es, IATI, BDNS y PLACE. No implica acusaciones de ilegalidad. El marco de fenómenos corruptivos analiza <em>inequidades estructurales</em> en la distribución de fondos públicos.</p>
  </div>

  <!-- 2 -->
  <h2 id="eslabones">2. El Modelo de 7 Eslabones</h2>
  <div class="card">
    <p>Cada fondo es evaluado según el último eslabón de trazabilidad alcanzado. La cadena va del presupuesto hasta el beneficiario final:</p>
    <table>
      <thead><tr><th>Eslabón</th><th>Etapa</th><th>Descripción</th><th>Score</th></tr></thead>
      <tbody>
        <tr><td><code>E1</code></td><td>Presupuesto España</td><td>Fondo visible en el Presupuesto General del Estado aprobado por las Cortes.</td><td>14/100</td></tr>
        <tr><td><code>E2</code></td><td>Transferencia AECID</td><td>La entidad receptora está identificada: OOII, ONGD o consultora.</td><td>28/100</td></tr>
        <tr><td><code>E3</code></td><td>Registro OOII/BDNS</td><td>El fondo figura en BDNS o en los sistemas de reporte de organismos internacionales.</td><td>42/100</td></tr>
        <tr><td><code>E4</code></td><td>Destino geográfico</td><td>El país o región de destino está declarado públicamente con código OCDE-CRS.</td><td>57/100</td></tr>
        <tr><td><code>E5</code></td><td>Contratos PLACE/OCDS</td><td>Los contratos derivados están publicados en el portal de contratación bajo estándar OCDS.</td><td>71/100</td></tr>
        <tr><td><code>E6</code></td><td>Justificantes públicos</td><td>Existen evaluaciones finales publicadas o respuestas positivas a solicitudes LTAIBG.</td><td>85/100</td></tr>
        <tr><td><code>E7</code></td><td>Beneficiario final</td><td>El beneficiario final está identificado con NIF/CIF o nombre completo verificable.</td><td>100/100</td></tr>
      </tbody>
    </table>
    <p style="margin-top:12px">El <strong>score de trazabilidad</strong> va de 14/100 (eslabón 1) a 100/100 (eslabón 7). Un score &lt;50 indica ruptura significativa en la cadena de rendición de cuentas.</p>
    <p>Actualmente el <strong>92% de los fondos no supera el eslabón 4</strong> — el destino geográfico es conocido pero los contratos y justificantes son opacOs.</p>
  </div>

  <!-- 3 -->
  <h2 id="rupturas">3. Las tres rupturas estructurales</h2>
  <div class="card">
    <h3><span class="badge r1">R1</span> OOII — Caja negra multilateral</h3>
    <p>Fondos transferidos a Organismos Internacionales (PNUD, UNICEF, FAO, ACNUR, OMS…) que agregan contribuciones multi-donante sin desglosar la aportación española en el estándar IATI. La trazabilidad se corta en el <strong>eslabón 3</strong>.</p>
    <p><strong>Por qué ocurre:</strong> Los OOII reciben fondos de decenas de países donantes en cuentas pooled y rinden cuentas globalmente, no por donante individual. España no exige desagregación en sus convenios de contribución.</p>
    <p><strong>Solución estructural:</strong> Exigir etiquetado IATI con donor-reference en todos los convenios de contribución firmados por la AECID.</p>

    <h3 style="margin-top:20px"><span class="badge r2">R2</span> Sub-contratación sin OCDS</h3>
    <p>Contratos adjudicados directamente o sin publicación en el Portal de la Contratación del Estado (PLACE) bajo el estándar Open Contracting Data Standard. Incluye contratos menores, negociados sin publicidad y urgencias declaradas.</p>
    <p><strong>Por qué ocurre:</strong> Los contratos en el extranjero ejecutados por ONGDs o socios locales no están sujetos a la Ley de Contratos del Sector Público (LCSP) española, sino a la legislación del país receptor, que generalmente no publica en OCDS.</p>
    <p><strong>Solución estructural:</strong> Inclusión de cláusula de publicación OCDS en todos los convenios de subvención con ONGDs y contratos marco de la AECID.</p>

    <h3 style="margin-top:20px"><span class="badge r3">R3</span> Sin justificante auditable</h3>
    <p>Proyectos con importe superior a 500.000€ que no tienen evaluación final publicada ni respuesta favorable a solicitud de información via Ley de Transparencia (LTAIBG 19/2013).</p>
    <p><strong>Por qué ocurre:</strong> Las evaluaciones finales son un requisito formal pero no hay un repositorio público centralizado. El Tribunal de Cuentas fiscaliza una muestra, no la totalidad.</p>
    <p><strong>Solución estructural:</strong> Repositorio público de evaluaciones finales como condición para el cierre contable de cada proyecto en el sistema de gestión interna de la AECID.</p>
  </div>

  <!-- 4 -->
  <h2 id="indicadores">4. Indicadores de riesgo</h2>
  <div class="card">
    <p>El <strong>score de riesgo</strong> integra cuatro indicadores, cada uno con peso diferente:</p>
    <table>
      <thead><tr><th>Indicador</th><th>Peso</th><th>Fórmula</th><th>Alerta si…</th></tr></thead>
      <tbody>
        <tr><td><strong>ICR</strong> — Índice de Concentración de Receptores</td><td>15%</td><td>HHI normalizado por entidad receptora</td><td>&gt; 0,25</td></tr>
        <tr><td><strong>SOG</strong> — Score de Opacidad en Gestión</td><td>35%</td><td>Suma ponderada de flags: es_ooii, R2, R3, adj. directa, sin país</td><td>&gt; 50</td></tr>
        <tr><td><strong>RES</strong> — Riesgo por Eslabón de Corte</td><td>30%</td><td>100 − score_trazabilidad</td><td>eslabon &lt; 4</td></tr>
        <tr><td><strong>VIA</strong> — Vulnerabilidad Institucional del receptor</td><td>20%</td><td>Proxy WGI Banco Mundial (0-100, invertido)</td><td>&gt; 60</td></tr>
      </tbody>
    </table>
    <p style="margin-top:10px"><strong>Score integrado</strong> = 60% × (ICR+SOG+RES+VIA) + 40% × (100 − score_trazabilidad)</p>
    <table style="margin-top:12px">
      <thead><tr><th>Clasificación</th><th>Score</th><th>Significado operativo</th></tr></thead>
      <tbody>
        <tr><td><span class="badge ok">VERDE</span></td><td>0–25</td><td>Trazabilidad aceptable, bajo riesgo. Apto para cierre.</td></tr>
        <tr><td><span class="badge warn">AMARILLO</span></td><td>25–50</td><td>Trazabilidad parcial. Revisar eslabones faltantes.</td></tr>
        <tr><td><span class="badge r2">NARANJA</span></td><td>50–75</td><td>Rupturas detectadas. Requiere solicitud LTAIBG o auditoría.</td></tr>
        <tr><td><span class="badge r1">ROJO</span></td><td>75–100</td><td>Múltiples rupturas. Derivar al Tribunal de Cuentas o IGAE.</td></tr>
      </tbody>
    </table>
  </div>

  <!-- 5 -->
  <h2 id="dashboard">5. Cómo leer el dashboard</h2>
  <div class="card">
    <h3>KPIs superiores</h3>
    <p>Los 6 indicadores en la franja superior resumen el estado global: total de fondos analizados, importe total en M€, score medio de trazabilidad y porcentaje de fondos con cada ruptura (R1/R2/R3). Un score medio &lt;50 indica que la mayoría del portafolio tiene rupturas significativas.</p>

    <h3>Gráficos de rupturas y eslabones</h3>
    <p>Las barras de progreso muestran qué porcentaje del total tiene cada ruptura. El gráfico de barras de eslabones muestra cuántos fondos se cortan en cada etapa — idealmente todo debería estar en E5 o superior.</p>

    <h3>Evolución anual y distribución geográfica</h3>
    <p>El gráfico combinado barra+línea muestra el importe anual y la curva acumulada. El doughnut geográfico agrupa los fondos en 5 regiones principales para detectar concentración.</p>

    <h3>Clasificación de riesgo, Score por eslabón y Sector CRS</h3>
    <p>Tres gráficos nuevos que muestran: (1) cuántos fondos caen en cada clasificación ROJO/NARANJA/AMARILLO/VERDE, (2) el score medio de trazabilidad por eslabón de corte — permite ver si los E3 son sistemáticamente más opacos, (3) distribución del importe por sector de actividad CRS.</p>

    <h3>Filtros en las tablas</h3>
    <p>Todas las tablas tienen filtros combinables: podés filtrar por clasificación + eslabón + año simultáneamente. El buscador de texto filtra en tiempo real sobre título y entidad.</p>
  </div>

  <!-- 6 -->
  <h2 id="rendicion">6. Cards de rendición de cuentas</h2>
  <div class="card">
    <p>Cada card muestra un fondo clasificado ROJO u NARANJA con la siguiente información:</p>
    <ul>
      <li><strong>Barra de trazabilidad:</strong> score visual 0-100 con color según nivel</li>
      <li><strong>Eslabón de corte:</strong> en qué etapa se rompió la cadena</li>
      <li><strong>Rupturas detectadas:</strong> badges R1/R2/R3 cuando aplican</li>
      <li><strong>🔗 Fuente AECID:</strong> enlace directo al registro en datos.aecid.es</li>
      <li><strong>⚖️ Tribunal de Cuentas:</strong> buscador en tcu.es filtrado por AECID</li>
      <li><strong>📋 BDNS:</strong> buscador en infosubvenciones.es filtrado por AECID</li>
    </ul>
    <p>Estos links permiten verificar manualmente si existe información adicional en fuentes oficiales que el sistema automático no capturó. Si encontrás documentación relevante, podés registrarla en <code>data/raw/ltaibg_respuestas.csv</code> para que el próximo pipeline actualice el score.</p>
  </div>

  <!-- 7 -->
  <h2 id="ltaibg">7. Ley de Transparencia — Cómo solicitar información</h2>
  <div class="ltaibg-box">
    <h3>⚖️ Ley 19/2013 de Transparencia, Acceso a la Información Pública y Buen Gobierno</h3>
    <p>Todo ciudadano tiene derecho a solicitar información pública a la AECID sin necesidad de justificar el motivo. La Administración tiene <strong>30 días hábiles</strong> para responder (ampliable a 30 días más en casos complejos).</p>
  </div>
  <div class="card">
    <h3>¿Qué podés solicitar sobre fondos AECID?</h3>
    <ul>
      <li>Evaluaciones finales de proyectos específicos</li>
      <li>Contratos y convenios de contribución con OOII</li>
      <li>Justificantes de gasto de subvenciones a ONGDs</li>
      <li>Informes de seguimiento de intervenciones</li>
      <li>Criterios de selección de socios locales</li>
      <li>Actas de órganos de seguimiento de programas bilaterales</li>
    </ul>

    <h3 style="margin-top:16px">Pasos para presentar una solicitud</h3>
    <div class="step"><div class="step-num">1</div><div><strong>Portal de transparencia del Gobierno:</strong><br>Accedé a <a href="https://transparencia.gob.es/transparencia/transparencia_Home/index/Solicitar-Informacion.html" target="_blank">transparencia.gob.es → Solicitar Información</a>. Necesitás certificado electrónico, DNIe o Cl@ve.</div></div>
    <div class="step"><div class="step-num">2</div><div><strong>Portal AECID directamente:</strong><br><a href="https://www.aecid.es/ES/la-aecid/transparencia" target="_blank">aecid.es/transparencia</a> — Tienen formulario propio y canal de acceso a la información.</div></div>
    <div class="step"><div class="step-num">3</div><div><strong>Consejo de Transparencia:</strong><br>Si la respuesta es negativa o no llega en plazo, podés reclamar ante el <a href="https://www.consejodetransparencia.es/" target="_blank">Consejo de Transparencia y Buen Gobierno</a> de forma gratuita.</div></div>
    <div class="step"><div class="step-num">4</div><div><strong>Registrar la respuesta:</strong><br>Una vez recibida, añadí el resultado en <code>data/raw/ltaibg_respuestas.csv</code> con los campos: fecha_solicitud, proyecto, organismo, fecha_respuesta, tipo_respuesta, tiene_justificante. El próximo pipeline actualizará el score R3 del fondo.</div></div>

    <h3 style="margin-top:16px">Plazos y recursos legales</h3>
    <table>
      <thead><tr><th>Situación</th><th>Plazo</th><th>Acción</th></tr></thead>
      <tbody>
        <tr><td>Sin respuesta</td><td>30 días hábiles</td><td>Silencio negativo — reclamar ante CTBG</td></tr>
        <tr><td>Respuesta parcial</td><td>—</td><td>Recurso de reposición o reclamación CTBG</td></tr>
        <tr><td>Denegación</td><td>1 mes</td><td>Reclamación ante CTBG (gratuita, sin abogado)</td></tr>
        <tr><td>Resolución CTBG desfavorable</td><td>2 meses</td><td>Recurso contencioso-administrativo</td></tr>
      </tbody>
    </table>
  </div>

  <!-- 8 -->
  <h2 id="api">8. Endpoints de la API</h2>
  <div class="card">
    <div class="endpoint">GET /api/status — Estado del servicio, versión y total de fondos cargados</div>
    <div class="endpoint">GET /api/resumen — KPIs ejecutivos, acumulativo anual y top países/regiones</div>
    <div class="endpoint">GET /api/fondos?entidad=X&amp;clasificacion=ROJO&amp;eslabon=3&amp;pais=Bolivia&amp;año=2023&amp;limit=100</div>
    <div class="endpoint">GET /api/trazabilidad — Análisis completo por eslabón con scores</div>
    <div class="endpoint">GET /api/entidades?top=30&amp;nivel=Alto — Ranking de entidades por riesgo integrado</div>
    <div class="endpoint">GET /api/riesgo — Scores ICR/SOG/RES/VIA desagregados por entidad</div>
    <div class="endpoint">GET /api/mensual — Evolución mensual por región y sector CRS</div>
    <div class="endpoint">GET /api/informe — Informe ejecutivo completo en formato Markdown</div>
    <div class="endpoint">POST /api/refresh (Header: X-Refresh-Token: &lt;token&gt;) — Ejecuta el pipeline completo</div>
    <p style="margin-top:12px;font-size:0.82rem;color:#7c8db5">Todos los endpoints devuelven JSON. No requieren autenticación excepto <code>/api/refresh</code>.</p>
  </div>

  <!-- 9 -->
  <h2 id="actualizacion">9. Actualización de datos y pipeline</h2>
  <div class="card">
    <p>El pipeline corre automáticamente <strong>cada día a las 07:00 UTC</strong> via GitHub Actions, descargando y procesando:</p>
    <ul>
      <li><strong>AECID</strong> — Portal datos.aecid.es (intervenciones activas y finalizadas)</li>
      <li><strong>BDNS</strong> — Base de Datos Nacional de Subvenciones (convocatorias y convenios AECID)</li>
      <li><strong>PLACE</strong> — Portal de Contratación del Estado en estándar OCDS</li>
      <li><strong>LTAIBG</strong> — Registro manual de respuestas a solicitudes de transparencia</li>
    </ul>
    <h3>Ejecución manual</h3>
    <ul>
      <li><code>python pipeline.py</code> — Pipeline completo</li>
      <li><code>python pipeline.py --solo-ingesta</code> — Solo descarga datos</li>
      <li><code>python pipeline.py --solo-analisis</code> — Solo análisis (sin descarga)</li>
      <li><code>python pipeline.py --forzar</code> — Re-descarga aunque los archivos existan</li>
      <li><code>python pipeline.py --años 2022 2023 2024</code> — Filtrar por años</li>
    </ul>
    <h3>Persistencia entre deploys (Railway)</h3>
    <p>Los datos procesados se guardan automáticamente en PostgreSQL al terminar cada pipeline. Al arrancar la app en Railway después de un redeploy, los CSVs se restauran desde la base de datos — no se pierde información entre deploys.</p>
  </div>

  <!-- 10 -->
  <h2 id="archivos">10. Archivos generados</h2>
  <div class="card">
    <table>
      <thead><tr><th>Archivo</th><th>Descripción</th></tr></thead>
      <tbody>
        <tr><td><code>data/raw/aecid_intervenciones.csv</code></td><td>Intervenciones descargadas de datos.aecid.es</td></tr>
        <tr><td><code>data/raw/bdns_subvenciones.csv</code></td><td>Convocatorias y convenios BDNS</td></tr>
        <tr><td><code>data/raw/place_contratos.csv</code></td><td>Contratos PLACE/OCDS adjudicados</td></tr>
        <tr><td><code>data/raw/ltaibg_respuestas.csv</code></td><td>Completar manualmente con respuestas a solicitudes</td></tr>
        <tr><td><code>data/processed/intervenciones_clean.csv</code></td><td>Datos limpios con campo eslabon_corte calculado</td></tr>
        <tr><td><code>data/processed/trazabilidad_por_fondo.csv</code></td><td>Score de trazabilidad (0-100) por intervención</td></tr>
        <tr><td><code>data/processed/scores_riesgo.csv</code></td><td>Indicadores ICR/SOG/RES/VIA por entidad</td></tr>
        <tr><td><code>data/processed/analisis_completo.csv</code></td><td>Dataset completo fusionado para el dashboard</td></tr>
        <tr><td><code>reports/informe_ejecutivo.md</code></td><td>Informe ejecutivo con top riesgos en Markdown</td></tr>
      </tbody>
    </table>
  </div>

  <!-- 11 -->
  <h2 id="indicadores-internacionales">11. Indicadores internacionales de referencia</h2>
  <div class="card">
    <p>El sistema integra y cruza los siguientes estándares internacionales para evaluar cada fondo:</p>
    <table>
      <thead><tr><th>Estándar</th><th>Organismo</th><th>Uso en el sistema</th></tr></thead>
      <tbody>
        <tr><td><strong>CRS</strong> — Creditor Reporting System</td><td>OCDE</td><td>Clasificación de sector, canal y tipo de flujo de cada intervención</td></tr>
        <tr><td><strong>IATI</strong> — International Aid Transparency</td><td>IATI Secretariat</td><td>Detección de rupturas R1: OOII que no desagregan en IATI</td></tr>
        <tr><td><strong>OCDS</strong> — Open Contracting Data Standard</td><td>Open Contracting Partnership</td><td>Detección de rupturas R2: contratos sin publicación PLACE/OCDS</td></tr>
        <tr><td><strong>WGI</strong> — Worldwide Governance Indicators</td><td>Banco Mundial</td><td>Indicador VIA: vulnerabilidad institucional del país receptor</td></tr>
        <tr><td><strong>IPC/CPI</strong> — Índice Percepción Corrupción</td><td>Transparency International</td><td>Complemento al VIA para países con IPC &lt;40</td></tr>
        <tr><td><strong>HHI</strong> — Herfindahl-Hirschman Index</td><td>DOJ / Literatura económica</td><td>Indicador ICR: concentración de fondos en pocos receptores</td></tr>
        <tr><td><strong>OLAF</strong> — Marco antifraude UE</td><td>Comisión Europea</td><td>Referencia para fondos con cofinanciación europea (FEDER/FSE)</td></tr>
        <tr><td><strong>LTAIBG</strong> — Ley 19/2013</td><td>España</td><td>Base legal del indicador R3: solicitudes de acceso a información</td></tr>
      </tbody>
    </table>
    <h3 style="margin-top:16px">¿Por qué estos estándares?</h3>
    <p>Cada indicador del sistema tiene un referente internacional que lo valida:</p>
    <ul>
      <li><strong>ICR &gt;0,25</strong> — equivale a HHI &gt;2.500 en mercados (umbral DOJ de concentración elevada), adaptado a cuotas de receptores de fondos públicos</li>
      <li><strong>SOG &gt;50</strong> — combina flags binarios ponderados, metodología similar al Corruption Risk Index de la UE (ERCAS)</li>
      <li><strong>VIA basado en WGI</strong> — el WGI control of corruption es el indicador de gobernanza más usado en evaluaciones de riesgo fiduciario (Banco Mundial, PNUD)</li>
      <li><strong>Score integrado 60/40</strong> — proporción riesgo/trazabilidad calibrada sobre metodología de Aid Quality Index (Brookings) y Open Budget Index (IBP)</li>
    </ul>
  </div>

  <!-- 12 -->
  <h2 id="marco">12. Marco teórico</h2>
  <div class="card">
    <p>El análisis se basa en la teoría de los <em>Fenómenos Corruptivos</em> desarrollada por el Ph.D. Vicente Humberto Monteverde, que conceptualiza la corrupción como <strong>transferencias regresivas de ingresos</strong> facilitadas por la discrecionalidad en las decisiones legales — no solo actos ilegales, sino distribuciones inequitativas de rentas a grupos de interés con base de legalidad.</p>
    <p>Los 7 escenarios de transferencia identificados son: Privatización/Concesión, Contratos Públicos, Tarifas de Servicios Públicos, Precios Regulados, Salarios/Negociación Paritaria, Jubilaciones y Traslado de Impuestos.</p>
    <p>Aplicado a cooperación internacional, el modelo detecta cuándo la opacidad estructural en la cadena AECID→OOII→Socio local→Beneficiario crea condiciones favorables para la captura de rentas, independientemente de la legalidad formal de cada transacción.</p>
    <p style="margin-top:10px">Referencia: Monteverde, V.H. (2019). <em>Economía Corruptiva</em>. Dialnet. — <a href="https://github.com/Viny2030/Fenomenos_corruptivos_spain" target="_blank">github.com/Viny2030/Fenomenos_corruptivos_spain</a></p>
  </div>

</main>
<footer>Monitor AECID v2.0 · github.com/Viny2030/Fenomenos_corruptivos_spain · Ley 19/2013 LTAIBG</footer>
</body>
</html>
"""

@app.get("/manual", response_class=HTMLResponse)
def manual():
    return HTMLResponse(MANUAL_HTML)


# ─────────────────────────────────────────────────────────────────────────────
# API — STATUS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/status")
def status():
    df = _cargar_fondos()
    return {
        "servicio":        "Monitor Trazabilidad AECID v1.0",
        "status":          "activo",
        "total_fondos":    len(df),
        "cache_timestamp": _cache["ts"],
        "timestamp":       datetime.now().isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# API — RESUMEN
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/resumen")
def resumen():
    df = _cargar_fondos()
    if df.empty:
        return {"total_fondos": 0, "mensaje": "Sin datos — correr pipeline primero"}

    total_eur = df["importe_eur"].apply(_parsear_monto).sum() if "importe_eur" in df.columns else 0

    def _pct(col):
        if col not in df.columns:
            return 0.0
        n = df[col].astype(str).str.upper().isin(["TRUE", "1"]).sum()
        return round(n / len(df) * 100, 1) if len(df) else 0

    score_traz = round(df["score_trazabilidad"].mean(), 1) if "score_trazabilidad" in df.columns else 0

    dist_eslabon = {}
    if "eslabon_corte" in df.columns:
        dist_eslabon = df["eslabon_corte"].value_counts().to_dict()

    # Acumulativo por año
    acumulativo = []
    if "fecha" in df.columns:
        df2 = df.copy()
        df2["año"] = pd.to_datetime(df2["fecha"], errors="coerce").dt.year
        df2["importe_num"] = df2["importe_eur"].apply(_parsear_monto)
        acum = df2.groupby("año").agg(
            n=("importe_num", "count"),
            importe=("importe_num", "sum"),
        ).reset_index().sort_values("año")
        acum["importe_acum"] = acum["importe"].cumsum()
        acumulativo = acum.dropna().to_dict(orient="records")

    # Top países por importe
    por_pais = []
    if "pais_region" in df.columns:
        df3 = df.copy()
        df3["importe_num"] = df3["importe_eur"].apply(_parsear_monto)
        grp = df3.groupby("pais_region").agg(
            n=("importe_num", "count"),
            importe=("importe_num", "sum"),
        ).reset_index().sort_values("importe", ascending=False).head(20)
        grp["pct"] = (grp["importe"] / total_eur * 100).round(1)
        por_pais = grp.to_dict(orient="records")

    return {
        "total_fondos":              len(df),
        "total_eur":                 round(total_eur / 1e6, 1),
        "score_trazabilidad_medio":  score_traz,
        "pct_r1":                    _pct("ruptura_r1"),
        "pct_r2":                    _pct("ruptura_r2"),
        "pct_r3":                    _pct("ruptura_r3"),
        "distribucion_eslabones":    dist_eslabon,
        "acumulativo_anual":         acumulativo,
        "top_paises":                por_pais,
        "timestamp":                 datetime.now().isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# API — FONDOS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/fondos")
def fondos(
    entidad:       str | None = Query(None),
    clasificacion: str | None = Query(None),
    eslabon:       int | None = Query(None),
    pais:          str | None = Query(None),
    limit:         int        = Query(100, le=1000),
    offset:        int        = Query(0),
):
    df = _cargar_fondos().copy()
    if df.empty:
        return {"total": 0, "data": []}

    if entidad and "entidad" in df.columns:
        df = df[df["entidad"].str.contains(entidad, case=False, na=False)]
    if clasificacion and "clasificacion" in df.columns:
        df = df[df["clasificacion"].str.upper() == clasificacion.upper()]
    if eslabon and "eslabon_corte" in df.columns:
        df = df[df["eslabon_corte"].astype(str) == str(eslabon)]
    if pais and "pais_region" in df.columns:
        df = df[df["pais_region"].str.contains(pais, case=False, na=False)]

    total = len(df)
    return {
        "total":  total,
        "limit":  limit,
        "offset": offset,
        "data":   df.iloc[offset: offset + limit].fillna("").to_dict(orient="records"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# API — TRAZABILIDAD
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/trazabilidad")
def trazabilidad():
    df = _cargar_trazabilidad()
    if df.empty:
        return {"data": [], "resumen": {}}

    resumen = {}
    if "eslabon_corte" in df.columns:
        resumen["distribucion"] = df["eslabon_corte"].value_counts().to_dict()
    if "score_trazabilidad" in df.columns:
        resumen["score_medio"] = round(df["score_trazabilidad"].mean(), 1)
    for col in ["ruptura_r1", "ruptura_r2", "ruptura_r3"]:
        if col in df.columns:
            n = df[col].astype(str).str.upper().isin(["TRUE", "1"]).sum()
            resumen[f"n_{col}"] = int(n)

    return {
        "resumen": resumen,
        "data":    df.fillna("").head(200).to_dict(orient="records"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# API — ENTIDADES
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/entidades")
def entidades(
    top:    int        = Query(30, le=100),
    nivel:  str | None = Query(None),
    busqueda: str | None = Query(None),
):
    df = _cargar_scores()
    if df.empty:
        return {"data": []}

    if nivel and "nivel_riesgo" in df.columns:
        df = df[df["nivel_riesgo"].str.lower() == nivel.lower()]
    if busqueda and "entidad" in df.columns:
        df = df[df["entidad"].str.contains(busqueda, case=False, na=False)]

    if "score_riesgo" in df.columns:
        df = df.sort_values("score_riesgo", ascending=False)

    return {"data": df.head(top).fillna(0).to_dict(orient="records")}


# ─────────────────────────────────────────────────────────────────────────────
# API — RIESGO
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/riesgo")
def riesgo():
    df = _cargar_scores()
    if df.empty:
        return {"data": [], "resumen": {}}

    resumen = {}
    if "nivel_riesgo" in df.columns:
        resumen["distribucion"] = df["nivel_riesgo"].value_counts().to_dict()
    if "score_riesgo" in df.columns:
        resumen["score_medio"] = round(df["score_riesgo"].mean(), 1)
        idx = df["score_riesgo"].idxmax()
        resumen["entidad_mayor_riesgo"] = df.loc[idx, "entidad"] if "entidad" in df.columns else ""

    return {
        "resumen": resumen,
        "data":    df.fillna(0).to_dict(orient="records"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# API — INFORME
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/informe", response_class=PlainTextResponse)
def informe():
    p = REPORTS / "informe_ejecutivo.md"
    if not p.exists():
        raise HTTPException(404, "Informe no generado — correr pipeline primero")
    return PlainTextResponse(p.read_text(encoding="utf-8"))


# ─────────────────────────────────────────────────────────────────────────────
# API — REFRESH
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/refresh")
def refresh(x_refresh_token: str = Header(None)):
    if x_refresh_token != REFRESH_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")
    _invalidar_cache()
    try:
        result = subprocess.run(
            [sys.executable, "pipeline.py", "--solo-analisis"],
            capture_output=True, text=True, timeout=300,
            cwd=str(ROOT),
        )
        _invalidar_cache()
        return {
            "status":    "ok" if result.returncode == 0 else "error",
            "log":       result.stdout[-2000:] + result.stderr[-1000:],
            "timestamp": datetime.now().isoformat(),
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Timeout — pipeline tardó más de 5 minutos")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# API — MENSUAL (evolución de importes por mes y región)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/mensual")
def mensual():
    df = _cargar_fondos()
    if df.empty:
        return {"data": []}

    if "fecha" not in df.columns:
        return {"data": []}

    df = df.copy()
    df["fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["mes"] = df["fecha_dt"].dt.to_period("M").astype(str)
    df["importe_num"] = df["importe_eur"].apply(_parsear_monto)

    # Evolución mensual total
    mensual_total = df.groupby("mes").agg(
        n=("importe_num", "count"),
        importe=("importe_num", "sum"),
    ).reset_index().sort_values("mes")

    # Por región
    mensual_region = {}
    if "region" in df.columns:
        for region, grp in df.groupby("region"):
            evol = grp.groupby("mes")["importe_num"].sum().reset_index()
            evol.columns = ["mes", "importe"]
            mensual_region[str(region)] = evol.to_dict(orient="records")
    elif "pais_region" in df.columns:
        # Agrupar por región inferida
        df["region_inf"] = df["pais_region"].apply(lambda p: (
            "América Latina" if any(x in str(p) for x in ["Bolivia","Colombia","Ecuador","Guatemala","Honduras","México","Nicaragua","Perú","Cuba","Haití"]) else
            "África" if any(x in str(p) for x in ["Etiopía","Mozambique","Mali","Niger","Senegal","Chad","Kenya"]) else
            "MENA" if any(x in str(p) for x in ["Marruecos","Túnez","Jordania","Líbano","Palestina","Siria","Yemen"]) else
            "Multipaís/Global"
        ))
        for region, grp in df.groupby("region_inf"):
            evol = grp.groupby("mes")["importe_num"].sum().reset_index()
            evol.columns = ["mes", "importe"]
            mensual_region[str(region)] = evol.to_dict(orient="records")

    # Por sector
    mensual_sector = {}
    if "ambito" in df.columns:
        for sector, grp in df.groupby("ambito"):
            if str(sector) in ("", "nan"):
                continue
            evol = grp.groupby("mes")["importe_num"].sum().reset_index()
            evol.columns = ["mes", "importe"]
            mensual_sector[str(sector)] = evol.to_dict(orient="records")

    return {
        "total":   mensual_total.to_dict(orient="records"),
        "region":  mensual_region,
        "sector":  mensual_sector,
    }