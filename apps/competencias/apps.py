from django.apps import AppConfig
from django.core.checks import register


class CompetenciasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.competencias"

    def ready(self) -> None:
        from .checks import checar_registro_de_acoes

        register(checar_registro_de_acoes)
