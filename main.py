import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime
import analisis  # Importa tu motor de lógica ajustado a la teoría

# ===============================
# CONFIGURACIÓN UI
# ===============================
st.set_page_config(page_title="Monitor de Gran Corrupción", layout="wide")

DATA_DIR = "/app/data" if os.path.exists("/app/data") else "data"

# ===============================
# HEADER
# ===============================
st.title("⚖️ Fenómenos Corruptivos Legales")
st.subheader("Implementación computacional de *The Great Corruption*")

st.markdown(f"""
Este sistema analiza **decisiones estatales legales** que, según la teoría económica del 
**Ph.D. Vicente Humberto Monteverde**, pueden generar **transferencias regresivas de ingresos**. 
No detecta delitos penales, sino la intensidad de fenómenos discrecionales.
""")

# ===============================
# CARGA DE DATOS
# ===============================
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

ARCHIVOS = [
    f for f in os.listdir(DATA_DIR) if f.endswith(".xlsx") or f.endswith(".csv")
]

if not ARCHIVOS:
    st.error(f"No se encontraron reportes en la carpeta: {DATA_DIR}")
    st.stop()

archivo_selec = st.selectbox(
    "Seleccioná el reporte a analizar:", sorted(ARCHIVOS, reverse=True)
)
ruta_completa = os.path.join(DATA_DIR, archivo_selec)

try:
    df = (
        pd.read_excel(ruta_completa)
        if archivo_selec.endswith(".xlsx")
        else pd.read_csv(ruta_completa)
    )
except Exception as e:
    st.error(f"Error al leer el archivo: {e}")
    st.stop()

# ===============================
# MÉTRICAS Y GRÁFICOS
# ===============================
df_teoria = df[df["tipo_decision"] != "No identificado"]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Normas Analizadas", len(df))

if not df_teoria.empty:
    m2.metric("Fenómenos Detectados", len(df_teoria))
    m3.metric("Índice Promedio", f"{int(df_teoria['indice_total'].mean())}%")
    m4.metric(
        "Riesgo Alto", len(df_teoria[df_teoria["nivel_riesgo_teorico"] == "Alto"])
    )

    st.divider()

    # Gráfico de Dispersión de Intensidad
    st.subheader("📊 Mapa de Intensidad de Fenómenos Corruptivos")
    fig, ax = plt.subplots(figsize=(10, 4))
    colores = {"Alto": "red", "Medio": "orange", "Bajo": "blue"}

    for nivel, color in colores.items():
        subset = df_teoria[df_teoria["nivel_riesgo_teorico"] == nivel]
        ax.scatter(
            subset["tipo_decision"],
            subset["indice_total"],
            c=color,
            label=nivel,
            s=100,
            edgecolors="black",
        )

    plt.xticks(rotation=45, ha="right")
    ax.set_ylabel("Índice de Intensidad (%)")
    ax.legend(title="Riesgo Teórico")
    st.pyplot(fig)
else:
    st.warning(
        "El reporte seleccionado no contiene fenómenos identificados bajo la matriz teórica."
    )

st.divider()

# ===============================
# EXPLORADOR DE DATOS
# ===============================
st.header("🔍 Exploración de Normas")
cols_vista = [
    "fecha",
    "tipo_decision",
    "indice_total",
    "nivel_riesgo_teorico",
    "origen",
    "mecanismo",
    "link",
]
st.dataframe(df[[c for c in cols_vista if c in df.columns]], use_container_width=True)

# ===============================
# GLOSARIO TEÓRICO
# ===============================
st.divider()
with st.expander("📖 Glosario: Los 7 Escenarios de la Gran Corrupción", expanded=False):
    st.markdown("### Matriz de Transferencia de Ingresos")
    st.write("""
    Según la teoría expuesta en el artículo, estos escenarios representan decisiones estatales 
    discrecionales que redistribuyen la riqueza de forma regresiva:
    """)

    glosario_teorico = {
        "Escenario": [
            "1. Privatizaciones / Concesiones",
            "2. Contratos Públicos",
            "3. Tarifas de Servicios Públicos",
            "4. Autorizaciones de Precios",
            "5. Precios de Salud y Educación",
            "6. Jubilaciones y Pensiones",
            "7. Traslado de Impuestos",
        ],
        "Descripción Teórica": [
            "Transferencia de patrimonio estatal a privados por debajo del valor real.",
            "Sobreprecios o continuación de obras ineficientes basándose en la legalidad.",
            "Aumentos que compensan devaluaciones beneficiando a concesionarias.",
            "Validación discrecional de aumentos en sectores regulados.",
            "Aumentos autorizados por encima de la capacidad de ajuste del salario.",
            "Ajustes de movilidad que transfieren ingresos del jubilado al Estado.",
            "Doble imposición trasladada directamente al consumidor (Fenómeno Desastroso).",
        ],
    }
    st.table(pd.DataFrame(glosario_teorico))

# ==========================================
# REFERENCIA ACADÉMICA (Final de página)
# ==========================================
st.divider()
st.markdown("### 📄 Referencia Académica del Marco Teórico")
st.info(f"""
Este desarrollo implementa la metodología de análisis de **transferencia de ingresos** detallada en el artículo científico del **Ph.D. Vicente Humberto Monteverde**:

**"Great corruption - theory of corrupt phenomena"** Publicado en: *Journal of Financial Crime, Vol. 28 No. 2, pp. 580-596.*

🔗 [**Acceder al artículo original en Emerald Insight**](https://www.emerald.com/jfc/article-abstract/28/2/580/224032/Great-corruption-theory-of-corrupt-phenomena?redirectedFrom=fulltext)
""")