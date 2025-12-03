import pandas as pd
import numpy as np
from .utils import read_excel_or_csv, find_first_existing

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


def make_dataset(config: dict):
    paths = config["paths"]
    cols = config["columns"]

    grd = read_excel_or_csv(paths["grd_path"])
    score = read_excel_or_csv(paths["score_path"])

    episode_grd = cols["episode_id_grd"]
    if episode_grd not in grd.columns:
        raise ValueError(f"No encuentro '{episode_grd}' en GRD.")
    episode_score = find_first_existing(score, cols["episode_id_score_candidates"])
    if episode_score is None:
        raise ValueError(f"No encuentro ninguna de {cols['episode_id_score_candidates']} en Score.")

    fecha_ing = cols.get("fecha_ingreso")
    estancia_dias = cols["estancia_dias"]
    estancia_norma = cols["estancia_norma"]

    required_grd = [
        episode_grd,
        fecha_ing,
        estancia_norma,
        estancia_dias,
        "edad_en_anos",
        "sexo_desc_",
        "servicio_ingreso_descripcion_",
        "prevision_desc_",
        "ir_grd_codigo_",
    ]
    for c in required_grd:
        if c and c not in grd.columns:
            raise ValueError(f"No encuentro '{c}' en GRD.")

    score_subset_cols = {
        "total",
        "salud_mental",
        "gestion",
        "categorizacion_de_gestion",
    }
    missing_score = [c for c in score_subset_cols if c not in score.columns]
    if missing_score:
        raise ValueError(f"Faltan columnas en Score: {missing_score}")

    merge_cols = [c for c in required_grd if c]
    grd_sub = grd[merge_cols].copy()
    score_sub = score[[episode_score] + list(score_subset_cols)].copy()

    df = grd_sub.merge(
        score_sub,
        left_on=episode_grd,
        right_on=episode_score,
        how="left",
        suffixes=("", "_score"),
    )

    df["excede_norma"] = (df[estancia_dias] > df[estancia_norma]).astype(int)
    y = df["excede_norma"].copy()

    excess_days = (
        pd.to_numeric(df[estancia_dias], errors="coerce")
        - pd.to_numeric(df[estancia_norma], errors="coerce")
    )
    excess_days = excess_days.clip(lower=0).fillna(0)
    base_weight = 1 + 0.05 * excess_days
    base_weight = base_weight.clip(lower=1.0, upper=3.0)
    sample_weights = pd.Series(base_weight, index=df.index)

    feat_df = build_simplified_features(df, estancia_norma)

    from sklearn.model_selection import train_test_split

    if fecha_ing and fecha_ing in df.columns:
        fechas = pd.to_datetime(df[fecha_ing], errors="coerce")
        cutoff = fechas.quantile(0.8)
        train_idx = fechas <= cutoff
        test_idx = fechas > cutoff
        X_train = feat_df.loc[train_idx]
        X_test = feat_df.loc[test_idx]
        y_train = y.loc[train_idx]
        y_test = y.loc[test_idx]
        w_train = sample_weights.loc[train_idx]
        w_test = sample_weights.loc[test_idx]
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            feat_df, y, test_size=0.2, stratify=y, random_state=42
        )
        w_train, w_test = train_test_split(
            sample_weights, test_size=0.2, stratify=y, random_state=42
        )

    num_cols = [
        "edad",
        "fecha_estimada_de_alta",
        "riesgo_social",
        "riesgo_clinico",
        "riesgo_administrativo",
        "codigo_grd",
    ]
    cat_cols = ["sexo", "servicio_clinico", "prevision"]
    return X_train, X_test, y_train, y_test, num_cols, cat_cols, w_train, w_test


def build_simplified_features(df: pd.DataFrame, estancia_norma_col: str) -> pd.DataFrame:
    features = pd.DataFrame(index=df.index)
    features["edad"] = pd.to_numeric(df["edad_en_anos"], errors="coerce")
    features["sexo"] = df["sexo_desc_"].fillna("desconocido").astype(str)
    features["servicio_clinico"] = df["servicio_ingreso_descripcion_"].fillna("desconocido").astype(str)
    features["prevision"] = df["prevision_desc_"].fillna("desconocido").astype(str)
    features["fecha_estimada_de_alta"] = pd.to_numeric(df[estancia_norma_col], errors="coerce")
    features["codigo_grd"] = pd.to_numeric(df["ir_grd_codigo_"], errors="coerce")

    total = pd.to_numeric(df["total"], errors="coerce")
    features["riesgo_social"] = bucketize_series(total, default_value=1.0)

    salud = pd.to_numeric(df["salud_mental"], errors="coerce")
    features["riesgo_clinico"] = salud_subscale(salud)

    gestion = df["gestion"].astype(str).str.strip().str.lower()
    categ = df["categorizacion_de_gestion"].astype(str).str.strip().str.lower()
    features["riesgo_administrativo"] = admin_scale(gestion, categ)

    return features[FEATURE_COLUMNS].copy()


def bucketize_series(series: pd.Series, default_value: float = 1.0) -> pd.Series:
    valid = series.dropna()
    if valid.empty:
        return pd.Series(default_value, index=series.index, dtype=float)
    q1 = valid.quantile(0.33)
    q2 = valid.quantile(0.66)
    if q2 <= q1:
        q2 = q1 + 1e-6
    out = pd.Series(default_value, index=series.index, dtype=float)
    out = out.where(~series.notna(), default_value)
    out.loc[series <= q1] = 0.0
    out.loc[(series > q1) & (series <= q2)] = 1.0
    out.loc[series > q2] = 2.0
    return out


def salud_subscale(series: pd.Series) -> pd.Series:
    out = pd.Series(1.0, index=series.index, dtype=float)
    numeric = pd.to_numeric(series, errors="coerce")
    out.loc[numeric.notna()] = (numeric.loc[numeric.notna()] - 1).clip(0, 2)
    return out


def admin_scale(gestion: pd.Series, categ: pd.Series) -> pd.Series:
    out = pd.Series(0.0, index=gestion.index, dtype=float)
    out = out.mask(gestion.eq("si"), 1.0)
    mapping = {
        "coordinacion_familiar": 1.0,
        "coordinacion_interinstitucional": 1.0,
        "soporte_financiero": 2.0,
        "intervencion_psicosocial": 2.0,
        "derivacion_apoyo_psicosocial": 2.0,
    }
    mapped = categ.map(mapping)
    out = np.maximum(out, mapped.fillna(0.0))
    return out
