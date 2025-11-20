Backend UC Christus — Ingesta & API (FastAPI + MongoDB)

## 🚀 Stack
- API: FastAPI (Python 3.11) en Docker
- DB: MongoDB en Docker (contenedor mongo)
- Infra: AWS EC2 (puerto 80 abierto en el Security Group)
- Red Docker: appnet
- Healthcheck: GET /health

---

## 🗃️ Base de datos (MongoDB)
Base: ucchristus
Colecciones:
- estadias — ingesta CSV de Gestión
- camas — ingesta CSV de Camas

Índices:
- estadias: índice único ("episodio", "marca_temporal")
- camas: recomendado ("episodio", 1), ("snapshot_at", 1) (no-único)

### Normalización (Gestión)
- Encabezados slugificados (minúsculas, sin tildes, espacios → _)
- Sinónimos a canónicos: Marco Temporal → marca_temporal; Rut → run (también se guarda rut)
- Fechas a ISO (se interpretan seriales de Excel)
- Numéricos: dias_hospitalizacion, dias_reales, dias_solicitados_homecare → enteros
- Columnas no mapeadas se conservan (normalizadas)

### Identidad sintética (si faltan datos)
- Si faltan run/rut, nombre, fecha_de_nacimiento o sexo para un episodio, se genera identidad sintética determinística (semilla por episodio).
- RUT válido con dígito verificador.
- Marcado con _synthetic_identity: true.
- Si el CSV trae datos reales, no se alteran.

---

## 🔌 Endpoints (8 principales)

1) POST /gestion/ingest/csv — Ingesta Gestión → estadias
- Clave única: ("episodio","marca_temporal")
- Respuesta:
  ```bash
  { "collection": "estadias", "inserted": N, "duplicates": D, "total": T, "unique_key_used": ["episodio","marca_temporal"] }
- Ejemplos (macOS):
  ```bash
  # Nombre con espacios/acentos
  curl -fSs -X POST http://<IP>/gestion/ingest/csv \
    -F "file=@'$HOME/Downloads/Gestion Estadía(Respuestas Formulario).csv';type=text/csv"
  
  # O renombrando
  cp "$HOME/Downloads/Gestion Estadía(Respuestas Formulario).csv" "$HOME/Downloads/gestion.csv"
  curl -fSs -X POST http://<IP>/gestion/ingest/csv \
    -F "file=@$HOME/Downloads/gestion.csv;type=text/csv"

2) POST /camas/ingest/csv — Ingesta Camas → camas
- Encabezados normalizados (sin raw_*)
- Campos comunes: unidad, sala, cama, estado, paciente, run/rut, diagnostico, episodio, snapshot_at, etc.
- Ejemplo:
  ```bash
  curl -fSs -X POST http://<IP>/camas/ingest/csv \
    -F "file=@$HOME/Downloads/camas.csv;type=text/csv"

3) GET /gestion/personas/resumen — Resumen por episodio (solo estadias)
- Devuelve por episodio (último registro por marca_temporal): episodio, nombre, sexo, rut/run, fecha_de_nacimiento, tipo_cuenta_1..3, fecha_admision, fecha_alta|null, convenio, nombre_de_la_aseguradora, valor_parcial, dias_hospitalizacion, ultima_cama (si hay fecha_alta → cama con marca_temporal ≤ fecha_alta 23:59:59 más cercana; si no hay o no aplica, null).
- Params: limit (default 100, máx 2000), skip.
- Ejemplo:
  ```bash
  curl -sS "http://<IP>/gestion/personas/resumen?limit=5&skip=0" | jq .

4) GET /gestion/episodios/resumen — Todos los registros por episodio
- Por episodio, retorna todos los registros en orden ascendente por marca_temporal, con:
  que_gestion_se_solicito, marca_temporal (y marco_temporal si existe), ultima_modificacion, fecha_inicio, hora_inicio, mes, ano, cama, texto_libre_diagnostico_admision, diagnostico_transfer, concretado, solicitud_de_traslado, status, causa_devolucion_rechazo, estado, motivo_de_cancelacion, motivo_de_rechazo, tipo_de_traslado, centro_de_destinatario, nivel_de_atencion, servicio_especialidad, fecha_de_finalizacion, hora_de_finalizacion, dias_solicitados_homecare, texto_libre_causa_rechazo.
