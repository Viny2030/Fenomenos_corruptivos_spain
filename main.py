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
import secrets
import time
from contextlib import asynccontextmanager
from functools import lru_cache
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
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
if not REFRESH_TOKEN:
    REFRESH_TOKEN = secrets.token_hex(32)
    print(
        "\u26a0\ufe0f  REFRESH_TOKEN no esta configurada como variable de entorno "
        "-- se genero un valor aleatorio temporal solo para este proceso. "
        "POST /api/refresh quedara inaccesible hasta que definas REFRESH_TOKEN "
        "(valor fuerte, ej. `openssl rand -hex 32`) en las variables de entorno de Railway."
    )

TEMPLATES_DIR = ROOT / "templates"

@lru_cache(maxsize=None)
def _tpl(name: str) -> str:
    """Lee y cachea un template HTML estatico desde templates/."""
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")

LANDING_HTML    = _tpl("landing_es.html")
DASHBOARD_HTML  = _tpl("dashboard.html")
MANUAL_HTML     = _tpl("manual_es.html")
AUTOR_HTML      = _tpl("autor.html")
LANDING_HTML_EN = _tpl("landing_en.html")
MANUAL_HTML_EN  = _tpl("manual_en.html")

# ─────────────────────────────────────────────────────────────────────────────
# LIFESPAN
# ─────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA_PRO.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    try:
        from db import restaurar_procesados
        n = restaurar_procesados(solo_si_faltan=True)
        if n:
            print(f"✅ {n} archivo(s) restaurados desde PostgreSQL (DATABASE_URL)")
    except Exception as e:
        # No-op si DATABASE_URL no esta definida; nunca debe tumbar el arranque.
        print(f"⚠️  Restauracion desde DB omitida: {e}")
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
    allow_methods=["GET", "POST"],
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

@app.get("/en", response_class=HTMLResponse)
def landing_en():
    return HTMLResponse(LANDING_HTML_EN)

@app.get("/en/manual", response_class=HTMLResponse)
def manual_en():
    return HTMLResponse(MANUAL_HTML_EN)

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
_REFRESH_MIN_INTERVAL_S = 60
_refresh_state = {"last_call": 0.0}

