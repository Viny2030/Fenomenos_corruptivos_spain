# Informe Ejecutivo — Trazabilidad de Fondos AECID
*Generado: 30/06/2026 19:30*

---

## Resumen ejecutivo

| Métrica | Valor |
|---------|-------|
| Total fondos analizados | 41.4 M€ |
| Intervenciones | 8 |
| Entidades receptoras | 6 |
| Score medio de trazabilidad | 44/100 |

---

## Trazabilidad por eslabón de corte

| Eslabón | Etapa | Nº fondos | M€ | % total |
|---------|-------|-----------|-----|---------|
| 3 | OOII sin desglose (R1) | 7 | 40.5 | 97.8% |
| 4 | Destino geográfico opaco | 1 | 0.9 | 2.2% |

---

## Clasificación de riesgo integrado

| Clasificación | Nº fondos | M€ | % total |
|---------------|-----------|-----|---------|
| AMARILLO | 1 | 0.9 | 2.2% |
| NARANJA | 7 | 40.5 | 97.8% |

---

## Top 10 intervenciones de mayor riesgo

| Título | Entidad | Importe | Eslabón | Score | Clasificación |
|--------|---------|---------|---------|-------|---------------|
| Refugiados Siria ACNUR | ACNUR | 6.4M€ | E3 | 56 | NARANJA |
| Seguridad Alimentaria Sahel FAO | FAO | 7.2M€ | E3 | 55 | NARANJA |
| Salud Mozambique OMS | OMS | 3.1M€ | E3 | 54 | NARANJA |
| Programa Agua y Saneamiento Bolivia | PNUD | 4.5M€ | E3 | 54 | NARANJA |
| Fondo Adaptación Climática África | PNUD | 15.0M€ | E3 | 54 | NARANJA |
| Microfinanzas Ecuador PNUD | PNUD | 1.5M€ | E3 | 54 | NARANJA |
| Educación Guatemala UNICEF | UNICEF | 2.8M€ | E3 | 53 | NARANJA |
| Gobernabilidad Honduras consultoría | Consultoría XYZ S.L. | 0.9M€ | E4 | 40 | AMARILLO |

---

## Fuentes utilizadas

- **aecid**: 8 registros (`aecid_intervenciones.csv`)
- **bdns**: 3 registros (`bdns_subvenciones.csv`)
- **place**: 200 registros (`place_contratos.csv`)
- **ltaibg**: 0 registros (`ltaibg_respuestas.csv`)

---

## Notas metodológicas

- **R1**: Fondos a organismos internacionales (OOII) que agregan multi-donante sin desglosar la contribución española en IATI.
- **R2**: Contratos con adjudicación directa o sin publicación de sub-contratos en estándar OCDS.
- **R3**: Proyectos con importe >500.000€ sin evaluación final publicada ni respuesta favorable a solicitud LTAIBG.
- **Score integrado**: 60% riesgo corruptivo (ICR+SOG+RES+VIA) + 40% trazabilidad invertida.
- Análisis basado exclusivamente en datos públicos. No implica acusaciones de ilegalidad.

*Marco teórico: Fenómenos corruptivos — Economía Corruptiva (Dialnet, 2019)*
