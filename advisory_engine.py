import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import NotFittedError
from sklearn.metrics import accuracy_score, mean_squared_error
from sklearn.model_selection import train_test_split
from models import Student, Result

risk_map = {
    'Distinction': 'low',
    'Average': 'medium',
    'At-Risk': 'high'
}

badge_map = {
    'Distinction': 'success',
    'Average': 'warning',
    'At-Risk': 'danger'
}

_model_store = {
    'classifier': None,
    'regressor': None,
    'scaler': None,
    'feature_names': [],
    'metrics': {},
    'training_data': None
}

TRAINING_DATA_PATH = os.path.join(os.path.dirname(__file__), 'student_performance.csv')


def get_badge_class(prediction):
    return badge_map.get(prediction, 'secondary')


def load_training_dataset():
    if not os.path.exists(TRAINING_DATA_PATH):
        return None

    df = pd.read_csv(TRAINING_DATA_PATH)
    
    # Filter for Form 5 & 6 (ages 16-18)
    df = df[(df['age'] >= 16) & (df['age'] <= 18)]
    
    # Clean and encode data
    df['internet_access'] = df['internet_access'].map({'Yes': 1, 'No': 0})
    df['extracurricular'] = df['extracurricular'].map({'Yes': 1, 'No': 0})
    df['passed'] = df['passed'].map({'Yes': 1, 'No': 0})
    
    # Encode parent education
    parent_ed_map = {'None': 0, 'High School': 1, 'Bachelor': 2, 'Master': 3, 'PhD': 4}
    df['parent_education_encoded'] = df['parent_education'].map(parent_ed_map)
    
    # Encode gender
    df['gender_encoded'] = df['gender'].map({'Male': 0, 'Female': 1})
    
    # Convert numeric columns
    numeric_cols = ['study_hours_per_week', 'attendance_rate', 'previous_score', 'final_score', 'age']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Drop rows with missing values
    df = df.dropna(subset=['study_hours_per_week', 'attendance_rate', 'previous_score', 'final_score', 
                           'passed', 'internet_access', 'extracurricular', 'parent_education_encoded', 'gender_encoded'])
    
    return df if not df.empty else None


def train_ai_model():
    if _model_store['classifier'] is not None and _model_store['regressor'] is not None:
        return _model_store['classifier'], _model_store['regressor']

    df = load_training_dataset()
    if df is None or df.empty:
        return None, None

    feature_cols = ['study_hours_per_week', 'attendance_rate', 'previous_score', 'internet_access',
                    'extracurricular', 'parent_education_encoded', 'gender_encoded', 'age']
    
    X = df[feature_cols].copy()
    y_class = df['passed']
    y_reg = df['final_score']

    if len(df) < 20:
        return None, None

    # Store training data and feature names
    _model_store['training_data'] = df.copy()
    _model_store['feature_names'] = feature_cols

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    _model_store['scaler'] = scaler

    # Train classifier
    X_train_cls, X_test_cls, y_train_cls, y_test_cls = train_test_split(
        X_scaled, y_class, test_size=0.25, random_state=42, stratify=y_class
    )
    classifier = RandomForestClassifier(n_estimators=150, max_depth=12, random_state=42, n_jobs=-1)
    classifier.fit(X_train_cls, y_train_cls)
    y_pred_cls = classifier.predict(X_test_cls)
    pass_accuracy = float(accuracy_score(y_test_cls, y_pred_cls))

    # Train regressor
    X_train_reg, X_test_reg, y_train_reg, y_test_reg = train_test_split(
        X_scaled, y_reg, test_size=0.25, random_state=42
    )
    regressor = RandomForestRegressor(n_estimators=150, max_depth=12, random_state=42, n_jobs=-1)
    regressor.fit(X_train_reg, y_train_reg)
    y_pred_reg = regressor.predict(X_test_reg)
    final_score_mse = float(mean_squared_error(y_test_reg, y_pred_reg))
    final_score_rmse = float(np.sqrt(final_score_mse))

    _model_store['classifier'] = classifier
    _model_store['regressor'] = regressor
    _model_store['metrics'] = {
        'pass_accuracy': round(pass_accuracy, 3),
        'final_score_rmse': round(final_score_rmse, 2),
        'training_rows': len(df),
        'features_used': len(feature_cols)
    }

    return classifier, regressor


