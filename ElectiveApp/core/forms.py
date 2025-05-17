from django import forms
from django.contrib.auth.forms import AuthenticationForm
from core.models import *
from django.utils.translation import gettext_lazy as _
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

class CreateStudentForm(forms.Form):
    email = forms.EmailField(
        label=_("Email Address"),
        max_length=255,
        help_text=_("Enter the student's email address.")
    )
class AddSubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['code', 'name', 'semester', 'stream', 'is_elective']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-lg',
                'placeholder': 'e.g., PCC-CS701'
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-lg',
                'placeholder': 'e.g., Machine Learning'
            }),
            'semester': forms.Select(
                choices=[(i, f'Semester {i}') for i in range(1, 9)],
                attrs={'class': 'w-full p-2 border border-gray-300 rounded-lg'}
            ),
            'stream': forms.TextInput(attrs={
                'class': 'w-full p-2 border border-gray-300 rounded-lg',
                'placeholder': 'e.g., Core CS or Professional Elective VI'
            }),
            'is_elective': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600'})
        }

    def clean_code(self):
        code = self.cleaned_data['code'].strip().upper()
        if Subject.objects.filter(code=code).exists():
            raise forms.ValidationError("A subject with this code already exists.")
        return code

    def clean_semester(self):
        semester = self.cleaned_data['semester']
        try:
            return int(semester)
        except ValueError:
            raise forms.ValidationError("Semester must be a valid number.")