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

  <!-- Fila 4: Entidades -->
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
  main{padding:32px 28px;max-width:900px;margin:0 auto}
  h2{font-size:1.2rem;color:#7eb8f7;margin:32px 0 12px;border-bottom:1px solid #2d3561;padding-bottom:6px}
  h3{font-size:1rem;color:#a0aec0;margin:20px 0 8px}
  p{margin-bottom:10px;color:#c0c8d8}
  ul,ol{padding-left:20px;margin-bottom:12px;color:#c0c8d8}
  li{margin-bottom:6px}
  .card{background:#1a1d2e;border:1px solid #2d3561;border-radius:10px;padding:20px;margin-bottom:18px}
  .badge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:0.78rem;font-weight:600;margin-right:6px}
  .r1{background:#7f1d1d;color:#fca5a5}
  .r2{background:#78350f;color:#fcd34d}
  .r3{background:#78350f;color:#fb923c}
  .ok{background:#14532d;color:#86efac}
  .info{background:#1e3a5f;color:#7eb8f7}
  table{width:100%;border-collapse:collapse;font-size:0.85rem;margin:12px 0}
  th{text-align:left;padding:8px 10px;color:#7c8db5;border-bottom:1px solid #2d3561;font-weight:600}
  td{padding:8px 10px;border-bottom:1px solid #1e2235;color:#c0c8d8}
  code{background:#1e2235;padding:2px 7px;border-radius:4px;font-family:monospace;font-size:0.85rem;color:#7eb8f7}
  .endpoint{background:#1e2235;border-left:3px solid #3b82f6;padding:10px 14px;margin:8px 0;border-radius:0 6px 6px 0;font-family:monospace;font-size:0.85rem}
  footer{text-align:center;padding:16px;color:#4a5568;font-size:0.75rem;border-top:1px solid #1a1d2e;margin-top:32px}
</style>
</head>
<body>
<header>
  <div>
    <h1>📖 Manual de Uso — Monitor Trazabilidad AECID</h1>
  </div>
  <a href="/" style="background:#2d3561;color:#7eb8f7;padding:6px 16px;border-radius:6px;font-size:0.85rem">← Dashboard</a>
</header>
<main>

  <div class="card">
    <h2 style="margin-top:0">¿Qué es este sistema?</h2>
    <p>El <strong>Monitor de Trazabilidad AECID</strong> es una herramienta de auditoría algorítmica que analiza los fondos de cooperación internacional gestionados por la Agencia Española de Cooperación Internacional para el Desarrollo (AECID), aplicando la metodología de <em>Fenómenos Corruptivos</em> del Ph.D. Vicente Humberto Monteverde.</p>
    <p>El sistema detecta automáticamente las <strong>rupturas en la cadena de trazabilidad</strong> de cada fondo — desde el presupuesto aprobado en España hasta el beneficiario final — e identifica patrones de riesgo corruptivo.</p>
  </div>

  <h2>📊 El Modelo de 7 Eslabones</h2>
  <div class="card">
    <p>Cada fondo es evaluado según el último eslabón de trazabilidad alcanzado:</p>
    <table>
      <thead><tr><th>Eslabón</th><th>Etapa</th><th>Descripción</th></tr></thead>
      <tbody>
        <tr><td><code>E1</code></td><td>Presupuesto España</td><td>El fondo aparece en el Presupuesto General del Estado aprobado.</td></tr>
        <tr><td><code>E2</code></td><td>Transferencia AECID</td><td>La entidad receptora está identificada (OOII, ONGD o consultora).</td></tr>
        <tr><td><code>E3</code></td><td>Registro OOII/BDNS</td><td>El fondo está registrado en BDNS o en organismos internacionales.</td></tr>
        <tr><td><code>E4</code></td><td>Destino geográfico</td><td>El país o región de destino está declarado públicamente.</td></tr>
        <tr><td><code>E5</code></td><td>Contratos PLACE/OCDS</td><td>Los contratos derivados están publicados en el portal de contratación.</td></tr>
        <tr><td><code>E6</code></td><td>Justificantes públicos</td><td>Existen evaluaciones finales o respuestas positivas a solicitudes LTAIBG.</td></tr>
        <tr><td><code>E7</code></td><td>Beneficiario final</td><td>El beneficiario final está identificado con NIF/CIF o nombre.</td></tr>
      </tbody>
    </table>
    <p>El <strong>score de trazabilidad</strong> va de 14/100 (eslabón 1) a 100/100 (eslabón 7). Un score &lt;50 indica ruptura significativa.</p>
  </div>

  <h2>🚨 Las Tres Rupturas Principales</h2>
  <div class="card">
    <h3><span class="badge r1">R1</span> OOII — Caja negra</h3>
    <p>Fondos transferidos a Organismos Internacionales (PNUD, UNICEF, FAO, ACNUR…) que agregan contribuciones multi-donante sin desglosar la aportación española en el estándar IATI. La trazabilidad se corta en el eslabón 3.</p>
    <p><strong>Indicador:</strong> % de fondos cuyo receptor es una OOII de la lista de caja negra.</p>

    <h3><span class="badge r2">R2</span> Sub-contratación sin OCDS</h3>
    <p>Contratos adjudicados directamente o sin publicación en el Portal de la Contratación del Estado (PLACE) bajo el estándar Open Contracting Data Standard. Incluye contratos menores, negociados sin publicidad y urgencias.</p>
    <p><strong>Indicador:</strong> % de fondos sin correspondencia en PLACE o con adjudicación directa.</p>

    <h3><span class="badge r3">R3</span> Sin justificante auditable</h3>
    <p>Proyectos con importe superior a 500.000€ que no tienen evaluación final publicada ni respuesta favorable a solicitud de información via Ley de Transparencia (LTAIBG 19/2013).</p>
    <p><strong>Indicador:</strong> % de fondos &gt;500K€ sin justificante registrado en el sistema.</p>
  </div>

  <h2>📈 Indicadores de Riesgo</h2>
  <div class="card">
    <table>
      <thead><tr><th>Indicador</th><th>Peso</th><th>Descripción</th></tr></thead>
      <tbody>
        <tr><td><strong>ICR</strong></td><td>15%</td><td>Índice de Concentración de Receptores (HHI normalizado). Detecta si unos pocos actores concentran la mayoría de los fondos.</td></tr>
        <tr><td><strong>SOG</strong></td><td>35%</td><td>Score de Opacidad en la Gestión. Suma ponderada de indicadores binarios: es OOII, tiene R2, tiene R3, adjudicación directa, sin país declarado.</td></tr>
        <tr><td><strong>RES</strong></td><td>30%</td><td>Riesgo por Eslabón de Corte. Inverso del score de trazabilidad — cuanto más bajo el eslabón, mayor el riesgo.</td></tr>
        <tr><td><strong>VIA</strong></td><td>20%</td><td>Vulnerabilidad Institucional del país receptor, basado en proxy del Índice de Gobernanza del Banco Mundial (WGI 0-100).</td></tr>
      </tbody>
    </table>
    <p><strong>Score integrado</strong> = 60% riesgo (ICR+SOG+RES+VIA) + 40% trazabilidad invertida.</p>
    <table>
      <thead><tr><th>Clasificación</th><th>Score</th><th>Significado</th></tr></thead>
      <tbody>
        <tr><td><span class="badge ok">VERDE</span></td><td>0-25</td><td>Trazabilidad aceptable, bajo riesgo</td></tr>
        <tr><td><span class="badge" style="background:#713f12;color:#fde68a">AMARILLO</span></td><td>25-50</td><td>Trazabilidad parcial, riesgo moderado</td></tr>
        <tr><td><span class="badge r2">NARANJA</span></td><td>50-75</td><td>Rupturas detectadas, riesgo alto</td></tr>
        <tr><td><span class="badge r1">ROJO</span></td><td>75-100</td><td>Múltiples rupturas, riesgo crítico</td></tr>
      </tbody>
    </table>
  </div>

  <h2>🔌 Endpoints de la API</h2>
  <div class="card">
    <div class="endpoint">GET /api/status — Estado del servicio y total de fondos cargados</div>
    <div class="endpoint">GET /api/resumen — KPIs ejecutivos, acumulativo anual y top países</div>
    <div class="endpoint">GET /api/fondos?entidad=X&amp;clasificacion=ROJO&amp;eslabon=3&amp;pais=Bolivia&amp;limit=100 — Tabla de fondos con filtros</div>
    <div class="endpoint">GET /api/trazabilidad — Análisis completo por eslabón</div>
    <div class="endpoint">GET /api/entidades?top=30&amp;nivel=Alto — Ranking de entidades por riesgo</div>
    <div class="endpoint">GET /api/riesgo — Scores ICR/SOG/RES/VIA por entidad</div>
    <div class="endpoint">GET /api/mensual — Evolución mensual por región y sector</div>
    <div class="endpoint">GET /api/informe — Informe ejecutivo completo en Markdown</div>
    <div class="endpoint">POST /api/refresh (Header: X-Refresh-Token) — Ejecuta el pipeline</div>
  </div>

  <h2>🔄 Actualización de datos</h2>
  <div class="card">
    <p>El pipeline corre automáticamente cada día hábil a las 07:00 UTC via GitHub Actions, descargando:</p>
    <ul>
      <li><strong>AECID</strong> — Portal datos.aecid.es (intervenciones activas)</li>
      <li><strong>BDNS</strong> — Base de Datos Nacional de Subvenciones (convocatorias AECID)</li>
      <li><strong>PLACE</strong> — Portal de Contratación del Estado (contratos adjudicados)</li>
      <li><strong>LTAIBG</strong> — Registro manual de solicitudes de transparencia (completar en <code>data/raw/ltaibg_respuestas.csv</code>)</li>
    </ul>
    <p>Para forzar una actualización manual desde la terminal:</p>
    <code>python pipeline.py --forzar</code>
  </div>

  <h2>📂 Archivos generados</h2>
  <div class="card">
    <table>
      <thead><tr><th>Archivo</th><th>Descripción</th></tr></thead>
      <tbody>
        <tr><td><code>data/raw/aecid_intervenciones.csv</code></td><td>Intervenciones descargadas de AECID</td></tr>
        <tr><td><code>data/raw/bdns_subvenciones.csv</code></td><td>Convocatorias BDNS</td></tr>
        <tr><td><code>data/raw/place_contratos.csv</code></td><td>Contratos PLACE/OCDS</td></tr>
        <tr><td><code>data/raw/ltaibg_respuestas.csv</code></td><td>Solicitudes LTAIBG (completar manualmente)</td></tr>
        <tr><td><code>data/processed/trazabilidad_por_fondo.csv</code></td><td>Score trazabilidad por intervención</td></tr>
        <tr><td><code>data/processed/scores_riesgo.csv</code></td><td>Indicadores ICR/SOG/RES/VIA por entidad</td></tr>
        <tr><td><code>data/processed/analisis_completo.csv</code></td><td>Dataset completo para el dashboard</td></tr>
        <tr><td><code>reports/informe_ejecutivo.md</code></td><td>Informe ejecutivo en Markdown</td></tr>
      </tbody>
    </table>
  </div>

  <h2>📚 Marco teórico</h2>
  <div class="card">
    <p>El análisis se basa en la teoría de los <em>Fenómenos Corruptivos</em> desarrollada por el Ph.D. Vicente Humberto Monteverde, que conceptualiza la corrupción como <strong>transferencias regresivas de ingresos</strong> facilitadas por la discrecionalidad en las decisiones legales.</p>
    <p>Los 7 escenarios de transferencia identificados son: Privatización/Concesión, Contratos Públicos, Tarifas de Servicios, Precios Regulados, Salarios/Paritarias, Jubilaciones y Traslado de Impuestos.</p>
    <p>Referencia: Monteverde, V.H. (2019). <em>Economía Corruptiva</em>. Dialnet.</p>
  </div>

</main>
<footer>Monitor AECID v2.0 · github.com/Viny2030/Fenomenos_corruptivos_spain</footer>
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