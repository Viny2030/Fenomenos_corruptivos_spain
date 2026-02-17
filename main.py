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

# Forzamos la ruta relativa para Render
DATA_DIR = "data"
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
                # Excluir archivos auxiliares si es necesario
                if "adjudicaciones" not in f and "boe_legislacion" not in f:
                    archivos.append(os.path.join(root, f))
    
    # Ordenar por fecha de modificación (más recientes primero)
    if archivos:
        archivos.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return archivos

def etiqueta_archivo(ruta):
    # Mejora la visualización en el selector para mostrar la subcarpeta (ej. 2026-02)
    partes = ruta.replace("\\", "/").split("/")
    if len(partes) >= 2:
        return f"📁 {' / '.join(partes[-2:])}"
    return ruta

ARCHIVOS = buscar_todos_los_csv_xlsx(DATA_DIR)

# ===============================
# HEADER
# ===============================
st.title("📉 Monitor de Fenómenos Corruptivos – España")
st.subheader("Implementación computacional de *The Great Corruption*")
st.markdown("""
Este sistema analiza **decisiones estatales legales** que, según la teoría económica del 
**Ph.D. Vicente Humberto Monteverde**, pueden generar **transferencias regresivas de ingresos**.
""")

# ===============================
# CARGA DE DATOS (CORREGIDO PARA EVITAR ERROR 502)
# ===============================
if not ARCHIVOS:
    st.warning(f"⚠️ No se encontraron reportes en la carpeta: `{DATA_DIR}`")
    st.info("Asegúrate de que tus archivos CSV/XLSX estén dentro de la carpeta `data/` en GitHub.")
    # No usamos st.stop() para que Render mantenga la app viva y el puerto abierto
else:
    st.success(f"✅ {len(ARCHIVOS)} reportes detectados correctamente.")
    
    etiquetas = [etiqueta_archivo(r) for r in ARCHIVOS]
    idx = st.selectbox(
        "Seleccioná el reporte a visualizar:",
        range(len(etiquetas)),
        format_func=lambda i: etiquetas[i]
    )
    ruta_completa = ARCHIVOS[idx]

    try:
        if ruta_completa.endswith(".xlsx"):
            df = pd.read_excel(ruta_completa, engine='openpyxl')
        else:
            df = pd.read_csv(ruta_completa)
            
        # --- Lógica de procesamiento de datos ---
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
        if "indice_fenomeno_corruptivo" in df.columns:
            if df["indice_fenomeno_corruptivo"].max() > 10:
                df["indice_fenomeno_corruptivo"] = (df["indice_fenomeno_corruptivo"] / 10).round(1)

        # MÉTRICAS PRINCIPALES
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Registros", len(df))
        c2.metric("Fenómenos Detectados", len(df[df["tipo_decision"] != "Sin riesgo detectado"]) if "tipo_decision" in df.columns else 0)
        c3.metric("Índice Promedio", f"{df['indice_fenomeno_corruptivo'].mean():.1f}/10" if "indice_fenomeno_corruptivo" in df.columns else "N/D")
        c4.metric("Casos Riesgo Alto", len(df[df["nivel_riesgo_teorico"] == "Alto"]) if "nivel_riesgo_teorico" in df.columns else 0)

        # VISUALIZACIONES
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
                df["nivel_riesgo_teorico"].value_counts().plot(kind="pie", autopct="%1.1f%%", ax=ax, colors=["red", "orange", "green"])
                ax.set_ylabel("")
                st.pyplot(fig)

        # EXPLORADOR DE DATOS
        st.divider()
        st.header("🔍 Exploración de Decisiones Estatales")
        st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")

# ===============================
# FUNDAMENTO TEÓRICO
# ===============================
st.divider()
with st.expander("📖 Glosario y Fundamentación"):
    st.markdown("""
    **Gran Corrupción - Teoría de los Fenómenos Corruptivos**
    Formulada por el **Ph.D. Vicente Humberto Monteverde**. 
    Este dashboard automatiza la detección de acuerdos colusorios y discrecionalidad técnica.
    """)

st.caption(f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
