"""Renderização da página /faq/ (SPEC faq/001), sem banco: o que o template faz com o índice."""

import pytest
from django.test import Client
from django.urls import reverse
from pydantic import HttpUrl

from services.domain.faq import (
    Faq,
    LinkDoSistema,
    LinkExterno,
    LinkReferencia,
    Pergunta,
    Resposta,
    Situacao,
    Tema,
    Visibilidade,
)


def _faq(id: int, pergunta: str, **overrides: object) -> Faq:
    dados: dict[str, object] = {
        "id": id,
        "pergunta": Pergunta(texto=pergunta),
        "resposta": Resposta(markdown="**Resposta** <script>alert(1)</script>"),
        "tema": Tema(nome="Certidões"),
        "situacao": Situacao.PUBLICADA,
    }
    dados.update(overrides)
    return Faq(**dados)  # type: ignore[arg-type]


@pytest.fixture
def faqs_no_banco(monkeypatch: pytest.MonkeyPatch) -> list[Faq]:
    faqs = [
        _faq(
            1,
            "Como confiro uma certidão?",
            relacionadas=[2, 3],
            resposta=Resposta(
                markdown="**Resposta** <script>alert(1)</script>",
                links=[
                    LinkReferencia(
                        titulo="Conferir um documento",
                        destino=LinkDoSistema(caminho="/documentos/"),
                    ),
                    LinkReferencia(
                        titulo="Portal da Prefeitura",
                        destino=LinkExterno(
                            url=HttpUrl("https://www.prefeitura.sp.gov.br/")
                        ),
                    ),
                ],
            ),
        ),
        _faq(2, "Quem emite a certidão?"),
        _faq(3, "Quem vê esta pergunta?", visibilidade=Visibilidade.INTERNA),
    ]
    monkeypatch.setattr(
        "apps.faq.pagina.views.carregar_faqs", lambda _visibilidades: faqs
    )
    return faqs


def test_pagina_renderiza_resposta_links_e_relacionadas(
    client: Client,
    faqs_no_banco: list[Faq],
) -> None:
    html = client.get(reverse("faq:pagina")).content.decode()

    assert "<strong>Resposta</strong>" in html
    assert "<script>alert(1)" not in html
    # Do sistema abre na mesma aba; o externo, em aba nova.
    assert 'href="/documentos/" class="item-menu"' in html
    assert 'href="https://www.prefeitura.sp.gov.br/" target="_blank"' in html
    assert 'href="#faq-2"' in html
    # A interna é podada para o visitante: nem como link, nem como pergunta.
    assert 'href="#faq-3"' not in html
    assert "Quem vê esta pergunta?" not in html


def test_pagina_sem_faq_visivel_mostra_o_estado_vazio_sem_banco(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "apps.faq.pagina.views.carregar_faqs", lambda _visibilidades: []
    )

    html = client.get(reverse("faq:pagina")).content.decode()

    assert "Ainda não há perguntas públicas" in html
    assert "faq-conjunto" not in html
