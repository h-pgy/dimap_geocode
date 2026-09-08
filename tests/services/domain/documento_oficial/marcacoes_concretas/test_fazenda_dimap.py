from io import BytesIO
from pathlib import Path
from typing import cast

from pypdf import PdfReader
from pypdf.generic import DictionaryObject
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph

from services.domain.documento_oficial import (
    MarcacaoConfig,
    TemaConfig,
    marcacao_fazenda_dimap,
    montar_tema,
)
from services.utils.pdf import DocumentoPdfInput, gerar_pdf
from services.utils.pdf.models import A4, Orientacao

SVG_RETANGULO = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10" viewBox="0 0 20 10">
<rect x="0" y="0" width="20" height="10" fill="#336633" />
</svg>"""

ESTILO_NORMAL = getSampleStyleSheet()["Normal"]


def _svg(tmp_path: Path, nome: str) -> Path:
    caminho = tmp_path / nome
    caminho.write_text(SVG_RETANGULO)
    return caminho


# ---------------------------------------------------------------------------
# As cinco marcas em toda página, e a marca d'água sob o corpo
# ---------------------------------------------------------------------------


def test_papel_da_fazenda_traz_as_cinco_marcas_em_toda_pagina(tmp_path: Path) -> None:
    tema = montar_tema(TemaConfig())
    config = MarcacaoConfig(
        logo_horizontal=_svg(tmp_path, "h.svg"),
        logo_vertical=_svg(tmp_path, "v.svg"),
    )
    marcacao = marcacao_fazenda_dimap(config, tema)

    corpo = (
        Paragraph("Corpo pagina 1", ESTILO_NORMAL),
        PageBreak(),
        Paragraph("Corpo pagina 2", ESTILO_NORMAL),
        PageBreak(),
        Paragraph("Corpo pagina 3", ESTILO_NORMAL),
    )
    pdf = gerar_pdf(DocumentoPdfInput(titulo="Amostra", corpo=corpo, marcacao=marcacao))
    paginas = PdfReader(BytesIO(pdf)).pages

    assert len(paginas) == 3
    for numero, pagina in enumerate(paginas, start=1):
        recursos = cast(DictionaryObject, pagina["/Resources"])
        xobjects = recursos.get("/XObject", {})
        assert any(nome.endswith("timbre") for nome in xobjects)
        assert any(nome.endswith("marca_dagua") for nome in xobjects)

        texto = pagina.extract_text()
        assert config.unidade[0] in texto
        assert config.endereco[0] in texto
        assert f"Página {numero} de 3" in texto

        fluxo = pagina.get_contents()
        assert fluxo is not None
        conteudo = fluxo.get_data()
        indice_marca_dagua = conteudo.find(b"marca_dagua Do")
        indice_corpo = conteudo.find(f"(Corpo pagina {numero})".encode())
        assert indice_marca_dagua != -1
        assert indice_corpo != -1
        assert indice_marca_dagua < indice_corpo


# ---------------------------------------------------------------------------
# O papel timbrado atual sai inalterado pela SPEC documentos_oficiais/005
# ---------------------------------------------------------------------------


def test_papel_timbrado_atual_permanece_identico(tmp_path: Path) -> None:
    tema = montar_tema(TemaConfig())
    config = MarcacaoConfig(
        logo_horizontal=_svg(tmp_path, "h.svg"),
        logo_vertical=_svg(tmp_path, "v.svg"),
    )
    tamanho = A4.orientar(Orientacao.RETRATO)

    sem_qr = marcacao_fazenda_dimap(config, tema).para(1, 1)
    com_qr = marcacao_fazenda_dimap(config, tema, qr_verificacao="https://exemplo/verificar").para(
        1, 1
    )

    # Valores tirados do papel timbrado ANTES de `largura_mm` existir no ABC `Marca` — a
    # generalização do compositor lado a lado não pode mexer no que já está em produção.
    margens_sem_qr = sem_qr.margens(tamanho)
    assert margens_sem_qr.esquerda_mm == 25.0
    assert margens_sem_qr.direita_mm == 25.0
    assert margens_sem_qr.superior_mm == 52.0
    assert margens_sem_qr.inferior_mm == 31.4
    assert len(list(sem_qr._faixas(tamanho))) == 3

    margens_com_qr = com_qr.margens(tamanho)
    assert margens_com_qr.superior_mm == 52.0
    assert margens_com_qr.inferior_mm == 48.0
    assert len(list(com_qr._faixas(tamanho))) == 2
