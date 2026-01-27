import os
import pandas as pd
from datetime import datetime

# Configuración de ruta
DATA_DIR = "/app/data" if os.path.exists("/app/data") else "data"


def simular_raspado_bora():
    """
    Simulación de obtención de datos enfocada en las áreas
    críticas de la teoría de Monteverde.
    """
    # En la realidad, aquí iría tu lógica de BeautifulSoup o Selenium
    data = [
        {
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "seccion": "Sección Segunda",  # Contratos y licitaciones [cite: 895]
            "detalle": "ADJUDICACIÓN DIRECTA por urgencia para la concesión de transporte de energía.",
            "link": "https://www.boletinoficial.gob.ar/ejemplo1",
        },
        {
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "seccion": "Sección Primera",  # Normas generales y tarifas [cite: 900]
            "detalle": "Aumento del cuadro tarifario de medicina prepaga y servicios de salud.",
            "link": "https://www.boletinoficial.gob.ar/ejemplo2",
        },
    ]

    df = pd.DataFrame(data)

    # Guardar crudo para que analisis.py lo procese
    file_name = f"bora_{datetime.now().strftime('%Y%m%d')}.csv"
    df.to_csv(os.path.join(DATA_DIR, file_name), index=False)
    return df