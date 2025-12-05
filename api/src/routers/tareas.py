from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from bson import ObjectId
from pymongo import ReturnDocument, errors
from ..deps import get_db

router = APIRouter(prefix="/tareas", tags=["tareas"])

# -----------------------
# Helpers
# -----------------------
def _oid(id_str: str) -> ObjectId:
    if not ObjectId.is_valid(id_str):
        raise HTTPException(status_code=400, detail="ID inválido")
    return ObjectId(id_str)

def _ensure_indexes(db):
    # gestoras: nombre único
    db.gestoras.create_index("name", unique=True, name="gestoras_name_unique")
    # tareas: filtros útiles
    db.tareas.create_index([("gestor", 1)], name="tareas_gestor")
    db.tareas.create_index([("paciente_episodio", 1)], name="tareas_paciente_episodio")
    db.tareas.create_index([("status", 1)], name="tareas_status")
    db.tareas.create_index([("prioridad", 1)], name="tareas_prioridad")
    db.tareas.create_index([("fecha_vencimiento", 1)], name="tareas_fecha_vencimiento")
    db.tareas.create_index([("updated_at", -1)], name="tareas_updated_at")

def _validate_gestora_exists(db, name: str):
    if not db.gestoras.find_one({"name": name}):
        raise HTTPException(status_code=422, detail="La gestora no existe en la lista")

def _validate_paciente_exists(db, episodio: str):
    # Descomenta si quieres forzar que exista en 'estadias'
    if not db.estadias.find_one({"episodio": str(episodio)}):
        raise HTTPException(status_code=422, detail="Paciente/episodio no existe en 'estadias'")

def _doc_to_out(d: Dict[str, Any]) -> Dict[str, Any]:
    if not d:
        return d
    d = dict(d)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # Datetimes -> ISO
    for k in ("fecha_inicio", "fecha_vencimiento", "created_at", "updated_at"):
        if isinstance(d.get(k), datetime):
            d[k] = d[k].isoformat()
    return d

# -----------------------
# Esquemas
# -----------------------
TIPOS = {"social", "general", "clinica", "administrativa", "coordinacion"}
PRIORIDADES = {"alta", "media", "baja", "critica"}
STATUSES = {"completado", "en progreso", "pendiente", "cancelada"}

class GestoraCreate(BaseModel):
    name: str = Field(..., min_length=1, strip_whitespace=True)

class GestoraOut(BaseModel):
    id: str
    name: str

class TareaBase(BaseModel):
    # referencias
    paciente_episodio: str = Field(..., description="Episodio (string) de un paciente")
    gestor: str = Field(..., description="Nombre de la gestora (debe existir)")

    # libres
    rol: Optional[str] = None
    tipo: str = Field(..., description=f"Uno de: {', '.join(sorted(TIPOS))}")
    prioridad: str = Field(..., description=f"Uno de: {', '.join(sorted(PRIORIDADES))}")

    titulo: str
    descripcion: Optional[str] = None

    fecha_inicio: Optional[datetime] = None
    fecha_vencimiento: Optional[datetime] = None
    status: str = Field("pendiente", description=f"Uno de: {', '.join(sorted(STATUSES))}")

class TareaUpdate(BaseModel):
    paciente_episodio: Optional[str] = None
    gestor: Optional[str] = None
    rol: Optional[str] = None
    tipo: Optional[str] = None
    prioridad: Optional[str] = None
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    fecha_inicio: Optional[datetime] = None
    fecha_vencimiento: Optional[datetime] = None
    status: Optional[str] = None

# -----------------------
# Endpoints Gestoras
# -----------------------
@router.post("/gestoras", response_model=GestoraOut, status_code=201)
def crear_gestora(body: GestoraCreate, db=Depends(get_db)):
    _ensure_indexes(db)
    try:
        res = db.gestoras.insert_one({"name": body.name})
    except errors.DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Ya existe una gestora con ese nombre")
    doc = db.gestoras.find_one({"_id": res.inserted_id})
    return GestoraOut(id=str(doc["_id"]), name=doc["name"])

