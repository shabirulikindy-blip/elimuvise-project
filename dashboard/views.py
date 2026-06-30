import csv
import io
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta
from functools import wraps

from .models import Alert, Notification, Result, Student, SystemLog, School, UploadedFile, AdvisoryNote
from .prediction_service import predict_student_outcome
from .advisory_service import get_student_advisory_data, prioritize_students


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
    
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    if request.method == 'GET':
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'GET method not allowed for login AJAX.'}, status=405)
        next_url = request.GET.get('next', '')
        redirect_url = '/?auth=login'
        if next_url:
            redirect_url += f'&next={next_url}'
        return redirect(redirect_url)

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
                    error_msg = 'Your registration request has been rejected by the administrator.'
                    return JsonResponse({'success': False, 'message': error_msg}, status=403)
                elif not user.approved:
                    warn_msg = 'Your registration is pending administrator approval. Please try again later.'
                    return JsonResponse({'success': False, 'message': warn_msg}, status=403)
            
            auth_login(request, user)
            
            # Determine redirect URL
            role = getattr(user, 'role', '')
            next_url = request.POST.get('next', '') or request.GET.get('next', '')
            if next_url:
                redirect_url = next_url
            elif role == 'advisor':
                redirect_url = '/advisor/portal/'
            elif role == 'parent':
                redirect_url = '/parent/portal/'
            elif role == 'student':
                redirect_url = '/student/dashboard/'
            elif role == 'admin' or user.is_staff:
                redirect_url = '/platform/admin-dashboard/'
            else:
                redirect_url = '/'
                
            return JsonResponse({'success': True, 'redirect_url': redirect_url})
            
        error_msg = 'Invalid credentials. Please try again.'
        return JsonResponse({'success': False, 'message': error_msg}, status=400)
        
    return render(request, 'login.html')


def logout_view(request):
    auth_logout(request)
    return redirect('login')


