from fastapi import FastAPI
from .routers.ingest import router as gestion_router
from .routers.ingest_camas import router as camas_router
from .routers.resumen import router as resumen_router
from .routers import estadias, tareas
from .routers.prediccion import router as prediccion_router

app = FastAPI(title="API Backend - Scaffold")

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(gestion_router)        # /gestion/ingest/csv
app.include_router(camas_router)          # /camas/ingest/csv
app.include_router(resumen_router)        # /gestion/episodios/resumen
app.include_router(estadias.router)
app.include_router(tareas.router)
app.include_router(prediccion_router)
