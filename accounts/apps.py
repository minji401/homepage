from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "회원"

    def ready(self):
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
        try:
            from herium.audit import connect

            connect()
        except Exception:
            pass
