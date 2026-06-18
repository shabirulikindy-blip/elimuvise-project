import csv
import io
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta
from functools import wraps

from .models import Alert, Notification, Result, Student, SystemLog
from .prediction_service import predict_student_outcome

User = get_user_model()

_admin_checked = False
_advisor_checked = False


def admin_session_required(view_func):
    """
    Decorator to enforce session timeout and admin-only access for dashboard views.
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        if not (request.user.role == 'admin' or request.user.is_staff):
            messages.error(request, 'Admin dashboard access is limited to admin accounts only.')
            return redirect('index')

        timeout_duration = timedelta(seconds=getattr(settings, 'ADMIN_SESSION_TIMEOUT', 60))
        last_activity = request.session.get('last_admin_activity')
        if last_activity:
            last_activity_time = timezone.datetime.fromisoformat(last_activity)
            if timezone.now() - last_activity_time > timeout_duration:
                auth_logout(request)
                messages.warning(request, 'Your admin session has expired. Please log in again.')
                return redirect('login')

        request.session['last_admin_activity'] = timezone.now().isoformat()
        request.session.modified = True
        return view_func(request, *args, **kwargs)

    return wrapped_view


def ensure_admin_exists():
    global _admin_checked
    if _admin_checked:
        return
    try:
        admin_user = User.objects.filter(username='ElimuVISE').first()
        if admin_user:
            if not admin_user.check_password('project2026') or not admin_user.is_superuser:
                admin_user.set_password('project2026')
                admin_user.is_superuser = True
                admin_user.is_staff = True
                admin_user.role = 'admin'
                admin_user.approved = True
                admin_user.save()
        else:
            User.objects.create_superuser(
                username='ElimuVISE',
                email='admin@example.com',
                password='project2026',
                role='admin',
                approved=True,
                first_name='System',
                last_name='Administrator'
            )
        _admin_checked = True
    except Exception:
        pass


def ensure_advisor_exists():
    global _advisor_checked
    if _advisor_checked:
        return
    try:
        advisor = User.objects.filter(Q(username__iexact='advisor@example.com') | Q(email__iexact='advisor@example.com')).first()
        if advisor:
            if not advisor.check_password('advisor123'):
                advisor.set_password('advisor123')
            advisor.role = 'advisor'
            advisor.approved = True
            advisor.rejected = False
            if not advisor.email:
                advisor.email = 'advisor@example.com'
            if not advisor.username:
                advisor.username = 'advisor@example.com'
            if not advisor.first_name:
                advisor.first_name = 'Advisor'
            if not advisor.last_name:
                advisor.last_name = 'User'
            advisor.save()
        else:
            User.objects.create_user(
                username='advisor@example.com',
                email='advisor@example.com',
                password='advisor123',
                role='advisor',
                approved=True,
                rejected=False,
                first_name='Advisor',
                last_name='User',
                school_name='ElimuVISE Academic Center'
            )
        _advisor_checked = True
    except Exception:
        pass


def home(request):
    ensure_admin_exists()
    ensure_advisor_exists()
    return render(request, 'home.html')


def login_view(request):
    ensure_admin_exists()
    ensure_advisor_exists()
    if request.method == 'POST':
        identifier = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = None
        if identifier:
            user = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier)).first()
            if user is None or not user.check_password(password):
                user = None
        if user is not None:
            # Check user approval status unless they are an admin/staff
            if not (user.is_superuser or user.is_staff or user.role == 'admin'):
                if user.rejected:
                    messages.error(request, 'Your registration request has been rejected by the administrator.')
                    return redirect('login')
                elif not user.approved:
                    messages.warning(request, 'Your registration is pending administrator approval. Please try again later.')
                    return redirect('login')
            
            auth_login(request, user)
            messages.success(request, 'Logged in successfully.')
            role = getattr(user, 'role', '')
            if role == 'advisor':
                return redirect('advisor_portal')
            elif role == 'parent':
                return redirect('parent_portal')
            elif role == 'student':
                return redirect('student_dashboard')
            elif role == 'admin' or user.is_staff:
                return redirect('admin_dashboard')
            else:
                return redirect('index')
        messages.error(request, 'Invalid credentials. Please try again.')
    return render(request, 'login.html')


def logout_view(request):
    auth_logout(request)
    return redirect('login')


def register(request):
    selected_role = request.GET.get('role', '')
    if request.method == 'POST':
        rule = request.POST.get('rule', '')
        if rule in ('student', 'admin'):
            if rule == 'student':
                messages.info(request, 'Students must be registered by an advisor. Please ask your advisor for a login account.')
            else:
                messages.error(request, 'Admin registration is not allowed.')
            return redirect('login')
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        phone = request.POST.get('phone', '').strip()
        home_address = request.POST.get('home_address', '').strip()
        school_name = request.POST.get('school_name', '').strip()
        subjects = request.POST.get('subjects', '').strip()
        username = request.POST.get('username', '').strip() or email
        if not email or not password or not name or not rule:
            messages.error(request, 'Please fill in all required fields before registering.')
            return redirect('register')
        if User.objects.filter(Q(username=username) | Q(email=email)).exists():
            messages.error(request, 'A user with that username or email already exists.')
            return redirect('register')
        first_name = name.strip().split(' ', 1)[0] if name else ''
        last_name = name.strip().split(' ', 1)[1] if name and ' ' in name else ''
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            home_address=home_address,
            role=rule,
            approved=False,
            rejected=False,
            registration_rule=rule,
            school_name=school_name,
            subjects=subjects,
            password=make_password(password),
        )
        user.save()
        SystemLog.objects.create(
            event_type='User Registration',
            description=f"New {user.role} registration: {user.name or user.username} ({user.email}). Pending approval."
        )
        messages.success(request, 'Registration successful! Your account has been created and is pending administrator approval. Once approved, you can log in.')
        return redirect('login')
    return render(request, 'register.html', {'selected_role': selected_role})


@login_required
def account_settings(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_profile':
            name = request.POST.get('name', request.user.name)
            first_name = name.strip().split(' ', 1)[0] if name else ''
            last_name = name.strip().split(' ', 1)[1] if name and ' ' in name else ''
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.email = request.POST.get('email', request.user.email)
            request.user.phone = request.POST.get('phone', request.user.phone)
            request.user.home_address = request.POST.get('home_address', request.user.home_address)
            request.user.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('account_settings')
        elif action == 'change_password':
            old_password = request.POST.get('old_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            if not request.user.check_password(old_password):
                messages.error(request, 'Current password is incorrect.')
            elif new_password != confirm_password:
                messages.error(request, 'New passwords do not match.')
            elif len(new_password) < 6:
                messages.error(request, 'New password must be at least 6 characters long.')
            else:
                request.user.set_password(new_password)
                request.user.save()
                messages.success(request, 'Password changed successfully. Please log in again.')
                return redirect('login')
    return render(request, 'account_settings.html')


@login_required
def parent_portal(request):
    if request.user.role != 'parent':
        messages.error(request, 'Parent portal access is limited to parent accounts only.')
        return redirect('index')

    student = Student.objects.select_related('user').first()
    if student is None:
        from types import SimpleNamespace
        student = SimpleNamespace(
            user=SimpleNamespace(name='No student assigned'),
            form_level='N/A',
            combination='N/A',
            prediction='N/A',
            attendance_rate=0,
        )
        badge_class = 'secondary'
    else:
        badge_class = 'danger' if student.prediction == 'At-Risk' else 'warning' if student.prediction == 'Average' else 'success'

    alerts = Alert.objects.order_by('-created_at')[:10]
    return render(request, 'parent_portal.html', {
        'student': student,
        'alerts': alerts,
        'badge_class': badge_class,
    })


@login_required
def student_dashboard(request):
    if request.user.role != 'student':
        messages.error(request, 'Student dashboard access is limited to student accounts only.')
        return redirect('index')

    student = getattr(request.user, 'student_profile', None)
    if student is None:
        messages.error(request, 'Student profile not found.')
        return redirect('index')

    results = Result.objects.filter(student=student).order_by('-created_at')
    alerts = Alert.objects.filter(student=student).order_by('-created_at')[:10]
    subject_breakdown = {}
    for result in results:
        subject_breakdown.setdefault(result.subject, []).append(result.score)
    subject_breakdown = {subject: sum(scores) / len(scores) for subject, scores in subject_breakdown.items()}
    study_tips = [
        'Review your top scoring subjects weekly.',
        'Ask your advisor for targeted help on weaker areas.',
        'Keep attendance above 90% for the best outcomes.',
    ]
    badge_class = 'danger' if student.prediction == 'At-Risk' else 'warning' if student.prediction == 'Average' else 'success'
    return render(request, 'student_dashboard.html', {
        'student': student,
        'results': results,
        'alerts': alerts,
        'subject_breakdown': subject_breakdown,
        'study_tips': study_tips,
        'badge_class': badge_class,
    })


@login_required
def advisor_portal(request):
    if request.user.role != 'advisor':
        messages.error(request, 'Advisor portal access is limited to advisor accounts only.')
        return redirect('index')

    total_students = Student.objects.count()
    at_risk = Student.objects.filter(prediction='At-Risk').count()
    average = Student.objects.filter(prediction='Average').count()
    recent_registered_students = Student.objects.select_related('user').order_by('-user__date_joined')[:10]
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
    priority_list = list(Student.objects.select_related('user').order_by('-attendance_rate')[:10])
    for student in priority_list:
        if student.risk_level == 'high':
            risk_level = 'high'
        elif student.risk_level == 'medium':
            risk_level = 'medium'
        else:
            risk_level = 'low'
        student.assessment = {
            'risk_level': risk_level,
            'concerns': ['Attendance below target', 'Improved support recommended'] if risk_level != 'low' else ['Consistent performance'],
            'strengths': ['Strong class participation', 'Improving assignment performance'],
            'interventions': ['Schedule a review meeting', 'Provide additional study resources'],
        }
    return render(request, 'advisor_portal.html', {
        'total_students': total_students,
        'at_risk': at_risk,
        'average': average,
        'recent_registered_students': recent_registered_students,
        'notifications': notifications,
        'priority_list': priority_list,
    })


@login_required
@require_POST
def advisor_register_student(request):
    if request.user.role != 'advisor':
        messages.error(request, 'Only advisors can register students.')
        return redirect('index')

    name = request.POST.get('name', '').strip()
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '').strip()
    form_level = request.POST.get('form_level', '').strip()
    combination = request.POST.get('combination', '').strip()

    if not name or not username or not password or not form_level or not combination:
        messages.error(request, 'Please fill in all required student registration fields.')
        return redirect('advisor_portal')

    if User.objects.filter(username__iexact=username).exists():
        messages.error(request, 'A user with this username already exists.')
        return redirect('advisor_portal')

    if email and User.objects.filter(email__iexact=email).exists():
        messages.error(request, 'A user with this email already exists.')
        return redirect('advisor_portal')

    first_name = name.split(' ', 1)[0]
    last_name = name.split(' ', 1)[1] if ' ' in name else ''

    student_user = User.objects.create_user(
        username=username,
        email=email or None,
        password=password,
        role='student',
        approved=True,
        rejected=False,
        registration_rule='student',
        school_name=request.user.school_name,
        first_name=first_name,
        last_name=last_name,
    )

    Student.objects.create(
        user=student_user,
        form_level=form_level,
        combination=combination,
        attendance_rate=0.0,
        prediction='Average',
        risk_level='average',
        study_hours_per_week=0.0,
        internet_access='Unknown',
        extracurricular='No',
    )

    Notification.objects.create(
        user=request.user,
        message=f'Student account created: {student_user.name or student_user.username} ({student_user.username}).',
    )
    SystemLog.objects.create(
        event_type='Student Registration',
        description=f'Advisor {request.user.username} registered student {student_user.username}.',
    )

    messages.success(
        request,
        f'Student registered successfully. Login username: {student_user.username}',
    )
    return redirect('advisor_portal')


@login_required
def upload_results(request):
    students = Student.objects.select_related('user').all()
    recent_results = Result.objects.select_related('student__user').order_by('-created_at')[:10]

    def apply_prediction(student, score_value, study_hours_value, attendance_value, internet_access, extracurricular):
        student.study_hours_per_week = study_hours_value
        student.attendance_rate = attendance_value
        student.internet_access = internet_access
        student.extracurricular = extracurricular

        prediction_input = {
            'study_hours_per_week': study_hours_value,
            'attendance_rate': attendance_value,
            'internet_access': internet_access,
            'extracurricular': extracurricular,
            'previous_score': score_value,
        }
        prediction_result = predict_student_outcome(prediction_input)
        student.prediction = prediction_result['risk_label']
        student.risk_level = (
            'high'
            if prediction_result['risk_label'] == 'At-Risk'
            else 'medium'
            if prediction_result['risk_label'] == 'Average'
            else 'low'
        )
        student.save()
        return prediction_result

    if request.method == 'POST':
        upload_type = request.POST.get('upload_type')
        if upload_type == 'manual':
            student_id = request.POST.get('student_id')
            subject = request.POST.get('subject', '').strip()
            score = request.POST.get('score')
            assessment_name = request.POST.get('assessment_name', '').strip()
            study_hours_per_week = request.POST.get('study_hours_per_week')
            attendance_rate = request.POST.get('attendance_rate')
            internet_access = request.POST.get('internet_access', '').strip()
            extracurricular = request.POST.get('extracurricular', '').strip()
            if (
                student_id
                and subject
                and score
                and assessment_name
                and study_hours_per_week
                and attendance_rate
                and internet_access
                and extracurricular
            ):
                student = Student.objects.filter(id=student_id).first()
                if student:
                    try:
                        score_value = float(score)
                        study_hours_value = float(study_hours_per_week)
                        attendance_value = float(attendance_rate)
                    except (TypeError, ValueError):
                        messages.error(request, 'Score, study hours, and attendance rate must be valid numbers.')
                        return redirect('upload_results')

                    Result.objects.create(
                        student=student,
                        subject=subject,
                        score=score_value,
                        assessment_name=assessment_name,
                    )

                    try:
                        prediction_result = apply_prediction(
                            student,
                            score_value,
                            study_hours_value,
                            attendance_value,
                            internet_access,
                            extracurricular,
                        )
                        messages.success(
                            request,
                            f"Result added and prediction updated ({prediction_result['risk_label']}, pass probability {prediction_result['probability_pass']:.2%}).",
                        )
                    except Exception as exc:
                        student.save()
                        messages.warning(
                            request,
                            f'Result saved, but prediction update failed: {exc}',
                        )
                else:
                    messages.error(request, 'Selected student was not found.')
            else:
                messages.error(request, 'Please fill in all required fields, including the five prediction inputs.')
        elif upload_type == 'csv':
            csv_file = request.FILES.get('csv_file')
            if not csv_file:
                messages.error(request, 'Please choose a CSV file before uploading.')
                return redirect('upload_results')

            try:
                decoded_csv = csv_file.read().decode('utf-8-sig')
            except UnicodeDecodeError:
                messages.error(request, 'Unable to read CSV file. Please save it as UTF-8 and try again.')
                return redirect('upload_results')

            reader = csv.DictReader(io.StringIO(decoded_csv))
            required_columns = {
                'student_id',
                'study_hours_per_week',
                'attendance_rate',
                'internet_access',
                'extracurricular',
                'previous_score',
            }
            file_columns = set(reader.fieldnames or [])
            missing_columns = sorted(required_columns - file_columns)
            if missing_columns:
                messages.error(
                    request,
                    f'Missing required CSV columns: {", ".join(missing_columns)}',
                )
                return redirect('upload_results')

            predicted_count = 0
            updated_student_count = 0
            external_only_count = 0
            failed_rows = []
            output_rows = []
            source_columns = list(reader.fieldnames or [])

            for row_index, row in enumerate(reader, start=2):
                output_row = {column: row.get(column, '') for column in source_columns}
                try:
                    student_id_value = str(row.get('student_id', '')).strip()
                    study_hours_raw = str(row.get('study_hours_per_week', '')).strip()
                    attendance_raw = str(row.get('attendance_rate', '')).strip()
                    internet_access = str(row.get('internet_access', '')).strip()
                    extracurricular = str(row.get('extracurricular', '')).strip()
                    previous_score_raw = str(row.get('previous_score', '')).strip()

                    if not student_id_value:
                        raise ValueError('student_id is required')
                    if not study_hours_raw or not attendance_raw or not internet_access or not extracurricular or not previous_score_raw:
                        raise ValueError('all five factors are required: study_hours_per_week, attendance_rate, internet_access, extracurricular, previous_score')

                    score_value = float(previous_score_raw)
                    study_hours_value = float(study_hours_raw)
                    attendance_value = float(attendance_raw)

                    student = None
                    if student_id_value.isdigit():
                        student = Student.objects.filter(id=int(student_id_value)).first()
                    if student is None:
                        student = Student.objects.filter(user__username__iexact=student_id_value).first()
                    if student is None:
                        student = Student.objects.filter(user__email__iexact=student_id_value).first()

                    try:
                        if student is not None:
                            prediction_result = apply_prediction(
                                student,
                                score_value,
                                study_hours_value,
                                attendance_value,
                                internet_access,
                                extracurricular,
                            )
                            updated_student_count += 1
                            output_row['matched_local_student'] = 'Yes'
                            output_row['matched_student_db_id'] = str(student.id)
                        else:
                            # Support external IDs (e.g. STU0001) by scoring without requiring a local Student record.
                            prediction_result = predict_student_outcome({
                                'study_hours_per_week': study_hours_value,
                                'attendance_rate': attendance_value,
                                'internet_access': internet_access,
                                'extracurricular': extracurricular,
                                'previous_score': score_value,
                            })
                            external_only_count += 1
                            output_row['matched_local_student'] = 'No'
                            output_row['matched_student_db_id'] = ''

                        output_row['probability_pass'] = str(prediction_result['probability_pass'])
                        output_row['predicted_label'] = prediction_result['predicted_label']
                        output_row['risk_label'] = prediction_result['risk_label']
                        output_row['error'] = ''
                        predicted_count += 1
                    except Exception as exc:
                        if student is not None:
                            student.save()
                        output_row['matched_local_student'] = 'No' if student is None else 'Yes'
                        output_row['matched_student_db_id'] = '' if student is None else str(student.id)
                        output_row['probability_pass'] = ''
                        output_row['predicted_label'] = ''
                        output_row['risk_label'] = ''
                        output_row['error'] = f'Prediction failed: {exc}'
                        failed_rows.append(f'Row {row_index}: prediction failed: {exc}')
                except Exception as exc:
                    failed_rows.append(f'Row {row_index}: {exc}')
                    output_row['matched_local_student'] = ''
                    output_row['matched_student_db_id'] = ''
                    output_row['probability_pass'] = ''
                    output_row['predicted_label'] = ''
                    output_row['risk_label'] = ''
                    output_row['error'] = str(exc)

                output_rows.append(output_row)

            if output_rows:
                output_buffer = io.StringIO()
                output_columns = source_columns + [
                    'matched_local_student',
                    'matched_student_db_id',
                    'probability_pass',
                    'predicted_label',
                    'risk_label',
                    'error',
                ]
                writer = csv.DictWriter(output_buffer, fieldnames=output_columns)
                writer.writeheader()
                writer.writerows(output_rows)

                response = HttpResponse(output_buffer.getvalue(), content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="elimuvise_predictions_output.csv"'
                response['X-ElimuVISE-CSV-Summary'] = (
                    f'processed={predicted_count};updated={updated_student_count};external={external_only_count};failed={len(failed_rows)}'
                )
                return response

            messages.info(request, 'CSV file had no data rows to import.')
        else:
            messages.error(request, 'Unknown upload type selected.')
        return redirect('upload_results')
    return render(request, 'upload_results.html', {
        'students': students,
        'recent_results': recent_results,
    })


@login_required
def send_alert(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        message_text = request.POST.get('message', 'Please schedule a meeting with your advisor to discuss academic support.')
        Alert.objects.create(student=student, message=message_text)
        if student.user:
            Notification.objects.create(user=student.user, message=message_text)
        messages.success(request, 'Alert has been sent.')
    return redirect('advisor_portal')


@admin_session_required
def admin_dashboard(request):
    pending_users = User.objects.filter(approved=False, rejected=False).order_by('date_joined')
    pending_advisors_count = pending_users.filter(role='advisor').count()
    pending_parents_count = pending_users.filter(role='parent').count()
    failed_logins = SystemLog.objects.filter(event_type='failed_login').order_by('-timestamp')[:10]
    school_list = list(User.objects.filter(school_name__isnull=False).values_list('school_name', flat=True).distinct())
    teachers = User.objects.filter(role='advisor')
    logs = SystemLog.objects.order_by('-timestamp')[:10]
    all_students = User.objects.filter(role='student')
    all_results = Result.objects.select_related('student__user').order_by('-created_at')[:10]
    
    total_students = Student.objects.count()
    total_teachers = User.objects.filter(role='advisor').count()
    
    return render(request, 'admin_dashboard.html', {
        'pending_users': pending_users,
        'pending_count': pending_users.count(),
        'pending_advisors_count': pending_advisors_count,
        'pending_parents_count': pending_parents_count,
        'failed_logins': failed_logins,
        'school_list': school_list,
        'teachers': teachers,
        'logs': logs,
        'all_students': all_students,
        'all_results': all_results,
        'total_students': total_students,
        'total_teachers': total_teachers,
    })


@admin_session_required
@require_POST
def approve_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.approved = True
    user.rejected = False
    user.save()
    SystemLog.objects.create(
        event_type='User Approved',
        description=f"User {user.name or user.username} ({user.role}) was approved by admin."
    )
    Notification.objects.create(
        user=user,
        message="Your registration request has been approved! You now have full access to ElimuVISE."
    )
    messages.success(request, 'User approved successfully.')
    return redirect('admin_dashboard')


@admin_session_required
@require_POST
def approve_all_advisors(request):
    pending_advisors = User.objects.filter(role='advisor', approved=False, rejected=False)
    approved_count = 0
    for user in pending_advisors:
        user.approved = True
        user.rejected = False
        user.save()
        Notification.objects.create(
            user=user,
            message='Your registration request has been approved! You now have full access to ElimuVISE.',
        )
        approved_count += 1

    SystemLog.objects.create(
        event_type='Bulk User Approval',
        description=f'Admin approved {approved_count} advisor account(s) in one action.',
    )
    messages.success(request, f'Approved {approved_count} advisor account(s).')
    return redirect('admin_dashboard')


@admin_session_required
@require_POST
def approve_all_parents(request):
    pending_parents = User.objects.filter(role='parent', approved=False, rejected=False)
    approved_count = 0
    for user in pending_parents:
        user.approved = True
        user.rejected = False
        user.save()
        Notification.objects.create(
            user=user,
            message='Your registration request has been approved! You now have full access to ElimuVISE.',
        )
        approved_count += 1

    SystemLog.objects.create(
        event_type='Bulk User Approval',
        description=f'Admin approved {approved_count} parent account(s) in one action.',
    )
    messages.success(request, f'Approved {approved_count} parent account(s).')
    return redirect('admin_dashboard')


@admin_session_required
@require_POST
def reject_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.rejected = True
    user.approved = False
    user.save()
    SystemLog.objects.create(
        event_type='User Rejected',
        description=f"User {user.name or user.username} ({user.role}) was rejected by admin."
    )
    messages.success(request, 'User rejected successfully.')
    return redirect('admin_dashboard')
