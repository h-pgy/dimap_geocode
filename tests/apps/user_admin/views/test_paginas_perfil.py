"""
Testes das páginas administrativas de servidor (SPEC user_admin/007): o contrato HTTP/partial de
criar e editar perfil. O que é visual (estados do poço, disco de tinta, deriva do fundo) se valida
no mock da SPEC, não aqui.

Todos levam o marker `banco`: a página de criar já monta os selects de unidade e cargos a partir
das tabelas, então nem ela renderiza sem Postgres (SPEC 007, Patch 001).
"""

import base64
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

import pytest
from pytest_django.fixtures import SettingsWrapper

from apps.user_admin.models import CargoBase, CorUnidade, Perfil, TipoUnidade, Unidade
from apps.user_admin.paleta import HEX_POR_COR

banco = pytest.mark.banco

# PNG 1x1 real: o ImageField grava no storage e a view só oferece a foto que existe em disco.
PNG_MINIMO = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _perfil_gravado(cor: str, com_foto: bool) -> Perfil:
    tipo_unidade = TipoUnidade.objects.create(
        nome="Divisão",
        nivel=10,
        pode_ser_raiz=True,
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
    return perfil


@banco
@pytest.mark.django_db
def test_pagina_criar_perfil_renderiza_o_formulario(client: Client) -> None:
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
