from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Custom manager for the User model, handling user creation with email as the primary identifier.
    """
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with the given email and password.
        """
        if not email:
            raise ValueError(_("The Email field must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True"))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True"))

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model using email as the unique identifier instead of username.
    """
    username = None  # Disable username field
    email = models.EmailField(_("email address"), unique=True, max_length=255)
    role = models.CharField(
        max_length=10,
        choices=[
            ('admin', 'Admin'),
            ('student', 'Student'),
        ],
        default='student',
        help_text=_("User's role in the system (admin or student).")
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")

class Student(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student',
        help_text=_("Associated user account.")
    )
    plain_password = models.CharField(
        max_length=128,
        blank=True,
        help_text=_("Plain-text password for initial login (temporary storage).")
    )
    roll = models.CharField(
        max_length=10,
        blank=True,
        unique=False,
        null=True,  # Ensures roll is optional in the database
        help_text=_("Student's roll number, if assigned.")
    )
    department = models.CharField(
        max_length=50,
        choices=[
            ('CS', 'Computer Science'),
            ('IT', 'Information Technology'),
            ('ECE', 'Electronics and Communication'),
        ],
        blank=True,
        help_text=_("Student's department.")
    )
    semester = models.CharField(
        max_length=10,
        choices=[(str(i), f'Semester {i}') for i in range(1, 9)],
        blank=True,
        help_text=_("Current semester of the student.")
    )
    year = models.IntegerField(
        null=True,
        blank=True,
        help_text=_("Academic year (e.g., 2023).")
    )
    first_login_info_submitted = models.BooleanField(
        default=False,
        help_text=_("Indicates if the student has submitted initial info (department, semester).")
    )
    date_created = models.DateTimeField(
        default=timezone.now,
        help_text=_("Timestamp when the student record was created.")
    )

    def __str__(self):
        return f"{self.user.email} — {self.roll or 'no roll'}"

    class Meta:
        verbose_name = _("Student")
        verbose_name_plural = _("Students")

class Subject(models.Model):
    """
    Model representing a subject (course) offered in a semester.
    """
    name = models.CharField(
        max_length=255,
        help_text=_("Name of the subject (e.g., Database Management Systems).")
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text=_("Subject code (e.g., PCC-CS601).")
    )
    semester = models.IntegerField(
        help_text=_("Semester in which the subject is offered (1-8).")
    )
    stream = models.CharField(
        max_length=50,
        help_text=_("Stream or category (e.g., Core CS, PE Group 1, OE I).")
    )
    is_elective = models.BooleanField(
        default=False,
        help_text=_("Indicates if the subject is an elective.")
    )

    def __str__(self):
        return f"{self.name} - Sem {self.semester}"

    class Meta:
        verbose_name = _("Subject")
        verbose_name_plural = _("Subjects")


class ElectiveSelection(models.Model):
    """
    Model to track elective subjects selected by a student.
    """
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='elective_selections',
        help_text=_("Student who selected the elective.")
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='selections',
        help_text=_("Selected elective subject.")
    )
    selected_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Timestamp when the elective was selected.")
    )

    def __str__(self):
        return f"{self.student.user.email} - {self.subject.code}"

    class Meta:
        unique_together = ('student', 'subject')
        verbose_name = _("Elective Selection")
        verbose_name_plural = _("Elective Selections")