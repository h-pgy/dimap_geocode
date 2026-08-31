from django.apps import AppConfig
from django.core.checks import register


class PainelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.painel"

    def ready(self) -> None:
        from .checks import checar_painel

        register(checar_painel)
