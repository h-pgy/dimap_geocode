"""
Testes da página e corpo da listagem de unidades (SPEC user_admin/021):
- Página completa em `/gestao/unidades/` renderiza fundo, organograma no topo e tabela de unidades.
- Rota antiga `/gestao/unidades/arvore/` redireciona para `/gestao/unidades/`.
- `?foco=<pk>` abre a árvore no ego e a tabela com a linha da unidade no topo; `?foco=` forjado
  abre a listagem inteira em vez de derrubar a página.
- Requisição HTMX em `/gestao/unidades/corpo/` devolve estritamente o `<tbody>` filtrado sem `<head>` nem `<thead>`.
- Filtro sem correspondência devolve o estado vazio `.table-onsen-vazio`.
- Links de sigla, titular e subordinação são renderizados apontando para as respectivas páginas.

Todos levam o marker `banco`: as unidades e titulares saem do banco PostGIS de testes.
"""

from django.test import Client
from django.urls import reverse

import pytest

from apps.unidades.models import CorUnidade, TipoUnidade, Unidade
from apps.cargos.models import CargoBase
from apps.user_admin.models import Perfil

banco = pytest.mark.banco


def _criar_cenario_unidades() -> tuple[Unidade, Unidade, Perfil]:
    tipo_sec, _ = TipoUnidade.objects.get_or_create(
        nome="Secretaria",
        defaults={"nivel": 1, "pode_ser_raiz": True, "nivel_minimo_titular": 1},
    )
    tipo_div, _ = TipoUnidade.objects.get_or_create(
        nome="Divisão",
        defaults={"nivel": 10, "pode_ser_raiz": False, "nivel_minimo_titular": 1},
    )
    cargo, _ = CargoBase.objects.get_or_create(
        nome="Auditor-Fiscal Tributário Municipal",
        defaults={"sigla": "AFTM"},
    )

    secretaria = Unidade.objects.create(
        sigla="SF",
        nome="Secretaria Municipal da Fazenda",
        tipo=tipo_sec,
        cor=CorUnidade.AGUA_700,
    )
    divisao = Unidade.objects.create(
        sigla="DIMAP",
        nome="Divisão de Mapeamento",
        tipo=tipo_div,
        cor=CorUnidade.MADEIRA_700,
        pai=secretaria,
    )
    titular = Perfil.objects.create_user(
        rf="8123456",
        nome="Beatriz",
        sobrenome="Silva",
        cargo_base=cargo,
        unidade=divisao,
        e_titular=True,
    )

    return secretaria, divisao, titular


# ---------------------------------------------------------------------------
# Página completa e redirecionamento
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_pagina_unidades_renderiza_organograma_e_tabela(client: Client) -> None:
    _criar_cenario_unidades()

    resposta = client.get(reverse("unidades:listar_unidades"))
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert "Unidades" in html
    assert "SF" in html
    assert "DIMAP" in html
    assert "Beatriz Silva" in html
    # Tabela com as colunas essenciais
    assert "Sigla" in html
    assert "Unidade" in html
    assert "Subordinação" in html
    assert "Titular" in html
    # Organograma presente na página
    assert "organograma" in html


@banco
@pytest.mark.django_db
def test_redirecionamento_rota_arvore_para_listagem(client: Client) -> None:
    resposta = client.get(reverse("unidades:arvore_de_unidades"))

    assert resposta.status_code == 302
    assert resposta.url == reverse("unidades:listar_unidades")


@banco
@pytest.mark.django_db
def test_foco_forjado_abre_a_listagem_inteira(client: Client) -> None:
    """O `?foco=` é conveniência de navegação: link velho ou parâmetro forjado não pode derrubar a
    página numa tela de erro de validação."""
    _criar_cenario_unidades()

    resposta = client.get(reverse("unidades:listar_unidades"), {"foco": "nao-e-pk"})
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert "DIMAP" in html
    # `data-ego-inicial`, e não a classe: `no-arvore-ego` também aparece no CSS embutido na página.
    assert "data-ego-inicial" not in html
    assert 'data-unidade-sigla="DIMAP" data-ativo="true"' not in html


# ---------------------------------------------------------------------------
# Swap HTMX do Corpo da Tabela
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_corpo_unidades_htmx_devolve_apenas_tbody(client: Client) -> None:
    _criar_cenario_unidades()

    resposta = client.get(reverse("unidades:corpo_unidades"), {"sigla": "dimap"})
    html = resposta.content.decode().strip()

    assert resposta.status_code == 200
    assert html.startswith("<tbody")
    assert "<html" not in html
    assert "<thead" not in html
    assert 'data-unidade-sigla="DIMAP"' in html
    assert 'data-unidade-sigla="SF"' not in html


@banco
@pytest.mark.django_db
def test_filtro_sem_correspondencia_devolve_estado_vazio(client: Client) -> None:
    _criar_cenario_unidades()

    resposta = client.get(
        reverse("unidades:corpo_unidades"),
        {"sigla": "unidade_inexistente"},
    )
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert "table-onsen-vazio" in html
    assert "Nenhuma unidade corresponde aos filtros." in html
    assert "DIMAP" not in html


@banco
@pytest.mark.django_db
def test_links_de_unidade_titular_e_subordinacao_presentes(client: Client) -> None:
    secretaria, divisao, titular = _criar_cenario_unidades()

    resposta = client.get(reverse("unidades:corpo_unidades"))
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert reverse("unidades:pagina_unidade", args=[divisao.pk]) in html
    assert reverse("user_admin:pagina_perfil", args=[titular.pk]) in html
    assert reverse("unidades:pagina_unidade", args=[secretaria.pk]) in html


@banco
@pytest.mark.django_db
def test_listagem_unidades_com_parametro_foco_pre_ativa_arvore_e_tabela(client: Client) -> None:
    secretaria, divisao, _ = _criar_cenario_unidades()

    # 1. O botão "Organograma inteiro" na página de detalhes da unidade passa ?foco=<pk>
    resp_pagina = client.get(reverse("unidades:pagina_unidade", args=[divisao.pk]))
    assert f'{reverse("unidades:listar_unidades")}?foco={divisao.pk}' in resp_pagina.content.decode()

    # 2. Acessar com ?foco=<pk> renderiza a árvore com o ego na unidade e a tabela com data-ativo="true"
    resposta = client.get(reverse("unidades:listar_unidades"), {"foco": str(divisao.pk)})
    html = resposta.content.decode()

    assert resposta.status_code == 200
    # Árvore tem ego na unidade em foco — pelo atributo que só o nó em foco recebe, porque a
    # classe `no-arvore-ego` também aparece no CSS embutido na página.
    assert f'data-unidade-id="{divisao.pk}"' in html
    assert "data-ego-inicial" in html
    # Tabela traz a linha da unidade com data-ativo="true"
    assert f'data-unidade-sigla="{divisao.sigla}" data-ativo="true"' in html