def register(request):
    selected_role = request.GET.get('role', '')
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    if request.method == 'GET':
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'GET method not allowed for registration AJAX.'}, status=405)
        redirect_url = '/?auth=register'
        if selected_role:
            redirect_url += f'&role={selected_role}'
        return redirect(redirect_url)
        
    if request.method == 'POST':
        rule = request.POST.get('rule', '')
        if rule in ('student', 'admin'):
            if rule == 'student':
                msg = 'Students must be registered by an advisor. Please ask your advisor for a login account.'
            else:
                msg = 'Admin registration is not allowed.'
            
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.info(request, msg)
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
            msg = 'Please fill in all required fields before registering.'
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('register')
            
        if User.objects.filter(Q(username=username) | Q(email=email)).exists():
            msg = 'A user with that username or email already exists.'
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('register')
            
        first_name = name.strip().split(' ', 1)[0] if name else ''
        last_name = name.strip().split(' ', 1)[1] if name and ' ' in name else ''
        
        try:
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

            # Child linking is handled exclusively by advisors.
            pass
            
            SystemLog.objects.create(
                event_type='User Registration',
                description=f"New {user.role} registration: {user.name or user.username} ({user.email}). Pending approval."
            )

            
            success_msg = 'Successfully registered! Please wait for admin approval.'
            if is_ajax:
                return JsonResponse({'success': True, 'message': success_msg})
            messages.success(request, success_msg)
            return redirect('login')
            
        except Exception as e:
            msg = f'Registration failed: {str(e)}'
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('register')
            
    schools = School.objects.filter(is_active=True).order_by('name')
    return render(request, 'register.html', {
        'selected_role': selected_role,
        'schools': schools,
    })



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

    students = Student.objects.filter(parent=request.user).select_related('user')
    
    if students.exists():
        selected_student_id = request.GET.get('student_id')
        student = None
        if selected_student_id:
            try:
                student = students.get(id=selected_student_id)
            except (Student.DoesNotExist, ValueError):
                pass
        if not student:
            student = students.first()

        advisory_res = get_student_advisory_data(student)
        parent_advisory = advisory_res["parent_data"]
        badge_class = advisory_res["badge_class"]
        alerts = Alert.objects.filter(student=student).order_by('-created_at')[:10]
        
        # Get primary advisor for this school dynamically
        primary_advisor = None
        school_name = student.user.school_name
        if school_name:
            primary_advisor = User.objects.filter(role='advisor', school_name=school_name, is_school_advisor=True).first()
            if not primary_advisor:
                primary_advisor = User.objects.filter(role='advisor', school_name=school_name).first()

        results = Result.objects.filter(student=student).order_by('-created_at')
        
        # Calculate academic trends dynamically from all student results
        from django.db.models import Avg
        all_results = Result.objects.filter(student=student).order_by('created_at')
        trend_results = []
        seen_assessments = set()
        for r in all_results:
            name = r.assessment_name
            if name not in seen_assessments:
                seen_assessments.add(name)
                avg_score = all_results.filter(assessment_name=name).aggregate(Avg('score'))['score__avg']
                trend_results.append({
                    'assessment_name': name,
                    'score': round(avg_score, 1) if avg_score is not None else 0
                })

        subject_breakdown = {}
        for result in results:
            subject_breakdown.setdefault(result.subject, []).append(result.score)
        subject_breakdown = {subject: sum(scores) / len(scores) for subject, scores in subject_breakdown.items()}

        return render(request, 'parent_portal.html', {
            'student': student,
            'linked_students': students,
            'alerts': alerts,
            'badge_class': badge_class,
            'parent_advisory': parent_advisory,
            'child_linked': True,
            'trend_results': trend_results,
            'subject_breakdown': subject_breakdown,
            'primary_advisor': primary_advisor,
        })
    else:
        return render(request, 'parent_portal.html', {
            'child_linked': False,
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
    
    # Calculate academic trends dynamically from all student results
    from django.db.models import Avg
    all_results = Result.objects.filter(student=student).order_by('created_at')
    trend_results = []
    seen_assessments = set()
    for r in all_results:
        name = r.assessment_name
        if name not in seen_assessments:
            seen_assessments.add(name)
            avg_score = all_results.filter(assessment_name=name).aggregate(Avg('score'))['score__avg']
            trend_results.append({
                'assessment_name': name,
                'score': round(avg_score, 1) if avg_score is not None else 0
            })

    alerts = Alert.objects.filter(student=student).order_by('-created_at')[:10]
    subject_breakdown = {}
    for result in results:
        subject_breakdown.setdefault(result.subject, []).append(result.score)
    subject_breakdown = {subject: sum(scores) / len(scores) for subject, scores in subject_breakdown.items()}
    
    advisory = get_student_advisory_data(student)
    student_advisory = advisory["student_data"]
    badge_class = advisory["badge_class"]
    
    return render(request, 'student_dashboard.html', {
        'student': student,
        'results': results,
        'trend_results': trend_results,
        'alerts': alerts,
        'subject_breakdown': subject_breakdown,
        'student_advisory': student_advisory,
        'badge_class': badge_class,
        'advisory': advisory,
    })



@login_required
def advisor_portal(request):
    if request.user.role != 'advisor':
        messages.error(request, 'Advisor portal access is limited to advisor accounts only.')
        return redirect('index')

    school_name = request.user.school_name
    total_students = Student.objects.filter(user__school_name=school_name).count()
    at_risk = Student.objects.filter(user__school_name=school_name, prediction='At-Risk').count()
    average = Student.objects.filter(user__school_name=school_name, prediction='Average').count()
    recent_registered_students = Student.objects.filter(user__school_name=school_name).select_related('user').order_by('-user__date_joined')[:10]
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    students_qs = Student.objects.filter(user__school_name=school_name).select_related('user')
    priority_list = prioritize_students(students_qs)[:10]
    for student in priority_list:
        student.assessment = student.advisory_data["advisor_data"]
        
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
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true'

    if request.user.role != 'advisor':
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'Only advisors can register students.'}, status=403)
        messages.error(request, 'Only advisors can register students.')
        return redirect('index')

    name = request.POST.get('name', '').strip()
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '').strip()
    form_level = request.POST.get('form_level', '').strip()
    combination = request.POST.get('combination', '').strip()

    if not name or not username or not password or not form_level or not combination:
        error_msg = 'Please fill in all required student registration fields.'
        if is_ajax:
            return JsonResponse({'success': False, 'message': error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect('advisor_portal')

    if User.objects.filter(username__iexact=username).exists():
        error_msg = 'A user with this username already exists.'
        if is_ajax:
            return JsonResponse({'success': False, 'message': error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect('advisor_portal')

    if email and User.objects.filter(email__iexact=email).exists():
        error_msg = 'A user with this email already exists.'
        if is_ajax:
            return JsonResponse({'success': False, 'message': error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect('advisor_portal')

    first_name = name.split(' ', 1)[0]
    last_name = name.split(' ', 1)[1] if ' ' in name else ''

    try:
        student_user = User(
            username=username,
            role='student',
            approved=True,
            rejected=False,
            registration_rule='student',
            school_name=request.user.school_name,
            first_name=first_name,
            last_name=last_name,
        )
        if email:
            student_user.email = User.objects.normalize_email(email)
        else:
            student_user.email = None
        student_user.set_password(password)
        student_user.save()

        student = Student.objects.create(
            user=student_user,
            form_level=form_level,
            combination=combination,
            temp_password=password,
            attendance_rate=0.0,
            prediction='Average',
            risk_level='average',
            study_hours_per_week=0.0,
            internet_access='Unknown',
            extracurricular='No',
        )
    except Exception as e:
        error_msg = f"Failed to create student: {str(e)}"
        if is_ajax:
            return JsonResponse({'success': False, 'message': error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect('advisor_portal')

    Notification.objects.create(
        user=request.user,
        message=f'Student account created: {student_user.name or student_user.username} ({student_user.username}).',
    )
    SystemLog.objects.create(
        event_type='Student Registration',
        description=f'Advisor {request.user.username} registered student {student_user.username}.',
    )

    success_msg = f'Student registered successfully. Login username: {student_user.username}'
    if is_ajax:
        return JsonResponse({
            'success': True,
            'message': success_msg,
            'student': {
                'id': student.id,
                'name': student_user.name or student_user.username,
                'username': student_user.username,
                'temp_password': student.temp_password,
                'form_level': student.form_level,
                'combination': student.combination,
                'date_joined': student_user.date_joined.strftime('%b %d, %Y %H:%M'),
                'prediction': student.prediction,
            }
        })

    messages.success(request, success_msg)
    return redirect('advisor_portal')


@login_required
def upload_results(request):
    if request.user.role not in ['advisor', 'admin']:
        messages.error(request, 'Access denied.')
        return redirect('index')

    if request.user.role == 'advisor':
        profile = getattr(request.user, 'advisor_profile', None)
        if profile and not profile.can_edit:
            messages.error(request, 'You do not have permission to upload results.')
            return redirect('advisor_portal')

    is_main_advisor = True
    
    if request.user.role == 'advisor':
        school_name = request.user.school_name
        students = Student.objects.filter(user__school_name=school_name).select_related('user')
        recent_results = Result.objects.filter(student__user__school_name=school_name).select_related('student__user').order_by('-created_at')[:10]
    else:
        students = Student.objects.select_related('user').all()
        recent_results = Result.objects.select_related('student__user').order_by('-created_at')[:10]

    def apply_prediction(student, score_value, study_hours_value, attendance_value, internet_access, extracurricular, gender=None, age=None, parent_education=None):
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
        if gender:
            student.gender = gender
            prediction_input['gender'] = gender
        if age is not None:
            student.age = age
            prediction_input['age'] = age
        if parent_education:
            student.parent_education = parent_education
            prediction_input['parent_education'] = parent_education

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
        if upload_type != 'manual' and not is_main_advisor:
            messages.error(request, 'Only main advisors can upload CSV files.')
            return redirect('upload_results')
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
                if request.user.role == 'advisor':
                    student = Student.objects.filter(id=student_id, user__school_name=request.user.school_name).first()
                else:
                    student = Student.objects.filter(id=student_id).first()
                if student:
                    try:
                        score_value = float(score)
                        study_hours_value = float(study_hours_per_week)
                        attendance_value = float(attendance_rate)
                    except (TypeError, ValueError):
                        messages.error(request, 'Score, study hours, and attendance rate must be valid numbers.')
                        return redirect('upload_results')

                    # Permission check for assistant advisors
                    if request.user.role == 'advisor':
                        profile = getattr(request.user, 'advisor_profile', None)
                        if profile and not profile.can_edit:
                            messages.error(request, 'Assistant advisors cannot edit results.')
                            return redirect('advisor_portal')
                    # Create Result entry
                    Result.objects.create(
                        student=student,
                        subject=subject,
                        score=score_value,
                        assessment_name=assessment_name,
                        uploaded_file=UploadedFile.objects.get(id=upload_type) if upload_type.isdigit() else None,
                        edited_by=request.user,
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
                        # Store AI prediction in Result (risk detection only)
                        result = Result.objects.filter(student=student, subject=subject, assessment_name=assessment_name).last()
                        if result:
                            result.ai_prediction = {
                                'risk_label': prediction_result['risk_label'],
                                'probability_pass': prediction_result['probability_pass'],
                            }
                            result.ai_recommendation = _ai_suggestion_text(prediction_result['risk_label'], prediction_result['probability_pass'])
                            result.save()

                        # Send notification to all advisors of the student's school
                        advisors = User.objects.filter(role='advisor', school_name=student.user.school_name)
                        for adv in advisors:
                            Notification.objects.create(
                                user=adv,
                                message=f"AI Prediction: Student {student.user.name or student.user.username} is predicted to be '{student.prediction}' after result upload by {request.user.username}."
                            )

                        messages.success(
                            request,
                            f"Result added and risk detection updated ({prediction_result['risk_label']}, pass probability {prediction_result['probability_pass']:.2%}).",
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
        else:
            # Existing CSV processing continues here, using uploaded_file_record
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
                'gender',
                'age',
                'study_hours',
                'attendance',
                'parent_education',
                'internet_access',
                'extracurricular',
                'previous_score',
                'final_score',
                'passed',
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
            failed_rows = []

            for row_index, row in enumerate(reader, start=2):
                try:
                    student_id_value = str(row.get('student_id', '')).strip()
                    gender = str(row.get('gender', '')).strip()
                    age_raw = str(row.get('age', '')).strip()
                    study_hours_raw = str(row.get('study_hours', '')).strip()
                    attendance_raw = str(row.get('attendance', '')).strip()
                    parent_education = str(row.get('parent_education', '')).strip()
                    internet_access = str(row.get('internet_access', '')).strip()
                    extracurricular = str(row.get('extracurricular', '')).strip()
                    previous_score_raw = str(row.get('previous_score', '')).strip()

                    if not student_id_value:
                        raise ValueError('student_id is required')
                    if not study_hours_raw or not attendance_raw or not internet_access or not extracurricular or not previous_score_raw:
                        raise ValueError('study_hours, attendance, internet_access, extracurricular, previous_score are required')

                    score_value = float(previous_score_raw)
                    study_hours_value = float(study_hours_raw)
                    attendance_value = float(attendance_raw)
                    age_value = float(age_raw) if age_raw else None

                    student = None
                    if request.user.role == 'advisor':
                        school_name = request.user.school_name
                        if student_id_value.isdigit():
                            student = Student.objects.filter(id=int(student_id_value), user__school_name=school_name).first()
                        if student is None:
                            student = Student.objects.filter(user__username__iexact=student_id_value, user__school_name=school_name).first()
                        if student is None:
                            student = Student.objects.filter(user__email__iexact=student_id_value, user__school_name=school_name).first()
                    else:
                        if student_id_value.isdigit():
                            student = Student.objects.filter(id=int(student_id_value)).first()
                        if student is None:
                            student = Student.objects.filter(user__username__iexact=student_id_value).first()
                        if student is None:
                            student = Student.objects.filter(user__email__iexact=student_id_value).first()

                    if student is None:
                        # Auto register new student user
                        final_username = student_id_value
                        if User.objects.filter(username__iexact=final_username).exists():
                            suffix = str(request.user.school_name or "school").replace(" ", "_").lower()
                            final_username = f"{student_id_value}_{suffix}"
                            counter = 1
                            base_username = final_username
                            while User.objects.filter(username__iexact=final_username).exists():
                                final_username = f"{base_username}_{counter}"
                                counter += 1

                        user = User.objects.create(
                            username=final_username,
                            role='student',
                            school_name=request.user.school_name,
                            school=request.user.school,
                            approved=True
                        )
                        user.set_password("123456")
                        user.save()
                        student = Student.objects.create(
                            user=user,
                            form_level='Form 4',
                            combination='PCM',
                        )

                    try:
                        prediction_result = apply_prediction(
                            student,
                            score_value,
                            study_hours_value,
                            attendance_value,
                            internet_access,
                            extracurricular,
                            gender=gender,
                            age=age_value,
                            parent_education=parent_education,
                        )

                        # Create or update Previous Exam Result
                        Result.objects.update_or_create(
                            student=student,
                            subject='All Subjects (Previous)',
                            assessment_name='Previous Score',
                            defaults={'score': score_value, 'edited_by': request.user}
                        )

                        # Create or update Final Exam Result if final_score is present
                        try:
                            final_score_raw = str(row.get('final_score', '')).strip()
                            if final_score_raw:
                                final_score_value = float(final_score_raw)
                                Result.objects.update_or_create(
                                    student=student,
                                    subject='All Subjects (Final)',
                                    assessment_name='Final Score',
                                    defaults={'score': final_score_value, 'edited_by': request.user}
                                )
                        except ValueError:
                            pass

                        updated_student_count += 1
                        predicted_count += 1
                    except Exception as exc:
                        failed_rows.append(f'Row {row_index} prediction failed: {exc}')
                except Exception as exc:
                    failed_rows.append(f'Row {row_index} error: {exc}')

            if updated_student_count > 0:
                advisors = User.objects.filter(role='advisor', school_name=request.user.school_name)
                for adv in advisors:
                    Notification.objects.create(
                        user=adv,
                        message=f"AI Prediction: {updated_student_count} student records updated and predicted after CSV upload by {request.user.username}."
                    )
                messages.success(request, f'Results uploaded successfully. {updated_student_count} student records imported/updated and predicted.')
            else:
                messages.warning(request, 'No student records were updated. Errors: ' + '; '.join(failed_rows[:5]))

            return redirect('advisor_school_records')
        # If CSV processing didn't return a response, redirect back
        return redirect('upload_results')
    return render(request, 'upload_results.html', {
        'students': students,
        'recent_results': recent_results,
    })


@login_required
def send_alert(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.user.role == 'advisor' and student.user.school_name != request.user.school_name:
        messages.error(request, 'Permission denied. Student belongs to another school.')
        return redirect('advisor_portal')
    if request.method == 'POST':
        message_text = request.POST.get('message', 'Please schedule a meeting with your advisor to discuss academic support.')
        Alert.objects.create(student=student, message=message_text)
        if student.user:
            Notification.objects.create(user=student.user, message=message_text)
        messages.success(request, 'Alert has been sent.')
    return redirect('advisor_portal')


@login_required
@require_POST
def edit_student_inline(request):
    # Allows advisors (main or assistants with edit permission) to edit attendance and trigger AI prediction.
    student_id = request.POST.get('student_id')
    attendance_rate = request.POST.get('attendance_rate')
    if not student_id or not attendance_rate:
        return JsonResponse({'error': 'Missing parameters.'}, status=400)
    # Permission check
    if request.user.role != 'advisor':
        return JsonResponse({'error': 'Only advisors can edit student data.'}, status=403)
    profile = getattr(request.user, 'advisor_profile', None)
    if profile and not profile.is_main and not profile.can_edit:
        return JsonResponse({'error': 'Assistant advisors lack edit permission.'}, status=403)
    try:
        student = Student.objects.get(id=student_id)
        if student.user.school_name != request.user.school_name:
            return JsonResponse({'error': 'Permission denied. Student belongs to another school.'}, status=403)
        student.attendance_rate = float(attendance_rate)
        # Run prediction using current student data
        prediction_input = {
            'study_hours_per_week': student.study_hours_per_week,
            'attendance_rate': student.attendance_rate,
            'internet_access': student.internet_access,
            'extracurricular': student.extracurricular,
            'previous_score': student.results.last().score if student.results.exists() else 0,
        }
        prediction_result = predict_student_outcome(prediction_input)
        student.prediction = prediction_result['risk_label']
        student.risk_level = (
            'high' if prediction_result['risk_label'] == 'At-Risk' else
            'medium' if prediction_result['risk_label'] == 'Average' else
            'low'
        )
        student.save()
        # Notify all advisors of the same school (excluding the editor)
        advisor_qs = User.objects.filter(role='advisor', school_name=request.user.school_name).exclude(id=request.user.id)
        notification_msg = f"Attendance updated for {student.user.name or student.user.username}. New risk: {student.prediction}."
        for adv in advisor_qs:
            Notification.objects.create(user=adv, message=notification_msg)
            # Optional email notification if email is set
            if adv.email:
                from django.core.mail import send_mail
                send_mail(
                    subject='Student Attendance Updated',
                    message=notification_msg,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                    recipient_list=[adv.email],
                    fail_silently=True,
                )
        return JsonResponse({'risk_label': student.prediction})
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'User approved successfully.'})
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


# ─────────────────────────────────────────────────────────
# ADMIN – SCHOOL BROWSER
# ─────────────────────────────────────────────────────────

def _get_or_create_school_from_name(school_name, registered_by=None):
    """Helper to ensure a School record exists for any school_name string."""
    if not school_name:
        return None
    school, _ = School.objects.get_or_create(
        name=school_name,
        defaults={'registered_by': registered_by, 'is_active': True}
    )
    return school


@admin_session_required
def admin_schools(request):
    """Show searchable list of all schools registered in the system."""
    # Auto-sync: create School records from any school_name on User objects
    existing_names = School.objects.values_list('name', flat=True)
    for sname in User.objects.exclude(school_name__isnull=True).exclude(school_name='') \
                              .values_list('school_name', flat=True).distinct():
        if sname not in existing_names:
            School.objects.get_or_create(name=sname)

    q = request.GET.get('q', '').strip()
    schools_qs = School.objects.filter(is_active=True)
    if q:
        schools_qs = schools_qs.filter(name__icontains=q)

    school_data = []
    for school in schools_qs:
        advisors = User.objects.filter(role='advisor', school_name=school.name, approved=True)
        students = Student.objects.filter(user__school_name=school.name)
        f56_students = students.filter(form_level__in=['Form 5', 'Form 6'])
        primary = advisors.filter(is_school_advisor=True).first()
        school_data.append({
            'school': school,
            'advisor_count': advisors.count(),
            'student_count': students.count(),
            'f56_count': f56_students.count(),
            'primary_advisor': primary,
        })

    return render(request, 'admin_schools.html', {
        'school_data': school_data,
        'q': q,
        'total_schools': School.objects.filter(is_active=True).count(),
    })


@admin_session_required
def admin_school_detail(request, school_id):
    """Detailed view for a specific school — students, advisors, permissions, register advisor."""
    school = get_object_or_404(School, id=school_id)

    # All Form 5 & 6 students for this school
    f56_students = Student.objects.filter(
        user__school_name=school.name,
        form_level__in=['Form 5', 'Form 6']
    ).select_related('user').prefetch_related('results')

    # All advisors for this school
    advisors = User.objects.filter(role='advisor', school_name=school.name).order_by('-is_school_advisor', 'username')

    # Parents linked to this school
    parents = User.objects.filter(role='parent', school_name=school.name, approved=True)

    # Pending users for this school
    pending = User.objects.filter(school_name=school.name, approved=False, rejected=False)

    # Recent activity logs
    logs = SystemLog.objects.filter(school_name=school.name).order_by('-timestamp')[:20]

    # Upload history
    uploads = UploadedFile.objects.filter(school_name=school.name).select_related('uploaded_by')[:20]

    return render(request, 'admin_school_detail.html', {
        'school': school,
        'f56_students': f56_students,
        'advisors': advisors,
        'parents': parents,
        'pending': pending,
        'logs': logs,
        'uploads': uploads,
    })


@login_required
@require_POST
def admin_grant_permission(request, user_id):
    """Toggle upload/edit/approve permissions for an advisor (single toggle or bulk checkboxes)."""
    # Check authorization: must be admin OR a primary advisor for the same school
    is_admin = request.user.role == 'admin' or request.user.is_staff
    is_primary_advisor = request.user.role == 'advisor' and request.user.is_school_advisor

    if not (is_admin or is_primary_advisor):
        messages.error(request, 'You do not have permission to manage advisor permissions.')
        return redirect('index')

    user = get_object_or_404(User, id=user_id, role='advisor')

    # If primary advisor, must be same school and cannot modify themselves
    if is_primary_advisor:
        if user.school_name != request.user.school_name:
            messages.error(request, 'You can only manage advisor permissions for your own school.')
            return redirect('advisor_school_records')
        if user.id == request.user.id:
            messages.error(request, 'You cannot modify your own permissions.')
            return redirect('advisor_school_records')

    actor_str = "Admin" if is_admin else f"Primary Advisor {request.user.username}"
    perm = request.POST.get('permission')
    if perm:
        # Backward compatibility for single toggle
        value = request.POST.get('value', '0') == '1'
        allowed = {'can_upload', 'can_edit_records', 'can_approve_users', 'is_school_advisor'}
        if perm not in allowed:
            return JsonResponse({'success': False, 'message': 'Invalid permission.'}, status=400)

        setattr(user, perm, value)
        user.save(update_fields=[perm])

        action_str = 'granted' if value else 'revoked'
        action_desc = f"{actor_str} {action_str} '{perm}' for {user.username} ({user.school_name})."
        msg = f"'{perm}' {action_str} for {user.username}."
    else:
        # Bulk update from checkboxes
        is_school_advisor = request.POST.get('is_school_advisor') == '1'
        can_upload = request.POST.get('can_upload') == '1'
        can_edit_records = request.POST.get('can_edit_records') == '1'
        can_approve_users = request.POST.get('can_approve_users') == '1'

        user.is_school_advisor = is_school_advisor
        user.can_upload = can_upload
        user.can_edit_records = can_edit_records
        user.can_approve_users = can_approve_users
        user.save(update_fields=['is_school_advisor', 'can_upload', 'can_edit_records', 'can_approve_users'])

        action_desc = (
            f"{actor_str} updated permissions for {user.username} ({user.school_name}): "
            f"Primary={is_school_advisor}, Upload={can_upload}, Edit/AI={can_edit_records}, Approve={can_approve_users}."
        )
        msg = f"Permissions updated successfully for {user.name or user.username}."

    SystemLog.objects.create(
        event_type='Permission Change',
        description=action_desc,
        school_name=user.school_name,
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': msg})

    from django.contrib import messages
    messages.success(request, msg)

    if is_primary_advisor:
        return redirect('advisor_school_records')

    school_id = request.POST.get('school_id')
    if school_id:
        return redirect('admin_school_detail', school_id=school_id)
    return redirect('admin_schools')


@admin_session_required
@require_POST
def admin_register_advisor(request):
    """Admin registers a new school-level advisor for a specific school."""
    name = request.POST.get('name', '').strip()
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '').strip()
    phone = request.POST.get('phone', '').strip()
    school_name = request.POST.get('school_name', '').strip()
    is_primary = request.POST.get('is_school_advisor', '0') == '1'
    school_id = request.POST.get('school_id', '')

    if not all([name, username, password, school_name]):
        messages.error(request, 'Name, username, password, and school name are required.')
        if school_id:
            return redirect('admin_school_detail', school_id=school_id)
        return redirect('admin_schools')

    if User.objects.filter(username=username).exists():
        messages.error(request, f'Username "{username}" already taken.')
        if school_id:
            return redirect('admin_school_detail', school_id=school_id)
        return redirect('admin_schools')

    first_name = name.split(' ', 1)[0]
    last_name = name.split(' ', 1)[1] if ' ' in name else ''

    new_advisor = User(
        username=username,
        first_name=first_name,
        last_name=last_name,
        role='advisor',
        approved=True,
        school_name=school_name,
        phone=phone,
        is_school_advisor=is_primary,
        can_approve_users=is_primary,
    )
    if email:
        new_advisor.email = email
    new_advisor.set_password(password)
    new_advisor.save()

    # Ensure school record exists
    school = _get_or_create_school_from_name(school_name, registered_by=request.user)
    if school_id and not school.id == int(school_id):
        # Use the existing school by ID
        school = get_object_or_404(School, id=school_id)

    SystemLog.objects.create(
        event_type='Advisor Registered',
        description=f"Admin registered advisor {username} for {school_name}.",
        school_name=school_name,
    )
    Notification.objects.create(
        user=new_advisor,
        message=f"Your advisor account for {school_name} has been created by Admin.",
    )
    messages.success(request, f'Advisor "{username}" registered successfully for {school_name}.')

    if school_id:
        return redirect('admin_school_detail', school_id=school_id)
    return redirect('admin_schools')


@admin_session_required
@require_POST
def admin_edit_student(request, student_id):
    """Admin edits a student's profile fields directly."""
    student = get_object_or_404(Student, id=student_id)
    user = student.user

    # Update User fields
    full_name = request.POST.get('name', '').strip()
    if full_name:
        user.first_name = full_name.split(' ', 1)[0]
        user.last_name = full_name.split(' ', 1)[1] if ' ' in full_name else ''
    phone = request.POST.get('phone', '').strip()
    if phone:
        user.phone = phone
    email = request.POST.get('email', '').strip()
    if email:
        user.email = email
    user.save()

    # Update Student fields
    form_level = request.POST.get('form_level', '').strip()
    if form_level:
        student.form_level = form_level
    combination = request.POST.get('combination', '').strip()
    if combination:
        student.combination = combination
    try:
        student.study_hours_per_week = float(request.POST.get('study_hours_per_week', student.study_hours_per_week))
        student.attendance_rate = float(request.POST.get('attendance_rate', student.attendance_rate))
    except (TypeError, ValueError):
        pass
    student.internet_access = request.POST.get('internet_access', student.internet_access)
    student.extracurricular = request.POST.get('extracurricular', student.extracurricular)
    student.save()

    SystemLog.objects.create(
        event_type='Student Record Edited',
        description=f"Admin edited student {user.username} ({student.form_level}).",
        school_name=user.school_name,
    )

    school_id = request.POST.get('school_id', '')
    if school_id:
        return redirect('admin_school_detail', school_id=school_id)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Student updated.'})
    messages.success(request, f'Student {user.username} updated.')
    return redirect('admin_schools')


@admin_session_required
@require_POST
def admin_edit_advisor(request, user_id):
    """Admin edits an advisor's profile fields directly."""
    user = get_object_or_404(User, id=user_id, role='advisor')

    full_name = request.POST.get('name', '').strip()
    if full_name:
        user.first_name = full_name.split(' ', 1)[0]
        user.last_name = full_name.split(' ', 1)[1] if ' ' in full_name else ''
    phone = request.POST.get('phone', '').strip()
    if phone:
        user.phone = phone
    email = request.POST.get('email', '').strip()
    if email:
        user.email = email
    subjects = request.POST.get('subjects', '').strip()
    if subjects:
        user.subjects = subjects
    user.save()

    SystemLog.objects.create(
        event_type='Advisor Record Edited',
        description=f"Admin edited advisor {user.username} ({user.school_name}).",
        school_name=user.school_name,
    )

    school_id = request.POST.get('school_id', '')
    if school_id:
        return redirect('admin_school_detail', school_id=school_id)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Advisor updated.'})
    messages.success(request, f'Advisor {user.username} updated.')
    return redirect('admin_schools')


# ─────────────────────────────────────────────────────────
# ADVISOR – SCHOOL RECORDS, EDIT & AI ANALYSIS
# ─────────────────────────────────────────────────────────

def _ai_suggestion_text(risk_label, probability_pass):
    """Generate human-readable AI suggestion based on risk label."""
    pct = f"{probability_pass:.0%}"
    if risk_label == 'At-Risk':
        return (
            f"⚠️ This student is AT-RISK (Pass probability: {pct}). "
            "Immediate actions required: "
            "1) Schedule a student check-in meeting as soon as possible, "
            "2) Investigate reasons for low attendance, "
            "3) Limit extracurricular activities until academic progress improves, "
            "4) Notify parent/guardian immediately."
        )
    elif risk_label == 'Average':
        return (
            f"📊 This student is performing at an AVERAGE level (Pass probability: {pct}). "
            "Recommendations: "
            "1) Increase self-study hours (at least 2 more hours per week), "
            "2) Monitor upcoming assessment results closely, "
            "3) Encourage extra academic participation."
        )
    else:
        return (
            f"✅ This student is SAFE/LOW RISK (Pass probability: {pct}). "
            "Recommendations: "
            "1) Maintain current study habits and discipline, "
            "2) Consider exploring advanced topic areas or electives, "
            "3) Encourage them to act as a peer mentor for other classmates."
        )



@login_required
def advisor_school_records(request):
    """Advisor sees all school results, advisors list, pending users, logs and uploads."""
    if request.user.role != 'advisor':
        messages.error(request, 'Only advisor accounts can access school records.')
        return redirect('index')

    school_name = request.user.school_name
    students = Student.objects.filter(
        user__school_name=school_name
    ).select_related('user', 'parent').prefetch_related('results', 'advisory_notes__advisor').order_by('user__first_name')

    # All advisors for this school
    advisors = User.objects.filter(role='advisor', school_name=school_name).order_by('-is_school_advisor', 'username')

    # Parents list (all approved parents so advisor can link them)
    parents = User.objects.filter(role='parent', approved=True).order_by('first_name', 'username')


    # Pending users at this school
    pending_users = User.objects.filter(
        school_name=school_name, approved=False, rejected=False
    ).order_by('date_joined')

    # Recent activity logs
    logs = SystemLog.objects.filter(school_name=school_name).order_by('-timestamp')[:20]

    # Recent uploads at this school
    uploads = UploadedFile.objects.filter(school_name=school_name).select_related('uploaded_by')[:15]

    return render(request, 'advisor_school_records.html', {
        'students': students,
        'school_name': school_name,
        'advisors': advisors,
        'parents': parents,
        'pending_users': pending_users,
        'logs': logs,
        'uploads': uploads,
        'can_edit': (
            request.user.role == 'admin' or (
                request.user.role == 'advisor' and (
                    not getattr(request.user, 'advisor_profile', None) or 
                    request.user.advisor_profile.can_edit
                )
            )
        ),
        'can_approve': request.user.can_approve_users or request.user.is_school_advisor,
    })


@login_required
@require_POST
def advisor_edit_result(request, result_id):
    """Advisor edits a Result record."""
    is_authorized = (
        request.user.role == 'admin' or (
            request.user.role == 'advisor' and (
                not getattr(request.user, 'advisor_profile', None) or 
                request.user.advisor_profile.can_edit
            )
        )
    )
    if not is_authorized:
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)

    result = get_object_or_404(Result, id=result_id)

    if request.user.role == 'advisor' and result.student.user.school_name != request.user.school_name:
        return JsonResponse({'success': False, 'message': 'Permission denied. Student belongs to another school.'}, status=403)

    try:
        subject = request.POST.get('subject', result.subject).strip()
        score = float(request.POST.get('score', result.score))
        assessment_name = request.POST.get('assessment_name', result.assessment_name).strip()
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'message': 'Invalid score value.'}, status=400)

    result.subject = subject
    result.score = score
    result.assessment_name = assessment_name
    result.edited_by = request.user
    result.save()

    # Also update student's study factors if provided
    student = result.student
    updated_fields = []
    try:
        if 'study_hours_per_week' in request.POST:
            student.study_hours_per_week = float(request.POST['study_hours_per_week'])
            updated_fields.append('study_hours_per_week')
        if 'attendance_rate' in request.POST:
            student.attendance_rate = float(request.POST['attendance_rate'])
            updated_fields.append('attendance_rate')
        if 'internet_access' in request.POST:
            student.internet_access = request.POST['internet_access']
            updated_fields.append('internet_access')
        if 'extracurricular' in request.POST:
            student.extracurricular = request.POST['extracurricular']
            updated_fields.append('extracurricular')
        if updated_fields:
            student.save(update_fields=updated_fields)
    except (TypeError, ValueError):
        pass

    # Automatically update prediction and notify advisors
    try:
        prediction_input = {
            'study_hours_per_week': student.study_hours_per_week,
            'attendance_rate': student.attendance_rate,
            'internet_access': student.internet_access,
            'extracurricular': student.extracurricular,
            'previous_score': result.score,
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

        # Update Result object predictions
        result.ai_prediction = {
            'risk_label': prediction_result['risk_label'],
            'probability_pass': prediction_result['probability_pass'],
        }
        result.ai_recommendation = _ai_suggestion_text(prediction_result['risk_label'], prediction_result['probability_pass'])
        result.save()

        # Send notification to all advisors of the student's school
        advisors = User.objects.filter(role='advisor', school_name=student.user.school_name)
        for adv in advisors:
            Notification.objects.create(
                user=adv,
                message=f"AI Prediction Updated: Student {student.user.name or student.user.username} is predicted to be '{student.prediction}' after result edit by {request.user.username}."
            )
    except Exception as exc:
        pass

    SystemLog.objects.create(
        event_type='Result Edited',
        description=f"{request.user.username} edited result #{result_id} for student {student.user.username}.",
        school_name=request.user.school_name,
    )

    return JsonResponse({
        'success': True,
        'message': 'Result updated successfully.',
        'result': {
            'id': result.id,
            'subject': result.subject,
            'score': result.score,
            'assessment_name': result.assessment_name,
        }
    })


@login_required
def advisor_ai_analyse(request, student_id):
    """Run AI analysis on a student and return risk label + suggestions."""
    is_authorized = (
        request.user.role == 'admin' or (
            request.user.role == 'advisor' and (
                not getattr(request.user, 'advisor_profile', None) or 
                request.user.advisor_profile.can_edit
            )
        )
    )
    if not is_authorized:
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)

    student = get_object_or_404(Student, id=student_id)

    if request.user.role == 'advisor' and student.user.school_name != request.user.school_name:
        return JsonResponse({'success': False, 'message': 'Permission denied. Student belongs to another school.'}, status=403)

    # Get latest result score
    latest_result = student.results.order_by('-created_at').first()
    previous_score = latest_result.score if latest_result else 60.0

    try:
        result = predict_student_outcome({
            'study_hours_per_week': student.study_hours_per_week,
            'attendance_rate': student.attendance_rate,
            'internet_access': student.internet_access,
            'extracurricular': student.extracurricular,
            'previous_score': previous_score,
        })
        risk_label = result['risk_label']
        probability_pass = result['probability_pass']

        # Update student
        student.prediction = risk_label
        student.risk_level = (
            'high' if risk_label == 'At-Risk'
            else 'medium' if risk_label == 'Average'
            else 'low'
        )
        student.ai_suggestion = _ai_suggestion_text(risk_label, probability_pass)
        student.ai_analysed_at = timezone.now()
        student.save(update_fields=['prediction', 'risk_level', 'ai_suggestion', 'ai_analysed_at'])

        SystemLog.objects.create(
            event_type='AI Analysis',
            description=f"{request.user.username} ran AI analysis on {student.user.username} → {risk_label}.",
            school_name=request.user.school_name,
        )

        return JsonResponse({
            'success': True,
            'risk_label': risk_label,
            'probability_pass': f"{probability_pass:.0%}",
            'suggestion': student.ai_suggestion,
            'analysed_at': student.ai_analysed_at.strftime('%b %d, %Y %H:%M'),
        })
    except Exception as exc:
        return JsonResponse({'success': False, 'message': f'AI analysis failed: {exc}'}, status=500)


@login_required
@require_POST
def advisor_approve_user(request, user_id):
    """School advisor (with can_approve_users or is_school_advisor) approves or rejects a user at their school."""
    if not (request.user.can_approve_users or request.user.is_school_advisor):
        messages.error(request, 'You do not have permission to approve users.')
        return redirect('advisor_school_records')

    target_user = get_object_or_404(User, id=user_id)

    # Must be same school
    if target_user.school_name != request.user.school_name:
        messages.error(request, 'You can only manage users from your own school.')
        return redirect('advisor_school_records')

    action = request.POST.get('action', 'approve')
    if action == 'approve':
        target_user.approved = True
        target_user.rejected = False
        target_user.save()
        Notification.objects.create(
            user=target_user,
            message=f"Your registration for {target_user.school_name} has been approved by your school advisor.",
        )
        SystemLog.objects.create(
            event_type='User Approved by Advisor',
            description=f"{request.user.username} approved {target_user.username} ({target_user.role}).",
            school_name=request.user.school_name,
        )
        messages.success(request, f'{target_user.username} approved successfully.')
    else:
        target_user.rejected = True
        target_user.approved = False
        target_user.save()
        SystemLog.objects.create(
            event_type='User Rejected by Advisor',
            description=f"{request.user.username} rejected {target_user.username} ({target_user.role}).",
            school_name=request.user.school_name,
        )
        messages.warning(request, f'{target_user.username} rejected.')

    return redirect('advisor_school_records')


@login_required
@require_POST
def advisor_register_advisor(request):
    """Primary Advisor registers a new school-level advisor for their school (pending admin approval)."""
    if not (request.user.role == 'advisor' and request.user.is_school_advisor):
        messages.error(request, 'Only Primary Advisors can register other advisors.')
        return redirect('advisor_portal')

    name = request.POST.get('name', '').strip()
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '').strip()
    phone = request.POST.get('phone', '').strip()
    
    school_name = request.user.school_name
    school = request.user.school

    if not all([name, username, password]):
        messages.error(request, 'Name, username, and password are required.')
        return redirect('advisor_school_records')

    if User.objects.filter(username__iexact=username).exists():
        messages.error(request, f'Username "{username}" already taken.')
        return redirect('advisor_school_records')

    first_name = name.split(' ', 1)[0]
    last_name = name.split(' ', 1)[1] if ' ' in name else ''

    new_advisor = User(
        username=username,
        first_name=first_name,
        last_name=last_name,
        role='advisor',
        approved=False,  # Needs admin approval!
        rejected=False,
        school_name=school_name,
        school=school,
        phone=phone,
        is_school_advisor=False,
        can_approve_users=False,
    )
    if email:
        new_advisor.email = email
    new_advisor.set_password(password)
    new_advisor.save()

    SystemLog.objects.create(
        event_type='Advisor Registered by Primary',
        description=f"Primary Advisor {request.user.username} registered pending advisor {username} for {school_name}.",
        school_name=school_name,
    )
    messages.success(request, f'Advisor "{username}" registered successfully. Waiting for Platform Admin approval.')
    return redirect('advisor_school_records')


@login_required
@require_POST
def add_advisory_note(request):
    if request.user.role != 'advisor':
        return JsonResponse({'success': False, 'message': 'Only advisors can add advisory notes.'}, status=403)

    student_id = request.POST.get('student_id')
    note_text = request.POST.get('note_text', '').strip()

    if not student_id or not note_text:
        return JsonResponse({'success': False, 'message': 'Student ID and note text are required.'}, status=400)

    student = get_object_or_404(Student, id=student_id, user__school_name=request.user.school_name)

    note = AdvisoryNote.objects.create(
        student=student,
        advisor=request.user,
        note_text=note_text
    )

    SystemLog.objects.create(
        event_type='Advisory Note Created',
        description=f"Advisor {request.user.username} logged an advisory note for student {student.user.username}.",
        school_name=request.user.school_name
    )

    return JsonResponse({
        'success': True,
        'note': {
            'id': note.id,
            'advisor_name': note.advisor.name or note.advisor.username,
            'note_text': note.note_text,
            'created_at': note.created_at.strftime('%b %d, %Y %H:%M')
        }
    })


@login_required
@require_POST
def link_parent_to_student(request):
    if request.user.role != 'advisor':
        return JsonResponse({'success': False, 'message': 'Only advisors can associate parents.'}, status=403)

    student_id = request.POST.get('student_id')
    parent_id = request.POST.get('parent_id')

    if not student_id:
        return JsonResponse({'success': False, 'message': 'Student ID is required.'}, status=400)

    student = get_object_or_404(Student, id=student_id, user__school_name=request.user.school_name)

    if parent_id:
        parent = get_object_or_404(User, id=parent_id, role='parent')
        student.parent = parent
        student.save()
        parent_name = parent.name or parent.username
        msg = f"Linked parent {parent_name} to student {student.user.name or student.user.username}."
    else:
        student.parent = None
        student.save()
        parent_name = "None"
        msg = f"Removed parent link for student {student.user.name or student.user.username}."

    SystemLog.objects.create(
        event_type='Parent Linked',
        description=f"Advisor {request.user.username} updated parent association for student {student.user.username} to {parent_name}.",
        school_name=request.user.school_name
    )

    return JsonResponse({
        'success': True,
        'message': msg,
        'parent_name': parent_name
    })


@login_required
@require_POST
def parent_verify_child(request):
    return JsonResponse({'success': False, 'message': 'Self-linking is disabled for privacy and security. Please contact your advisor.'}, status=403)


@login_required
@require_POST
def parent_unlink_child(request):
    return JsonResponse({'success': False, 'message': 'Unlinking child is disabled for privacy and security. Please contact your advisor.'}, status=403)



