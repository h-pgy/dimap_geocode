"""Página /faq/ (SPEC faq/001): visibilidade por leitor e estado vazio."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.faq.conteudo import gravar_faq
from apps.cargos.models import CargoBase
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import Perfil
from services.domain.faq import (
    Faq,
    Pergunta,
    Resposta,
    Situacao,
    Tema,
    Visibilidade,
)

banco = pytest.mark.banco

TEXTO_PUBLICA = "Pergunta publica visivel"
TEXTO_INTERNA = "Pergunta interna visivel"
TEXTO_RASCUNHO = "Pergunta em rascunho"


def _gravar(pergunta: str, visibilidade: Visibilidade, situacao: Situacao) -> None:
    gravar_faq(
        Faq(
            pergunta=Pergunta(texto=pergunta),
            resposta=Resposta(markdown="**Resposta**"),
            tema=Tema(nome="Tema único"),
            visibilidade=visibilidade,
            situacao=situacao,
        ),
    )


def _servidor() -> Perfil:
    tipo = TipoUnidade.objects.create(
        nome="Divisão FAQ",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )
    unidade = Unidade.objects.create(nome="Divisão FAQ", sigla="DIVFAQ", tipo=tipo)
    cargo = CargoBase.objects.create(nome="Analista FAQ", sigla="AFAQ")
    return Perfil.objects.create_user(
        rf="900100",
        nome="Fulano",
        sobrenome="de Tal",
        password="segredo123",
        cargo_base=cargo,
        unidade=unidade,
    )


def _popular() -> None:
    _gravar(TEXTO_PUBLICA, Visibilidade.PUBLICA, Situacao.PUBLICADA)
    _gravar(TEXTO_INTERNA, Visibilidade.INTERNA, Situacao.PUBLICADA)
    _gravar(TEXTO_RASCUNHO, Visibilidade.PUBLICA, Situacao.RASCUNHO)


@banco
@pytest.mark.django_db
def test_visibilidade_da_pagina_por_leitor(client: Client) -> None:
    _popular()
    url = reverse("faq:pagina")

    anonimo = client.get(url).content.decode()

    assert TEXTO_PUBLICA in anonimo
    assert TEXTO_INTERNA not in anonimo
    assert TEXTO_RASCUNHO not in anonimo

    client.force_login(_servidor())
    logado = client.get(url).content.decode()

    assert TEXTO_PUBLICA in logado
    assert TEXTO_INTERNA in logado
    assert TEXTO_RASCUNHO not in logado


@banco
@pytest.mark.django_db
def test_pagina_sem_faq_visivel_mostra_o_estado_vazio(client: Client) -> None:
    _gravar(TEXTO_RASCUNHO, Visibilidade.PUBLICA, Situacao.RASCUNHO)

    resposta = client.get(reverse("faq:pagina"))

    assert resposta.status_code == 200
    assert "Ainda não há perguntas públicas" in resposta.content.decode()
