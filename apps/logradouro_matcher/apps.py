from django.apps import AppConfig


class LogradouroMatcherConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.logradouro_matcher"

    def ready(self) -> None:
        from services.domain.logradouros_match import logradouro_catalog

        logradouro_catalog.aquecer()
