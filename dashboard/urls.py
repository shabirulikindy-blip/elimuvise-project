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
    path('advisor/school-records/', views.advisor_school_records, name='advisor_school_records'),
    path('advisor/edit-result/<int:result_id>/', views.advisor_edit_result, name='advisor_edit_result'),
    path('advisor/edit-student-inline/', views.edit_student_inline, name='edit_student_inline'),
    path('advisor/ai-analyse/<int:student_id>/', views.advisor_ai_analyse, name='advisor_ai_analyse'),
    path('advisor/approve-user/<int:user_id>/', views.advisor_approve_user, name='advisor_approve_user'),
    path('advisor/register-advisor/', views.advisor_register_advisor, name='advisor_register_advisor'),
    path('parent/portal/', views.parent_portal, name='parent_portal'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('platform/admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('platform/approve-user/<int:user_id>/', views.approve_user, name='approve_user'),
    path('platform/approve-all-advisors/', views.approve_all_advisors, name='approve_all_advisors'),
    path('platform/approve-all-parents/', views.approve_all_parents, name='approve_all_parents'),
    path('platform/reject-user/<int:user_id>/', views.reject_user, name='reject_user'),
    # School management
    path('platform/schools/', views.admin_schools, name='admin_schools'),
    path('platform/schools/<int:school_id>/', views.admin_school_detail, name='admin_school_detail'),
    path('platform/grant-permission/<int:user_id>/', views.admin_grant_permission, name='admin_grant_permission'),
    path('platform/register-advisor/', views.admin_register_advisor, name='admin_register_advisor'),
    path('platform/edit-student/<int:student_id>/', views.admin_edit_student, name='admin_edit_student'),
    path('platform/edit-advisor/<int:user_id>/', views.admin_edit_advisor, name='admin_edit_advisor'),
    # Advisory Support Module
    path('advisor/add-advisory-note/', views.add_advisory_note, name='add_advisory_note'),
    path('advisor/link-parent/', views.link_parent_to_student, name='link_parent_to_student'),
    # Parent child-verification flow (disabled for data privacy)
    # path('parent/verify-child/', views.parent_verify_child, name='parent_verify_child'),
    # path('parent/unlink-child/', views.parent_unlink_child, name='parent_unlink_child'),
]


