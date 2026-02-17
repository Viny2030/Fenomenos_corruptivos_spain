import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime

# ===============================
# CONFIGURACIÓN DE PÁGINA
# ===============================
st.set_page_config(
    page_title="Monitor Monteverde - Dashboard",
    layout="wide"
)

# Definir ruta de datos (Render usa rutas relativas al proyecto)
DATA_DIR = "data"

# Crear carpeta si no existe para evitar errores de sistema
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# ===============================
# LÓGICA DE BÚSQUEDA DE ARCHIVOS
# ===============================
def buscar_archivos(base_dir):
    """Busca reportes en data/ y subcarpetas."""
    archivos_encontrados = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.endswith((".csv", ".xlsx")):
                # Evitar cargar archivos de respaldo o vigilancia base
                if "adjudicaciones" not in f and "boe_legislacion" not in f:
                    archivos_encontrados.append(os.path.join(root, f))
    
    # Ordenar por fecha de creación (más nuevos primero)
    if archivos_encontrados:
        archivos_encontrados.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return archivos_encontrados

def limpiar_nombre(ruta):
    """Formatea la ruta para el selector (ej: 2026-02 / reporte.csv)"""
    partes = ruta.replace("\\", "/").split("/")
    return " / ".join(partes[-2:]) if len(partes) >= 2 else ruta

ARCHIVOS = buscar_archivos(DATA_DIR)

# ===============================
# DISEÑO DEL DASHBOARD
# ===============================
st.title("🛡️ Dashboard de Vigilancia: Fenómenos Corruptivos")
st.subheader("Análisis basado en la teoría del Ph.D. Vicente Humberto Monteverde")

# MANEJO DE CARGA SIN ARCHIVOS (Evita Error 502)
if not ARCHIVOS:
    st.warning(f"🔎 Buscando reportes en la carpeta: `{DATA_DIR}`...")
    st.info("Si acabas de subir archivos a GitHub, espera un minuto y refresca la página.")
    st.image("https://via.placeholder.com/800x200.png?text=Esperando+Datos+en+Carpeta+Data")
else:
    st.sidebar.success(f"✅ {len(ARCHIVOS)} reportes encontrados")
    
    etiquetas = [limpiar_nombre(a) for a in ARCHIVOS]
    seleccion = st.sidebar.selectbox(
        "Seleccionar Reporte Diario:",
        range(len(etiquetas)),
        format_func=lambda i: etiquetas[i]
    )
    
    ruta_final = ARCHIVOS[seleccion]

    try:
        # Carga inteligente de datos
        if ruta_final.endswith(".xlsx"):
            df = pd.read_excel(ruta_final, engine='openpyxl')
        else:
            df = pd.read_csv(ruta_final)

        # Mapeo de columnas para compatibilidad con main.py original
        mapeo = {
            "origen": "transferencia",
            "indice_total": "indice_fenomeno_corruptivo",
            "nivel_riesgo": "nivel_riesgo_teorico",
            "Contrato_Sospechoso": "detalle",
            "Organismo": "departamento",
            "Indicador_Riesgo": "tipo_decision",
            "Fecha_Deteccion": "fecha"
        }
        df = df.rename(columns=mapeo)

        # MÉTRICAS
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Total de Casos", len(df))
        with m2:
            promedio = df["indice_fenomeno_corruptivo"].mean() if "indice_fenomeno_corruptivo" in df.columns else 0
            st.metric("Índice de Riesgo Promedio", f"{promedio:.1f}/10")
        with m3:
            altos = len(df[df["nivel_riesgo_teorico"] == "Alto"]) if "nivel_riesgo_teorico" in df.columns else 0
            st.metric("Alertas Críticas", altos)

        st.divider()

        # GRÁFICOS
        g1, g2 = st.columns(2)
        
        with g1:
            if "tipo_decision" in df.columns:
                st.write("### Escenarios Detectados")
                fig, ax = plt.subplots()
                df["tipo_decision"].value_counts().plot(kind="bar", ax=ax, color="#1f77b4")
                plt.xticks(rotation=45, ha='right')
                st.pyplot(fig)

        with g2:
            if "nivel_riesgo_teorico" in df.columns:
                st.write("### Distribución de Riesgo")
                fig2, ax2 = plt.subplots()
                df["nivel_riesgo_teorico"].value_counts().plot(kind="pie", autopct="%1.1f%%", ax=ax2)
                st.pyplot(fig2)

        # TABLA DE DATOS
        st.write("### 🔍 Detalle de la Matriz de Alertas")
        st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"Error procesando el archivo {ruta_final}: {e}")

# ===============================
# PIE DE PÁGINA
# ===============================
st.sidebar.divider()
st.sidebar.markdown("""
**Metodología:**
Analiza decisiones legales discrecionales que producen transferencias regresivas de ingresos.
*Autor: Ph.D. Vicente Humberto Monteverde*
""")
st.caption(f"Sincronizado con Render a las {datetime.now().strftime('%H:%M:%S')}")
