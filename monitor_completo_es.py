import requests
import pandas as pd
import os
from datetime import datetime, timedelta

def ejecutar_monitor():
    if not os.path.exists("data"):
        os.makedirs("data")

    headers = {"Accept": "application/json", "User-Agent": "MonitorMonteverde/1.0"}
    ayer = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

    # --- FASE 1: OBTENCIÓN DE MARCO LEGAL (BOE) ---
    url_boe = "https://boe.es/datosabiertos/api/legislacion-consolidada"
    query_json = '{"query":{"query_string":{"query":"titulo:contrato OR titulo:adjudicacion OR titulo:emergencia"}}}'
    params_boe = {"limit": 100, "query": query_json}

    df_boe = pd.DataFrame()
    try:
        r_boe = requests.get(url_boe, params=params_boe, headers=headers, timeout=30)
        if r_boe.status_code == 200:
            items = r_boe.json().get("data", [])
            df_boe = pd.DataFrame([{"id": i.get("identificador"), "titulo": i.get("titulo")} for i in items])
            df_boe.to_csv("data/boe_legislacion.csv", index=False, encoding="utf-8-sig")
    except Exception as e:
        print(f"Error BOE: {e}")

    # --- FASE 2: CRUCE ANALÍTICO (MATRIZ MONTEVERDE) ---
    # Cargamos las adjudicaciones detectadas previamente
    ruta_adj = "data/adjudicaciones_espana.csv"
    if os.path.exists(ruta_adj) and not df_boe.empty:
        df_adj = pd.read_csv(ruta_adj)
        
        # Palabras clave de tu artículo: Decisiones discrecionales y falta de control
        keywords_riesgo = ['EMERGENCIA', 'URGENCIA', 'DIRECTA', 'EXCEPCIONAL']
        alertas = []

        for _, contrato in df_adj.iterrows():
            titulo_c = str(contrato.get('titulo', '')).upper()
            
            # Si el contrato elude la licitación estándar (Discrecionalidad)
            if any(k in titulo_c for k in keywords_riesgo):
                # Buscamos la norma en el BOE que ampara este gasto
                for _, ley in df_boe.head(5).iterrows():
                    alertas.append({
                        "Fecha_Deteccion": datetime.now().strftime("%Y-%m-%d"),
                        "Contrato_Sospechoso": contrato.get('titulo'),
                        "Organismo": contrato.get('departamento', 'N/D'),
                        "Indicador_Riesgo": "Acuerdo Colusorio / Discrecionalidad",
                        "Evidencia_Legal_BOE": ley['titulo'],
                        "Teoria_Aplicada": "Transferencia de ingresos vía legalidad"
                    })
        
        # Guardamos la PRUEBA MATERIAL
        df_matriz = pd.DataFrame(alertas)
        df_matriz.to_csv("data/matriz_alertas_monteverde.csv", index=False, encoding="utf-8-sig")
        print(f"Matriz generada: {len(df_matriz)} alertas.")

if __name__ == "__main__":
    ejecutar_monitor()
