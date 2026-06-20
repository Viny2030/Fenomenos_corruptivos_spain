"""
main.py — FastAPI Monitor Trazabilidad AECID
Ph.D. Monteverde — Algoritmos contra la Corrupción
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

ROOT = Path(__file__).parent
DATA_DIR = Path("/app/data") if Path("/app").exists() else ROOT / "data"
DATA_PRO = DATA_DIR / "processed"
REPORTS  = ROOT / "reports"
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN", "dev-token")

FOTO_BASE64 = "data:image/jpeg;base64,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"


# ─────────────────────────────────────────────────────────────────────────────
# LANDING HTML
# ─────────────────────────────────────────────────────────────────────────────
LANDING_HTML = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Monitor Fenómenos Corruptivos — España · AECID</title>

<!-- Google Analytics (GA4) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-0JK8GYT9GT"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-0JK8GYT9GT');
</script>

<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#050f0a;color:#d1fae5}}
nav{{background:#071a10;border-bottom:1px solid #0d3320;padding:14px 28px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px}}
.nav-brand{{display:flex;align-items:center;gap:10px}}
.nav-logo{{width:34px;height:34px;background:#064e2e;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;border:1px solid #0d6e3f}}
.nav-title{{font-size:.9rem;font-weight:600;color:#a7f3d0}}
.nav-sub{{font-size:.7rem;color:#34795a}}
.nav-links{{display:flex;gap:6px;flex-wrap:wrap}}
.nav-link{{padding:5px 12px;border-radius:6px;border:1px solid #0d3320;color:#34d399;font-size:.76rem;text-decoration:none;transition:background .15s}}
.nav-link:hover{{background:#0d3320;color:#a7f3d0}}
.hero{{background:#071a10;padding:56px 36px 48px;text-align:center;border-bottom:1px solid #0d3320}}
.hero-badge{{display:inline-flex;align-items:center;gap:6px;background:#0a2e1a;color:#34d399;border:1px solid #0d6e3f;border-radius:20px;padding:4px 14px;font-size:.74rem;margin-bottom:20px}}
.dot{{width:7px;height:7px;background:#34d399;border-radius:50%;display:inline-block;animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.35}}}}
.hero h1{{font-size:2rem;font-weight:700;color:#a7f3d0;line-height:1.25;margin-bottom:12px;max-width:680px;margin-left:auto;margin-right:auto}}
.hero h1 em{{color:#34d399;font-style:normal}}
.hero-sub{{color:#4ade80;opacity:.8;font-size:.9rem;max-width:560px;margin:0 auto 28px;line-height:1.65}}
.hero-tags{{display:flex;justify-content:center;gap:8px;flex-wrap:wrap;margin-bottom:30px}}
.hero-tag{{background:#0a2218;border:1px solid #0d3320;color:#6ee7b7;padding:4px 12px;border-radius:8px;font-size:.74rem}}
.hero-btns{{display:flex;justify-content:center;gap:10px;flex-wrap:wrap}}
.btn-p{{background:#059669;color:#fff;border:none;padding:10px 22px;border-radius:8px;font-size:.85rem;font-weight:600;text-decoration:none;display:inline-block}}
.btn-p:hover{{background:#047857}}
.btn-g{{background:transparent;color:#34d399;border:1px solid #0d3320;padding:10px 20px;border-radius:8px;font-size:.85rem;text-decoration:none;display:inline-block}}
.btn-g:hover{{background:#0a2218}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));border-bottom:1px solid #0d3320}}
.stat{{padding:22px 14px;text-align:center;border-right:1px solid #0d3320}}
.stat:last-child{{border-right:none}}
.stat-val{{font-size:1.5rem;font-weight:700;color:#34d399}}
.stat-lbl{{font-size:.7rem;color:#34795a;margin-top:4px}}
.sec{{padding:40px 28px;max-width:1200px;margin:0 auto}}
.sec-title{{font-size:1.1rem;font-weight:600;color:#a7f3d0;margin-bottom:6px}}
.sec-sub{{font-size:.8rem;color:#34795a;margin-bottom:22px}}
.divider{{border:none;border-top:1px solid #0d3320;margin:0}}
.method-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.mcard{{background:#071a10;border:1px solid #0d3320;border-radius:10px;padding:16px;display:flex;gap:12px}}
.mpct{{font-size:1.4rem;font-weight:700;min-width:50px;flex-shrink:0}}
.m1{{color:#34d399}}.m2{{color:#6ee7b7}}.m3{{color:#a7f3d0}}.m4{{color:#4ade80}}
.mname{{font-size:.82rem;font-weight:600;color:#a7f3d0;margin-bottom:4px}}
.mdesc{{font-size:.73rem;color:#34795a;line-height:1.5}}
.mbar{{height:3px;border-radius:2px;background:#34d399;margin-top:8px}}
.esl-grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}}
.esl-card{{background:#071a10;border:1px solid #0d3320;border-radius:8px;padding:10px 8px;text-align:center}}
.esl-num{{font-size:1rem;font-weight:700;color:#34d399;margin-bottom:3px}}
.esl-name{{font-size:.65rem;color:#6ee7b7;margin-bottom:4px;font-weight:600}}
.esl-desc{{font-size:.62rem;color:#34795a;line-height:1.35}}
.rupt-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}}
.rcard{{background:#071a10;border:1px solid #0d3320;border-radius:10px;padding:16px}}
.rbadge{{display:inline-block;background:#052e16;color:#34d399;border:1px solid #0d6e3f;border-radius:6px;font-size:.7rem;font-weight:700;padding:2px 8px;margin-bottom:8px}}
.rname{{font-size:.82rem;font-weight:600;color:#a7f3d0;margin-bottom:5px}}
.rdesc{{font-size:.73rem;color:#34795a;line-height:1.5}}
.ind-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.icard{{background:#071a10;border:1px solid #0d3320;border-radius:10px;padding:16px;display:flex;gap:10px;align-items:flex-start}}
.ipct{{font-size:1.05rem;font-weight:700;color:#34d399;min-width:38px;flex-shrink:0}}
.iname{{font-size:.82rem;font-weight:600;color:#a7f3d0;margin-bottom:3px}}
.idesc{{font-size:.73rem;color:#34795a;line-height:1.4}}
.tech-row{{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}}
.tpill{{background:#071a10;border:1px solid #0d3320;color:#6ee7b7;padding:5px 12px;border-radius:20px;font-size:.74rem;display:flex;align-items:center;gap:5px}}
.tdot{{width:5px;height:5px;border-radius:50%;background:#34d399;flex-shrink:0}}
.autor-card{{background:#071a10;border:1px solid #0d3320;border-radius:12px;padding:24px;display:flex;gap:20px;align-items:flex-start;margin-top:6px}}
.autor-img{{width:90px;height:90px;border-radius:50%;object-fit:cover;border:2px solid #34d399;flex-shrink:0}}
.autor-name{{font-size:1rem;font-weight:600;color:#a7f3d0;margin-bottom:4px}}
.autor-role{{font-size:.78rem;color:#34795a;line-height:1.6;margin-bottom:12px}}
.autor-em{{color:#34d399;font-style:normal}}
.amail{{display:inline-flex;align-items:center;gap:5px;background:#0a2218;color:#34d399;border:1px solid #0d3320;padding:5px 12px;border-radius:6px;font-size:.76rem;margin-right:6px;text-decoration:none}}
.dona-header{{text-align:center;padding:20px 0 14px}}
.dona-header h3{{font-size:1rem;color:#fbbf24;margin-bottom:5px}}
.dona-header p{{font-size:.8rem;color:#34795a}}
.dona-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}}
.dcard{{background:#071a10;border-radius:10px;padding:18px}}
.dcard.ars{{border:1px solid #0d6e3f;border-top:3px solid #34d399}}
.dcard.usd{{border:1px solid #0d6e3f;border-top:3px solid #6ee7b7}}
.dcard.wire{{border:1px solid #0d6e3f;border-top:3px solid #a7f3d0}}
.dcard h4{{font-size:.76rem;color:#6ee7b7;font-weight:600;margin-bottom:14px}}
.drow{{margin-bottom:9px}}
.dlbl{{font-size:.67rem;color:#34795a;text-transform:uppercase;letter-spacing:.04em;margin-bottom:2px}}
.dval{{font-size:.82rem;color:#d1fae5;font-weight:500}}
.dval.mono{{font-family:monospace;color:#34d399;background:#050f0a;padding:2px 7px;border-radius:4px;display:inline-block;font-size:.84rem}}
.dval.alias{{color:#6ee7b7;font-family:monospace;font-size:.84rem}}
.disclaimer{{background:#050f0a;border-top:1px solid #0d3320;padding:20px 28px;font-size:.72rem;color:#1a4a2e;text-align:center;line-height:1.65}}
footer{{background:#071a10;border-top:1px solid #0d3320;padding:16px 28px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}}
.footer-t{{font-size:.72rem;color:#1a4a2e}}
.footer-l{{display:flex;gap:14px}}
.footer-l a{{font-size:.72rem;color:#34795a;text-decoration:none}}
.footer-l a:hover{{color:#34d399}}
@media(max-width:800px){{
  .method-grid,.rupt-grid,.dona-grid,.ind-grid{{grid-template-columns:1fr}}
  .esl-grid{{grid-template-columns:repeat(4,1fr)}}
  .hero h1{{font-size:1.4rem}}
  .autor-card{{flex-direction:column;align-items:center;text-align:center}}
  .stats{{grid-template-columns:repeat(3,1fr)}}
}}
</style>
</head>
<body>

<nav>
  <div class="nav-brand">
    <div class="nav-logo">🔍</div>
    <div>
      <div class="nav-title">Monitor de Fenómenos Corruptivos</div>
      <div class="nav-sub">España · AECID · Ph.D. Vicente Humberto Monteverde</div>
    </div>
  </div>
  <div class="nav-links">
    <a class="nav-link" href="/dashboard">Dashboard</a>
    <a class="nav-link" href="/manual">Manual</a>
    <a class="nav-link" href="/autor">Autor</a>
    <a class="nav-link" href="https://github.com/Viny2030/Fenomenos_corruptivos_spain" target="_blank">GitHub</a>
  </div>
</nav>

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
    <a class="btn-p" href="/dashboard">Abrir Dashboard →</a>
    <a class="btn-g" href="https://github.com/Viny2030/Fenomenos_corruptivos_spain" target="_blank">Ver en GitHub</a>
  </div>
</div>

<div class="stats">
  <div class="stat"><div class="stat-val">~1.000M€</div><div class="stat-lbl">AECID / año</div></div>
  <div class="stat"><div class="stat-val">7</div><div class="stat-lbl">Eslabones</div></div>
  <div class="stat"><div class="stat-val">3</div><div class="stat-lbl">Rupturas estructurales</div></div>
  <div class="stat"><div class="stat-val">8%</div><div class="stat-lbl">Trazabilidad beneficiario</div></div>
  <div class="stat"><div class="stat-val">4</div><div class="stat-lbl">Indicadores de riesgo</div></div>
  <div class="stat"><div class="stat-val">100%</div><div class="stat-lbl">Datos públicos oficiales</div></div>
</div>

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

<hr class="divider">
<div class="sec">
  <div class="sec-title">Las 3 Rupturas Estructurales</div>
  <div class="sec-sub">Explican por qué la trazabilidad colapsa entre el eslabón 3 y el 7.</div>
  <div class="rupt-grid">
    <div class="rcard"><div class="rbadge">R1</div><div class="rname">OOII — Caja negra</div><div class="rdesc">Fondos a PNUD, UNICEF, FAO, ACNUR… que agregan contribuciones multi-donante sin desglosar la aportación española en IATI. La trazabilidad se corta en E3.</div></div>
    <div class="rcard"><div class="rbadge">R2</div><div class="rname">Sub-contratación sin OCDS</div><div class="rdesc">Contratos adjudicados sin publicación en el Portal de la Contratación del Estado (PLACE) bajo el estándar Open Contracting Data Standard.</div></div>
    <div class="rcard"><div class="rbadge">R3</div><div class="rname">Sin justificante auditable</div><div class="rdesc">Proyectos &gt;500.000€ sin evaluación final publicada ni respuesta favorable a solicitud de información (Ley 19/2013 Transparencia).</div></div>
  </div>
</div>

<hr class="divider">
<div class="sec">
  <div class="sec-title">Indicadores de Riesgo</div>
  <div class="sec-sub">Score integrado = 60% riesgo (ICR + SOG + RES + VIA) + 40% trazabilidad invertida. Clasificación: VERDE / AMARILLO / NARANJA / ROJO.</div>
  <div class="ind-grid">
    <div class="icard"><div class="ipct">ICR<br><span style="font-size:.68rem;color:#34795a;font-weight:400">15%</span></div><div><div class="iname">Índice de Concentración de Receptores</div><div class="idesc">HHI normalizado. Detecta si unos pocos actores concentran la mayoría de los fondos.</div></div></div>
    <div class="icard"><div class="ipct">SOG<br><span style="font-size:.68rem;color:#34795a;font-weight:400">35%</span></div><div><div class="iname">Score de Opacidad en la Gestión</div><div class="idesc">Suma ponderada de indicadores binarios: es OOII, tiene R2, tiene R3, adjudicación directa, sin país declarado.</div></div></div>
    <div class="icard"><div class="ipct">RES<br><span style="font-size:.68rem;color:#34795a;font-weight:400">30%</span></div><div><div class="iname">Riesgo por Eslabón de Corte</div><div class="idesc">Inverso del score de trazabilidad. Cuanto más bajo el eslabón alcanzado, mayor el riesgo.</div></div></div>
    <div class="icard"><div class="ipct">VIA<br><span style="font-size:.68rem;color:#34795a;font-weight:400">20%</span></div><div><div class="iname">Vulnerabilidad Institucional</div><div class="idesc">Proxy del Índice de Gobernanza del Banco Mundial (WGI 0-100) para el país receptor del fondo.</div></div></div>
  </div>
</div>

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
  </div>
</div>

<hr class="divider">
<div class="sec">
  <div class="sec-title">Autor</div>
  <div class="sec-sub">Investigador responsable del proyecto</div>
  <div class="autor-card">
    <img class="autor-img" src="{FOTO_BASE64}" alt="Ph.D. Vicente Humberto Monteverde">
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

<div class="disclaimer">
  Esta herramienta es de naturaleza experimental y académica. Los resultados son indicadores algorítmicos de riesgo —
  no implican juicio legal, acusación ni determinación de responsabilidad respecto de ninguna empresa, institución o individuo.
  El objetivo es promover la transparencia y el debate público informado sobre el gasto en cooperación internacional.
</div>

<footer>
  <div class="footer-t">Monitor Fenómenos Corruptivos Spain · github.com/Viny2030 · Ph.D. Vicente Humberto Monteverde</div>
  <div class="footer-l">
    <a href="/dashboard">Dashboard</a>
    <a href="/manual">Manual</a>
    <a href="/autor">Autor</a>
    <a href="https://github.com/Viny2030/Fenomenos_corruptivos_spain" target="_blank">GitHub</a>
    <a href="mailto:vhmonte@retina.ar">Contacto</a>
  </div>
</footer>

</body>
</html>"""

