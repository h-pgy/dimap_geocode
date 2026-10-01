from pydantic import BaseModel, ConfigDict

from apps.competencias.schemas import AcaoImplementada
from services.domain.autorizacao import VarianteIcone

PADRAO_SQL = r"^\d{3}\.\d{3}\.\d{4}-\d$"


class AcaoDeLote(BaseModel):
    """Uma ação oferecida sobre o lote fiscal ou sobre o conjunto deles. A rota do modal recebe a
    query string que o router monta: o polígono e o SQL no lote, a chave no conjunto."""

    model_config = ConfigDict(frozen=True)

    acao: AcaoImplementada
    url_name: str   # rota do modal da ação
    variante_icone: VarianteIcone = VarianteIcone.PEQUENO


class ContratoAcoesLote(BaseModel):
    """Coleção explícita do que opera sobre um lote fiscal, ou sobre um conjunto deles."""

    model_config = ConfigDict(frozen=True)

    itens: tuple[AcaoDeLote, ...]
