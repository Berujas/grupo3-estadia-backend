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
def cama_actual(episodio: str, db=Depends(get_db), include_discharged: bool = True):
    episodio = str(episodio)

    # Si no quieres permitir dados de alta, llama con ?include_discharged=false
    if not include_discharged and not _is_active_episode(db, episodio):
        raise HTTPException(status_code=404, detail="Episodio no activo o no encontrado")

    bed = db.camas.find_one(
        {"episodio": episodio},
        sort=[("snapshot_at", -1), ("marca_temporal", -1)]
    )
    if not bed:
        raise HTTPException(status_code=404, detail="Sin cama para el episodio")

    timestamp = bed.get("snapshot_at") or bed.get("marca_temporal")
    return {
        "episodio": bed.get("episodio"),
        "unidad": bed.get("unidad") or bed.get("asign_enfermeria"),
        "sala": bed.get("sala"),
        "cama": bed.get("cama"),
        "estado": bed.get("estado") or bed.get("tipo_movimiento"),
        "paciente": bed.get("paciente"),
        "timestamp": timestamp,
    }

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

    # Normaliza ausentes a null (None) para campos conocidos
    known_fields = [
        "status","causa_devolucion_rechazo","ultima_modificacion","episodio","que_gestion_se_solicito",
        "fecha_inicio","hora_inicio","informe","tipo_cuenta_1","tipo_cuenta_2","tipo_cuenta_3","nombre",
        "fecha_admision","mes","ano","fecha_alta","cama","texto_libre_diagnostico_admision",
        "diagnostico_transfer","convenio","nombre_de_la_aseguradora","valor_parcial","solicitud_de_traslado",
        "concretado","dias_hospitalizacion","dias_reales","mes2","ano2","fecha_de_nacimiento","sexo","estado",
        "motivo_de_cancelacion","motivo_de_rechazo","tipo_de_solicitud","tipo_de_traslado","motivo_de_traslado",
        "centro_de_destinatario","nivel_de_atencion","servicio_especialidad","fecha_de_finalizacion",
        "hora_de_finalizacion","dias_solicitados_homecare","texto_libre_causa_rechazo","run","rut","marca_temporal"
    ]
    for k in known_fields:
        payload.setdefault(k, None)

    res = db.estadias.insert_one(payload)
    return {"inserted_id": str(res.inserted_id)}

@router.put("/estadias/{episodio}/{registroId}")
def editar_estadia(episodio: str, registroId: str, payload: Dict[str, Any], db=Depends(get_db)):
    # Campos permitidos para editar
    allowed = {
        "fecha_admision","fecha_alta","servicio_especialidad","estado",
        "cama","unidad","sala","valor_parcial","dias_hospitalizacion",
        "ultima_modificacion","status","diagnostico_transfer",
        # añadidos para tu caso
        "tipo_cuenta_1","tipo_cuenta_2","tipo_cuenta_3"
    }
    update = {k: v for k, v in payload.items() if k in allowed}

    if not update:
        raise HTTPException(status_code=422, detail="No hay campos permitidos para actualizar")

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
