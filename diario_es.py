import requests
from lxml import etree
import pandas as pd
import os

def procesar_espana():
    # 1. Asegurar que la carpeta 'data' exista desde el inicio
    if not os.path.exists("data"):
        os.makedirs("data")
        print("Carpeta 'data/' creada.")

    url = "https://contrataciondelestado.es/sindicacion/sindicacion_1044/adjudicaciones.atom"

    # Headers para simular un navegador real y evitar bloqueos
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/atom+xml,application/xml;q=0.9",
        "Accept-Language": "es-ES,es;q=0.9",
    }

    print("Descargando datos de la Plataforma de Contratación de España...")
    
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status() # Lanza error si la descarga falla (404, 500, etc.)

        # Verificación de bloqueo por Firewall (si devuelve HTML en lugar de XML)
        if "<html" in r.text.lower():
            print("ERROR: El servidor devolvió HTML. Es posible que el bot haya sido bloqueado.")
            return

        # Parsear el XML
        parser = etree.XMLParser(recover=True, encoding="utf-8")
        root = etree.fromstring(r.content, parser=parser)

        # Namespaces del estándar ATOM y CÓDICE
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "cbc": "urn:dgpe:names:draft:codice-localization:schema:xsd:AbstractBasicComponents-1",
            "cac": "urn:dgpe:names:draft:codice-localization:schema:xsd:AbstractAggregateComponents-1",
        }

        entries = root.xpath("//atom:entry", namespaces=ns)
        print(f"Se encontraron {len(entries)} entradas.")

        resultados = []
        for entry in entries:
            # Extraer Título
            titulo = entry.xpath("./atom:title/text()", namespaces=ns)
            titulo = titulo[0].strip() if titulo else "Sin título"

            # Extraer Importe
            importe = entry.xpath(".//cbc:TotalAmount/text()", namespaces=ns)
            
            # Extraer Órgano de Contratación
            organo = entry.xpath(".//cac:PartyName/cbc:Name/text()", namespaces=ns)

            resultados.append({
                "titulo": titulo,
                "organo": organo[0] if organo else "N/A",
                "importe": float(importe[0]) if importe else 0.0,
            })

        # Crear el DataFrame
        df = pd.DataFrame(resultados)

        # Guardar siempre el archivo (aunque esté vacío) para que GitHub Actions no falle
        ruta_archivo = "data/adjudicaciones_espana.csv"
        df.to_csv(ruta_archivo, index=False, encoding="utf-8-sig")
        print(f"Archivo guardado con éxito en: {ruta_archivo}")

    except Exception as e:
        print(f"Error durante la ejecución: {e}")
        # Opcional: crear un archivo vacío o de error para que la carpeta 'data' exista
        with open("data/ultimo_error.txt", "w") as f:
            f.write(f"Error en la descarga del {pd.Timestamp.now()}: {str(e)}")

if __name__ == "__main__":
    procesar_espana()
