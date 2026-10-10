from io import BytesIO
from pathlib import Path

import pytest
from pydantic import ValidationError
from svglib.svglib import svg2rlg

from services.utils.qr_code import QrCodeInput, gerar_qr_code

# ---------------------------------------------------------------------------
# O símbolo sai como SVG vetorial, em memória
# ---------------------------------------------------------------------------


def test_simbolo_sai_como_svg_vetorial_em_memoria(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    simbolo = gerar_qr_code(QrCodeInput(conteudo="https://exemplo.sp.gov.br/verificar"))

    assert isinstance(simbolo.svg, bytes)
    desenho = svg2rlg(BytesIO(simbolo.svg))
    assert desenho is not None
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# Sempre QR padrão, nunca Micro QR, com o silêncio contado na matriz
# ---------------------------------------------------------------------------


def test_simbolo_eh_sempre_qr_padrao_com_silencio() -> None:
    simbolo = gerar_qr_code(QrCodeInput(conteudo="1", silencio_modulos=4))

    # Micro QR não passa da versão M4 (17 módulos); QR padrão começa na versão 1, com 21. Um
    # único caractere força o menor símbolo de cada família — a diferença é o que prova que
    # `make_qr` nunca degrada para Micro QR.
    assert simbolo.modulos == 21 + 2 * 4


# ---------------------------------------------------------------------------
# Conteúdo vazio e conteúdo maior do que cabe são recusados, não truncados
# ---------------------------------------------------------------------------


def test_conteudo_vazio_e_longo_demais_sao_recusados() -> None:
    with pytest.raises(ValidationError):
        QrCodeInput(conteudo="")

    conteudo_longo_demais = "x" * 5000
    with pytest.raises(ValueError, match="5000"):
        gerar_qr_code(QrCodeInput(conteudo=conteudo_longo_demais))
