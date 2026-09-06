"""O contrato do painel (SPEC painel/001): a aba agrupa por assunto, o grupo é o poço que reúne os
cards, e o card é um item de duas naturezas — ato administrativo (`ItemAcao`) ou view livre
(`ItemLivre`) — que convivem no mesmo grupo.
"""

from pydantic import BaseModel, ConfigDict, model_validator

from apps.competencias.schemas import AcaoImplementada
from services.domain.autorizacao import VarianteIcone

PARTIAL_CARTAO = "painel/partials/_card_item.html"


class ItemAcao(BaseModel):
    """Ato administrativo inscrito no registro: só aparece para quem tem a caneta."""

    model_config = ConfigDict(frozen=True)

    acao: AcaoImplementada
    # Nulo herda o do grupo. Declarado, é a liberdade de dar desenho próprio a UM item.
    partial: str | None = None
    variante_icone: VarianteIcone = VarianteIcone.GRANDE

    @model_validator(mode="after")
    def _variante_declarada(self) -> "ItemAcao":
        if self.variante_icone not in self.acao.acao.variantes_icone:
            raise ValueError(
                f"a ação '{self.acao.acao.slug}' não declara a variante de ícone "
                f"'{self.variante_icone}'"
            )
        return self


class ItemLivre(BaseModel):
    """View do sistema que não é ato administrativo. Fora do registro: não é concedível nem
    delegável, não passa por caneta, e traz na mão o que a ação traz no contrato."""

    model_config = ConfigDict(frozen=True)

    # Mesmo formato `<app>.<nome>` das ações: é ele que encontra o SVG.
    slug: str
    nome: str
    tooltip: str
    url_name: str
    # O kwarg que recebe o pk do perfil da sessão. None quando a rota não tem argumento.
    argumento_perfil: str | None = None
    partial: str | None = None
    variante_icone: VarianteIcone = VarianteIcone.GRANDE


class Grupo(BaseModel):
    """O poço da aba. Rótulo e nada mais de texto — descrição por grupo repetiria o parágrafo da
    aba."""

    model_config = ConfigDict(frozen=True)

    rotulo: str
    itens: tuple[ItemAcao | ItemLivre, ...]
    # O template de todo item deste continente, salvo o que declarar o seu.
    partial_padrao: str = PARTIAL_CARTAO


class Aba(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    # As três faces que a aba mostra: o texto da tab, o que abre com ela, e o parágrafo abaixo.
    rotulo: str
    titulo: str
    descricao: str
    # Solto no corpo da aba, sem poço: dois campos e não uma posição, porque o que muda entre eles
    # é só onde o item entra na página.
    itens_acima: tuple[ItemAcao | ItemLivre, ...] = ()
    grupos: tuple[Grupo, ...] = ()
    itens_abaixo: tuple[ItemAcao | ItemLivre, ...] = ()
    partial_padrao: str = PARTIAL_CARTAO
    # Aba do sistema: nunca some, e é ela que garante painel não-vazio.
    basica: bool = False


class ContratoPainel(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Ordem de exibição é a de declaração: campo de ordenação seria um segundo lugar para o mesmo.
    abas: tuple[Aba, ...]


class ItemResolvido(BaseModel):
    model_config = ConfigDict(frozen=True)

    partial: str
    url: str
    nome: str
    tooltip: str
    slug: str
    variante_icone: VarianteIcone


class GrupoResolvido(BaseModel):
    model_config = ConfigDict(frozen=True)

    rotulo: str
    itens: tuple[ItemResolvido, ...]


class AbaResolvida(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    rotulo: str
    titulo: str
    descricao: str
    itens_acima: tuple[ItemResolvido, ...]
    grupos: tuple[GrupoResolvido, ...]
    itens_abaixo: tuple[ItemResolvido, ...]
    # Sobrevive à resolução por dois motivos: é o que impede o painel de abrir vazio (`vazia()`
    # não basta — ela sobrevive mesmo vazia) e é o template quem marca a aba básica como aberta.
    basica: bool

    def vazia(self) -> bool:
        return not (self.itens_acima or self.grupos or self.itens_abaixo)


class PainelResolvido(BaseModel):
    model_config = ConfigDict(frozen=True)

    abas: tuple[AbaResolvida, ...]
