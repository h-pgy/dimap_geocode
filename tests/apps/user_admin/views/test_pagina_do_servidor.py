"""
Testes da página do servidor (SPEC user_admin/017): o resumo em leitura, o modal de edição buscado
por rota própria e o painel de cadastro de unidade que cresce dentro dele. Todos fixam contrato
HTTP/partial e tocam o banco — os selects do modal e o resumo são montados a partir das tabelas. A
montagem da seção de exercício já é testada na SPEC 015 e não se repete aqui.
"""

import re
from datetime import timedelta

from django.test import Client
from django.urls import reverse
from django.utils import timezone

import pytest

from apps.user_admin.exercicio import registrar_impedimento
from apps.user_admin.models import (
    CargoBase,
    CargoComissao,
    Perfil,
    TipoImpedimento,
    TipoUnidade,
    Unidade,
)
from apps.user_admin.schemas import NovoImpedimento
from apps.user_admin.titularidade import definir_titular

banco = pytest.mark.banco

# Um <form> aberto antes do anterior fechar é aninhamento — o navegador descarta o interno.
ABERTURA_OU_FECHAMENTO_DE_FORM = re.compile(r"</?form\b")


def _tipo(sigla: str) -> TipoUnidade:
    return TipoUnidade.objects.create(
        nome=f"Tipo {sigla}",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )


def _unidade(sigla: str) -> Unidade:
    return Unidade.objects.create(nome=f"Divisão {sigla}", sigla=sigla, tipo=_tipo(sigla))


def _cargo_base() -> CargoBase:
    cargo, _ = CargoBase.objects.get_or_create(
        nome="Analista de Ordenamento Territorial", defaults={"sigla": "AOT"}
    )
    return cargo


def _perfil(
    unidade: Unidade,
    rf: str,
    nome: str = "Fulano",
    sobrenome: str = "de Tal",
    cargo_comissao: CargoComissao | None = None,
) -> Perfil:
    return Perfil.objects.create_user(
        rf=rf,
        nome=nome,
        sobrenome=sobrenome,
        password="segredo123",
        cargo_base=_cargo_base(),
        unidade=unidade,
        cargo_comissao=cargo_comissao,
    )


@banco
@pytest.mark.django_db
def test_pagina_do_servidor_traz_o_resumo_em_leitura(client: Client) -> None:
    unidade = _unidade("SRV1")
    cargo_comissao = CargoComissao.objects.create(
        sigla="CDA", nivel=2, e_chefia=True, nome="Diretora de Divisão SRV1"
    )
    perfil = _perfil(unidade, "900001", "Marcos", "Vieira", cargo_comissao=cargo_comissao)

    resposta = client.get(reverse("user_admin:pagina_perfil", kwargs={"pk": perfil.pk}))
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert perfil.rf in html
    assert "Marcos Vieira" in html
    assert unidade.sigla in html
    assert perfil.cargo_base.nome in html
    assert "CDA-II · Diretora de Divisão SRV1" in html
    assert reverse("user_admin:pagina_unidade", kwargs={"pk": unidade.pk}) in html
    # Resumo é leitura: nenhum campo de formulário do cadastro fora do modal.
    assert 'name="rf"' not in html


@banco
@pytest.mark.django_db
def test_resumo_diz_o_que_o_servidor_nao_tem(client: Client) -> None:
    sem_nada = _perfil(_unidade("SRV2"), "900002", "Sem", "Titularidade")

    html_sem_nada = client.get(
        reverse("user_admin:pagina_perfil", kwargs={"pk": sem_nada.pk})
    ).content.decode()
    assert "— sem cargo em comissão —" in html_sem_nada
    assert "Não é titular de unidade alguma." in html_sem_nada

    unidade_titular = _unidade("SRV3")
    cargo = CargoComissao.objects.create(
        sigla="CDA", nivel=1, e_chefia=True, nome="Diretora de Divisão SRV3"
    )
    titular = _perfil(unidade_titular, "900003", "Titular", "Da Casa", cargo_comissao=cargo)
    definir_titular(titular)

    html_titular = client.get(
        reverse("user_admin:pagina_perfil", kwargs={"pk": titular.pk})
    ).content.decode()
    assert f"Titular da {unidade_titular.sigla}" in html_titular


@banco
@pytest.mark.django_db
def test_rota_do_modal_devolve_so_o_partial_preenchido(client: Client) -> None:
    unidade = _unidade("SRV4")
    outra_unidade = _unidade("SRV5")
    cargo_comissao = CargoComissao.objects.create(
        sigla="CDA", nivel=3, e_chefia=True, nome="Diretora de Divisão SRV4"
    )
    perfil = _perfil(unidade, "900004", "Helena", "Prado", cargo_comissao=cargo_comissao)
    # Editar servidor é ação protegida (SPEC criacao_usuarios/005): quem dirige a própria unidade
    # abre o próprio cadastro sem concessão gravada.
    definir_titular(perfil)
    client.force_login(perfil)

    html = client.get(
        reverse("user_admin:editar_perfil", kwargs={"servidor": perfil.pk})
    ).content.decode()

    assert '<input type="checkbox" id="modal-editar-perfil" class="modal-toggle" checked />' in html
    assert "<!doctype html>" not in html.lower()
    assert "action=" not in html
    assert perfil.rf in html
    assert (
        f'<option value="{unidade.pk}" selected>{unidade.sigla} · {unidade.nome}</option>'
        in html
    )
    # Fora do alcance de quem edita, e por isso fora do select (SPEC criacao_usuarios/006).
    assert f"{outra_unidade.sigla} · {outra_unidade.nome}" not in html
    assert f'<option value="{perfil.cargo_base_id}" selected>' in html
    assert (
        f'<option value="{cargo_comissao.pk}" selected>{cargo_comissao.padrao} · {cargo_comissao.nome}</option>'
        in html
    )


