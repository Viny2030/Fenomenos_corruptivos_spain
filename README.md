# 🔍 Trazabilidad de Fondos AECID — Del Presupuesto al Beneficiario Final

> Basado en la estructura de [Fenomenos_corruptivos_spain](https://github.com/Viny2030/Fenomenos_corruptivos_spain).  
> Reconvertido para rastrear **cada euro** de la AECID a través de 7 eslabones hasta el beneficiario final.

---

## 🎯 Problema central

La AECID gestiona ~1.000 M€/año de cooperación internacional. La trazabilidad de esos fondos **colapsa entre el eslabón 3 y el 7**:

| Eslabón | Etapa | Trazabilidad estimada |
|---------|-------|----------------------|
| 1 | Presupuesto General del Estado → AECID | 95% |
| 2 | AECID sede → asignación interna MAP | 80% |
| 3 | Canal: ONGD / OOII / Cooperación financiera | 50% |
| 4 | OTC en país → supervisión local | 40% |
| 5 | Sub-ejecutor: socio local / empresa | 25% |
| 6 | Actividad concreta: obra / servicio / transferencia | 12% |
| 7 | Beneficiario/a final | 8% |

Tres rupturas estructurales explican la caída:

- **R1** — Organismos internacionales (PNUD, UNICEF, ONU Mujeres) agregan fondos multi-donante y no desagregan el origen español
- **R2** — Sub-contratación en país sin obligación de publicar en estándar OCDS
- **R3** — Justificantes de gasto solo accesibles via auditoría (IGAE / Tribunal de Cuentas), no públicos

---

## 🔬 Metodología: Fenómenos Corruptivos aplicados a Cooperación

> *No se analizan solo actos ilegales, sino distribuciones inequitativas de rentas a grupos de interés **con base de legalidad** — legales pero potencialmente capturadas.*  
> — Economía Corruptiva (Dialnet, 2019)

### Indicadores de riesgo

| ID | Nombre | Fórmula | Alerta |
|----|--------|---------|--------|
| ICR | Índice de Concentración de Receptores | HHI normalizado por entidad | > 0.25 |
| SOG | Score de Opacidad Geográfica | % fondos a destino NE | > 30% |
| RES | Ratio Entidad-Sector | cuota de entidad en sector | > 60% |
| VIA | Variación Interanual Anómala | cambio % interanual | > 200% |
| R1 | Ruptura OOII | % fondos a canal multilateral sin desglose | > 40% |
| R2 | Ruptura sub-contratación | % contratos sin trazabilidad OCDS segundo nivel | > 20% |
| R3 | Ruptura justificación | % proyectos sin evaluación final pública | > 50% |

### Modelo de red (grafo bipartito)

```
PGE → AECID → [ONGD / OOII / Coop.Financiera] → OTC → [Socio local / Empresa] → Actividad → Beneficiario
```

Cada nodo es analizable: peso, centralidad, cambios temporales, eslabón de corte.

---

## 📐 Estructura del proyecto

```
aecid_fondos/
│
├── notebooks/
│   ├── 00_ingesta_datos.ipynb          # AECID portal + BDNS + PLACE + IATI + LTAIBG
│   ├── 01_limpieza_normalizacion.ipynb # Entidades, CRS, regiones, campo eslabón_corte
│   ├── 02_analisis_contratos.ipynb     # Contrato a contrato: importes, alertas, cruce PLACE
│   ├── 03_flujos_financieros.ipynb     # Grafo bipartito NetworkX — flujos por eslabón
│   ├── 04_concentracion_actores.ipynb  # HHI, curva de Lorenz, capturas de sector
│   ├── 05_riesgo_trazabilidad.ipynb    # ICR+SOG+RES+VIA + R1+R2+R3 — score por fondo
│   ├── 06_comparativa_ocde.ipynb       # España vs Francia, Alemania, Suecia (CRS)
│   └── 07_dashboard_resumen.ipynb      # Visualizaciones finales + informe ejecutivo
│
├── data/
│   ├── raw/
│   │   ├── aecid_intervenciones.csv    # datos.aecid.es — 835+ registros
│   │   ├── aecid_detalles.csv          # Detalle individual por intervención
│   │   ├── bdns_subvenciones.csv       # BDNS — convenios y subvenciones AECID
│   │   ├── place_contratos.csv         # PLACE / OCDS — contratos adjudicados
│   │   ├── iati_spain.xml              # IATI estándar — España como donante
│   │   ├── ocde_crs_spain.csv          # OCDE CRS donor=20 años 2000-2024
│   │   └── ltaibg_respuestas.csv       # Respuestas a solicitudes de transparencia
│   └── processed/
│       ├── intervenciones_clean.csv    # Datos limpios con campo eslabón_corte
│       ├── contratos_analizados.csv    # Con flags de alerta por contrato
│       ├── scores_riesgo.csv           # ICR+SOG+RES+VIA+R1+R2+R3 por entidad
│       └── trazabilidad_por_fondo.csv  # Score de trazabilidad 0-100 por intervención
│
├── src/
│   ├── scraper_aecid.py                # Portal datos.aecid.es (✓ completo)
│   ├── scraper_bdns.py                 # BDNS — subvenciones y convenios
│   ├── scraper_place.py                # PLACE / OCDS — contratos
│   ├── scraper_iati.py                 # IATI XML parser
│   ├── indicadores_riesgo.py           # ICR, SOG, RES, VIA (✓ completo)
│   ├── trazabilidad_score.py           # R1, R2, R3 + score por eslabón (NUEVO)
│   ├── red_actores.py                  # Grafo bipartito de flujos
│   └── utils.py                        # Funciones auxiliares
│
├── reports/
│   ├── informe_ejecutivo.md
│   └── fichas_entidades/               # Una ficha por entidad top-20
│
├── config/
│   └── params.yaml                     # Umbrales, años, fuentes, eslabones
│
└── requirements.txt
```

---

## 📊 Fuentes de datos

| Fuente | URL | Eslabón | Formato |
|--------|-----|---------|---------|
| Portal AECID | datos.aecid.es/lista-de-intervenciones | 1–3 | HTML scraping |
| BDNS | infosubvenciones.es | 2–3 | API JSON |
| PLACE / OCDS | contrataciondelestado.es | 3–5 | JSON / SPARQL |
| IATI | iatistandard.org | 3–6 | XML / API |
| OCDE CRS | stats.oecd.org | 1–3 | CSV |
| transparencia.gob.es | transparencia.gob.es | 2–5 | CSV |
| LTAIBG (solicitudes) | access-info.org / portal transparencia | 5–7 | Manual + CSV |

---

## 🚀 Inicio rápido

```bash
git clone https://github.com/TU_USUARIO/aecid_fondos_analisis
cd aecid_fondos_analisis
pip install -r requirements.txt

# Paso 1: descargar datos de todos los eslabones
python src/scraper_aecid.py        # eslabón 1-3
python src/scraper_bdns.py         # eslabón 2-3
python src/scraper_place.py        # eslabón 3-5

# Paso 2: ejecutar notebooks en orden
jupyter lab notebooks/
```

---

## ⚖️ Nota metodológica

Análisis basado exclusivamente en **datos públicos** (AECID, OCDE, Hacienda, transparencia.gob.es, IATI). No implica acusaciones de ilegalidad. El marco de fenómenos corruptivos analiza inequidades estructurales en la distribución de fondos públicos.

Las solicitudes LTAIBG se realizan conforme a la Ley 19/2013 de Transparencia, Acceso a la Información Pública y Buen Gobierno.

---

## 📄 Licencia

MIT — Datos abiertos, análisis reproducible.