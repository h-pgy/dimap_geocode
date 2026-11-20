from io import BytesIO
from zipfile import ZipFile

from .erros import ExtracaoImpossivel
from .models import TipoDocumento

MENSAGEM_FORMATO = "Só são aceitos arquivos PDF, DOCX ou ODT."
MENSAGEM_DOC = (
    "Arquivos .doc (Word 97–2003) não são aceitos. "
    "Abra o arquivo no Word ou no LibreOffice, salve como DOCX e envie de novo."
)
ASSINATURA_PDF = b"%PDF-"
ASSINATURA_ZIP = b"PK\x03\x04"
ASSINATURA_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
MIMETYPE_ODT = b"application/vnd.oasis.opendocument.text"


class DetectorTipo:
    def __call__(self, conteudo: bytes) -> TipoDocumento:
        if conteudo.startswith(ASSINATURA_PDF):
            return TipoDocumento.PDF
        if conteudo.startswith(ASSINATURA_ZIP):
            return self._tipo_do_zip(conteudo)
        if conteudo.startswith(ASSINATURA_OLE):
            raise ExtracaoImpossivel(MENSAGEM_DOC)
        raise ExtracaoImpossivel(MENSAGEM_FORMATO)

    def _tipo_do_zip(self, conteudo: bytes) -> TipoDocumento:
        with ZipFile(BytesIO(conteudo)) as pacote:
            membros = set(pacote.namelist())
            # O DOCX do LibreOffice tem o mesmo `word/document.xml` do DOCX do Word.
            if "word/document.xml" in membros:
                return TipoDocumento.DOCX
            # ODS e ODP também têm `mimetype`, com outro valor.
            if "mimetype" in membros and pacote.read("mimetype") == MIMETYPE_ODT:
                return TipoDocumento.ODT
        raise ExtracaoImpossivel(MENSAGEM_FORMATO)
