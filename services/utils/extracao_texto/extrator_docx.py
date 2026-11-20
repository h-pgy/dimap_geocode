from collections.abc import Iterator
from io import BytesIO

from docx import Document
from docx.document import Document as DocumentoDocx

from .aproveitamento import texto_aproveitavel
from .models import OrigemTexto, TextoExtraido


class ExtratorDocx:
    def __call__(self, conteudo: bytes) -> TextoExtraido:
        documento = Document(BytesIO(conteudo))
        return texto_aproveitavel(
            "\n".join(self._trechos(documento)), OrigemTexto.CAMADA_DE_TEXTO
        )

    def conferir(self, conteudo: bytes) -> OrigemTexto:
        return self(conteudo).origem

    def _trechos(self, documento: DocumentoDocx) -> Iterator[str]:
        yield from (paragrafo.text for paragrafo in documento.paragraphs)
        for tabela in documento.tables:
            for linha in tabela.rows:
                yield from (celula.text for celula in linha.cells)
