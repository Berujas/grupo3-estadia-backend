from fastapi import FastAPI
from .routers.ingest import router as gestion_router
from .routers.ingest_camas import router as camas_router

app = FastAPI(title="API Backend - Scaffold")

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(gestion_router)   # /gestion/ingest/csv
app.include_router(camas_router)     # /camas/ingest/csv