@app.post("/api/refresh")
def refresh(x_refresh_token: str = Header(None)):
    if x_refresh_token != REFRESH_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")
    elapsed = time.monotonic() - _refresh_state["last_call"]
    if elapsed < _REFRESH_MIN_INTERVAL_S:
        raise HTTPException(
            status_code=429,
            detail=f"Esperá {int(_REFRESH_MIN_INTERVAL_S - elapsed)}s antes de reintentar",
        )
    _refresh_state["last_call"] = time.monotonic()
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
        return {"total": [], "region": {}, "sector": {}}
    df = df.copy()
    df["fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["mes"] = df["fecha_dt"].dt.to_period("M").astype(str)
    df["importe_num"] = df["importe_eur"].apply(_parsear_monto)

    mensual_total = df.groupby("mes").agg(
        n=("importe_num", "count"),
        importe=("importe_num", "sum"),
    ).reset_index().sort_values("mes")

    mensual_region = {}
    if "region" in df.columns:
        for region, grp in df.groupby("region"):
            evol = grp.groupby("mes")["importe_num"].sum().reset_index()
            evol.columns = ["mes", "importe"]
            mensual_region[str(region)] = evol.to_dict(orient="records")
    elif "pais_region" in df.columns:
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

    mensual_sector = {}
    if "ambito" in df.columns:
        for sector, grp in df.groupby("ambito"):
            if str(sector) in ("", "nan"):
                continue
            evol = grp.groupby("mes")["importe_num"].sum().reset_index()
            evol.columns = ["mes", "importe"]
            mensual_sector[str(sector)] = evol.to_dict(orient="records")

    return {
        "total": mensual_total.to_dict(orient="records"),
        "region": mensual_region,
        "sector": mensual_sector,
    }

# ─────────────────────────────────────────────────────────────────────────────
# API — GRAFO DE FLUJOS (AECID → Entidad → Eslabón de corte)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/grafo")
def grafo(top: int = Query(30, ge=5, le=200, description="Cantidad de entidades a graficar")):
    """
    Construye la red de flujo de fondos AECID → entidad → eslabón donde se corta
    la trazabilidad, a partir de los datos ya existentes en analisis_completo.csv
    (entidad, importe_eur, eslabon_corte, clasificacion, ruptura_r2).

    No requiere un modelo de grafo separado: se sintetiza on-the-fly agregando
    por entidad, igual que hacen /api/resumen y /api/entidades.
    """
    df = _cargar_fondos()
    if df.empty or "entidad" not in df.columns:
        return {"nodes": [], "edges": [], "total_entidades": 0}

    df = df.copy()
    df["importe_num"] = df["importe_eur"].apply(_parsear_monto)

    stats: dict = {}
    for _, f in df.iterrows():
        ent = str(f.get("entidad") or "").strip()
        if not ent:
            continue
        s = stats.setdefault(
            ent, {"importe": 0.0, "n": 0, "eslabones": {}, "clasif": {}, "r2": 0}
        )
        s["importe"] += float(f.get("importe_num") or 0)
        s["n"] += 1

        esl = f.get("eslabon_corte")
        if esl not in (None, "") and str(esl) != "nan":
            try:
                esl_i = int(float(esl))
                s["eslabones"][esl_i] = s["eslabones"].get(esl_i, 0) + 1
            except (ValueError, TypeError):
                pass

        clasif = f.get("clasificacion")
        if clasif and str(clasif) != "nan":
            s["clasif"][clasif] = s["clasif"].get(clasif, 0) + 1

        if f.get("ruptura_r2"):
            s["r2"] += 1

    top_entidades = sorted(stats.items(), key=lambda kv: kv[1]["importe"], reverse=True)[:top]

    CLASIF_COLOR = {"ROJO": "#f87171", "NARANJA": "#fb923c", "AMARILLO": "#fbbf24", "VERDE": "#34d399"}
    ESLABON_LABEL = {
        1: "E1 · PGE",
        2: "E2 · AECID sede",
        3: "E3 · Canal (ONGD/OOII)",
        4: "E4 · OTC país",
        5: "E5 · Sub-ejecutor",
        6: "E6 · Actividad",
        7: "E7 · Beneficiario final",
    }

    nodes = [{
        "id": "AECID",
        "label": "AECID",
        "group": "root",
        "value": int(sum(s["importe"] for _, s in top_entidades)) or 1,
        "title": "AECID — origen de los fondos",
    }]
    edges = []
    eslabones_usados = set()

    for ent, s in top_entidades:
        ent_id = f"ent::{ent}"
        clasif_top = max(s["clasif"], key=s["clasif"].get) if s["clasif"] else ""
        color = CLASIF_COLOR.get(clasif_top, "#7eb8f7")
        nodes.append({
            "id": ent_id,
            "label": ent[:34],
            "group": "entidad",
            "value": int(s["importe"]) or 1,
            "color": color,
            "title": f"{ent} · {s['n']} fondos · {s['importe']/1e6:.1f}M€ · Clasif: {clasif_top or '—'}",
        })
        edges.append({
            "from": "AECID",
            "to": ent_id,
            "value": int(s["importe"]) or 1,
            "title": f"{s['importe']/1e6:.1f}M€",
        })

        esl_top = max(s["eslabones"], key=s["eslabones"].get) if s["eslabones"] else None
        if esl_top is not None:
            esl_id = f"E{esl_top}"
            eslabones_usados.add(esl_top)
            edges.append({
                "from": ent_id,
                "to": esl_id,
                "value": int(s["importe"]) or 1,
                "dashes": s["r2"] > s["n"] / 2,
                "title": "Sin contrato PLACE/OCDS trazable (R2)" if s["r2"] > s["n"] / 2 else "",
            })

    for esl in sorted(eslabones_usados):
        nodes.append({
            "id": f"E{esl}",
            "label": ESLABON_LABEL.get(esl, f"E{esl}"),
            "group": "eslabon",
            "value": 1,
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "total_entidades": len(stats),
    }
