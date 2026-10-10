from typing import Literal

from django.template.loader import render_to_string

from apps.unidades.paleta import HEX_POR_COR, TINTA_AVATAR
from services.domain.avatar import ImagemPerfilOutput


def _imagem(
    tipo: Literal["foto", "avatar"] = "avatar",
    valor: str = "<svg>...</svg>",
) -> ImagemPerfilOutput:
    return ImagemPerfilOutput(tipo=tipo, valor=valor)


def _luminancia_relativa(hex_cor: str) -> float:
    hex_cor = hex_cor.lstrip("#")
    rgb = [int(hex_cor[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [
        canal / 12.92 if canal <= 0.04045 else ((canal + 0.055) / 1.055) ** 2.4
        for canal in rgb
    ]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _razao_contraste(cor1: str, cor2: str) -> float:
    l1 = _luminancia_relativa(cor1)
    l2 = _luminancia_relativa(cor2)
    mais_clara = max(l1, l2)
    mais_escura = min(l1, l2)
    return (mais_clara + 0.05) / (mais_escura + 0.05)


# ---------------------------------------------------------------------------
# Template _imagem_perfil.html: injeção de variáveis inline
# ---------------------------------------------------------------------------


def test_imagem_perfil_renderiza_cor_unidade_como_hex() -> None:
    html = render_to_string(
        "user_admin/partials/_imagem_perfil.html",
        {
            "imagem": _imagem(),
            "cor_unidade_hex": "#0077B6",
            "tamanho": "w-10 h-10",
        },
    )
    assert "--cor-unidade: #0077B6" in html


def test_avatar_glass_suporta_parametro_halo_escala() -> None:
    html_com_escala = render_to_string(
        "user_admin/partials/_imagem_perfil.html",
        {
            "imagem": _imagem(),
            "cor_unidade_hex": "#0077B6",
            "tamanho": "w-10 h-10",
            "halo_escala": "0.5",
        },
    )
    assert "--halo-escala: 0.5" in html_com_escala

    html_sem_escala = render_to_string(
        "user_admin/partials/_imagem_perfil.html",
        {
            "imagem": _imagem(),
            "cor_unidade_hex": "#0077B6",
            "tamanho": "w-10 h-10",
        },
    )
    assert "--halo-escala" not in html_sem_escala


# ---------------------------------------------------------------------------
# Contraste de acessibilidade (WCAG AA)
# ---------------------------------------------------------------------------


def test_avatar_iniciais_preserva_contraste_tinta_clara() -> None:
    for tom, hex_cor in HEX_POR_COR.items():
        contraste = _razao_contraste(TINTA_AVATAR, hex_cor)
        assert contraste >= 4.5, f"Contraste insuficiente para {tom}: {contraste:.2f} < 4.5"
