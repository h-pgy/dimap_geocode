from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from django.conf import settings
from django.utils import timezone
from pydantic import SecretStr
from reportlab.pdfgen.canvas import Canvas

from services.domain.documento_oficial import (
    DocumentoAmostraInput,
    RenderizarDocumentoInput,
    RenderizarDocumentoOficial,
    build_marcacao_config,
    build_tema_config,
    marcacao_fazenda_dimap,
    montar_documento_amostra,
    montar_tema,
)
from services.utils.assinatura import (
    ConferirInput,
    EstadoSelo,
    SelarInput,
    conferir_selo,
    selar_documento,
)
from services.utils.assinatura.envelope import embutir_envelope

SEGREDO = SecretStr("segredo-de-teste")


def _pdf(texto: str = "Documento de teste") -> bytes:
    buffer = BytesIO()
    canvas = Canvas(buffer)
    canvas.drawString(72, 720, texto)
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def _pedido(pdf: bytes, **overrides: Any) -> SelarInput:
    defaults: dict[str, Any] = {
        "pdf": pdf,
        "dados": {"alvo": "111"},
        "segredo": SEGREDO,
        "id_chave": "v1",
    }
    return SelarInput(**(defaults | overrides))


# ---------------------------------------------------------------------------
# O que sai da selagem confere com o segredo que o selou
# ---------------------------------------------------------------------------


def test_documento_selado_confere_consigo_mesmo() -> None:
    original = _pdf()

    selado = selar_documento(_pedido(original))

    resultado = conferir_selo(ConferirInput(pdf=selado.pdf, segredo=SEGREDO))
    assert resultado.estado is EstadoSelo.INTEGRO
    # A troca do placeholder pela tag não acrescenta nem tira byte: o arquivo entregue tem o
    # tamanho do arquivo que só recebeu o envelope.
    assert len(selado.pdf) == len(embutir_envelope(original, selado.envelope))


# ---------------------------------------------------------------------------
# Selar o que já foi selado
# ---------------------------------------------------------------------------


def test_selar_documento_ja_selado_eh_recusado() -> None:
    selado = selar_documento(_pedido(_pdf()))

    with pytest.raises(ValueError):
        selar_documento(_pedido(selado.pdf))


# ---------------------------------------------------------------------------
# Artefato: o documento selado abre e continua legível
# ---------------------------------------------------------------------------


@pytest.mark.artefato
def test_amostra_selada_para_conferencia(publicar_artefato: Callable[[str, bytes], Path]) -> None:
    conteudo = montar_documento_amostra(
        DocumentoAmostraInput(ambiente=settings.ALLOWED_HOSTS[0], momento=timezone.now())
    )
    tema = montar_tema(build_tema_config(settings))
    marcacao = marcacao_fazenda_dimap(build_marcacao_config(settings), tema)
    renderizado = RenderizarDocumentoOficial(tema)(
        RenderizarDocumentoInput(conteudo=conteudo, marcacao=marcacao)
    )

    selado = selar_documento(_pedido(renderizado.pdf))

    caminho = publicar_artefato("documento_amostra_selado.pdf", selado.pdf)
    assert caminho.stat().st_size > 0
