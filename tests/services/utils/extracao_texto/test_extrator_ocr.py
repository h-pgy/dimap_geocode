from io import BytesIO

import pytest
from PIL import Image, ImageDraw, ImageFont

from services.utils.extracao_texto import (
    ExtracaoConfig,
    ExtracaoImpossivel,
    OrigemTexto,
)
from services.utils.extracao_texto.extrator_ocr import MENSAGEM_PRAZO_OCR, ExtratorOcr

LINHAS = (
    "Certidão de lançamento do imposto",
    "predial e territorial urbano",
    "emitida pela divisão de avaliação",
)


def _config(**overrides: object) -> ExtracaoConfig:
    padrao: dict[str, object] = {
        "tamanho_maximo_bytes": 20_000_000,
        "paginas_maximas_ocr": 40,
        "prazo_ocr_s": 120.0,
        "idioma_ocr": "por",
        "dpi_ocr": 200,
    }
    return ExtracaoConfig.model_validate(padrao | overrides)


def _pagina_escaneada() -> Image.Image:
    pagina = Image.new("L", (1700, 2200), color=255)
    desenho = ImageDraw.Draw(pagina)
    fonte = ImageFont.load_default(size=56)
    for indice, linha in enumerate(LINHAS):
        desenho.text((120, 200 + indice * 110), linha, fill=0, font=fonte)
    return pagina


def _pdf_escaneado(paginas: int = 1) -> bytes:
    imagens = [_pagina_escaneada() for _ in range(paginas)]
    saida = BytesIO()
    imagens[0].save(
        saida, "PDF", resolution=200, save_all=True, append_images=imagens[1:]
    )
    return saida.getvalue()


# ---------------------------------------------------------------------------
# Integração com tesseract e poppler
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_pdf_escaneado_passa_pelo_ocr() -> None:
    texto = ExtratorOcr(config=_config())(_pdf_escaneado())

    assert texto.origem is OrigemTexto.OCR
    minusculo = texto.conteudo.lower()
    assert "imposto" in minusculo
    assert "territorial" in minusculo


@pytest.mark.integration
def test_ocr_que_passa_do_prazo_eh_recusado() -> None:
    extrator = ExtratorOcr(config=_config(prazo_ocr_s=0.01))

    with pytest.raises(ExtracaoImpossivel) as recusa:
        extrator(_pdf_escaneado(paginas=2))

    assert str(recusa.value) == MENSAGEM_PRAZO_OCR
