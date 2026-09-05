"""
Testes do formulário de unidade (SPEC user_admin/012): a página própria, o modal dentro da página
de criar servidor e a troca do campo de cor pela unidade superior. Editar servidor passou a montar
o cadastro de unidade como painel dentro do próprio modal de edição (SPEC user_admin/017), testado
em test_pagina_do_servidor.py. O que é visual — a placa de gelo do modal, o embaçamento do fundo, o
brilho do botão — se valida no mock da SPEC.

Todos levam o marker `banco`: os selects são montados a partir das tabelas.
"""

import re

from django.test import Client
from django.urls import reverse

import pytest

from apps.unidades.models import CorUnidade, TipoUnidade, Unidade
from apps.cargos.models import CargoBase, CargoComissao
from apps.user_admin.models import Perfil
from apps.unidades.titularidade import definir_titular

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


def _dirigente_de(unidade: Unidade) -> Perfil:
    # Criar servidor é ação protegida (SPEC criacao_usuarios/004): as duas telas abaixo que
    # abrem `criar_perfil` (e o modal de unidade dentro dela) precisam de quem dirige.
    cargo_base, _ = CargoBase.objects.get_or_create(
        nome="Analista de Ordenamento Territorial", defaults={"sigla": "AOT"}
    )
    perfil = Perfil.objects.create_user(
        rf="900098",
        nome="Dirigente",
        sobrenome="Modal Unidade",
        password="segredo123",
        cargo_base=cargo_base,
        unidade=unidade,
        cargo_comissao=CargoComissao.objects.create(
            sigla="CDM", nivel=1, e_chefia=True, nome="Diretor Modal Unidade"
        ),
    )
    definir_titular(perfil)
    return perfil


def _radio_do_tom(slug: str) -> str:
    # form="form-nova-unidade" desde a SPEC user_admin/017: cada campo do cadastro de unidade
    # declara o formulário a que pertence, porque o painel da página do servidor o mantém fora
    # do formulário do servidor.
    return f'<input type="radio" name="cor" value="{slug}" form="form-nova-unidade" class="sr-only"'


@banco
@pytest.mark.django_db
def test_pagina_criar_unidade_renderiza_o_formulario(client: Client) -> None:
    # Criar unidade é ação estrutural protegida desde a SPEC user_admin/020: quem abre a tela
    # precisa dirigir alguma unidade.
    unidade = _unidade_gravada(cor=CorUnidade.ROCHA_700)
    client.force_login(_dirigente_de(unidade))

    resposta = client.get(reverse("unidades:criar_unidade"))
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
def test_pagina_de_criar_perfil_traz_o_modal_de_unidade(client: Client) -> None:
    # O modal precisa dos catálogos: sem eles o disco de paleta nasce sem tons e o select de tipo,
    # vazio. O modal de EDITAR servidor passou a montar o cadastro de unidade como painel dentro de
    # si mesmo (SPEC user_admin/017) — testado em test_pagina_do_servidor.py.
    unidade = _unidade_gravada(cor=CorUnidade.ROCHA_700)
    client.force_login(_dirigente_de(unidade))

    html = client.get(reverse("user_admin:criar_perfil")).content.decode()

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
    unidade = _unidade_gravada(cor=CorUnidade.ROCHA_700)
    client.force_login(_dirigente_de(unidade))

    html = client.get(reverse("user_admin:criar_perfil")).content.decode()

    marcas = ABERTURA_OU_FECHAMENTO_DE_FORM.findall(html)

    assert marcas == ["<form", "</form", "<form", "</form"]


@banco
@pytest.mark.django_db
def test_campo_de_cor_assume_a_cor_da_unidade_superior(client: Client) -> None:
    pai = _unidade_gravada(cor=CorUnidade.ROCHA_700)

    resposta = client.get(
        reverse("unidades:cor_sugerida_unidade"),
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
        reverse("unidades:cor_sugerida_unidade"),
        {"pai": ""},
    )
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert f"{_radio_do_tom(CorUnidade.AGUA_700)} checked>" in html
    assert f"{_radio_do_tom(CorUnidade.ROCHA_700)}>" in html
