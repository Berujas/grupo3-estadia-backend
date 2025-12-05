import io, re, unicodedata, hashlib, random
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException
from pymongo.errors import BulkWriteError
from ..services.mongo import get_collection

router = APIRouter(prefix="/gestion/ingest", tags=["gestion"])

# ---------- utils ----------
def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii")
    s = re.sub(r"[^0-9a-zA-Z]+", "_", s.lower()).strip("_")
    s = re.sub(r"_+", "_", s)
    return s

def _excel_serial_to_iso(x, with_time=False):
    try:
        val = float(str(x).replace(",", "."))
    except:
        return None
    base = pd.Timestamp("1899-12-30")
    dt = base + pd.to_timedelta(val, unit="D")
    if pd.isna(dt): return None
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
    iso = _excel_serial_to_iso(x, with_time=keep_time)
    if iso: return iso
    dt = pd.to_datetime(x, errors="coerce", dayfirst=True)
    if pd.isna(dt): return None
    return dt.strftime("%Y-%m-%dT%H:%M:%S") if keep_time else dt.strftime("%Y-%m-%d")

# ---------- identidad sintética determinística por episodio ----------
_MALE_FIRST = ["Juan","Pedro","Luis","Carlos","Jose","Diego","Jorge","Miguel","Andres","Felipe","Rodrigo","Sebastian","Francisco","Tomas","Nicolas","Matias","Cristobal","Alvaro","Rafael","Hernan"]
_FEMALE_FIRST = ["Maria","Ana","Carmen","Patricia","Daniela","Catalina","Fernanda","Valentina","Camila","Sofia","Isidora","Francisca","Antonia","Paula","Javiera","Carolina","Andrea","Beatriz","Teresa","Marcela"]
_LASTNAMES = ["Gonzalez","Munoz","Rojas","Diaz","Perez","Soto","Contreras","Silva","Martinez","Sepulveda","Gomez","Vasquez","Castillo","Ramirez","Herrera","Gutierrez","Castro","Alvarez","Romero","Vargas"]

def _seed_from_episode(episodio: str) -> int:
    h = hashlib.sha1((episodio or "").encode("utf-8")).hexdigest()
    return int(h[:12], 16)

def _rut_dv(num: int) -> str:
    factors = [2,3,4,5,6,7]
    s, i = 0, 0
    for d in reversed(str(num)):
        s += int(d) * factors[i % len(factors)]
        i += 1
    dv = 11 - (s % 11)
    if dv == 11: return "0"
    if dv == 10: return "K"
    return str(dv)

def _gen_birthdate(rng: random.Random, edad: int|None, marca_iso: str|None) -> str:
    ref_year = 2010
    if marca_iso:
        try: ref_year = pd.to_datetime(marca_iso).year
        except: pass
    if edad is not None:
        y = max(1900, ref_year - max(0, edad))
    else:
        y = rng.randint(1935, 2015)
    m = rng.randint(1, 12)
    d = rng.randint(1, 28)
    return f"{y:04d}-{m:02d}-{d:02d}"

def _synthetic_identity_for_episode(episodio: str, edad: int|None, marca_iso: str|None):
    rng = random.Random(_seed_from_episode(episodio))
    is_male = rng.choice([True, False])
    if is_male:
        first = rng.choice(_MALE_FIRST); sexo = "Masculino"
    else:
        first = rng.choice(_FEMALE_FIRST); sexo = "Femenino"
    last = rng.choice(_LASTNAMES)
    nombre = f"{first} {last}"
    base = rng.randint(7000000, 27000000)
    dv = _rut_dv(base)
    run = f"{base}-{dv}"
    dob = _gen_birthdate(rng, edad, marca_iso)
    return {"run": run, "rut": run, "nombre": nombre, "fecha_de_nacimiento": dob, "sexo": sexo}

