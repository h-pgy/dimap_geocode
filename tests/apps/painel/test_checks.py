"""Testes de apps/painel/checks.py (SPEC painel/001): o que o registro de ações já cobra das
ações, cobrado agora dos itens livres — ícone e rota resolvem —, e o painel cobrado de dar destino
a toda ação inscrita no registro.
"""

from unittest.mock import patch

import pytest

from apps.competencias.schemas import RegistroAcoes
from apps.competencias.utils import instanciar_acao
from apps.painel import checks
from apps.painel.checks import validar_painel
from apps.painel.estrutura import Aba, ContratoPainel, Grupo, ItemAcao, ItemLivre
from services.domain.autorizacao import VarianteIcone

URL_NAME_REAL = "core:home"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _item_livre(
    slug: str = "painel.item_teste",
    url_name: str = URL_NAME_REAL,
    variante_icone: VarianteIcone = VarianteIcone.GRANDE,
) -> ItemLivre:
    return ItemLivre(
        slug=slug,
        nome="Item de Teste",
        tooltip="tt",
        url_name=url_name,
        variante_icone=variante_icone,
    )


def _aba_basica() -> Aba:
    # Sem item algum: só existe para satisfazer a exigência de uma aba básica sem entrar em
    # cena nos testes que não são sobre ela.
    return Aba(slug="painel.basica", rotulo="Básica", titulo="Básica", descricao="d", basica=True)


# ---------------------------------------------------------------------------
# Painel sem aba básica
# ---------------------------------------------------------------------------


def test_check_recusa_painel_sem_aba_basica() -> None:
    aba = Aba(slug="painel.aba", rotulo="Aba", titulo="Aba", descricao="d", basica=False)
    painel = ContratoPainel(abas=(aba,))

    erros = validar_painel(painel, RegistroAcoes(acoes=()))

    assert any(e.id == "painel.E001" for e in erros)


def test_check_com_aba_basica_nao_acusa_e001() -> None:
    painel = ContratoPainel(abas=(_aba_basica(),))

    erros = validar_painel(painel, RegistroAcoes(acoes=()))

    assert not any(e.id == "painel.E001" for e in erros)


# ---------------------------------------------------------------------------
# Item livre com rota que não resolve
# ---------------------------------------------------------------------------


def test_check_recusa_item_livre_com_rota_que_nao_resolve() -> None:
    grupo = Grupo(rotulo="Grupo", itens=(_item_livre(url_name="painel:rota_fantasma"),))
    aba = Aba(
        slug="painel.aba",
        rotulo="Aba",
        titulo="Aba",
        descricao="d",
        basica=True,
        grupos=(grupo,),
    )
    painel = ContratoPainel(abas=(aba,))

    with patch("django.contrib.staticfiles.finders.find", return_value="/fake/path.svg"):
        erros = validar_painel(painel, RegistroAcoes(acoes=()))

    assert any(e.id == "painel.E003" for e in erros)


def test_check_item_livre_com_rota_valida_nao_acusa_e003() -> None:
    grupo = Grupo(rotulo="Grupo", itens=(_item_livre(url_name=URL_NAME_REAL),))
    aba = Aba(
        slug="painel.aba",
        rotulo="Aba",
        titulo="Aba",
        descricao="d",
        basica=True,
        grupos=(grupo,),
    )
    painel = ContratoPainel(abas=(aba,))

    with patch("django.contrib.staticfiles.finders.find", return_value="/fake/path.svg"):
        erros = validar_painel(painel, RegistroAcoes(acoes=()))

    assert not any(e.id == "painel.E003" for e in erros)


# ---------------------------------------------------------------------------
# Ação inscrita no registro sem card em aba alguma
# ---------------------------------------------------------------------------


def test_check_recusa_acao_inscrita_sem_card_no_painel() -> None:
    painel = ContratoPainel(abas=(_aba_basica(),))
    registro = RegistroAcoes(
        acoes=(
            instanciar_acao(
                slug="painel.acao_orfa",
                nome="Ação Órfã",
                tooltip="tt",
                url_name=URL_NAME_REAL,
            ),
        )
    )

    with patch("django.contrib.staticfiles.finders.find", return_value="/fake/path.svg"):
        erros = validar_painel(painel, registro)

    assert any(e.id == "painel.E004" and "painel.acao_orfa" in e.msg for e in erros)


def test_check_acao_com_card_no_painel_nao_acusa_e004() -> None:
    acao_implementada = instanciar_acao(
        slug="painel.acao_com_card",
        nome="Ação Com Card",
        tooltip="tt",
        url_name=URL_NAME_REAL,
        variantes_icone=frozenset({VarianteIcone.GRANDE}),
    )
    grupo = Grupo(rotulo="Grupo", itens=(ItemAcao(acao=acao_implementada),))
    aba = Aba(
        slug="painel.aba",
        rotulo="Aba",
        titulo="Aba",
        descricao="d",
        basica=True,
        grupos=(grupo,),
    )
    painel = ContratoPainel(abas=(aba,))
    registro = RegistroAcoes(acoes=(acao_implementada,))

    with patch("django.contrib.staticfiles.finders.find", return_value="/fake/path.svg"):
        erros = validar_painel(painel, registro)

    assert not any(e.id == "painel.E004" for e in erros)


def test_check_acao_orfa_em_acoes_sem_card_nao_acusa_e004(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    painel = ContratoPainel(abas=(_aba_basica(),))
    registro = RegistroAcoes(
        acoes=(
            instanciar_acao(
                slug="painel.acao_dispensada",
                nome="Ação Dispensada",
                tooltip="tt",
                url_name=URL_NAME_REAL,
            ),
        )
    )
    monkeypatch.setattr(checks, "ACOES_SEM_CARD", frozenset({"painel.acao_dispensada"}))

    with patch("django.contrib.staticfiles.finders.find", return_value="/fake/path.svg"):
        erros = validar_painel(painel, registro)

    assert not any(e.id == "painel.E004" for e in erros)
