import json
import os
from pathlib import Path

import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split


FEATURE_COLUMNS = [
    "gender",
    "age",
    "study_hours_per_week",
    "attendance_rate",
    "parent_education",
    "internet_access",
    "extracurricular",
    "previous_score",
]
CATEGORICAL_COLUMNS = ["gender", "parent_education", "internet_access", "extracurricular"]
TARGET_COLUMN = "passed"
SEED = 42
DEFAULT_EXTERNAL_DATASET = Path("c:/Users/SHABIRU-MK/Desktop/exampler/student_data.xlsx")


def load_training_data(data_path: Path) -> tuple[pd.DataFrame, pd.Series]:
    data = pd.read_excel(data_path)
    data.columns = data.columns.str.strip()

    if TARGET_COLUMN not in data.columns:
        raise ValueError(f"Missing required target column: {TARGET_COLUMN}")

    missing_features = [col for col in FEATURE_COLUMNS if col not in data.columns]
    if missing_features:
        raise ValueError(f"Missing required feature columns: {missing_features}")

    data[TARGET_COLUMN] = data[TARGET_COLUMN].map({"Yes": 1, "No": 0})
    if data[TARGET_COLUMN].isna().any():
        raise ValueError("Target column has values other than 'Yes'/'No'.")

    data["parent_education"] = data["parent_education"].fillna("Unknown")

    X = data[FEATURE_COLUMNS].copy()
    y = data[TARGET_COLUMN].astype(int)
    return X, y


def resolve_data_path(script_dir: Path) -> Path:
    env_path = os.getenv("ELIMUVISE_DATASET_PATH", "").strip()
    if env_path:
        candidate = Path(env_path).expanduser()
        if candidate.exists():
            return candidate

    if DEFAULT_EXTERNAL_DATASET.exists():
        return DEFAULT_EXTERNAL_DATASET

    return script_dir / "student_data.xlsx"


def build_feature_defaults(X: pd.DataFrame) -> dict[str, object]:
    defaults: dict[str, object] = {}
    for column in FEATURE_COLUMNS:
        if column in CATEGORICAL_COLUMNS:
            mode_series = X[column].dropna().mode()
            defaults[column] = str(mode_series.iloc[0]) if not mode_series.empty else "Unknown"
        else:
            defaults[column] = round(float(X[column].dropna().median()), 4)
    return defaults


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    data_path = resolve_data_path(script_dir)
    output_dir = script_dir.parent / "dashboard"
    model_path = output_dir / "elimuvise_predictor.cbm"
    metadata_path = output_dir / "elimuvise_predictor_metadata.json"

    if not data_path.exists():
        raise FileNotFoundError(f"Training data not found: {data_path}")

    print("Step 1: Loading and validating historical spreadsheet...")
    X, y = load_training_data(data_path)
    feature_defaults = build_feature_defaults(X)

    print("Step 2: Splitting dataset (train/validation)...")
    X_train, X_val, y_train, y_val = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=SEED,
        stratify=y,
    )

    print("Step 3: Training CatBoost model with early stopping...")
    model = CatBoostClassifier(
        iterations=800,
        learning_rate=0.05,
        depth=6,
        random_seed=SEED,
        loss_function="Logloss",
        eval_metric="AUC",
        auto_class_weights="Balanced",
        verbose=50,
    )
    model.fit(
        X_train,
        y_train,
        cat_features=CATEGORICAL_COLUMNS,
        eval_set=(X_val, y_val),
        early_stopping_rounds=60,
        use_best_model=True,
    )

    print("Step 4: Evaluating validation performance...")
    val_prob = model.predict_proba(X_val)[:, 1]
    val_pred = (val_prob >= 0.5).astype(int)
    metrics = {
        "validation_accuracy": round(float(accuracy_score(y_val, val_pred)), 4),
        "validation_auc": round(float(roc_auc_score(y_val, val_prob)), 4),
        "validation_f1": round(float(f1_score(y_val, val_pred)), 4),
        "train_rows": int(len(X_train)),
        "validation_rows": int(len(X_val)),
        "best_iteration": int(model.get_best_iteration()),
    }
    print(json.dumps(metrics, indent=2))

    print("Step 5: Saving model + metadata for Django integration...")
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_model(model_path)

    metadata = {
        "model_type": "CatBoostClassifier",
        "target_column": TARGET_COLUMN,
        "feature_columns": FEATURE_COLUMNS,
        "categorical_columns": CATEGORICAL_COLUMNS,
        "feature_defaults": feature_defaults,
        "positive_label": "passed",
        "negative_label": "failed",
        "probability_threshold": 0.5,
        "metrics": metrics,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Success! Model saved to: {model_path}")
    print(f"Metadata saved to: {metadata_path}")


if __name__ == "__main__":
    main()