# ---------- mapeos de encabezados ----------
# Mapea EXACTAMENTE todas las columnas pedidas a nombres canónicos
CANON_MAP = {
    "marco_temporal": "marca_temporal",
    "status": "status",
    "causa_devolucion_rechazo": "causa_devolucion_rechazo",
    "ultima_modificacion": "ultima_modificacion",
    "episodio": "episodio",
    "que_gestion_se_solicito": "que_gestion_se_solicito",
    "fecha_inicio": "fecha_inicio",
    "hora_inicio": "hora_inicio",
    "informe": "informe",
    "tipo_cuenta_1": "tipo_cuenta_1",
    "tipo_cuenta_2": "tipo_cuenta_2",
    "tipo_cuenta_3": "tipo_cuenta_3",
    "nombre": "nombre",
    "rut": "run",
    "fecha_admision": "fecha_admision",
    "mes": "mes",
    "ano": "ano",
    "fecha_alta": "fecha_alta",
    "cama": "cama",
    "texto_libre_diagnostico_admision": "texto_libre_diagnostico_admision",
    "diagnostico_transfer": "diagnostico_transfer",
    "convenio": "convenio",
    "nombre_de_la_aseguradora": "nombre_de_la_aseguradora",
    "valor_parcial": "valor_parcial",
    "solicitud_de_traslado": "solicitud_de_traslado",
    "concretado": "concretado",
    "dias_hospitalizacion": "dias_hospitalizacion",
    "dias_reales": "dias_reales",
    "mes2": "mes2",
    "ano2": "ano2",
    "fecha_de_nacimiento": "fecha_de_nacimiento",
    "sexo": "sexo",
    "estado": "estado",
    "motivo_de_cancelacion": "motivo_de_cancelacion",
    "motivo_de_rechazo": "motivo_de_rechazo",
    "tipo_de_solicitud": "tipo_de_solicitud",
    "tipo_de_traslado": "tipo_de_traslado",
    "motivo_de_traslado": "motivo_de_traslado",
    "centro_de_destinatario": "centro_de_destinatario",
    "nivel_de_atencion": "nivel_de_atencion",
    "servicio_especialidad": "servicio_especialidad",
    "fecha_de_finalizacion": "fecha_de_finalizacion",
    "hora_de_finalizacion": "hora_de_finalizacion",
    "dias_solicitados_homecare": "dias_solicitados_homecare",
    "texto_libre_causa_rechazo": "texto_libre_causa_rechazo",
}

# Campos que convertimos a fecha (ISO). Con hora en los que pueden traer hora.
DATE_KEEP_TIME = {"marca_temporal","ultima_modificacion","fecha_inicio","fecha_de_finalizacion"}
DATE_ONLY      = {"fecha_admision","fecha_alta","fecha_de_nacimiento"}

