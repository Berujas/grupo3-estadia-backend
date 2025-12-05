# 🏥 Sistema de Predicción de Exceso de Estadía - Guía de Uso

## 📋 **RESUMEN**
El sistema recibe un **solo CSV simplificado** con información básica del paciente y devuelve la probabilidad de que exceda la estadía normativa más una etiqueta de riesgo (Baja, Media, Alta).

---

## 🚀 **CÓMO USAR EL SISTEMA**

### **Paso 1: Preparar tu CSV**
El archivo puede tener una o varias filas. Cada fila **debe** incluir las siguientes columnas (mínimas para el modelo):

| Columna obligatoria | Descripción |
| --- | --- |
| `edad` | Edad en años |
| `sexo` | Hombre/Mujer o M/F (se toleran variantes) |
| `servicio_clinico` | Servicio de hospitalización |
| `prevision` | Fonasa, Isapre, etc. |
| `fecha_estimada_de_alta` | Días permitidos de estadía (misma lógica que la estancia norma GRD) |
| `riesgo_social` | Escala 0/1/2 o texto Bajo/Medio/Alto |
| `riesgo_clinico` | Escala 0/1/2 o texto Bajo/Medio/Alto |
| `riesgo_administrativo` | Escala 0/1/2 o texto Bajo/Medio/Alto |
| `codigo_grd` | Código GRD numérico |

Además puedes incluir columnas identitarias (`rut`, `nombre`, `apellido_paterno`, `apellido_materno`) u otras que quieras mantener en el resultado; el script las copiará sin modificaciones.

### **Paso 2A: Ejecutar la predicción**

```bash
python3 predict_nuevos_pacientes.py \
  --input nuevos_pacientes/pacientes.csv \
  --output output/predicciones.csv
```

### **Paso 2B: Usar el modelo desde tu backend (JSON)**

```python
from predict_nuevos_pacientes import predict_nuevos_pacientes

payload = [{
    "rut": "API-001",
    "nombre": "Paciente",
    "apellido_paterno": "Web",
    "apellido_materno": "Demo",
    "edad": 60,
    "sexo": "Femenino",
    "servicio_clinico": "Medicina",
    "prevision": "FONASA",
    "fecha_estimada_de_alta": 7,
    "riesgo_social": "Medio",
    "riesgo_clinico": "Medio",
    "riesgo_administrativo": "Bajo",
    "codigo_grd": 51401,
}]

predicciones = predict_nuevos_pacientes(
    records=payload,
    persist=False,
    return_json=True,
)
```

### **Paso 3: Revisar resultados**
El CSV de salida contiene las mismas columnas de entrada más:
- `probabilidad_sobre_estadia`
- `riesgo_categoria`
- Guardado por defecto en la carpeta `output/`. Si el archivo ya existe, las nuevas filas se **agregan** al final (no se sobrescriben).
- Tras procesar el archivo, el CSV de entrada se elimina automáticamente para evitar acumulación (los registros ya quedaron guardados en `output/`).
- En modo API (`records=`) puedes establecer `persist=False` para no escribir en disco y `return_json=True` para obtener directamente una lista de dicts lista para responder en tu endpoint.

---

## 📊 **EJEMPLO RÁPIDO**

```bash
python3 predict_nuevos_pacientes.py --ejemplo
python3 predict_nuevos_pacientes.py --input nuevos_pacientes/pacientes.csv --output output/predicciones.csv
```

El primer comando genera un CSV de ejemplo (tres pacientes) listo para ser usado en el segundo comando.

---

## 🎯 **INTERPRETACIÓN DE RESULTADOS**

- **Probabilidad < 0.33** → Riesgo **Bajo**
- **0.33 – 0.66** → Riesgo **Medio**
- **> 0.66** → Riesgo **Alto**

Recomendaciones sugeridas:
- **Alto**: intervención inmediata, trabajo social prioritario.
- **Medio**: monitoreo intensivo / seguimiento diario.
- **Bajo**: seguimiento normal.

---

## 🔧 **COLUMNAS MÍNIMAS REQUERIDAS**

- `edad`
- `sexo`
- `servicio_clinico`
- `prevision`
- `fecha_estimada_de_alta`
- `riesgo_social`
- `riesgo_clinico`
- `riesgo_administrativo`
- `codigo_grd`

Las columnas identitarias (`rut`, `nombre`, etc.) son opcionales y se mantienen tal como llegan para facilitar la trazabilidad.

---

## ⚠️ **IMPORTANTE**

1. Si una columna tiene texto en vez de números (ej.: “Alto”), el sistema lo convierte automáticamente.
2. La columna `fecha_estimada_de_alta` debe indicar el número de días permitidos; si se entrega una fecha, se intenta convertir, pero es preferible usar días.
3. Se utiliza el modelo calibrado `models/model_hgb_calibrated.joblib`. Si no existe, se usa el modelo baseline.
4. Asegúrate de tener los modelos entrenados antes de predecir (ejecuta `python -m src.train` si es necesario).

---

## 📁 **ARCHIVOS DEL SISTEMA**

- `predict_nuevos_pacientes.py` – Script principal para leer el CSV simplificado y generar predicciones.
- `models/` – Carpeta con los modelos entrenados (`model_hgb_calibrated.joblib`, `model_baseline.joblib`).
- `config.yaml` – Configuración usada durante el entrenamiento.

---

## 🆘 **SOLUCIÓN DE PROBLEMAS**

### **“Faltan columnas necesarias en el CSV”**
Asegúrate de que el archivo tenga todos los campos indicados en la tabla de columnas mínimas (los nombres se estandarizan automáticamente: sin acentos, minúsculas y con guiones bajos).

### **“El archivo de entrada no contiene pacientes”**
El CSV está vacío. Agrega al menos una fila.

### **“No se puede cargar el modelo”**
Revisa que existan `model_hgb_calibrated.joblib` o `model_baseline.joblib` dentro de `models/`. Si no, vuelve a entrenar.

---

## 📞 **SOPORTE**

- Verifica primero que los nombres de las columnas estén correctos.
- Usa `python3 predict_nuevos_pacientes.py --ejemplo` para validar que el flujo funciona en tu entorno.
- Si el error persiste, revisa el mensaje completo que imprime el script o recompártelo para identificar el problema específico.
