import json
from io import BytesIO
from typing import Any

from pypdf import PdfReader, PdfWriter

from .constants import CHAVE_METADADO


class EmbutirEnvelope:
    """Callable: bytes + envelope → bytes com o envelope no `/Info`. Guardar em `/Info`, e não em
    stream próprio, é o que faz o envelope sobreviver a leitura por qualquer biblioteca."""

    def __call__(self, pdf: bytes, envelope: dict[str, Any]) -> bytes:
        return self.pipeline(pdf, envelope)

    def pipeline(self, pdf: bytes, envelope: dict[str, Any]) -> bytes:
        escritor = PdfWriter()
        escritor.append_pages_from_reader(PdfReader(BytesIO(pdf)))
        escritor.add_metadata({CHAVE_METADADO: self._serializar(envelope)})
        buffer = BytesIO()
        escritor.write(buffer)
        return buffer.getvalue()

    def _serializar(self, envelope: dict[str, Any]) -> str:
        # `ensure_ascii=True` é o que garante que os 64 dígitos da tag entrem no arquivo como texto
        # simples, e não dentro de uma string reencodada por causa de um acento no envelope.
        return json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def ler_envelope(pdf: bytes) -> dict[str, Any] | None:
    # Quem lê pode estar lendo arquivo de terceiro: PDF que não abre, `/Info` ausente, JSON
    # quebrado e JSON que não é objeto são todos "não há envelope aqui" — nunca erro do sistema.
    try:
        metadados = PdfReader(BytesIO(pdf)).metadata
    except Exception:
        return None
    if metadados is None or CHAVE_METADADO not in metadados:
        return None
    try:
        # O `pypdf` devolve um `PdfObject`; o que não for texto morre no `json.loads`.
        envelope = json.loads(str(metadados[CHAVE_METADADO]))
    except (TypeError, ValueError):
        return None
    if not isinstance(envelope, dict):
        return None
    return envelope


embutir_envelope = EmbutirEnvelope()
