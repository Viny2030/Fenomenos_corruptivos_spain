# Auditoría técnica — Fenomenos_corruptivos_spain1

**Repositorio local:** `Fenomenos_corruptivos_spain1` (PyCharm) · **Deploy:** Railway (`/dashboard`, FastAPI, `main.py`)
**Fecha:** 31/08/2026

El dashboard en producción funciona correctamente (KPIs, tabla de fondos, rankings de entidades y gráficos cargan con datos reales — 834 fondos, 675,2M€ analizados). El problema no es que esté roto: es que el repo acumuló dos generaciones de arquitectura superpuestas, higiene de git débil y un endpoint de administración protegido con una contraseña por defecto pública. Abajo va todo ordenado por prioridad.

---

## 1. Crítico — seguridad

### 1.1 `POST /api/refresh` protegido con un token por defecto público
En `main.py`:

```python
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN", "dev-token")
...
@app.post("/api/refresh")
def refresh(x_refresh_token: str = Header(None)):
    if x_refresh_token != REFRESH_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")
    ...
    subprocess.run([sys.executable, "pipeline.py", "--solo-analisis"], timeout=300, ...)
```

Como el repo es público en GitHub, el valor por defecto `"dev-token"` es público. **Si en Railway no configuraste la variable de entorno `REFRESH_TOKEN` con un valor fuerte, cualquiera puede disparar tu pipeline** (`subprocess.run(..., timeout=300)`) enviando ese header, tantas veces como quiera — no hay rate limiting. Esto es un vector de denegación de servicio y de consumo de recursos/costos en Railway.

**Acción:** entrá a Railway → Variables → confirmá que `REFRESH_TOKEN` existe y tiene un valor largo y aleatorio (`openssl rand -hex 32`). Además, considerá:
- Eliminar el default inseguro: `REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]` (que falle al arrancar si no está seteada, en vez de caer a `"dev-token"`).
- Agregar rate limiting básico al endpoint (p. ej. `slowapi`) para que no se pueda golpear en loop aunque el token se filtre.

### 1.2 CORS completamente abierto
```python
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
```
Para una API de solo lectura de datos públicos esto no es grave en sí, pero es más permisivo de lo necesario: no hace falta `allow_methods=["*"]` (solo usás GET y POST) ni `allow_headers=["*"]`. Si en algún momento agregás autenticación por cookies, esta config combinada con `allow_credentials=True` sería una falla real. Dejalo explícito (`allow_methods=["GET", "POST"]`) para que quede documentado qué se permite.

### 1.3 Posible archivo de 342 MB versionado en git
`data/raw/_tmp_backfill_historico/2023.zip` pesa **342.911.532 bytes (~343 MB)**. Tu `.gitignore` actual es:
```
.venv/
__pycache__/
*.pyc
```
No excluye `data/`, así que si ese zip fue agregado con `git add` en algún momento, quedó en el historial de git — y GitHub rechaza archivos de más de 100 MB (o los pide vía Git LFS). Esto puede estar impidiendo pushes, o infló el `.git` local a un tamaño enorme.

**Acción:** desde el repo, corré `git ls-files | xargs du -h 2>/dev/null | sort -rh | head -20` (o `git log --stat` para ese path) para confirmar si está trackeado. Si lo está: sacalo del working tree del sistema de archivos versionado y, si ya está en el historial, usá `git filter-repo` (o BFG Repo-Cleaner) para purgarlo del historial completo — un simple `git rm` no libera el espacio del `.git`.

---

## 2. Alto — higiene del repositorio

