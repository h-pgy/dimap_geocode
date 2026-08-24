"""
Testes da listagem de servidores (SPEC user_admin/013): o pedido do HTMX devolve só o corpo da
tabela — é o que protege o campo em que se está digitando — e um filtro sem correspondência volta
com a linha de vazio, não com uma tabela sem linhas.

Ambos levam o marker `banco`: as linhas saem das tabelas de perfil, unidade e cargo. O que é
visual — o relevo, a bandeja, a barra gravada — se valida no mock da SPEC.
"""

from django.test import Client
from django.urls import reverse

import pytest

from apps.unidades.models import CorUnidade, TipoUnidade, Unidade
from apps.user_admin.models import CargoBase, Perfil

banco = pytest.mark.banco


def _perfil_gravado(nome: str, rf: str) -> Perfil:
    tipo, _ = TipoUnidade.objects.get_or_create(
        nome="Divisão",
        defaults={"nivel": 10, "pode_ser_raiz": True, "nivel_minimo_titular": 1},
    )
    unidade, _ = Unidade.objects.get_or_create(
        sigla="DIMAP-1",
        defaults={
            "nome": "Divisão de Mapeamento",
            "tipo": tipo,
            "cor": CorUnidade.AGUA_700,
        },
    )
    cargo, _ = CargoBase.objects.get_or_create(
        nome="Analista de Ordenamento Territorial",
        defaults={"sigla": "AOT"},
    )
    return Perfil.objects.create_user(
        rf=rf,
        nome=nome,
        sobrenome="de Tal",
        cargo_base=cargo,
        unidade=unidade,
    )


@banco
@pytest.mark.django_db
def test_listagem_htmx_devolve_apenas_o_corpo_da_tabela(client: Client) -> None:
    _perfil_gravado(nome="Marina", rf="812345")

    resposta = client.get(reverse("user_admin:corpo_servidores"), {"nome": "marina"})
    html = resposta.content.decode().strip()

    assert resposta.status_code == 200
    assert html.startswith("<tbody")
    # A página inteira destruiria o campo em foco a cada tecla: nem casca nem cabeçalho no swap.
    assert "<html" not in html
    assert "<thead" not in html
    assert "Marina" in html


@banco
@pytest.mark.django_db
def test_filtro_sem_correspondencia_devolve_estado_vazio(client: Client) -> None:
    _perfil_gravado(nome="Marina", rf="812345")

    resposta = client.get(
        reverse("user_admin:corpo_servidores"),
        {"nome": "ninguem com este nome"},
    )
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert "table-onsen-vazio" in html
    assert "Marina" not in html


@banco
@pytest.mark.django_db
def test_links_de_servidor_e_unidade_possuem_classes_de_afordancia(client: Client) -> None:
    _perfil_gravado(nome="Marina", rf="812345")

    resposta = client.get(reverse("user_admin:corpo_servidores"), {"nome": "marina"})
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert 'class="link-tabela-onsen"' in html
    assert 'class="link-sigla-onsen"' in html
