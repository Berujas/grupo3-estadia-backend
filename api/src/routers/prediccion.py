from typing import List, Union, Any, Dict
from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from bson import ObjectId
from pymongo.errors import PyMongoError

from ..deps import get_db

# Importa la función del modelo
try:
    from ..ml.predict_nuevos_pacientes import predict_nuevos_pacientes
except Exception:
    raise

router = APIRouter(prefix="/prediccion", tags=["prediccion"])

# ---------- Schemas ----------
class PacienteIn(BaseModel):
    rut: str = Field(..., description="Identificador del paciente (string)")
    edad: int
    sexo: str
    servicio_clinico: str
    prevision: str
    fecha_estimada_de_alta: Union[int, str]
    riesgo_social: Union[int, str]
    riesgo_clinico: Union[int, str]
    riesgo_administrativo: Union[int, str]
    codigo_grd: int

    class Config:
        extra = "allow"  # preserva campos adicionales

def _ensure_indexes(db):
    coll = db.predicciones
    coll.create_index([("rut", 1), ("created_at", -1)], name="predicciones_rut_created_at")
    coll.create_index([("codigo_grd", 1)], name="predicciones_codigo_grd")

def _to_dicts(payload: Union[PacienteIn, List[PacienteIn]]) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [p.dict() for p in payload]
    return [payload.dict()]

def _to_python_scalar(v):
    if isinstance(v, np.generic):
        return v.item()
    return v

def _sanitize_for_json(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        if obj.tzinfo is None:
            obj = obj.replace(tzinfo=timezone.utc)
        return obj.astimezone(timezone.utc).isoformat()
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, list):
        return [_sanitize_for_json(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    return obj

@router.post("/nuevos-pacientes")
def predecir_nuevos_pacientes(
    payload: Union[PacienteIn, List[PacienteIn]] = Body(...),
    persist: bool = True,
    db=Depends(get_db),
):
    """
    Recibe uno o varios pacientes, ejecuta el modelo y (opcional) guarda en Mongo (predicciones).
    Respuesta JSON-safe con probabilidad_sobre_estadia, riesgo_categoria y created_at.
    """
    _ensure_indexes(db)
    records = _to_dicts(payload)

    try:
        resultados = predict_nuevos_pacientes(
            records=records,
            persist=False,      # no escribir CSV desde el endpoint
            return_json=True,   # devolver dicts
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error en predicción: {str(e)}")

    now = datetime.now(timezone.utc)
    docs: List[Dict[str, Any]] = []
    for r_in, r_out in zip(records, resultados):
        doc = {k: _to_python_scalar(v) for k, v in dict(r_in).items()}
        for k, v in dict(r_out).items():
            doc[k] = _to_python_scalar(v)
        doc["created_at"] = now
        docs.append(doc)

    inserted_ids: List[str] = []
    if persist and docs:
        try:
            # Copiar antes de insertar para que PyMongo no mutile los objetos que vamos a devolver
            to_insert = [dict(d) for d in docs]
            res = db.predicciones.insert_many(to_insert)
            inserted_ids = [str(_id) for _id in res.inserted_ids]
        except PyMongoError as e:
            return {
                "count": len(docs),
                "items": _sanitize_for_json(docs),
                "inserted_ids": [],
                "warning": f"No se pudo guardar en Mongo: {str(e)}",
            }

    return {
        "count": len(docs),
        "items": _sanitize_for_json(docs),
        "inserted_ids": inserted_ids,
    }
