import os
import random
import string
import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings

from .forms import UploadFileForm
from .models import Student

User = get_user_model()

def password_generator(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def upload_student_excel(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = form.cleaned_data['student_file']
            try:
                df = pd.read_excel(excel_file)
            except Exception as e:
                messages.error(request, f"Cannot read Excel file: {e}")
                return redirect('upload-student-excel')

            if 'email' not in df.columns:
                messages.error(request, "Excel must have an 'email' column.")
                return redirect('upload-student-excel')

            created, skipped = 0, 0
            for raw in df['email']:
                email = str(raw).strip()
                if not email:
                    continue

                if User.objects.filter(email=email).exists():
                    skipped += 1
                    continue
                
                pwd = password_generator()

                try:
                    user = User.objects.create_user(email=email, password=pwd)
                    Student.objects.create(user=user,  plain_password=pwd)

                    send_mail(
                        subject="Your Portal Credentials",
                        message=f"Username: {email}\nPassword: {pwd}",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                    created += 1
                except Exception as e:
                    # Log to console; you can also use Django logging
                    print(f"[upload_student_excel] Error for {email}: {e}")

            messages.success(
                request,
                f"Done: {created} created, {skipped} skipped (already existed)."
            )
            return redirect('student-details')
        else:
            messages.error(request, "Invalid form submission.")
            return redirect('upload-student-excel')
    else:
        form = UploadFileForm()

    return render(request, 'core/upload_excel.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('username')
        pwd   = request.POST.get('password')
        user  = authenticate(request, email=email, password=pwd)
        if user:
            login(request, user)
            next_url = 'admin_dashboard' if user.is_staff else 'student_dashboard'
            return redirect(next_url)
        messages.error(request, "Invalid credentials.")
    return render(request, 'core/login.html')

@login_required
def student_dashboard(request):
    return render(request, 'core/student_dashboard.html', {'user': request.user})

@login_required
def admin_dashboard(request):
    return render(request, 'core/admin_dashboard.html', {'user': request.user})

@login_required
def student_details(request):
    students = Student.objects.select_related('user').all()
    return render(request, 'core/student_details.html', {'students': students})

def logout_view(request):
    logout(request)
    return redirect('login')
