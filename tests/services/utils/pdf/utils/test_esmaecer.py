from pathlib import Path

import pytest

from services.utils.pdf.utils.esmaecer import EsmaecerSvgInput, esmaecer_svg

SVG_COM_CORES_CONHECIDAS = """<svg xmlns="http://www.w3.org/2000/svg">
<path fill:rgb(0%,65.1%,31.37%) d="M0 0 L10 10" />
<path stroke:rgb(10%,10%,10%) d="M0 0 L10 10" />
</svg>"""

SVG_COM_COR_NAO_SUPORTADA = """<svg xmlns="http://www.w3.org/2000/svg">
<path fill:#3fa83c d="M0 0 L10 10" />
</svg>"""


def _svg(tmp_path: Path, conteudo: str, nome: str = "logo.svg") -> Path:
    caminho = tmp_path / nome
    caminho.write_text(conteudo)
    return caminho


def test_esmaecer_clareia_no_lugar_e_recusa_cor_que_nao_entende(tmp_path: Path) -> None:
    caminho = _svg(tmp_path, SVG_COM_CORES_CONHECIDAS)

    resultado = esmaecer_svg(EsmaecerSvgInput(caminho=caminho, forca=0.5))

    assert resultado.cores_clareadas == 2
    clareado = caminho.read_text()
    # Nenhuma cor conserva o valor original...
    assert "fill:rgb(0%,65.1%,31.37%)" not in clareado
    assert "stroke:rgb(10%,10%,10%)" not in clareado
    # ...e toda cor sobe para acima do limiar de clareza (mais perto do branco que da cor original).
    assert "fill:rgb(50.0%,82.55%,65.685%)" in clareado
    assert "stroke:rgb(55.0%,55.0%,55.0%)" in clareado

    caminho_invalido = _svg(tmp_path, SVG_COM_COR_NAO_SUPORTADA, nome="invalido.svg")
    original = caminho_invalido.read_text()

    with pytest.raises(ValueError):
        esmaecer_svg(EsmaecerSvgInput(caminho=caminho_invalido, forca=0.5))

    # A recusa acontece ANTES de escrever: o arquivo permanece intacto.
    assert caminho_invalido.read_text() == original
