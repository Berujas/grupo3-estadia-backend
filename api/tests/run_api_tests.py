#!/usr/bin/env python3
import os, io, csv, json, time, random
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, List, Optional
import requests

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")

# ---------- utils ----------
def log_line(name: str, ok: bool, detail: str = "", status: Optional[int] = None):
    mark = "✅" if ok else "❌"
    s = f"{mark} {name}"
    if status is not None: s += f" [HTTP {status}]"
    if detail: s += f" — {detail}"
    print(s)

def _as_json(r: requests.Response) -> Tuple[bool, Any, str]:
    try: return True, r.json(), ""
    except Exception as e: return False, None, f"no es JSON válido: {e}"

def _within(v, lo, hi) -> bool:
    try:
        x = float(v)
        return lo <= x <= hi
    except Exception:
        return False

def _episode_auto(suffix: str = "") -> str:
    base = f"EP-AUTO-{int(time.time())}-{random.randint(1000,9999)}"
    return f"{base}{('-'+suffix) if suffix else ''}"

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _get_one_episodio(sess: requests.Session) -> Optional[str]:
    """Intenta obtener un episodio existente para pruebas de /gestion/episodios/resumen?episodio=..."""
    r = sess.get(f"{BASE_URL}/gestion/episodios/resumen?limit=1", timeout=20)
    if r.status_code != 200: return None
    ok, data, _ = _as_json(r)
    if not ok: return None
    results = data.get("results") or []
    if not results: return None
    return results[0].get("episodio")

# ========== SUITES (3 tests por endpoint, excepto ingest CSV) ==========

# /health (GET) — 3 variantes
def suite_health(sess):
    tests = []

    def t1():
        r = sess.get(f"{BASE_URL}/health", timeout=10, headers={"Accept":"application/json"})
        if r.status_code != 200: return False, "status != 200", r.status_code
        ok, data, msg = _as_json(r); 
        return ((ok and data.get("status")=="ok"), "status debe ser 'ok'", r.status_code)

    def t2():
        r = sess.get(f"{BASE_URL}/health?ts={int(time.time())}", timeout=10, headers={"Accept":"*/*"})
        if r.status_code != 200: return False, "status != 200", r.status_code
        ok, data, msg = _as_json(r); 
        return ((ok and "status" in data), "respuesta JSON esperada", r.status_code)

    def t3():
        r = sess.get(f"{BASE_URL}/health", timeout=10)  # simple
        if r.status_code != 200: return False, "status != 200", r.status_code
        ok, data, msg = _as_json(r); 
        return (ok, "JSON válido", r.status_code)

    tests.extend([("GET /health #1", t1), ("GET /health #2", t2), ("GET /health #3", t3)])
    return tests

# /gestion/personas/resumen (GET) — 3 variantes
def suite_personas_resumen(sess):
    tests = []
    def t1():
        r = sess.get(f"{BASE_URL}/gestion/personas/resumen?limit=3&skip=0", timeout=20)
        if r.status_code != 200: return False, "status != 200", r.status_code
        ok, data, msg = _as_json(r)
        return (ok and "count" in data and "results" in data, "estructura mínima", r.status_code)
    def t2():
        r = sess.get(f"{BASE_URL}/gestion/personas/resumen?limit=10&skip=5", timeout=20)
        if r.status_code != 200: return False, "status != 200", r.status_code
        ok, data, msg = _as_json(r)
        if not ok: return False, msg, r.status_code
        cnt = data.get("count", 0)
        return (cnt <= 10, "count <= limit", r.status_code)
    def t3():
        r = sess.get(f"{BASE_URL}/gestion/personas/resumen?limit=100&skip=0", timeout=20)
        if r.status_code != 200: return False, "status != 200", r.status_code
        ok, data, msg = _as_json(r)
        return (ok and isinstance(data.get("results", []), list), "results es lista", r.status_code)
    tests.extend([
        ("GET /gestion/personas/resumen #1", t1),
        ("GET /gestion/personas/resumen #2", t2),
        ("GET /gestion/personas/resumen #3", t3),
    ])
    return tests

