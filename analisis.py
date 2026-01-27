import pandas as pd
import os
import unicodedata
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN E INFRAESTRUCTURA
# ==========================================
# Configuración de rutas para Docker o Local
if os.path.exists("/app"):
    DATA_DIR = "/app/data"
else:
    DATA_DIR = os.path.join(os.getcwd(), "data")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# ==========================================
# 2. MATRIZ TEÓRICA (Basada en "Great Corruption")
# ==========================================
# Mapeo de los 7 escenarios descritos en el paper [cite: 814-840, 1055-1060]
REGLAS_CLASIFICACION = {
    "Privatización / Concesión": [
        "concesión",
        "privatización",
        "venta de pliegos",
        "adjudicación",
        "licitación pública",
        "subvaluación",
        "precio vil",
    ],
    "Contratos Públicos": [
        "obra pública",
        "redeterminación de precios",
        "contratación directa",
        "ajuste de contrato",
        "continuidad de obra",
        "sobreprecio",
    ],
    "Tarifas Servicios Públicos": [
        "cuadro tarifario",
        "aumento de tarifa",
        "revisión tarifaria",
        "ente regulador",
        "peaje",
        "subsidio",
        "canon",
    ],
    "Autorizaciones de Precios": [
        "compensación cambiaria",
        "diferencia de cambio",
        "precio máximo",
        "secretaría de comercio",
        "ajuste de precio",
    ],
    "Precios Sector Privado (Salud/Educación)": [
        "medicina prepaga",
        "cuota colegio",
        "arancel educativo",
        "superintendencia de servicios de salud",
        "autorízase aumento",
    ],
    "Jubilaciones / Pensiones": [
        "movilidad jubilatoria",
        "haber mínimo",
        "anses",
        "índice de actualización",
        "bono previsional",
        "ripte",
    ],
    "Traslado de Impuestos": [
        "traslado a precios",
        "incidencia impositiva",
        "impuesto al consumo",
        "doble imposición",
        "impuesto al cheque",
        "traslado del impuesto",
    ],
}

MATRIZ_TEORICA = {
    "Privatización / Concesión": {
        "origen": "Patrimonio Estatal",
        "destino": "Empresas Privadas (Rent Seeking)",
        "mecanismo": "Subvaluación de activos o canon bajo [cite: 891]",
        "puntos_certeza": 40,
    },
    "Contratos Públicos": {
        "origen": "Contribuyentes (Impuestos Futuros)",
        "destino": "Empresas Contratistas",
        "mecanismo": "Sobreprecios o continuación ineficiente [cite: 896]",
        "puntos_certeza": 35,
    },
    "Tarifas Servicios Públicos": {
        "origen": "Usuarios / Población",
        "destino": "Empresas Concesionarias",
        "mecanismo": "Aumento de tarifa o subsidio cruzado [cite: 901]",
        "puntos_certeza": 40,
    },
    "Autorizaciones de Precios": {
        "origen": "Consumidores",
        "destino": "Sectores Regulados",
        "mecanismo": "Validación estatal de aumentos [cite: 975]",
        "puntos_certeza": 30,
    },
    "Precios Sector Privado (Salud/Educación)": {
        "origen": "Salario de los Trabajadores",
        "destino": "Empresas de Salud/Educación",
        "mecanismo": "Aumento por encima de capacidad de ajuste [cite: 980]",
        "puntos_certeza": 35,
    },
    "Jubilaciones / Pensiones": {
        "origen": "Jubilados (Sector Débil)",
        "destino": "Estado (Tesoro)",
        "mecanismo": "Fórmula de movilidad a la baja [cite: 984]",
        "puntos_certeza": 40,
    },
    "Traslado de Impuestos": {
        "origen": "Consumidor Final",
        "destino": "Estado / Empresas",
        "mecanismo": "Doble imposición (Traslado de carga fiscal) [cite: 1050]",
        "puntos_certeza": 50,
    },
}

# ==========================================
# 3. FUNCIONES DE PROCESAMIENTO
# ==========================================


def limpiar_texto(texto):
    if not isinstance(texto, str):
        return ""
    return unicodedata.normalize("NFKC", texto).strip()


