import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import time
import random
import analisis

# ===============================
# CONFIGURACIÓN UI
# ===============================
st.set_page_config(page_title="Gran Corrupción - Monitor Teórico", layout="wide")

if os.path.exists("/app"):
    DATA_DIR = "/app/data"
else:
    DATA_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-419,es;q=0.9",
    "Connection": "keep-alive",
}

# ===============================
# CLASIFICACIÓN BASADA EN PAPER
# ===============================
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


# ===============================
# SCRAPING
# ===============================
def obtener_boletin(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        return response.text if response.status_code == 200 else None
    except:
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


def generar_datos_prueba():
    ejemplos = [
        (
            "Resolución 45/2026: Autorízase nuevo cuadro tarifario de Edenor",
            "Tarifas Servicios Públicos",
        ),
        (
            "Decreto 102/2026: Modificación fórmula de movilidad jubilatoria",
            "Jubilaciones / Pensiones",
        ),
        (
            "Disposición 99: Redeterminación de precios obra Ruta 5",
            "Obra Pública / Contratos",
        ),
        ("Aviso: Venta de pliegos concesión Hidrovía", "Privatización / Concesión"),
        (
            "Resolución: Aumento autorizado cuotas medicina prepaga Marzo",
            "Servicios Privados (Salud/Educación)",
        ),
        (
            "Decreto: Compensación a distribuidoras por devaluación",
            "Compensación por Devaluación",
        ),
    ]
    datos = []
    for _ in range(15):
        texto, tipo = random.choice(ejemplos)
        datos.append(
            {
                "fecha": datetime.now().strftime("%Y%m%d"),
                "seccion": "Simulación Teórica",
                "detalle": texto,
                "link": "#",
                "tipo_decision": tipo,
            }
        )
    return datos


# ===============================
# INTERFAZ STREAMLIT
# ===============================
st.title("⚖️ Gran Corrupción: Teoría de Fenómenos Corruptivos")
st.markdown("""
> *"No son actos de corrupción ilegales, sino fenómenos de distribución de ingresos basados en decisiones discrecionales legales."*
""")

col1, col2 = st.columns([3, 1])
fecha_analisis = col1.date_input("Fecha de Análisis", datetime.now())

if col2.button("Ejecutar Análisis"):
    fecha_str = fecha_analisis.strftime("%Y%m%d")
    registros = []

    with st.spinner("Analizando decisiones estatales..."):
        urls = [
            (
                "primera",
                f"https://www.boletinoficial.gob.ar/seccion/primera/{fecha_str}",
            ),
            (
                "tercera",
                f"https://www.boletinoficial.gob.ar/seccion/tercera/{fecha_str}",
            ),
        ]

        progress = st.progress(0)
        for i, (sec, url) in enumerate(urls):
            html = obtener_boletin(url)
            if html:
                registros.extend(parsear_normas(html, sec, fecha_str))
            progress.progress((i + 1) / len(urls))
            time.sleep(1)

    if not registros:
        st.warning(
            "No se detectaron normas hoy (o bloqueo activo). Usando simulación basada en el Paper."
        )
        registros = generar_datos_prueba()

    df_raw = pd.DataFrame(registros)
    df_procesado, path_excel, df_glosario = analisis.analizar_boletin(df_raw)

    df_teoria = df_procesado[df_procesado["tipo_decision"] != "No identificado"]

    # VISUALIZACIÓN
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Fenómenos Detectados", len(df_teoria))
    promedio = int(df_teoria["indice_total"].mean()) if not df_teoria.empty else 0
    m2.metric("Certeza Teórica Promedio", f"{promedio}%")
    m3.metric("Legalidad", "100% (Estado de Derecho)")

    st.subheader("🔁 Matriz de Transferencia de Ingresos")
    st.info(
        "Muestra quién financia (Origen) y quién recibe la renta (Destino) según la decisión."
    )

    if not df_teoria.empty:
        st.dataframe(
            df_teoria[
                ["tipo_decision", "origen", "destino", "mecanismo"]
            ].drop_duplicates(),
            use_container_width=True,
            hide_index=True,
        )

    if not df_teoria.empty:
        st.subheader("Distribución de la Renta Discrecional")
        st.bar_chart(df_teoria["destino"].value_counts())

    with st.expander("Ver detalle normativo y desglose de cálculo", expanded=True):
        cols_mostrar = [
            "fecha",
            "tipo_decision",
            "indice_total",
            "elaboracion_indice",
            "detalle",
        ]
        cols_validas = [c for c in cols_mostrar if c in df_procesado.columns]
        st.dataframe(df_procesado[cols_validas])

    # GLOSARIO CON REFERENCIA AL FINAL
    with st.expander("📖 Ver Glosario y Definiciones de Columnas"):
        st.markdown("**Definiciones basadas en el Marco Teórico**")
        st.table(df_glosario)

        st.markdown("---")
        st.markdown("#### Referencia Académica")
        st.markdown("""
        **Fuente:** Monteverde, V. H. (2021). *Great corruption: theory of corrupt phenomena*. Journal of Financial Crime.

        🔗 [Leer artículo completo en Emerald Insight](https://www.emerald.com/jfc/article-abstract/28/2/580/224032/Great-corruption-theory-of-corrupt-phenomena?redirectedFrom=fulltext)
        """)

    with open(path_excel, "rb") as f:
        st.download_button(
            label="📥 Descargar Reporte Completo (Excel)",
            data=f,
            file_name=f"GC_Reporte_{fecha_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )