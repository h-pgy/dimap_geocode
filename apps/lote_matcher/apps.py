from django.apps import AppConfig


class LoteMatcherConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.lote_matcher"

    def ready(self) -> None:
        from services.domain.contribuinte_match import contribuinte_catalog

        contribuinte_catalog.aquecer()
