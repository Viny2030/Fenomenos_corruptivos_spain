"""
dashboard.py
============
DEPRECADO — esta era una app Streamlit de una iteración anterior del
proyecto. El deploy actual (Dockerfile → `uvicorn main:app`) no la ejecuta
en absoluto; el dashboard real hoy es el HTML+JS servido en GET /dashboard
(main.py + templates/dashboard.html), que consume la API REST del propio
FastAPI. Candidato a borrarse (`git rm dashboard.py`).

Si en algún momento quisieran un dashboard Streamlit real de nuevo,
reescribirlo desde cero contra /api/resumen, /api/fondos, etc., en vez de
reactivar este archivo (quedó desactualizado respecto del esquema de datos
actual).
"""
