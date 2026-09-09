"""Testes de apps/documentos/acervo.py (SPEC documentos_oficiais/008): a persistência do
documento emitido — guardar o que a selagem produziu, e buscá-lo de volta pelo código."""

from io import BytesIO
from typing import Any

from django.utils import timezone
from pydantic import SecretStr
from reportlab.pdfgen.canvas import Canvas

import pytest

from apps.documentos.acervo import guardar_documento
from apps.documentos.models import DocumentoEmitido
from services.domain.documento_selado import (
    AlvoDoAto,
    AutorDoAto,
    EnvelopeAto,
    gerar_codigo,
    montar_envelope,
)
from services.utils.assinatura import ConferirInput, SelarInput, conferir_selo, selar_documento

banco = pytest.mark.banco

SEGREDO = SecretStr("segredo-de-teste")


def _pdf() -> bytes:
    buffer = BytesIO()
    canvas = Canvas(buffer)
    canvas.drawString(72, 720, "Documento de teste")
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def _autor(**overrides: Any) -> AutorDoAto:
    defaults: dict[str, Any] = {
        "nome": "Fulano de Tal",
        "unidade": "DIMAP-1",
        "cargo_base": "Agente Fazendário",
        "cargo_comissao": None,
    }
    return AutorDoAto(**(defaults | overrides))


def _ato(**overrides: Any) -> EnvelopeAto:
    defaults: dict[str, Any] = {
        "codigo": gerar_codigo(),
        "acao": "certidoes.lancamento",
        "operacao": "emissao",
        "autor": _autor(),
        "alvo": AlvoDoAto(tipo="lote", identificador="123.456.7890-1"),
        "emitido_em": timezone.now(),
    }
    return EnvelopeAto(**(defaults | overrides))


def _documento_selado(ato: EnvelopeAto, **overrides: Any) -> Any:
    defaults: dict[str, Any] = {
        "pdf": _pdf(),
        "dados": montar_envelope(ato),
        "campos_publicos": ato.campos_publicos,
        "segredo": SEGREDO,
        "id_chave": "k1",
    }
    return selar_documento(SelarInput(**(defaults | overrides)))


# ---------------------------------------------------------------------------
# O documento emitido é guardado inteiro, e os bytes conferem contra o selo
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_documento_emitido_eh_guardado_inteiro() -> None:
    ato = _ato()
    selado = _documento_selado(ato)

    guardar_documento(selado, ato, execucao=None)

    linha = DocumentoEmitido.objects.get(codigo=ato.codigo)
    assert bytes(linha.arquivo) == selado.pdf
    assert linha.envelope == selado.envelope
    assert linha.emitido_em == ato.emitido_em

    conferencia = conferir_selo(ConferirInput(pdf=bytes(linha.arquivo), segredo=SEGREDO))
    assert conferencia.estado.value == "integro"
