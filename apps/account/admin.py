from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Perfil"
    fields = [
        "phone",
        "birth_date",
        "country",
        "language",
        "timezone",
        "avatar",
        "created_at",
        "updated_at",
    ]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]

    list_display = [
        "email",
        "first_name",
        "last_name",
        "provider",
        "is_active",
        "is_staff",
        "date_joined",
    ]
    list_filter = ["is_active", "is_staff", "is_superuser", "provider"]
    search_fields = ["email", "first_name", "last_name", "firebase_uid"]
    ordering = ["-date_joined"]
    readonly_fields = ["id", "firebase_uid", "date_joined", "last_login"]

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (
            _("Información personal"),
            {"fields": ("first_name", "last_name", "photo_url")},
        ),
        (
            _("Firebase"),
            {"fields": ("firebase_uid", "provider")},
        ),
        (
            _("Permisos"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("Fechas"),
            {"fields": ("last_login", "date_joined")},
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "phone",
        "country",
        "language",
        "timezone",
        "created_at",
    ]
    search_fields = ["user__email", "phone", "country"]
    readonly_fields = ["created_at", "updated_at"]
    list_select_related = ["user"]
