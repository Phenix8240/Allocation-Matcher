from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

#this is my user class where, role can be Admin or student(Kushal)
class User(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)#The '_' is used for translating the email id in english if u enter in other language

    ROLES = (
        ('admin', 'Admin'),
        ('student', 'Student'),
    )
    role = models.CharField(max_length=10, choices=ROLES, default='student')
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

#this is my student class(Kushal)
# I created this to separate student from admin
class Student(models.Model):
    user = User.OneToOneField(User, on_delete=models.CASCADE)
    roll = models.IntegerField(max_length=10, blank=True)
    semester = models.CharField(max_length=10, blank=True)
    department = models.CharField(max_length=50, blank=True)
    year = models.IntegerField(null=True, blank=True)
    first_login_info_submitted = models.BooleanField(default=False)