@banco
@pytest.mark.django_db
def test_pagina_do_servidor_nao_carrega_o_modal(client: Client) -> None:
    cargo_comissao = CargoComissao.objects.create(
        sigla="CDA", nivel=1, e_chefia=True, nome="Diretora de Divisão SRV6"
    )
    perfil = _perfil(_unidade("SRV6"), "900006", "Sem", "Modal", cargo_comissao=cargo_comissao)
    # O botão de editar (e o link por trás dele) só aparece a quem tem a competência e o alcance.
    definir_titular(perfil)
    client.force_login(perfil)

    html = client.get(
        reverse("user_admin:pagina_perfil", kwargs={"pk": perfil.pk})
    ).content.decode()

    assert '<div id="poco-modal" class="poco-modal"></div>' in html
    assert reverse("user_admin:editar_perfil", kwargs={"servidor": perfil.pk}) in html
    assert 'name="rf"' not in html
    assert 'id="modal-editar-perfil"' not in html


@banco
@pytest.mark.django_db
def test_modal_traz_o_painel_de_unidade_fechado_e_com_formulario_proprio(
    client: Client,
) -> None:
    unidade = _unidade("SRV7")
    _tipo("SRV8")
    cargo_comissao = CargoComissao.objects.create(
        sigla="CDA", nivel=1, e_chefia=True, nome="Diretora de Divisão SRV7"
    )
    perfil = _perfil(unidade, "900007", "Painel", "Fechado", cargo_comissao=cargo_comissao)
    definir_titular(perfil)
    client.force_login(perfil)

    html = client.get(
        reverse("user_admin:editar_perfil", kwargs={"servidor": perfil.pk})
    ).content.decode()

    assert "Tipo SRV8" in html
    assert '<input type="checkbox" id="painel-nova-unidade" class="painel-onsen-toggle" />' in html
    assert 'name="nome" form="form-nova-unidade"' in html
    assert 'name="sigla" form="form-nova-unidade"' in html
    assert 'name="tipo" form="form-nova-unidade"' in html
    assert 'name="pai" form="form-nova-unidade"' in html
    assert 'name="cor" value="agua-700" form="form-nova-unidade"' in html

    marcas = ABERTURA_OU_FECHAMENTO_DE_FORM.findall(html)
    assert marcas == ["<form", "</form", "<form", "</form"]


@banco
@pytest.mark.django_db
def test_pagina_do_servidor_mantem_a_secao_de_exercicio(client: Client) -> None:
    tipo_impedimento = TipoImpedimento.objects.create(nome="Férias SPEC017")
    afastado = _perfil(_unidade("SRV9"), "900009", "Afastado", "Servidor")
    registrar_impedimento(
        afastado,
        NovoImpedimento(
            tipo=tipo_impedimento.pk,
            data_inicio=timezone.localdate() - timedelta(days=1),
            data_fim=None,
        ),
    )

    html = client.get(
        reverse("user_admin:pagina_perfil", kwargs={"pk": afastado.pk})
    ).content.decode()

    assert "Afastado" in html
    assert "Férias SPEC017" in html
    assert 'id="modal-impedimento"' in html
    assert 'id="modal-editar-perfil"' not in html


@banco
@pytest.mark.django_db
def test_criar_servidor_mantem_a_mesma_estrutura_de_formulario(client: Client) -> None:
    # Criar servidor virou ação protegida na SPEC criacao_usuarios/004 — quem exerce a
    # autenticação e a autorização é `tests/apps/user_admin/views/test_criar_servidor.py`; aqui
    # só se fixa que a estrutura do formulário em si não mudou.
    dirigente = _perfil(
        _unidade("SRV-CRIAR"),
        "900099",
        "Dirigente",
        "Criar Servidor",
        cargo_comissao=CargoComissao.objects.create(
            sigla="CDC", nivel=1, e_chefia=True, nome="Diretor Criar Servidor Aberto"
        ),
    )
    definir_titular(dirigente)
    client.force_login(dirigente)

    html = client.get(reverse("user_admin:criar_perfil")).content.decode()

    assert "Identificação" in html
    assert "Lotação" in html
    assert 'id="modal-editar-perfil"' not in html
    assert "Exercício" not in html
    # A molécula grande é exclusiva de quem já tem foto/perfil gravado.
    assert 'class="avatar-glass' not in html


@banco
@pytest.mark.django_db
def test_caminhos_levam_a_pagina_do_servidor(client: Client) -> None:
    unidade = _unidade("SRVA")
    cargo_comissao = CargoComissao.objects.create(
        sigla="CDA", nivel=1, e_chefia=True, nome="Diretora de Divisão SRVA"
    )
    titular = _perfil(unidade, "900010", "Titular", "Caminho", cargo_comissao=cargo_comissao)
    definir_titular(titular)

    html_listagem = client.get(reverse("user_admin:listar_servidores")).content.decode()
    assert reverse("user_admin:pagina_perfil", kwargs={"pk": titular.pk}) in html_listagem
    assert reverse("user_admin:editar_perfil", kwargs={"servidor": titular.pk}) not in html_listagem

    html_unidade = client.get(
        reverse("user_admin:pagina_unidade", kwargs={"pk": unidade.pk})
    ).content.decode()
    assert reverse("user_admin:pagina_perfil", kwargs={"pk": titular.pk}) in html_unidade
    assert reverse("user_admin:editar_perfil", kwargs={"servidor": titular.pk}) not in html_unidade
