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

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}".strip()

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.username or self.email or self.get_full_name()


class Student(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    form_level = models.CharField(max_length=10)
    combination = models.CharField(max_length=20)
    attendance_rate = models.FloatField(default=0.0)
    prediction = models.CharField(max_length=20, default='Average')
    risk_level = models.CharField(max_length=10, default='average')

    class Meta:
        db_table = 'students'

    def __str__(self):
        return f"{self.user.username or self.user.email} - {self.form_level}"


class Result(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='results')
    subject = models.CharField(max_length=80)
    score = models.FloatField()
    assessment_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

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
