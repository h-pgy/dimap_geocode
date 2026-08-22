"""
Testes das páginas administrativas de servidor (SPEC user_admin/007): o contrato HTTP/partial de
criar perfil e do modal de edição — que a SPEC user_admin/017 separou da leitura, hoje em
`test_pagina_do_servidor.py`. O que é visual (estados do poço, disco de tinta, deriva do fundo) se
valida no mock da SPEC, não aqui.

Todos levam o marker `banco`: a página de criar já monta os selects de unidade e cargos a partir
das tabelas, então nem ela renderiza sem Postgres (SPEC 007, Patch 001).
"""

import base64
from datetime import timedelta
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from django.utils import timezone

import pytest
from pytest_django.fixtures import SettingsWrapper

from apps.user_admin.exercicio import designar_substituto, registrar_impedimento
from apps.user_admin.models import (
    CargoBase,
    CargoComissao,
    CorUnidade,
    Perfil,
    TipoImpedimento,
    TipoUnidade,
    Unidade,
)
from apps.user_admin.paleta import HEX_POR_COR
from apps.user_admin.schemas import NovaSubstituicao, NovoImpedimento
from apps.user_admin.titularidade import definir_titular

banco = pytest.mark.banco

# PNG 1x1 real: o ImageField grava no storage e a view só oferece a foto que existe em disco.
PNG_MINIMO = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _perfil_gravado(cor: str, com_foto: bool, dirigente: bool = False) -> Perfil:
    tipo_unidade = TipoUnidade.objects.create(
        nome="Divisão",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )
    unidade = Unidade.objects.create(
        nome="Divisão de Avaliação",
        sigla="DIMAP-1",
        tipo=tipo_unidade,
        cor=cor,
    )
    cargo_base = CargoBase.objects.create(
        nome="Analista de Ordenamento Territorial",
        sigla="AOT",
    )
    perfil = Perfil.objects.create_user(
        rf="812345",
        nome="Fulano",
        sobrenome="de Tal",
        password="segredo123",
        cargo_base=cargo_base,
        unidade=unidade,
    )
    if com_foto:
        perfil.foto.save("retrato.png", SimpleUploadedFile("retrato.png", PNG_MINIMO))
    if dirigente:
        # `criar_perfil` é ação estrutural protegida (SPEC criacao_usuarios/004): só quem dirige a
        # unidade abre a tela.
        perfil.cargo_comissao = CargoComissao.objects.create(
            nome="Diretor Estrutural Páginas Perfil", sigla="CDE", nivel=1, e_chefia=True
        )
        perfil.save(update_fields=["cargo_comissao"])
        definir_titular(perfil)
    return perfil


@banco
@pytest.mark.django_db
def test_pagina_criar_perfil_renderiza_o_formulario(client: Client) -> None:
    # Criar servidor é ação protegida (SPEC criacao_usuarios/004): só quem dirige a abre.
    dirigente = _perfil_gravado(cor=CorUnidade.AGUA_700, com_foto=False, dirigente=True)
    client.force_login(dirigente)

    resposta = client.get(reverse("user_admin:criar_perfil"))
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert "Identificação" in html
    assert "Lotação" in html
    assert "upload-well" in html
    # Sem perfil ainda não há imagem a mostrar: a molécula grande é exclusiva da edição. Procura o
    # uso da classe, não o nome dela — o design system inteiro é servido inline pelo base.html.
    assert 'class="avatar-glass' not in html


@banco
@pytest.mark.django_db
def test_pagina_admin_nao_carrega_o_wms_do_geosampa(client: Client) -> None:
    dirigente = _perfil_gravado(cor=CorUnidade.AGUA_700, com_foto=False, dirigente=True)
    client.force_login(dirigente)

    html = client.get(reverse("user_admin:criar_perfil")).content.decode()

    assert 'id="map-admin"' in html
    assert "mapa-wms" not in html
    assert "geosampa" not in html.lower()


@banco
@pytest.mark.django_db
def test_editar_perfil_sem_foto_mostra_avatar_de_iniciais(client: Client) -> None:
    perfil = _perfil_gravado(cor=CorUnidade.SAKURA_600, com_foto=False)

    html = client.get(
        reverse("user_admin:editar_perfil", kwargs={"pk": perfil.pk})
    ).content.decode()

    assert ">FT<" in html
    assert f"--cor-unidade: {HEX_POR_COR[CorUnidade.SAKURA_600]}" in html