def build_student_features(results_df, attendance_rate, student=None, features_dict=None):
    """Build feature vector for a student. Uses provided features or estimates from results."""
    if features_dict is None:
        features_dict = {}
    
    # Base features (always required)
    avg_score = float(results_df['score'].mean()) if not results_df.empty else 50.0
    study_hours = float(features_dict.get('study_hours_per_week', min(40.0, max(2.0, (avg_score * 0.2) + (attendance_rate * 0.15)))))
    
    # Optional features with reasonable defaults
    internet = float(features_dict.get('internet_access', 1.0))
    extracurricular = float(features_dict.get('extracurricular', 0.5))
    parent_education = float(features_dict.get('parent_education_encoded', 2.0))
    gender = float(features_dict.get('gender_encoded', 0.5))
    age = float(features_dict.get('age', 17.0))
    
    return {
        'study_hours_per_week': study_hours,
        'attendance_rate': attendance_rate,
        'previous_score': avg_score,
        'internet_access': internet,
        'extracurricular': extracurricular,
        'parent_education_encoded': parent_education,
        'gender_encoded': gender,
        'age': age
    }


def predict_student_status(results_df, attendance_rate, features_dict=None):
    """Predict student status using AI model. Falls back to rule-based if model unavailable."""
    classifier, regressor = train_ai_model()
    if classifier is None or regressor is None:
        return fallback_student_status(results_df, attendance_rate)

    features = build_student_features(results_df, attendance_rate, features_dict=features_dict)
    feature_df = pd.DataFrame([features])
    
    # Reorder columns to match training order
    feature_cols = _model_store['feature_names']
    feature_df = feature_df[feature_cols]
    
    try:
        # Scale features using the trained scaler
        if _model_store['scaler'] is not None:
            feature_df_scaled = _model_store['scaler'].transform(feature_df)
        else:
            feature_df_scaled = feature_df.values

        prob_pass = float(classifier.predict_proba(feature_df_scaled)[0][1])
        predicted_final = float(regressor.predict(feature_df_scaled)[0])
    except (AttributeError, NotFittedError, IndexError):
        prob_pass = float(classifier.predict(feature_df)[0])
        predicted_final = float(regressor.predict(feature_df)[0])

    # Decision logic
    if prob_pass >= 0.85 and predicted_final >= 75:
        return 'Distinction'
    if prob_pass < 0.60 or predicted_final < 60:
        return 'At-Risk'
    return 'Average'


def fallback_student_status(results_df, attendance_rate):
    if results_df.empty:
        return 'Average'

    avg_score = float(results_df['score'].mean())
    if avg_score >= 85 and attendance_rate >= 90:
        return 'Distinction'
    if avg_score < 65 or attendance_rate < 80:
        return 'At-Risk'
    return 'Average'


def get_risk_assessment(results_df, attendance_rate, prediction):
    """Generate detailed risk assessment with interventions."""
    assessment = {
        'prediction': prediction,
        'risk_level': risk_map.get(prediction, 'medium'),
        'concerns': [],
        'strengths': [],
        'interventions': []
    }
    
    if results_df.empty:
        assessment['concerns'].append('No assessment scores recorded yet')
        assessment['interventions'].append('Upload at least 2 assessment scores for analysis')
        return assessment
    
    avg_score = float(results_df['score'].mean())
    
    # Identify concerns
    if avg_score < 60:
        assessment['concerns'].append('Below-average performance across assessments')
        assessment['interventions'].append('Schedule weekly tutoring sessions')
        assessment['interventions'].append('Review and simplify study strategies')
    elif avg_score < 70:
        assessment['concerns'].append('Performance below expected Form 5/6 level')
        assessment['interventions'].append('Increase study hours to 25+ per week')
        assessment['interventions'].append('Form study groups with high-performing peers')
    
    if attendance_rate < 80:
        assessment['concerns'].append('Low attendance rate ({:.1f}%)'.format(attendance_rate))
        assessment['interventions'].append('Improve class attendance - aim for 95%+')
        assessment['interventions'].append('Contact advisor about attendance barriers')
    elif attendance_rate < 90:
        assessment['concerns'].append('Attendance could be improved')
        assessment['interventions'].append('Target 95%+ attendance for final term')
    
    # Identify strengths
    if avg_score >= 75:
        assessment['strengths'].append('Strong overall academic performance')
    if attendance_rate >= 90:
        assessment['strengths'].append('Excellent attendance record')
    if avg_score >= 80 and attendance_rate >= 85:
        assessment['strengths'].append('Consistent high performer')
        assessment['interventions'].append('Consider advanced topics or mentoring peers')
    
    return assessment


