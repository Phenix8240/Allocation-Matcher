from django import forms
from django.contrib.auth.forms import AuthenticationForm

class UploadFileForm(forms.Form):
    file = forms.FileField()

class LoginForm(AuthenticationForm):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)