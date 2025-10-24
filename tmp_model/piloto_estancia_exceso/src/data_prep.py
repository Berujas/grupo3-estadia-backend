import json
import yaml
import pandas as pd
from .utils import read_excel_or_csv, coerce_dtypes, find_first_existing

def make_dataset(config: dict):
    paths = config["paths"]
    cols = config["columns"]
    forbidden_patterns = config["forbidden_feature_patterns"]
    drop_from_score = set(config.get("drop_from_score", []))
    whitelist_grd = set(config.get("feature_whitelist_grd", []))

    grd = read_excel_or_csv(paths["grd_path"])
    score = read_excel_or_csv(paths["score_path"])

    # Detectar llaves
    episode_grd = cols["episode_id_grd"]
    if episode_grd not in grd.columns:
        raise ValueError(f"No encuentro '{episode_grd}' en GRD.")
    episode_score = find_first_existing(score, cols["episode_id_score_candidates"])
    if episode_score is None:
        raise ValueError(f"No encuentro ninguna de {cols['episode_id_score_candidates']} en Score.")

    fecha_ing = cols.get("fecha_ingreso")
    estancia_dias = cols["estancia_dias"]
    estancia_norma = cols["estancia_norma"]

    for c in [estancia_dias, estancia_norma]:
        if c not in grd.columns:
            raise ValueError(f"No encuentro '{c}' en GRD.")

    # Subset GRD con features de admision
    keep_grd = [x for x in whitelist_grd if x in grd.columns]
    base_cols = [episode_grd, fecha_ing, estancia_norma, estancia_dias]
    grd_sub = grd[ list(dict.fromkeys(base_cols + keep_grd)) ].copy()

    # Subset Score (excluir obvios de tiempo/nombres)
    score_cols = [c for c in score.columns if c not in drop_from_score]
    score_sub = score[score_cols].copy()

    # Merge
    df = grd_sub.merge(score_sub, left_on=episode_grd, right_on=episode_score, how="left", suffixes=("","_score"))

    # Target
    df["excede_norma"] = (df[estancia_dias] > df[estancia_norma]).astype(int)

    # Quitar columnas con fuga
    leak_cols = [c for c in df.columns if any(pat in c for pat in forbidden_patterns)]
    feat_df = df.drop(columns=["excede_norma"] + leak_cols, errors="ignore")

    # Quitar ids obvios
    for c in [episode_grd, episode_score]:
        if c in feat_df.columns:
            feat_df = feat_df.drop(columns=[c])

    y = df["excede_norma"].copy()

    # Separación
    from sklearn.model_selection import train_test_split
    if fecha_ing and fecha_ing in feat_df.columns:
        feat_df[fecha_ing] = pd.to_datetime(feat_df[fecha_ing], errors="coerce")
        cutoff = feat_df[fecha_ing].quantile(0.8)
        train_idx = feat_df[fecha_ing] <= cutoff
        test_idx  = feat_df[fecha_ing] > cutoff
        X_train = feat_df.loc[train_idx].drop(columns=[fecha_ing])
        X_test  = feat_df.loc[test_idx].drop(columns=[fecha_ing])
        y_train = y.loc[train_idx]
        y_test  = y.loc[test_idx]
    else:
        X_train, X_test, y_train, y_test = train_test_split(feat_df, y, test_size=0.2, stratify=y, random_state=42)

    # Tipos
    X_train, num_cols, cat_cols = coerce_dtypes(X_train)
    for c in X_test.columns:
        if c not in X_train.columns:
            X_test = X_test.drop(columns=[c])
    X_test = X_test[X_train.columns]
    return X_train, X_test, y_train, y_test, num_cols, cat_cols
