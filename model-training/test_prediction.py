import os
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

def main():
    print("--- Testing Saved Model Correctness ---")
    
    # 1. Load data
    if not os.path.exists("student_data.xlsx"):
        print("Error: student_data.xlsx not found.")
        return
    data = pd.read_excel("student_data.xlsx")
    data.columns = data.columns.str.strip()
    
    # Map target variable
    data['passed'] = data['passed'].map({'Yes': 1, 'No': 0})
    y = data['passed']
    
    # Fill missing values
    data['parent_education'] = data['parent_education'].fillna('Unknown')
    
    # Feature columns
    feature_columns = [
        'gender', 'age', 'study_hours_per_week', 'attendance_rate', 
        'parent_education', 'internet_access', 'extracurricular', 'previous_score'
    ]
    X = data[feature_columns]
    categorical_columns = ['gender', 'parent_education', 'internet_access', 'extracurricular']
    
    # 2. Load the saved model
    model_path = os.path.join("..", "dashboard", "elimuvise_predictor.cbm")
    if not os.path.exists(model_path):
        print(f"Error: Saved model not found at {model_path}. Please run train.py first.")
        return
        
    model = CatBoostClassifier()
    model.load_model(model_path)
    print("Loaded model successfully.")
    
    # 3. Predict and evaluate on the full dataset (training performance)
    preds = model.predict(X)
    probs = model.predict_proba(X)[:, 1]
    
    acc = accuracy_score(y, preds)
    print(f"\nModel Performance on Full Dataset:")
    print(f"Overall Accuracy: {acc:.4f} ({acc*100:.2f}%)")
    print("\nClassification Report:")
    print(classification_report(y, preds, target_names=['Failed (No)', 'Passed (Yes)']))
    
    print("Confusion Matrix:")
    print(confusion_matrix(y, preds))
    
    # 4. Show sample predictions
    print("\nSample Predictions:")
    samples = data.copy()
    samples['Predicted_Prob'] = probs
    samples['Predicted_Label'] = preds
    samples['Predicted_Passed'] = samples['Predicted_Label'].map({1: 'Yes', 0: 'No'})
    samples['Actual_Passed'] = data['passed'].map({1: 'Yes', 0: 'No'})
    
    # Select columns to display
    display_cols = [
        'student_id', 'gender', 'age', 'attendance_rate', 
        'previous_score', 'final_score', 'Actual_Passed', 'Predicted_Passed', 'Predicted_Prob'
    ]
    print(samples[display_cols].head(10).to_string(index=False))
    
    # 5. Evaluate Generalization (Train/Test Split validation)
    print("\n--- Running Train/Test Split Validation (80/20) ---")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    split_model = CatBoostClassifier(
        iterations=150,
        learning_rate=0.1,
        depth=6,
        verbose=0
    )
    split_model.fit(X_train, y_train, cat_features=categorical_columns)
    split_preds = split_model.predict(X_test)
    split_acc = accuracy_score(y_test, split_preds)
    print(f"Validation (Test Set) Accuracy: {split_acc:.4f} ({split_acc*100:.2f}%)")
    print("\nValidation Classification Report:")
    print(classification_report(y_test, split_preds, target_names=['Failed (No)', 'Passed (Yes)']))

if __name__ == "__main__":
    main()
