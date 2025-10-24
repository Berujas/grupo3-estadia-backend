import re
import unicodedata
import pandas as pd

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