@banco
@pytest.mark.django_db
def test_editar_perfil_com_foto_mostra_a_foto(
    client: Client,
    settings: SettingsWrapper,
    tmp_path: Path,
) -> None:
    # A foto vai para um MEDIA_ROOT descartável: a view só oferece o arquivo que existe no storage.
    settings.MEDIA_ROOT = tmp_path
    perfil = _perfil_gravado(cor=CorUnidade.AGUA_700, com_foto=True)

    html = client.get(
        reverse("user_admin:editar_perfil", kwargs={"pk": perfil.pk})
    ).content.decode()

    assert perfil.foto.url in html
    assert ">FT<" not in html


# ---------------------------------------------------------------------------
# Campo de seleção de vidro (SPEC user_admin/011). O comportamento de navegador — abrir, filtrar,
# andar com as setas — se valida no mock; o que pode regredir sem ninguém ver é o contrato do
# servidor: um <select> de verdade, marcado para o componente, com o módulo carregado na página.
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_selects_da_lotacao_usam_o_componente_de_vidro(client: Client) -> None:
    dirigente = _perfil_gravado(cor=CorUnidade.AGUA_700, com_foto=False, dirigente=True)
    client.force_login(dirigente)
    CargoComissao.objects.create(
        nome="Diretor de Divisão",
        sigla="CDA",
        nivel=2,
        e_chefia=True,
    )

    html = client.get(reverse("user_admin:criar_perfil")).content.decode()

    for campo in ("unidade", "cargo_base", "cargo_comissao"):
        assert (
            f'<select name="{campo}" class="select select-glass" data-select-onsen>'
            in html
        )
    assert "DIMAP-1 · Divisão de Avaliação" in html
    assert "Analista de Ordenamento Territorial" in html
    assert "CDA-II · Diretor de Divisão" in html
    assert "js/ui/select_onsen.js" in html


@banco
@pytest.mark.django_db
def test_select_de_unidade_mantem_a_opcao_selecionada_na_edicao(client: Client) -> None:
    perfil = _perfil_gravado(cor=CorUnidade.AGUA_700, com_foto=False)

    html = client.get(
        reverse("user_admin:editar_perfil", kwargs={"pk": perfil.pk})
    ).content.decode()

    # É da <option selected> que a casca lê o rótulo inicial do gatilho.
    assert (
        f'<option value="{perfil.unidade_id}" selected>DIMAP-1 · Divisão de Avaliação</option>'
        in html
    )


# ---------------------------------------------------------------------------
# Seção de exercício e substituição (SPEC user_admin/015): nenhuma rota nova — a seção entra no
# contexto que a página de leitura do servidor renderiza (SPEC user_admin/017; § Fora de escopo:
# nenhum submit tem destino).
# ---------------------------------------------------------------------------


def _unidade_exercicio(sigla: str, **overrides: object) -> Unidade:
    tipo, _ = TipoUnidade.objects.get_or_create(
        nome="Divisão Seção Exercício",
        defaults={"nivel": 10, "pode_ser_raiz": True, "nivel_minimo_titular": 1},
    )
    dados: dict[str, object] = {
        "nome": f"Divisão {sigla}",
        "sigla": sigla,
        "tipo": tipo,
    }
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _perfil_exercicio(
    unidade: Unidade, rf: str, nome: str, **overrides: object
) -> Perfil:
    cargo_base, _ = CargoBase.objects.get_or_create(
        nome="Cargo Seção Exercício", sigla="CGSE"
    )
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Seção",
        "cargo_base": cargo_base,
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


