import requests
import pandas as pd
import os
from datetime import datetime, timedelta

def ejecutar_monitor():
    if not os.path.exists("data"):
        os.makedirs("data")

    # Definir fecha de búsqueda (ayer) para el BORME [cite: 13]
    ayer = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    headers = {"Accept": "application/json", "User-Agent": "MonitorTransparencia/1.0"}

    # --- 1. CONSULTA BOE (Legislación) ---
    # Buscamos normas sobre contratos o adjudicaciones usando 'query_string' [cite: 72, 85]
    url_boe = "https://boe.es/datosabiertos/api/legislacion-consolidada"
    query_json = '{"query":{"query_string":{"query":"titulo:contrato OR titulo:adjudicacion"}}}'
    params_boe = {"limit": 50, "query": query_json} [cite: 51]

    try:
        r_boe = requests.get(url_boe, params=params_boe, headers=headers, timeout=30)
        if r_boe.status_code == 200: [cite: 24]
            items = r_boe.json().get("data", [])
            # Extraemos identificador, título y URL [cite: 115, 118]
            df_boe = pd.DataFrame([{
                "id": i.get("identificador"),
                "titulo": i.get("titulo"),
                "url": i.get("url_html_consolidada")
            } for i in items])
            df_boe.to_csv("data/boe_legislacion.csv", index=False, encoding="utf-8-sig")
            print(f"BOE: Guardadas {len(df_boe)} normas.")
    except Exception as e:
        print(f"Error en BOE: {e}")

    # --- 2. CONSULTA BORME (Registro Mercantil) ---
    # El BORME utiliza la misma estructura de API del BOE [cite: 17, 43]
    url_borme = f"https://boe.es/datosabiertos/api/borme/sumario/{ayer}"
    
    try:
        r_borme = requests.get(url_borme, headers=headers, timeout=30)
        if r_borme.status_code == 200:
            actos = r_borme.json().get("data", [])
            df_borme = pd.DataFrame([{
                "empresa": a.get("titulo"),
                "acto": a.get("sumario_codigo_texto"),
                "id_acto": a.get("identificador")
            } for a in actos])
            df_borme.to_csv("data/borme_empresas.csv", index=False, encoding="utf-8-sig")
            print(f"BORME: Guardados {len(df_borme)} actos de empresas.")
    except Exception as e:
        print(f"Error en BORME: {e}")

if __name__ == "__main__":
    ejecutar_monitor()
