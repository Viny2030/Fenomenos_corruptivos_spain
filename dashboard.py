import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os

# ===============================
# CONFIGURACIÓN GENERAL
# ===============================

st.set_page_config(
    page_title="Fenómenos Corruptivos – Dashboard Teórico",
    layout="wide"
)

DATA_DIR = "/app/data" if os.path.exists("/app/data") else "."
ARCHIVOS = [f for f in os.listdir(DATA_DIR) if f.startswith("reporte_fenomenos")]

# ===============================
# HEADER
# ===============================

st.title("📉 Fenómenos Corruptivos Legales")
st.subheader("Implementación computacional de *The Great Corruption*")

st.markdown("""
Este sistema **NO detecta delitos ni corrupción penal**.  
Analiza **decisiones estatales legales** que, según la teoría económica,
pueden generar **transferencias regresivas de ingresos** mediante
mecanismos discrecionales.

🔎 El índice presentado mide **intensidad del fenómeno**, no culpabilidad.
""")

# ===============================
# CARGA DE DATOS
# ===============================

if not ARCHIVOS:
    st.error("No se encontraron reportes procesados.")
    st.stop()

archivo = st.selectbox(
    "Seleccioná el reporte a analizar:",
    sorted(ARCHIVOS, reverse=True)
)

df = pd.read_excel(os.path.join(DATA_DIR, archivo))

# ===============================
# MÉTRICAS CLAVE
# ===============================

col1, col2, col3, col4 = st.columns(4)

col1.metric("Normas Analizadas", len(df))
col2.metric(
    "Fenómenos Detectados",
    int((df["indice_fenomeno_corruptivo"] > 0).sum())
)
col3.metric(
    "Índice Promedio",
    round(df["indice_fenomeno_corruptivo"].mean(), 2)
)
col4.metric(
    "Riesgo Alto",
    int((df["nivel_riesgo_teorico"] == "Alto").sum())
)

# ===============================
# DISTRIBUCIÓN POR TIPO
# ===============================

st.header("📌 Tipos de Decisión Estatal Detectados")

fig, ax = plt.subplots()
df["tipo_decision"].value_counts().plot(kind="barh", ax=ax)
ax.set_xlabel("Cantidad de normas")
ax.set_ylabel("Tipo de decisión")
st.pyplot(fig)

# ===============================
# TRANSFERENCIA DE INGRESOS
# ===============================

st.header("🔄 Dirección de la Transferencia de Ingresos")

fig2, ax2 = plt.subplots()
df["transferencia"].value_counts().plot(kind="pie", autopct="%1.1f%%", ax=ax2)
ax2.set_ylabel("")
st.pyplot(fig2)

st.markdown("""
**Interpretación teórica**  
Esta visualización muestra quién **soporta el costo económico**
de las decisiones analizadas según la teoría:
- Población general
- Jubilados
- Estado
""")

# ===============================
# FILTROS INTERACTIVOS
# ===============================

st.header("🔍 Exploración de Normas")

colf1, colf2 = st.columns(2)

tipo_filtro = colf1.multiselect(
    "Filtrar por tipo de decisión:",
    options=df["tipo_decision"].unique(),
    default=df["tipo_decision"].unique()
)

riesgo_filtro = colf2.multiselect(
    "Filtrar por nivel de riesgo:",
    options=df["nivel_riesgo_teorico"].unique(),
    default=df["nivel_riesgo_teorico"].unique()
)

df_filtrado = df[
    (df["tipo_decision"].isin(tipo_filtro)) &
    (df["nivel_riesgo_teorico"].isin(riesgo_filtro))
]

st.dataframe(
    df_filtrado[[
        "fecha",
        "seccion",
        "detalle",
        "tipo_decision",
        "transferencia",
        "indice_fenomeno_corruptivo",
        "nivel_riesgo_teorico",
        "link"
    ]],
    use_container_width=True
)

# ===============================
# NOTA METODOLÓGICA FINAL
# ===============================

st.markdown("---")
st.markdown("""
### 📘 Nota metodológica

Este dashboard implementa la **Teoría de los Fenómenos Corruptivos**
(*The Great Corruption*), la cual sostiene que existen decisiones
estatales **legales** que generan impactos económicos regresivos
sin constituir delitos penales.

El índice presentado:
- ❌ NO acusa
- ❌ NO judicializa
- ✅ CUANTIFICA intensidad teórica del fenómeno

Su objetivo es **análisis institucional, económico y social**.
""")
