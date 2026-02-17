import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime

# ===============================
# CONFIGURACIÓN GENERAL
# ===============================
st.set_page_config(
    page_title="Fenómenos Corruptivos España – Dashboard Teórico",
    layout="wide"
)

DATA_DIR = "/app/data" if os.path.exists("/app/data") else "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# ===============================
# BÚSQUEDA RECURSIVA DE ARCHIVOS
# ===============================
def buscar_todos_los_csv_xlsx(base_dir):
    """Busca CSV y XLSX en el directorio base y todas sus subcarpetas."""
    archivos = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.endswith(".csv") or f.endswith(".xlsx"):
                # Excluir archivos auxiliares
                if "adjudicaciones" not in f and "boe_legislacion" not in f:
                    archivos.append(os.path.join(root, f))
    archivos.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return archivos

def etiqueta_archivo(ruta):
    partes = ruta.replace("\\", "/").split("/")
    if len(partes) >= 3:
        return f"{partes[-2]} / {partes[-1]}"
    return partes[-1]

ARCHIVOS = buscar_todos_los_csv_xlsx(DATA_DIR)

# ===============================
# HEADER
# ===============================
st.title("📉 Monitor de Fenómenos Corruptivos – España")
st.subheader("Implementación computacional de *The Great Corruption*")
st.markdown("""
Este sistema analiza **decisiones estatales legales** que, según la teoría económica del 
**Ph.D. Vicente Humberto Monteverde**, pueden generar **transferencias regresivas de ingresos**. 
No detecta delitos penales, sino la intensidad de fenómenos discrecionales.
""")

# ===============================
# CARGA DE DATOS
# ===============================
if not ARCHIVOS:
    st.error(f"No se encontraron reportes en: {DATA_DIR}")
    st.stop()

st.caption(f"📁 {len(ARCHIVOS)} reportes encontrados en total")

etiquetas = [etiqueta_archivo(r) for r in ARCHIVOS]
idx = st.selectbox(
    "Seleccioná el reporte a visualizar:",
    range(len(etiquetas)),
    format_func=lambda i: etiquetas[i]
)
ruta_completa = ARCHIVOS[idx]

try:
    df = (pd.read_excel(ruta_completa)
          if ruta_completa.endswith(".xlsx")
          else pd.read_csv(ruta_completa))
except Exception as e:
    st.error(f"Error al leer el archivo: {e}")
    st.stop()

# Mapeo de compatibilidad de columnas
mapeo = {
    "origen":       "transferencia",
    "indice_total": "indice_fenomeno_corruptivo",
    "nivel_riesgo": "nivel_riesgo_teorico",
    "Contrato_Sospechoso": "detalle",
    "Organismo":    "departamento",
    "Indicador_Riesgo": "tipo_decision",
    "Fecha_Deteccion": "fecha",
}
df = df.rename(columns=mapeo)

# Normalización escala 0-10
if ("indice_fenomeno_corruptivo" in df.columns
        and df["indice_fenomeno_corruptivo"].max() > 10):
    df["indice_fenomeno_corruptivo"] = (
        df["indice_fenomeno_corruptivo"] / 10
    ).round(1)

# ===============================
# MÉTRICAS PRINCIPALES
# ===============================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Registros", len(df))
c2.metric(
    "Fenómenos Detectados",
    len(df[df["tipo_decision"] != "Sin riesgo detectado"])
    if "tipo_decision" in df.columns else 0,
)
c3.metric(
    "Índice Promedio",
    f"{df['indice_fenomeno_corruptivo'].mean():.1f}/10"
    if "indice_fenomeno_corruptivo" in df.columns else "N/D",
)
c4.metric(
    "Casos Riesgo Alto",
    len(df[df["nivel_riesgo_teorico"] == "Alto"])
    if "nivel_riesgo_teorico" in df.columns else 0,
)

# ===============================
# VISUALIZACIONES
# ===============================
st.divider()
col_g1, col_g2 = st.columns(2)

