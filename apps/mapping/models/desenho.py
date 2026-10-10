import json

from pydantic import BaseModel, ConfigDict, Field, field_validator

from apps.competencias.schemas import AcaoImplementada
from services.domain.autorizacao import PADRAO_SLUG
from services.domain.desenho import TipoDesenho
from services.domain.geometry import PointGeometry


class AcaoSobreDesenho(BaseModel):
    """Ato administrativo inscrito no REGISTRO que opera sobre desenho: só aparece a quem tem a caneta."""

    model_config = ConfigDict(frozen=True)

    acao: AcaoImplementada
    tipos: frozenset[TipoDesenho] = Field(min_length=1)


class ConsultaSobreDesenho(BaseModel):
    """Rota aberta que opera sobre desenho. Fora do REGISTRO: não é concedível e aparece a todos."""

    model_config = ConfigDict(frozen=True)

    slug: str = Field(pattern=PADRAO_SLUG)  # mesmo formato das ações: é ele que encontra o SVG
    nome: str
    tooltip: str
    url_name: str
    tipos: frozenset[TipoDesenho] = Field(min_length=1)


class RegistroDesenho(BaseModel):
    """Coleção explícita e curada do que opera sobre desenho."""

    model_config = ConfigDict(frozen=True)

    itens: tuple[AcaoSobreDesenho | ConsultaSobreDesenho, ...]


class ItemPoco(BaseModel):
    """O que o poço desenha: as duas naturezas convergem para o mesmo item."""

    model_config = ConfigDict(frozen=True)

    slug: str
    nome: str
    tooltip: str
    url_name: str


class OfertaPocoInput(BaseModel):
    tipo: TipoDesenho
    slugs_liberados: frozenset[str]  # já resolvidos pela view: o router não vê request


class ConsultaSobrePonto(BaseModel):
    """A geometria que o envio.js enxertou. Linha e polígono viram ValidationError."""

    desenho: PointGeometry

    @field_validator("desenho", mode="before")
    @classmethod
    def _do_json(cls, valor: object) -> object:
        # Sem o envio.js o campo não chega: vira ValidationError e cai no middleware.
        return json.loads(valor) if isinstance(valor, str) else valor
