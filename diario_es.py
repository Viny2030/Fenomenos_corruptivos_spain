import requests
from lxml import etree
import pandas as pd
import os
import time

def procesar_espana():
    if not os.path.exists("data"):
        os.makedirs("data")

    url = "https://contrataciondelestado.es/sindicacion/sindicacion_1044/adjudicaciones.atom"

    # Usamos una sesión para manejar cookies automáticamente
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "application/atom+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
        "Referer": "https://contrataciondelestado.es/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    print("Iniciando descarga con sesión camuflada...")
    
    try:
        # Simulamos una pequeña espera para no parecer un bot instantáneo
        time.sleep(2)
        r = session.get(url, headers=headers, timeout=45)
        
        if r.status_code == 200 and "<html" not in r.text.lower()[:100]:
            print("¡Éxito! XML recibido correctamente.")
            # ... (aquí sigue tu lógica de lxml y pandas que ya tienes) ...
            
            # (Asegúrate de guardar el CSV al final del try)
            # df.to_csv("data/adjudicaciones_espana.csv", index=False)
            
        else:
            print(f"Bloqueo detectado. Código: {r.status_code}")
            # Guardamos el HTML de error para inspeccionarlo después
            with open("data/error_debug.html", "w", encoding="utf-8") as f:
                f.write(r.text)
            print("Se guardó 'error_debug.html' para análisis.")

    except Exception as e:
        print(f"Error técnico: {e}")

if __name__ == "__main__":
    procesar_espana()
