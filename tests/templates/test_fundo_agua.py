"""
Testes do fundo administrativo com água (SPEC design/017): as duas camadas novas — o piso de
rocha e o canvas da água — e a torre de ajustes que ascende do controle de fundo.

Nenhuma condição de pronto da SPEC tem teste de verdade aqui (Caveats): o projeto não tem
infraestrutura de teste de JavaScript nem de render, e o que se fixa é só que as peças chegam ao
HTML de quem as inclui — e que a home, que roda sobre o Leaflet, segue sem elas.
"""

from django.test import Client
from django.urls import reverse

TELA_ADMINISTRATIVA = "autenticacao:login"


def _html(rota: str) -> str:
    resposta = Client().get(reverse(rota))

    assert resposta.status_code == 200
    return resposta.content.decode()


# ---------------------------------------------------------------------------
# As camadas novas da pilha do fundo
# ---------------------------------------------------------------------------


def test_tela_administrativa_traz_o_piso_de_rocha() -> None:
    html = _html(TELA_ADMINISTRATIVA)

    assert '<div class="fundo-rocha"><div class="fundo-rocha__grao"></div></div>' in html


def test_tela_administrativa_traz_o_canvas_da_agua() -> None:
    html = _html(TELA_ADMINISTRATIVA)

    assert '<canvas class="fundo-agua"' in html
    assert 'type="module" src="/static/js/ui/fundo_agua.js"' in html
    assert 'type="module" src="/static/js/ui/controle_agua.js"' in html


# ---------------------------------------------------------------------------
# A torre de ajustes
# ---------------------------------------------------------------------------


def test_controle_de_fundo_traz_a_engrenagem_e_a_torre() -> None:
    html = _html(TELA_ADMINISTRATIVA)

    assert "data-ajustes" in html
    assert 'aria-controls="torre-ajustes"' in html
    assert "torre-ajustes torre-ajustes--fechada" in html


def test_torre_de_ajustes_traz_o_interruptor_e_o_padrao() -> None:
    html = _html(TELA_ADMINISTRATIVA)

    assert "Ajustes da Animação" in html
    assert "data-agua-ligada" in html
    assert "data-padrao" in html
    assert "data-barras" in html


# ---------------------------------------------------------------------------
# A home não é tela administrativa
# ---------------------------------------------------------------------------


def test_home_nao_traz_o_fundo_administrativo() -> None:
    html = _html("core:home")

    assert "fundo-rocha" not in html
    assert "fundo-agua" not in html