@router.get("/gestoras", response_model=List[GestoraOut])
def listar_gestoras(db=Depends(get_db)):
    _ensure_indexes(db)
    cur = db.gestoras.find({}, {"name": 1})
    return [GestoraOut(id=str(x["_id"]), name=x["name"]) for x in cur]

# -----------------------
# Endpoints Tareas
# -----------------------
@router.post("", status_code=201)
def crear_tarea(body: TareaBase, db=Depends(get_db)):
    _ensure_indexes(db)

    # Validaciones
    _validate_gestora_exists(db, body.gestor)
    _validate_paciente_exists(db, body.paciente_episodio)

    if body.tipo not in TIPOS:
        raise HTTPException(status_code=422, detail="tipo inválido")
    if body.prioridad not in PRIORIDADES:
        raise HTTPException(status_code=422, detail="prioridad inválida")
    if body.status not in STATUSES:
        raise HTTPException(status_code=422, detail="status inválido")

    now = datetime.utcnow()
    doc = {
        "paciente_episodio": body.paciente_episodio,
        "gestor": body.gestor,
        "rol": body.rol,
        "tipo": body.tipo,
        "prioridad": body.prioridad,
        "titulo": body.titulo,
        "descripcion": body.descripcion,
        "fecha_inicio": body.fecha_inicio,
        "fecha_vencimiento": body.fecha_vencimiento,
        "status": body.status,
        "created_at": now,
        "updated_at": now,
    }
    res = db.tareas.insert_one(doc)
    out = db.tareas.find_one({"_id": res.inserted_id})
    return _doc_to_out(out)

@router.get("")
def listar_tareas(
    gestor: Optional[str] = None,
    paciente_episodio: Optional[str] = None,
    status: Optional[str] = None,
    prioridad: Optional[str] = None,
    tipo: Optional[str] = None,
    limit: int = Query(50, ge=1, le=2000),
    skip: int = Query(0, ge=0),
    db=Depends(get_db),
):
    _ensure_indexes(db)
    q: Dict[str, Any] = {}
    if gestor: q["gestor"] = gestor
    if paciente_episodio: q["paciente_episodio"] = paciente_episodio
    if status: q["status"] = status
    if prioridad: q["prioridad"] = prioridad
    if tipo: q["tipo"] = tipo

    cur = db.tareas.find(q).sort([("updated_at", -1)]).skip(skip).limit(limit)
    return [_doc_to_out(x) for x in cur]

@router.put("/{tarea_id}")
def actualizar_tarea(tarea_id: str, body: TareaUpdate, db=Depends(get_db)):
    _ensure_indexes(db)
    set_fields: Dict[str, Any] = {}

    if body.gestor is not None:
        _validate_gestora_exists(db, body.gestor)
        set_fields["gestor"] = body.gestor
    if body.paciente_episodio is not None:
        _validate_paciente_exists(db, body.paciente_episodio)
        set_fields["paciente_episodio"] = body.paciente_episodio

    for k in ("rol","tipo","prioridad","titulo","descripcion","fecha_inicio","fecha_vencimiento","status"):
        v = getattr(body, k)
        if v is not None:
            set_fields[k] = v

    if "tipo" in set_fields and set_fields["tipo"] not in TIPOS:
        raise HTTPException(status_code=422, detail="tipo inválido")
    if "prioridad" in set_fields and set_fields["prioridad"] not in PRIORIDADES:
        raise HTTPException(status_code=422, detail="prioridad inválida")
    if "status" in set_fields and set_fields["status"] not in STATUSES:
        raise HTTPException(status_code=422, detail="status inválido")

    if not set_fields:
        raise HTTPException(status_code=422, detail="Sin cambios")

    set_fields["updated_at"] = datetime.utcnow()

    doc = db.tareas.find_one_and_update(
        {"_id": _oid(tarea_id)},
        {"$set": set_fields},
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return _doc_to_out(doc)

@router.delete("/{tarea_id}", status_code=204)
def borrar_tarea(tarea_id: str, db=Depends(get_db)):
    r = db.tareas.delete_one({"_id": _oid(tarea_id)})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return
