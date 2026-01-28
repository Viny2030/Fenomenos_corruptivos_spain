import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Monitor Monteverde", layout="wide")
st.title("🔍 Evidencia de Fenómenos Corruptivos")

def cargar(name):
    path = f"data/{name}"
    return pd.read_csv(path) if os.path.exists(path) else None

df_adj = cargar("adjudicaciones_espana.csv")
df_boe = cargar("boe_legislacion.csv")
df_matriz = cargar("matriz_alertas_monteverde.csv")

# --- SECCIÓN DE PRUEBA MATERIAL ---
st.header("🚨 Matriz de Alertas (Prueba Material)")
if df_matriz is not None and not df_matriz.empty:
    st.error("Se han detectado coincidencias que validan la hipótesis de la Cadena de Valor.")
    st.dataframe(df_matriz, use_container_width=True, hide_index=True)
else:
    st.success("No hay alertas críticas en el cruce de hoy.")

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.subheader("Contratos Detectados")
    st.dataframe(df_adj, use_container_width=True) if df_adj is not None else st.write("Sin datos")
with col2:
    st.subheader("Marco Legal (BOE)")
    st.dataframe(df_boe[['titulo_ley']], use_container_width=True) if df_boe is not None else st.write("Sin datos")