# /gestion/episodios/resumen (GET) — 3 variantes
def suite_episodios_resumen(sess):
    tests = []
    epi = _get_one_episodio(sess)

    def t1():
        r = sess.get(f"{BASE_URL}/gestion/episodios/resumen?limit=1", timeout=20)
        if r.status_code != 200: return False, "status != 200", r.status_code
        ok, data, msg = _as_json(r)
        return (ok and "results" in data, "estructura mínima", r.status_code)

    def t2():
        # si no logramos encontrar episodio, igual probamos sin filtro (pasa si responde 200)
        url = f"{BASE_URL}/gestion/episodios/resumen?episodio={epi}" if epi else f"{BASE_URL}/gestion/episodios/resumen?limit=2"
        r = sess.get(url, timeout=20)
        if r.status_code != 200: return False, "status != 200", r.status_code
        ok, data, msg = _as_json(r)
        if not ok: return False, msg, r.status_code
        return (("results" in data), "estructura válida", r.status_code)

    def t3():
        r = sess.get(f"{BASE_URL}/gestion/episodios/resumen?limit=2&skip=1", timeout=20)
        if r.status_code != 200: return False, "status != 200", r.status_code
        ok, data, _ = _as_json(r)
        return (ok and "count" in data, "incluye count", r.status_code)

    tests.extend([
        ("GET /gestion/episodios/resumen #1", t1),
        ("GET /gestion/episodios/resumen #2", t2),
        ("GET /gestion/episodios/resumen #3", t3),
    ])
    return tests

# /prediccion/nuevos-pacientes (POST persist=false) — 3 payloads
def suite_prediccion(sess):
    tests = []
    def check_pred(r):
        if r.status_code != 200: return False, "status != 200", r.status_code
        ok, data, msg = _as_json(r)
        if not ok: return False, msg, r.status_code
        try:
            item = data["items"][0]
            ok_prob = _within(item["probabilidad_sobre_estadia"], 0.0, 1.0)
            ok_cat = isinstance(item["riesgo_categoria"], str)
            return (ok_prob and ok_cat, "probabilidad [0,1] y categoría", r.status_code)
        except Exception as e:
            return False, f"estructura inesperada: {e}", r.status_code

    def t1():
        payload = {
            "rut":"API-T1","edad":60,"sexo":"Femenino","servicio_clinico":"Medicina",
            "prevision":"FONASA","fecha_estimada_de_alta":7,
            "riesgo_social":"Medio","riesgo_clinico":"Medio","riesgo_administrativo":"Bajo",
            "codigo_grd":51401
        }
        r = sess.post(f"{BASE_URL}/prediccion/nuevos-pacientes?persist=false", json=payload, timeout=30)
        return check_pred(r)

    def t2():
        payload = {
            "rut":"API-T2","edad":78,"sexo":"Masculino","servicio_clinico":"UCI",
            "prevision":"FONASA","fecha_estimada_de_alta":2,
            "riesgo_social":"Alto","riesgo_clinico":"Alto","riesgo_administrativo":"Medio",
            "codigo_grd":81605
        }
        r = sess.post(f"{BASE_URL}/prediccion/nuevos-pacientes?persist=false", json=payload, timeout=30)
        return check_pred(r)

    def t3():
        payload = {
            "rut":"API-T3","edad":40,"sexo":"Femenino","servicio_clinico":"Cirugia",
            "prevision":"ISAPRE","fecha_estimada_de_alta":12,
            "riesgo_social":0,"riesgo_clinico":1,"riesgo_administrativo":2,
            "codigo_grd":174121
        }
        r = sess.post(f"{BASE_URL}/prediccion/nuevos-pacientes?persist=false", json=payload, timeout=30)
        return check_pred(r)

    tests.extend([
        ("POST /prediccion/nuevos-pacientes #1", t1),
        ("POST /prediccion/nuevos-pacientes #2", t2),
        ("POST /prediccion/nuevos-pacientes #3", t3),
    ])
    return tests

