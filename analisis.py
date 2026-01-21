import pandas as pd
import os
from datetime import datetime

# ===============================
# CONFIGURACIÓN DE ENTORNO
# ===============================
if os.path.exists("/app"):
    DATA_DIR = "/app/data"
else:
    DATA_DIR = os.path.join(os.getcwd(), "data")

# ===============================
# MATRIZ DE TRANSFERENCIAS (TEORÍA)
# ===============================
MATRIZ_TEORICA = {
    "Privatización / Concesión": {
        "origen": "Patrimonio Estatal",
        "destino": "Empresas Privadas (Rent Seeking)",
        "mecanismo": "Subvaluación de activos o canon bajo",
        "certeza_nivel": "Alta",
        "puntos_certeza": 30,
    },
    "Obra Pública / Contratos": {
        "origen": "Contribuyentes (Impuestos Futuros)",
        "destino": "Empresas Contratistas",
        "mecanismo": "Sobreprecios o continuación ineficiente",
        "certeza_nivel": "Media-Alta",
        "puntos_certeza": 25,
    },
    "Tarifas Servicios Públicos": {
        "origen": "Usuarios / Población",
        "destino": "Empresas Concesionarias",
        "mecanismo": "Aumento de tarifa o subsidio cruzado",
        "certeza_nivel": "Muy Alta",
        "puntos_certeza": 40,
    },
    "Compensación por Devaluación": {
        "origen": "Tesoro Nacional (Población)",
        "destino": "Empresas Endeudadas",
        "mecanismo": "Licuación de pasivos privados",
        "certeza_nivel": "Alta",
        "puntos_certeza": 30,
    },
    "Servicios Privados (Salud/Educación)": {
        "origen": "Salario de los Trabajadores",
        "destino": "Empresas de Salud/Educación",
        "mecanismo": "Autorización de aumento por encima de inflación",
        "certeza_nivel": "Alta",
        "puntos_certeza": 30,
    },
    "Jubilaciones / Pensiones": {
        "origen": "Jubilados (Ingreso Diferido)",
        "destino": "Estado (Tesoro)",
        "mecanismo": "Fórmula de movilidad a la baja / Inflación",
        "certeza_nivel": "Muy Alta",
        "puntos_certeza": 40,
    },
    "Traslado Impositivo": {
        "origen": "Consumidor Final",
        "destino": "Estado / Empresas",
        "mecanismo": "Traslado de carga fiscal (Doble imposición)",
        "certeza_nivel": "Muy Alta",
        "puntos_certeza": 40,
    },
}


def aplicar_matriz_teorica(tipo_decision):
    return MATRIZ_TEORICA.get(
        tipo_decision,
        {
            "origen": "Indeterminado",
            "destino": "Indeterminado",
            "mecanismo": "No detectado",
            "certeza_nivel": "Nula",
            "puntos_certeza": 0,
        },
    )


def desglosar_indice(row):
    if row["tipo_decision"] == "No identificado":
        return pd.Series(
            {
                "idx_legalidad": 0,
                "idx_discrecionalidad": 0,
                "idx_certeza": 0,
                "indice_total": 0,
                "elaboracion_indice": "No aplica",
            }
        )

    p_legal = 30
    p_discrecional = 30
    datos_teoricos = MATRIZ_TEORICA.get(row["tipo_decision"])
    p_certeza = datos_teoricos["puntos_certeza"] if datos_teoricos else 0
    certeza_txt = datos_teoricos["certeza_nivel"] if datos_teoricos else "Nula"

    total = p_legal + p_discrecional + p_certeza
    explicacion = f"Legal({p_legal}) + Discrec({p_discrecional}) + Certeza {certeza_txt}({p_certeza}) = {total}%"

    return pd.Series(
        {
            "idx_legalidad": p_legal,
            "idx_discrecionalidad": p_discrecional,
            "idx_certeza": p_certeza,
            "indice_total": total,
            "elaboracion_indice": explicacion,
        }
    )


# ===============================
# PROCESAMIENTO PRINCIPAL
# ===============================


def analizar_boletin(df):
    # 1. Aplicar lógica
    detalles = df["tipo_decision"].apply(aplicar_matriz_teorica)
    df_detalles = pd.json_normalize(detalles)
    df = pd.concat(
        [df.reset_index(drop=True), df_detalles.reset_index(drop=True)], axis=1
    )

    desglose = df.apply(desglosar_indice, axis=1)
    df = pd.concat([df, desglose], axis=1)

    # 2. Glosario con Referencias Académicas (ACTUALIZADO CON DETALLE DE DECISIONES)
    glosario_data = [
        {
            "Columna": "fecha",
            "Descripción": "Fecha de publicación del Boletín Oficial analizado.",
        },
        {
            "Columna": "seccion",
            "Descripción": "Sección del BORA (1ra = Legislación, 3ra = Contrataciones).",
        },
        {
            "Columna": "tipo_decision",
            "Descripción": "Clasificación teórica según las 7 decisiones de 'Great Corruption': 1. Privatización/Concesión, 2. Obra Pública, 3. Tarifas, 4. Devaluación, 5. Servicios Privados, 6. Jubilaciones, 7. Traslado Impositivo.",
        },
        {
            "Columna": "indice_total",
            "Descripción": "Intensidad del fenómeno (0-100%). Suma de Legalidad + Discrecionalidad + Certeza.",
        },
        {
            "Columna": "elaboracion_indice",
            "Descripción": "Fórmula desglosada del cálculo del índice. Ver artículo: https://www.emerald.com/jfc/article-abstract/28/2/580/224032/Great-corruption-theory-of-corrupt-phenomena?redirectedFrom=fulltext",
        },
        {
            "Columna": "origen",
            "Descripción": "Sector que financia o pierde ingresos en la transferencia (Víctima económica).",
        },
        {
            "Columna": "destino",
            "Descripción": "Sector que recibe la renta o beneficio (Beneficiario / Rent Seeking).",
        },
        {
            "Columna": "mecanismo",
            "Descripción": "Herramienta técnica/legal usada para la transferencia (ej. Subsidio, Tarifa).",
        },
        {
            "Columna": "detalle",
            "Descripción": "Resumen extraído de la norma en el Boletín Oficial.",
        },
        {"Columna": "link", "Descripción": "Enlace a la fuente oficial."},
    ]
    df_glosario = pd.DataFrame(glosario_data)

    # 3. Guardar Excel con Múltiples Hojas
    columnas_ordenadas = [
        "fecha",
        "seccion",
        "tipo_decision",
        "indice_total",
        "elaboracion_indice",
        "origen",
        "destino",
        "mecanismo",
        "detalle",
        "link",
    ]
    cols_final = [c for c in columnas_ordenadas if c in df.columns]
    df_final = df[cols_final]

    fecha = datetime.now().strftime("%Y%m%d")
    output_path = os.path.join(DATA_DIR, f"reporte_fenomenos_{fecha}.xlsx")

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df_final.to_excel(writer, index=False, sheet_name="Analisis")
        ws_analisis = writer.sheets["Analisis"]
        ws_analisis.column_dimensions["E"].width = 45
        ws_analisis.column_dimensions["I"].width = 60

        df_glosario.to_excel(writer, index=False, sheet_name="Glosario")
        ws_glosario = writer.sheets["Glosario"]
        ws_glosario.column_dimensions["A"].width = 25
        ws_glosario.column_dimensions['B'].width = 120 # Más ancho para que entren las definiciones largas

    return df, output_path, df_glosario