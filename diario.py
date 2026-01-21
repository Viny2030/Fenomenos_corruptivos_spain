import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import time
import analisis  # Reutilizamos tu cerebro teórico

# Configuración
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-419,es;q=0.9",
    "Connection": "keep-alive",
}

# --- LÓGICA COPIADA DE MAIN.PY (Versión Headless) ---
TIPO_DECISION_ESTATAL = {
    "Privatización / Concesión": [
        "concesión",
        "privatización",
        "venta de pliegos",
        "adjudicación",
        "licitación pública nacional e internacional",
    ],
    "Obra Pública / Contratos": [
        "obra pública",
        "redeterminación de precios",
        "contratación directa",
        "ajuste de contrato",
        "continuidad de obra",
    ],
    "Tarifas Servicios Públicos": [
        "cuadro tarifario",
        "aumento de tarifa",
        "revisión tarifaria",
        "ente regulador",
        "precio mayorista",
        "peaje",
    ],
    "Compensación por Devaluación": [
        "compensación cambiaria",
        "diferencia de cambio",
        "bono fiscal",
        "subsidio extraordinario",
    ],
    "Servicios Privados (Salud/Educación)": [
        "medicina prepaga",
        "cuota colegio",
        "arancel educativo",
        "superintendencia de servicios de salud",
        "autorízase aumento",
    ],
    "Jubilaciones / Pensiones": [
        "movilidad jubilatoria",
        "haber mínimo",
        "anses",
        "índice de actualización",
        "bono previsional",
    ],
    "Traslado Impositivo": [
        "traslado a precios",
        "incidencia impositiva",
        "impuesto al consumo",
        "tasas y contribuciones",
    ],
}


def clasificar_decision_estatal(texto: str) -> str:
    texto = texto.lower()
    for tipo, palabras in TIPO_DECISION_ESTATAL.items():
        if any(p in texto for p in palabras):
            return tipo
    return "No identificado"


def obtener_boletin(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        return response.text if response.status_code == 200 else None
    except Exception as e:
        print(f"Error conectando a {url}: {e}")
        return None


def parsear_normas(html, seccion_nombre, fecha_target):
    soup = BeautifulSoup(html, "html.parser")
    normas = []
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if any(x in href for x in ["DetalleNorma", "idNorma", "detalleAviso"]):
            detalle = link.get_text(strip=True)
            if len(detalle) > 15:
                tipo = clasificar_decision_estatal(detalle)
                normas.append(
                    {
                        "fecha": fecha_target,
                        "seccion": seccion_nombre,
                        "detalle": detalle,
                        "link": f"https://www.boletinoficial.gob.ar{href}"
                        if not href.startswith("http")
                        else href,
                        "tipo_decision": tipo,
                    }
                )
    return normas


# --- EJECUCIÓN PRINCIPAL ---
if __name__ == "__main__":
    print("--- INICIANDO ROBOT DIARIO ---")
    fecha_obj = datetime.now()
    fecha_str = fecha_obj.strftime("%Y%m%d")
    print(f"Fecha objetivo: {fecha_str}")

    registros = []
    secciones = ["primera", "tercera"]

    for seccion in secciones:
        url = f"https://www.boletinoficial.gob.ar/seccion/{seccion}/{fecha_str}"
        print(f"Escaneando: {seccion}...")
        html = obtener_boletin(url)

        if html:
            nuevos = parsear_normas(html, seccion, fecha_str)
            print(f"   -> Encontrados {len(nuevos)} items.")
            registros.extend(nuevos)
        else:
            print(f"   -> Sin respuesta del servidor para {seccion}.")
        time.sleep(2)

    if registros:
        print("Procesando datos con teoría 'Great Corruption'...")
        df_raw = pd.DataFrame(registros)
        # Usamos tu modulo de analisis
        df_proc, path, _ = analisis.analizar_boletin(df_raw)

        # Filtramos solo lo relevante para mostrar en consola
        alertas = len(df_proc[df_proc["tipo_decision"] != "No identificado"])
        print(f"✅ EXITO. Reporte generado en: {path}")
        print(f"📊 Total Normas: {len(df_proc)} | Alertas Teóricas: {alertas}")
    else:
        print("⚠️ No se encontraron normas hoy (o hubo bloqueo).")