# 🏥 Flujo para Pacientes Nuevos - Sistema de Predicción

## 📋 **RESUMEN**
Sistema independiente que predice exceso de estadía para pacientes que acaban de llegar a la clínica, sin interferir con la carpeta `data` existente.

---

## 🚀 **FLUJO DE USO**

### **Paso 1: Preparar archivos**
Coloca tus archivos en la carpeta `nuevos_pacientes/`:
- **`GRD.xlsx`** - Datos clínicos (sin estancia real)
- **`Score.xlsx`** - Encuesta social

### **Paso 2: Ejecutar predicción**
```bash
# Activar entorno
source .venv/bin/activate

# Ejecutar predicción
python predict_nuevos_pacientes.py --predecir
```

### **Paso 3: Revisar resultados**
Los resultados se guardan en `nuevos_pacientes/predicciones.csv` con:
- **`id_episodio`** - ID del paciente
- **`probabilidad_exceso`** - Probabilidad de exceso (0-1)
- **`riesgo_categoria`** - Baja/Media/Alta

---

## 📊 **FORMATO DE ARCHIVOS**

### **GRD.xlsx** (datos clínicos)
```csv
Episodio CMBD, Edad en años, Sexo (Desc), Servicio Ingreso (Descripción), 
Diagnóstico Principal, Estancia Norma GRD, IR GRD, IR Tipo GRD, ...
```

### **Score.xlsx** (encuesta social)
```csv
episodio, total, habitacional, socioeconomica, salud_mental, redes, cuidador, ...
```

---

## 🎯 **INTERPRETACIÓN DE RESULTADOS**

### **Probabilidades:**
- **0.0 - 0.33**: Riesgo bajo (hasta 33%)
- **0.33 - 0.66**: Riesgo medio (33% a 66%)
- **0.66 - 1.0**: Riesgo alto (sobre 66%)

### **Ejemplo de salida:**
```csv
id_episodio,probabilidad_exceso,riesgo_categoria
1001,0.000,Baja
1002,0.000,Baja
1003,0.005,Baja
1004,0.016,Baja
1005,0.000,Baja
```

---

## 🧪 **PROBAR EL SISTEMA**

### **Crear archivos de ejemplo:**
```bash
python predict_nuevos_pacientes.py --ejemplo
```

### **Ejecutar con datos de ejemplo:**
```bash
python predict_nuevos_pacientes.py --predecir
```

---

## 📁 **ESTRUCTURA DE ARCHIVOS**

```
piloto_estancia_exceso/
├── nuevos_pacientes/          # Carpeta para pacientes nuevos
│   ├── GRD.xlsx              # Datos clínicos
│   ├── Score.xlsx            # Encuesta social
│   └── predicciones.csv      # Resultados
├── data/                     # Datos originales (no tocar)
├── models/                   # Modelos entrenados
└── predict_nuevos_pacientes.py  # Script principal
```

---

## ⚠️ **IMPORTANTE**

1. **NO modificar la carpeta `data/`** - Es para datos de entrenamiento
2. **Usar solo la carpeta `nuevos_pacientes/`** para pacientes nuevos
3. **Los archivos deben tener columnas de ID** para unir GRD y Score
4. **NO incluir datos de estancia real** - El sistema predice el futuro

---

## 🔧 **SOLUCIÓN DE PROBLEMAS**

### **Error: "No se encontró archivo"**
- Verifica que `GRD.xlsx` y `Score.xlsx` estén en `nuevos_pacientes/`
- Revisa que los nombres de archivo sean exactos

### **Error: "No se encontró ID de episodio"**
- Verifica que tus archivos tengan columnas de ID
- Nombres aceptados: "Episodio CMBD", "episodio", "ID", etc.

### **Error: "No se encontraron coincidencias"**
- Verifica que los IDs en GRD y Score coincidan
- Revisa que no haya espacios extra en los IDs

---

## 📞 **SOPORTE**

Si tienes problemas:
1. Usa `--ejemplo` para crear archivos de prueba
2. Verifica que los archivos estén en `nuevos_pacientes/`
3. Revisa que las columnas de ID coincidan entre archivos
4. Revisa los mensajes de error para identificar el problema específico

