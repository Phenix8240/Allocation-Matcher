import os
import random
import string
import pandas as pd
import json
import io,re
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from .forms import UploadFileForm,UploadAllocationForm 
from django.contrib.admin.views.decorators import staff_member_required
from .models import Student, Subject, ElectiveSelection, AllocationResult
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import ensure_csrf_cookie

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
    
    try:
        semester = int(student.semester)  # Convert to integer
    except ValueError:
        return JsonResponse({'error': 'Invalid semester value'}, status=400)
    
    core_subjects = Subject.objects.filter(
        semester=semester,  # Now comparing integer to integer
        is_elective=False
    ).values('code', 'name', 'stream')
    
    return JsonResponse({'core_subjects': list(core_subjects)})

@login_required
def fetch_electives(request):
    student = request.user.student
    if not student.semester:
        return JsonResponse({'error': 'Semester not set'}, status=400)
    
    # Corrected typo: electives_finalized -> elective_finalized
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
    
    # Handle non-finalized state
    try:
        semester = int(student.semester)
    except ValueError:
        return JsonResponse({'error': 'Invalid semester value'}, status=400)
    
    # Fetch electives for the semester
    electives = Subject.objects.filter(semester=semester, is_elective=True)
    
    # Group by stream
    grouped_electives = {}
    for elective in electives:
        stream = elective.stream
        if stream not in grouped_electives:
            grouped_electives[stream] = []
        grouped_electives[stream].append({
            'code': elective.code,
            'name': elective.name,
        })
    
    # Get selected codes
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
    if student.elective_finalized:  # Corrected field name
        return JsonResponse({'error': 'Electives have been finalized and cannot be modified.'}, status=400)

    try:
        data = json.loads(request.body)
        selected_codes = data.get('selected_codes', [])
        action = data.get('action', 'save')

        # Validation: Ensure selected codes are valid electives for the student's semester
        valid_subjects = Subject.objects.filter(
            code__in=selected_codes, 
            is_elective=True, 
            semester=student.semester
        )

        if len(valid_subjects) != len(selected_codes):
            return JsonResponse({'error': 'Invalid subject selection'}, status=400)

        # Save new selections
        ElectiveSelection.objects.filter(student=student).delete()
        for subject in valid_subjects:
            ElectiveSelection.objects.create(student=student, subject=subject)

        # Finalize if action is confirm
        if action == 'confirm':
            student.elective_finalized = True  # Corrected from electives_finalized
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
    """Render a table of elective choices for a given semester."""
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

    # Get unique streams for electives in this semester
    streams = Subject.objects.filter(semester=semester_int, is_elective=True).values_list('stream', flat=True).distinct()

    # Prepare data for the table
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
    """Generate and serve an Excel file with elective choices for a given semester."""
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

    # Prepare data for Excel
    data = []
    for student in students:
        row = {'Roll Number': student.roll}
        selections = {sel.subject.stream: f"{sel.subject.code} - {sel.subject.name}" 
                      for sel in student.elective_selections.all()}
        for stream in streams:
            row[stream] = selections.get(stream, 'N/A')
        data.append(row)

    # Create DataFrame and Excel file in memory
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=f'Semester {semester}')
    output.seek(0)

    # Prepare response
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="choices_semester_{semester}.xlsx"'
    return response

def clean_subject_code(value):
    if pd.isna(value) or not value:
        return None
    value = str(value).strip()
    match = re.match(r'^([A-Z0-9-]+)', value)
    return match.group(1) if match else None
def find_roll_column(columns):
    roll_patterns = [
        r'roll\s*(number|no\.?|num)?\s*(id)?',
        r'student\s*(roll|id|number|no\.?)',
        r'roll\s*id',
        r'roll',
        r'registration\s*(no\.?|number)',
        r'reg\s*no\.?'
    ]
    for col in columns:
        col_lower = str(col).lower().strip()
        if any(re.search(pattern, col_lower, re.IGNORECASE) for pattern in roll_patterns):
            return col
    return None

@staff_member_required
def upload_allocation(request):
    if request.method == 'POST':
        form = UploadAllocationForm(request.POST, request.FILES)
        if form.is_valid():
            semester = form.cleaned_data['semester']
            allocation_file = request.FILES['allocation_file']
            
            try:
                # Read Excel file with all data as strings and fill NaN with empty strings
                df = pd.read_excel(allocation_file, dtype=str).fillna('')
                df.columns = [col.strip() for col in df.columns]

                # Dynamically find roll number column
                roll_col = find_roll_column(df.columns)
                if roll_col is None:
                    messages.error(request, "Could not find a roll number column in the Excel file.")
                    return redirect('upload_allocation')

                # Identify elective columns as all columns except roll_col
                elective_columns = [col for col in df.columns if col != roll_col]

                errors = []
                allocations_created = 0

                for index, row in df.iterrows():
                    # Process roll number
                    raw_roll = str(row[roll_col]).strip()
                    if not raw_roll:
                        errors.append(f"Row {index+2}: Missing roll number")
                        continue

                    # Find student using roll and semester
                    try:
                        student = Student.objects.get(roll=raw_roll, semester=semester)
                    except Student.DoesNotExist:
                        errors.append(f"Row {index+2}: Student with roll {raw_roll} not found for semester {semester}")
                        continue

                    # Process elective columns
                    for col in elective_columns:
                        cell_value = str(row[col]).strip()
                        if not cell_value:
                            continue

                        # Extract subject code using regex
                        code_match = re.search(r'^([A-Z]+-[A-Z0-9]+)', cell_value.upper())
                        if not code_match:
                            errors.append(f"Row {index+2}: Invalid subject code format in '{col}' - '{cell_value}'")
                            continue
                        
                        subject_code = code_match.group(1).replace(" ", "")

                        # Find subject
                        try:
                            subject = Subject.objects.get(
                                code__iexact=subject_code,
                                semester=int(semester),
                                is_elective=True
                            )
                        except Subject.DoesNotExist:
                            errors.append(f"Row {index+2}: Subject {subject_code} not found for semester {semester}")
                            continue
                        
                        # Create or update allocation result
                        AllocationResult.objects.update_or_create(
                            semester=semester,
                            student=student,
                            stream=subject.stream,
                            defaults={
                                'allocated_subject': subject,
                                'is_match': ElectiveSelection.objects.filter(
                                    student=student,
                                    subject=subject
                                ).exists()
                            }
                        )
                        allocations_created += 1

                # Provide feedback to the user
                if errors:
                    error_summary = f"Created {allocations_created} allocations with {len(errors)} errors: " + "; ".join(errors[:5])  # Limit to first 5 errors for brevity
                    messages.warning(request, error_summary)
                else:
                    messages.success(request, f"Successfully created {allocations_created} allocations")

                return redirect('allocation_results', semester=semester)

            except Exception as e:
                messages.error(request, f"Processing failed: {str(e)}")
                return redirect('upload_allocation')

    form = UploadAllocationForm()
    return render(request, 'core/upload_allocation.html', {'form': form})

@login_required
def allocation_results(request, semester):
    if not request.user.is_staff:
        return redirect('student_dashboard')
    results = AllocationResult.objects.filter(semester=semester).select_related('student', 'chosen_subject', 'allocated_subject').order_by('student__roll', 'stream')
    return render(request, 'core/allocation_results.html', {'results': results, 'semester': semester})
