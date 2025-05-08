from django.shortcuts import render, redirect
import random
import pandas as pd
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from .forms import UploadFileForm, LoginForm
from .models import User, Student


# Admin uploads XLSX file containing student emails and registration numbers
@login_required
def admin_upload(request):
    if request.user.role != 'admin':
        return redirect('login')

    message = None
    form = UploadFileForm()

    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            df = pd.read_excel(request.FILES['file'])

            for _, row in df.iterrows():
                email = row.get('Email')
                reg_no = row.get('RegNo', '')
                if email and not User.objects.filter(email=email).exists():
                    password = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                    user = User.objects.create(
                        email=email,
                        password=make_password(password),
                        role='student',
                    )
                    Student.objects.create(
                        user=user,
                        roll=reg_no,
                    )
            message = "Student accounts created successfully."

    return render(request, 'core/admin_uploads.html', {'form': form, 'message': message})


# # Login view for both admin and student
# def login_view(request):
#     if request.user.is_authenticated:
#         if request.user.role == 'admin':
#             return redirect('admin_dashboard')
#         elif request.user.role == 'student':
#             return redirect('student_dashboard')
#         else:
#             print('User doesnot exist')

#     if request.method == 'POST':
#         form = LoginForm(request.POST)
#         if form.is_valid():
#             email = form.cleaned_data['username']  # still using 'username' field in form
#             password = form.cleaned_data['password']
#             user = authenticate(request, email=email, password=password)
#             if user:
#                 login(request, user)
#                 print(f"User {user.email} logged in with role {user.role}")
#                 if user.role == 'admin':
#                     return redirect('admin_dashboard')
#                 elif user.role == 'student':
#                     return redirect('student_dashboard')
#             else:
#                 messages.error(request, "Invalid email or password.")
#     else:
#         form = LoginForm()

#     return render(request, 'core/login.html', {'form': form})


# Admin dashboard
@login_required
def admin_dashboard(request):
    if request.user.role != 'admin':
        return redirect('login')
    return render(request, 'core/admin_dashboard.html')


def login_view(request):
    if request.user.is_authenticated:
        if request.user.role == 'admin':
            return redirect('admin_dashboard')
        elif request.user.role == 'student':
            return redirect('student_dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                elif user.role == 'student':
                    return redirect('student_dashboard')
            else:
                messages.error(request, 'Invalid credentials.')
    else:
        form = LoginForm()

    return render(request, 'core/login.html', {'form': form})
