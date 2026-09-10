"""
Testes das páginas que carregam o design system (SPEC infraestrutura/004): a casca da aplicação
(`templates/base.html`) e o styleguide (`templates/core/design_system.html`) leem o mesmo CSS
compilado do projeto, não CDN.
"""

from pathlib import Path

from django.test import Client
from django.urls import reverse

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_HTML = REPO_ROOT / "templates" / "base.html"
STYLEGUIDE_HTML = REPO_ROOT / "templates" / "core" / "design_system.html"

FONTES_DE_CDN_PROIBIDAS = (
    "cdn.jsdelivr.net",
    "@tailwindcss/browser",
    'type="text/tailwindcss"',
)


# ---------------------------------------------------------------------------
# A casca não busca mais o compilador nem a folha do daisyUI na rede
# ---------------------------------------------------------------------------


def test_base_html_nao_referencia_cdn_de_tailwind_nem_daisyui() -> None:
    casca = BASE_HTML.read_text(encoding="utf-8")

    presentes = [fonte for fonte in FONTES_DE_CDN_PROIBIDAS if fonte in casca]

    assert not presentes, f"CDN de CSS ainda referenciado no base.html: {presentes}"


def test_home_serve_o_link_do_css_compilado() -> None:
    resposta = Client().get(reverse("core:home"))

    assert resposta.status_code == 200
    html = resposta.content.decode()
    assert "output.css" in html
    assert 'type="text/tailwindcss"' not in html


# ---------------------------------------------------------------------------
# Styleguide: página da aplicação, servida pelo mesmo CSS
# ---------------------------------------------------------------------------


def test_rota_design_system_responde_sem_login() -> None:
    resposta = Client().get(reverse("core:design_system"))

    assert resposta.status_code == 200


def test_styleguide_usa_o_css_compilado_da_aplicacao() -> None:
    casca = STYLEGUIDE_HTML.read_text(encoding="utf-8")

    presentes = [fonte for fonte in FONTES_DE_CDN_PROIBIDAS if fonte in casca]

    assert not presentes, f"CDN de CSS ainda referenciado no styleguide: {presentes}"
    assert "output.css" in casca
