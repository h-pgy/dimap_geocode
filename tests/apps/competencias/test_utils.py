"""Testes de apps/competencias/utils.py (SPEC autorizacao/001).

Cobre: instanciar_acao (composição aninhada).
"""

from services.domain.autorizacao.contratos import Acao
from apps.competencias.utils import instanciar_acao


def test_instanciar_acao_compoe_contrato_aninhado() -> None:
    # instanciar_acao achata a declaração no ponto de escrita; o contrato guarda aninhado.
    impl = instanciar_acao(
        slug="search.exportar_csv",
        nome="Exportar CSV",
        tooltip="Exporta os resultados em CSV",
        url_name="search:exportar_csv",
    )
    assert isinstance(impl.acao, Acao)
    assert impl.acao.slug == "search.exportar_csv"
    assert impl.url_name == "search:exportar_csv"
    assert impl.acao.estrutural is False


def test_instanciar_acao_compoe_estrutural() -> None:
    impl = instanciar_acao(
        slug="competencias.conceder",
        nome="Conceder competência",
        tooltip="Concede competência ao cargo",
        url_name="competencias:conceder",
        estrutural=True,
    )
    assert impl.acao.estrutural is True
