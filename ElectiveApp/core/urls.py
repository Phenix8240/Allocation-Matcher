from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('upload-student-excel/', views.upload_student_excel, name='upload-student-excel'),
    path('student-details/', views.student_details, name='student-details'),
    path('logout/', views.logout_view, name='logout'),
    path('select-department-semester/', views.select_department_semester, name='select_department_semester'),
    path('fetch-core-subjects/', views.fetch_core_subjects, name='fetch_core_subjects'),
    path('fetch-electives/', views.fetch_electives, name='fetch_electives'),
    path('save-elective-selection/', views.save_elective_selection, name='save_elective_selection'),
    path('admin/student-choices/', views.student_choices, name='student_choices'),
    path('admin/view-choices/<str:semester>/', views.view_choices, name='view_choices'),
    path('admin/download-choices/<str:semester>/', views.download_choices, name='download_choices'),
]
