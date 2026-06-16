# landing.py — Página de presentación del Monitor de Fenómenos Corruptivos Spain
# Agregar al main.py existente: importar LANDING_HTML y agregar el endpoint @app.get("/landing")

FOTO_BASE64 = "data:image/jpeg;base64,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"

LANDING_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Monitor Fenómenos Corruptivos — España · AECID</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#050f0a;color:#d1fae5}
nav{background:#071a10;border-bottom:1px solid #0d3320;padding:14px 28px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px}
.nav-brand{display:flex;align-items:center;gap:10px}
.nav-logo{width:34px;height:34px;background:#064e2e;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;border:1px solid #0d6e3f}
.nav-title{font-size:.9rem;font-weight:600;color:#a7f3d0}
.nav-sub{font-size:.7rem;color:#34795a}
.nav-links{display:flex;gap:6px;flex-wrap:wrap}
.nav-link{padding:5px 12px;border-radius:6px;border:1px solid #0d3320;color:#34d399;font-size:.76rem;text-decoration:none;transition:background .15s}
.nav-link:hover{background:#0d3320;color:#a7f3d0}
.hero{background:#071a10;padding:56px 36px 48px;text-align:center;border-bottom:1px solid #0d3320}
.hero-badge{display:inline-flex;align-items:center;gap:6px;background:#0a2e1a;color:#34d399;border:1px solid #0d6e3f;border-radius:20px;padding:4px 14px;font-size:.74rem;margin-bottom:20px}
.dot{width:7px;height:7px;background:#34d399;border-radius:50%;display:inline-block;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
.hero h1{font-size:2rem;font-weight:700;color:#a7f3d0;line-height:1.25;margin-bottom:12px;max-width:680px;margin-left:auto;margin-right:auto}
.hero h1 em{color:#34d399;font-style:normal}
.hero-sub{color:#4ade80;opacity:.8;font-size:.9rem;max-width:560px;margin:0 auto 28px;line-height:1.65}
.hero-tags{display:flex;justify-content:center;gap:8px;flex-wrap:wrap;margin-bottom:30px}
.hero-tag{background:#0a2218;border:1px solid #0d3320;color:#6ee7b7;padding:4px 12px;border-radius:8px;font-size:.74rem}
.hero-btns{display:flex;justify-content:center;gap:10px;flex-wrap:wrap}
.btn-p{background:#059669;color:#fff;border:none;padding:10px 22px;border-radius:8px;font-size:.85rem;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block}
.btn-p:hover{background:#047857}
.btn-g{background:transparent;color:#34d399;border:1px solid #0d3320;padding:10px 20px;border-radius:8px;font-size:.85rem;text-decoration:none;display:inline-block}
.btn-g:hover{background:#0a2218}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));border-bottom:1px solid #0d3320}
.stat{padding:22px 14px;text-align:center;border-right:1px solid #0d3320}
.stat:last-child{border-right:none}
.stat-val{font-size:1.5rem;font-weight:700;color:#34d399}
.stat-lbl{font-size:.7rem;color:#34795a;margin-top:4px}
.sec{padding:40px 28px;max-width:1200px;margin:0 auto}
.sec-title{font-size:1.1rem;font-weight:600;color:#a7f3d0;margin-bottom:6px}
.sec-sub{font-size:.8rem;color:#34795a;margin-bottom:22px}
.divider{border:none;border-top:1px solid #0d3320;margin:0}
.method-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.mcard{background:#071a10;border:1px solid #0d3320;border-radius:10px;padding:16px;display:flex;gap:12px}
.mpct{font-size:1.4rem;font-weight:700;min-width:50px;flex-shrink:0}
.m1{color:#34d399}.m2{color:#6ee7b7}.m3{color:#a7f3d0}.m4{color:#4ade80}
.mname{font-size:.82rem;font-weight:600;color:#a7f3d0;margin-bottom:4px}
.mdesc{font-size:.73rem;color:#34795a;line-height:1.5}
.mbar{height:3px;border-radius:2px;background:#34d399;margin-top:8px}
.esl-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}
.esl-card{background:#071a10;border:1px solid #0d3320;border-radius:8px;padding:10px 8px;text-align:center}
.esl-num{font-size:1rem;font-weight:700;color:#34d399;margin-bottom:3px}
.esl-name{font-size:.65rem;color:#6ee7b7;margin-bottom:4px;font-weight:600}
.esl-desc{font-size:.62rem;color:#34795a;line-height:1.35}
.rupt-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
.rcard{background:#071a10;border:1px solid #0d3320;border-radius:10px;padding:16px}
.rbadge{display:inline-block;background:#052e16;color:#34d399;border:1px solid #0d6e3f;border-radius:6px;font-size:.7rem;font-weight:700;padding:2px 8px;margin-bottom:8px}
.rname{font-size:.82rem;font-weight:600;color:#a7f3d0;margin-bottom:5px}
.rdesc{font-size:.73rem;color:#34795a;line-height:1.5}
.ind-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.icard{background:#071a10;border:1px solid #0d3320;border-radius:10px;padding:16px;display:flex;gap:10px;align-items:flex-start}
.ipct{font-size:1.05rem;font-weight:700;color:#34d399;min-width:38px;flex-shrink:0}
.iname{font-size:.82rem;font-weight:600;color:#a7f3d0;margin-bottom:3px}
.idesc{font-size:.73rem;color:#34795a;line-height:1.4}
.tech-row{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.tpill{background:#071a10;border:1px solid #0d3320;color:#6ee7b7;padding:5px 12px;border-radius:20px;font-size:.74rem;display:flex;align-items:center;gap:5px}
.tdot{width:5px;height:5px;border-radius:50%;background:#34d399;flex-shrink:0}
.autor-card{background:#071a10;border:1px solid #0d3320;border-radius:12px;padding:24px;display:flex;gap:20px;align-items:flex-start;margin-top:6px}
.autor-img{width:90px;height:90px;border-radius:50%;object-fit:cover;border:2px solid #34d399;flex-shrink:0}
.autor-name{font-size:1rem;font-weight:600;color:#a7f3d0;margin-bottom:4px}
.autor-role{font-size:.78rem;color:#34795a;line-height:1.6;margin-bottom:12px}
.autor-em{color:#34d399;font-style:normal}
.amail{display:inline-flex;align-items:center;gap:5px;background:#0a2218;color:#34d399;border:1px solid #0d3320;padding:5px 12px;border-radius:6px;font-size:.76rem;margin-right:6px;text-decoration:none}
.dona-header{text-align:center;padding:20px 0 14px}
.dona-header h3{font-size:1rem;color:#fbbf24;margin-bottom:5px}
.dona-header p{font-size:.8rem;color:#34795a}
.dona-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
.dcard{background:#071a10;border-radius:10px;padding:18px}
.dcard.ars{border:1px solid #0d6e3f;border-top:3px solid #34d399}
.dcard.usd{border:1px solid #0d6e3f;border-top:3px solid #6ee7b7}
.dcard.wire{border:1px solid #0d6e3f;border-top:3px solid #a7f3d0}
.dcard h4{font-size:.76rem;color:#6ee7b7;font-weight:600;margin-bottom:14px}
.drow{margin-bottom:9px}
.dlbl{font-size:.67rem;color:#34795a;text-transform:uppercase;letter-spacing:.04em;margin-bottom:2px}
.dval{font-size:.82rem;color:#d1fae5;font-weight:500}
.dval.mono{font-family:monospace;color:#34d399;background:#050f0a;padding:2px 7px;border-radius:4px;display:inline-block;font-size:.84rem}
.dval.alias{color:#6ee7b7;font-family:monospace;font-size:.84rem}
.disclaimer{background:#050f0a;border-top:1px solid #0d3320;padding:20px 28px;font-size:.72rem;color:#1a4a2e;text-align:center;line-height:1.65}
footer{background:#071a10;border-top:1px solid #0d3320;padding:16px 28px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}
.footer-t{font-size:.72rem;color:#1a4a2e}
.footer-l{display:flex;gap:14px}
.footer-l a{font-size:.72rem;color:#34795a;text-decoration:none}
.footer-l a:hover{color:#34d399}
@media(max-width:800px){
  .method-grid,.rupt-grid,.dona-grid,.ind-grid{grid-template-columns:1fr}
  .esl-grid{grid-template-columns:repeat(4,1fr)}
  .hero h1{font-size:1.4rem}
  .autor-card{flex-direction:column;align-items:center;text-align:center}
  .stats{grid-template-columns:repeat(3,1fr)}
}
</style>
</head>
<body>

<!-- NAV -->
<nav>
  <div class="nav-brand">
    <div class="nav-logo">🔍</div>
    <div>
      <div class="nav-title">Monitor de Fenómenos Corruptivos</div>
      <div class="nav-sub">España · AECID · Ph.D. Vicente Humberto Monteverde</div>
    </div>
  </div>
  <div class="nav-links">
    <a class="nav-link" href="/">Dashboard</a>
    <a class="nav-link" href="/manual">Manual</a>
    <a class="nav-link" href="/autor">Autor</a>
    <a class="nav-link" href="https://github.com/Viny2030/Fenomenos_corruptivos_spain" target="_blank">GitHub</a>
  </div>
</nav>

<!-- HERO -->
<div class="hero">
  <div class="hero-badge"><span class="dot"></span> Activo · Datos oficiales públicos · Código abierto</div>
  <h1>Monitor de Trazabilidad <em>AECID</em><br>Fenómenos Corruptivos — España</h1>
  <p class="hero-sub">Auditoría algorítmica de fondos de cooperación internacional. Del presupuesto español al beneficiario final — 7 eslabones, 3 rupturas estructurales, 1 índice de riesgo explicable.</p>
  <div class="hero-tags">
    <div class="hero-tag">🔍 Trazabilidad de fondos</div>
    <div class="hero-tag">🌍 AECID · OOII · ONGD</div>
    <div class="hero-tag">⚙️ XAI · Algoritmo explicable</div>
    <div class="hero-tag">📡 API REST</div>
    <div class="hero-tag">⭐ Open Source</div>
  </div>
  <div class="hero-btns">
    <a class="btn-p" href="/">Abrir Dashboard →</a>
    <a class="btn-g" href="https://github.com/Viny2030/Fenomenos_corruptivos_spain" target="_blank">Ver en GitHub</a>
  </div>
</div>

<!-- STATS -->
<div class="stats">
  <div class="stat"><div class="stat-val">~1.000M€</div><div class="stat-lbl">AECID / año</div></div>
  <div class="stat"><div class="stat-val">7</div><div class="stat-lbl">Eslabones</div></div>
  <div class="stat"><div class="stat-val">3</div><div class="stat-lbl">Rupturas estructurales</div></div>
  <div class="stat"><div class="stat-val">8%</div><div class="stat-lbl">Trazabilidad beneficiario</div></div>
  <div class="stat"><div class="stat-val">4</div><div class="stat-lbl">Indicadores de riesgo</div></div>
  <div class="stat"><div class="stat-val">100%</div><div class="stat-lbl">Datos públicos oficiales</div></div>
</div>

<!-- METODOLOGÍA -->
<hr class="divider">
<div class="sec">
  <div class="sec-title">Metodología</div>
  <div class="sec-sub">Índice de Riesgo Institucional (IRI) — 4 dimensiones ponderadas. Cada alerta es explicable, no es una caja negra.</div>
  <div class="method-grid">
    <div class="mcard"><div><div class="mpct m1">35%</div><div class="mbar" style="width:35%"></div></div><div><div class="mname">Riesgo Financiero</div><div class="mdesc">Anomalías en ejecución presupuestaria, flujos de pago y operaciones de tesorería de la AECID</div></div></div>
    <div class="mcard"><div><div class="mpct m2">30%</div><div class="mbar" style="width:30%;opacity:.8"></div></div><div><div class="mname">Riesgo de Contratación</div><div class="mdesc">Detección XAI de patrones irregulares en licitaciones y contratos (PLACE + BDNS + OCDS)</div></div></div>
    <div class="mcard"><div><div class="mpct m3">20%</div><div class="mbar" style="width:20%;opacity:.6"></div></div><div><div class="mname">Riesgo Operacional</div><div class="mdesc">Métricas de rendimiento institucional y de gestión de las entidades receptoras de fondos</div></div></div>
    <div class="mcard"><div><div class="mpct m4">15%</div><div class="mbar" style="width:15%;opacity:.45"></div></div><div><div class="mname">Riesgo de Datos</div><div class="mdesc">Calidad, completitud y oportunidad de la información pública disponible por fuente</div></div></div>
  </div>
</div>

<!-- ESLABONES -->
<hr class="divider">
<div class="sec">
  <div class="sec-title">Modelo de 7 Eslabones</div>
  <div class="sec-sub">Cada fondo es evaluado según el último eslabón de trazabilidad alcanzado. Score de 14/100 (E1) a 100/100 (E7).</div>
  <div class="esl-grid">
    <div class="esl-card"><div class="esl-num">E1</div><div class="esl-name">Presupuesto</div><div class="esl-desc">PGE España aprobado</div></div>
    <div class="esl-card"><div class="esl-num">E2</div><div class="esl-name">Transferencia</div><div class="esl-desc">AECID sede → entidad</div></div>
    <div class="esl-card"><div class="esl-num">E3</div><div class="esl-name">OOII/BDNS</div><div class="esl-desc">Canal receptor registrado</div></div>
    <div class="esl-card"><div class="esl-num">E4</div><div class="esl-name">Destino</div><div class="esl-desc">País / región declarado</div></div>
    <div class="esl-card"><div class="esl-num">E5</div><div class="esl-name">Contratos</div><div class="esl-desc">PLACE / OCDS publicado</div></div>
    <div class="esl-card"><div class="esl-num">E6</div><div class="esl-name">Justificantes</div><div class="esl-desc">Auditoría / LTAIBG</div></div>
    <div class="esl-card" style="border-color:#0d6e3f"><div class="esl-num" style="color:#6ee7b7">E7</div><div class="esl-name" style="color:#6ee7b7">Beneficiario</div><div class="esl-desc">NIF / nombre identificado</div></div>
  </div>
</div>

<!-- RUPTURAS -->
<hr class="divider">
<div class="sec">
  <div class="sec-title">Las 3 Rupturas Estructurales</div>
  <div class="sec-sub">Explican por qué la trazabilidad colapsa entre el eslabón 3 y el 7.</div>
  <div class="rupt-grid">
    <div class="rcard">
      <div class="rbadge">R1</div>
      <div class="rname">OOII — Caja negra</div>
      <div class="rdesc">Fondos transferidos a PNUD, UNICEF, FAO, ACNUR… que agregan contribuciones multi-donante sin desglosar la aportación española en el estándar IATI. La trazabilidad se corta en E3.</div>
    </div>
    <div class="rcard">
      <div class="rbadge">R2</div>
      <div class="rname">Sub-contratación sin OCDS</div>
      <div class="rdesc">Contratos adjudicados directamente o sin publicación en el Portal de la Contratación del Estado (PLACE) bajo el estándar Open Contracting Data Standard.</div>
    </div>
    <div class="rcard">
      <div class="rbadge">R3</div>
      <div class="rname">Sin justificante auditable</div>
      <div class="rdesc">Proyectos con importe superior a 500.000€ sin evaluación final publicada ni respuesta favorable a solicitud de información (Ley 19/2013 de Transparencia).</div>
    </div>
  </div>
</div>

<!-- INDICADORES -->
<hr class="divider">
<div class="sec">
  <div class="sec-title">Indicadores de Riesgo</div>
  <div class="sec-sub">Score integrado = 60% riesgo (ICR + SOG + RES + VIA) + 40% trazabilidad invertida. Clasificación: VERDE / AMARILLO / NARANJA / ROJO.</div>
  <div class="ind-grid">
    <div class="icard">
      <div class="ipct">ICR<br><span style="font-size:.68rem;color:#34795a;font-weight:400">15%</span></div>
      <div><div class="iname">Índice de Concentración de Receptores</div><div class="idesc">HHI normalizado. Detecta si unos pocos actores concentran la mayoría de los fondos de cooperación.</div></div>
    </div>
    <div class="icard">
      <div class="ipct">SOG<br><span style="font-size:.68rem;color:#34795a;font-weight:400">35%</span></div>
      <div><div class="iname">Score de Opacidad en la Gestión</div><div class="idesc">Suma ponderada de indicadores binarios: es OOII, tiene R2, tiene R3, adjudicación directa, sin país declarado.</div></div>
    </div>
    <div class="icard">
      <div class="ipct">RES<br><span style="font-size:.68rem;color:#34795a;font-weight:400">30%</span></div>
      <div><div class="iname">Riesgo por Eslabón de Corte</div><div class="idesc">Inverso del score de trazabilidad. Cuanto más bajo el eslabón alcanzado, mayor el riesgo asignado.</div></div>
    </div>
    <div class="icard">
      <div class="ipct">VIA<br><span style="font-size:.68rem;color:#34795a;font-weight:400">20%</span></div>
      <div><div class="iname">Vulnerabilidad Institucional del país receptor</div><div class="idesc">Proxy del Índice de Gobernanza del Banco Mundial (WGI 0-100) para el país de destino del fondo.</div></div>
    </div>
  </div>
</div>

<!-- TECNOLOGÍA -->
<hr class="divider">
<div class="sec">
  <div class="sec-title">Stack tecnológico</div>
  <div class="sec-sub">Open source · Python + FastAPI · Railway · Datos oficiales AECID, BDNS, PLACE, IATI, OCDE. Actualización diaria via GitHub Actions.</div>
  <div class="tech-row">
    <div class="tpill"><div class="tdot"></div>Python 3</div>
    <div class="tpill"><div class="tdot"></div>FastAPI</div>
    <div class="tpill"><div class="tdot"></div>Uvicorn</div>
    <div class="tpill"><div class="tdot"></div>Railway</div>
    <div class="tpill"><div class="tdot"></div>XAI / Explainable AI</div>
    <div class="tpill"><div class="tdot"></div>AECID Open Data</div>
    <div class="tpill"><div class="tdot"></div>BDNS</div>
    <div class="tpill"><div class="tdot"></div>PLACE / OCDS</div>
    <div class="tpill"><div class="tdot"></div>IATI Standard</div>
    <div class="tpill"><div class="tdot"></div>OCDE CRS</div>
    <div class="tpill"><div class="tdot"></div>Ley 19/2013 LTAIBG</div>
    <div class="tpill"><div class="tdot"></div>GitHub Actions</div>
    <div class="tpill"><div class="tdot"></div>Swagger UI</div>
  </div>
</div>

<!-- AUTOR -->
<hr class="divider">
<div class="sec">
  <div class="sec-title">Autor</div>
  <div class="sec-sub">Investigador responsable del proyecto</div>
  <div class="autor-card">
    <img class="autor-img" src="__FOTO__" alt="Ph.D. Vicente Humberto Monteverde">
    <div style="flex:1">
      <div class="autor-name">Ph.D. Vicente Humberto Monteverde</div>
      <div class="autor-role">
        Doctor en Ciencias Económicas · Investigador en economía política y fenómenos de corrupción.<br>
        Autor de la teoría de <em class="autor-em">Transferencia Regresiva de Ingresos</em> y desarrollador
        del algoritmo <em class="autor-em">XAI</em> aplicado al análisis de contrataciones públicas.<br>
        Publicaciones en <em class="autor-em">Journal of Financial Crime</em> (Emerald Publishing).
        Asesor en transparencia y auditoría algorítmica del gasto público.
      </div>
      <a class="amail" href="mailto:vhmonte@retina.ar">✉️ vhmonte@retina.ar</a>
      <a class="amail" href="mailto:viny01958@gmail.com">✉️ viny01958@gmail.com</a>
    </div>
  </div>

  <!-- DONACIONES -->
  <div class="dona-header">
    <h3>💛 Apoyar este proyecto — Donaciones voluntarias</h3>
    <p>Si este proyecto te resulta útil, podés apoyarlo con una donación voluntaria.</p>
  </div>
  <div class="dona-grid">
    <div class="dcard ars">
      <h4>🇦🇷 Argentina · Pesos (ARS)</h4>
      <div class="drow"><div class="dlbl">Tipo</div><div class="dval">Caja de Ahorro</div></div>
      <div class="drow"><div class="dlbl">CBU</div><div class="dval mono">0140005203400552652310</div></div>
      <div class="drow"><div class="dlbl">Alias</div><div class="dval alias">ALGORIT.MONTE.PESOS</div></div>
      <div class="drow"><div class="dlbl">Titular</div><div class="dval">Vicente Humberto Monteverde</div></div>
      <div class="drow"><div class="dlbl">CUIL/CUIT</div><div class="dval mono">20-12034411-1</div></div>
    </div>
    <div class="dcard usd">
      <h4>🇦🇷 Argentina · Dólares (USD)</h4>
      <div class="drow"><div class="dlbl">Tipo</div><div class="dval">Caja de Ahorro Dólares</div></div>
      <div class="drow"><div class="dlbl">CBU</div><div class="dval mono">0140005204400550329709</div></div>
      <div class="drow"><div class="dlbl">Alias</div><div class="dval alias">ALGO.MONTE.DOLARES</div></div>
      <div class="drow"><div class="dlbl">Titular</div><div class="dval">Vicente Humberto Monteverde</div></div>
      <div class="drow"><div class="dlbl">CUIL/CUIT</div><div class="dval mono">20-12034411-1</div></div>
    </div>
    <div class="dcard wire">
      <h4>🌐 Desde el Exterior (USD Wire)</h4>
      <div class="drow"><div class="dlbl">Banco</div><div class="dval">Banco Santander Rio</div></div>
      <div class="drow"><div class="dlbl">Beneficiario</div><div class="dval">Vicente Humberto Monteverde</div></div>
      <div class="drow"><div class="dlbl">Dirección</div><div class="dval">Av. Directorio 3024 PB DTO 04</div></div>
      <div class="drow"><div class="dlbl">Cuenta USD</div><div class="dval mono">005200183500</div></div>
      <div class="drow"><div class="dlbl">SWIFT / BIC</div><div class="dval alias">BSCHUYMM</div></div>
      <div class="drow"><div class="dlbl">CUIT</div><div class="dval mono">20-12034411-1</div></div>
    </div>
  </div>
</div>

<!-- DISCLAIMER -->
<div class="disclaimer">
  Esta herramienta es de naturaleza experimental y académica. Los resultados son indicadores algorítmicos de riesgo —
  no implican juicio legal, acusación ni determinación de responsabilidad respecto de ninguna empresa, institución o individuo.
  El objetivo es promover la transparencia y el debate público informado sobre el gasto en cooperación internacional.
</div>

<!-- FOOTER -->
<footer>
  <div class="footer-t">Monitor Fenómenos Corruptivos Spain · github.com/Viny2030 · Ph.D. Vicente Humberto Monteverde</div>
  <div class="footer-l">
    <a href="/">Dashboard</a>
    <a href="/manual">Manual</a>
    <a href="/autor">Autor</a>
    <a href="https://github.com/Viny2030/Fenomenos_corruptivos_spain" target="_blank">GitHub</a>
    <a href="mailto:vhmonte@retina.ar">Contacto</a>
  </div>
</footer>

</body>
</html>""".replace("__FOTO__", FOTO_BASE64)


# ─────────────────────────────────────────────────────────────────────────────
# INSTRUCCIONES DE INTEGRACIÓN EN main.py
# ─────────────────────────────────────────────────────────────────────────────
# 1. Copiar este archivo al mismo directorio que main.py
# 2. En main.py agregar al inicio:
#
#    from landing import LANDING_HTML
#
# 3. Agregar el endpoint después de @app.get("/autor"):
#
#    @app.get("/landing", response_class=HTMLResponse)
#    def landing():
#        return HTMLResponse(LANDING_HTML)
#
# O si querés que sea la página principal, reemplazar el endpoint existente "/" :
#
#    @app.get("/", response_class=HTMLResponse)
#    def landing():
#        return HTMLResponse(LANDING_HTML)
#
# ─────────────────────────────────────────────────────────────────────────────
