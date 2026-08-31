# Cambios aplicados — 31/08/2026

Escribí estos archivos directamente en tu carpeta del repo. **Nada de esto está commiteado todavía** — no tengo terminal disponible en tu compu ahora mismo (el puente no me da shell), así que no pude correr `git`, ni levantar el server para probarlo end-to-end. Quedó como cambios locales sin commitear, para que los revises en PyCharm antes de subir nada.

## Lo que arreglé (verificado por lectura/sintaxis, no por ejecución)

**Seguridad**
- `main.py` — `REFRESH_TOKEN` ya no tiene el default público `"dev-token"`. Si la variable de entorno no está seteada, ahora genera un token aleatorio en cada arranque (el endpoint queda inutilizable hasta que definas `REFRESH_TOKEN` de verdad) en vez de aceptar una contraseña que estaba escrita en el código público.
- `main.py` — `POST /api/refresh` ahora tiene rate limiting básico (mínimo 60s entre llamadas), sin agregar dependencias nuevas.
- `main.py` — CORS: `allow_methods` pasó de `["*"]` a `["GET", "POST"]` (los únicos que usa la API).

**Arquitectura — `main.py` de 1737 → ~500 líneas**
- Los 6 bloques HTML gigantes (landing ES/EN, dashboard, manual ES/EN, autor) se movieron a `templates/*.html` — archivos HTML de verdad, editables sin tocar Python.
- La foto del autor (que estaba en base64 embebido, duplicada 3 veces en el string) ahora es `static/autor.jpg`, un archivo real, referenciado como `/static/autor.jpg`.
- `main.py` carga esos templates con una función chica (`_tpl()`, con cache) — el HTML que se sirve es *exactamente* el mismo que antes, no cambié ni una línea de diseño.
- Bonus: encontré que `db.py` define `restaurar_procesados()` (restaura los CSV desde PostgreSQL al arrancar) pero **nada la llamaba** — el `lifespan` de `main.py` no la invocaba, a pesar de que el propio docstring de `db.py` dice que main.py debería hacerlo. Se la agregué al arranque (con try/except para que nunca tumbe el server si `DATABASE_URL` no está seteada).

**Higiene / código muerto**
- `.gitignore` ahora excluye `.pytest_cache/`, `.idea/`, `*.log`, `*.diff`, `debug_page*.html` y `data/raw/_tmp_backfill_historico/` (la carpeta donde vive el zip de 343 MB).
- `landing.py`, `dashboard.py` (la app Streamlit vieja) y `api_grafo_endpoint.py` quedaron con un docstring de `DEPRECADO` explicando por qué no se usan y sugiriendo `git rm`, en vez de dejarlos como código muerto silencioso. No los borré porque no tengo cómo ejecutar `git rm` desde acá — ver checklist abajo.
- `src/db.py` (que era un duplicado byte a byte de `db.py`, y que nada importaba) ahora es un shim de 10 líneas que re-exporta desde `db.py` (raíz) — la fuente real de verdad sigue siendo `db.py`, que es el que `pipeline.py` importa.
- `docker-compose.yml` corría `streamlit run dashboard.py` (la app vieja, puerto 8501). Lo cambié para que levante lo que realmente está en producción: `uvicorn main:app` en el puerto 8000 — antes, si alguien corría `docker-compose up` para probar localmente, no veía el sitio real.
- `README.md` — la sección "Estructura del proyecto" describía una carpeta `aecid_fondos/` con notebooks y archivos que no existen (`scraper_iati.py`, `red_actores.py`, notebooks 00-07...). La reemplacé por la estructura real, incluyendo `templates/` y `static/` nuevos.

**Tests**
- `tests/test_api.py` estaba vacío. Ahora tiene tests con `TestClient` de FastAPI para los 16 endpoints (páginas HTML + los 9 GET de la API + `/api/refresh`), incluida una prueba de regresión específica para que `"dev-token"` no vuelva a colarse como default.

## Lo que necesito que hagas vos (no lo puedo hacer yo)

### 1. Revisar y probar antes de commitear — importante
Como no pude correr el server ni pytest, hacelo vos antes de subir nada:
```bash
cd Fenomenos_corruptivos_spain1
git diff --stat            # ver qué cambió
uvicorn main:app --reload  # confirmar que / , /dashboard, /manual, /autor, /en se ven igual que antes
pytest --tb=short -q       # confirmar que test_api.py pasa
```
Si algo no se ve bien, avisame y lo corrijo — todo esto quedó sin commitear a propósito.

### 2. Railway — variable de entorno `REFRESH_TOKEN`
Andá a Railway → tu proyecto → Variables, y confirmá que `REFRESH_TOKEN` está seteada con un valor fuerte (`openssl rand -hex 32`, o cualquier string largo y random). Si no la tenías seteada, el endpoint `/api/refresh` va a quedar inaccesible después de este cambio (que es justo lo que se busca) hasta que la configures.

### 3. Borrar los archivos deprecados (si estás de acuerdo)
Los dejé con un aviso en vez de borrarlos. Si querés sacarlos del todo:
```bash
git rm landing.py dashboard.py api_grafo_endpoint.py src/db.py
```
(`src/db.py` es opcional de borrar — hoy es solo un shim de 10 líneas, no molesta.)

### 4. El `.git` pesa 167 MB por un entorno virtual de Windows commiteado en 2026
Confirmé esto clonando tu repo público de GitHub: el checkout actual pesa 6.2 MB, pero el historial de `.git` tiene ~167 MB porque en algún commit viejo se subió `.venv/` completo (arrow.dll, PyArrow, NumPy, etc. — binarios de Windows) y después se borró, pero **borrar en un commit nuevo no lo saca del historial**. Esto no rompe nada hoy, pero hace que cualquier `git clone` de tu repo baje 167 MB de basura.

Para arreglarlo de raíz hace falta reescribir el historial (`git filter-repo` o BFG) y después un `git push --force` — es una operación destructiva que **no voy a hacer sin que me lo pidas explícitamente**, y además necesita tus credenciales de git que no tengo acceso desde acá. Si querés, te paso los comandos exactos cuando estés listo (avisale a cualquiera que tenga el repo clonado, porque después de un force-push va a tener que re-clonar).

*(Buena noticia aparte: el zip de 343 MB en `data/raw/_tmp_backfill_historico/2023.zip` que había marcado en la auditoría anterior — confirmé que ese NO está en git, es solo un archivo local en tu disco. No es un problema de repo, aunque igual conviene borrarlo del disco si ya no lo necesitás.)*

### 5. Cosas que dejé sin tocar, a propósito
- `monitor_completo_es.py` y su workflow (`ejecucion_diaria.yml`) — me dijiste que seguís usando los dos pipelines, así que no toqué nada ahí.
- Los archivos vacíos `confest.py`, `seed_data.py`, `pytest.ini`, `railway.toml` y los archivos sueltos en la raíz (`img*.png`, `grafico_20260120.png`, `reporte_procesado*.xlsx`, `reporte_codigo.pdf`, `bora_20260120.csv`) — no sé si algo los referencia (por ejemplo, capturas para el README) y no quise borrar algo que quizás usás sin preguntarte primero.
- El `README.md` dice licencia MIT pero no hay archivo `LICENSE` en el repo — si querés que lo agregue, decime y lo hago.
