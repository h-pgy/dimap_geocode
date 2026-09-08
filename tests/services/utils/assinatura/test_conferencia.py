from io import BytesIO
from typing import Any

from pydantic import SecretStr
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen.canvas import Canvas

from services.utils.assinatura import (
    ConferirInput,
    EstadoSelo,
    ResultadoConferencia,
    SelarInput,
    conferir_selo,
    selar_documento,
)
from services.utils.assinatura.constants import CHAVE_METADADO
from services.utils.assinatura.envelope import embutir_envelope

SEGREDO = SecretStr("segredo-de-teste")
OUTRO_SEGREDO = SecretStr("outro-segredo")
NOME_ACENTUADO = "João Gonçalves de Assunção"


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


def _conferencia(pdf: bytes, segredo: SecretStr = SEGREDO) -> ResultadoConferencia:
    return conferir_selo(ConferirInput(pdf=pdf, segredo=segredo))


def _virar_byte(pdf: bytes, posicao: int) -> bytes:
    return pdf[:posicao] + bytes([pdf[posicao] ^ 0x01]) + pdf[posicao + 1 :]


def _com_metadado(pdf: bytes, valor: str) -> bytes:
    """Escreve à mão o que a selagem escreveria — é como se forja um arquivo de terceiro."""
    escritor = PdfWriter()
    escritor.append_pages_from_reader(PdfReader(BytesIO(pdf)))
    escritor.add_metadata({CHAVE_METADADO: valor})
    buffer = BytesIO()
    escritor.write(buffer)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Um byte virado derruba o selo
# ---------------------------------------------------------------------------


def test_um_byte_virado_no_conteudo_derruba_o_selo() -> None:
    selado = selar_documento(_pedido(_pdf()))
    # Dentro do stream comprimido da página, muito depois do `/Info` onde mora o envelope.
    posicao = selado.pdf.find(b"stream") + 30

    adulterado = _virar_byte(selado.pdf, posicao)

    assert _conferencia(adulterado).estado is EstadoSelo.VIOLADO


def test_alteracao_no_envelope_derruba_o_selo() -> None:
    selado = selar_documento(_pedido(_pdf()))

    adulterado = embutir_envelope(selado.pdf, {**selado.envelope, "alvo": "222"})

    resultado = _conferencia(adulterado)
    assert resultado.estado is EstadoSelo.VIOLADO
    assert resultado.envelope is not None
    assert resultado.envelope["alvo"] == "222"


def test_segredo_diferente_derruba_o_selo() -> None:
    selado = selar_documento(_pedido(_pdf()))

    assert _conferencia(selado.pdf, OUTRO_SEGREDO).estado is EstadoSelo.VIOLADO


# ---------------------------------------------------------------------------
# Sem selo não é selo violado
# ---------------------------------------------------------------------------


def test_documento_sem_selo_eh_distinguido_de_selo_violado() -> None:
    resultado = _conferencia(_pdf())

    assert resultado.estado is EstadoSelo.SEM_SELO
    assert resultado.envelope is None
    assert resultado.publicos is None


def test_arquivo_ilegivel_devolve_sem_selo() -> None:
    assert _conferencia(b"isto nao e um pdf").estado is EstadoSelo.SEM_SELO
    assert _conferencia(_com_metadado(_pdf(), "{isto nao e json")).estado is EstadoSelo.SEM_SELO


def test_tag_fora_de_forma_devolve_violado() -> None:
    forjado = embutir_envelope(_pdf(), {"alvo": "111", "tag": "nao e um hexdigest"})

    assert _conferencia(forjado).estado is EstadoSelo.VIOLADO


# ---------------------------------------------------------------------------
# O que a conferência devolve do envelope
# ---------------------------------------------------------------------------


def test_envelope_volta_com_acentuacao_intacta() -> None:
    selado = selar_documento(_pedido(_pdf(), dados={"servidor": NOME_ACENTUADO}))

    resultado = _conferencia(selado.pdf)

    assert resultado.estado is EstadoSelo.INTEGRO
    assert resultado.envelope is not None
    assert resultado.envelope["servidor"] == NOME_ACENTUADO


def test_conferencia_devolve_so_os_campos_publicos() -> None:
    selado = selar_documento(
        _pedido(
            _pdf(),
            dados={"alvo": "111", "emitido_por": "servidor"},
            campos_publicos=("alvo",),
        )
    )

    resultado = _conferencia(selado.pdf)

    assert resultado.publicos == {"alvo": "111"}
    assert resultado.envelope is not None
    assert resultado.envelope["emitido_por"] == "servidor"
