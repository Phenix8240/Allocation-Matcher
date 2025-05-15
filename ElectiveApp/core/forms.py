from django import forms
from django.contrib.auth.forms import AuthenticationForm
from core.models import Student
class UploadFileForm(forms.Form):
    student_file = forms.FileField(
        label="Select an Excel file (.xlsx)",
        help_text="File must have a column named 'email'."
    )

class LoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email')
    password = forms.CharField(widget=forms.PasswordInput)

class UploadAllocationForm(forms.Form):
    semester = forms.ChoiceField(choices=[(str(i), f"Semester {i}") for i in range(1, 9)])
    allocation_file = forms.FileField()