import re
import unicodedata
import pandas as pd
import numpy as np

LOW_RISK_THRESHOLD = 0.33
HIGH_RISK_THRESHOLD = 0.66
RISK_LABELS = ['Baja', 'Media', 'Alta']

def standardize_col(name: str) -> str:
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode("ascii")
    s = s.strip().lower()
    s = re.sub(r"[^\w\s]+", " ", s)
    s = re.sub(r"\s+", "_", s)
    return s

def read_excel_or_csv(path: str) -> pd.DataFrame:
    if path.lower().endswith(".csv"):
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path)
    df.columns = [standardize_col(c) for c in df.columns]
    return df

def coerce_dtypes(X: pd.DataFrame):
    # Separa num/cat y fuerza tipos consistentes
    num_cols = X.select_dtypes(include=["number","bool"]).columns.tolist()
    cat_cols = [c for c in X.columns if c not in num_cols]
    for c in num_cols:
        X[c] = pd.to_numeric(X[c], errors="coerce")
    for c in cat_cols:
        X[c] = X[c].astype(str)
    return X, num_cols, cat_cols

def find_first_existing(df: pd.DataFrame, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def categorize_probability(prob: float,
                           low: float = LOW_RISK_THRESHOLD,
                           high: float = HIGH_RISK_THRESHOLD) -> str:
    """Devuelve la categoría de riesgo Baja/Media/Alta para una probabilidad."""
    if prob is None:
        return 'Desconocido'
    try:
        if np.isnan(prob):
            return 'Desconocido'
    except TypeError:
        pass
    if prob < low:
        return 'Baja'
    if prob <= high:
        return 'Media'
    return 'Alta'


def categorize_probabilities(probabilities,
                             low: float = LOW_RISK_THRESHOLD,
                             high: float = HIGH_RISK_THRESHOLD):
    """Categorización vectorial de probabilidades."""
    bins = [0.0, low, high, 1.0]
    return pd.cut(probabilities, bins=bins, labels=RISK_LABELS, include_lowest=True)


def align_columns_to_template(df: pd.DataFrame, template_columns) -> pd.DataFrame:
    """
    Renombra columnas para que coincidan con las esperadas por el modelo.
    Permite mapear nombres sin guión bajo final a su versión con guión bajo (y viceversa).
    """
    template_set = set(template_columns)
    rename_map = {}
    for col in df.columns:
        if col in template_set:
            continue
        alt = f"{col}_"
        if alt in template_set:
            rename_map[col] = alt
            continue
        if col.endswith("_") and col[:-1] in template_set:
            rename_map[col] = col[:-1]
    if rename_map:
        df = df.rename(columns=rename_map)
    return df
