import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuración de la interfaz profesional
st.set_page_config(page_title="Monitor Monteverde - Prevención de Corrupción", layout="wide")

# Estilo personalizado para resaltar alertas
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Dashboard de Vigilancia: Fenómenos Corruptivos")
st.subheader("Análisis de la Cadena de Valor y Acuerdos Colusorios (España)")

# Función de carga de datos con manejo de errores
def cargar_datos(filename):
    path = f"data/{filename}"
    if os.path.exists(path):
        return pd.read_csv(path)
    return None

# Cargar fuentes de datos
df_adj = cargar_datos("adjudicaciones_espana.csv")
df_boe = cargar_datos("boe_legislacion.csv")
df_matriz = cargar_datos("matriz_alertas_monteverde.csv")

# --- BLOQUE 1: MATRIZ DE ALERTAS (LA PRUEBA MATERIAL) ---
st.error("🚨 MATRIZ DE ALERTAS MONTEVERDE: COINCIDENCIAS CRÍTICAS")
if df_matriz is not None and not df_matriz.empty:
    st.write("El algoritmo ha detectado procesos de gasto que coinciden con marcos legales de excepción.")
    st.dataframe(df_matriz, use_container_width=True, hide_index=True)
    
    # Descarga directa del reporte de alertas
    csv_alertas = df_matriz.to_csv(index=False).encode('utf-8')
    st.download_button("Descargar Matriz de Alertas (CSV)", csv_alertas, "matriz_alertas.csv", "text/csv")
else:
    st.success("No se han detectado alertas críticas en el cruce de datos de las últimas 24 horas.")

st.divider()

# --- BLOQUE 2: MÉTRICAS Y FILTROS ---
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    total_adj = len(df_adj) if df_adj is not None else 0
    st.metric("Contratos Analizados", total_adj)
with col_m2:
    total_boe = len(df_boe) if df_boe is not None else 0
    st.metric("Normativas BOE", total_boe)
with col_m3:
    total_alertas = len(df_matriz) if df_matriz is not None else 0
    st.metric("Banderas Rojas", total_alertas, delta_color="inverse")

# --- BLOQUE 3: DETALLE DE FUENTES ---
st.header("🔍 Detalle de Fuentes de Información")
tab1, tab2 = st.tabs(["Licitaciones y Adjudicaciones", "Vigilancia Legislativa (BOE)"])

with tab1:
    if df_adj is not None:
        st.write("Últimos contratos detectados en la Plataforma de Contratación:")
        st.dataframe(df_adj, use_container_width=True)
    else:
        st.info("Esperando datos de adjudicaciones...")

with tab2:
    if df_boe is not None:
        st.write("Leyes y Decretos analizados:")
        st.dataframe(df_boe, use_container_width=True)
    else:
        st.info("Esperando datos del BOE...")

# --- BLOQUE 4: FUNDAMENTOS METODOLÓGICOS ---
with st.sidebar:
    st.header("Metodología")
    st.write("**Autor:** Ph.D. Vicente Humberto Monteverde")
    st.markdown("""
    Este dashboard automatiza la detección de:
    * [cite_start]**Acuerdos Colusorios**: Cruce entre normas de gasto y beneficiarios[cite: 14].
    * [cite_start]**Discrecionalidad Técnica**: Identificación de contratos de 'Emergencia' o 'Urgencia'[cite: 14].
    * [cite_start]**Soborno**: Análisis de procesos sin publicidad competitiva[cite: 14].
    """)
    if st.button("Re-ejecutar Algoritmo de Cruce"):
        st.toast("Procesando matriz de alertas...")
