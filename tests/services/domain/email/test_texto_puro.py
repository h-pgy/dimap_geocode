from typing import Any

from pydantic import HttpUrl

from services.domain.email import (
    Bloco,
    Botao,
    ConteudoEmail,
    Destaque,
    Divisor,
    Imagem,
    Paragrafo,
    Subtitulo,
    Tabela,
    Titulo,
    renderizar_texto_puro,
)

RODAPE = "Mensagem automática do DIMAP GeoCoder. Não é necessário responder."


def _todos_os_blocos() -> tuple[Bloco, ...]:
    return (
        Titulo(texto="O envio de e-mail está funcionando"),
        Subtitulo(texto="Dados do disparo"),
        Paragrafo(texto="Mensagem disparada para provar a configuração de envio."),
        Destaque(rotulo="Ambiente", valor="producao"),
        Tabela(
            cabecalho=("Campo", "Valor"),
            linhas=(("Ambiente", "producao"), ("Momento", "21/08/2026 14:30:05")),
        ),
        Divisor(),
        Imagem(
            url=HttpUrl("https://geocoder.dimap.local/selo.png"),
            alternativo="Selo da DIMAP",
        ),
        Botao(rotulo="Entrar", url=HttpUrl("https://geocoder.dimap.local/entrar")),
    )


def _conteudo(**overrides: Any) -> ConteudoEmail:
    defaults: dict[str, Any] = {
        "assunto": "DIMAP GeoCoder — e-mail de teste",
        "blocos": _todos_os_blocos(),
        "rodape": RODAPE,
    }
    return ConteudoEmail(**(defaults | overrides))


# ---------------------------------------------------------------------------
# A mesma sequência de blocos, em texto
# ---------------------------------------------------------------------------


def test_texto_puro_preserva_blocos_e_url() -> None:
    texto = renderizar_texto_puro(_conteudo())

    assert "O envio de e-mail está funcionando" in texto
    assert "Dados do disparo" in texto
    assert "Ambiente: producao" in texto
    assert "Campo | Valor\nAmbiente | producao\nMomento | 21/08/2026 14:30:05" in texto
    assert "[imagem: Selo da DIMAP]" in texto
    assert "Entrar: https://geocoder.dimap.local/entrar" in texto
    assert texto.endswith(RODAPE)
    # O divisor não diz nada em texto: some, sem deixar parágrafo em branco a mais.
    assert "\n\n\n" not in texto
