from typing import Any

from services.domain.email import (
    ConteudoEmail,
    Destaque,
    Paragrafo,
    Titulo,
    montar_mensagem,
)


def _conteudo(**overrides: Any) -> ConteudoEmail:
    defaults: dict[str, Any] = {
        "assunto": "DIMAP GeoCoder — e-mail de teste",
        "blocos": (
            Titulo(texto="O envio de e-mail está funcionando"),
            Paragrafo(texto="Mensagem disparada para provar a configuração de envio."),
            Destaque(rotulo="Ambiente", valor="producao", monoespacado=True),
        ),
        "rodape": "Mensagem automática do DIMAP GeoCoder. Não é necessário responder.",
    }
    return ConteudoEmail(**(defaults | overrides))


# ---------------------------------------------------------------------------
# As duas versões saem do mesmo conteúdo
# ---------------------------------------------------------------------------


def test_montagem_devolve_mensagem_com_as_duas_versoes() -> None:
    conteudo = _conteudo()

    mensagem = montar_mensagem(conteudo, destinatarios=("ana@example.com",))

    assert mensagem.destinatarios == ("ana@example.com",)
    assert mensagem.assunto == conteudo.assunto
    assert mensagem.corpo_html is not None
    assert "<h1" in mensagem.corpo_html
    assert "O envio de e-mail está funcionando" in mensagem.corpo_html
    assert "<" not in mensagem.corpo_texto
    assert "O envio de e-mail está funcionando" in mensagem.corpo_texto
    assert "Ambiente: producao" in mensagem.corpo_texto
