from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from  django.conf import settings
 
class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):  # ✅ method name fixed
        if not email:
            raise ValueError("The 'EMAIL' field should not be left blank")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)  # ✅ call the corrected method

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
    objects = UserManager()

#this is my student class(Kushal)
# I created this to separate student from admin
class Student(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    roll = models.CharField(max_length=10, blank=True)
    semester = models.CharField(max_length=10, blank=True)
    department = models.CharField(max_length=50, blank=True)
    year = models.IntegerField(null=True, blank=True)
    first_login_info_submitted = models.BooleanField(default=False)