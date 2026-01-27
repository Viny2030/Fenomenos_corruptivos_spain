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

# Ajuste de ruta para entorno Docker o local
DATA_DIR = "/app/data" if os.path.exists("/app/data") else "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Buscar reportes generados
ARCHIVOS = [f for f in os.listdir(DATA_DIR) if f.endswith(".xlsx") or f.endswith(".csv")]

# ===============================
# HEADER
# ===============================
st.title("📉 Fenómenos Corruptivos Legales")
st.subheader("Implementación computacional de *The Great Corruption*")

st.markdown("""
Este sistema analiza **decisiones estatales legales** que, según la teoría económica del **Ph.D. Vicente Humberto Monteverde**,
pueden generar **transferencias regresivas de ingresos**. No detecta delitos penales, sino intensidad de fenómenos discrecionales.
""")

# ===============================
# CARGA DE DATOS
# ===============================
if not ARCHIVOS:
    st.error(f"No se encontraron reportes en la carpeta: {DATA_DIR}")
    st.info("Asegúrate de que el script de análisis haya generado los archivos en el volumen de Docker.")
    st.stop()

archivo_selec = st.selectbox(
    "Seleccioná el reporte a analizar:",
    sorted(ARCHIVOS, reverse=True)
)

ruta_completa = os.path.join(DATA_DIR, archivo_selec)

try:
    if archivo_selec.endswith('.xlsx'):
        df = pd.read_excel(ruta_completa)
    else:
        df = pd.read_csv(ruta_completa)
except Exception as e:
    st.error(f"Error al leer el archivo: {e}")
    st.stop()

# ===============================
# VALIDACIÓN DE COLUMNAS
# ===============================
col_indice = "indice_fenomeno_corruptivo"
col_riesgo = "nivel_riesgo_teorico"
col_tipo = "tipo_decision"
col_trans = "transferencia"

# ===============================
# MÉTRICAS CLAVE
# ===============================
col1, col2, col3, col4 = st.columns(4)

# Métrica 1: Normas totales
col1.metric("Normas Analizadas", len(df))

# Métrica 2 y 3: Basadas en el Índice
if col_indice in df.columns:
    conteo_detectados = int((df[col_indice] > 0).sum())
    promedio_indice = round(df[col_indice].mean(), 2)
else:
    conteo_detectados = "N/D"
    promedio_indice = "N/D"

col2.metric("Fenómenos Detectados", conteo_detectados)
col3.metric("Índice Promedio", promedio_indice)

# Métrica 4: Riesgo Alto
if col_riesgo in df.columns:
    conteo_riesgo = int((df[col_riesgo].str.contains("Alto", na=False)).sum())
else:
    conteo_riesgo = "N/D"

col4.metric("Riesgo Alto", conteo_riesgo)

st.markdown("---")

# ===============================
# GRÁFICOS
# ===============================
c_izq, c_der = st.columns(2)

with c_izq:
    if col_tipo in df.columns:
        st.header("📌 Tipos de Decisión")
        fig, ax = plt.subplots()
        df[col_tipo].value_counts().plot(kind="barh", ax=ax, color="skyblue")
        ax.set_xlabel("Cantidad")
        st.pyplot(fig)

with c_der:
    if col_trans in df.columns:
        st.header("🔄 Transferencia de Ingresos")
        fig2, ax2 = plt.subplots()
        df[col_trans].value_counts().plot(kind="pie", autopct="%1.1f%%", ax=ax2)
        ax2.set_ylabel("")
        st.pyplot(fig2)

# ===============================
# EXPLORADOR DE DATOS
# ===============================
st.header("🔍 Exploración de Normas")

columnas_vista = ["fecha", "detalle", col_tipo, col_indice, col_riesgo, "link"]
columnas_existentes = [c for c in columnas_vista if c in df.columns]

st.dataframe(
    df[columnas_existentes],
    use_container_width=True
)

# ===============================
# DICCIONARIO DE VARIABLES Y EXPLICACIÓN
# ===============================
st.markdown("---")
st.header("📖 Diccionario de Variables")
st.markdown("""
A continuación se detalla el significado de las columnas analizadas bajo la teoría de **Fenómenos Corruptivos**:

| Columna | Descripción |
| :--- | :--- |
| **fecha** | Fecha de emisión de la norma en el Boletín Oficial. |
| **tipo_decision** | Clasificación de la norma (Contrataciones, Subsidios, Transferencias, etc.). |
| **transferencia** | Sector económico que financia o se ve afectado por la decisión (Estado, Jubilados, etc.). |
| **indice_fenomeno_corruptivo** | Puntuación de 0 a 10 que mide el grado de discrecionalidad y potencial transferencia regresiva. |
| **nivel_riesgo_teorico** | Evaluación cualitativa (Bajo, Medio, Alto) del riesgo de opacidad en la decisión estatal. |
| **link** | Acceso directo a la norma original para auditoría manual. |
""")

st.info("Nota: Este dashboard es una herramienta de investigación académica basada en algoritmos de detección de patrones en actos administrativos.")

st.markdown("""
**Metodología:** El sistema utiliza técnicas de procesamiento de lenguaje natural (NLP) para identificar patrones en el Boletín Oficial de la República Argentina (BORA) que coinciden con la tipología de fenómenos corruptivos legales descritos en la bibliografía del autor.
""")