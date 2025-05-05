from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/upload/', views.admin_upload, name='admin_upload'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),  # Add this when ready
    path('logout/', views.logout_view, name='logout'),  # Optional, but useful
]
