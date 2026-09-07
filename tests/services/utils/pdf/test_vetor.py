from io import BytesIO
from pathlib import Path

from services.utils.pdf import carregar_vetor

SVG_RETANGULO = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10" viewBox="0 0 20 10">
<rect x="0" y="0" width="20" height="10" fill="#336633" />
</svg>"""


# ---------------------------------------------------------------------------
# O mesmo SVG, lido do disco ou de bytes em memória, produz o mesmo Drawing
# ---------------------------------------------------------------------------


def test_carregar_vetor_aceita_caminho_e_memoria(tmp_path: Path) -> None:
    caminho = tmp_path / "retangulo.svg"
    caminho.write_text(SVG_RETANGULO)

    do_disco = carregar_vetor(caminho, largura_mm=40.0)
    da_memoria = carregar_vetor(BytesIO(SVG_RETANGULO.encode()), largura_mm=40.0)

    assert do_disco.width == da_memoria.width
    assert do_disco.height == da_memoria.height