def clasificar_fenomeno(texto):
    texto = str(texto).lower()
    for tipo, palabras in REGLAS_CLASIFICACION.items():
        if any(p in texto for p in palabras):
            return tipo
    return "No identificado"


def calcular_indice_monteverde(row):
    """
    Calcula el Índice de Fenómeno Corruptivo (0-100).
    Suma Legalidad (30) + Discrecionalidad (30) + Certeza Teórica [cite: 810-811].
    """
    if row["tipo_decision"] == "No identificado":
        return 0, "No aplica"

    legalidad = 30  # Todo acto analizado es legal bajo esta teoría [cite: 151, 319]
    discrecionalidad = 0

    # Palabras clave de discrecionalidad [cite: 224, 322]
    keywords_dis = ["excepción", "urgencia", "facúltase", "directa", "discrecional"]
    texto = str(row.get("detalle", "")).lower()

    if any(k in texto for k in keywords_dis):
        discrecionalidad = 30
    else:
        discrecionalidad = 15  # Discrecionalidad técnica implícita

    puntos_teoria = MATRIZ_TEORICA.get(row["tipo_decision"], {}).get(
        "puntos_certeza", 0
    )
    total = legalidad + discrecionalidad + puntos_teoria
    formula = f"Leg({legalidad}) + Disc({discrecionalidad}) + Teor({puntos_teoria})"

    return total, formula


# ==========================================
# 4. ORQUESTADOR PRINCIPAL
# ==========================================


def analizar_boletin(df):
    """
    Procesa el DataFrame y retorna (df_procesado, path_excel, df_glosario).
    """
    if df.empty:
        return df, None, pd.DataFrame()

    # Curado de Datos
    df["detalle"] = df["detalle"].apply(limpiar_texto)

    # Clasificación y Cálculos
    df["tipo_decision"] = df["detalle"].apply(clasificar_fenomeno)
    df[["indice_total", "elaboracion_indice"]] = df.apply(
        lambda r: pd.Series(calcular_indice_monteverde(r)), axis=1
    )

    # Enriquecimiento Teórico [cite: 811, 813]
    df["origen"] = df["tipo_decision"].apply(
        lambda x: MATRIZ_TEORICA.get(x, {}).get("origen", "-")
    )
    df["destino"] = df["tipo_decision"].apply(
        lambda x: MATRIZ_TEORICA.get(x, {}).get("destino", "-")
    )
    df["mecanismo"] = df["tipo_decision"].apply(
        lambda x: MATRIZ_TEORICA.get(x, {}).get("mecanismo", "-")
    )

    # Clasificación de Riesgo
    df["nivel_riesgo_teorico"] = pd.cut(
        df["indice_total"], bins=[0, 40, 70, 100], labels=["Bajo", "Medio", "Alto"]
    ).fillna("Bajo")

    # Generación de Glosario para UI
    glosario_data = [
        {
            "Columna": "tipo_decision",
            "Descripción": "Mapeo a los 7 escenarios de Great Corruption[cite: 814].",
        },
        {
            "Columna": "indice_total",
            "Descripción": "Intensidad del fenómeno (Suma de Legalidad, Discrecionalidad y Certeza).",
        },
        {
            "Columna": "mecanismo",
            "Descripción": "Técnica legal de transferencia de ingresos identificada[cite: 813].",
        },
        {
            "Columna": "origen",
            "Descripción": "Sector que soporta el costo económico (Víctima teórica).",
        },
    ]
    df_glosario = pd.DataFrame(glosario_data)

    # Exportación
    fecha_str = datetime.now().strftime("%Y%m%d")
    output_path = os.path.join(DATA_DIR, f"reporte_fenomenos_{fecha_str}.xlsx")

    cols_final = [
        "fecha",
        "seccion",
        "tipo_decision",
        "indice_total",
        "nivel_riesgo_teorico",
        "origen",
        "destino",
        "mecanismo",
        "detalle",
        "link",
    ]

    try:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df[cols_final].to_excel(writer, index=False, sheet_name="Analisis")
            df_glosario.to_excel(writer, index=False, sheet_name="Glosario")
    except Exception as e:
        print(f"Error al generar Excel: {e}")

    return df, output_path, df_glosario