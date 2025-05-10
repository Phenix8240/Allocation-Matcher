from django import forms
from django.contrib.auth.forms import AuthenticationForm

class UploadFileForm(forms.Form):
    student_file = forms.FileField(
        label="Select an Excel file (.xlsx)",
        help_text="File must have a column named 'email'."
    )

class LoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email')
    password = forms.CharField(widget=forms.PasswordInput)