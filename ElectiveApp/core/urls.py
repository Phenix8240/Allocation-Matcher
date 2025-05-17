from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('upload-student-excel/', views.upload_student_excel, name='upload-student-excel'),
    path('student-details/', views.student_details, name='student-details'),
    path('admin/upload-allocation/', views.upload_allocation, name='upload_allocation'),
    path('admin/allocation-results/<str:semester>/', views.allocation_results, name='allocation_results'),
    path('logout/', views.logout_view, name='logout'),
    path('add-subject/', views.add_subject, name='add_subject'),
    path('list-subjects/', views.list_subjects, name='list_subjects'),
    path('select-department-semester/', views.select_department_semester, name='select_department_semester'),
    path('reselect-department-semester/', views.reselect_department_semester, name='reselect_department_semester'),
    path('fetch-core-subjects/', views.fetch_core_subjects, name='fetch_core_subjects'),
    path('fetch-electives/', views.fetch_electives, name='fetch_electives'),
    path('save-elective-selection/', views.save_elective_selection, name='save_elective_selection'),
    path('reset-student-password/<int:student_id>/', views.reset_student_password, name='reset_student_password'),
    path('create-student/', views.create_student, name='create_student'),
    path('add_student/', views.add_student, name='add_student'),
    path('admin/student-choices/', views.student_choices, name='student_choices'),
    path('admin/view-choices/<str:semester>/', views.view_choices, name='view_choices'),
    path('admin/download-choices/<str:semester>/', views.download_choices, name='download_choices'),
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset-confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('delete-subject/<int:subject_id>/', views.delete_subject, name='delete_subject'),
]
