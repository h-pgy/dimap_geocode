"""Resolução do destino de um link de referência (SPEC faq/001)."""

import pytest
from pydantic import HttpUrl, ValidationError

from services.domain.faq import LinkDoSistema, LinkExterno, resolver_destino

DOMINIOS = frozenset({"localhost"})


@pytest.mark.parametrize(
    ("url", "esperado"),
    [
        ("/certidoes/", LinkDoSistema(caminho="/certidoes/")),
        ("https://localhost/certidoes/?x=1", LinkDoSistema(caminho="/certidoes/?x=1")),
        (
            "https://www.prefeitura.sp.gov.br/",
            LinkExterno(url=HttpUrl("https://www.prefeitura.sp.gov.br/")),
        ),  # type: ignore[arg-type]
    ],
)
def test_resolver_destino_classifica_o_link(
    url: str,
    esperado: LinkDoSistema | LinkExterno,
) -> None:
    assert resolver_destino(url, DOMINIOS) == esperado


@pytest.mark.parametrize(
    "url", ["//site.com", "javascript:alert(1)", "https://", "certidoes"]
)
def test_resolver_destino_recusa_o_que_nao_eh_link(url: str) -> None:
    with pytest.raises(ValidationError):
        resolver_destino(url, DOMINIOS)
