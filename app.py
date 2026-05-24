import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from sqlalchemy import text
from dotenv import load_dotenv
from config import Config
from models import db, User, Student, Result, Alert, SystemLog, Notification
from advisory_engine import run_prediction_engine, generate_study_tips, get_badge_class, get_risk_assessment, generate_advisor_recommendations

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_unread_notifications():
    unread_count = 0
    if current_user.is_authenticated:
        unread_count = Notification.query.filter_by(user_id=current_user.id, read=False).count()
    return dict(unread_notification_count=unread_count)

_db_initialized = False

def upgrade_schema():
    with db.engine.begin() as conn:
        try:
            conn.execute(text('ALTER TABLE users ADD COLUMN approved BOOLEAN DEFAULT FALSE'))
        except Exception:
            pass  # Column already exists
        try:
            conn.execute(text('ALTER TABLE users ADD COLUMN rejected BOOLEAN DEFAULT FALSE'))
        except Exception:
            pass  # Column already exists
        try:
            conn.execute(text('ALTER TABLE users ADD COLUMN registration_rule VARCHAR(120)'))
        except Exception:
            pass  # Column already exists


def setup_database():
    global _db_initialized
    if _db_initialized:
        return
    db.create_all()
    upgrade_schema()
    seed_sample_data()
    run_prediction_engine(db)
    _db_initialized = True

def log_event(event_type, description):
    entry = SystemLog(event_type=event_type, description=description)
    db.session.add(entry)
    db.session.commit()

def seed_sample_data():
    # Drop all existing data to reseed
    db.session.query(Notification).delete()
    db.session.query(Alert).delete()
    db.session.query(Result).delete()
    db.session.query(Student).delete()
    db.session.query(User).delete()
    db.session.commit()

    admin = User(name='System Admin', username='ElimuVISE', password_hash=generate_password_hash('admin2026'), role='admin', approved=True)
    advisor = User(name='Lead Advisor', email='advisor@example.com', password_hash=generate_password_hash('advisor123'), role='advisor', school_name='Example School', subjects='Math,Science', phone='1234567890', home_address='123 Main St', approved=True)
    parent = User(name='Parent User', email='parent@example.com', password_hash=generate_password_hash('parent123'), role='parent', phone='0987654321', approved=True)
    student_user = User(name='Form 6 Student', username='student123', password_hash=generate_password_hash('student123'), role='student', approved=True)
    db.session.add_all([admin, advisor, parent, student_user])
    db.session.commit()

    student = Student(user_id=student_user.id, form_level='Form 6', combination='PCM', attendance_rate=88.5)
    db.session.add(student)
    db.session.commit()

    first_assessments = [
        ('Mathematics', 78, 'Assessment 1'),
        ('Physics', 82, 'Assessment 1'),
        ('Chemistry', 74, 'Assessment 1'),
        ('Biology', 69, 'Assessment 1'),
        ('Mathematics', 83, 'Assessment 2'),
        ('Physics', 77, 'Assessment 2'),
        ('Chemistry', 79, 'Assessment 2'),
        ('Biology', 72, 'Assessment 2')
    ]
    for subject, score, assessment in first_assessments:
        db.session.add(Result(student_id=student.id, subject=subject, score=score, assessment_name=assessment))
    alert = Alert(student_id=student.id, message='Attendance dropped below 90% this month.')
    db.session.add(alert)
    db.session.commit()

    log_event('seed', 'Initialized sample users, student records, and results.')

@app.route('/')
def index():
    setup_database()
    if current_user.is_authenticated:
        if current_user.role == 'student':
            return redirect(url_for('student_dashboard'))
        if current_user.role == 'advisor':
            return redirect(url_for('advisor_portal'))
        if current_user.role == 'parent':
            return redirect(url_for('parent_portal'))
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
    return render_template('home.html')

