from pydantic import BaseModel


class CamadaBaseItem(BaseModel):
    """Definição de uma camada base declarada em settings.WMS_BASES com metadados para a torrezinha."""

    nome: str
    glifo: str
    layers: str
    url: str | None = None
    zoom_nativo: int | None = None
