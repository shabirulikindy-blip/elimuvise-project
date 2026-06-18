import json
from pathlib import Path
from typing import Any

from catboost import CatBoostClassifier


MODEL_PATH = Path(__file__).resolve().parent / "elimuvise_predictor.cbm"
METADATA_PATH = Path(__file__).resolve().parent / "elimuvise_predictor_metadata.json"

_model: CatBoostClassifier | None = None
_metadata: dict[str, Any] | None = None


def _load_metadata() -> dict[str, Any]:
    global _metadata
    if _metadata is None:
        if not METADATA_PATH.exists():
            raise FileNotFoundError(f"Model metadata not found: {METADATA_PATH}")
        _metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    return _metadata


def _load_model() -> CatBoostClassifier:
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"CatBoost model not found: {MODEL_PATH}")
        loaded = CatBoostClassifier()
        loaded.load_model(MODEL_PATH)
        _model = loaded
    return _model


def predict_student_outcome(features: dict[str, Any]) -> dict[str, Any]:
    """
    Predict probability of passing for a single student feature payload.

    Required keys are defined in dashboard/elimuvise_predictor_metadata.json.
    """
    metadata = _load_metadata()
    model = _load_model()

    feature_columns: list[str] = metadata["feature_columns"]
    categorical_columns: list[str] = metadata.get("categorical_columns", [])
    threshold = float(metadata.get("probability_threshold", 0.5))
    feature_defaults: dict[str, Any] = metadata.get("feature_defaults", {})

    missing = [column for column in feature_columns if column not in features and column not in feature_defaults]
    if missing:
        raise ValueError(f"Missing required feature(s): {missing}")

    row = []
    for column in feature_columns:
        value = features.get(column, feature_defaults.get(column))
        if column in categorical_columns and value is None:
            value = "Unknown"
        if column not in categorical_columns and value is not None:
            value = float(value)
        row.append(value)

    probability = float(model.predict_proba([row])[0][1])
    binary_prediction = 1 if probability >= threshold else 0

    if probability < 0.40:
        risk_label = "At-Risk"
    elif probability < 0.70:
        risk_label = "Average"
    else:
        risk_label = "Low Risk"

    return {
        "probability_pass": round(probability, 4),
        "predicted_class": binary_prediction,
        "predicted_label": "Yes" if binary_prediction == 1 else "No",
        "risk_label": risk_label,
        "threshold": threshold,
    }