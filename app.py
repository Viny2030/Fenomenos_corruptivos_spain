import streamlit as st
import pandas as pd
import os

# Configuración de la página
st.set_page_config(page_title="Monitor de Transparencia España", layout="wide")

st.title("🔍 Monitor de Transparencia y Contratación")
st.markdown("---")

# Función para cargar datos desde la carpeta data
def cargar_csv(nombre_archivo):
    ruta = f"data/{nombre_archivo}"
    if os.path.exists(ruta):
        return pd.read_csv(ruta)
    return None

# Cargar tus dos archivos
df_contratos = cargar_csv("adjudicaciones_espana.csv")
df_leyes = cargar_csv("boe_legislacion.csv")

# --- BLOQUE DE DATOS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Últimas Adjudicaciones")
    if df_contratos is not None:
        st.write(f"Se encontraron **{len(df_contratos)}** registros de contratos.")
        # Mostramos la tabla. Ajusta los nombres de columnas si cambiaron
        st.dataframe(df_contratos, use_container_width=True, hide_index=True)
    else:
        st.error("No se encontró 'adjudicaciones_espana.csv' en la carpeta data.")

with col2:
    st.subheader("⚖️ Legislación (BOE)")
    if df_leyes is not None:
        st.write(f"Se encontraron **{len(df_leyes)}** normativas relacionadas.")
        st.dataframe(df_leyes[['titulo', 'id']], use_container_width=True, hide_index=True)
    else:
        st.error("No se encontró 'boe_legislacion.csv' en la carpeta data.")

st.markdown("---")

# --- BLOQUE DE CRUCE Y ANÁLISIS ---
st.header("🎯 Análisis de Coincidencias")

if df_contratos is not None and df_leyes is not None:
    # Filtro de búsqueda manual para el usuario
    busqueda = st.text_input("Buscar palabra clave en ambos archivos (ej. 'Urgencia', 'Directa', o nombre de empresa):")
    
    if busqueda:
        # Buscamos en contratos
        res_c = df_contratos[df_contratos.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)]
        # Buscamos en leyes
        res_l = df_leyes[df_leyes.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)]
        
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"Resultados en Contratación: {len(res_c)}")
            st.dataframe(res_c, use_container_width=True)
        with c2:
            st.write(f"Resultados en BOE: {len(res_l)}")
            st.dataframe(res_l, use_container_width=True)
    else:
        st.info("Ingresa una palabra para buscar posibles vínculos o patrones de riesgo.")
else:
    st.warning("Faltan archivos para realizar el cruce.")

# Footer simple
st.sidebar.markdown("""
**Fuentes de Datos:**
- Plataforma de Contratación del Sector Público.
- API Datos Abiertos BOE.
""")
