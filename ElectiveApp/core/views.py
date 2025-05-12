import os
import random
import string
import pandas as pd
import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from .forms import UploadFileForm
from .models import Student, Subject, ElectiveSelection

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
                messages.info(request, f"Loaded Excel file with {len(df)} rows.")
            except Exception as e:
                messages.error(request, f"Cannot read Excel file: {e}")
                return redirect('upload-student-excel')

            # Normalize column names to lowercase for case-insensitive comparison
            columns = [col.strip().lower() for col in df.columns]
            original_columns = df.columns.tolist()

            # Find the email column
            email_column = None
            for i, col in enumerate(columns):
                if col == 'email':
                    email_column = original_columns[i]
                    break

            if email_column is None:
                messages.error(
                    request,
                    f"Excel file must have an 'email' column. Found columns: {', '.join(original_columns)}"
                )
                return redirect('upload-student-excel')

            created, skipped = 0, 0
            for raw in df[email_column]:
                email = str(raw).strip()
                if not email:
                    continue

                if User.objects.filter(email=email).exists():
                    skipped += 1
                    continue
                
                pwd = password_generator()  # Ensure this function is defined elsewhere

                try:
                    user = User.objects.create_user(email=email, password=pwd)
                except Exception as e:
                    messages.error(request, f"Failed to create User for {email}: {e}")
                    continue

                try:
                    Student.objects.create(user=user, plain_password=pwd)
                    messages.success(request, f"Created student for {email}")
                except Exception as e:
                    messages.error(request, f"Failed to create Student for {email}: {e}")
                    user.delete()  # Roll back User creation if Student fails
                    continue

                try:
                    send_mail(
                        subject="Your Portal Credentials",
                        message=f"Username: {email}\nPassword: {pwd}",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                    created += 1
                except Exception as e:
                    messages.warning(request, f"Student created but email failed for {email}: {e}")

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
    student = request.user.student
    if not student.department or not student.semester or not student.roll:
        return redirect('select_department_semester')
    
    return render(request, 'core/student_dashboard.html', {
        'student': student,
        'electives_saved': ElectiveSelection.objects.filter(student=student).exists()
    })

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

@login_required
def select_department_semester(request):
    student = request.user.student
    if request.method == 'POST':
        department = request.POST.get('department')
        semester = request.POST.get('semester')
        roll = request.POST.get('roll', '').strip()

        try:
            if not department or not semester:
                raise ValueError("Both department and semester are required")
            
            # Validate roll number uniqueness if provided
            if roll:
                if Student.objects.exclude(pk=student.pk).filter(roll=roll).exists():
                    raise ValueError("This roll number is already taken")

            student.department = department
            student.semester = semester
            student.roll = roll or None
            student.save()
            
            messages.success(request, "Profile information updated successfully")
            return redirect('student_dashboard')

        except Exception as e:
            messages.error(request, str(e))
    
    return render(request, 'core/select_department_semester.html', {
        'student': student,
        'departments': Student._meta.get_field('department').choices,
        'semesters': Student._meta.get_field('semester').choices,
    })


@login_required
def fetch_core_subjects(request):
    student = request.user.student
    if not student.semester:
        return JsonResponse({'error': 'Semester not set'}, status=400)
    
    core_subjects = Subject.objects.filter(
        semester=student.semester,
        is_elective=False
    ).values('code', 'name', 'stream')
    
    return JsonResponse({'core_subjects': list(core_subjects)})

@login_required
def fetch_electives(request):
    student = request.user.student
    if not student.semester:
        return JsonResponse({'error': 'Semester not set'}, status=400)
    
    electives = Subject.objects.filter(
        semester=student.semester,
        is_elective=True
    ).order_by('stream', 'code')
    
    # Group electives by stream
    grouped_electives = {}
    for subject in electives:
        grouped_electives.setdefault(subject.stream, []).append({
            'code': subject.code,
            'name': subject.name,
        })
    
    # Get selected electives
    selected_codes = ElectiveSelection.objects.filter(
        student=student
    ).values_list('subject__code', flat=True)
    
    return JsonResponse({
        'electives': grouped_electives,
        'selected': list(selected_codes),
    })

@login_required
def save_elective_selection(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    student = request.user.student
    try:
        data = json.loads(request.body)
        selected_codes = data.get('selected_codes', [])
        
        # Validate selected codes
        valid_subjects = Subject.objects.filter(
            semester=student.semester,
            is_elective=True,
            code__in=selected_codes
        )
        
        # Group by stream to ensure one selection per group
        stream_selections = {}
        for subject in valid_subjects:
            stream_selections.setdefault(subject.stream, []).append(subject)
        
        # Check for multiple selections in the same stream
        for stream, subjects in stream_selections.items():
            if len(subjects) > 1:
                return JsonResponse({
                    'error': f"Cannot select multiple subjects from stream {stream}"
                }, status=400)
        
        # Clear previous selections
        ElectiveSelection.objects.filter(student=student).delete()
        
        # Save new selections
        for subject in valid_subjects:
            ElectiveSelection.objects.create(student=student, subject=subject)
        
        return JsonResponse({'message': 'Elective selections saved successfully'})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)