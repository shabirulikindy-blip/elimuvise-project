from django.contrib import messages
from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Alert, Notification, Result, Student, SystemLog

User = get_user_model()

_admin_checked = False


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


def home(request):
    ensure_admin_exists()
    return render(request, 'home.html')


def login_view(request):
    ensure_admin_exists()
    if request.method == 'POST':
        identifier = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = None
        if identifier:
            user = User.objects.filter(Q(username=identifier) | Q(email=identifier)).first()
            if user is None or not user.check_password(password):
                user = None
        if user is not None:
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
        messages.success(request, 'Your account has been created and is now pending approval.')
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
    total_students = Student.objects.count()
    at_risk = Student.objects.filter(prediction='At-Risk').count()
    average = Student.objects.filter(prediction='Average').count()
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
        'notifications': notifications,
        'priority_list': priority_list,
    })


@login_required
def upload_results(request):
    students = Student.objects.select_related('user').all()
    recent_results = Result.objects.select_related('student__user').order_by('-created_at')[:10]
    if request.method == 'POST':
        upload_type = request.POST.get('upload_type')
        if upload_type == 'manual':
            student_id = request.POST.get('student_id')
            subject = request.POST.get('subject', '').strip()
            score = request.POST.get('score')
            assessment_name = request.POST.get('assessment_name', '').strip()
            if student_id and subject and score and assessment_name:
                student = Student.objects.filter(id=student_id).first()
                if student:
                    Result.objects.create(
                        student=student,
                        subject=subject,
                        score=float(score),
                        assessment_name=assessment_name,
                    )
                    messages.success(request, 'Result added successfully.')
                else:
                    messages.error(request, 'Selected student was not found.')
            else:
                messages.error(request, 'Please fill in all required fields.')
        else:
            messages.info(request, 'CSV uploads are currently not supported in this preview.')
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


@login_required
def admin_dashboard(request):
    pending_users = User.objects.filter(approved=False, rejected=False)
    failed_logins = SystemLog.objects.filter(event_type='failed_login').order_by('-timestamp')[:10]
    school_list = list(User.objects.filter(school_name__isnull=False).values_list('school_name', flat=True).distinct())
    teachers = User.objects.filter(role='advisor')
    logs = SystemLog.objects.order_by('-timestamp')[:10]
    all_students = User.objects.filter(role='student')
    all_results = Result.objects.select_related('student__user').order_by('-created_at')[:10]
    return render(request, 'admin_dashboard.html', {
        'pending_users': pending_users,
        'failed_logins': failed_logins,
        'school_list': school_list,
        'teachers': teachers,
        'logs': logs,
        'all_students': all_students,
        'all_results': all_results,
    })


@login_required
@require_POST
def approve_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.approved = True
    user.rejected = False
    user.save()
    messages.success(request, 'User approved successfully.')
    return redirect('admin_dashboard')


@login_required
@require_POST
def reject_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.rejected = True
    user.approved = False
    user.save()
    messages.success(request, 'User rejected successfully.')
    return redirect('admin_dashboard')
