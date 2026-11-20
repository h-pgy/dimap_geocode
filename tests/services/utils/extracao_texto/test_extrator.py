from io import BytesIO
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

import pytest
from PIL import Image, ImageDraw, ImageFont

from services.utils.extracao_texto import (
    ExtracaoConfig,
    ExtracaoImpossivel,
    ExtratorTexto,
    OrigemTexto,
    TipoDocumento,
)
from services.utils.extracao_texto import extrator_ocr
from services.utils.extracao_texto.aproveitamento import MENSAGEM_RECUSA
from services.utils.extracao_texto.deteccao import MENSAGEM_DOC, MENSAGEM_FORMATO
from services.utils.extracao_texto.extrator import MENSAGEM_TAMANHO
from services.utils.extracao_texto.extrator_ocr import MENSAGEM_PAGINAS

PARAGRAFO_ODT = "Orientação para a emissão da certidão de lançamento do IPTU."
CELULA_ODT = "Valor venal de referência do imóvel"
CONTEUDO_ODT = f"""<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
  xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0">
  <office:body><office:text>
    <text:h>Certidões</text:h>
    <text:p>{PARAGRAFO_ODT}</text:p>
    <table:table><table:table-row>
      <table:table-cell><text:p>{CELULA_ODT}</text:p></table:table-cell>
    </table:table-row></table:table>
  </office:text></office:body>
</office:document-content>"""


def _config(**overrides: object) -> ExtracaoConfig:
    padrao: dict[str, object] = {
        "tamanho_maximo_bytes": 20_000_000,
        "paginas_maximas_ocr": 40,
        "prazo_ocr_s": 120.0,
        "idioma_ocr": "por",
        "dpi_ocr": 200,
    }
    return ExtracaoConfig.model_validate(padrao | overrides)


def _pacote_open_document(mimetype: str, conteudo: str) -> bytes:
    saida = BytesIO()
    with ZipFile(saida, "w") as pacote:
        # O `mimetype` vai primeiro e sem compressão, como o LibreOffice o grava.
        pacote.writestr("mimetype", mimetype, compress_type=ZIP_STORED)
        pacote.writestr("content.xml", conteudo, compress_type=ZIP_DEFLATED)
    return saida.getvalue()


def _odt() -> bytes:
    return _pacote_open_document(
        "application/vnd.oasis.opendocument.text", CONTEUDO_ODT
    )


def _ods() -> bytes:
    return _pacote_open_document(
        "application/vnd.oasis.opendocument.spreadsheet", CONTEUDO_ODT
    )


def _zip_qualquer() -> bytes:
    saida = BytesIO()
    with ZipFile(saida, "w") as pacote:
        pacote.writestr("leia-me.txt", "nada de documento aqui")
    return saida.getvalue()


def _doc() -> bytes:
    return b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + bytes(512)


def _pagina_em_branco() -> Image.Image:
    return Image.new("L", (1700, 2200), color=255)


def _pagina_escaneada() -> Image.Image:
    pagina = _pagina_em_branco()
    desenho = ImageDraw.Draw(pagina)
    fonte = ImageFont.load_default(size=56)
    desenho.text(
        (120, 200), "Certidão de lançamento do imposto predial", fill=0, font=fonte
    )
    return pagina


def _pdf_de_imagens(imagens: list[Image.Image]) -> bytes:
    saida = BytesIO()
    imagens[0].save(
        saida, "PDF", resolution=200, save_all=True, append_images=imagens[1:]
    )
    return saida.getvalue()


def _sem_rasterizar(monkeypatch: pytest.MonkeyPatch) -> None:
    def _proibido(*args: object, **kwargs: object) -> None:
        raise AssertionError("rasterizou uma página")

    monkeypatch.setattr(extrator_ocr, "convert_from_path", _proibido)


# ---------------------------------------------------------------------------
# Formatos
# ---------------------------------------------------------------------------


def test_odt_rende_texto_de_paragrafos_e_tabelas() -> None:
    tipo, texto = ExtratorTexto(_config())(_odt())

    assert tipo is TipoDocumento.ODT
    assert texto.origem is OrigemTexto.CAMADA_DE_TEXTO
    assert PARAGRAFO_ODT in texto.conteudo
    assert CELULA_ODT in texto.conteudo


def test_doc_eh_recusado_com_pedido_de_docx() -> None:
    with pytest.raises(ExtracaoImpossivel) as recusa:
        ExtratorTexto(_config())(_doc())

    assert str(recusa.value) == MENSAGEM_DOC


@pytest.mark.parametrize(
    "conteudo", [_zip_qualquer(), _ods(), b"so um texto chamado .pdf"]
)
def test_extensao_mentirosa_eh_recusada(conteudo: bytes) -> None:
    with pytest.raises(ExtracaoImpossivel) as recusa:
        ExtratorTexto(_config())(conteudo)

    assert str(recusa.value) == MENSAGEM_FORMATO


def test_falha_da_biblioteca_vira_recusa() -> None:
    corrompido = b"%PDF-1.7\n" + bytes(range(256)) * 4

    with pytest.raises(ExtracaoImpossivel) as recusa:
        ExtratorTexto(_config())(corrompido)

    assert str(recusa.value) == MENSAGEM_RECUSA


# ---------------------------------------------------------------------------
# Limites e conferência (integração com poppler e tesseract)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_arquivo_sem_texto_eh_recusado() -> None:
    em_branco = _pdf_de_imagens([_pagina_em_branco()])

    with pytest.raises(ExtracaoImpossivel) as recusa:
        ExtratorTexto(_config())(em_branco)

    assert str(recusa.value) == MENSAGEM_RECUSA


@pytest.mark.integration
def test_limites_recusam_antes_de_extrair(monkeypatch: pytest.MonkeyPatch) -> None:
    _sem_rasterizar(monkeypatch)
    # Bytes que nem PDF são: a recusa por tamanho vem antes da detecção do formato.
    grande = b"x" * 2_000_001
    escaneado = _pdf_de_imagens([_pagina_escaneada()] * 3)

    with pytest.raises(ExtracaoImpossivel) as por_tamanho:
        ExtratorTexto(_config(tamanho_maximo_bytes=2_000_000))(grande)
    with pytest.raises(ExtracaoImpossivel) as por_paginas:
        ExtratorTexto(_config(paginas_maximas_ocr=2))(escaneado)

    assert str(por_tamanho.value) == MENSAGEM_TAMANHO.format(limite_mb=2)
    assert str(por_paginas.value) == MENSAGEM_PAGINAS.format(limite=2)


@pytest.mark.integration
def test_conferencia_nao_roda_ocr(monkeypatch: pytest.MonkeyPatch) -> None:
    _sem_rasterizar(monkeypatch)
    extrator = ExtratorTexto(_config())
    escaneado = _pdf_de_imagens([_pagina_escaneada()])

    assert extrator.conferir(escaneado) == (TipoDocumento.PDF, OrigemTexto.OCR)
    with pytest.raises(ExtracaoImpossivel) as recusa:
        extrator.conferir(_doc())
    assert str(recusa.value) == MENSAGEM_DOC