### 2.1 `.gitignore` insuficiente
Solo ignora `.venv/`, `__pycache__/` y `*.pyc`. Deberías sumar (como mínimo):
```
data/
reports/
*.log
*.pdf
*.xlsx
debug_page*.html
.pytest_cache/
.idea/
*.diff
```
Ahora mismo tenés en la raíz del repo, probablemente commiteados: `pipeline.log` (159 KB), tres `debug_page*.html` (~100 KB cada uno, dumps de scraping), `reporte_codigo.pdf` (788 KB), `reporte_procesado_2026012*.xlsx`, `grafico_20260120.png`, `img.png`/`img_1.png`/`img_2.png`/`img_3.png`, `bora_20260120.csv` y cuatro `diff_*.diff`. Son artefactos de trabajo/debug, no código fuente — no deberían vivir en la raíz de un repo que después se clona para producir un `Dockerfile` (`COPY . .` los copia todos a la imagen).

### 2.2 Archivos vacíos / placeholder sin usar
`confest.py` (0 bytes — probable typo de `conftest.py`, y de hecho no cumple ninguna función de pytest así nombrado), `seed_data.py` (0 bytes), `pytest.ini` (0 bytes), `railway.toml` (0 bytes) y `tests/test_api.py` (0 bytes) están vacíos. O les das contenido real, o los borrás — tal como están solo generan confusión sobre qué hace cada uno.

### 2.3 `db.py` duplicado byte a byte
`db.py` (raíz) y `src/db.py` son **idénticos**. `pipeline.py` importa `from src.trazabilidad_score import ...` (vía paquete `src`) pero para otras cosas usa `sys.path.insert(0, str(SRC))` e imports planos (`from scraper_aecid import ...`). Es una mezcla de dos convenciones de import. Recomendación: quedate con un solo `db.py` (por ejemplo, movés todo a `src/db.py` y en `main.py`/`pipeline.py` importás `from src.db import ...`), y unificá el estilo de import en todo `pipeline.py` a imports de paquete (`from src.scraper_aecid import ...`), eliminando el `sys.path.insert`.

### 2.4 Código muerto de una arquitectura anterior
- `landing.py` define su propio `LANDING_HTML` + `FOTO_BASE64` (comentario: *"Agregar al main.py existente"*), pero `main.py` tiene **su propia copia inline** de `LANDING_HTML`/`FOTO_BASE64` y nunca importa `landing.py`. Es un archivo huérfano.
- `dashboard.py` es una app **Streamlit** completamente separada (`import streamlit as st`), de una generación anterior del proyecto — el deploy actual (`Dockerfile` → `uvicorn main:app`) no la ejecuta en absoluto. El nombre choca además con el endpoint `/dashboard` de `main.py`, lo cual confunde a cualquiera que abra el repo por primera vez.
- `api_grafo_endpoint.py` define su propia versión de `@app.get("/api/grafo")`, pero `main.py` **ya tiene ese mismo endpoint definido inline** (línea ~1628) y nunca importa este archivo.

**Acción:** o herramientas de este tipo se archivan en una carpeta `legacy/` con un README que explique que están desactivados, o se borran directamente (siempre están en el historial de git si hace falta recuperarlos).

---

## 3. Medio — arquitectura y mantenibilidad

### 3.1 `main.py` de 1737 líneas mezclando todo
`main.py` concentra: routing FastAPI, lógica de negocio (agregaciones con pandas), y **HTML+CSS+JS completos como strings de Python** (`LANDING_HTML`, `DASHBOARD_HTML`, `MANUAL_HTML`, `AUTOR_HTML` y sus versiones `_EN`) — varios miles de caracteres cada uno, incluyendo una imagen en base64 de ~8 KB embebida directamente en el código fuente. Esto hace que:
- Cualquier cambio de texto/estilo en el sitio requiera tocar un archivo Python de 1700 líneas.
- No haya highlighting/lint de HTML/CSS, ni forma de que un diseñador toque el front sin tocar Python.
- El diff de cualquier cambio visual sea gigante y difícil de revisar.

**Recomendación:** migrar a `Jinja2Templates` de FastAPI con una carpeta `templates/` (`landing.html`, `dashboard.html`, `manual.html`, `autor.html`, con variante `lang` en vez de duplicar todo en `_EN`) y `static/` para CSS/JS/imagen del autor como archivo real (no base64 embebido). Es un refactor de una tarde y baja muchísimo el tamaño y la complejidad de `main.py`.

