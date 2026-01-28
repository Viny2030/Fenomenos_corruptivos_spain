import requests
import pandas as pd
import os

def procesar_espana_api():
    # Asegurar que la carpeta 'data' exista
    if not os.path.exists("data"):
        os.makedirs("data")

    # Endpoint oficial de la API del BOE para lista de normas
    # Documentación: apartado 2.1 del manual técnico
    url = "https://boe.es/datosabiertos/api/legislacion-consolidada"

    # Definimos la búsqueda según el manual (ejemplo: buscar 'crisis' en el título)
    # Se pueden añadir más filtros como 'materia@codigo' o 'rango@codigo'
    params = {
        "limit": 50,          # Máximo de resultados por defecto [cite: 51]
        "offset": 0,         # Desde el primer resultado [cite: 51]
        "query": '{"query":{"query_string":{"query":"titulo:crisis"}}}' # Sintaxis JSON [cite: 72, 101]
    }

    headers = {
        "Accept": "application/json", # Solicitamos formato JSON [cite: 20, 61]
        "User-Agent": "RobotMonitorViny/1.0"
    }

    print("Consultando la API oficial del BOE...")
    
    try:
        # Petición GET según indica el manual [cite: 18]
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            # La respuesta contiene un nodo 'status' y un nodo 'data' [cite: 163, 167]
            items = data.get("data", [])
            
            if not items:
                print("No se encontraron resultados para los criterios de búsqueda.")
                # Creamos archivo vacío para que Git no de error
                pd.DataFrame().to_csv("data/adjudicaciones_espana.csv", index=False)
                return

            # Procesamos los items recibidos (campos definidos en apartado 2.1) [cite: 118]
            resultados = []
            for item in items:
                resultados.append({
                    "id": item.get("identificador"),
                    "titulo": item.get("titulo"),
                    "departamento": item.get("departamento", {}).get("texto") if isinstance(item.get("departamento"), dict) else item.get("departamento"),
                    "fecha_publicacion": item.get("fecha_publicacion"),
                    "url_boe": item.get("url_html_consolidada")
                })

            df = pd.DataFrame(resultados)
            df.to_csv("data/adjudicaciones_espana.csv", index=False, encoding="utf-8-sig")
            print(f"Éxito: Se guardaron {len(resultados)} registros en data/adjudicaciones_espana.csv")
            
        else:
            print(f"Error de API: {response.status_code} - {response.text}")
            with open("data/api_error.log", "w") as f:
                f.write(f"Status: {response.status_code}\nContent: {response.text}")

    except Exception as e:
        print(f"Error técnico al conectar con la API: {e}")

if __name__ == "__main__":
    procesar_espana_api()
