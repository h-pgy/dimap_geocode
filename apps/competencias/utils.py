from services.domain.autorizacao import Acao, TipoAlcance, VarianteIcone

from .schemas import AcaoImplementada


def instanciar_acao(
    slug: str,
    nome: str,
    tooltip: str,
    url_name: str,
    partial: str,
    nome_curto: str | None = None,
    variantes_icone: frozenset[VarianteIcone] = frozenset(),
    estrutural: bool = False,
    alcance: TipoAlcance | None = None,
) -> AcaoImplementada:
    """Achata a composição no ponto de declaração: o app da ação escreve plano, o contrato guarda
    aninhado."""
    return AcaoImplementada(
        acao=Acao(
            slug=slug,
            nome=nome,
            tooltip=tooltip,
            nome_curto=nome_curto,
            variantes_icone=variantes_icone,
            estrutural=estrutural,
            alcance=alcance,
        ),
        url_name=url_name,
        partial=partial,
    )
