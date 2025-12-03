from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from ..services.mongo import get_collection

router = APIRouter(prefix="/gestion", tags=["gestion"])

def _clean_nulls(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convierte strings vacíos en None (solo salida)."""
    for k, v in list(doc.items()):
        if isinstance(v, str) and v.strip() == "":
            doc[k] = None
    return doc

# ===========================================================
# /gestion/personas/resumen
#   - Usa SOLO la colección 'estadias'
#   - Por cada episodio, toma el último registro por marca_temporal
#   - Si fecha_alta != null -> ultima_cama = cama más cercana (<= fecha_alta)
#     sacada del propio historial de gestión; si no hay -> null.
#   - Si fecha_alta == null -> ultima_cama = null
# ===========================================================
@router.get("/personas/resumen")
async def personas_resumen(
    limit: int = Query(100, ge=1, le=10000),
    skip: int = Query(0, ge=0),
):
    coll = get_collection()  # 'estadias'

    pipe = [
        {"$match": {"episodio": {"$ne": None}, "marca_temporal": {"$ne": None}}},
        {"$sort": {"episodio": 1, "marca_temporal": 1}},
        {"$group": {
            "_id": "$episodio",
            # último registro por episodio
            "episodio": {"$last": "$episodio"},
            "marca_temporal": {"$last": "$marca_temporal"},

            # Identidad
            "run": {"$last": "$run"},
            "rut": {"$last": "$rut"},
            "nombre": {"$last": "$nombre"},
            "sexo": {"$last": "$sexo"},
            "fecha_de_nacimiento": {"$last": "$fecha_de_nacimiento"},

            # Cuentas
            "tipo_cuenta_1": {"$last": "$tipo_cuenta_1"},
            "tipo_cuenta_2": {"$last": "$tipo_cuenta_2"},
            "tipo_cuenta_3": {"$last": "$tipo_cuenta_3"},

            # Fechas clave
            "fecha_admision": {"$last": "$fecha_admision"},
            "fecha_alta": {"$last": "$fecha_alta"},

            # Otros solicitados
            "convenio": {"$last": "$convenio"},
            "nombre_de_la_aseguradora": {"$last": "$nombre_de_la_aseguradora"},
            "valor_parcial": {"$last": "$valor_parcial"},
            "dias_hospitalizacion": {"$last": "$dias_hospitalizacion"},

            # Historial para derivar ultima_cama desde gestión
            "camas_hist": {"$push": {"mt": "$marca_temporal", "cama": "$cama"}}
        }},
        # Deriva ultima_cama desde historial si hay fecha_alta
        {"$addFields": {
            "ultima_cama": {
                "$cond": [
                    {"$ifNull": ["$fecha_alta", False]},
                    {
                        "$let": {
                            "vars": { "fa": {"$concat": ["$fecha_alta","T23:59:59"]}, "hist": "$camas_hist" },
                            "in": {
                                "$let": {
                                    "vars": {
                                        "cand": {
                                            "$filter": {
                                                "input": "$$hist",
                                                "as": "h",
                                                "cond": { "$and": [
                                                    {"$ne": ["$$h.cama", None]},
                                                    {"$lte": ["$$h.mt", "$$fa"]}
                                                ]}
                                            }
                                        }
                                    },
                                    "in": {
                                        "$cond": [
                                            {"$gt":[{"$size":"$$cand"},0]},
                                            {"$arrayElemAt":["$$cand.cama", {"$subtract":[{"$size":"$$cand"},1]}]},
                                            None
                                        ]
                                    }
                                }
                            }
                        }
                    },
                    None
                ]
            }
        }},
        {"$project": {
            "_id": 0,
            "episodio": 1,
            "nombre": 1,
            "sexo": 1,
            # rut preferente: 'run' si está, si no 'rut'
            "rut": {"$ifNull": ["$run", "$rut"]},
            "fecha_de_nacimiento": 1,
            "tipo_cuenta_1": 1,
            "tipo_cuenta_2": 1,
            "tipo_cuenta_3": 1,
            "fecha_admision": 1,
            "fecha_alta": { "$cond": [ { "$ifNull": ["$fecha_alta", False] }, "$fecha_alta", None ] },
            "convenio": 1,
            "nombre_de_la_aseguradora": 1,
            "valor_parcial": 1,
            "dias_hospitalizacion": 1,
            "ultima_cama": 1
        }},
        {"$sort": {"episodio": 1}},
        {"$skip": skip},
        {"$limit": limit}
    ]

    rows: List[Dict[str, Any]] = await coll.aggregate(pipe).to_list(length=limit)
    rows = [_clean_nulls(r) for r in rows]
    return {"count": len(rows), "results": rows}

# ===========================================================
# /gestion/episodios/resumen
#   - Devuelve, por episodio, TODOS los registros relacionados
#     (ordenados del más antiguo al más nuevo) con los campos
#     solicitados para CADA registro del episodio.
#   - Si se pasa ?episodio=..., devuelve solo ese grupo.
# ===========================================================
@router.get("/episodios/resumen")
async def episodios_resumen(
    episodio: Optional[str] = Query(default=None, description="Filtrar por un episodio en particular"),
    limit: int = Query(50, ge=1, le=1000),
    skip: int = Query(0, ge=0),
):
    coll = get_collection()  # 'estadias'

    match_stage = {"$match": {"episodio": {"$ne": None}}}
    if episodio:
        match_stage = {"$match": {"episodio": episodio}}

    pipe = [
        match_stage,
        {"$sort": {"episodio": 1, "marca_temporal": 1}},
        {"$group": {
            "_id": "$episodio",
            "episodio": {"$first": "$episodio"},
            "registros": {"$push": {
                # ORDENADOS por marca_temporal ASC
                "marca_temporal": "$marca_temporal",
                "marco_temporal": "$marco_temporal",  # si venía así en el CSV original
                "que_gestion_se_solicito": "$que_gestion_se_solicito",
                "ultima_modificacion": "$ultima_modificacion",
                "fecha_inicio": "$fecha_inicio",
                "hora_inicio": "$hora_inicio",
                "mes": "$mes",
                "ano": "$ano",
                "cama": "$cama",
                "texto_libre_diagnostico_admision": "$texto_libre_diagnostico_admision",
                "diagnostico_transfer": "$diagnostico_transfer",
                "concretado": "$concretado",
                "solicitud_de_traslado": "$solicitud_de_traslado",
                "status": "$status",
                "causa_devolucion_rechazo": "$causa_devolucion_rechazo",
                "estado": "$estado",
                "motivo_de_cancelacion": "$motivo_de_cancelacion",
                "motivo_de_rechazo": "$motivo_de_rechazo",
                "tipo_de_traslado": "$tipo_de_traslado",
                "centro_de_destinatario": "$centro_de_destinatario",
                "nivel_de_atencion": "$nivel_de_atencion",
                "servicio_especialidad": "$servicio_especialidad",
                "fecha_de_finalizacion": "$fecha_de_finalizacion",
                "hora_de_finalizacion": "$hora_de_finalizacion",
                "dias_solicitados_homecare": "$dias_solicitados_homecare",
                "texto_libre_causa_rechazo": "$texto_libre_causa_rechazo"
            }}
        }},
        {"$project": {"_id": 0, "episodio": 1, "registros": 1}},
        {"$sort": {"episodio": 1}},
    ]

    if not episodio:
        pipe += [{"$skip": skip}, {"$limit": limit}]

    groups: List[Dict[str, Any]] = await coll.aggregate(pipe).to_list(length=None if episodio else limit)

    # Limpieza: strings vacías -> null
    for g in groups:
        g["registros"] = [_clean_nulls(x) for x in g.get("registros", [])]

    return {"count": len(groups), "results": groups}
