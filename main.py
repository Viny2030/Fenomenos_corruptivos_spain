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
