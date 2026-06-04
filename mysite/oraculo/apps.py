from django.apps import AppConfig


class OraculoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "oraculo"

    def ready(self):
        try:
            import oraculo.signals
        except Exception:
            pass