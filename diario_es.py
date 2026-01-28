import requests
from lxml import etree
import pandas as pd
import os


def procesar_espana():
    url = "https://contrataciondelestado.es/sindicacion/sindicacion_1044/adjudicaciones.atom"

    # Headers muy completos para parecer un navegador real
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/atom+xml,application/xml;q=0.9",
        "Accept-Language": "es-ES,es;q=0.9",
    }

    print("Descargando datos de la Plataforma de Contratación...")
    r = requests.get(url, headers=headers, timeout=30)

    # Verificación: ¿Nos han bloqueado?
    if "<html" in r.text.lower():
        print("ERROR: El servidor devolvió HTML (posible bloqueo).")
        # Intentamos extraer algo aunque sea texto plano
        return

    try:
        # Usamos el parser con recuperación de errores
        parser = etree.XMLParser(recover=True, encoding="utf-8")
        root = etree.fromstring(r.content, parser=parser)

        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "cbc": "urn:dgpe:names:draft:codice-localization:schema:xsd:AbstractBasicComponents-1",
            "cac": "urn:dgpe:names:draft:codice-localization:schema:xsd:AbstractAggregateComponents-1",
        }

        entries = root.xpath("//atom:entry", namespaces=ns)
        print(f"Se encontraron {len(entries)} entradas.")

        resultados = []
        for entry in entries:
            titulo = entry.xpath("./atom:title/text()", namespaces=ns)[0]
            importe = entry.xpath(".//cbc:TotalAmount/text()", namespaces=ns)
            organo = entry.xpath(".//cac:PartyName/cbc:Name/text()", namespaces=ns)

            resultados.append(
                {
                    "titulo": titulo,
                    "organo": organo[0] if organo else "N/A",
                    "importe": float(importe[0]) if importe else 0.0,
                }
            )

        if not os.path.exists("data"):
            os.makedirs("data")
        df = pd.DataFrame(resultados)
        df.to_csv("data/adjudicaciones_espana.csv", index=False)
        print("Archivo guardado con éxito.")

    except Exception as e:
        print(f"Error al procesar el XML: {e}")

if __name__ == "__main__":
    procesar_espana()