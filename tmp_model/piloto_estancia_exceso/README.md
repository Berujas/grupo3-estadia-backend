# Piloto Rápido: Predicción de Exceso de Estancia vs Norma GRD

Este proyecto trae **todo lo necesario** para entrenar y probar localmente, en **VS Code**, un modelo que estime la **probabilidad de que un episodio supere la estancia normativa (GRD)**.

## 0) Requisitos
- **Python 3.10 o 3.11** instalado.
- **VS Code** + extensión *Python* (Microsoft).

## 1) Descarga y preparación
1. Descomprime esta carpeta en tu computador (por ejemplo `C:\proyectos\piloto_estancia_exceso`).
2. Copia tus dos Excel a la carpeta `data/` y nómbralos:
   - `GRD.xlsx`  (tu archivo de hospitalizaciones con columnas como `episodio_cmbd`, `estancia_del_episodio`, `estancia_norma_grd`, `fecha_ingreso_completa`, etc.)
   - `Score.xlsx` (tu archivo de encuesta social, con columna de episodio como `episodio` o `buscar_episodio_con_asignacion_encuesta`)
3. Si tus nombres de columnas difieren, **ajústalos** en `config.yaml` (ver sección siguiente).

## 2) Configurar columnas (si es necesario)
Abre `config.yaml` y revisa:
- Llaves de unión por *episodio*.
- Columnas de **norma** y **estancia real**.
- Columnas prohibidas (para evitar fuga de información).
- Lista de **features** conocidas al ingreso.

> Si tus exceles ya tienen los nombres sugeridos, no cambies nada.

## 3) Crear y activar entorno virtual
En la **raíz del proyecto** (la carpeta que contiene este README):

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**macOS / Linux (bash/zsh):**
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4) Abrir VS Code y elegir intérprete
- Abre la carpeta del proyecto en VS Code.
- `Ctrl+Shift+P` → **Python: Select Interpreter** → elige `.venv`.

## 5) Entrenar modelos (baseline y potente)
En la terminal de VS Code (con el venv activo):
```bash
python -m src.train --config config.yaml
```

Qué hace esto:
- Lee `data/GRD.xlsx` y `data/Score.xlsx`.
- Estandariza columnas, **une por episodio**, crea el **target** `excede_norma`.
- Split **temporal** (si existe `fecha_ingreso_completa`) o aleatorio estratificado.
- Entrena **Regresión Logística** (baseline) y **HistGradientBoosting** (modelo fuerte) con **calibración**.
- Genera **métricas** y **gráficos** en `reports/` y guarda artefactos en `models/`.

## 6) Resultados
- `reports/metrics.json`: ROC-AUC, PR-AUC (Average Precision), Brier score.
- `reports/roc.png`, `reports/pr.png`, `reports/calibration.png`
- `reports/deciles_lift.csv` (tasa de exceso por decil de riesgo).
- `models/model_baseline.joblib` y `models/model_hgb_calibrated.joblib`.
- `artifacts/X_test_preview.csv` (muestra del set de prueba con probabilidades).

## 7) Inferencia sobre nuevos ingresos
Coloca un CSV o XLSX con columnas esperadas en `data/nuevos.xlsx` (o `.csv`) y ejecuta:
```bash
python -m src.predict --config config.yaml --input data/nuevos.xlsx --output predicciones.csv
```
Obtendrás un archivo `predicciones.csv` con `p_excede_norma` por fila.

## 8) Opinión y buenas prácticas
- **Modelo recomendado**: `HistGradientBoosting` calibrado (cero dependencias raras y excelente desempeño en tabular clínico).
- **Siempre** separar por **fecha** para evitar fuga.
- Calibrar probabilidades (curvas de calibración y Brier).
- Elegir **umbrales** según capacidad operativa (por ejemplo, intervenir el **top 15%** de riesgo).
- Monitorear **drift** y recalibrar trimestralmente.

---

Cualquier duda, abre `src/` para ver el código: está comentado y listo para personalizar.
