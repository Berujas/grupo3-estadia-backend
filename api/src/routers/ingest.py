import io, re, unicodedata, hashlib, json
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException
from pymongo.errors import BulkWriteError
from ..services.mongo import get_collection

router = APIRouter(prefix="/gestion/ingest", tags=["gestion"])

def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii")
    s = re.sub(r"[^0-9a-zA-Z]+", "_", s.lower()).strip("_")
    s = re.sub(r"_+", "_", s)
    return s

SYNONYMS = {
    # Identificadores
    "episodio": ["episodio","id_episodio","n_episodio","numero_episodio","episode","case_id","folio","n_folio"],
    "run": ["run","rut","id_paciente","identificacion","nro_run","numero_run","r_u_n"],
    # Demografía y clínica
    "edad": ["edad","anos","años"],
    "tipo_ingreso": ["tipo_ingreso","motivo_ingreso","via_ingreso"],
    "ir_gravedad": ["ir_gravedad","indice_riesgo","gravedad","irs"],
    "estancia_norma_grd": ["estancia_norma_grd","gmlos","estancia_norma","estancia_esperada","norma_grd"],
    "horas_estancia": ["horas_estancia","horas_totales","hrs_estancia"],
    # Fechas relevantes
    "fecha_ingreso": ["fecha_ingreso","f_ingreso","fecha_de_ingreso"],
    "fecha_alta": ["fecha_alta","f_alta","fecha_de_alta","fecha_egreso"],
    "marca_temporal": ["marca_temporal","marco_temporal","timestamp","fecha_hora_respuesta"],
    "ultima_modificacion": ["ultima_modificacion","última_modificacion","ultima_modification","ultima_actualizacion","ultima_act","last_update","ultima_modif"],
    # Otras
    "servicio": ["servicio","unidad","servicio_clinico"],
    "diagnostico": ["diagnostico","diagnostico_principal","dx_principal"]
}

def _detect_mapping(cols_slug: set):
    mapping = {}
    for std, variants in SYNONYMS.items():
        for v in variants:
            if v in cols_slug:
                mapping[std] = v
                break
    return mapping

def _excel_serial_to_iso(x, with_time=False):
    try:
        val = float(str(x).replace(",", "."))
    except:
        return None
    base = pd.Timestamp("1899-12-30")
    dt = base + pd.to_timedelta(val, unit="D")
    if pd.isna(dt):
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%S") if with_time else dt.strftime("%Y-%m-%d")

def _to_int(x):
    if x is None or x == "": return None
    try: return int(re.sub(r"[^0-9\-]", "", str(x)))
    except: return None

def _to_float(x):
    if x is None or x == "": return None
    try: return float(str(x).replace(",", "."))
    except: return None

def _to_date(x, keep_time=False):
    if x is None or x == "": return None
    # Excel serial primero
    iso = _excel_serial_to_iso(x, with_time=keep_time)
    if iso: return iso
    # Parseo flexible
    dt = pd.to_datetime(x, errors="coerce", dayfirst=True)
    if pd.isna(dt): return None
    return dt.strftime("%Y-%m-%dT%H:%M:%S") if keep_time else dt.strftime("%Y-%m-%d")

