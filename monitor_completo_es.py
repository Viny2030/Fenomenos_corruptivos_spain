import requests
import pandas as pd
import os
from datetime import datetime, timedelta

def ejecutar_monitor():
    if not os.path.exists("data"):
        os.makedirs("data")

    # Definir fecha de búsqueda (ayer) para el BORME
    ayer = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    headers = {"Accept": "application/json", "User-Agent": "MonitorTransparencia/1.0"}

    # --- 1. CONSULTA BOE (Legislación) ---
    url_boe = "https://boe.es/datosabiertos/api/legislacion-consolidada"
    query_json = '{"query":{"query_string":{"query":"titulo:contrato OR titulo:adjudicacion"}}}'
    params_boe = {"limit": 50, "query": query_json}

    try:
        r_boe = requests.get(url_boe, params=params_boe, headers=headers, timeout=30)
        # El código 200 indica éxito según el manual técnico
        if r_boe.status_code == 200:
            items = r_boe.json().get("data", [])
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
