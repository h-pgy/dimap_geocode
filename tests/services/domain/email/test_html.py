from collections.abc import Callable
from typing import Any

import pytest
from pydantic import HttpUrl

from services.domain.email import (
    ESCRITORES,
    TEMA_EMAIL,
    Bloco,
    Botao,
    ConteudoEmail,
    Destaque,
    Divisor,
    Imagem,
    Paragrafo,
    RenderizadorEmailHtml,
    Subtitulo,
    Tabela,
    Titulo,
    renderizar_html,
)
from services.utils.html import validar_html


def _todos_os_blocos() -> tuple[Bloco, ...]:
    return (
        Titulo(texto="O envio de e-mail está funcionando"),
        Subtitulo(texto="Dados do disparo"),
        Paragrafo(texto="Mensagem disparada para provar a configuração de envio."),
        Destaque(rotulo="Ambiente", valor="producao", monoespacado=True),
        Tabela(
            cabecalho=("Campo", "Valor"),
            linhas=(("Ambiente", "producao"), ("Momento", "21/08/2026 14:30:05")),
        ),
        Imagem(
            url=HttpUrl("https://geocoder.dimap.local/selo.png"),
            alternativo="Selo da DIMAP",
            largura=120,
        ),
        Botao(rotulo="Entrar", url=HttpUrl("https://geocoder.dimap.local/entrar")),
        Divisor(),
    )


def _conteudo(**overrides: Any) -> ConteudoEmail:
    defaults: dict[str, Any] = {
        "assunto": "DIMAP GeoCoder — e-mail de teste",
        "blocos": _todos_os_blocos(),
        "rodape": "Mensagem automática do DIMAP GeoCoder. Não é necessário responder.",
    }
    return ConteudoEmail(**(defaults | overrides))


# ---------------------------------------------------------------------------
# Bloco sem escritor não some do e-mail
# ---------------------------------------------------------------------------


def test_bloco_sem_escritor_falha_na_montagem() -> None:
    incompleto: dict[str, Callable[[Any], str]] = {
        tipo: escritor for tipo, escritor in ESCRITORES.items() if tipo != "destaque"
    }

    with pytest.raises(KeyError):
        RenderizadorEmailHtml(incompleto)(_conteudo())


# ---------------------------------------------------------------------------
# O envelope inteiro: boa-formação e estilo colado no elemento
# ---------------------------------------------------------------------------


def test_html_montado_e_bem_formado_e_nao_tem_folha_nem_classe() -> None:
    html = renderizar_html(_conteudo())

    assert validar_html(html).valido
    assert "<style" not in html.lower()
    assert "class=" not in html
    for peca in ("fundo", "placa", "faixa", "corpo", "rodape"):
        assert TEMA_EMAIL[peca] in html, peca
