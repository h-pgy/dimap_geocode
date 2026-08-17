from enum import StrEnum

from django.urls import reverse

from pydantic import BaseModel, ConfigDict, model_validator

from services.domain.autorizacao import VarianteIcone

from .schemas import AcaoImplementada


class FormaItem(StrEnum):
    LINHA = "linha"
    CARTAO = "cartao"


class ItemDeMenu(BaseModel):
    """A apresentação de uma ação DENTRO de um menu. É aqui que ela mora, não no contrato da ação."""

    model_config = ConfigDict(frozen=True)

    # Nome não é "acao": o valor é o envelope de implementação, não o contrato (SPEC 001).
    acao_implementada: AcaoImplementada
    # Entre as que a ação declara possuir: pedir uma que ela não tem é erro de declaração.
    variante_icone: VarianteIcone
    # Linha compacta ou cartão explicativo (SPEC 006): também é escolha de quem exibe.
    forma: FormaItem

    @model_validator(mode="after")
    def _variante_declarada(self) -> "ItemDeMenu":
        # O fallback da SPEC 006 existe para arquivo faltando em runtime, não para esconder erro de
        # declaração. Como o item já compõe a ação, a checagem é local — dispensa system check.
        if self.variante_icone not in self.acao_implementada.acao.variantes_icone:
            raise ValueError(
                f"a ação '{self.acao_implementada.acao.slug}' não declara a variante de ícone "
                f"'{self.variante_icone}'"
            )
        return self


class ContratoMenu(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    nome: str
    # Ordem de exibição é a de declaração: campo de ordenação seria um segundo lugar para o mesmo.
    itens: tuple[ItemDeMenu, ...]


class MontagemMenu(BaseModel):
    model_config = ConfigDict(frozen=True)

    menu: ContratoMenu
    # O router recebe o CONJUNTO, não o usuário: é o que o mantém puro e testável sem banco.
    slugs_liberados: frozenset[str]


class ItemRenderizavel(BaseModel):
    model_config = ConfigDict(frozen=True)

    partial: str
    url: str
    # A linha compacta usa o curto; o cartão nomeia por extenso e usa o tooltip como descrição.
    nome: str
    nome_curto: str
    tooltip: str
    slug: str
    variante_icone: VarianteIcone
    forma: FormaItem


class MenuResolvido(BaseModel):
    model_config = ConfigDict(frozen=True)

    itens: tuple[ItemRenderizavel, ...]


class RoteadorMenu:
    def __call__(self, montagem: MontagemMenu) -> MenuResolvido:
        # A ordem é a da declaração, e o menu vazio é resposta válida: quem decide o que fazer com
        # nenhum item é a tela (SPEC 006), não o router.
        return MenuResolvido(
            itens=tuple(
                self._renderizavel(item)
                for item in montagem.menu.itens
                if item.acao_implementada.acao.slug in montagem.slugs_liberados
            ),
        )

    def _renderizavel(self, item: ItemDeMenu) -> ItemRenderizavel:
        acao = item.acao_implementada.acao
        # nome_curto é opcional na ação (SPEC 001): a forma compacta cai no nome quando falta.
        return ItemRenderizavel(
            partial=item.acao_implementada.partial,
            url=reverse(item.acao_implementada.url_name),
            nome=acao.nome,
            nome_curto=acao.nome_curto or acao.nome,
            tooltip=acao.tooltip,
            slug=acao.slug,
            variante_icone=item.variante_icone,
            forma=item.forma,
        )
