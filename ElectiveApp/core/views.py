import os
import random
import string
import pandas as pd
import json
import io
import re
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from .forms import UploadFileForm, UploadAllocationForm 
from django.contrib.admin.views.decorators import staff_member_required
from .models import Student, Subject, ElectiveSelection, AllocationResult
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import transaction
import logging
logger = logging.getLogger(__name__)


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

            columns = [col.strip().lower() for col in df.columns]
            original_columns = df.columns.tolist()

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
                
                pwd = password_generator()

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
                    user.delete()
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
@ensure_csrf_cookie
def student_dashboard(request):
    student = request.user.student
    if not student.department or not student.semester or not student.roll:
        return redirect('select_department_semester')
    allocation_results = AllocationResult.objects.filter(student=student, semester=student.semester)    
    return render(request, 'core/student_dashboard.html', {
        'student': student,
        'electives_finalized': student.elective_finalized,
        'allocation_results': allocation_results,
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
    
    try:
        semester = int(student.semester)
    except ValueError:
        return JsonResponse({'error': 'Invalid semester value'}, status=400)
    
    core_subjects = Subject.objects.filter(
        semester=semester,
        is_elective=False
    ).values('code', 'name', 'stream')
    
    return JsonResponse({'core_subjects': list(core_subjects)})

@login_required
def fetch_electives(request):
    student = request.user.student
    if not student.semester:
        return JsonResponse({'error': 'Semester not set'}, status=400)
    
    if student.elective_finalized:
        chosen = ElectiveSelection.objects.filter(student=student)
        return JsonResponse({
            'chosen': [{
                'code': s.subject.code,
                'name': s.subject.name,
                'stream': s.subject.stream
            } for s in chosen],
            'finalized': True
        })
    
    try:
        semester = int(student.semester)
    except ValueError:
        return JsonResponse({'error': 'Invalid semester value'}, status=400)
    
    electives = Subject.objects.filter(semester=semester, is_elective=True)
    
    grouped_electives = {}
    for elective in electives:
        stream = elective.stream
        if stream not in grouped_electives:
            grouped_electives[stream] = []
        grouped_electives[stream].append({
            'code': elective.code,
            'name': elective.name,
        })
    
    selected_codes = list(ElectiveSelection.objects.filter(
        student=student
    ).values_list('subject__code', flat=True))
    
    return JsonResponse({
        'electives': grouped_electives,
        'selected': selected_codes,
        'finalized': False
    })

@login_required
def save_elective_selection(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    student = request.user.student
    if student.elective_finalized:
        return JsonResponse({'error': 'Electives have been finalized and cannot be modified.'}, status=400)

    try:
        data = json.loads(request.body)
        selected_codes = data.get('selected_codes', [])
        action = data.get('action', 'save')

        valid_subjects = Subject.objects.filter(
            code__in=selected_codes, 
            is_elective=True, 
            semester=student.semester
        )

        if len(valid_subjects) != len(selected_codes):
            return JsonResponse({'error': 'Invalid subject selection'}, status=400)

        ElectiveSelection.objects.filter(student=student).delete()
        for subject in valid_subjects:
            ElectiveSelection.objects.create(student=student, subject=subject)

        if action == 'confirm':
            student.elective_finalized = True
            student.save()

        return JsonResponse({'message': 'Elective selections saved successfully'})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@staff_member_required
def student_choices(request):
    semesters = [choice[0] for choice in Student._meta.get_field('semester').choices]
    return render(request, 'core/student_choices.html', {'semesters': semesters})

@login_required
def view_choices(request, semester):
    if not request.user.is_staff:
        return redirect('student_dashboard')
    
    try:
        semester_int = int(semester)
    except ValueError:
        return HttpResponseBadRequest("Invalid semester")

    students = Student.objects.filter(semester=semester, elective_finalized=True)
    if not students.exists():
        return render(request, 'core/view_choices.html', {
            'semester': semester,
            'message': 'No students have finalized choices for this semester.'
        })

    streams = Subject.objects.filter(semester=semester_int, is_elective=True).values_list('stream', flat=True).distinct()

    data = []
    for student in students:
        row = {'roll': student.roll}
        selections = {sel.subject.stream: f"{sel.subject.code} - {sel.subject.name}" 
                      for sel in student.elective_selections.all()}
        for stream in streams:
            row[stream] = selections.get(stream, 'N/A')
        data.append(row)

    context = {
        'semester': semester,
        'streams': streams,
        'data': data,
    }
    return render(request, 'core/view_choices.html', context)

@login_required
def download_choices(request, semester):
    if not request.user.is_staff:
        return redirect('student_dashboard')
    
    try:
        semester_int = int(semester)
    except ValueError:
        return HttpResponseBadRequest("Invalid semester")

    students = Student.objects.filter(semester=semester, elective_finalized=True)
    if not students.exists():
        return HttpResponse("No students have finalized choices for this semester.", status=404)

    streams = Subject.objects.filter(semester=semester_int, is_elective=True).values_list('stream', flat=True).distinct()

    data = []
    for student in students:
        row = {'Roll Number': student.roll}
        selections = {sel.subject.stream: f"{sel.subject.code} - {sel.subject.name}" 
                      for sel in student.elective_selections.all()}
        for stream in streams:
            row[stream] = selections.get(stream, 'N/A')
        data.append(row)

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=f'Semester {semester}')
    output.seek(0)

    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="choices_semester_{semester}.xlsx"'
    return response

def find_roll_column(columns):
    """Identify the roll number column using common patterns."""
    patterns = [
        r'university\s*roll',
        r'roll\s*no',
        r'registration\s*no',
        r'reg\s*no',
        r'student\s*id',
        r'^\s*roll\s*$'
    ]
    for col in columns:
        if any(re.search(p, str(col), re.IGNORECASE) for p in patterns):
            return col
    return None

def normalize_code(raw):
    """Standardize subject codes by removing all spaces and underscores, preserving hyphens."""
    if pd.isna(raw) or not str(raw).strip():
        return None
    code = str(raw).strip().upper()
    code = re.sub(r'[\s_]+', '', code)
    return code

@staff_member_required
@transaction.atomic
def upload_allocation(request):
    if request.method == 'POST':
        form = UploadAllocationForm(request.POST, request.FILES)
        if form.is_valid():
            semester = form.cleaned_data['semester']
            allocation_file = request.FILES['allocation_file']

            try:
                df = pd.read_excel(allocation_file, header=0, skiprows=[1, 2], dtype=str).fillna('')
                df.columns = [col.strip() for col in df.columns]

                logger.info("Columns: %s", df.columns.tolist())
                logger.info("First 5 rows: %s", df.head(5).to_dict(orient='records'))

                roll_col = find_roll_column(df.columns)
                if roll_col is None:
                    messages.error(request, "Could not find roll number column in the Excel file.")
                    logger.error("No roll number column found.")
                    return redirect('upload_allocation')

                df = df[df[roll_col].str.strip().ne('') & ~df[roll_col].isna()]
                if df.empty:
                    messages.error(request, "No valid student data found in the Excel file.")
                    logger.error("No valid student data found.")
                    return redirect('upload_allocation')
                logger.info("Number of student rows: %d", len(df))

                elective_columns = [col for col in df.columns if 'elective' in col.lower()]
                if not elective_columns:
                    messages.error(request, "No elective columns found in the Excel file.")
                    logger.error("No elective columns found.")
                    return redirect('upload_allocation')
                logger.info("Elective columns detected: %s", elective_columns)

                students = Student.objects.filter(semester=semester)
                student_map = {str(s.roll).strip(): s for s in students}
                logger.info("Students fetched: %s", list(student_map.keys()))

                subjects = Subject.objects.filter(semester=int(semester), is_elective=True)
                subject_map = {normalize_code(s.code): s for s in subjects}
                logger.info("Subjects fetched: %s", list(subject_map.keys()))

                allocations = []
                errors = []

                for index, row in df.iterrows():
                    roll = str(row[roll_col]).strip()
                    student = student_map.get(roll)
                    if not student:
                        errors.append(f"Row {index+4}: Student roll {roll} not found for semester {semester}")
                        logger.error("Student roll %s not found at row %d", roll, index+4)
                        continue

                    chosen_selections = ElectiveSelection.objects.filter(student=student).select_related('subject')
                    chosen_by_stream = {sel.subject.stream: sel.subject for sel in chosen_selections}
                    logger.info("Student %s chosen streams: %s", roll, list(chosen_by_stream.keys()))

                    for col in elective_columns:
                        cell_value = str(row[col]).strip()
                        logger.info("Row %d, Col '%s': Cell value = '%s'", index+4, col, cell_value)
                        if not cell_value:
                            errors.append(f"Row {index+4}, Col '{col}': No subject code provided")
                            logger.warning("No subject code in row %d, col '%s'", index+4, col)
                            continue

                        subject_code = normalize_code(cell_value)
                        if not subject_code:
                            errors.append(f"Row {index+4}, Col '{col}': Invalid subject code '{cell_value}'")
                            logger.error("Invalid subject code '%s' in row %d, col '%s'", cell_value, index+4, col)
                            continue

                        allocated_subject = subject_map.get(subject_code)
                        if not allocated_subject:
                            errors.append(f"Row {index+4}, Col '{col}': Subject code '{subject_code}' not found in database")
                            logger.error("Subject code '%s' not found in row %d, col '%s'", subject_code, index+4, col)
                            continue

                        stream = allocated_subject.stream
                        logger.info("Allocated subject %s in stream %s (from code %s)", allocated_subject, stream, subject_code)

                        chosen_subject = chosen_by_stream.get(stream)
                        if chosen_subject is None:
                            logger.warning("Student %s has no chosen subject for stream %s", roll, stream)

                        is_match = chosen_subject and chosen_subject.code == allocated_subject.code

                        allocations.append(
                            AllocationResult(
                                student=student,
                                semester=semester,
                                stream=stream,
                                allocated_subject=allocated_subject,
                                chosen_subject=chosen_subject,
                                is_match=is_match
                            )
                        )
                        logger.info("Allocation added for student %s, stream %s", roll, stream)

                AllocationResult.objects.filter(semester=semester).delete()
                logger.info("Cleared existing allocations for semester %s", semester)

                AllocationResult.objects.bulk_create(allocations)
                logger.info("Created %d allocations", len(allocations))

                if errors:
                    error_msg = f"Processed {len(allocations)} allocations with {len(errors)} errors: " + "; ".join(errors[:5])
                    messages.warning(request, error_msg)
                    logger.warning(error_msg)
                else:
                    messages.success(request, f"Successfully processed {len(allocations)} allocations")
                    logger.info("All allocations processed successfully")

                return redirect('allocation_results', semester=semester)

            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
                logger.exception("Processing error: %s", str(e))
                return redirect('upload_allocation')
    else:
        form = UploadAllocationForm()

    return render(request, 'core/upload_allocation.html', {'form': form})


@login_required
def allocation_results(request, semester):
    if not request.user.is_staff:
        return redirect('student_dashboard')
    results = AllocationResult.objects.filter(semester=semester).select_related('student', 'allocated_subject').order_by('student__roll', 'stream')
    return render(request, 'core/allocation_results.html', {'results': results, 'semester': semester})