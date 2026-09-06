from datetime import date

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

from apps.user_admin.schemas import DataOpcional, conferir_fim
from services.domain.autorizacao import Acao


class NovaDelegacao(BaseModel):
    model_config = ConfigDict(frozen=True)

    delegado: int
    data_inicio: date
    data_fim: DataOpcional = None

    @field_validator("data_fim")
    @classmethod
    def _fim_nao_antecede_inicio(cls, fim: date | None, info: ValidationInfo) -> date | None:
        return conferir_fim(fim, info.data.get("data_inicio"), "Fim da delegação não pode anteceder o início.")


class AcaoImplementada(BaseModel):
    """O que a ação é (`Acao`) + como está montada na interface."""

    model_config = ConfigDict(frozen=True)

    acao: Acao
    # Rota por nome: importar a view acoplaria a ação ao app que a exibe e fecharia um ciclo.
    url_name: str


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