### 3.2 README desalineado con la estructura real
El `README.md` describe una estructura de carpetas `aecid_fondos/...` que no coincide con el repo real (todo vive en la raíz, no dentro de `aecid_fondos/`). Vale la pena actualizarlo — es la primera impresión de cualquiera (incluido tu propio yo del futuro) que entra al repo.

---

## 4. Medio — CI/CD

Tenés **dos workflows que corren diariamente y commitean sobre `data/`**:
- `ejecucion_diaria.yml` (07:00 UTC) → corre `monitor_completo_es.py`, instala solo `pandas requests` (no usa `requirements.txt`), y hace `git add data/`.
- `ejecucion_diaria_aecid.yml` (06:00 UTC) → corre `python pipeline.py --forzar`, instala `requirements.txt`, y hace `git add data/raw/ data/processed/ reports/ pipeline.log`.

Corren en horarios distintos así que hoy probablemente no chocan, pero son **dos generaciones de pipeline en paralelo** (el viejo `monitor_completo_es.py` con dependencias mínimas, y el nuevo `pipeline.py` modular con scrapers en `src/`) escribiendo sobre rutas superpuestas de `data/`. Si en algún momento se disparan juntos manualmente (`workflow_dispatch`) o se corre un backfill largo, el `git pull --rebase` de uno puede pisar cambios del otro. Vale la pena preguntarse si `monitor_completo_es.py` todavía cumple una función distinta de `pipeline.py`, o si es el predecesor que quedó corriendo por inercia.

---

## 5. Medio — testing

- `tests/test_trazabilidad.py` (162 líneas) tiene tests reales sobre `ModeloTrazabilidad` e indicadores de riesgo — bien.
- `tests/test_api.py` está **vacío**, pese a que `main.py` expone 10 endpoints REST (`/api/status`, `/api/resumen`, `/api/fondos`, `/api/trazabilidad`, `/api/entidades`, `/api/riesgo`, `/api/informe`, `/api/refresh`, `/api/mensual`, `/api/grafo`). El workflow `test.yml` corre `pytest` en cada push a `main`/`desarrollo`, pero al no haber tests de la API, un cambio que rompa un endpoint (por ejemplo, una columna renombrada en un CSV que tira un `KeyError`) no lo detecta el CI.

**Acción sugerida:** con `TestClient` de FastAPI (ya tenés `httpx` en `requirements.txt`, que es lo que usa `TestClient`) es rápido cubrir al menos que cada endpoint devuelve 200 y la forma esperada del JSON.

---

## Resumen de acciones priorizadas

1. **Hoy:** confirmar en Railway que `REFRESH_TOKEN` está seteada con un valor fuerte (no `dev-token`).
2. **Esta semana:** verificar si `data/raw/_tmp_backfill_historico/2023.zip` (343 MB) está trackeado en git; si lo está, purgarlo del historial y ampliar `.gitignore` (sección 2.1) para que no vuelva a pasar con `data/`, logs, PDFs, xlsx, debug HTML.
3. **Esta semana:** borrar o archivar `landing.py`, `dashboard.py` (Streamlit) y `api_grafo_endpoint.py` — no se ejecutan y confunden sobre qué es el sistema real. Unificar `db.py` (raíz) con `src/db.py`.
4. **Próximas dos semanas:** extraer `LANDING_HTML`/`DASHBOARD_HTML`/`MANUAL_HTML`/`AUTOR_HTML` de `main.py` a templates Jinja2 + estáticos.
5. **Cuando puedas:** escribir tests mínimos para la API (`tests/test_api.py`), decidir si `monitor_completo_es.py` sigue teniendo un rol o se retira, y actualizar el `README.md` a la estructura real del repo.

---

*Nota: no ejecuté el endpoint `/api/refresh` contra el sitio en producción (dispara un proceso real en tu servidor) — si querés que lo pruebe para confirmar si el token por defecto sigue activo, decímelo y lo hago con tu autorización explícita.*
