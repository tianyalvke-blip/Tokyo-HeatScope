"""
train_rf_models.py — train day/night Random Forest LST models from the raw
indicators CSV and save them for future GLEN Agent use (prepared, not wired in).

Inputs:
  F:\\Poster\\dataset\\nofar\\Indicators_nofar.csv
    targets: Summer (daytime LST, = GLEN day_lst), Night (nighttime LST, = GLEN night_lst)
    features: Dist_to_Coast, Elevation_Mean, Water_Ratio, Dist_to_Major_River,
              Avg_Height, Road_Length, Bldg_Coverage_Ratio, SVF_Mean,
              Height_Variance, NDVI

Outputs (models/rf/):
  rf_day.joblib    Pipeline(SimpleImputer(median) + RandomForestRegressor) for Summer
  rf_night.joblib  same, for Night
  features.json            ordered model feature names
  model_metadata.json      R2/RMSE/MAE, feature importances, how to load later

Training shows a live progress bar (tqdm + warm_start incremental tree fitting).
Source CSV and the GLEN source data are never modified.
"""

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(r"F:\Poster\dataset\nofar\Indicators_nofar.csv")
OUT = ROOT / "models" / "rf"

FEATURES = [
    "Dist_to_Coast", "Elevation_Mean", "Water_Ratio", "Dist_to_Major_River",
    "Avg_Height", "Road_Length", "Bldg_Coverage_Ratio", "SVF_Mean",
    "Height_Variance", "NDVI",
]
N_ESTIMATORS = 100
TEST_SIZE = 0.2
SEED = 42
# Constrain tree growth so the serialized models stay small enough for the
# agent to load quickly (unconstrained RF on 15k rows produced ~325 MB files).
RF_PARAMS = dict(n_estimators=1, warm_start=True, random_state=SEED, n_jobs=-1,
                 min_samples_leaf=5, max_features="sqrt")


def train_one(df_full, target, name):
    df = df_full.dropna(subset=[target]).copy()
    X = df[FEATURES]
    y = df[target].astype(float)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=SEED
    )

    pipe = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("rf", RandomForestRegressor(**RF_PARAMS)),
    ])

    # Incremental warm-start fitting so tqdm can show a real per-tree progress bar.
    for n in tqdm(range(1, N_ESTIMATORS + 1), desc=f"Training RF[{name}] ({target})",
                  unit="tree", ncols=100):
        pipe.named_steps["rf"].n_estimators = n
        pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    metrics = {
        "target": target,
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
        "n_estimators": int(pipe.named_steps["rf"].n_estimators),
        "r2": float(r2_score(y_test, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "mae": float(mean_absolute_error(y_test, y_pred)),
    }
    importances = {
        k: float(v)
        for k, v in zip(FEATURES, pipe.named_steps["rf"].feature_importances_.tolist())
    }
    joblib.dump(pipe, OUT / f"rf_{name}.joblib")
    return metrics, importances


def main():
    if not SRC.exists():
        raise SystemExit(f"source CSV not found: {SRC}")
    df_full = pd.read_csv(SRC)
    print(f"rows: {len(df_full)}  | features: {len(FEATURES)}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "features.json").write_text(json.dumps(FEATURES, indent=2), encoding="utf-8")

    day_metrics, day_imp = train_one(df_full, "Summer", "day")
    print()
    night_metrics, night_imp = train_one(df_full, "Night", "night")

    meta = {
        "description": "Random Forest LST models trained from Indicators_nofar.csv "
                       "(CSIS/satellite-derived indicators, Tokyo 200 m grid, 14 896 cells).",
        "source": str(SRC),
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "seed": SEED,
        "features": FEATURES,
        "feature_order_note": "Model features are the CSV names; the GLEN grid uses the "
                              "lowercase equivalents (dist_to_coast, elevation_mean, ...).",
        "models": {
            "day": {
                "file": "rf_day.joblib",
                "target": "Summer (= GLEN day_lst, deg C)",
                "metrics": day_metrics,
                "feature_importances": day_imp,
            },
            "night": {
                "file": "rf_night.joblib",
                "target": "Night (= GLEN night_lst, deg C)",
                "metrics": night_metrics,
                "feature_importances": night_imp,
            },
        },
        "how_to_load_in_agent": (
            "In run_python: import joblib; m = joblib.load('models/rf/rf_day.joblib'); "
            "pred = m.predict(df[['Dist_to_Coast','Elevation_Mean','Water_Ratio',"
            "'Dist_to_Major_River','Avg_Height','Road_Length','Bldg_Coverage_Ratio',"
            "'SVF_Mean','Height_Variance','NDVI']]); missing features are median-imputed "
            "by the pipeline automatically."
        ),
    }
    (OUT / "model_metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== Results ===")
    for name, m in (("day", day_metrics), ("night", night_metrics)):
        print(f"{name}: R2={m['r2']:.4f}  RMSE={m['rmse']:.3f}  MAE={m['mae']:.3f}  "
              f"n={m['n_train']}+{m['n_test']}")
    print(f"\nSaved to: {OUT}")


if __name__ == "__main__":
    main()