@banco
@pytest.mark.django_db
def test_secao_mostra_a_agenda_do_afastamento(client: Client) -> None:
    unidade = _unidade_exercicio("DIVSE")
    tipo_impedimento = TipoImpedimento.objects.create(nome="Férias Seção")
    hoje = timezone.localdate()

    # Cartão com histórico: encerrada, vigente e futura, em ordem cronológica.
    afastado = _perfil_exercicio(
        unidade,
        "700601",
        "Afastado",
        cargo_comissao=CargoComissao.objects.create(
            sigla="CDA", nivel=1, e_chefia=True, nome="Diretor Seção Exercício"
        ),
    )
    impedimento = registrar_impedimento(
        afastado,
        NovoImpedimento(
            tipo=tipo_impedimento.pk,
            data_inicio=hoje - timedelta(days=10),
            data_fim=hoje + timedelta(days=20),
        ),
    )
    encerrada_substituto = _perfil_exercicio(unidade, "700602", "Encerrada")
    designar_substituto(
        impedimento,
        NovaSubstituicao(
            substituto=encerrada_substituto.pk,
            data_inicio=hoje - timedelta(days=10),
            data_fim=hoje - timedelta(days=1),
        ),
    )
    vigente_substituto = _perfil_exercicio(unidade, "700603", "Vigente")
    designar_substituto(
        impedimento,
        NovaSubstituicao(
            substituto=vigente_substituto.pk,
            data_inicio=hoje,
            data_fim=hoje + timedelta(days=20),
        ),
    )

    html_afastado = client.get(
        reverse("user_admin:pagina_perfil", kwargs={"pk": afastado.pk})
    ).content.decode()
    assert "Afastado" in html_afastado
    assert (
        f"{encerrada_substituto.nome} {encerrada_substituto.sobrenome}" in html_afastado
    )
    assert f"{vigente_substituto.nome} {vigente_substituto.sobrenome}" in html_afastado
    assert html_afastado.index(encerrada_substituto.nome) < html_afastado.index(
        vigente_substituto.nome
    )

    # Impedimento futuro com substituto já designado: a pessoa segue "em exercício" — não é
    # afastado ainda —, e a cobertura que vem já aparece.
    futuro_afastado = _perfil_exercicio(
        unidade,
        "700604",
        "Futuro",
        cargo_comissao=CargoComissao.objects.create(
            sigla="CDB", nivel=1, e_chefia=True, nome="Diretor Futuro Seção"
        ),
    )
    impedimento_futuro = registrar_impedimento(
        futuro_afastado,
        NovoImpedimento(
            tipo=tipo_impedimento.pk,
            data_inicio=hoje + timedelta(days=30),
            data_fim=hoje + timedelta(days=40),
        ),
    )
    ja_designado = _perfil_exercicio(unidade, "700605", "JaDesignado")
    designar_substituto(
        impedimento_futuro, NovaSubstituicao(substituto=ja_designado.pk)
    )

    html_futuro = client.get(
        reverse("user_admin:pagina_perfil", kwargs={"pk": futuro_afastado.pk})
    ).content.decode()
    assert "Em exercício" in html_futuro
    assert f"{ja_designado.nome} {ja_designado.sobrenome}" in html_futuro

    # Exonerado: mesma causa de estar fora da cadeira, palavra diferente do afastado.
    exonerado = _perfil_exercicio(unidade, "700606", "Exonerado")
    exonerado.is_active = False
    exonerado.save(update_fields=["is_active"])

    html_exonerado = client.get(
        reverse("user_admin:pagina_perfil", kwargs={"pk": exonerado.pk})
    ).content.decode()
    assert "Exonerado" in html_exonerado


@banco
@pytest.mark.django_db
def test_modal_de_designar_propoe_a_lacuna_e_os_candidatos(client: Client) -> None:
    tipo_superior = TipoUnidade.objects.create(
        nome="Coordenadoria Modal Exercício",
        nivel=20,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )
    unidade_superior = Unidade.objects.create(
        nome="Coordenadoria Modal Exercício", sigla="DIVSUP", tipo=tipo_superior
    )
    unidade_propria = _unidade_exercicio("DIVPROP", pai=unidade_superior)
    hoje = timezone.localdate()
    tipo_impedimento = TipoImpedimento.objects.create(nome="Férias Modal")

    substituido = _perfil_exercicio(
        unidade_propria,
        "700610",
        "Substituído",
        cargo_comissao=CargoComissao.objects.create(
            sigla="CDA", nivel=1, e_chefia=True, nome="Diretor Modal Exercício"
        ),
    )
    impedimento = registrar_impedimento(
        substituido,
        NovoImpedimento(
            tipo=tipo_impedimento.pk,
            data_inicio=hoje,
            data_fim=hoje + timedelta(days=14),
        ),
    )

    # Impedido na própria unidade: não entra na lista de candidatos.
    impedido = _perfil_exercicio(unidade_propria, "700611", "Impedido")
    registrar_impedimento(
        impedido,
        NovoImpedimento(tipo=tipo_impedimento.pk, data_inicio=hoje, data_fim=None),
    )

    # Livre na própria unidade: entra.
    livre = _perfil_exercicio(unidade_propria, "700612", "Livre")

    # Só aparece com o alcance ampliado, e a unidade superior vem primeiro.
    da_unidade_superior = _perfil_exercicio(unidade_superior, "700613", "DaSuperior")

    html = client.get(
        reverse("user_admin:pagina_perfil", kwargs={"pk": substituido.pk})
    ).content.decode()

    # As datas do diálogo já vêm preenchidas com a lacuna proposta — aqui, o impedimento inteiro,
    # porque ainda não há nenhuma substituição.
    assert f'value="{impedimento.data_inicio.isoformat()}"' in html
    assert impedimento.data_fim is not None
    assert f'value="{impedimento.data_fim.isoformat()}"' in html

    assert f'value="{livre.pk}"' in html
    assert f'value="{impedido.pk}"' not in html
    assert f'value="{da_unidade_superior.pk}"' in html
