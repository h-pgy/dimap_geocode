import pytest
from bs4 import BeautifulSoup, Tag
from django.template.loader import render_to_string


def _placa(contexto: dict[str, object]) -> Tag:
    html = render_to_string("mapping/_resultado_acao.html", contexto)
    placa = BeautifulSoup(html, "html.parser").select_one("aside.gaveta-inferior")
    assert placa is not None
    return placa


# ---------------------------------------------------------------------------
# Gaveta inferior puxável (SPEC design/022)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("contexto", "puxavel"),
    [
        ({}, False),
        ({"puxavel": False}, False),
        ({"puxavel": True}, True),
    ],
)
def test_resultado_de_acao_so_e_puxavel_quando_o_contexto_pede(
    contexto: dict[str, object],
    puxavel: bool,
) -> None:
    classes = _placa(contexto)["class"]

    assert "gaveta-inferior-rasa" in classes
    assert ("gaveta-inferior-puxavel" in classes) is puxavel
