from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('account/settings/', views.account_settings, name='settings'),
    path('account/settings/', views.account_settings, name='account_settings'),
    path('advisor/portal/', views.advisor_portal, name='advisor_portal'),
    path('advisor/register-student/', views.advisor_register_student, name='advisor_register_student'),
    path('advisor/upload-results/', views.upload_results, name='upload_results'),
    path('advisor/send-alert/<int:student_id>/', views.send_alert, name='advisor_send_alert'),
    path('parent/portal/', views.parent_portal, name='parent_portal'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('platform/admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('platform/approve-user/<int:user_id>/', views.approve_user, name='approve_user'),
    path('platform/approve-all-advisors/', views.approve_all_advisors, name='approve_all_advisors'),
    path('platform/approve-all-parents/', views.approve_all_parents, name='approve_all_parents'),
    path('platform/reject-user/<int:user_id>/', views.reject_user, name='reject_user'),
]