- Params: episodio (opcional), limit, skip.
- Ejemplos:
  ```bash
  # Un episodio
  curl -sS "http://<IP>/gestion/episodios/resumen?episodio=1011454142" | jq .
  
  # Paginado
  curl -sS "http://<IP>/gestion/episodios/resumen?limit=3&skip=0" | jq .

5) GET /gestion/episodios/{episodio}/cama-actual
   
- Devuelve la cama **más reciente** asociada al episodio, tomando prioridad por `snapshot_at` y luego `marca_temporal`.  
No requiere que el episodio esté activo: por defecto **incluye dados de alta**.
- Respuesta (ejemplo)
```json
{
  "episodio": "1020137038",
  "unidad": "UE-PED",
  "sala": "204",
  "cama": "204-1",
  "estado": "3",
  "paciente": null,
  "timestamp": "2025-01-01T00:00:00"
}
```
- Ejemplos:
```bash
curl -sS "http://<IP>/gestion/episodios/1020137038/cama-actual"
curl -sS "http://<IP>/gestion/episodios/1020137038/cama-actual?include_discharged=false"
```
6) POST /gestion/estadias
Crea una nueva estadia en la colección estadias.
- Requeridos: episodio (string), marca_temporal (ISO string).
- Reglas:
  - Rechaza duplicados por clave (episodio, marca_temporal) con 409.
	- Todos los campos conocidos (los observados en los datos de ejemplo) se aceptan; si faltan, se guardan como null.
  - Campos no mapeados: se preservan tal cual llegaron.
- Ejemplo minimo:
```bash
curl -sS -X POST http://<IP>/gestion/estadias \
  -H "Content-Type: application/json" \
  -d '{
    "episodio": "1013",
    "marca_temporal": "2025-11-19T00:00:00",
    "nombre": "Ejemplo Prueba",
    "tipo_cuenta_1": "Episodios GES"
  }'
```
- Ejemplo con todos los parametros ingresables:
```bash
curl -sS -X POST http://<IP>/gestion/estadias \
  -H "Content-Type: application/json" \
  -d '{
    "episodio": "1013578840",
    "marca_temporal": "2023-03-23T00:00:00",
    "status": null,
    "causa_devolucion_rechazo": null,
    "ultima_modificacion": "2023-03-23T00:00:00",
    "que_gestion_se_solicito": "Traslado",
    "fecha_inicio": null,
    "hora_inicio": null,
    "informe": null,
    "tipo_cuenta_1": "Episodios GES",
    "tipo_cuenta_2": null,
    "tipo_cuenta_3": null,
    "nombre": "Valentina Martinez",
    "fecha_admision": "2023-01-16",
    "mes": "enero",
    "ano": "2023",
    "fecha_alta": "2023-03-23",
    "cama": "CH5B03P5",
    "texto_libre_diagnostico_admision": "POLITRAUMA + TEC + DELIRIUM",
    "diagnostico_transfer": null,
    "convenio": "PUC - COLMENA GES HOSPITAL",
    "nombre_de_la_aseguradora": "COLMENA GOLDEN CROSS S.A.",
    "valor_parcial": " $53.052.920 ",
    "solicitud_de_traslado": null,
    "concretado": "SI",
    "dias_hospitalizacion": 66,
    "dias_reales": null,
    "mes2": "3",
    "ano2": "2023",
    "fecha_de_nacimiento": "1992-11-20",
    "sexo": "Femenino",
    "estado": null,
    "motivo_de_cancelacion": null,
    "motivo_de_rechazo": null,
    "tipo_de_solicitud": null,
    "tipo_de_traslado": null,
    "motivo_de_traslado": null,
    "centro_de_destinatario": null,
    "nivel_de_atencion": null,
    "servicio_especialidad": null,
    "fecha_de_finalizacion": null,
    "hora_de_finalizacion": null,
    "dias_solicitados_homecare": null,
    "texto_libre_causa_rechazo": null,
    "run": "17085132-3",
    "rut": "17085132-3",
    "_synthetic_identity": true,
    "_tipo_fuente": "respuestas_formulario"
  }'
