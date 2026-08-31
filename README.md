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
Fenomenos_corruptivos_spain1/
│
├── main.py                  # App FastAPI: rutas UI + API REST (servida en Railway)
├── pipeline.py               # Orquestador: ingesta (scrapers) + análisis + scores
├── db.py                     # Persistencia opcional en PostgreSQL (Railway) — no-op sin DATABASE_URL
├── monitor_completo_es.py    # Script legado, corrido por .github/workflows/ejecucion_diaria.yml
│
├── templates/                 # HTML estático servido por main.py (sin lógica de plantillas)
│   ├── landing_es.html / landing_en.html
│   ├── dashboard.html
│   ├── manual_es.html / manual_en.html
│   └── autor.html
├── static/
│   └── autor.jpg              # Foto del autor (antes embebida en base64 dentro de main.py)
│
├── src/                       # Scrapers + cálculo de indicadores
│   ├── scraper_aecid.py       # Portal datos.aecid.es
│   ├── scraper_bdns.py        # BDNS — convocatorias y concesiones
│   ├── scraper_place.py       # PLACE / OCDS — contratos adjudicados
│   ├── indicadores_riesgo.py  # ICR, SOG, RES, VIA
│   ├── trazabilidad_score.py  # R1, R2, R3 + score por eslabón (E1-E7)
│   └── seed_aecid.py
│
├── data/
│   ├── raw/                   # CSVs descargados por los scrapers (aecid, bdns, place)
│   └── processed/             # analisis_completo.csv, trazabilidad_por_fondo.csv, scores_riesgo.csv
│
├── reports/
│   └── informe_ejecutivo.md   # Generado por pipeline.py
│
├── config/
│   └── params.yaml            # Umbrales de riesgo, sectores CRS
│
├── tests/
│   ├── test_trazabilidad.py   # Tests del modelo de scoring
│   └── test_api.py            # Smoke tests de los endpoints REST (FastAPI TestClient)
│
├── .github/workflows/         # Actualización diaria (AECID + legado) y backfill PLACE histórico
├── Dockerfile                 # Imagen usada por Railway (uvicorn main:app)
└── requirements.txt
```

> Nota: `data/processed/*.csv` y `reports/informe_ejecutivo.md` se versionan en git a propósito —
> es lo que le da a Railway datos disponibles inmediatamente después de cada deploy, sin depender
> de que el pipeline corra primero. `db.py` (PostgreSQL) es una capa de respaldo adicional, opcional.

---

## 🚀 Inicio rápido

```bash
git clone https://github.com/Viny2030/Fenomenos_corruptivos_spain
cd Fenomenos_corruptivos_spain
pip install -r requirements.txt

# Pipeline completo (ingesta + análisis) — genera data/processed/ y reports/
python pipeline.py

# Levantar la API + dashboard localmente
uvicorn main:app --reload
# → http://127.0.0.1:8000/dashboard

# Tests
pytest --tb=short -q
```

Variables de entorno relevantes (ver `.env` / configuración de Railway):

| Variable | Requerida | Uso |
|---|---|---|
| `REFRESH_TOKEN` | **Sí, en producción** | Header `X-Refresh-Token` para `POST /api/refresh`. Si no está seteada, `main.py` genera un token aleatorio en cada arranque (el endpoint queda inutilizable hasta que la configures). |
| `DATABASE_URL` | No | Si está seteada (Postgres de Railway), `db.py` persiste los CSVs procesados como respaldo entre deploys. |

---

## ⚖️ Nota metodológica

Análisis basado exclusivamente en **datos públicos** (AECID, OCDE, Hacienda, transparencia.gob.es, IATI). No implica acusaciones de ilegalidad. El marco de fenómenos corruptivos analiza inequidades estructurales en la distribución de fondos públicos.

Las solicitudes LTAIBG se realizan conforme a la Ley 19/2013 de Transparencia, Acceso a la Información Pública y Buen Gobierno.

---

## 📄 Licencia

MIT — Datos abiertos, análisis reproducible.