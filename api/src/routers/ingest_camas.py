# /opt/app/repo/api/src/routers/ingest_camas.py
import io, re, unicodedata, os
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException
from pymongo.errors import BulkWriteError
from ..services.mongo import get_named_collection

router = APIRouter(prefix="/camas/ingest", tags=["camas"])
COLL_CAMAS = os.getenv("MONGODB_COLLECTION_CAMAS", "camas")

def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii")
    s = re.sub(r"[^0-9a-zA-Z]+", "_", s.lower()).strip("_")
    s = re.sub(r"_+", "_", s)
    return s

SYN = {
    "unidad": ["unidad","servicio","establecimiento","area","pabellon","unidad_clinica"],
    "sala": ["sala","sector","modulo","habitacion"],
    "cama": ["cama","bed","nro_cama","numero_cama","id_cama"],
    "estado": ["estado","status","ocupacion","disponibilidad","condicion"],
    "paciente": ["paciente","nombre_paciente","paciente_nombre"],
    "run": ["run","rut","id_paciente","identificacion"],
    "diagnostico": ["diagnostico","dx_principal","diagnostico_principal"],
    "fecha": ["fecha","fecha_registro","fecha_corte","fecha_medicion","marca_temporal","timestamp","fecha_carga"],
    "hora": ["hora","hora_registro","hora_medicion"],
    "fecha_hora": ["fecha_hora","fechahora","datetime","fecha_y_hora","marca_temporal"]
}

def _read_csv_raw(raw: bytes) -> pd.DataFrame:
    for enc in ("utf-8-sig","latin-1"):
        try:
            return pd.read_csv(
                io.BytesIO(raw),
                sep=None, engine="python", encoding=enc,
                dtype=str, keep_default_na=False, na_values=[]
            )
        except Exception:
            continue
    raise HTTPException(status_code=400, detail="No fue posible leer el CSV (encoding/sep).")

def _map_cols(cols_slug: set):
    m = {}
    for std, variants in SYN.items():
        for v in variants:
            if v in cols_slug:
                m[std] = v
                break
    return m

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

def _parse_snapshot_from_name(filename: str):
    if not filename:
        return None
    name = filename.replace("%20"," ")
    m = re.search(r'(\d{2})[-_/](\d{2})[-_/](\d{4}).*?(\d{2})(\d{2})', name)
    if m:
        dd, mm, yyyy, hh, mi = m.groups()
        return f"{yyyy}-{mm}-{dd}T{hh}:{mi}:00"
    m = re.search(r'(\d{2})[-_/](\d{2})[-_/](\d{4})', name)
    if m:
        dd, mm, yyyy = m.groups()
        return f"{yyyy}-{mm}-{dd}T00:00:00"
    return None

