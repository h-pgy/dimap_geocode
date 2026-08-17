"""Testes de apps/competencias/menus.py (SPEC autorizacao/005): o contrato de menu — declaração em
código de quais ações ele contém — e o router que filtra pelos slugs liberados, na ordem
declarada, sem decidir competência.
"""

from django.urls import reverse

from pydantic import ValidationError

import pytest

from services.domain.autorizacao.contratos import VarianteIcone
from apps.competencias.menus import (
    ContratoMenu,
    FormaItem,
    ItemDeMenu,
    MontagemMenu,
    RoteadorMenu,
)
from apps.competencias.schemas import AcaoImplementada
from apps.competencias.utils import instanciar_acao


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _acao_implementada(
    slug: str = "menus.acao_teste",
    nome: str = "Ação de Teste",
    nome_curto: str | None = None,
    tooltip: str = "tt",
    url_name: str = "core:home",
    partial: str = "_teste.html",
    variantes_icone: frozenset[VarianteIcone] = frozenset({VarianteIcone.PEQUENO}),
) -> AcaoImplementada:
    return instanciar_acao(
        slug=slug,
        nome=nome,
        nome_curto=nome_curto,
        tooltip=tooltip,
        url_name=url_name,
        partial=partial,
        variantes_icone=variantes_icone,
    )


def _item_de_menu(
    acao_implementada: AcaoImplementada,
    variante_icone: VarianteIcone = VarianteIcone.PEQUENO,
    forma: FormaItem = FormaItem.LINHA,
) -> ItemDeMenu:
    return ItemDeMenu(
        acao_implementada=acao_implementada, variante_icone=variante_icone, forma=forma
    )


def _contrato_menu(
    *itens: ItemDeMenu, slug: str = "menus.contrato_teste", nome: str = "Menu de Teste"
) -> ContratoMenu:
    return ContratoMenu(slug=slug, nome=nome, itens=itens)


# ---------------------------------------------------------------------------
# O router filtra pelos liberados, preservando a ordem declarada
# ---------------------------------------------------------------------------


def test_router_devolve_apenas_liberados_na_ordem_declarada() -> None:
    item_a = _item_de_menu(_acao_implementada(slug="menus.item_a"))
    item_b = _item_de_menu(_acao_implementada(slug="menus.item_b"))
    item_c = _item_de_menu(_acao_implementada(slug="menus.item_c"))
    menu = _contrato_menu(item_a, item_b, item_c)
    montagem = MontagemMenu(
        menu=menu, slugs_liberados=frozenset({"menus.item_c", "menus.item_a"})
    )

    resolvido = RoteadorMenu()(montagem)

    assert [item.slug for item in resolvido.itens] == ["menus.item_a", "menus.item_c"]


def test_router_devolve_vazio_sem_nenhum_liberado() -> None:
    menu = _contrato_menu(_item_de_menu(_acao_implementada()))
    montagem = MontagemMenu(menu=menu, slugs_liberados=frozenset())

    resolvido = RoteadorMenu()(montagem)

    assert resolvido.itens == ()


# ---------------------------------------------------------------------------
# A variante de ícone é do menu, não da ação
# ---------------------------------------------------------------------------


def test_item_carrega_a_variante_de_icone_do_menu() -> None:
    acao = _acao_implementada(
        slug="menus.duas_variantes",
        variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    )
    menu = _contrato_menu(
        _item_de_menu(acao, variante_icone=VarianteIcone.PEQUENO),
        _item_de_menu(acao, variante_icone=VarianteIcone.GRANDE),
    )
    montagem = MontagemMenu(
        menu=menu, slugs_liberados=frozenset({"menus.duas_variantes"})
    )

    resolvido = RoteadorMenu()(montagem)

    assert [item.variante_icone for item in resolvido.itens] == [
        VarianteIcone.PEQUENO,
        VarianteIcone.GRANDE,
    ]


def test_item_recusa_variante_que_a_acao_nao_declara() -> None:
    acao = _acao_implementada(
        slug="menus.so_pequeno", variantes_icone=frozenset({VarianteIcone.PEQUENO})
    )

    with pytest.raises(ValidationError):
        _item_de_menu(acao, variante_icone=VarianteIcone.GRANDE)


# ---------------------------------------------------------------------------
# O item renderizável reflete a ação por trás do envelope
# ---------------------------------------------------------------------------


def test_item_usa_nome_curto_quando_declarado_e_cai_no_nome_quando_falta() -> None:
    com_curto = _acao_implementada(
        slug="menus.com_curto", nome="Nome Longo", nome_curto="Curto"
    )
    sem_curto = _acao_implementada(slug="menus.sem_curto", nome="Nome Sem Curto")
    menu = _contrato_menu(_item_de_menu(com_curto), _item_de_menu(sem_curto))
    montagem = MontagemMenu(
        menu=menu, slugs_liberados=frozenset({"menus.com_curto", "menus.sem_curto"})
    )

    resolvido = RoteadorMenu()(montagem)

    assert [item.nome_curto for item in resolvido.itens] == ["Curto", "Nome Sem Curto"]


def test_item_renderizavel_carrega_dados_da_acao_e_do_item() -> None:
    acao = _acao_implementada(
        slug="menus.dados_completos",
        nome="Ação Completa",
        tooltip="Tooltip completo",
        url_name="core:home",
        partial="_completo.html",
    )
    menu = _contrato_menu(_item_de_menu(acao, forma=FormaItem.CARTAO))
    montagem = MontagemMenu(
        menu=menu, slugs_liberados=frozenset({"menus.dados_completos"})
    )

    (renderizado,) = RoteadorMenu()(montagem).itens

    assert renderizado.partial == "_completo.html"
    assert renderizado.url == reverse("core:home")
    assert renderizado.nome == "Ação Completa"
    assert renderizado.tooltip == "Tooltip completo"
    assert renderizado.forma == FormaItem.CARTAO