```
- Respuesta: {"inserted_id":"<mongo_id>"} ó 409 si duplicado.

7) PUT /gestion/estadias/{episodio}/{registroId}
   
Actualiza solo campos permitidos de una estadia de un episodio.
- registroId puede ser ObjectId del documento o la marca_temporal.
- Ejemplos:
```bash
# Por marca_temporal:
curl -sS -X PUT "http://<IP>/gestion/estadias/1013/2025-11-19T00%3A00%3A00" \
  -H "Content-Type: application/json" \
  -d '{"tipo_cuenta_2":"Cuenta 2 de prueba","dias_hospitalizacion":10}'

# Por _id (primero obtén el _id desde Mongo y reemplázalo):
curl -sS -X PUT "http://<IP>/gestion/estadias/1013/<_id_mongo>" \
  -H "Content-Type: application/json" \
  -d '{"estado":"En curso"}'
```
- Respuestas: documento actualizado o 404 si no existe.

8) DELETE /gestion/estadias/{episodio}/{registroId}
   
Elimina una línea concreta del historial de estadias.
- registroId puede ser ObjectId o marca_temporal.
- Ejemplo:
```bash
# Por marca_temporal (ojo con los dos puntos):
curl -i -X DELETE "http://<IP>/gestion/estadias/1013/2025-11-19T00%3A00%3A00"

# Por _id:
curl -i -X DELETE "http://<IP>/gestion/estadias/1013/<_id_mongo>"
```
- Respuestas: 204 No Content si se borró, 404 si no existe.

---

## 🩺 Health & Docs
- Health: curl -s http://<IP>/health
- Swagger: http://<IP>/docs
- Redoc: http://<IP>/redoc

---

## ▶️ Despliegue (Docker)
API
  ```bash
  cd /opt/app/repo/api
  sudo docker build -t hello-api:latest .
  sudo docker stop api || true
  sudo docker rm api || true
  sudo docker run -d --name api \
    --network appnet \
    -p 80:8000 \
    --env-file ../.env \
    --restart unless-stopped \
    hello-api:latest
  ```

MongoDB (si no está corriendo)
  ```bash
  sudo docker run -d --name mongo \
    --network appnet \
    -p 27017:27017 \
    -e MONGO_INITDB_ROOT_USERNAME=app \
    -e MONGO_INITDB_ROOT_PASSWORD=app \
    mongo:6
  ```

## 🧪 Verificación rápida (Mongo)
```bash
##Entrar a mongosh dentro del contenedor:
  sudo docker exec -it mongo mongosh -u app -p app --authenticationDatabase admin
##Dentro de mongosh:
  use ucchristus
  show collections
  db.estadias.countDocuments({})
  db.camas.countDocuments({})
  db.estadias.find({episodio:"<EP>"},{_id:0}).sort({marca_temporal:1}).limit(3).pretty()
##(Cuidado) borrar y reingestar:
  db.estadias.deleteMany({})
```

## 🛡️ Consideraciones
- No commitear .env ni credenciales.
- Security Group con HTTP 80 abierto para quienes consuman la API.
- Ingesta acepta CSV (no .numbers).

## 📌 Reglas de negocio
- Unicidad en estadias: ("episodio","marca_temporal").
- Identidad sintética si faltan datos de persona (_synthetic_identity: true).
- ultima_cama en /gestion/personas/resumen:
  - null si fecha_alta es null;
  - si fecha_alta existe: cama con marca_temporal ≤ fecha_alta 23:59:59 más cercana (historial de gestión).
- Se guardan todas las columnas del CSV (normalizadas) + alias rut = run si venía Rut.

## 👥 Colaboración
- SSH o VS Code Remote SSH (con tu .pem).

