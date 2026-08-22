from typing import Any

from services.domain.email import (
    ASSUNTO_ACESSO,
    Botao,
    Destaque,
    EmailAcessoInput,
    Otp,
    montar_email_acesso,
    renderizar_html,
)
from services.utils.html import validar_html


def _pedido(**overrides: Any) -> EmailAcessoInput:
    defaults: dict[str, Any] = {
        "nome": "Ana Beatriz",
        "rf": "123.456-7",
        "destinatario": "ana@example.com",
        "senha_temporaria": "k7Qm-2af9",
        "url_acesso": "https://geocoder.dimap.local/entrar",
    }
    return EmailAcessoInput(**(defaults | overrides))


# ---------------------------------------------------------------------------
# O conteúdo do e-mail de acesso entrega RF, senha e caminho, na ordem
# ---------------------------------------------------------------------------


def test_email_de_acesso_diz_rf_senha_e_caminho() -> None:
    conteudo = montar_email_acesso(_pedido())

    assert conteudo.assunto == ASSUNTO_ACESSO
    tipos = [type(bloco) for bloco in conteudo.blocos]
    assert tipos.index(Destaque) < tipos.index(Otp) < tipos.index(Botao)

    destaque = next(bloco for bloco in conteudo.blocos if isinstance(bloco, Destaque))
    assert destaque.rotulo == "RF"
    assert destaque.valor == "123.456-7"

    otp = next(bloco for bloco in conteudo.blocos if isinstance(bloco, Otp))
    assert otp.valor == "k7Qm-2af9"

    botao = next(bloco for bloco in conteudo.blocos if isinstance(bloco, Botao))
    assert str(botao.url) == "https://geocoder.dimap.local/entrar"


# ---------------------------------------------------------------------------
# O envelope inteiro, com o bloco de OTP, é bem formado
# ---------------------------------------------------------------------------


def test_email_de_acesso_e_bem_formado() -> None:
    html = renderizar_html(montar_email_acesso(_pedido()))

    assert validar_html(html).valido
