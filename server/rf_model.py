"""
rf_model.py — Random Forest LST model loader for the GLEN LST Agent.

PREPARED FOR FUTURE AGENT INTEGRATION — NOT wired into the MCP server yet.
The agent can use this from `run_python` (or a future `rf_predict` MCP tool)
to predict daytime / nighttime LST from the 10 grid indicators.

Models (trained by scripts/train_rf_models.py):
  models/rf/rf_day.joblib     -> GLEN day_lst  (source CSV column "Summer")
  models/rf/rf_night.joblib   -> GLEN night_lst (source CSV column "Night")

Each saved object is a sklearn Pipeline(SimpleImputer(median) -> RandomForestRegressor),
so missing predictor values are median-imputed automatically at predict time.

The GLEN grid columns map to model features (lowercase -> CSV name):
  dist_to_coast          -> Dist_to_Coast
  elevation_mean         -> Elevation_Mean
  water_ratio            -> Water_Ratio
  dist_to_major_river    -> Dist_to_Major_River
  avg_height             -> Avg_Height
  road_length            -> Road_Length
  bldg_coverage_ratio    -> Bldg_Coverage_Ratio
  svf_mean               -> SVF_Mean
  height_variance        -> Height_Variance
  ndvi                   -> NDVI
"""

import json
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models" / "rf"

FEATURES = json.loads((MODEL_DIR / "features.json").read_text(encoding="utf-8"))

GLEN_TO_MODEL = {
    "dist_to_coast": "Dist_to_Coast",
    "elevation_mean": "Elevation_Mean",
    "water_ratio": "Water_Ratio",
    "dist_to_major_river": "Dist_to_Major_River",
    "avg_height": "Avg_Height",
    "road_length": "Road_Length",
    "bldg_coverage_ratio": "Bldg_Coverage_Ratio",
    "svf_mean": "SVF_Mean",
    "height_variance": "Height_Variance",
    "ndvi": "NDVI",
}


def load(model_name: str = "day"):
    """Load a trained pipeline: 'day' (day_lst) or 'night' (night_lst)."""
    if model_name not in ("day", "night"):
        raise ValueError("model_name must be 'day' or 'night'")
    return joblib.load(MODEL_DIR / f"rf_{model_name}.joblib")


def predict(df, model_name: str = "day"):
    """Predict LST (°C) for a grid-like DataFrame.

    Accepts a DataFrame with either the model feature names or the GLEN
    lowercase column names (or a mix). Returns a numpy array aligned with the
    input rows. Missing values are median-imputed by the pipeline.
    """
    model = load(model_name)
    missing = [c for c in FEATURES if c not in df.columns]
    if missing:
        # Try GLEN lowercase names for any missing model features.
        renames = {g: m for g, m in GLEN_TO_MODEL.items() if m in missing and g in df.columns}
        if renames:
            df = df.rename(columns=renames)
        missing = [c for c in FEATURES if c not in df.columns]
        if missing:
            raise ValueError(f"missing features in input: {missing}")
    return model.predict(df[FEATURES])
