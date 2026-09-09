from xml.etree import ElementTree

from services.domain.avatar import (
    AvatarIniciaisInput,
    AvatarIniciaisOutput,
    AvatarIniciaisSvg,
)

_SVG_NS = {"svg": "http://www.w3.org/2000/svg"}


def _gerar(
    nome: str,
    sobrenome: str,
    cor_fundo: str = "#123456",
    cor_tinta: str = "#ffffff",
) -> AvatarIniciaisOutput:
    entrada = AvatarIniciaisInput(
        nome=nome,
        sobrenome=sobrenome,
        cor_fundo=cor_fundo,
        cor_tinta=cor_tinta,
    )
    return AvatarIniciaisSvg()(entrada)


# ---------------------------------------------------------------------------
# Extração das iniciais
# ---------------------------------------------------------------------------


def test_iniciais_vem_do_primeiro_nome_e_do_ultimo_sobrenome() -> None:
    resultado = _gerar("João", "Pedro da Silva")
    assert resultado.iniciais == "JS"


def test_iniciais_sao_maiusculas_e_sem_acento() -> None:
    resultado = _gerar("ávila", "éboli")
    assert resultado.iniciais == "AE"


def test_particula_elidida_nao_vira_inicial() -> None:
    assert _gerar("João", "d'Angelo").iniciais == "JA"
    assert _gerar("D'Artagnan", "Silva").iniciais == "AS"


def test_iniciais_descartam_termos_nao_alfabeticos() -> None:
    # nome sem termo aproveitável: nenhum dígito vaza para as iniciais, sobra só o sobrenome.
    # A checagem é só no texto/aria-label (as cores recebidas podem ter dígitos legitimamente).
    resultado = _gerar("3", "Silva")
    assert resultado.iniciais == "S"
    raiz = ElementTree.fromstring(resultado.svg)
    assert raiz.get("aria-label") == "S"
    assert raiz.find("svg:text", _SVG_NS).text == "S"  # type: ignore[union-attr]

    # sobrenome sem termo alfabético: avatar sai com uma inicial só, não duas.
    resultado = _gerar("Maria", "123")
    assert resultado.iniciais == "M"
    assert len(resultado.iniciais) == 1


# ---------------------------------------------------------------------------
# Markup do SVG
# ---------------------------------------------------------------------------


def test_avatar_e_um_circulo_pintado_com_as_cores_recebidas() -> None:
    resultado = _gerar("João", "Silva", cor_fundo="#ea580c", cor_tinta="#f8fafc")

    raiz = ElementTree.fromstring(resultado.svg)
    largura, altura = (float(v) for v in raiz.get("viewBox", "").split()[2:])
    assert largura == altura

    circulo = raiz.find("svg:circle", _SVG_NS)
    assert circulo is not None
    assert float(circulo.get("r", "0")) == 48
    assert circulo.get("fill") == "#ea580c"

    texto = raiz.find("svg:text", _SVG_NS)
    assert texto is not None
    assert texto.get("fill") == "#f8fafc"
    assert texto.text == resultado.iniciais


def test_avatar_svg_preserva_iniciais_e_aria_label() -> None:
    resultado = _gerar("João", "Silva")

    raiz = ElementTree.fromstring(resultado.svg)
    assert raiz.get("role") == "img"
    assert raiz.get("aria-label") == resultado.iniciais
    texto = raiz.find("svg:text", _SVG_NS)
    assert texto is not None
    assert texto.text == resultado.iniciais


def test_avatar_svg_circulo_nao_ultrapassa_area_visivel() -> None:
    resultado = _gerar("João", "Silva")

    raiz = ElementTree.fromstring(resultado.svg)
    largura, altura = (float(v) for v in raiz.get("viewBox", "").split()[2:])
    circulo = raiz.find("svg:circle", _SVG_NS)
    assert circulo is not None
    r = float(circulo.get("r", "0"))
    cx = float(circulo.get("cx", "0"))
    cy = float(circulo.get("cy", "0"))

    # Margem anti-serrilhado: círculo interno não alcança a borda do viewBox
    assert r < largura / 2
    assert cx - r > 0
    assert cx + r < largura
    assert cy - r > 0
    assert cy + r < altura

