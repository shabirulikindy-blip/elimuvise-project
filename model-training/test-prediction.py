import os
from pathlib import Path

import pandas as pd
from catboost import CatBoostClassifier


DEFAULT_EXTERNAL_DATASET = Path("c:/Users/SHABIRU-MK/Desktop/exampler/student_data.xlsx")


def resolve_data_path(script_dir: Path) -> Path:
    env_path = os.getenv("ELIMUVISE_DATASET_PATH", "").strip()
    if env_path:
        candidate = Path(env_path).expanduser()
        if candidate.exists():
            return candidate

    if DEFAULT_EXTERNAL_DATASET.exists():
        return DEFAULT_EXTERNAL_DATASET

    return script_dir / "student_data.xlsx"

# 1. Load the trained brain we just built
model = CatBoostClassifier()
model.load_model("../dashboard/elimuvise_predictor.cbm")

# 2. Read the excel sheet data you want to predict on
data = pd.read_excel(resolve_data_path(Path(__file__).resolve().parent))
data.columns = data.columns.str.strip().str.lower()

# 3. Align the features exactly like training
# Handle missing values in parent_education (must match training data prep)
for col in data.columns:
    if 'parent' in col:
        data[col] = data[col].fillna('Unknown')

feature_columns = []
for expected in ['gender', 'age', 'study', 'attendance', 'parent', 'internet', 'extra', 'previous']:
    matched = [col for col in data.columns if expected in col]
    if matched:
        feature_columns.append(matched[0])
X = data[feature_columns]

# 4. Generate the predictions!
# predict() gives 1 (Pass) or 0 (Fail)
# predict_proba() gives the percentage chance of passing
data['predicted_pass_fail'] = model.predict(X)
data['confidence_score'] = model.predict_proba(X)[:, 1] # Chance of passing

# Clean up display format
data['predicted_pass_fail'] = data['predicted_pass_fail'].map({1: 'Will Pass', 0: 'Risk of Failing'})
data['confidence_score'] = (data['confidence_score'] * 100).round(1).astype(str) + '%'

# 5. Show the first 10 students and their predictions on screen
print("\n--- GENERATED STUDENT PREDICTIONS ---")
student_id_col = [col for col in data.columns if 'student' in col][0]
print(data[[student_id_col, 'predicted_pass_fail', 'confidence_score']].head(10).to_string(index=False))
print("-------------------------------------\n")

# Save these results back to a brand new spreadsheet
data.to_excel("student_predictions_output.xlsx", index=False)
print("Saved all predictions to 'student_predictions_output.xlsx'!")