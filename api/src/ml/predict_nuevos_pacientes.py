#!/usr/bin/env python3
"""
Predicción de exceso de estadía a partir de un CSV simplificado.

Cada fila debe contener las columnas de FEATURE_COLUMNS. El script agrega
`probabilidad_sobre_estadia` y `riesgo_categoria`, guarda/concatena en `output/`
y elimina el CSV de entrada tras procesarlo.
"""
from pathlib import Path
MODELS_DIR = Path(__file__).resolve().parent / "models"
import os
import sys
from typing import Dict

import numpy as np
import pandas as pd
from joblib import load

sys.path.append('src')

from .utils import (  # noqa: E402
    categorize_probabilities,
    standardize_col,
)

DEFAULT_INPUT = os.path.join("nuevos_pacientes", "pacientes.csv")
OUTPUT_DIR = "output"
DEFAULT_OUTPUT = os.path.join(OUTPUT_DIR, "predicciones.csv")

FEATURE_COLUMNS = [
    "edad",
    "sexo",
    "servicio_clinico",
    "prevision",
    "fecha_estimada_de_alta",
    "riesgo_social",
    "riesgo_clinico",
    "riesgo_administrativo",
    "codigo_grd",
]


def predict_nuevos_pacientes(
    input_path: str | None = DEFAULT_INPUT,
    output_path: str = DEFAULT_OUTPUT,
    records: list[dict] | None = None,
    persist: bool = True,
    return_json: bool = False,
):
    """Genera predicciones desde un CSV o desde una lista de dicts (para integración web).

    Args:
        input_path: Ruta al CSV (modo batch).
        output_path: Ruta donde se guarda/apende el CSV de resultados.
        records: Lista de dicts (modo API). Si se usa, `input_path` se ignora.
        persist: Si es False, no se escribe en disco y solo se devuelve el DataFrame.
        return_json: Si es True, la función devuelve una lista de dicts lista para JSON.
    """
    if persist:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if records is not None:
        original_df = pd.DataFrame(records)
        source_path = None
    else:
        if not input_path or not os.path.exists(input_path):
            print(f"❌ No se encontró el archivo de entrada: {input_path}")
            return None
        try:
            original_df = pd.read_csv(input_path)
        except Exception as exc:  # pragma: no cover - lectura de archivo
            print(f"❌ Error al leer {input_path}: {exc}")
            return None
        source_path = input_path

    if original_df.empty:
        print("⚠️ El archivo de entrada no contiene pacientes.")
        return None

    print(f"📥 Pacientes recibidos: {len(original_df)}")
    standardized_df = original_df.copy()
    standardized_df.columns = [standardize_col(col) for col in standardized_df.columns]
    missing = [col for col in FEATURE_COLUMNS if col not in standardized_df.columns]
    if missing:
        print(f"❌ Faltan columnas necesarias en el CSV: {missing}")
        return None

    print("🔧 Preparando columnas para el modelo...")
    features_df = build_feature_frame(standardized_df)

    candidates = [
   	MODELS_DIR / "model_hgb_calibrated.joblib",
   	MODELS_DIR / "model_baseline.joblib",
    	MODELS_DIR / "model_logistic_only.joblib",
    ]

    model_path = next((str(p) for p in candidates if p.exists()), None)
    if not model_path:
        raise FileNotFoundError(f"No se encontraron modelos en {MODELS_DIR}")

    print(f"📦 Cargando modelo: {model_path}")
    model = load(model_path)

    print("🔮 Calculando probabilidades...")
    raw_probabilities = model.predict_proba(features_df)[:, 1]
    probabilities = apply_risk_boost(raw_probabilities, features_df)
    risk_labels = categorize_probabilities(probabilities)

    result_df = original_df.copy()
    result_df["probabilidad_sobre_estadia"] = probabilities
    result_df["riesgo_categoria"] = risk_labels
    appended_count = 0
    if persist:
        appended_count = save_predictions(result_df, output_path)
        print(f"✅ Predicciones generadas ({len(result_df)} pacientes).")
        if appended_count:
            print(f"   ➕ Se agregaron {len(result_df)} filas a las {appended_count} ya existentes.")
        print(f"💾 Archivo guardado en: {output_path}")
    else:
        print(f"✅ Predicciones generadas ({len(result_df)} pacientes). (Modo sin persistencia)")

    print(f"   Probabilidad promedio: {probabilities.mean():.3f}")
    print(f"   Probabilidad máxima:   {probabilities.max():.3f}")
    print(f"   Probabilidad mínima:   {probabilities.min():.3f}")
    if source_path and records is None:
        cleanup_input(source_path)

    if return_json:
        return result_df.to_dict(orient="records")
    return result_df


