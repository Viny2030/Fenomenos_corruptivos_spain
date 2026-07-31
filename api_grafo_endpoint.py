# ─────────────────────────────────────────────────────────────────────────────
# PEGAR ESTE BLOQUE EN main.py
# Ubicación: al final del archivo, después de la función mensual() (última ruta
# existente, "/api/mensual"), y ANTES de cualquier bloque `if __name__ == "__main__":`
# si existiera. Sangría a nivel de módulo (sin indentar), igual que las demás rutas.
# No requiere nuevas dependencias: usa pandas y _cargar_fondos(), _parsear_monto()
# que ya existen en main.py.
# ─────────────────────────────────────────────────────────────────────────────

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
