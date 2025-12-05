import argparse, os, yaml
import pandas as pd
from joblib import load
from .utils import read_excel_or_csv, coerce_dtypes

def main(args):
    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    model_dir = config["paths"]["model_dir"]
    # Por defecto usamos el modelo calibrado
    model_path = os.path.join(model_dir, "model_hgb_calibrated.joblib")
    if not os.path.exists(model_path):
        model_path = os.path.join(model_dir, "model_baseline.joblib")
    pipe = load(model_path)

    df_new = read_excel_or_csv(args.input)
    # Coerción de tipos (pipeline es robusto, pero ayudamos)
    df_new, _, _ = coerce_dtypes(df_new)

    # El pipeline maneja missing y OHE. Solo aseguramos mismas columnas cuando sea posible.
    # Si faltan columnas, el OneHot de sklearn las ignora; si sobran, serán ignoradas.
    proba = pipe.predict_proba(df_new)[:,1]
    out = df_new.copy()
    out["p_excede_norma"] = proba
    out.to_csv(args.output, index=False)
    print(f"Predicciones guardadas en {args.output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="config.yaml")
    parser.add_argument("--input", type=str, required=True, help="Ruta a archivo nuevos (CSV/XLSX)")
    parser.add_argument("--output", type=str, default="predicciones.csv")
    args = parser.parse_args()
    main(args)
