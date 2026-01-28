import pandas as pd
import os
from datetime import datetime

def generar_matriz_alertas():
    # Rutas de archivos
    ruta_adj = "data/adjudicaciones_espana.csv"
    ruta_boe = "data/boe_legislacion.csv"
    ruta_salida = "data/matriz_alertas_monteverde.csv"

    if not os.path.exists(ruta_adj) or not os.path.exists(ruta_boe):
        print("Error: No se encuentran los archivos base en la carpeta 'data'.")
        return

    # 1. Cargar datos
    df_adj = pd.read_csv(ruta_adj)
    df_boe = pd.read_csv(ruta_boe)

    # 2. Definir criterios de "Acuerdo Colusorio" (Keywords de riesgo)
    # Basado en tu artículo sobre decisiones discrecionales
    keywords_riesgo = ['URGENCIA', 'EMERGENCIA', 'DIRECTA', 'EXCEPCIONAL', 'COVID']
    
    alertas = []

    # 3. Algoritmo de Cruce
    for _, contrato in df_adj.iterrows():
        titulo_c = str(contrato.get('titulo', '')).upper()
        
        # Si el contrato tiene una bandera roja de discrecionalidad
        if any(k in titulo_c for k in keywords_riesgo):
            
            # Buscamos en el BOE la norma que "legaliza" o enmarca este fenómeno
            # Filtramos leyes que mencionen contratos o adjudicaciones
            coincidencias_legales = df_boe[df_boe['titulo'].str.contains('Contrato|Adjudicación|Medidas', case=False, na=False)]
            
            for _, ley in coincidencias_legales.head(3).iterrows():
                alertas.append({
                    "Fecha_Deteccion": datetime.now().strftime("%Y-%m-%d"),
                    "Evidencia_Contrato": contrato.get('titulo'),
                    "Organismo_Emisor": contrato.get('departamento', 'N/D'),
                    "Indicador_Riesgo": "Discrecionalidad/Acuerdo Colusorio",
                    "Marco_Legal_BOE": ley['titulo'],
                    "Fase_Cadena_Valor": "Ejecución (Fenómeno Corrupto Legal)"
                })

    # 4. Guardar la Matriz (La prueba material)
    df_final = pd.DataFrame(alertas)
    if not df_final.empty:
        df_final.to_csv(ruta_salida, index=False, encoding="utf-8-sig")
        print(f"✅ Matriz generada con {len(df_final)} alertas encontradas.")
    else:
        # Si no hay alertas, creamos el archivo con cabeceras para no romper el Dashboard
        pd.DataFrame(columns=["Fecha_Deteccion", "Indicador_Riesgo"]).to_csv(ruta_salida, index=False)
        print("⚠️ No se detectaron coincidencias críticas hoy.")

if __name__ == "__main__":
    # Asegúrate de llamar a la función
    generar_matriz_alertas()
