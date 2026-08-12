"""
Testes do formulário de unidade (SPEC user_admin/012): a página própria, o modal dentro da página
de servidor e a troca do campo de cor pela unidade superior. O que é visual — a placa de gelo do
modal, o embaçamento do fundo, o brilho do botão — se valida no mock da SPEC.

Todos levam o marker `banco`: os selects são montados a partir das tabelas.
"""

import re

from django.test import Client
from django.urls import reverse

import pytest

from apps.user_admin.models import CargoBase, CorUnidade, Perfil, TipoUnidade, Unidade

banco = pytest.mark.banco

# Um <form> aberto antes do anterior fechar é aninhamento — o navegador descarta o interno.
ABERTURA_OU_FECHAMENTO_DE_FORM = re.compile(r"</?form\b")


def _unidade_gravada(cor: str) -> Unidade:
    tipo = TipoUnidade.objects.create(
        nome="Coordenadoria",
        nivel=20,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )
    return Unidade.objects.create(
        nome="Coordenadoria de Gestão Territorial",
        sigla="SUREM",
        tipo=tipo,
        cor=cor,
    )


def _perfil_gravado(unidade: Unidade) -> Perfil:
    cargo_base = CargoBase.objects.create(
        nome="Analista de Ordenamento Territorial",
        sigla="AOT",
    )
    return Perfil.objects.create_user(
        rf="812345",
        nome="Fulano",
        sobrenome="de Tal",
        password="segredo123",
        cargo_base=cargo_base,
        unidade=unidade,
    )


def _radio_do_tom(slug: str) -> str:
    return f'<input type="radio" name="cor" value="{slug}" class="sr-only"'


@banco
@pytest.mark.django_db
def test_pagina_criar_unidade_renderiza_o_formulario(client: Client) -> None:
    _unidade_gravada(cor=CorUnidade.ROCHA_700)

    resposta = client.get(reverse("user_admin:criar_unidade"))
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert "Identificação" in html
    assert "Hierarquia" in html
    assert "Identidade visual" in html
    assert "palette-disc" in html
    assert 'id="campo-cor-unidade"' in html
    # A hierarquia é montada das tabelas: tipo e unidade superior vêm do banco.
    assert "Coordenadoria" in html
    assert "SUREM · Coordenadoria de Gestão Territorial" in html


@banco
@pytest.mark.django_db
@pytest.mark.parametrize("pagina", ["criar", "editar"])
def test_pagina_de_perfil_traz_o_modal_de_unidade(client: Client, pagina: str) -> None:
    # Criar e editar servidor renderizam o mesmo organismo: o modal precisa dos catálogos nas duas
    # — sem eles o disco de paleta nasce sem tons e o select de tipo, vazio.
    unidade = _unidade_gravada(cor=CorUnidade.ROCHA_700)
    url = (
        reverse("user_admin:criar_perfil")
        if pagina == "criar"
        else reverse(
            "user_admin:editar_perfil",
            kwargs={"pk": _perfil_gravado(unidade).pk},
        )
    )

    html = client.get(url).content.decode()

    assert 'for="modal-nova-unidade"' in html
    assert 'id="modal-nova-unidade"' in html
    assert "modal-box-glass" in html
    # Os mesmos campos da página própria, do mesmo partial.
    assert "Nova unidade" in html
    assert "Identidade visual" in html
    assert 'id="campo-cor-unidade"' in html
    assert html.count('class="paint-well"') == len(CorUnidade)
    assert f'<option value="{unidade.tipo_id}">Coordenadoria</option>' in html


@banco
@pytest.mark.django_db
def test_modal_de_unidade_nao_aninha_formulario(client: Client) -> None:
    _unidade_gravada(cor=CorUnidade.ROCHA_700)

    html = client.get(reverse("user_admin:criar_perfil")).content.decode()

    marcas = ABERTURA_OU_FECHAMENTO_DE_FORM.findall(html)

    assert marcas == ["<form", "</form", "<form", "</form"]


@banco
@pytest.mark.django_db
def test_campo_de_cor_assume_a_cor_da_unidade_superior(client: Client) -> None:
    pai = _unidade_gravada(cor=CorUnidade.ROCHA_700)

    resposta = client.get(
        reverse("user_admin:cor_sugerida_unidade"),
        {"pai": pai.pk},
    )
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert f"{_radio_do_tom(CorUnidade.ROCHA_700)} checked>" in html
    assert f"{_radio_do_tom(CorUnidade.AGUA_700)}>" in html


@banco
@pytest.mark.django_db
def test_campo_de_cor_sem_unidade_superior_volta_ao_tom_padrao(client: Client) -> None:
    # "" é o que o select manda na opção raiz — o DTO o traduz para nulo.
    resposta = client.get(
        reverse("user_admin:cor_sugerida_unidade"),
        {"pai": ""},
    )
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert f"{_radio_do_tom(CorUnidade.AGUA_700)} checked>" in html
    assert f"{_radio_do_tom(CorUnidade.ROCHA_700)}>" in html
