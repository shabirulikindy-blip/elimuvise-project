from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True, blank=True, null=True)
    role = models.CharField(max_length=20)
    school_name = models.CharField(max_length=120, blank=True, null=True)
    subjects = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    home_address = models.CharField(max_length=255, blank=True, null=True)
    approved = models.BooleanField(default=False)
    rejected = models.BooleanField(default=False)
    registration_rule = models.CharField(max_length=120, blank=True, null=True)
    can_approve_users = models.BooleanField(default=False)
    # New permission fields
    can_upload = models.BooleanField(default=False)
    can_edit_records = models.BooleanField(default=False)
    is_school_advisor = models.BooleanField(default=False)
    school = models.ForeignKey(
        'School', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='members'
    )

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}".strip()

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.username or self.email or self.get_full_name()

class AdvisorProfile(models.Model):
    """Profile for advisors distinguishing main and assistant roles."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='advisor_profile')
    is_main = models.BooleanField(default=False, help_text='Main advisor with full permissions')
    can_edit = models.BooleanField(default=True, help_text='Assistant advisors can edit uploaded data')

    class Meta:
        db_table = 'advisor_profiles'

    def __str__(self):
        role = 'Main' if self.is_main else 'Assistant'
        return f"{role} Advisor: {self.user.username}"


class School(models.Model):
    name = models.CharField(max_length=200, unique=True)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='registered_schools'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'schools'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_students(self):
        return Student.objects.filter(
            user__school_name=self.name
        ).select_related('user')

    def get_advisors(self):
        return User.objects.filter(role='advisor', school_name=self.name)

    def get_primary_advisor(self):
        return User.objects.filter(
            role='advisor', school_name=self.name, is_school_advisor=True
        ).first()


class Student(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    form_level = models.CharField(max_length=10)
    combination = models.CharField(max_length=20)
    study_hours_per_week = models.FloatField(default=0.0)
    attendance_rate = models.FloatField(default=0.0)
    internet_access = models.CharField(max_length=10, default='Unknown')
    extracurricular = models.CharField(max_length=10, default='No')
    prediction = models.CharField(max_length=20, default='Average')
    risk_level = models.CharField(max_length=10, default='average')
    temp_password = models.CharField(max_length=128, blank=True, null=True)
    gender = models.CharField(max_length=15, default='Unknown')
    age = models.FloatField(null=True, blank=True)
    parent_education = models.CharField(max_length=100, default='Unknown')
    # AI suggestion cache
    ai_suggestion = models.TextField(blank=True, null=True)
    ai_analysed_at = models.DateTimeField(null=True, blank=True)
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students_parent_of'
    )

    class Meta:
        db_table = 'students'

    def __str__(self):
        return f"{self.user.username or self.user.email} - {self.form_level}"


class AdvisoryNote(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='advisory_notes')
    advisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='written_notes')
    note_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'advisory_notes'
        ordering = ['-created_at']

    def __str__(self):
        return f"Note by {self.advisor.username} on {self.student.user.username} at {self.created_at}"



class UploadedFile(models.Model):
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_files'
    )
    school_name = models.CharField(max_length=200, blank=True, null=True)
    file_name = models.CharField(max_length=255)
    upload_type = models.CharField(max_length=20, default='csv')
    row_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='pending')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'uploaded_files'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.file_name} by {self.uploaded_by} ({self.created_at.date()})"


class Result(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='results')
    subject = models.CharField(max_length=80)
    score = models.FloatField()
    assessment_name = models.CharField(max_length=100)
    uploaded_file = models.ForeignKey(
        UploadedFile, null=True, blank=True, on_delete=models.SET_NULL, related_name='results'
    )
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='edited_results'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # AI prediction data stored per result
    ai_prediction = models.JSONField(blank=True, null=True, help_text='AI prediction metadata')
    ai_recommendation = models.TextField(blank=True, null=True, help_text='AI recommendation text')

    class Meta:
        db_table = 'results'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.subject} ({self.assessment_name}) - {self.score}"


class Alert(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='alerts')
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'alerts'
        ordering = ['-created_at']

    def __str__(self):
        return self.message


class SystemLog(models.Model):
    event_type = models.CharField(max_length=80)
    description = models.CharField(max_length=255)
    school_name = models.CharField(max_length=200, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'system_logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.event_type}: {self.description[:50]}"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return self.message
