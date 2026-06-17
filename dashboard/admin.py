from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Alert, Notification, Result, Student, SystemLog, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role Information', {
            'fields': ('role', 'school_name', 'subjects', 'phone', 'home_address', 'approved', 'rejected', 'registration_rule')
        }),
    )


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'form_level', 'combination', 'attendance_rate', 'prediction', 'risk_level')
    search_fields = ('user__username', 'user__email', 'combination')


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'score', 'assessment_name', 'created_at')
    list_filter = ('subject',)


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('student', 'message', 'created_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'read', 'created_at')


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'description', 'timestamp')
    search_fields = ('event_type', 'description')