def build_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve un DataFrame solo con las columnas necesarias para el modelo."""
    out = pd.DataFrame(index=df.index)
    out["edad"] = pd.to_numeric(df["edad"], errors="coerce")
    out["sexo"] = df["sexo"].fillna("Desconocido").astype(str).apply(normalize_sex)
    out["servicio_clinico"] = df["servicio_clinico"].fillna("Desconocido").astype(str)
    out["prevision"] = df["prevision"].fillna("Desconocido").astype(str)
    out["fecha_estimada_de_alta"] = df["fecha_estimada_de_alta"].apply(parse_estancia_norma)
    out["codigo_grd"] = pd.to_numeric(df["codigo_grd"], errors="coerce")
    out["riesgo_social"] = encode_risk_series(df["riesgo_social"]).clip(0, 2)
    out["riesgo_clinico"] = encode_risk_series(df["riesgo_clinico"]).clip(0, 2)
    out["riesgo_administrativo"] = encode_risk_series(df["riesgo_administrativo"]).clip(0, 2)
    return out[FEATURE_COLUMNS].copy()


def normalize_sex(value) -> str:
    """Homologa valores de sexo al formato esperado por el modelo."""
    if pd.isna(value):
        return "Desconocido"
    text = str(value).strip().lower()
    if text in {"m", "masculino", "h", "hombre"}:
        return "Hombre"
    if text in {"f", "femenino", "mujer"}:
        return "Mujer"
    return str(value)


def parse_estancia_norma(value):
    """Convierte la 'fecha estimada de alta' en días de estancia normativa."""
    if pd.isna(value):
        return np.nan
    number = pd.to_numeric(value, errors="coerce")
    if not pd.isna(number):
        return float(number)
    try:
        return pd.to_datetime(value, errors="coerce").day
    except Exception:
        return np.nan


def encode_risk_series(series: pd.Series) -> pd.Series:
    """Convierte las etiquetas de riesgo en valores numéricos 0/1/2."""
    if series is None:
        return pd.Series(dtype=float)
    return series.apply(encode_single_risk)


def encode_single_risk(value):
    if pd.isna(value):
        return np.nan
    numeric = pd.to_numeric(value, errors="coerce")
    if not pd.isna(numeric):
        return numeric
    text = str(value).strip().lower()
    mapping: Dict[str, float] = {
        "bajo": 0.0,
        "baja": 0.0,
        "medio": 1.0,
        "media": 1.0,
        "alto": 2.0,
        "alta": 2.0,
    }
    return mapping.get(text, np.nan)


def cleanup_input(input_path: str) -> None:
    """Elimina el CSV de entrada para evitar acumulación de archivos."""
    try:
        os.remove(input_path)
        print(f"🧹 Archivo procesado eliminado: {input_path}")
    except FileNotFoundError:
        pass
    except OSError as exc:
        print(f"⚠️ No se pudo eliminar {input_path}: {exc}")


def save_predictions(df: pd.DataFrame, output_path: str) -> int:
    """Guarda las predicciones, agregando filas si el archivo ya existe. Devuelve filas previas."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if os.path.exists(output_path):
        existing = pd.read_csv(output_path)
        prev_rows = len(existing)
        combined = pd.concat([existing, df], ignore_index=True, sort=False)
        combined.to_csv(output_path, index=False)
        return prev_rows
    df.to_csv(output_path, index=False)
    return 0


def apply_risk_boost(probabilities: np.ndarray, features: pd.DataFrame) -> np.ndarray:
    """Ajusta las probabilidades usando los riesgos y los días permitidos."""
    risk_sum = (
        features["riesgo_social"].fillna(1.0)
        + features["riesgo_clinico"].fillna(1.0)
        + features["riesgo_administrativo"].fillna(1.0)
    )
    risk_norm = risk_sum / 6.0  # 0 = bajo, 1 = alto

    dias = features["fecha_estimada_de_alta"].clip(lower=0).fillna(
        features["fecha_estimada_de_alta"].median()
    )
    dias_shift = np.clip((5.0 - dias) / 10.0, -0.5, 0.5)

    risk_shift = (risk_norm - 0.5) * 0.2  # -0.1 a +0.1
    dias_shift = dias_shift * 0.2         # -0.1 a +0.1

    servicio = features["servicio_clinico"].fillna("").str.lower()
    uci_boost = np.where(servicio.str.contains("uci"), 0.08, 0.0)
    prevision = features["prevision"].fillna("").str.lower()
    fonasa_boost = np.where(prevision.str.contains("fonasa"), 0.03, 0.0)
    age_boost = np.clip((features["edad"].fillna(features["edad"].median()) - 70) / 50.0, 0, 0.08)

    adjusted = probabilities + risk_shift + dias_shift + uci_boost + fonasa_boost + age_boost
    return np.clip(adjusted, 0.0, 1.0)


def crear_ejemplo():
    """Genera un CSV de ejemplo con el nuevo esquema simplificado."""
    carpeta = os.path.dirname(DEFAULT_INPUT)
    os.makedirs(carpeta, exist_ok=True)
    data = {
        "rut": ["12345678-9", "9876543-2", "5555555-5"],
        "nombre": ["Ana", "Luis", "Jose"],
        "apellido_paterno": ["Martinez", "Rojas", "Perez"],
        "apellido_materno": ["Perez", "Soto", "Diaz"],
        "edad": [70, 58, 82],
        "sexo": ["Femenino", "Masculino", "Masculino"],
        "servicio_clinico": ["Medicina", "Cirugia", "UCI"],
        "prevision": ["FONASA", "ISAPRE", "FONASA"],
        "fecha_estimada_de_alta": [5, 4, 12],
        "riesgo_social": ["Medio", "Alto", "Bajo"],
        "riesgo_clinico": ["Bajo", "Medio", "Alto"],
        "riesgo_administrativo": ["Bajo", "Medio", "Alto"],
        "codigo_grd": [51401, 81605, 174121],
    }
    df = pd.DataFrame(data)
    df.to_csv(DEFAULT_INPUT, index=False)
    print(f"✅ Ejemplo creado en {DEFAULT_INPUT} ({len(df)} pacientes).")
    print(df)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Predicción de exceso de estadía desde un CSV simplificado.")
    parser.add_argument("--input", type=str, default=DEFAULT_INPUT, help="Ruta al CSV de pacientes nuevos.")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT, help="Ruta para guardar las predicciones.")
    parser.add_argument("--ejemplo", action="store_true", help="Crear un CSV de ejemplo con el nuevo formato.")

    args = parser.parse_args()

    if args.ejemplo:
        crear_ejemplo()
    else:
        result = predict_nuevos_pacientes(args.input, args.output)
        if result is None:
            print("❌ La predicción no pudo completarse.")

