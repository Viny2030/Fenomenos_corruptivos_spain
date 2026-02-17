import requests
import pandas as pd
import os
from datetime import datetime, timedelta

def ejecutar_monitor():
    # ==========================================
    # DIRECTORIOS CON ARCHIVADO MENSUAL
    # ==========================================
    if not os.path.exists("data"):
        os.makedirs("data")

    ahora = datetime.now()
    mes_carpeta = ahora.strftime("%Y-%m")
    ruta_mes = os.path.join("data", mes_carpeta)
    if not os.path.exists(ruta_mes):
        os.makedirs(ruta_mes)
        print(f"📁 Creada nueva carpeta mensual: {ruta_mes}")

    fecha_hoy = ahora.strftime("%Y-%m-%d")
    timestamp = ahora.strftime("%Y%m%d_%H%M%S")

    headers = {"Accept": "application/json", "User-Agent": "MonitorMonteverde/1.0"}

    # ==========================================
    # FASE 1: BOE - LEGISLACIÓN CONSOLIDADA
    # ==========================================
    url_boe = "https://boe.es/datosabiertos/api/legislacion-consolidada"
    query_json = '{"query":{"query_string":{"query":"titulo:contrato OR titulo:adjudicacion OR titulo:emergencia"}}}'
    params_boe = {"limit": 100, "query": query_json}
    df_boe = pd.DataFrame()

    try:
        r_boe = requests.get(url_boe, params=params_boe, headers=headers, timeout=30)
        if r_boe.status_code == 200:
            items = r_boe.json().get("data", [])
            df_boe = pd.DataFrame([{
                "id":     i.get("identificador"),
                "titulo": i.get("titulo")
            } for i in items])
            # Guardar copia diaria del BOE
            ruta_boe = os.path.join(ruta_mes, f"boe_legislacion_{timestamp}.csv")
            df_boe.to_csv(ruta_boe, index=False, encoding="utf-8-sig")
            # También actualizar el archivo "actual" para compatibilidad
            df_boe.to_csv("data/boe_legislacion.csv", index=False, encoding="utf-8-sig")
            print(f"✅ BOE: {len(df_boe)} normas obtenidas.")
        else:
            print(f"⚠️ BOE respondió con status {r_boe.status_code}")
    except Exception as e:
        print(f"❌ Error BOE: {e}")

    # ==========================================
    # FASE 2: ADJUDICACIONES (CONTRATACIÓN PÚBLICA)
    # ==========================================
    ruta_adj = "data/adjudicaciones_espana.csv"

    # Si no existe el archivo base, intentar obtenerlo de la API de contratación
    if not os.path.exists(ruta_adj):
        print("⚠️ No existe adjudicaciones_espana.csv, intentando obtener de API...")
        try:
            # API de contratación del sector público español
            url_contrat = "https://contrataciondelestado.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom"
            r_cont = requests.get(url_contrat, headers=headers, timeout=30)
            if r_cont.status_code == 200:
                import re
                entries = re.findall(r"<entry>(.*?)</entry>", r_cont.text, re.DOTALL)
                datos = []
                for entry in entries[:50]:
                    titulo_m = re.search(r"<title[^>]*>(.*?)</title>", entry, re.DOTALL)
                    link_m   = re.search(r"<link[^>]*href=['\"]([^'\"]+)['\"]", entry)
                    org_m    = re.search(r"<summary[^>]*>(.*?)</summary>", entry, re.DOTALL)
                    titulo   = re.sub(r"<[^>]+>", "", titulo_m.group(1) if titulo_m else "").strip()
                    link     = link_m.group(1) if link_m else ""
                    org      = re.sub(r"<[^>]+>", "", org_m.group(1) if org_m else "").strip()[:100]
                    if titulo:
                        datos.append({
                            "titulo":      titulo,
                            "departamento": org,
                            "link":        link,
                            "fecha":       fecha_hoy,
                        })
                if datos:
                    pd.DataFrame(datos).to_csv(ruta_adj, index=False, encoding="utf-8-sig")
                    print(f"✅ Adjudicaciones obtenidas: {len(datos)} contratos.")
        except Exception as e:
            print(f"❌ Error obteniendo adjudicaciones: {e}")

    # ==========================================
    # FASE 3: MATRIZ MONTEVERDE
    # ==========================================
    keywords_riesgo = ['EMERGENCIA', 'URGENCIA', 'DIRECTA', 'EXCEPCIONAL',
                       'CONTRATO MENOR', 'NEGOCIADO', 'ADJUDICACI']

    alertas = []

    if os.path.exists(ruta_adj) and not df_boe.empty:
        df_adj = pd.read_csv(ruta_adj)
        for _, contrato in df_adj.iterrows():
            titulo_c = str(contrato.get('titulo', '')).upper()
            if any(k in titulo_c for k in keywords_riesgo):
                for _, ley in df_boe.head(5).iterrows():
                    alertas.append({
                        "Fecha_Deteccion":    fecha_hoy,
                        "Contrato_Sospechoso": contrato.get('titulo'),
                        "Organismo":          contrato.get('departamento', 'N/D'),
                        "Indicador_Riesgo":   "Acuerdo Colusorio / Discrecionalidad",
                        "Evidencia_Legal_BOE": ley['titulo'],
                        "Teoria_Aplicada":    "Transferencia de ingresos vía legalidad",
                        "link":               contrato.get('link', ''),
                    })
    elif df_boe.empty and os.path.exists(ruta_adj):
        # Sin BOE pero con adjudicaciones — generar alertas básicas
        df_adj = pd.read_csv(ruta_adj)
        for _, contrato in df_adj.iterrows():
            titulo_c = str(contrato.get('titulo', '')).upper()
            if any(k in titulo_c for k in keywords_riesgo):
                alertas.append({
                    "Fecha_Deteccion":    fecha_hoy,
                    "Contrato_Sospechoso": contrato.get('titulo'),
                    "Organismo":          contrato.get('departamento', 'N/D'),
                    "Indicador_Riesgo":   "Discrecionalidad detectada",
                    "Evidencia_Legal_BOE": "BOE no disponible en este ciclo",
                    "Teoria_Aplicada":    "Transferencia de ingresos vía legalidad",
                    "link":               contrato.get('link', ''),
                })

    if not alertas:
        alertas.append({
            "Fecha_Deteccion":    fecha_hoy,
            "Contrato_Sospechoso": "Sin alertas detectadas en este ciclo",
            "Organismo":          "N/D",
            "Indicador_Riesgo":   "Sin riesgo detectado",
            "Evidencia_Legal_BOE": "N/D",
            "Teoria_Aplicada":    "N/D",
            "link":               "",
        })

    df_matriz = pd.DataFrame(alertas)

    # Guardar con timestamp en carpeta mensual
    ruta_matriz_diaria = os.path.join(ruta_mes, f"matriz_alertas_{timestamp}.csv")
    df_matriz.to_csv(ruta_matriz_diaria, index=False, encoding="utf-8-sig")

    # También actualizar el archivo "actual" para compatibilidad con dashboard
    df_matriz.to_csv("data/matriz_alertas_monteverde.csv", index=False, encoding="utf-8-sig")

    print(f"Matriz generada: {len(df_matriz)} alertas.")
    print(f"📁 Archivo diario: {ruta_matriz_diaria}")

if __name__ == "__main__":
    ejecutar_monitor()