# /gestion/estadias (CRUD) — 3 rondas con datos distintos
def suite_estadias_crud(sess):
    tests = []

    def round_trip(suffix: str, extra: Dict[str,Any]):
        episodio = _episode_auto(suffix)
        marca = _iso_now()
        # CREATE
        payload = {"episodio": episodio, "marca_temporal": marca} | extra
        r_c = sess.post(f"{BASE_URL}/gestion/estadias", json=payload, timeout=20)
        if r_c.status_code != 201: return False, f"CREATE {r_c.text}", r_c.status_code
        ok, data_c, msg = _as_json(r_c)
        if not ok: return False, f"CREATE {msg}", r_c.status_code
        _id = data_c.get("inserted_id")
        if not _id: return False, "CREATE sin inserted_id", r_c.status_code
        # UPDATE
        r_u = sess.put(f"{BASE_URL}/gestion/estadias/{episodio}/{_id}", json={"estado":"ok-"+suffix}, timeout=20)
        if r_u.status_code != 200: return False, f"UPDATE {r_u.text}", r_u.status_code
        ok, data_u, msg = _as_json(r_u)
        if not ok: return False, f"UPDATE {msg}", r_u.status_code
        if data_u.get("estado") != "ok-"+suffix: return False, "UPDATE no reflejó cambio", r_u.status_code
        # CAMA ACTUAL (tolerante: 200 o 404)
        r_b = sess.get(f"{BASE_URL}/gestion/episodios/{episodio}/cama-actual", timeout=10)
        if r_b.status_code not in (200,404): return False, f"CAMA-ACTUAL {r_b.status_code}", r_b.status_code
        # DELETE
        r_d = sess.delete(f"{BASE_URL}/gestion/estadias/{episodio}/{_id}", timeout=20)
        if r_d.status_code != 204: return False, f"DELETE {r_d.text}", r_d.status_code
        return True, "CRUD ok", 200

    def t1():
        extra = {
            "riesgo_social": None, "riesgo_clinico": None, "riesgo_administrativo": None,
            "prob_sobre_estadia": None, "grd_code": None
        }
        return round_trip("R1", extra)

    def t2():
        extra = {
            "riesgo_social": 1, "riesgo_clinico": "Medio", "riesgo_administrativo": "Bajo",
            "prob_sobre_estadia": 0.25, "grd_code": 51401
        }
        return round_trip("R2", extra)

    def t3():
        extra = {
            "riesgo_social": "Alto", "riesgo_clinico": 2, "riesgo_administrativo": 0,
            "prob_sobre_estadia": 0.83, "grd_code": 81605
        }
        return round_trip("R3", extra)

    tests.extend([
        ("CRUD /gestion/estadias #1", t1),
        ("CRUD /gestion/estadias #2", t2),
        ("CRUD /gestion/estadias #3", t3),
    ])
    return tests

# /tareas/gestoras (GET) — 3 llamadas
def suite_tareas_gestoras(sess):
    tests = []
    def t1():
        r = sess.get(f"{BASE_URL}/tareas/gestoras", timeout=20)
        return (r.status_code == 200, "200 esperado", r.status_code)
    def t2():
        r = sess.get(f"{BASE_URL}/tareas/gestoras?ts="+str(int(time.time())), timeout=20)
        return (r.status_code == 200, "200 esperado", r.status_code)
    def t3():
        r = sess.get(f"{BASE_URL}/tareas/gestoras", timeout=20, headers={"Accept":"application/json"})
        return (r.status_code == 200, "200 esperado", r.status_code)
    tests.extend([
        ("GET /tareas/gestoras #1", t1),
        ("GET /tareas/gestoras #2", t2),
        ("GET /tareas/gestoras #3", t3),
    ])
    return tests

