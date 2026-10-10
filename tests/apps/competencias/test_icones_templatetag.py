from django.template import Context, Template
from django.utils.safestring import SafeString
import pytest


def test_icone_acao_retorna_svg_sem_escape_html() -> None:
    template = Template(
        '{% load icones %}{% icone_acao "certidao_lancamento.emitir" "pequeno" %}'
    )
    resultado = template.render(Context({}))

    assert resultado.startswith("<svg")
    assert "&lt;svg" not in resultado
    assert "viewBox" in resultado


def test_icone_acao_as_var_retorna_safestring() -> None:
    template = Template(
        '{% load icones %}{% icone_acao "certidao_lancamento.emitir" "pequeno" as icone %}{{ icone }}'
    )
    resultado = template.render(Context({}))

    assert resultado.startswith("<svg")
    assert "&lt;svg" not in resultado
