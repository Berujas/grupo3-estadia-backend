from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Response
from pymongo import ReturnDocument
from bson import ObjectId
from ..deps import get_db

router = APIRouter(prefix="/gestion", tags=["gestion"])

def _is_active_episode(db, episodio: str) -> bool:
    last = db.estadias.find_one(
        {"episodio": str(episodio)},
        sort=[("marca_temporal", -1)]
    )
    if not last:
        return False
    alta = (
        last.get("fecha_alta")
        or last.get("fecha_de_alta")
        or last.get("fecha_finalizacion")
        or last.get("estado_de_alta")
    )
    return not bool(alta)

def _id_filter(episodio: str, registroId: str) -> Dict[str, Any]:
    f = {"episodio": str(episodio)}
    if ObjectId.is_valid(registroId):
        f["_id"] = ObjectId(registroId)
    else:
        f["marca_temporal"] = registroId
    return f

@router.get("/episodios/{episodio}/cama-actual")
def cama_actual(episodio: str, include_discharged: bool = True, db=Depends(get_db)):
    episodio = str(episodio)

    if not include_discharged and not _is_active_episode(db, episodio):
        raise HTTPException(status_code=404, detail="Episodio no activo o no encontrado")

    bed = db.camas.find_one(
        {"episodio": episodio},
        sort=[("snapshot_at", -1), ("marca_temporal", -1)]
    )
    if not bed:
        raise HTTPException(status_code=404, detail="Sin cama para episodio")

    out = {
        "episodio": bed.get("episodio"),
        "unidad": bed.get("unidad") or bed.get("asign_enfermeria"),
        "sala": bed.get("sala"),
        "cama": bed.get("cama"),
        "estado": bed.get("estado"),
        "paciente": bed.get("paciente"),
        "timestamp": bed.get("snapshot_at") or bed.get("marca_temporal"),
    }
    return out

@router.post("/estadias", status_code=201)
def crear_estadia(payload: Dict[str, Any], db=Depends(get_db)):
    episodio = str(payload.get("episodio", "")).strip()
    marca_temporal = payload.get("marca_temporal")

    if not episodio or not marca_temporal:
        raise HTTPException(status_code=422, detail="episodio y marca_temporal son obligatorios")

    dup = db.estadias.find_one(
        {"episodio": episodio, "marca_temporal": marca_temporal},
        {"_id": 1}
    )
    if dup:
        raise HTTPException(status_code=409, detail="Duplicado (episodio, marca_temporal)")

    res = db.estadias.insert_one(payload)
    return {"inserted_id": str(res.inserted_id)}

@router.put("/estadias/{episodio}/{registroId}")
def editar_estadia(episodio: str, registroId: str, payload: Dict[str, Any], db=Depends(get_db)):
    # Permite actualizar cualquier campo excepto los inmutables:
    # - _id: id interno de Mongo
    # - episodio y marca_temporal: definen la identidad/clave
    protected = {"_id", "episodio", "marca_temporal"}
    update = {k: v for k, v in payload.items() if k not in protected}

    if not update:
        raise HTTPException(status_code=422, detail="No hay campos válidos para actualizar")

    doc = db.estadias.find_one_and_update(
        _id_filter(episodio, registroId),
        {"$set": update},
        return_document=ReturnDocument.AFTER
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    doc["_id"] = str(doc["_id"])
    return doc

@router.delete("/estadias/{episodio}/{registroId}", status_code=204)
def borrar_estadia(episodio: str, registroId: str, db=Depends(get_db)):
    r = db.estadias.delete_one(_id_filter(episodio, registroId))
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return Response(status_code=204)
