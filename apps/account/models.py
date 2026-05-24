import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from .managers import UserManager


class User(AbstractUser):
    """
    Modelo de usuario personalizado.
    Reemplaza el usuario por defecto de Django.
    Usa email como identificador principal. Sin username.
    Autenticación exclusivamente mediante Firebase (Google Sign-In).
    """

    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Estudiante"
        TEACHER = "TEACHER", "Profesor"

    # Eliminar campo username heredado
    username = None  # type: ignore[assignment]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID",
    )
    email = models.EmailField(
        "email",
        unique=True,
        db_index=True,
    )
    first_name = models.CharField("nombre", max_length=150, blank=True)
    last_name = models.CharField("apellido", max_length=150, blank=True)
    photo_url = models.URLField("foto de perfil", max_length=500, blank=True)
    firebase_uid = models.CharField(
        "Firebase UID",
        max_length=128,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )
    provider = models.CharField(
        "proveedor",
        max_length=50,
        default="google",
    )
    role = models.CharField(
        "rol",
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True,
    )

    # Campos heredados que se mantienen:
    # is_active, is_staff, date_joined, last_login

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()  # type: ignore[assignment]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        """Retorna el nombre completo del usuario."""
        return f"{self.first_name} {self.last_name}".strip()


class UserProfile(models.Model):
    """
    Perfil extendido del usuario.
    Se crea automáticamente via signal al crear un User.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="usuario",
    )
    phone = models.CharField("teléfono", max_length=20, null=True, blank=True)
    birth_date = models.DateField("fecha de nacimiento", null=True, blank=True)
    country = models.CharField("país", max_length=100, null=True, blank=True)
    language = models.CharField("idioma", max_length=10, default="es")
    timezone = models.CharField("zona horaria", max_length=50, default="America/Lima")
    avatar = models.ImageField("avatar", upload_to="avatars/", null=True, blank=True)
    created_at = models.DateTimeField("creado en", auto_now_add=True)
    updated_at = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        verbose_name = "perfil de usuario"
        verbose_name_plural = "perfiles de usuario"

    def __str__(self) -> str:
        return f"Perfil de {self.user.email}"


class StudentLoginActivity(models.Model):
    class Source(models.TextChoices):
        MOBILE_APP = "MOBILE_APP", "Mobile App"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="login_activities",
        verbose_name="usuario",
    )
    logged_at = models.DateTimeField("logueado en", auto_now_add=True)
    date = models.DateField("fecha", db_index=True)
    source = models.CharField(
        "origen",
        max_length=30,
        choices=Source.choices,
        default=Source.MOBILE_APP,
    )

    class Meta:
        verbose_name = "actividad de login estudiante"
        verbose_name_plural = "actividades de login estudiante"
        ordering = ["-logged_at"]
        indexes = [
            models.Index(fields=["date", "source"]),
            models.Index(fields=["user", "logged_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.date:
            self.date = timezone.localdate()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.user.email} - {self.date} ({self.source})"
