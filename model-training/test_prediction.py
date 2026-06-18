import json
import os
from pathlib import Path

import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)


DEFAULT_EXTERNAL_DATASET = Path("c:/Users/SHABIRU-MK/Desktop/exampler/student_data.xlsx")


def load_metadata(metadata_path: Path) -> dict:
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def prepare_data(data_path: Path, feature_columns: list[str], target_column: str) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    data = pd.read_excel(data_path)
    data.columns = data.columns.str.strip()
    data["parent_education"] = data["parent_education"].fillna("Unknown")
    data[target_column] = data[target_column].map({"Yes": 1, "No": 0})
    if data[target_column].isna().any():
        raise ValueError("Target column has values other than 'Yes'/'No'.")

    X = data[feature_columns].copy()
    y = data[target_column].astype(int)
    return X, y, data


def resolve_data_path(script_dir: Path) -> Path:
    env_path = os.getenv("ELIMUVISE_DATASET_PATH", "").strip()
    if env_path:
        candidate = Path(env_path).expanduser()
        if candidate.exists():
            return candidate

    if DEFAULT_EXTERNAL_DATASET.exists():
        return DEFAULT_EXTERNAL_DATASET

    return script_dir / "student_data.xlsx"


def main() -> None:
    print("--- Testing Saved CatBoost Model Correctness ---")

    script_dir = Path(__file__).resolve().parent
    data_path = resolve_data_path(script_dir)
    model_path = script_dir.parent / "dashboard" / "elimuvise_predictor.cbm"
    metadata_path = script_dir.parent / "dashboard" / "elimuvise_predictor_metadata.json"

    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}. Run train.py first.")
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}. Run train.py first.")

    metadata = load_metadata(metadata_path)
    feature_columns = metadata["feature_columns"]
    target_column = metadata["target_column"]
    threshold = float(metadata.get("probability_threshold", 0.5))

    X, y, raw = prepare_data(data_path, feature_columns, target_column)

    model = CatBoostClassifier()
    model.load_model(model_path)
    print(f"Loaded model: {model_path}")

    probs = model.predict_proba(X)[:, 1]
    preds = (probs >= threshold).astype(int)

    acc = accuracy_score(y, preds)
    auc = roc_auc_score(y, probs)
    f1 = f1_score(y, preds)

    print("\nModel Performance on dataset:")
    print(f"Accuracy: {acc:.4f} ({acc*100:.2f}%)")
    print(f"ROC-AUC:  {auc:.4f}")
    print(f"F1 Score: {f1:.4f}")
    print("\nClassification Report:")
    print(classification_report(y, preds, target_names=["Failed (No)", "Passed (Yes)"]))

    print("Confusion Matrix:")
    print(confusion_matrix(y, preds))

    display = raw.copy()
    display["predicted_prob"] = probs
    display["predicted_label"] = preds
    display["predicted_passed"] = display["predicted_label"].map({1: "Yes", 0: "No"})
    display["actual_passed"] = y.map({1: "Yes", 0: "No"})

    print("\nSample Predictions:")
    cols = [
        "student_id",
        "gender",
        "age",
        "attendance_rate",
        "previous_score",
        "actual_passed",
        "predicted_passed",
        "predicted_prob",
    ]
    available_cols = [c for c in cols if c in display.columns]
    print(display[available_cols].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
