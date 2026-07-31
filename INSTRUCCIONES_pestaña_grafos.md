# Pestaña "Grafos" para el Monitor Trazabilidad AECID

## Qué hace

Agrega una segunda pestaña al `/dashboard` (junto a "Resumen") con una **red interactiva**
que muestra el flujo de fondos: **AECID → Entidad receptora → Eslabón donde se corta la
trazabilidad (E1–E7)**. Los nodos de entidad se colorean según su `clasificacion`
(ROJO/NARANJA/AMARILLO/VERDE), su tamaño refleja el importe canalizado, y las aristas
punteadas marcan flujos sin contrato PLACE/OCDS trazable (ruptura R2). Es la
materialización visual del "grafo bipartito" que ya describe el README del proyecto
(PGE → AECID → canal → OTC → sub-ejecutor → actividad → beneficiario), construida con
los datos reales que ya produce el pipeline (`analisis_completo.csv`), sin necesidad de
una base de datos nueva ni de scraping adicional.

No usa Postgres/SQLAlchemy porque **`main.py` no los usa hoy** — todo el dashboard lee
`data/processed/*.csv` con pandas, y el nuevo endpoint sigue exactamente ese mismo patrón.

## Archivos de este paquete

1. `api_grafo_endpoint.py` — nueva ruta `GET /api/grafo` para pegar en `main.py`.
2. `dashboard_html_actualizado.txt` — el bloque `DASHBOARD_HTML` completo, con la pestaña
   "Grafos" ya integrada, para reemplazar el bloque actual.

## Pasos para aplicarlo

1. Abrí `main.py` en tu repo local.
2. **Reemplazá el bloque `DASHBOARD_HTML = r"""..."""`** completo (útimamente son las
   líneas ~368 a ~536) por el contenido de `dashboard_html_actualizado.txt` (sin la
   cabecera de instrucciones, solo desde `DASHBOARD_HTML = r"""` hasta el `"""` final).
3. **Agregá la nueva ruta**: pegá el contenido de `api_grafo_endpoint.py` al final de
   `main.py`, después de la función `mensual()` (la última ruta `/api/mensual`) y antes
   de cualquier bloque `if __name__ == "__main__":` si existe.
4. Confirmá que no rompiste la indentación: la nueva función `def grafo(...)` debe
   quedar al mismo nivel (sin indentar) que las demás funciones `def resumen()`, `def
   fondos()`, etc.
5. Probá en local: `uvicorn main:app --reload` y entrá a `http://localhost:8000/dashboard`,
   click en la pestaña "🕸️ Grafos".
6. Hacé commit y push — Railway redeploya automáticamente desde `main`.

## Qué NO requiere

- No hay que instalar ninguna librería Python nueva (usa pandas, ya en `requirements.txt`).
- No hay que tocar `pipeline.py`, los notebooks, ni los CSV — el endpoint agrega
  (`groupby` manual) sobre las columnas que ya existen: `entidad`, `importe_eur`,
  `eslabon_corte`, `clasificacion`, `ruptura_r2`.
- La librería de grafos (`vis-network`) se carga por CDN (`unpkg.com`), igual que ya
  se hace con Chart.js — no pasa por `npm`/bundler.

## Verificación recomendada antes de dar por cerrado

- Abrir `/api/grafo?top=30` directamente en el navegador y confirmar que devuelve JSON
  con `nodes` y `edges` no vacíos (si `analisis_completo.csv` no existe todavía, va a
  devolver listas vacías — igual que hacen hoy `/api/resumen` y `/api/fondos`).
- Verificar visualmente que los nodos "E3"–"E7" aparecen conectados a las entidades
  correctas y que el tooltip (al pasar el mouse) muestra importe y clasificación.
- Revisar que la pestaña "Resumen" sigue funcionando igual que antes (no debería haber
  cambiado nada de su lógica, solo quedó envuelta en un `<div id="view-resumen">`).

## Limitación de esta sesión

No pude acceder al `.zip` que subiste ni ejecutar el repo localmente porque el entorno
de ejecución (sandbox) no arrancó por falta de espacio en disco del lado del servicio.
Reconstruí `main.py` línea por línea leyendo el repo público en GitHub
(`github.com/Viny2030/Fenomenos_corruptivos_spain`), así que el código de arriba está
verificado contra el `main.py` real desplegado, pero no lo pude correr yo mismo. Probalo
en local antes de pushear a producción.
