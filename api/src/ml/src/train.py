import argparse, json, yaml, os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, RocCurveDisplay, PrecisionRecallDisplay
from joblib import dump
from .data_prep import make_dataset

def ensure_dirs(d):
    os.makedirs(d, exist_ok=True)

def plot_and_save_roc(y_true, proba, out_path):
    RocCurveDisplay.from_predictions(y_true, proba)
    plt.title("ROC")
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()

def plot_and_save_pr(y_true, proba, out_path):
    PrecisionRecallDisplay.from_predictions(y_true, proba)
    plt.title("Precision-Recall")
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()

def plot_and_save_calibration(y_true, proba, out_path):
    prob_true, prob_pred = calibration_curve(y_true, proba, n_bins=10, strategy="uniform")
    plt.plot(prob_pred, prob_true, marker="o")
    plt.plot([0,1],[0,1], linestyle="--")
    plt.xlabel("Predicted probability")
    plt.ylabel("Observed frequency")
    plt.title("Calibration curve")
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()

def decile_lift(y_true, proba):
    import pandas as pd
    df = pd.DataFrame({"y":y_true, "p":proba})
    df["decile"] = pd.qcut(df["p"], 10, labels=False, duplicates="drop")
    out = df.groupby("decile").agg(tasa_exceso=("y","mean"), n=("y","size")).reset_index().sort_values("decile")
    out["decile"] = out["decile"].astype(int)
    return out

def main(args):
    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    paths = config["paths"]
    ensure_dirs(paths["model_dir"]); ensure_dirs(paths["reports_dir"]); ensure_dirs(paths["artifacts_dir"])

    X_train, X_test, y_train, y_test, num_cols, cat_cols, w_train, w_test = make_dataset(config)


    preproc_lr = ColumnTransformer([
        ("num", SimpleImputer(strategy="median"), num_cols),
        ("cat", Pipeline([
            ("imp", SimpleImputer(strategy="most_frequent")),
            ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False, min_frequency=0.01, dtype=np.float32))
        ]), cat_cols)
    ])

    preproc_hgb = ColumnTransformer([
        ("num", SimpleImputer(strategy="median"), num_cols),
        ("cat", Pipeline([
            ("imp", SimpleImputer(strategy="most_frequent")),
            ("ord", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1))
        ]), cat_cols)
    ])


    print("Entrenando modelo base (logistic)...")
    lr = LogisticRegression(max_iter=500, class_weight="balanced", solver="saga", C=1.0, n_jobs=1)
    lr_pipe = Pipeline([("prep", preproc_lr), ("clf", lr)])
    lr_sample_weight = getattr(w_train, "values", w_train)
    lr_pipe.fit(X_train, y_train, clf__sample_weight=lr_sample_weight)

    lr_proba = lr_pipe.predict_proba(X_test)[:,1]
    lr_metrics = {
        "roc_auc": float(roc_auc_score(y_test, lr_proba)),
        "pr_auc": float(average_precision_score(y_test, lr_proba)),
        "brier": float(brier_score_loss(y_test, lr_proba))
    }
    dump(lr_pipe, os.path.join(paths["model_dir"], "model_baseline.joblib"))

 
    X_train_reset = X_train.reset_index(drop=True)
    y_train_reset = y_train.reset_index(drop=True)
    w_train_reset = pd.Series(lr_sample_weight).reset_index(drop=True)
    rng = np.random.RandomState(config["training"]["random_state"])
    cal_size = min(5000, int(len(X_train_reset) * 0.15))
    if cal_size == 0:
        cal_size = min(1000, len(X_train_reset))
    cal_idx = rng.choice(len(X_train_reset), size=cal_size, replace=False)
    cal_mask = np.zeros(len(X_train_reset), dtype=bool)
    cal_mask[cal_idx] = True
    X_cal = X_train_reset.loc[cal_mask]
    y_cal = y_train_reset.loc[cal_mask]
    w_cal = w_train_reset.loc[cal_mask]
    X_core = X_train_reset.loc[~cal_mask]
    y_core = y_train_reset.loc[~cal_mask]
    w_core = w_train_reset.loc[~cal_mask]

    hgb_sample_size = min(20000, len(X_core))
    if hgb_sample_size < len(X_core):
        core_idx = rng.choice(X_core.index, size=hgb_sample_size, replace=False)
        X_core_fit = X_core.loc[core_idx]
        y_core_fit = y_core.loc[core_idx]
        w_core_fit = w_core.loc[core_idx]
    else:
        X_core_fit = X_core
        y_core_fit = y_core
        w_core_fit = w_core

    print(f"Entrenando HistGradientBoosting con {len(X_core_fit)} muestras (calibración con {len(X_cal)}).")
    hgb = HistGradientBoostingClassifier(random_state=42, class_weight="balanced")
    hgb_pipe = Pipeline([("prep", preproc_hgb), ("clf", hgb)])
    hgb_pipe.fit(X_core_fit, y_core_fit, clf__sample_weight=w_core_fit.values)
    hgb_cal = CalibratedClassifierCV(hgb_pipe, method="sigmoid", cv="prefit", ensemble=False)
    hgb_cal.fit(X_cal, y_cal, sample_weight=w_cal.values)
    print("Calibración completada.")
    hgb_proba = hgb_cal.predict_proba(X_test)[:,1]

    hgb_metrics = {
        "roc_auc": float(roc_auc_score(y_test, hgb_proba)),
        "pr_auc": float(average_precision_score(y_test, hgb_proba)),
        "brier": float(brier_score_loss(y_test, hgb_proba))
    }
    dump(hgb_cal, os.path.join(paths["model_dir"], "model_hgb_calibrated.joblib"))


    # Guardar métricas visuales (omitido para reducir consumo de recursos)

    dec = decile_lift(y_test, hgb_proba)
    dec.to_csv(os.path.join(paths["reports_dir"], "deciles_lift.csv"), index=False)

    metrics = {"baseline_logistic": lr_metrics, "hgb_calibrated": hgb_metrics}
    with open(os.path.join(paths["reports_dir"], "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    preview = X_test.head(200).copy()
    preview["p_excede_norma"] = hgb_proba[:len(preview)]
    preview["y_real"] = y_test.iloc[:len(preview)].values
    preview.to_csv(os.path.join(paths["artifacts_dir"], "X_test_preview.csv"), index=False)

    print("Entrenamiento completado. Revisa la carpeta 'reports' y 'models'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="config.yaml")
    args = parser.parse_args()
    main(args)