@app.route('/home')
def home():
    setup_database()
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['email']  # Still called email in form, but can be email or username
        password = request.form['password']
        user = User.query.filter((User.email == identifier) | (User.username == identifier)).first()
        
        if not user:
            log_event('failed_login', f'Failed login attempt for {identifier}')
            flash('No account found with this email or username. Please register or contact admin.', 'danger')
            return redirect(url_for('login'))
        
        if not check_password_hash(user.password_hash, password):
            log_event('failed_login', f'Incorrect password attempt for {identifier}')
            flash('Incorrect password. Please try again.', 'danger')
            return redirect(url_for('login'))
        
        if user.role != 'admin' and user.rejected:
            log_event('rejected_login', f'Rejected user {identifier} attempted login.')
            flash('Your registration has been rejected by admin. Please contact admin for more information.', 'danger')
            return redirect(url_for('login'))
        
        if user.role != 'admin' and not user.approved:
            log_event('pending_login', f'User {identifier} attempted login before approval.')
            flash('Your registration is pending approval by admin. You will be notified once approved.', 'warning')
            return redirect(url_for('login'))
        
        login_user(user)
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/account/settings', methods=['GET', 'POST'])
@login_required
def account_settings():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_profile':
            current_user.name = request.form.get('name', current_user.name)
            current_user.email = request.form.get('email', current_user.email)
            current_user.phone = request.form.get('phone', current_user.phone)
            current_user.home_address = request.form.get('home_address', current_user.home_address)
            
            try:
                db.session.commit()
                log_event('profile_update', f'User {current_user.email} updated their profile.')
                flash('Profile updated successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash('Error updating profile. Email may already be in use.', 'danger')
        
        elif action == 'change_password':
            old_password = request.form.get('old_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if not check_password_hash(current_user.password_hash, old_password):
                flash('Current password is incorrect.', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
            elif len(new_password) < 6:
                flash('New password must be at least 6 characters long.', 'danger')
            else:
                current_user.password_hash = generate_password_hash(new_password)
                db.session.commit()
                log_event('password_change', f'User {current_user.email} changed their password.')
                flash('Password changed successfully!', 'success')
        
        return redirect(url_for('account_settings'))
    
    return render_template('account_settings.html', user=current_user)

@app.route('/dashboard/student')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('index'))
    student = Student.query.filter_by(user_id=current_user.id).first()
    results = Result.query.filter_by(student_id=student.id).order_by(Result.created_at).all()
    alerts = Alert.query.filter_by(student_id=student.id).order_by(Alert.created_at.desc()).all()
    results_df = pd.DataFrame([{'subject': r.subject, 'score': r.score} for r in results])
    study_tips = generate_study_tips(student, results_df)
    subject_breakdown = {}
    for result in results:
        subject_breakdown.setdefault(result.subject, []).append(result.score)
    subject_breakdown = {subject: sum(scores) / len(scores) for subject, scores in subject_breakdown.items()}
    return render_template('student_dashboard.html', student=student, results=results, alerts=alerts,
                           study_tips=study_tips, subject_breakdown=subject_breakdown,
                           badge_class=get_badge_class(student.prediction))

@app.route('/dashboard/advisor')
@login_required
def advisor_portal():
    if current_user.role != 'advisor':
        return redirect(url_for('index'))
    students = Student.query.all()
    total_students = len(students)
    at_risk = sum(1 for s in students if s.prediction == 'At-Risk')
    average = sum(1 for s in students if s.prediction == 'Average')
    priority_list = sorted(students, key=lambda s: ('At-Risk', 'Average', 'Distinction').index(s.prediction))
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    
    # Generate AI-powered assessments for each student
    student_assessments = {}
    for student in students:
        result_rows = Result.query.filter_by(student_id=student.id).all()
        results_df = pd.DataFrame([{'subject': r.subject, 'score': r.score} for r in result_rows]) if result_rows else pd.DataFrame()
        assessment = get_risk_assessment(results_df, student.attendance_rate, student.prediction)
        student_assessments[student.id] = assessment
    
    return render_template('advisor_portal.html', students=students, total_students=total_students,
                           at_risk=at_risk, average=average, priority_list=priority_list,
                           notifications=notifications, student_assessments=student_assessments)

@app.route('/register', methods=['GET', 'POST'])
def register():
    selected_role = request.args.get('role', '')
    if request.method == 'POST':
        rule = request.form['rule']
        if rule == 'student':
            flash('Students must be registered by an advisor. Please ask your advisor for a username and password.', 'info')
            return redirect(url_for('login'))
        if rule == 'advisor':
            name = request.form['name']
            email = request.form['email']
            password = generate_password_hash(request.form['password'])
            school_name = request.form['school_name']
            subjects = request.form['subjects']
            phone = request.form['phone']
            home_address = request.form['home_address']
            user = User(name=name, email=email, password_hash=password, role='advisor', school_name=school_name, subjects=subjects, phone=phone, home_address=home_address, approved=False, registration_rule=rule)
            db.session.add(user)
            db.session.commit()
            log_event('advisor_registration', f'Registered new advisor {name} awaiting approval.')
            flash('Advisor registered successfully and is now pending admin approval.', 'success')
            return redirect(url_for('login'))
        if rule == 'parent':
            email = request.form['email']
            password = generate_password_hash(request.form['password'])
            phone = request.form['phone']
            user = User(name=email, email=email, password_hash=password, role='parent', phone=phone, approved=False, registration_rule=rule)
            db.session.add(user)
            db.session.commit()
            log_event('parent_registration', f'Registered new parent {email} awaiting approval.')
            flash('Parent registered successfully and is now pending admin approval.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html', selected_role=selected_role)

@app.route('/register-student', methods=['GET', 'POST'])
@login_required
def register_student():
    if current_user.role != 'advisor':
        return redirect(url_for('index'))
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        form_level = request.form['form_level']
        combination = request.form['combination']
        attendance_rate = float(request.form['attendance_rate'])
        user = User(name=name, username=username, password_hash=password, role='student', approved=False)
        db.session.add(user)
        db.session.commit()
        student = Student(user_id=user.id, form_level=form_level, combination=combination, attendance_rate=attendance_rate)
        db.session.add(student)
        db.session.commit()
        log_event('student_registration', f'Registered new student {name} awaiting approval.')
        flash('Student registered successfully and is now pending admin approval.', 'success')
        return redirect(url_for('advisor_portal'))
    return render_template('register_student.html')

@app.route('/register-advisor', methods=['GET', 'POST'])
def register_advisor():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        school_name = request.form['school_name']
        subjects = request.form['subjects']
        phone = request.form['phone']
        home_address = request.form['home_address']
        user = User(name=name, email=email, password_hash=password, role='advisor', school_name=school_name, subjects=subjects, phone=phone, home_address=home_address, approved=False, registration_rule='advisor')
        db.session.add(user)
        db.session.commit()
        log_event('advisor_registration', f'Registered new advisor {name}.')
        flash('Advisor registered successfully and is now pending admin approval.', 'success')
        return redirect(url_for('login'))
    return render_template('register_advisor.html')

@app.route('/register-parent', methods=['GET', 'POST'])
def register_parent():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        phone = request.form['phone']
        home_address = request.form.get('home_address', '')
        user = User(name=name, email=email, password_hash=password, role='parent', phone=phone, home_address=home_address, approved=False, registration_rule='parent')
        db.session.add(user)
        db.session.commit()
        log_event('parent_registration', f'Registered new parent {name} awaiting approval.')
        flash('Parent registered successfully and is now pending admin approval.', 'success')
        return redirect(url_for('login'))
    return render_template('register_parent.html')

@app.route('/approve-user/<int:user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    user.approved = True
    user.rejected = False
    notification = Notification(user_id=user.id, message=f'Your {user.role} registration has been approved. You can now log in.')
    db.session.add(notification)
    db.session.commit()
    log_event('user_approval', f'Approved {user.role} {user.email or user.username}.')
    flash('User approved successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/reject-user/<int:user_id>', methods=['POST'])
@login_required
def reject_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    user.approved = False
    user.rejected = True
    notification = Notification(user_id=user.id, message=f'Your {user.role} registration has been rejected by admin.')
    db.session.add(notification)
    db.session.commit()
    log_event('user_rejection', f'Rejected registration request for {user.email or user.username}.')
    flash('User registration request rejected.', 'warning')
    return redirect(url_for('admin_dashboard'))

@app.route('/upload-results', methods=['GET', 'POST'])
@login_required
def upload_results():
    if current_user.role != 'advisor':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        upload_type = request.form.get('upload_type', 'manual')
        
        if upload_type == 'csv':
            # Handle CSV file upload
            if 'csv_file' not in request.files:
                flash('No CSV file uploaded.', 'danger')
                return redirect(url_for('upload_results'))
            
            file = request.files['csv_file']
            if file.filename == '':
                flash('No file selected.', 'danger')
                return redirect(url_for('upload_results'))
            
            if not file.filename.endswith('.csv'):
                flash('Please upload a CSV file.', 'danger')
                return redirect(url_for('upload_results'))
            
            try:
                # Read CSV file
                df = pd.read_csv(file)
                
                # Validate required columns
                required_cols = ['student_id', 'subject', 'score', 'assessment_name']
                if not all(col in df.columns for col in required_cols):
                    flash(f'CSV must contain columns: {", ".join(required_cols)}', 'danger')
                    return redirect(url_for('upload_results'))
                
                # Process each row
                success_count = 0
                error_rows = []
                
                for idx, row in df.iterrows():
                    try:
                        student_id = int(row['student_id'])
                        subject = str(row['subject']).strip()
                        score = float(row['score'])
                        assessment_name = str(row['assessment_name']).strip()
                        
                        # Validate score range
                        if score < 0 or score > 100:
                            error_rows.append(f"Row {idx+2}: Score must be between 0-100")
                            continue
                        
                        # Check if student exists
                        student = Student.query.get(student_id)
                        if not student:
                            error_rows.append(f"Row {idx+2}: Student ID {student_id} not found")
                            continue
                        
                        # Add result
                        db.session.add(Result(
                            student_id=student_id,
                            subject=subject,
                            score=score,
                            assessment_name=assessment_name
                        ))
                        success_count += 1
                    
                    except ValueError as e:
                        error_rows.append(f"Row {idx+2}: Invalid data format - {str(e)}")
                
                # Commit all successful records
                if success_count > 0:
                    db.session.commit()
                    run_prediction_engine(db)
                    log_event('csv_upload', f'Uploaded {success_count} results from CSV.')
                    flash(f'✓ Successfully uploaded {success_count} results!', 'success')
                
                # Show any errors
                if error_rows:
                    error_msg = ' | '.join(error_rows[:5])
                    if len(error_rows) > 5:
                        error_msg += f' | ... and {len(error_rows)-5} more errors'
                    flash(f'⚠ Errors: {error_msg}', 'warning')
                
                return redirect(url_for('upload_results'))
            
            except Exception as e:
                db.session.rollback()
                flash(f'Error processing CSV: {str(e)}', 'danger')
                return redirect(url_for('upload_results'))
        
        else:
            # Handle manual single result entry
            try:
                student_id = int(request.form['student_id'])
                subject = request.form['subject'].strip()
                score = float(request.form['score'])
                assessment_name = request.form['assessment_name'].strip()
                
                # Validate inputs
                if score < 0 or score > 100:
                    flash('Score must be between 0 and 100.', 'danger')
                    return redirect(url_for('upload_results'))
                
                # Check if student exists
                student = Student.query.get(student_id)
                if not student:
                    flash('Student not found.', 'danger')
                    return redirect(url_for('upload_results'))
                
                db.session.add(Result(student_id=student_id, subject=subject, score=score, assessment_name=assessment_name))
                db.session.commit()
                run_prediction_engine(db)
                log_event('manual_upload', f'Uploaded result for student ID {student_id} in {subject}.')
                flash('Result uploaded and AI predictions updated.', 'success')
            
            except Exception as e:
                db.session.rollback()
                flash(f'Error adding result: {str(e)}', 'danger')
            
            return redirect(url_for('upload_results'))
    
    students = Student.query.all()
    recent_results = Result.query.order_by(Result.created_at.desc()).limit(10).all()
    return render_template('upload_results.html', students=students, recent_results=recent_results)

@app.route('/send-alert/<int:student_id>', methods=['POST'])
@login_required
def send_alert(student_id):
    if current_user.role != 'advisor':
        return redirect(url_for('index'))
    message = request.form.get('message', 'Your child needs support in the upcoming exams.')
    db.session.add(Alert(student_id=student_id, message=message))
    db.session.commit()
    log_event('send_alert', f'Sent alert for student ID {student_id}.')
    flash('Alert sent to parent and student.', 'success')
    return redirect(url_for('advisor_portal'))

@app.route('/dashboard/parent')
@login_required
def parent_portal():
    if current_user.role != 'parent':
        return redirect(url_for('index'))
    student = Student.query.first()
    alerts = Alert.query.order_by(Alert.created_at.desc()).limit(5).all()
    return render_template('parent_portal.html', student=student, alerts=alerts,
                           badge_class=get_badge_class(student.prediction))

@app.route('/dashboard/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    total_students = Student.query.count()
    total_teachers = User.query.filter_by(role='advisor', approved=True).count()
    pending_users = User.query.filter_by(approved=False).all()
    school_list = sorted({u.school_name for u in User.query.filter_by(role='advisor').all() if u.school_name})
    teachers = User.query.filter_by(role='advisor').all()
    failed_logins = SystemLog.query.filter_by(event_type='failed_login').order_by(SystemLog.timestamp.desc()).limit(5).all()
    risk_by_subject = db.session.query(Result.subject, db.func.count(Result.id)).group_by(Result.subject).all()
    logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).limit(10).all()
    all_students = User.query.filter_by(role='student').all()
    all_results = Result.query.all()
    return render_template('admin_dashboard.html', total_students=total_students,
                           total_teachers=total_teachers, pending_users=pending_users,
                           school_list=school_list, teachers=teachers, failed_logins=failed_logins,
                           risk_by_subject=risk_by_subject, logs=logs, all_students=all_students,
                           all_results=all_results)

if __name__ == '__main__':
    app.run(debug=True)
