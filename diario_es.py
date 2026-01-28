import requests
from lxml import etree
import pandas as pd
import os


def procesar_espana():
    # URL de Adjudicaciones (España)
    url = "https://contrataciondelestado.es/sindicacion/sindicacion_1044/adjudicaciones.atom"

    # Namespaces necesarios para leer el XML de España
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "cbc": "urn:dgpe:names:draft:codice-localization:schema:xsd:AbstractBasicComponents-1",
        "cac": "urn:dgpe:names:draft:codice-localization:schema:xsd:AbstractAggregateComponents-1",
    }

    print("Descargando datos de la Plataforma de Contratación...")
    r = requests.get(url)
    root = etree.fromstring(r.content)
    entries = root.xpath("//atom:entry", namespaces=ns)

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

    # Crear carpeta data si no existe
    if not os.path.exists("data"):
        os.makedirs("data")

    df = pd.DataFrame(resultados)
    df.to_csv("data/adjudicaciones_espana.csv", index=False)
    print(
        f"Proceso finalizado. Se guardaron {len(df)} registros en data/adjudicaciones_espana.csv"
    )


if __name__ == "__main__":
    procesar_espana()