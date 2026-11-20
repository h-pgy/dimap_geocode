from io import BytesIO
from xml.etree import ElementTree
from zipfile import ZipFile

from .aproveitamento import texto_aproveitavel
from .models import OrigemTexto, TextoExtraido

NAMESPACE_TEXTO = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
# As células de tabela do ODT são feitas de parágrafos.
BLOCOS_DE_TEXTO = {f"{{{NAMESPACE_TEXTO}}}p", f"{{{NAMESPACE_TEXTO}}}h"}


class ExtratorOdt:
    def __call__(self, conteudo: bytes) -> TextoExtraido:
        with ZipFile(BytesIO(conteudo)) as pacote:
            raiz = ElementTree.fromstring(pacote.read("content.xml"))
        trechos = (
            "".join(no.itertext()) for no in raiz.iter() if no.tag in BLOCOS_DE_TEXTO
        )
        return texto_aproveitavel("\n".join(trechos), OrigemTexto.CAMADA_DE_TEXTO)

    def conferir(self, conteudo: bytes) -> OrigemTexto:
        return self(conteudo).origem
