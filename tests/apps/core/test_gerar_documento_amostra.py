from collections.abc import Callable
from io import BytesIO
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone
from pypdf import PdfReader
from pytest_django.fixtures import SettingsWrapper

from services.domain.documento_oficial import (
    DocumentoAmostraInput,
    RenderizarDocumentoInput,
    RenderizarDocumentoOficial,
    build_marcacao_config,
    build_tema_config,
    marcacao_fazenda_dimap,
    montar_documento_amostra,
    montar_tema,
    url_de_conferencia,
)

SVG_RETANGULO = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10" viewBox="0 0 20 10">
<rect x="0" y="0" width="20" height="10" fill="#336633" />
</svg>"""


def _logos_sinteticos(tmp_path: Path, settings: SettingsWrapper) -> None:
    horizontal = tmp_path / "h.svg"
    vertical = tmp_path / "v.svg"
    horizontal.write_text(SVG_RETANGULO)
    vertical.write_text(SVG_RETANGULO)
    settings.DOCUMENTO_LOGO_HORIZONTAL = horizontal
    settings.DOCUMENTO_LOGO_VERTICAL = vertical


# ---------------------------------------------------------------------------
# O comando grava o PDF no caminho pedido, e só ali
# ---------------------------------------------------------------------------


def test_comando_grava_a_amostra_no_caminho_pedido(
    tmp_path: Path,
    settings: SettingsWrapper,
) -> None:
    _logos_sinteticos(tmp_path, settings)
    pasta_destino = tmp_path / "saida"
    destino = pasta_destino / "amostra.pdf"

    call_command("gerar_documento_amostra", str(destino))

    conteudo = destino.read_bytes()
    assert conteudo.startswith(b"%PDF")
    assert len(PdfReader(BytesIO(conteudo)).pages) > 1
    assert list(pasta_destino.iterdir()) == [destino]


# ---------------------------------------------------------------------------
# Artefato para conferência visual do timbre, da marca d'água e da numeração
# ---------------------------------------------------------------------------


@pytest.mark.artefato
def test_amostra_para_conferencia(publicar_artefato: Callable[[str, bytes], Path]) -> None:
    conteudo = montar_documento_amostra(
        DocumentoAmostraInput(ambiente=settings.ALLOWED_HOSTS[0], momento=timezone.now())
    )
    tema = montar_tema(build_tema_config(settings))
    marcacao = marcacao_fazenda_dimap(build_marcacao_config(settings), tema)
    renderizado = RenderizarDocumentoOficial(tema)(
        RenderizarDocumentoInput(conteudo=conteudo, marcacao=marcacao)
    )

    caminho = publicar_artefato("documento_amostra.pdf", renderizado.pdf)
    assert caminho.stat().st_size > 0


# ---------------------------------------------------------------------------
# QR de verificação no corpo E no rodapé, para conferir com o celular
# ---------------------------------------------------------------------------


@pytest.mark.artefato
def test_amostra_com_qr_no_corpo_e_no_rodape(
    publicar_artefato: Callable[[str, bytes], Path],
) -> None:
    ambiente = settings.ALLOWED_HOSTS[0]
    conteudo = montar_documento_amostra(
        DocumentoAmostraInput(ambiente=ambiente, momento=timezone.now())
    )
    tema = montar_tema(build_tema_config(settings))
    marcacao = marcacao_fazenda_dimap(
        build_marcacao_config(settings),
        tema,
        qr_verificacao=url_de_conferencia(ambiente),
    )
    renderizado = RenderizarDocumentoOficial(tema)(
        RenderizarDocumentoInput(conteudo=conteudo, marcacao=marcacao)
    )

    caminho = publicar_artefato("documento_amostra_qr.pdf", renderizado.pdf)
    assert caminho.stat().st_size > 0