# /tareas (GET) — 3 variantes
def suite_tareas(sess):
    tests = []
    def t1():
        r = sess.get(f"{BASE_URL}/tareas", timeout=20)
        return (r.status_code == 200, "200 esperado", r.status_code)
    def t2():
        r = sess.get(f"{BASE_URL}/tareas?gestor=Pedro+Del+R%C3%ADo", timeout=20)
        return (r.status_code == 200, "200 (con filtro gestor)", r.status_code)
    def t3():
        r = sess.get(f"{BASE_URL}/tareas?gestor=NoExisteXYZ", timeout=20)
        return (r.status_code == 200, "200 (gestor inexistente tolerado)", r.status_code)
    tests.extend([
        ("GET /tareas #1", t1),
        ("GET /tareas #2", t2),
        ("GET /tareas #3", t3),
    ])
    return tests

# /gestion/ingest/csv (POST) — 1 prueba (NO se multiplica)
def single_ingest_csv(sess):
    tests = []
    def t1():
        ep = _episode_auto("CSV")
        mt = _iso_now()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Episodio", "Marco Temporal", "cama"])
        writer.writerow([ep, mt, "C-TEST"])
        output.seek(0)
        files = {"file": ("mini.csv", output.getvalue(), "text/csv")}
        r = sess.post(f"{BASE_URL}/gestion/ingest/csv", files=files, timeout=60)
        if r.status_code != 200: return False, f"status != 200: {r.text}", r.status_code
        ok, data, msg = _as_json(r)
        if not ok: return False, msg, r.status_code
        inserted = int(data.get("inserted", 0))
        total = int(data.get("total", 0))
        return (inserted >= 0 and total == 1, f"inserted={inserted}, total={total}", r.status_code)
    tests.append(("POST /gestion/ingest/csv #1", t1))
    return tests

# ------------------ RUNNER ------------------
SUITES = [
    ("health", suite_health),
    ("personas_resumen", suite_personas_resumen),
    ("episodios_resumen", suite_episodios_resumen),
    ("prediccion", suite_prediccion),
    ("estadias_crud", suite_estadias_crud),
    ("tareas_gestoras", suite_tareas_gestoras),
    ("tareas", suite_tareas),
    ("ingest_csv_single", single_ingest_csv),  # no se multiplica
]

def main():
    print(f"🔎 Probando API en: {BASE_URL}")
    overall_results: List[Dict[str, Any]] = []
    total_tests = passed_tests = 0
    per_suite_summary = []

    with requests.Session() as sess:
        for suite_name, factory in SUITES:
            tests = factory(sess)
            suite_passed = 0
            print(f"\n— Suite: {suite_name} —")
            for name, fn in tests:
                try:
                    ok, detail, status = fn()
                except Exception as e:
                    ok, detail, status = False, f"excepción: {e}", -1
                log_line(name, ok, detail, status if status!=-1 else None)
                overall_results.append({"suite": suite_name, "name": name, "ok": ok, "detail": detail, "status": status})
                total_tests += 1
                if ok: 
                    passed_tests += 1
                    suite_passed += 1
            per_suite_summary.append({
                "suite": suite_name,
                "tests": len(tests),
                "passed": suite_passed,
                "failed": len(tests) - suite_passed,
                "success_pct": round(100.0 * suite_passed / len(tests), 2)
            })

    success_pct = round(100.0 * passed_tests / total_tests, 2) if total_tests else 0.0
    summary = {
        "total_tests": total_tests,
        "passed": passed_tests,
        "failed": total_tests - passed_tests,
        "success_pct": success_pct,
        "timestamp": _iso_now(),
        "base_url": BASE_URL,
        "per_suite": per_suite_summary,
        "results": overall_results,
    }

    print("\n📊 RESUMEN")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if passed_tests != total_tests:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
