import requests
from lxml import etree
import pandas as pd
import os


def procesar_espana():
    url = "https://contrataciondelestado.es/sindicacion/sindicacion_1044/adjudicaciones.atom"

    # IMPORTANTE: Esto hace que parezca que entramos desde un navegador
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    print("Descargando datos de la Plataforma de Contratación...")
    r = requests.get(url, headers=headers)

    # Usamos un parser que ignora errores menores de etiquetas
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(r.content, parser=parser)

    # El resto del código sigue igual...

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