@router.post("/csv")
async def ingest_camas(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="El archivo debe ser .csv")
    raw = await file.read()
    df = _read_csv_raw(raw)

    cols_slug = [_slug(c) for c in df.columns]
    df.columns = cols_slug
    mapping = _map_cols(set(cols_slug))

    if "cama" not in mapping:
        raise HTTPException(status_code=400, detail="No se encontró la columna 'cama' en el CSV.")

    # Construir snapshot_at (fecha/hora)
    snapshot_name = _parse_snapshot_from_name(file.filename)
    if "fecha_hora" in mapping:
        col = mapping["fecha_hora"]
        # intenta serial excel primero
        ser = df[col].apply(lambda x: _excel_serial_to_iso(x, with_time=True) or x)
        ser = pd.to_datetime(ser, errors="coerce", dayfirst=True)
        df["snapshot_at"] = ser.dt.strftime("%Y-%m-%dT%H:%M:%S")
    else:
        fcol = mapping.get("fecha")
        hcol = mapping.get("hora")
        if fcol and hcol:
            f = df[fcol].apply(lambda x: _excel_serial_to_iso(x, with_time=False) or x)
            f = pd.to_datetime(f, errors="coerce", dayfirst=True).dt.strftime("%Y-%m-%d")
            h = df[hcol].astype(str).str.replace(r"[^0-9:]", "", regex=True)
            h = h.str.replace(r"^(\d{2})(\d{2})$", r"\1:\2", regex=True)  # 1305 -> 13:05
            df["snapshot_at"] = (f.fillna("") + "T" + h.fillna("") + ":00").str.replace("T:00","T00:00:00")
        elif fcol:
            f = df[fcol].apply(lambda x: _excel_serial_to_iso(x, with_time=False) or x)
            f = pd.to_datetime(f, errors="coerce", dayfirst=True).dt.strftime("%Y-%m-%d")
            df["snapshot_at"] = f.fillna("") + "T00:00:00"
        else:
            df["snapshot_at"] = snapshot_name or ""

    used = set(mapping.values()) | {"snapshot_at"}

    docs = []
    for _, row in df.iterrows():
        doc = {}
        if "unidad" in mapping:      doc["unidad"] = row.get(mapping["unidad"], "") or None
        if "sala" in mapping:        doc["sala"] = row.get(mapping["sala"], "") or None
        if "cama" in mapping:        doc["cama"] = (row.get(mapping["cama"], "") or "").strip().upper() or None
        if "estado" in mapping:      doc["estado"] = row.get(mapping["estado"], "") or None
        if "paciente" in mapping:    doc["paciente"] = row.get(mapping["paciente"], "") or None
        if "run" in mapping:         doc["run"] = (row.get(mapping["run"], "") or "").strip().upper() or None
        if "diagnostico" in mapping: doc["diagnostico"] = row.get(mapping["diagnostico"], "") or None

        # snapshot_at (general o por fila)
        val_snap = row.get("snapshot_at") or snapshot_name
        # intenta normalizar si parece serial Excel
        doc["snapshot_at"] = _excel_serial_to_iso(val_snap, with_time=True) or \
                             (pd.to_datetime(val_snap, errors="coerce", dayfirst=True).strftime("%Y-%m-%dT%H:%M:%S")
                              if val_snap not in ("", None) and pd.to_datetime(val_snap, errors="coerce", dayfirst=True) is not pd.NaT else None)

        # Agregar TODAS las demás columnas sin prefijo (normalizadas)
        for c in cols_slug:
            if c in used: 
                continue
            val = row.get(c, "")
            doc[c] = val if val != "" else None

        doc["_tipo_fuente"] = "censo_camas"
        docs.append(doc)

    if not docs:
        raise HTTPException(status_code=400, detail="CSV vacío.")

    coll = get_named_collection(COLL_CAMAS)

    # Índices únicos
    unique_used = None
    try:
        if all(k in docs[0] for k in ("unidad","sala","cama","snapshot_at")):
            await coll.create_index([("unidad",1),("sala",1),("cama",1),("snapshot_at",1)], unique=True, name="ux_unidad_sala_cama_snap")
            unique_used = ("unidad","sala","cama","snapshot_at")
        elif all(k in docs[0] for k in ("unidad","cama","snapshot_at")):
            await coll.create_index([("unidad",1),("cama",1),("snapshot_at",1)], unique=True, name="ux_unidad_cama_snap")
            unique_used = ("unidad","cama","snapshot_at")
        elif all(k in docs[0] for k in ("cama","snapshot_at")):
            await coll.create_index([("cama",1),("snapshot_at",1)], unique=True, name="ux_cama_snap")
            unique_used = ("cama","snapshot_at")
    except Exception:
        pass

    inserted, duplicates = 0, 0
    try:
        res = await coll.insert_many(docs, ordered=False)
        inserted = len(res.inserted_ids)
    except BulkWriteError as bwe:
        duplicates = sum(1 for e in bwe.details.get("writeErrors", []) if e.get("code")==11000)
        inserted = bwe.details.get("nInserted", 0)

    return {"collection": coll.name, "inserted": inserted, "duplicates": duplicates,
            "total": len(docs), "unique_key_used": unique_used}
