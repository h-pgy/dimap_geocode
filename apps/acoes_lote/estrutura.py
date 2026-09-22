from pydantic import BaseModel, ConfigDict

from apps.competencias.schemas import AcaoImplementada
from services.domain.autorizacao import VarianteIcone

PADRAO_SQL = r"^\d{3}\.\d{3}\.\d{4}-\d$"


class AcaoDeLote(BaseModel):
    """Uma ação oferecida sobre o lote fiscal. A rota recebe o identificador do polígono e o SQL."""

    model_config = ConfigDict(frozen=True)

    acao: AcaoImplementada
    url_name: str   # rota do modal da ação
    variante_icone: VarianteIcone = VarianteIcone.PEQUENO


class ContratoAcoesLote(BaseModel):
    """Coleção explícita do que opera sobre um lote fiscal."""

    model_config = ConfigDict(frozen=True)

    itens: tuple[AcaoDeLote, ...]
