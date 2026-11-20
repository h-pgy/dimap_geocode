from collections.abc import Iterator
from contextlib import contextmanager

from .aproveitamento import MENSAGEM_RECUSA
from .deteccao import DetectorTipo
from .erros import ExtracaoImpossivel
from .extrator_docx import ExtratorDocx
from .extrator_ocr import ExtratorOcr
from .extrator_odt import ExtratorOdt
from .extrator_pdf import ExtratorPdf
from .models import ExtracaoConfig, Extrator, OrigemTexto, TextoExtraido, TipoDocumento

MENSAGEM_TAMANHO = "O arquivo passa do limite de {limite_mb} MB."


class ExtratorTexto:
    def __init__(self, config: ExtracaoConfig) -> None:
        extrator_ocr = ExtratorOcr(config=config)
        extrator_pdf = ExtratorPdf(ocr=extrator_ocr)
        extrator_docx = ExtratorDocx()
        extrator_odt = ExtratorOdt()
        self._config = config
        self._detectar_tipo = DetectorTipo()
        self._extratores: dict[TipoDocumento, Extrator] = {
            TipoDocumento.PDF: extrator_pdf,
            TipoDocumento.DOCX: extrator_docx,
            TipoDocumento.ODT: extrator_odt,
        }

    def __call__(self, conteudo: bytes) -> tuple[TipoDocumento, TextoExtraido]:
        return self.pipeline(conteudo)

    def pipeline(self, conteudo: bytes) -> tuple[TipoDocumento, TextoExtraido]:
        tipo = self._tipo(conteudo)
        with self._recusando_falhas():
            return tipo, self._extratores[tipo](conteudo)

    def conferir(self, conteudo: bytes) -> tuple[TipoDocumento, OrigemTexto]:
        tipo = self._tipo(conteudo)
        with self._recusando_falhas():
            return tipo, self._extratores[tipo].conferir(conteudo)

    def _tipo(self, conteudo: bytes) -> TipoDocumento:
        if len(conteudo) > self._config.tamanho_maximo_bytes:
            limite_mb = self._config.tamanho_maximo_bytes // 1_000_000
            raise ExtracaoImpossivel(MENSAGEM_TAMANHO.format(limite_mb=limite_mb))
        with self._recusando_falhas():
            return self._detectar_tipo(conteudo)

    @contextmanager
    def _recusando_falhas(self) -> Iterator[None]:
        # Fail-safe: qualquer falha de biblioteca é recusa do arquivo, nunca anexo sem texto.
        try:
            yield
        except ExtracaoImpossivel:
            # Recusa com mensagem própria passa intacta.
            raise
        except Exception as erro:
            raise ExtracaoImpossivel(MENSAGEM_RECUSA) from erro
