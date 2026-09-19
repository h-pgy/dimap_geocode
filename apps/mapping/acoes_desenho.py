from pydantic import BaseModel, ConfigDict, Field

from apps.competencias.schemas import AcaoImplementada
from services.domain.autorizacao import PADRAO_SLUG
from services.domain.desenho import TipoDesenho


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


class OfertarNoPoco:
    def __init__(self, registro: RegistroDesenho) -> None:
        self.registro = registro

    def __call__(self, entrada: OfertaPocoInput) -> tuple[ItemPoco, ...]:
        return self.pipeline(entrada)

    def pipeline(self, entrada: OfertaPocoInput) -> tuple[ItemPoco, ...]:
        return tuple(
            self._item(item)
            for item in self.registro.itens
            if entrada.tipo in item.tipos and self._liberado(item, entrada.slugs_liberados)
        )

    def _liberado(
        self,
        item: AcaoSobreDesenho | ConsultaSobreDesenho,
        slugs: frozenset[str],
    ) -> bool:
        # A consulta não é ato: não há caneta que a libere. Quem recusa o ato é a rota, a cada execução.
        if isinstance(item, ConsultaSobreDesenho):
            return True
        return item.acao.acao.slug in slugs

    def _item(self, item: AcaoSobreDesenho | ConsultaSobreDesenho) -> ItemPoco:
        if isinstance(item, ConsultaSobreDesenho):
            return ItemPoco(
                slug=item.slug,
                nome=item.nome,
                tooltip=item.tooltip,
                url_name=item.url_name,
            )
        acao = item.acao.acao
        return ItemPoco(
            slug=acao.slug,
            nome=acao.nome,
            tooltip=acao.tooltip,
            url_name=item.acao.url_name,
        )
