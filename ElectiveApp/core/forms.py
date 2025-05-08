from django import forms
from django.contrib.auth.forms import AuthenticationForm

class UploadFileForm(forms.Form):
    file = forms.FileField()

class LoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email')
    password = forms.CharField(widget=forms.PasswordInput)