def _row_fingerprint(doc: dict) -> str:
    """
    Huella estable de la fila completa (sin _id).
    - Convierte None -> "" para estabilidad.
    - Ordena claves.
    - Serializa y hashea SHA1.
    """
    d = {k: ("" if v is None else v) for k, v in doc.items() if k != "_id"}
    payload = json.dumps(d, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()

@router.post("/csv")
async def ingest_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="El archivo debe ser .csv")

    raw = await file.read()

    # Leer como TEXTO sin NaN ni casts automáticos
    df = None
    for enc in ("utf-8-sig","latin-1"):
        try:
            df = pd.read_csv(
                io.BytesIO(raw),
                sep=None, engine="python", encoding=enc,
                dtype=str, keep_default_na=False, na_values=[]
            )
            break
        except Exception:
            df = None
    if df is None:
        raise HTTPException(status_code=400, detail="No fue posible leer el CSV (encoding/sep).")

    # Normaliza encabezados
    cols_slug = [_slug(c) for c in df.columns]
    df.columns = cols_slug
    mapping = _detect_mapping(set(cols_slug))

    # Debe haber al menos algún identificador razonable
    if not ("episodio" in mapping or "run" in mapping or "marca_temporal" in mapping or "fecha_ingreso" in mapping):
        raise HTTPException(status_code=400, detail="No se encontraron columnas identificadoras (episodio / RUN / marca_temporal / fecha_ingreso).")

    used_cols = set()  # NO excluimos nada: guardamos todo sin prefijo

    docs = []
    for _, row in df.iterrows():
        doc = {}

        # Campos "estándar" si existen (y convertimos tipos)
        if "episodio" in mapping:
            epi = row.get(mapping["episodio"], "")
            doc["episodio"] = (str(epi).strip() or None)

        if "run" in mapping:
            run = row.get(mapping["run"], "")
            doc["run"] = str(run).strip().upper() or None
        if "edad" in mapping:
            doc["edad"] = _to_int(row.get(mapping["edad"], ""))
        if "tipo_ingreso" in mapping:
            doc["tipo_ingreso"] = row.get(mapping["tipo_ingreso"], "") or None
        if "ir_gravedad" in mapping:
            doc["ir_gravedad"] = _to_int(row.get(mapping["ir_gravedad"], ""))
        if "estancia_norma_grd" in mapping:
            doc["estancia_norma_grd"] = _to_float(row.get(mapping["estancia_norma_grd"], ""))
        if "horas_estancia" in mapping:
            doc["horas_estancia"] = _to_int(row.get(mapping["horas_estancia"], ""))
        if "fecha_ingreso" in mapping:
            doc["fecha_ingreso"] = _to_date(row.get(mapping["fecha_ingreso"], ""), keep_time=False)
        if "fecha_alta" in mapping:
            doc["fecha_alta"] = _to_date(row.get(mapping["fecha_alta"], ""), keep_time=False)
        if "marca_temporal" in mapping:
            doc["marca_temporal"] = _to_date(row.get(mapping["marca_temporal"], ""), keep_time=True)
        if "ultima_modificacion" in mapping:
            doc["ultima_modificacion"] = _to_date(row.get(mapping["ultima_modificacion"], ""), keep_time=True)
        if "servicio" in mapping:
            doc["servicio"] = row.get(mapping["servicio"], "") or None
        if "diagnostico" in mapping:
            doc["diagnostico"] = row.get(mapping["diagnostico"], "") or None

        # Agrega TODAS las columnas originales normalizadas (sin prefijo),
        # respetando conversiones básicas de fechas cuando se parecen a serlo
        for c in cols_slug:
            # si ya lo setearon arriba, lo dejamos como está
            if c in doc:
                continue
            val = row.get(c, "")
            # intento simple de detectar fechas (si parece número excel o yyyy-mm-dd o dd/mm/yyyy)
            maybe_date = False
            if re.fullmatch(r"\d{5}(\.\d+)?", str(val).strip()):
                maybe_date = True  # serial excel típico
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?", str(val).strip()):
                maybe_date = True
            if re.fullmatch(r"\d{2}/\d{2}/\d{4}(\s+\d{2}:\d{2}(:\d{2})?)?", str(val).strip()):
                maybe_date = True

            if maybe_date:
                converted = _to_date(val, keep_time=True)
                doc[c] = converted if converted is not None else (val if val != "" else None)
            else:
                doc[c] = (val if val != "" else None)

        doc["_tipo_fuente"] = "respuestas_formulario"

        # Siempre calculamos una huella completa por si hay que usarla como clave
        doc["row_fingerprint"] = _row_fingerprint(doc)

        docs.append(doc)

    if not docs:
        raise HTTPException(status_code=400, detail="El CSV no contenía filas válidas.")

    coll = get_collection()

    # --- Índices: eliminamos antiguos y creamos el nuevo según disponibilidad ---
    unique_keys = None
    try:
        # eliminar si existieran (ignoramos errores)
        for idx in ("ux_episodio","ux_run_fechaing","ux_run_ts","ux_ts","ux_epi_ts","ux_epi_fing","ux_epi_ultmod","ux_rowfp"):
            try:
                await coll.drop_index(idx)
            except Exception:
                pass

        if ("episodio" in mapping) and ("marca_temporal" in mapping):
            await coll.create_index([("episodio",1),("marca_temporal",1)], unique=True, name="ux_epi_ts")
            unique_keys = ("episodio","marca_temporal")
        elif ("episodio" in mapping) and ("fecha_ingreso" in mapping):
            await coll.create_index([("episodio",1),("fecha_ingreso",1)], unique=True, name="ux_epi_fing")
            unique_keys = ("episodio","fecha_ingreso")
        elif ("episodio" in mapping) and ("ultima_modificacion" in mapping):
            await coll.create_index([("episodio",1),("ultima_modificacion",1)], unique=True, name="ux_epi_ultmod")
            unique_keys = ("episodio","ultima_modificacion")
        else:
            await coll.create_index([("row_fingerprint",1)], unique=True, name="ux_rowfp")
            unique_keys = ("row_fingerprint",)
    except Exception:
        unique_keys = unique_keys or None

    # Inserción (dejamos que el índice haga la deduplicación)
    inserted, duplicates = 0, 0
    try:
        res = await coll.insert_many(docs, ordered=False)
        inserted = len(res.inserted_ids)
    except BulkWriteError as bwe:
        duplicates = sum(1 for err in bwe.details.get("writeErrors", []) if err.get("code")==11000)
        inserted = bwe.details.get("nInserted", 0)

    return {"collection": coll.name, "inserted": inserted, "duplicates": duplicates,
            "total": len(docs), "unique_key_used": unique_keys}
