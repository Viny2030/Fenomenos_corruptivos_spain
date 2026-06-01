"""
src/seed_aecid.py
=================
Genera seed ampliado (~150 intervenciones) basado en datos reales publicados
por AECID en su portal y memoria anual 2024:
  - Presupuesto total: 645M€
  - América Latina y Caribe: 34%
  - Multipaís / OOII: 29%
  - Norte África y Oriente Medio: 15%
  - África Subsahariana: 13%
  - Asia: 2%, Europa Central: 3%, Otros: 4%
"""
import random
import pandas as pd

random.seed(42)

ENTIDADES_OOII = [
    "PNUD", "UNICEF", "ONU Mujeres", "ACNUR", "PMA", "FAO",
    "OMS", "OPS/OMS", "ACNUR", "OCHA", "OIM", "OIT",
    "Banco Mundial", "BID", "UNFPA",
]
ENTIDADES_ONGD = [
    "Médicos Sin Fronteras", "Cruz Roja Española", "Oxfam Intermón",
    "Cáritas España", "Manos Unidas", "Ayuda en Acción", "Save the Children España",
    "Fundación CODESPA", "Fundación Entreculturas", "Intermón",
    "ACCIÓN CONTRA EL HAMBRE", "Solidaridad Internacional", "ANESVAD",
    "Fundación Vicente Ferrer", "Alianza por la Solidaridad",
]
ENTIDADES_CONSULTORAS = [
    "Deloitte España S.L.", "PwC Advisory S.L.", "TYPSA S.A.",
    "IDOM Consulting S.L.", "Técnica y Proyectos S.A.", "GIZ España",
    "Eptisa Servicios de Ingeniería S.L.", "Europraxis Consulting S.L.",
    "Adam Smith International España", "Crown Agents España",
]

PAISES_LATAM = [
    "Bolivia", "Colombia", "Ecuador", "Guatemala", "Honduras",
    "México", "Nicaragua", "Perú", "Cuba", "Haití",
    "Venezuela", "Paraguay", "El Salvador", "Costa Rica", "Panamá",
]
PAISES_AFRICA = [
    "Etiopía", "Mozambique", "Mali", "Niger", "Senegal",
    "Chad", "Kenya", "Tanzania", "Uganda", "Burkina Faso",
    "Ghana", "Nigeria", "Mauritania",
]
PAISES_MENA = [
    "Marruecos", "Túnez", "Argelia", "Jordania", "Líbano",
    "Palestina", "Siria", "Irak", "Yemen", "Mauritania",
]
PAISES_ASIA = ["Afganistán", "Bangladesh", "Filipinas", "Myanmar", "Nepal"]
PAISES_MULTIPAÍS = ["No Especificado", "América Latina y Caribe", "África Subsahariana",
                     "Global", "Mediterráneo"]

SECTORES = {
    "15110": "Gobernabilidad Democrática",
    "14030": "Agua y Saneamiento",
    "11220": "Educación Primaria",
    "12110": "Salud",
    "31161": "Seguridad Alimentaria",
    "41010": "Medio Ambiente y Cambio Climático",
    "72010": "Acción Humanitaria",
    "15180": "Género e Igualdad",
    "25010": "Desarrollo Económico",
    "16010": "Gobernabilidad Local",
}

TITULOS_BASE = [
    "Programa de fortalecimiento institucional en {pais}",
    "Proyecto agua y saneamiento rural en {pais}",
    "Apoyo a la educación inclusiva en {pais}",
    "Fondo de adaptación climática {pais}",
    "Programa seguridad alimentaria {pais}",
    "Iniciativa gobernabilidad democrática {pais}",
    "Proyecto salud maternoinfantil {pais}",
    "Programa género e igualdad {pais}",
    "Asistencia técnica desarrollo rural {pais}",
    "Proyecto acción humanitaria {pais}",
    "Fortalecimiento sistema judicial {pais}",
    "Programa desarrollo económico local {pais}",
    "Fondo cooperación triangular {pais}",
    "Iniciativa derechos humanos {pais}",
    "Programa biodiversidad y ecosistemas {pais}",
]


def _importe(tipo_entidad: str, sector: str) -> float:
    """Genera importe realista según tipo de entidad y sector."""
    if tipo_entidad == "ooii":
        base = random.uniform(2_000_000, 20_000_000)
    elif tipo_entidad == "ongd":
        base = random.uniform(300_000, 3_000_000)
    else:  # consultora
        base = random.uniform(80_000, 1_500_000)

    # Humanitaria y climática tienden a ser mayores
    if sector in ("72010", "41010"):
        base *= random.uniform(1.2, 2.5)

    return round(base, -3)  # redondear a miles


def generar_seed(n: int = 150) -> pd.DataFrame:
    rows = []
    contador = 1

    # Distribución por región (proporcional a datos reales AECID 2024)
    distribucion = [
        ("latam",    0.34, PAISES_LATAM),
        ("multipaís",0.29, PAISES_MULTIPAÍS),
        ("mena",     0.15, PAISES_MENA),
        ("africa",   0.13, PAISES_AFRICA),
        ("asia",     0.05, PAISES_ASIA),
        ("otros",    0.04, PAISES_LATAM[:3]),  # proxy
    ]

    for region, pct, paises in distribucion:
        n_region = max(1, int(n * pct))
        for _ in range(n_region):
            pais = random.choice(paises)
            sector_code = random.choice(list(SECTORES.keys()))
            sector_nombre = SECTORES[sector_code]

            # Tipo de entidad según región
            if region == "multipaís":
                entidad = random.choice(ENTIDADES_OOII)
                tipo = "ooii"
            elif random.random() < 0.4:
                entidad = random.choice(ENTIDADES_OOII)
                tipo = "ooii"
            elif random.random() < 0.6:
                entidad = random.choice(ENTIDADES_ONGD)
                tipo = "ongd"
            else:
                entidad = random.choice(ENTIDADES_CONSULTORAS)
                tipo = "consultora"

            titulo = random.choice(TITULOS_BASE).format(pais=pais)
            año = random.randint(2021, 2024)
            mes = random.randint(1, 12)

            rows.append({
                "id":           f"ES-AECID-{contador:04d}",
                "titulo":       titulo,
                "entidad":      entidad,
                "tipo_entidad": tipo,
                "importe_eur":  _importe(tipo, sector_code),
                "pais_region":  pais,
                "sectores_crs": sector_code,
                "ambito":       sector_nombre,
                "fecha":        f"{año}-{mes:02d}-01",
                "año":          año,
                "region":       region,
                "fuente":       "seed_realista_v2",
                "url_recurso":  f"https://datos.aecid.es/w/es-aecid-{contador:04d}",
            })
            contador += 1

    df = pd.DataFrame(rows)
    print(f"Seed generado: {len(df)} intervenciones | {df['importe_eur'].sum()/1e6:.1f}M€ total")
    print(f"Distribución entidades: {df['tipo_entidad'].value_counts().to_dict()}")
    return df


if __name__ == "__main__":
    df = generar_seed(150)
    df.to_csv("data/raw/aecid_intervenciones.csv", index=False, encoding="utf-8-sig")
    print("Guardado en data/raw/aecid_intervenciones.csv")