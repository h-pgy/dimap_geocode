from io import BytesIO

from pypdf import PdfReader

from .aproveitamento import tem_texto_util, texto_aproveitavel
from .models import Extrator, OrigemTexto, TextoExtraido


class ExtratorPdf:
    def __init__(self, ocr: Extrator) -> None:
        self._ocr = ocr

    def __call__(self, conteudo: bytes) -> TextoExtraido:
        camada = self._camada(conteudo)
        if tem_texto_util(camada):
            return texto_aproveitavel(camada, OrigemTexto.CAMADA_DE_TEXTO)
        return self._ocr(conteudo)

    def conferir(self, conteudo: bytes) -> OrigemTexto:
        if tem_texto_util(self._camada(conteudo)):
            return OrigemTexto.CAMADA_DE_TEXTO
        return self._ocr.conferir(conteudo)

    def _camada(self, conteudo: bytes) -> str:
        leitor = PdfReader(BytesIO(conteudo))
        return "\n".join(pagina.extract_text() or "" for pagina in leitor.pages)
