from pydantic import BaseModel, ConfigDict

from services.domain.autorizacao import Acao


class AcaoImplementada(BaseModel):
    """O que a ação é (`Acao`) + como está montada na interface."""

    model_config = ConfigDict(frozen=True)

    acao: Acao
    # Rota por nome: importar a view acoplaria a ação ao app do menu e fecharia um ciclo.
    url_name: str
    partial: str


class RegistroAcoes(BaseModel):
    """Coleção explícita e curada de ações. Construtível à vontade — é o tipo, não o catálogo
    canônico, que tem instância única (`apps/competencias/registro.py`)."""

    model_config = ConfigDict(frozen=True)

    acoes: tuple[AcaoImplementada, ...]

    def todas(self) -> tuple[AcaoImplementada, ...]:
        return self.acoes

    def por_slug(self, slug: str) -> AcaoImplementada | None:
        for acao in self.acoes:
            if acao.acao.slug == slug:
                return acao
        return None