def generate_advisor_recommendations(student, results):
    """Generate comprehensive AI-powered recommendations for advisors."""
    if isinstance(results, list):
        results = pd.DataFrame(results)
    
    recommendations = {
        'priority_level': 'Low',
        'key_insights': [],
        'recommended_actions': [],
        'subject_focus': [],
        'resource_suggestions': []
    }
    
    if results.empty:
        recommendations['priority_level'] = 'Medium'
        recommendations['key_insights'].append('Limited data - cannot yet generate comprehensive recommendations')
        recommendations['recommended_actions'].append('Ensure assessment scores are regularly uploaded')
        return recommendations
    
    avg_score = float(results['score'].mean())
    attendance = student.attendance_rate
    
    # Determine priority
    if avg_score < 60 or attendance < 75:
        recommendations['priority_level'] = 'High'
    elif avg_score < 70 or attendance < 85:
        recommendations['priority_level'] = 'Medium'
    
    # Key insights
    if avg_score < 65:
        recommendations['key_insights'].append('Student is struggling academically and requires immediate intervention')
    elif avg_score >= 80:
        recommendations['key_insights'].append('Student demonstrates strong academic capability')
    
    if attendance >= 95:
        recommendations['key_insights'].append('Excellent attendance - student is engaged with classes')
    
    # Subject-specific analysis
    subject_avgs = results.groupby('subject')['score'].mean().sort_values()
    if not subject_avgs.empty:
        weakest_subject = subject_avgs.index[0]
        strongest_subject = subject_avgs.index[-1]
        recommendations['subject_focus'].append(f'Strengthen {weakest_subject} (avg: {subject_avgs.iloc[0]:.1f})')
        recommendations['subject_focus'].append(f'Leverage strength in {strongest_subject} to build confidence')
    
    # Recommended actions
    if avg_score < 70:
        recommendations['recommended_actions'].append('Schedule one-on-one mentoring session')
        recommendations['recommended_actions'].append('Consider reduced course load if applicable')
    
    if attendance < 85:
        recommendations['recommended_actions'].append('Conduct attendance counseling')
        recommendations['recommended_actions'].append('Identify and address attendance barriers')
    
    recommendations['recommended_actions'].append('Set SMART academic goals for next term')
    
    # Resources
    if avg_score < 70:
        recommendations['resource_suggestions'].append('Connect to peer tutoring program')
        recommendations['resource_suggestions'].append('Provide study skills workshop materials')
        recommendations['resource_suggestions'].append('Recommend time management resources')
    
    if attendance < 90:
        recommendations['resource_suggestions'].append('Explore transportation/logistic support options')
    
    return recommendations


def generate_study_tips(student, results):
    """Generate personalized study tips for students."""
    if isinstance(results, list):
        results = pd.DataFrame(results)
    if results.empty:
        return [
            'Upload continuous assessment scores so the advisory engine can provide tailored tips.',
            'Maintain consistent attendance to improve academic stability.',
            'The AI system is trained on Form 5/6 student data to identify support needs.',
            'Speak with your advisor if you need academic help.'
        ]

    average = float(results['score'].mean())
    weakest = results.groupby('subject')['score'].mean().sort_values().head(2).index.tolist()
    tips = []
    
    if average < 60:
        tips.append('Your scores suggest urgent need for intervention - contact your advisor today.')
        tips.append('Focus intensively on {}: practice past papers daily.'.format(', '.join(weakest)))
        tips.append('Aim to study at least 30 hours per week for the next 4 weeks.')
    elif average < 70:
        tips.append('Strengthen weaker areas: {}'.format(', '.join(weakest)))
        tips.append('Complete one timed practice exam per week in each subject.')
        tips.append('Form or join a study group - teaching others reinforces learning.')
    else:
        tips.append('Strong foundation! Keep reviewing {} to maintain gains.'.format(weakest[0]))
        tips.append('Challenge yourself with extension materials to prepare for final exams.')
    
    if student.attendance_rate < 80:
        tips.append('Attend every class from now on - missing lessons impacts all subjects.')
    elif student.attendance_rate < 90:
        tips.append('Your attendance is good but can improve - target 95%+ for final term.')
    else:
        tips.append('Excellent attendance! Keep this commitment through to final exams.')
    
    if average >= 75 and student.attendance_rate >= 90:
        tips.append('You are well-positioned for distinction - maintain your current habits.')
    
    return tips


def run_prediction_engine(db):
    train_ai_model()
    students = Student.query.all()
    for student in students:
        result_rows = Result.query.filter_by(student_id=student.id).all()
        if not result_rows:
            student.prediction = 'Average'
            student.risk_level = risk_map[student.prediction]
            continue

        results_df = pd.DataFrame([
            {'subject': r.subject, 'score': r.score}
            for r in result_rows
        ])
        prediction = predict_student_status(results_df, student.attendance_rate)
        student.prediction = prediction
        student.risk_level = risk_map[prediction]

    db.session.commit()
