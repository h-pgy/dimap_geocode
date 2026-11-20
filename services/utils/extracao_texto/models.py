from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

MINIMO_CARACTERES_UTEIS = 40


class TipoDocumento(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    ODT = "odt"


class OrigemTexto(StrEnum):
    CAMADA_DE_TEXTO = "camada_de_texto"
    OCR = "ocr"


class TextoExtraido(BaseModel):
    """O texto aproveitável de um arquivo. Não existe TextoExtraido vazio: a extração falha antes."""

    conteudo: str = Field(min_length=MINIMO_CARACTERES_UTEIS)
    origem: OrigemTexto


class ExtracaoConfig(BaseModel):
    """Limites e parâmetros do OCR. Nasce na orquestração (settings) e é injetada no extrator."""

    model_config = ConfigDict(frozen=True)

    tamanho_maximo_bytes: int = Field(gt=0)
    paginas_maximas_ocr: int = Field(gt=0)
    prazo_ocr_s: float = Field(gt=0)
    # Precisa do pacote tesseract-ocr-<idioma> na imagem.
    idioma_ocr: str = Field(min_length=3)
    dpi_ocr: int = Field(gt=0)


class Extrator(Protocol):
    def __call__(self, conteudo: bytes) -> TextoExtraido: ...

    def conferir(self, conteudo: bytes) -> OrigemTexto: ...
