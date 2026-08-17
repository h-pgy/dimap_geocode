"""Teste de templates/competencias/partials/_menu_acoes.html (SPEC autorizacao/006): o organismo
que desenha a saída do router — aqui, só o caso em que ela vem vazia.
"""

from django.template.loader import render_to_string

from apps.competencias.menus import MenuResolvido


def test_menu_vazio_renderiza_estado_vazio() -> None:
    html = render_to_string(
        "competencias/partials/_menu_acoes.html", {"menu": MenuResolvido(itens=())}
    )

    assert "menu-acoes-vazio" in html
    # Painel quebrado seria a lista de itens tentando desenhar algo do nada: aqui não há nem loop.
    assert "item-menu" not in html
    assert "card-acao" not in html
