from fastapi import FastAPI

app = FastAPI(title="API Backend - Scaffold")

@app.get("/health")
def health():
    return {"status": "ok"}