@router.post("/csv")
async def ingest_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="El archivo debe ser .csv")

    raw = await file.read()

    # Lee TODO como texto (sin NaN) e intenta separador automático
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

    # Slug de encabezados
    cols_slug = [_slug(c) for c in df.columns]
    df.columns = cols_slug

    # Requeridos: episodio + marca_temporal (puede venir como "marco_temporal")
    has_epi = "episodio" in df.columns
    has_marca = ("marca_temporal" in df.columns) or ("marco_temporal" in df.columns)
    if not (has_epi and has_marca):
        raise HTTPException(status_code=400, detail="Se requieren columnas de 'Episodio' y 'Marco/Marca Temporal'.")

    docs = []
    for _, row in df.iterrows():
        doc = {}
        consumed = set()   # columnas del CSV ya mapeadas a nombres canónicos

        # Primero: mapea todos los encabezados conocidos a sus nombres canónicos
        for src_slug, dest in CANON_MAP.items():
            if src_slug not in df.columns:
                continue
            val = row.get(src_slug, "")
            # fechas
            if dest in DATE_KEEP_TIME:
                val = _to_date(val, keep_time=True)
            elif dest in DATE_ONLY:
                val = _to_date(val, keep_time=False)
            else:
                val = (val if val != "" else None)

            doc[dest] = val
            consumed.add(src_slug)

            # espejo rut si venía 'rut' en CSV
            if src_slug == "rut":
                doc["rut"] = doc.get("run")

        # Asegura claves requeridas
        episodio = doc.get("episodio") or (row.get("episodio","") or None)
        marca = doc.get("marca_temporal") or (row.get("marca_temporal","") or row.get("marco_temporal","") or None)
        doc["episodio"] = episodio
        doc["marca_temporal"] = _to_date(marca, keep_time=True)

        # Convierte tipos numéricos razonables
        for k in ("dias_hospitalizacion","dias_reales","dias_solicitados_homecare"):
            if k in doc:
                doc[k] = _to_int(doc[k])

        # Agrega columnas extra no mapeadas (con heurística de fecha)
        for c in cols_slug:
            if c in consumed:
                continue
            val = row.get(c, "")
            s = str(val).strip()
            looks_date = False
            if re.fullmatch(r"\d{5}(\.\d+)?", s): looks_date = True           # serial excel
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?", s): looks_date = True
            if re.fullmatch(r"\d{2}/\d{2}/\d{4}(\s+\d{2}:\d{2}(:\d{2})?)?", s): looks_date = True
            doc[c] = (_to_date(val, keep_time=True) if looks_date else (val if val != "" else None))

        # Identidad sintética si faltan campos clave
        epi = doc.get("episodio")
        if epi:
            need_run = doc.get("run") in (None, "")
            need_nom = doc.get("nombre") in (None, "")
            need_dob = doc.get("fecha_de_nacimiento") in (None, "")
            need_sex = doc.get("sexo") in (None, "")
            edad_val = _to_int(doc.get("edad")) if "edad" in doc else None
            if need_run or need_nom or need_dob or need_sex:
                syn = _synthetic_identity_for_episode(epi, edad_val, doc.get("marca_temporal"))
                if need_run: doc["run"] = syn["run"]; doc["rut"] = syn["rut"]
                if need_nom: doc["nombre"] = syn["nombre"]
                if need_dob: doc["fecha_de_nacimiento"] = syn["fecha_de_nacimiento"]
                if need_sex: doc["sexo"] = syn["sexo"]
                doc["_synthetic_identity"] = True

        # Marca de origen
        doc["_tipo_fuente"] = "respuestas_formulario"

        # --- Campos ML por defecto (si no vienen en el CSV) ---
        for k in ("riesgo_social","riesgo_clinico","riesgo_administrativo","prob_sobre_estadia","grd_code"):
            if k not in doc:
                doc[k] = None

        docs.append(doc)

    if not docs:
        raise HTTPException(status_code=400, detail="El CSV no contenía filas válidas.")

    coll = get_collection()

    # Índice único (episodio, marca_temporal)
    try:
        for idx in ("ux_episodio","ux_run_fechaing","ux_run_ts","ux_ts","ux_epi_fing","ux_epi_ultmod","ux_rowfp","ux_epi_ts"):
            try:
                await coll.drop_index(idx)
            except Exception:
                pass
        await coll.create_index([("episodio",1),("marca_temporal",1)], unique=True, name="ux_epi_ts")
    except Exception:
        pass

    inserted, duplicates = 0, 0
    try:
        res = await coll.insert_many(docs, ordered=False)
        inserted = len(res.inserted_ids)
    except BulkWriteError as bwe:
        duplicates = sum(1 for err in bwe.details.get("writeErrors", []) if err.get("code")==11000)
        inserted = bwe.details.get("nInserted", 0)

    return {
        "collection": coll.name,
        "inserted": inserted,
        "duplicates": duplicates,
        "total": len(docs),
        "unique_key_used": ["episodio","marca_temporal"]
    }