with col_g1:
    if "tipo_decision" in df.columns:
        st.write("### Distribución por Escenario Teórico")
        fig, ax = plt.subplots()
        df["tipo_decision"].value_counts().plot(kind="barh", ax=ax, color="skyblue")
        st.pyplot(fig)

with col_g2:
    if "nivel_riesgo_teorico" in df.columns:
        st.write("### Intensidad de Riesgo")
        fig, ax = plt.subplots()
        df["nivel_riesgo_teorico"].value_counts().plot(
            kind="pie", autopct="%1.1f%%", ax=ax,
            colors=["red", "orange", "green"]
        )
        ax.set_ylabel("")
        st.pyplot(fig)

# ===============================
# EXPLORADOR DE DATOS
# ===============================
st.divider()
st.header("🔍 Exploración de Decisiones Estatales")

# Mostrar columnas disponibles
cols_preferidas = [
    "fecha", "detalle", "tipo_decision", "departamento",
    "transferencia", "indice_fenomeno_corruptivo",
    "nivel_riesgo_teorico", "Evidencia_Legal_BOE", "link"
]
cols_finales = [c for c in cols_preferidas if c in df.columns]
if not cols_finales:
    cols_finales = df.columns.tolist()

col_config = {}
if "link" in cols_finales:
    col_config["link"] = st.column_config.LinkColumn("Enlace")
if "indice_fenomeno_corruptivo" in cols_finales:
    col_config["indice_fenomeno_corruptivo"] = st.column_config.ProgressColumn(
        "Intensidad", min_value=0, max_value=10
    )

st.dataframe(df[cols_finales], use_container_width=True,
             column_config=col_config)

# ===============================
# GLOSARIO
# ===============================
st.divider()
with st.expander("📖 Glosario y Explicación de Variables"):
    st.markdown("""
    | Variable | Significado Teórico |
    | :--- | :--- |
    | **Tipo de Decisión** | Mapeo hacia los 7 escenarios de la teoría. |
    | **Transferencia** | Sector que soporta el costo económico. |
    | **Índice Fenómeno** | Puntuación 0-10 de discrecionalidad. |
    | **Nivel de Riesgo** | Evaluación cualitativa de opacidad e impacto social. |
    | **Evidencia Legal BOE** | Norma del BOE que ampara la decisión analizada. |
    """)

# ===============================
# FUNDAMENTO TEÓRICO
# ===============================
st.header("🔬 Fundamentación Científica")
tabs = st.tabs(["Núcleo de la Teoría", "Escenarios Analizados", "Impacto Social"])

with tabs[0]:
    st.markdown("""
    **Gran Corrupción - Teoría de los Fenómenos Corruptivos**
    
    Formulada por el **Ph.D. Vicente Humberto Monteverde**, propone que la corrupción no 
    solo son delitos penales, sino decisiones **discrecionales y legales** que producen 
    distribuciones inequitativas de ingresos.
    
    * **Búsqueda de Rentas:** El ingreso se obtiene por subsidios o privilegios del Estado.
    * **Legalidad como Escudo:** Ocurre dentro de la estructura normativa vigente.
    """)

with tabs[1]:
    st.markdown("""
    Los **7 escenarios críticos** de la obra original:
    1. **Privatizaciones Subvaluadas**
    2. **Contratos Públicos Ineficientes**
    3. **Compensación por Devaluación**
    4. **Aumentos Tarifarios Discrecionales**
    5. **Servicios Privados de Necesidad**
    6. **Cálculo Previsional**
    7. **Traslación Impositiva**
    """)

with tabs[2]:
    st.info("""
    **Referencia Académica:** Monteverde, V. H. (2020). *Great corruption – theory of corrupt phenomena*. 
    Journal of Financial Crime.  
    🔗 [Acceder al artículo original](https://www.emerald.com/jfc/article-abstract/28/2/580/224032/Great-corruption-theory-of-corrupt-phenomena?redirectedFrom=fulltext)
    """)

st.caption(f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
""")
