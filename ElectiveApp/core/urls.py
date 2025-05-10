from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('upload-student-excel/', views.upload_student_excel, name='upload-student-excel'),
    path('student-details/', views.student_details, name='student-details'),
    path('logout/', views.logout_view, name='logout'),
]
