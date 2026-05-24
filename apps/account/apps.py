from django.apps import AppConfig


class AccountConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "account"
    verbose_name = "Account"

    def ready(self) -> None:
        import account.signals  # noqa: F401