# ─────────────────────────────────────────────────────────────────────────────
# ESTILOS Y NAV COMUNES (dashboard y manual)
# ─────────────────────────────────────────────────────────────────────────────
_COMMON_STYLES = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#0f1117;color:#e0e0e0}
header{background:#1a1d2e;padding:18px 28px;border-bottom:2px solid #2d3561;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px}
header h1{font-size:1.3rem;color:#fff}
header span.sub{font-size:0.8rem;color:#7c8db5}
.badge{background:#2d3561;color:#7eb8f7;padding:3px 10px;border-radius:12px;font-size:0.75rem}
.nav-links{display:flex;gap:8px}
.nav-links a{background:#2d3561;color:#7eb8f7;padding:6px 14px;border-radius:6px;font-size:0.82rem;text-decoration:none;transition:background .2s}
.nav-links a:hover,.nav-links a.active{background:#3b82f6;color:#fff}
footer{text-align:center;padding:16px;color:#4a5568;font-size:0.75rem;border-top:1px solid #1a1d2e;margin-top:24px}
a{color:#7eb8f7;text-decoration:none}
a:hover{text-decoration:underline}
"""

def _nav(active="landing"):
    links = [
        ("landing",    "/",          "🏠 Inicio"),
        ("dashboard",  "/dashboard", "📊 Dashboard"),
        ("manual",     "/manual",    "📖 Manual"),
        ("autor",      "/autor",     "👤 Autor"),
    ]
    return "".join(
        f'<a href="{href}" class="{"active" if k==active else ""}">{label}</a>'
        for k, href, label in links
    )

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD HTML
# ─────────────────────────────────────────────────────────────────────────────
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Monitor Trazabilidad AECID</title>

<!-- Google Analytics (GA4) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-0JK8GYT9GT"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-0JK8GYT9GT');
</script>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#0f1117;color:#e0e0e0}
header{background:#1a1d2e;padding:18px 28px;border-bottom:2px solid #2d3561;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px}
header h1{font-size:1.3rem;color:#fff}
header span.sub{font-size:0.8rem;color:#7c8db5}
.badge{background:#2d3561;color:#7eb8f7;padding:3px 10px;border-radius:12px;font-size:0.75rem}
.nav-links{display:flex;gap:8px}
.nav-links a{background:#2d3561;color:#7eb8f7;padding:6px 14px;border-radius:6px;font-size:0.82rem;text-decoration:none;transition:background .2s}
.nav-links a:hover,.nav-links a.active{background:#3b82f6;color:#fff}
main{padding:20px 28px;max-width:1400px;margin:0 auto}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:24px}
.kpi{background:#1a1d2e;border:1px solid #2d3561;border-radius:10px;padding:16px}
.kpi .val{font-size:1.8rem;font-weight:700;color:#7eb8f7}
.kpi .lbl{font-size:0.75rem;color:#7c8db5;margin-top:4px}
.kpi.alerta .val{color:#f87171}
.kpi.medio .val{color:#fbbf24}
.kpi.ok .val{color:#34d399}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:20px}
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
.r1{background:#f87171}.r2{background:#fbbf24}.r3{background:#fb923c}
.filters{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.filters input,.filters select{background:#0f1117;border:1px solid #2d3561;color:#e0e0e0;padding:5px 10px;border-radius:6px;font-size:0.82rem}
.tabs{display:flex;gap:4px;margin-bottom:14px}
.tab{padding:5px 14px;border-radius:6px;border:1px solid #2d3561;cursor:pointer;font-size:0.8rem;color:#a0aec0;background:#0f1117}
.tab.active{background:#2d3561;color:#fff}
footer{text-align:center;padding:16px;color:#4a5568;font-size:0.75rem;border-top:1px solid #1a1d2e;margin-top:24px}
@media(max-width:900px){.grid2{grid-template-columns:1fr}}
</style>
</head>
<body>
<header>
  <div>
    <h1>🔍 Monitor Trazabilidad AECID</h1>
    <span class="sub">Ph.D. Vicente Humberto Monteverde — Algoritmos contra la Corrupción</span>
  </div>
  <div style="display:flex;align-items:center;gap:12px">
    <span class="badge" id="ts">Cargando...</span>
    <nav class="nav-links">
      <a href="/">🏠 Inicio</a>
      <a href="/dashboard" class="active">📊 Dashboard</a>
      <a href="/manual">📖 Manual</a>
      <a href="/autor">👤 Autor</a>
    </nav>
  </div>
</header>
<main>
<div class="kpis" id="kpis"></div>
<div class="grid2">
  <div class="card"><h3>🔗 Rupturas de trazabilidad</h3><div id="rupturas"></div><div class="chart-wrap" style="height:160px;margin-top:12px"><canvas id="chartRupturas"></canvas></div></div>
  <div class="card"><h3>📊 Distribución por eslabón</h3><div class="chart-wrap"><canvas id="chartEslabones"></canvas></div></div>
</div>
<div class="grid2">
  <div class="card"><h3>📈 Evolución anual acumulada (M€)</h3><div class="chart-wrap tall"><canvas id="chartAnual"></canvas></div></div>
  <div class="card"><h3>🌍 Distribución por región (M€)</h3><div class="chart-wrap tall"><canvas id="chartRegion"></canvas></div></div>
</div>
<div class="grid2">
  <div class="card"><h3>🗺️ Top países por importe</h3><div class="chart-wrap tall"><canvas id="chartPaises"></canvas></div></div>
  <div class="card"><h3>📆 Evolución mensual por región</h3><div class="tabs" id="tabsRegion"></div><div class="chart-wrap tall"><canvas id="chartMensual"></canvas></div></div>
</div>
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
<div class="card">
  <h3>📋 Fondos analizados</h3>
  <div class="filters">
    <input id="busq-fondo" placeholder="Buscar fondo o entidad..." oninput="filtrarFondos()">
    <select id="filtro-clasif" onchange="filtrarFondos()"><option value="">Todas las clasificaciones</option><option>ROJO</option><option>NARANJA</option><option>AMARILLO</option><option>VERDE</option></select>
    <select id="filtro-eslabon" onchange="filtrarFondos()"><option value="">Todos los eslabones</option><option value="3">E3</option><option value="4">E4</option><option value="5">E5</option><option value="6">E6</option><option value="7">E7</option></select>
    <select id="filtro-año" onchange="filtrarFondos()"><option value="">Todos los años</option><option>2021</option><option>2022</option><option>2023</option><option>2024</option></select>
  </div>
  <table id="tabla-fondos">
    <thead><tr><th>Título</th><th>Entidad</th><th>País</th><th>Año</th><th>Importe</th><th>Eslabón</th><th>Trazabilidad</th><th>Clasif.</th></tr></thead>
    <tbody></tbody>
  </table>
</div>
</main>
<footer>Monitor AECID v2.0 · github.com/Viny2030/Fenomenos_corruptivos_spain · Actualización diaria via GitHub Actions</footer>
<script>
const COLORS=['#3b82f6','#f87171','#fbbf24','#34d399','#a78bfa','#fb923c','#60a5fa','#f472b6','#4ade80','#facc15'];
const REGION_COLORS={'América Latina':'#34d399','Multipaís/Global':'#a78bfa','MENA':'#fbbf24','África':'#f87171'};
let _entidades=[],_fondos=[],_mensualData={},_chartMensual=null;
function mkChart(id,type,labels,datasets,opts={}){const ctx=document.getElementById(id);if(!ctx)return null;if(ctx._chart)ctx._chart.destroy();const c=new Chart(ctx,{type,data:{labels,datasets},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#a0aec0',font:{size:11}}}},scales:type!=='pie'&&type!=='doughnut'?{x:{ticks:{color:'#7c8db5',font:{size:10}},grid:{color:'#1e2235'}},y:{ticks:{color:'#7c8db5',font:{size:10}},grid:{color:'#1e2235'}}}:{},...opts}});ctx._chart=c;return c;}
async function cargar(){
  const[res,ent,fond,mens]=await Promise.all([fetch('/api/resumen').then(r=>r.json()),fetch('/api/entidades?top=50').then(r=>r.json()),fetch('/api/fondos?limit=500').then(r=>r.json()),fetch('/api/mensual').then(r=>r.json())]);
  document.getElementById('ts').textContent=(res.timestamp||'').substring(0,16).replace('T',' ');
  document.getElementById('kpis').innerHTML=[{val:res.total_fondos||0,lbl:'Total fondos',cls:''},{val:`${res.total_eur||0}M€`,lbl:'Total analizado',cls:''},{val:`${res.score_trazabilidad_medio||0}/100`,lbl:'Score trazabilidad',cls:(res.score_trazabilidad_medio||0)<50?'alerta':'ok'},{val:`${res.pct_r1||0}%`,lbl:'R1 — OOII caja negra',cls:'alerta'},{val:`${res.pct_r2||0}%`,lbl:'R2 — Sin PLACE/OCDS',cls:'medio'},{val:`${res.pct_r3||0}%`,lbl:'R3 — Sin justificante',cls:'medio'}].map(k=>`<div class="kpi ${k.cls}"><div class="val">${k.val}</div><div class="lbl">${k.lbl}</div></div>`).join('');
  document.getElementById('rupturas').innerHTML=[{lbl:'R1 — OOII caja negra',pct:res.pct_r1||0,cls:'r1'},{lbl:'R2 — Sin contrato OCDS',pct:res.pct_r2||0,cls:'r2'},{lbl:'R3 — Sin justificante',pct:res.pct_r3||0,cls:'r3'}].map(r=>`<div class="bar-wrap"><div class="bar-label"><span>${r.lbl}</span><span>${r.pct}%</span></div><div class="bar-bg"><div class="bar-fill ${r.cls}" style="width:${r.pct}%"></div></div></div>`).join('');
  mkChart('chartRupturas','doughnut',['R1 OOII','R2 Sin PLACE','R3 Sin justif.','Trazables'],[{data:[res.pct_r1,res.pct_r2,res.pct_r3,Math.max(0,100-res.pct_r1)],backgroundColor:['#f87171','#fbbf24','#fb923c','#34d399'],borderWidth:0}],{plugins:{legend:{position:'bottom',labels:{color:'#a0aec0',font:{size:10}}}}});
  const dist=res.distribucion_eslabones||{};
  mkChart('chartEslabones','bar',Object.keys(dist).sort().map(e=>`E${e}`),[{label:'Fondos',data:Object.keys(dist).sort().map(e=>dist[e]),backgroundColor:COLORS,borderRadius:4}],{plugins:{legend:{display:false}}});
  const acum=res.acumulativo_anual||[];
  mkChart('chartAnual','bar',acum.map(a=>String(a.año)),[{label:'Importe año (M€)',data:acum.map(a=>+(a.importe/1e6).toFixed(1)),backgroundColor:'#3b82f6',borderRadius:4,yAxisID:'y'},{label:'Acumulado (M€)',data:acum.map(a=>+(a.importe_acum/1e6).toFixed(1)),type:'line',borderColor:'#34d399',borderWidth:2,pointRadius:4,backgroundColor:'transparent',yAxisID:'y1'}],{scales:{y:{position:'left',ticks:{color:'#7c8db5',font:{size:10}},grid:{color:'#1e2235'}},y1:{position:'right',ticks:{color:'#34d399',font:{size:10}},grid:{display:false}},x:{ticks:{color:'#7c8db5'},grid:{color:'#1e2235'}}},plugins:{legend:{labels:{color:'#a0aec0',font:{size:10}}}}});
  const topPaises=res.top_paises||[];
  const regiones={};
  topPaises.forEach(p=>{let reg='Otros';const n=p.pais_region||'';if(['Bolivia','Colombia','Ecuador','Guatemala','Honduras','México','Nicaragua','Perú','Cuba','Haití','Venezuela','El Salvador','Costa Rica','Panamá','Paraguay','Brasil','Chile','Argentina'].some(x=>n.includes(x)))reg='América Latina';else if(['Marruecos','Túnez','Argelia','Jordania','Líbano','Palestina','Siria','Irak','Yemen'].some(x=>n.includes(x)))reg='MENA';else if(['Etiopía','Mozambique','Mali','Niger','Senegal','Chad','Kenya','Tanzania','Uganda','Ghana'].some(x=>n.includes(x)))reg='África';else if(['Global','Multipaís','América Latina y Caribe'].some(x=>n.includes(x)))reg='Multipaís/Global';regiones[reg]=(regiones[reg]||0)+p.importe;});
  const regKeys=Object.keys(regiones);
  mkChart('chartRegion','doughnut',regKeys,[{data:regKeys.map(k=>+(regiones[k]/1e6).toFixed(1)),backgroundColor:regKeys.map(k=>REGION_COLORS[k]||'#6b7280'),borderWidth:0}],{plugins:{legend:{position:'bottom',labels:{color:'#a0aec0',font:{size:10}}}}});
  const top15=topPaises.slice(0,15);
  mkChart('chartPaises','bar',top15.map(p=>p.pais_region||'').reverse(),[{label:'Importe (M€)',data:top15.map(p=>+(p.importe/1e6).toFixed(1)).reverse(),backgroundColor:top15.map((_,i)=>COLORS[i%COLORS.length]).reverse(),borderRadius:4}],{indexAxis:'y',plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#7c8db5',font:{size:10}},grid:{color:'#1e2235'}},y:{ticks:{color:'#7c8db5',font:{size:9}},grid:{color:'#1e2235'}}}});
  _mensualData=mens.region||{};
  const rm=Object.keys(_mensualData);
  document.getElementById('tabsRegion').innerHTML=rm.map((r,i)=>`<div class="tab ${i===0?'active':''}" onclick="switchRegion('${r}',this)">${r}</div>`).join('');
  if(rm.length>0)renderMensual(rm[0]);
  _entidades=ent.data||[];renderEntidades(_entidades);
  _fondos=fond.data||[];renderFondos(_fondos);
}
function renderMensual(region){const data=_mensualData[region]||[];if(_chartMensual)_chartMensual.destroy();const ctx=document.getElementById('chartMensual');if(!ctx)return;_chartMensual=new Chart(ctx,{type:'line',data:{labels:data.map(d=>d.mes),datasets:[{label:`${region} (M€)`,data:data.map(d=>+(d.importe/1e6).toFixed(2)),borderColor:REGION_COLORS[region]||'#3b82f6',backgroundColor:(REGION_COLORS[region]||'#3b82f6')+'33',fill:true,tension:0.3,pointRadius:3}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#a0aec0',font:{size:11}}}},scales:{x:{ticks:{color:'#7c8db5',font:{size:9}},grid:{color:'#1e2235'}},y:{ticks:{color:'#7c8db5',font:{size:10}},grid:{color:'#1e2235'}}}}});}
function switchRegion(region,el){document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));el.classList.add('active');renderMensual(region);}
function renderEntidades(data){document.querySelector('#tabla-entidades tbody').innerHTML=data.slice(0,30).map(e=>`<tr><td>${e.entidad||''}</td><td>${(e.score_riesgo||0).toFixed(1)}</td><td><span class="pill ${e.nivel_riesgo||''}">${e.nivel_riesgo||''}</span></td><td>${e.n_fondos||0}</td><td>${((e.importe_total||0)/1e6).toFixed(1)}M€</td><td>${(e.sog_medio||0).toFixed(0)}</td><td>${(e.icr||0).toFixed(0)}</td></tr>`).join('');}
function renderFondos(data){document.querySelector('#tabla-fondos tbody').innerHTML=data.slice(0,100).map(f=>`<tr><td title="${f.titulo||''}">${(f.titulo||'').substring(0,40)}…</td><td>${(f.entidad||'').substring(0,25)}</td><td>${f.pais_region||'—'}</td><td>${f.año||f.fecha?.substring(0,4)||'—'}</td><td>${((f.importe_eur||0)/1e6).toFixed(2)}M€</td><td>E${f.eslabon_corte||'—'}</td><td>${f.score_trazabilidad||0}/100</td><td><span class="pill ${f.clasificacion||''}">${f.clasificacion||'—'}</span></td></tr>`).join('');}
function filtrarEntidades(){const busq=document.getElementById('busq-entidad').value.toLowerCase();const nivel=document.getElementById('filtro-nivel').value;renderEntidades(_entidades.filter(e=>(!busq||(e.entidad||'').toLowerCase().includes(busq))&&(!nivel||e.nivel_riesgo===nivel)));}
function filtrarFondos(){const busq=document.getElementById('busq-fondo').value.toLowerCase();const clasif=document.getElementById('filtro-clasif').value;const eslab=document.getElementById('filtro-eslabon').value;const año=document.getElementById('filtro-año').value;renderFondos(_fondos.filter(f=>(!busq||(f.titulo||'').toLowerCase().includes(busq)||(f.entidad||'').toLowerCase().includes(busq))&&(!clasif||f.clasificacion===clasif)&&(!eslab||String(f.eslabon_corte)===eslab)&&(!año||String(f.año||f.fecha?.substring(0,4))===año)));}
cargar();
</script>
</body>
</html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# MANUAL HTML
# ─────────────────────────────────────────────────────────────────────────────
MANUAL_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Manual de Uso — Monitor AECID</title>

<!-- Google Analytics (GA4) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-0JK8GYT9GT"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-0JK8GYT9GT');
</script>

<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#0f1117;color:#e0e0e0}
header{background:#1a1d2e;padding:18px 28px;border-bottom:2px solid #2d3561;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px}
header h1{font-size:1.3rem;color:#fff}
.nav-links{display:flex;gap:8px}
.nav-links a{background:#2d3561;color:#7eb8f7;padding:6px 14px;border-radius:6px;font-size:0.82rem;text-decoration:none}
.nav-links a:hover,.nav-links a.active{background:#3b82f6;color:#fff}
main{padding:32px 28px;max-width:900px;margin:0 auto}
h2{font-size:1.2rem;color:#7eb8f7;margin:32px 0 12px;border-bottom:1px solid #2d3561;padding-bottom:6px}
h3{font-size:1rem;color:#a0aec0;margin:20px 0 8px}
p{margin-bottom:10px;color:#c0c8d8}
ul{padding-left:20px;margin-bottom:12px;color:#c0c8d8}
li{margin-bottom:6px}
.card{background:#1a1d2e;border:1px solid #2d3561;border-radius:10px;padding:20px;margin-bottom:18px}
.badge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:0.78rem;font-weight:600;margin-right:6px}
.r1{background:#7f1d1d;color:#fca5a5}
.r2{background:#78350f;color:#fcd34d}
.r3{background:#78350f;color:#fb923c}
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
  <div><h1>📖 Manual de Uso — Monitor Trazabilidad AECID</h1></div>
  <nav class="nav-links">
    <a href="/">🏠 Inicio</a>
    <a href="/dashboard">📊 Dashboard</a>
    <a href="/manual" class="active">📖 Manual</a>
    <a href="/autor">👤 Autor</a>
  </nav>
</header>
<main>
<div class="card">
  <h2 style="margin-top:0">¿Qué es este sistema?</h2>
  <p>El <strong>Monitor de Trazabilidad AECID</strong> es una herramienta de auditoría algorítmica que analiza los fondos de cooperación internacional gestionados por la AECID, aplicando la metodología de <em>Fenómenos Corruptivos</em> del Ph.D. Vicente Humberto Monteverde.</p>
  <p>El sistema detecta automáticamente las <strong>rupturas en la cadena de trazabilidad</strong> de cada fondo — desde el presupuesto aprobado en España hasta el beneficiario final.</p>
</div>
<h2>📊 El Modelo de 7 Eslabones</h2>
<div class="card">
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
</div>
<h2>🚨 Las Tres Rupturas Principales</h2>
<div class="card">
  <h3><span class="badge r1">R1</span> OOII — Caja negra</h3>
  <p>Fondos transferidos a Organismos Internacionales (PNUD, UNICEF, FAO, ACNUR…) sin desglosar la aportación española en el estándar IATI.</p>
  <h3><span class="badge r2">R2</span> Sub-contratación sin OCDS</h3>
  <p>Contratos sin publicación en el Portal de la Contratación del Estado (PLACE) bajo el estándar Open Contracting Data Standard.</p>
  <h3><span class="badge r3">R3</span> Sin justificante auditable</h3>
  <p>Proyectos con importe superior a 500.000€ sin evaluación final publicada ni respuesta favorable a solicitud LTAIBG (Ley 19/2013).</p>
</div>
<h2>📈 Indicadores de Riesgo</h2>
<div class="card">
  <table>
    <thead><tr><th>Indicador</th><th>Peso</th><th>Descripción</th></tr></thead>
    <tbody>
      <tr><td><strong>ICR</strong></td><td>15%</td><td>Índice de Concentración de Receptores (HHI normalizado).</td></tr>
      <tr><td><strong>SOG</strong></td><td>35%</td><td>Score de Opacidad en la Gestión.</td></tr>
      <tr><td><strong>RES</strong></td><td>30%</td><td>Riesgo por Eslabón de Corte.</td></tr>
      <tr><td><strong>VIA</strong></td><td>20%</td><td>Vulnerabilidad Institucional del país receptor.</td></tr>
    </tbody>
  </table>
</div>
<h2>🔌 Endpoints de la API</h2>
<div class="card">
  <div class="endpoint">GET /api/status — Estado del servicio</div>
  <div class="endpoint">GET /api/resumen — KPIs ejecutivos</div>
  <div class="endpoint">GET /api/fondos?entidad=X&amp;clasificacion=ROJO&amp;limit=100</div>
  <div class="endpoint">GET /api/trazabilidad — Análisis por eslabón</div>
  <div class="endpoint">GET /api/entidades?top=30&amp;nivel=Alto</div>
  <div class="endpoint">GET /api/riesgo — Scores por entidad</div>
  <div class="endpoint">GET /api/mensual — Evolución mensual por región</div>
  <div class="endpoint">GET /api/informe — Informe ejecutivo en Markdown</div>
  <div class="endpoint">POST /api/refresh (Header: X-Refresh-Token)</div>
</div>
<h2>📚 Marco teórico</h2>
<div class="card">
  <p>Basado en la teoría de los <em>Fenómenos Corruptivos</em> del Ph.D. Vicente Humberto Monteverde: transferencias regresivas de ingresos facilitadas por la discrecionalidad en decisiones legales.</p>
  <p>Referencia: Monteverde, V.H. (2020). <em>Great corruption – theory of corrupt phenomena</em>. Journal of Financial Crime. Emerald Publishing.</p>
</div>
</main>
<footer>Monitor AECID v2.0 · github.com/Viny2030/Fenomenos_corruptivos_spain</footer>
</body>
</html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# AUTOR HTML
# ─────────────────────────────────────────────────────────────────────────────
AUTOR_HTML = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Autor — Ph.D. Vicente Humberto Monteverde</title>

<!-- Google Analytics (GA4) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-0JK8GYT9GT"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-0JK8GYT9GT');
</script>

<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',sans-serif;background:#0f1117;color:#e0e0e0}}
header{{background:#1a1d2e;padding:18px 28px;border-bottom:2px solid #2d3561;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px}}
header h1{{font-size:1.3rem;color:#fff}}
.nav-links{{display:flex;gap:8px}}
.nav-links a{{background:#2d3561;color:#7eb8f7;padding:6px 14px;border-radius:6px;font-size:0.82rem;text-decoration:none}}
.nav-links a:hover,.nav-links a.active{{background:#3b82f6;color:#fff}}
main{{padding:36px 28px;max-width:900px;margin:0 auto}}
.autor-card{{background:#1a1d2e;border:1px solid #2d3561;border-radius:14px;padding:28px 32px;display:flex;gap:28px;align-items:flex-start;margin-bottom:36px}}
.autor-img{{width:90px;height:90px;border-radius:50%;object-fit:cover;border:3px solid #3b82f6;flex-shrink:0}}
.autor-info h2{{font-size:1.35rem;color:#fff;margin-bottom:6px}}
.autor-info p{{color:#c0c8d8;font-size:0.9rem;margin-bottom:8px;line-height:1.6}}
.autor-info em{{color:#7eb8f7;font-style:normal;font-weight:600}}
.autor-info .pub{{color:#a0aec0;font-size:0.85rem;margin-top:4px}}
.email-row{{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}}
.email-btn{{display:inline-flex;align-items:center;gap:6px;background:#2d3561;color:#7eb8f7;padding:7px 16px;border-radius:8px;font-size:0.83rem;text-decoration:none;border:1px solid #3b52a0}}
.email-btn:hover{{background:#3b52a0}}
.dona-header{{text-align:center;margin-bottom:24px}}
.dona-header h3{{font-size:1.15rem;color:#fbbf24;margin-bottom:6px}}
.dona-header p{{color:#a0aec0;font-size:0.88rem}}
.dona-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:18px;margin-bottom:28px}}
.dona-card{{background:#1a1d2e;border:1px solid #2d3561;border-radius:12px;padding:20px 22px}}
.dona-card.ars{{border-top:3px solid #3b82f6}}
.dona-card.usd{{border-top:3px solid #34d399}}
.dona-card.wire{{border-top:3px solid #f87171}}
.dona-card h4{{font-size:0.82rem;color:#a0aec0;text-transform:uppercase;letter-spacing:.06em;margin-bottom:14px}}
.dona-row{{margin-bottom:10px}}
.dona-row .lbl{{font-size:0.72rem;color:#7c8db5;text-transform:uppercase;letter-spacing:.04em;margin-bottom:2px}}
.dona-row .val{{font-size:0.88rem;color:#e0e0e0;font-weight:500}}
.dona-row .val.mono{{font-family:monospace;color:#7eb8f7;font-size:0.9rem;background:#0f1117;padding:3px 8px;border-radius:5px;display:inline-block;margin-top:2px}}
.dona-row .val.alias{{color:#34d399;font-family:monospace;font-size:0.9rem}}
footer{{text-align:center;padding:16px;color:#4a5568;font-size:0.75rem;border-top:1px solid #1a1d2e;margin-top:24px}}
a{{color:#7eb8f7;text-decoration:none}}
@media(max-width:600px){{.autor-card{{flex-direction:column;align-items:center;text-align:center}}.email-row{{justify-content:center}}}}
</style>
</head>
<body>
<header>
  <div><h1>👤 Autor del proyecto</h1></div>
  <nav class="nav-links">
    <a href="/">🏠 Inicio</a>
    <a href="/dashboard">📊 Dashboard</a>
    <a href="/manual">📖 Manual</a>
    <a href="/autor" class="active">👤 Autor</a>
  </nav>
</header>
<main>
  <div class="autor-card">
    <img class="autor-img" src="{FOTO_BASE64}" alt="Ph.D. Vicente Humberto Monteverde">
    <div class="autor-info">
      <h2>Ph.D. Vicente Humberto Monteverde</h2>
      <p>Investigador en economía política y fenómenos de corrupción. Doctor en Ciencias Económicas.
      Autor de la teoría de <em>Transferencia Regresiva de Ingresos</em> y desarrollador del algoritmo
      <em>XAI</em> aplicado al análisis de contrataciones públicas.</p>
      <p class="pub">Publicaciones en <em>Journal of Financial Crime</em> (Emerald Publishing).
      Asesor en transparencia y auditoría algorítmica del gasto público.</p>
      <div class="email-row">
        <a class="email-btn" href="mailto:vhmonte@retina.ar">✉️ vhmonte@retina.ar</a>
        <a class="email-btn" href="mailto:viny01958@gmail.com">✉️ viny01958@gmail.com</a>
      </div>
    </div>
  </div>
  <div class="dona-header">
    <h3>💛 Apoyar este proyecto — Donaciones voluntarias</h3>
    <p>Si este proyecto te resulta útil, podés apoyarlo con una donación voluntaria.</p>
  </div>
  <div class="dona-grid">
    <div class="dona-card ars">
      <h4>🇦🇷 Argentina · Pesos (ARS)</h4>
      <div class="dona-row"><div class="lbl">Tipo</div><div class="val">Caja de Ahorro</div></div>
      <div class="dona-row"><div class="lbl">CBU</div><div class="val mono">0140005203400552652310</div></div>
      <div class="dona-row"><div class="lbl">Alias</div><div class="val alias">ALGORIT.MONTE.PESOS</div></div>
      <div class="dona-row"><div class="lbl">Titular</div><div class="val">Vicente Humberto Monteverde</div></div>
      <div class="dona-row"><div class="lbl">CUIL/CUIT</div><div class="val mono">20-12034411-1</div></div>
    </div>
    <div class="dona-card usd">
      <h4>🇦🇷 Argentina · Dólares (USD)</h4>
      <div class="dona-row"><div class="lbl">Tipo</div><div class="val">Caja de Ahorro Dólares</div></div>
      <div class="dona-row"><div class="lbl">CBU</div><div class="val mono">0140005204400550329709</div></div>
      <div class="dona-row"><div class="lbl">Alias</div><div class="val alias">ALGO.MONTE.DOLARES</div></div>
      <div class="dona-row"><div class="lbl">Titular</div><div class="val">Vicente Humberto Monteverde</div></div>
      <div class="dona-row"><div class="lbl">CUIL/CUIT</div><div class="val mono">20-12034411-1</div></div>
    </div>
    <div class="dona-card wire">
      <h4>🌐 Desde el Exterior (USD Wire)</h4>
      <div class="dona-row"><div class="lbl">Banco</div><div class="val">Banco Santander Rio</div></div>
      <div class="dona-row"><div class="lbl">Beneficiario</div><div class="val">Vicente Humberto Monteverde</div></div>
      <div class="dona-row"><div class="lbl">Dirección</div><div class="val">Av. Directorio 3024 PB DTO 04</div></div>
      <div class="dona-row"><div class="lbl">Cuenta USD</div><div class="val mono">005200183500</div></div>
      <div class="dona-row"><div class="lbl">SWIFT / BIC</div><div class="val alias">BSCHUYMM</div></div>
      <div class="dona-row"><div class="lbl">CUIL/CUIT</div><div class="val mono">20-12034411-1</div></div>
    </div>
  </div>
</main>
<footer>Monitor AECID v2.0 · github.com/Viny2030/Fenomenos_corruptivos_spain · Ph.D. Vicente Humberto Monteverde · <a href="mailto:vhmonte@retina.ar">vhmonte@retina.ar</a></footer>
</body>
</html>"""

# ─────────────────────────────────────────────────────────────────────────────
# LIFESPAN
# ─────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA_PRO.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    print("✅ Monitor AECID arrancando")
    yield

app = FastAPI(
    title="Monitor Trazabilidad AECID — Ph.D. Monteverde",
    description="Algoritmos contra la Corrupción — Trazabilidad de Fondos AECID",
    version="2.0.0",
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
# ENDPOINTS UI
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def landing():
    return HTMLResponse(LANDING_HTML)

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(DASHBOARD_HTML)

@app.get("/manual", response_class=HTMLResponse)
def manual():
    return HTMLResponse(MANUAL_HTML)

@app.get("/autor", response_class=HTMLResponse)
def autor():
    return HTMLResponse(AUTOR_HTML)

# ─────────────────────────────────────────────────────────────────────────────
# API — STATUS
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/status")
def status():
    df = _cargar_fondos()
    return {
        "servicio": "Monitor Trazabilidad AECID v2.0",
        "status": "activo",
        "total_fondos": len(df),
        "cache_timestamp": _cache["ts"],
        "timestamp": datetime.now().isoformat(),
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
    acumulativo = []
    if "fecha" in df.columns:
        df2 = df.copy()
        df2["año"] = pd.to_datetime(df2["fecha"], errors="coerce").dt.year
        df2["importe_num"] = df2["importe_eur"].apply(_parsear_monto)
        acum = df2.groupby("año").agg(n=("importe_num","count"), importe=("importe_num","sum")).reset_index().sort_values("año")
        acum["importe_acum"] = acum["importe"].cumsum()
        acumulativo = acum.dropna().to_dict(orient="records")
    por_pais = []
    if "pais_region" in df.columns:
        df3 = df.copy()
        df3["importe_num"] = df3["importe_eur"].apply(_parsear_monto)
        grp = df3.groupby("pais_region").agg(n=("importe_num","count"), importe=("importe_num","sum")).reset_index().sort_values("importe", ascending=False).head(20)
        grp["pct"] = (grp["importe"] / total_eur * 100).round(1)
        por_pais = grp.to_dict(orient="records")
    return {
        "total_fondos": len(df),
        "total_eur": round(total_eur / 1e6, 1),
        "score_trazabilidad_medio": score_traz,
        "pct_r1": _pct("ruptura_r1"),
        "pct_r2": _pct("ruptura_r2"),
        "pct_r3": _pct("ruptura_r3"),
        "distribucion_eslabones": dist_eslabon,
        "acumulativo_anual": acumulativo,
        "top_paises": por_pais,
        "timestamp": datetime.now().isoformat(),
    }

# ─────────────────────────────────────────────────────────────────────────────
# API — FONDOS
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/fondos")
def fondos(
    entidad: str | None = Query(None),
    clasificacion: str | None = Query(None),
    eslabon: int | None = Query(None),
    pais: str | None = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
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
    return {"total": len(df), "limit": limit, "offset": offset, "data": df.iloc[offset:offset+limit].fillna("").to_dict(orient="records")}

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
            resumen[f"n_{col}"] = int(df[col].astype(str).str.upper().isin(["TRUE","1"]).sum())
    return {"resumen": resumen, "data": df.fillna("").head(200).to_dict(orient="records")}

# ─────────────────────────────────────────────────────────────────────────────
# API — ENTIDADES
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/entidades")
def entidades(
    top: int = Query(30, le=100),
    nivel: str | None = Query(None),
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
    return {"resumen": resumen, "data": df.fillna(0).to_dict(orient="records")}

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
            capture_output=True, text=True, timeout=300, cwd=str(ROOT),
        )
        _invalidar_cache()
        return {"status": "ok" if result.returncode == 0 else "error", "log": result.stdout[-2000:] + result.stderr[-1000:], "timestamp": datetime.now().isoformat()}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Timeout — pipeline tardó más de 5 minutos")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────────────────────────────────────
# API — MENSUAL
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/mensual")
def mensual():
    df = _cargar_fondos()
    if df.empty or "fecha" not in df.columns:
        return {"data": []}
    df = df.copy()
    df["fecha_dt"]    = pd.to_datetime(df["fecha"], errors="coerce")
    df["mes"]         = df["fecha_dt"].dt.to_period("M").astype(str)
    df["importe_num"] = df["importe_eur"].apply(_parsear_monto)
    mensual_total = df.groupby("mes").agg(n=("importe_num","count"), importe=("importe_num","sum")).reset_index().sort_values("mes")
    mensual_region = {}
    if "region" in df.columns:
        for region, grp in df.groupby("region"):
            evol = grp.groupby("mes")["importe_num"].sum().reset_index()
            evol.columns = ["mes", "importe"]
            mensual_region[str(region)] = evol.to_dict(orient="records")
    elif "pais_region" in df.columns:
        df["region_inf"] = df["pais_region"].apply(lambda p: (
            "América Latina" if any(x in str(p) for x in ["Bolivia","Colombia","Ecuador","Guatemala","Honduras","México","Nicaragua","Perú","Cuba","Haití"]) else
            "África"         if any(x in str(p) for x in ["Etiopía","Mozambique","Mali","Niger","Senegal","Chad","Kenya"]) else
            "MENA"           if any(x in str(p) for x in ["Marruecos","Túnez","Jordania","Líbano","Palestina","Siria","Yemen"]) else
            "Multipaís/Global"
        ))
        for region, grp in df.groupby("region_inf"):
            evol = grp.groupby("mes")["importe_num"].sum().reset_index()
            evol.columns = ["mes", "importe"]
            mensual_region[str(region)] = evol.to_dict(orient="records")
    mensual_sector = {}
    if "ambito" in df.columns:
        for sector, grp in df.groupby("ambito"):
            if str(sector) in ("", "nan"):
                continue
            evol = grp.groupby("mes")["importe_num"].sum().reset_index()
            evol.columns = ["mes", "importe"]
            mensual_sector[str(sector)] = evol.to_dict(orient="records")
    return {"total": mensual_total.to_dict(orient="records"), "region": mensual_region, "sector": mensual_sector}
