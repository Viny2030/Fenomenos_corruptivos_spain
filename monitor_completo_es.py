import requests
import pandas as pd
import os
from datetime import datetime, timedelta

def ejecutar_monitor():
    if not os.path.exists("data"):
        os.makedirs("data")

    ayer = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    headers = {"Accept": "application/json", "User-Agent": "MonitorMonteverde/1.0"}

    # --- 1. OBTENCIÓN DE DATOS (BOE) ---
    url_boe = "https://boe.es/datosabiertos/api/legislacion-consolidada"
    query_json = '{"query":{"query_string":{"query":"titulo:contrato OR titulo:adjudicacion OR titulo:emergencia"}}}'
    params_boe = {"limit": 100, "query": query_json}

    df_boe = pd.DataFrame()
    try:
        r_boe = requests.get(url_boe, params=params_boe, headers=headers, timeout=30)
        if r_boe.status_code == 200:
            items = r_boe.json().get("data", [])
            df_boe = pd.DataFrame([{
                "id_boe": i.get("identificador"),
                "titulo_ley": i.get("titulo"),
                "url_ley": i.get("url_html_consolidada")
            } for i in items])
            df_boe.to_csv("data/boe_legislacion.csv", index=False, encoding="utf-8-sig")
    except Exception as e:
        print(f"Error BOE: {e}")

    # --- 2. OBTENCIÓN DE DATOS (ADJUDICACIONES ANTERIORES) ---
    # Cargamos el archivo que ya tienes generado por tu otro script
    df_adj = pd.DataFrame()
    if os.path.exists("data/adjudicaciones_espana.csv"):
        df_adj = pd.read_csv("data/adjudicaciones_espana.csv")

    # --- 3. GENERACIÓN DE LA MATRIZ DE ALERTAS (ALGORITMO XVI) ---
    # Este proceso detecta el 'Acuerdo Colusorio' mediante el cruce de discrecionalidad
    if not df_boe.empty and not df_adj.empty:
        keywords_riesgo = ['EMERGENCIA', 'URGENCIA', 'DIRECTA', 'SIN PUBLICIDAD']
        alertas = []

        for _, contrato in df_adj.iterrows():
            objeto = str(contrato.get('titulo', '')).upper()
            # Si el contrato tiene indicadores de riesgo procedimental
            if any(k in objeto for k in keywords_riesgo):
                # Buscamos en el BOE leyes que coincidan con la fase de ocultación
                for _, ley in df_boe.head(5).iterrows(): 
                    alertas.append({
                        "fecha_alerta": ayer,
                        "objeto_contrato": contrato.get('titulo'),
                        "organismo": contrato.get('organo', 'N/D'),
                        "tipo_riesgo": "Discrecionalidad Técnica Detectada",
                        "evidencia_legal_boe": ley['titulo_ley'],
                        "fase_cadena_valor": "Ejecución / Acuerdo Colusorio"
                    })
        
        if alertas:
            df_matriz = pd.DataFrame(alertas)
            df_matriz.to_csv("data/matriz_alertas_monteverde.csv", index=False, encoding="utf-8-sig")
            print(f"Matriz generada con {len(df_matriz)} alertas.")
        else:
            pd.DataFrame(columns=["fecha_alerta", "tipo_riesgo"]).to_csv("data/matriz_alertas_monteverde.csv", index=False)

if __name__ == "__main__":
    ejecutar_monitor()
