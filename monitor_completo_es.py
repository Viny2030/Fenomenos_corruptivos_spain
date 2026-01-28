import requests
import pandas as pd
import os
from datetime import datetime, timedelta

def ejecutar_monitor():
    if not os.path.exists("data"):
        os.makedirs("data")

    # Fecha de ayer para el BORME (Manual técnico apartado 2.1)
    ayer = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    headers = {"Accept": "application/json", "User-Agent": "MonitorMonteverde/1.0"}

    # --- 1. CONSULTA BOE (Leyes de Contratación) ---
    url_boe = "https://boe.es/datosabiertos/api/legislacion-consolidada"
    # Buscamos términos clave de tu artículo: contrato, adjudicación, emergencia
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
            print(f"BOE: {len(df_boe)} normas de riesgo detectadas.")
    except Exception as e:
        print(f"Error en BOE: {e}")

    # --- 2. CONSULTA BORME (Actos Mercantiles Diarios) ---
    url_borme = f"https://boe.es/datosabiertos/api/borme/sumario/{ayer}"
    df_borme = pd.DataFrame()
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
            print(f"BORME: {len(df_borme)} actos de empresas registrados ayer.")
    except Exception as e:
        print(f"Error en BORME: {e}")

    # --- 3. ALGORITMO DE CRUCE (Detección de Colusión) ---
    if not df_boe.empty and not df_borme.empty:
        # Buscamos si empresas del BORME aparecen en títulos de leyes del BOE
        # Esto detecta "leyes con nombre y apellido"
        alertas = []
        for _, ley in df_boe.iterrows():
            for _, empresa in df_borme.iterrows():
                # Si el nombre de la empresa está contenido en el título de la ley
                if empresa['empresa'].upper() in ley['titulo_ley'].upper() and len(empresa['empresa']) > 5:
                    alertas.append({
                        "fecha_alerta": ayer,
                        "empresa": empresa['empresa'],
                        "acto_mercantil": empresa['acto'],
                        "evidencia_boe": ley['titulo_ley'],
                        "link": ley['url_ley'],
                        "tipo_riesgo": "Coincidencia Directa (Posible Tráfico de Influencias)"
                    })
        
        if alertas:
            df_alertas = pd.DataFrame(alertas)
            df_alertas.to_csv("data/matriz_alertas_monteverde.csv", index=False, encoding="utf-8-sig")
            print(f"¡ATENCIÓN!: Se han detectado {len(df_alertas)} alertas de cruce.")
        else:
            print("No se detectaron coincidencias directas en las últimas 24hs.")

if __name__ == "__main__":
    ejecutar_monitor()
