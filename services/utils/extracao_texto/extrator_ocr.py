from collections.abc import Iterator
from math import ceil
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import monotonic

import pytesseract
from pdf2image import convert_from_path, pdfinfo_from_path
from pdf2image.exceptions import PDFPopplerTimeoutError
from PIL.Image import Image

from .aproveitamento import texto_aproveitavel
from .erros import ExtracaoImpossivel
from .models import ExtracaoConfig, OrigemTexto, TextoExtraido

MENSAGEM_PAGINAS = "PDFs escaneados podem ter até {limite} páginas. Divida o arquivo e envie as partes."
MENSAGEM_PRAZO_OCR = (
    "O OCR deste PDF passou do tempo limite. Divida o arquivo e envie as partes."
)
TIMEOUT_TESSERACT = "Tesseract process timeout"


class ExtratorOcr:
    def __init__(self, config: ExtracaoConfig) -> None:
        self._config = config

    def __call__(self, conteudo: bytes) -> TextoExtraido:
        return self.pipeline(conteudo)

    def pipeline(self, conteudo: bytes) -> TextoExtraido:
        with self._arquivo_temporario(conteudo) as caminho:
            total_paginas = self._conferir_paginas(caminho)
            prazo = self._iniciar_prazo()
            paginas = [
                self._ler_pagina(caminho, numero, prazo)
                for numero in range(1, total_paginas + 1)
            ]
        return texto_aproveitavel("\n".join(paginas), OrigemTexto.OCR)

    def conferir(self, conteudo: bytes) -> OrigemTexto:
        with self._arquivo_temporario(conteudo) as caminho:
            self._conferir_paginas(caminho)
        return OrigemTexto.OCR

    @contextmanager
    def _arquivo_temporario(self, conteudo: bytes) -> Iterator[Path]:
        # O poppler lê de arquivo; gravar uma vez evita regravar o PDF inteiro a cada página.
        with NamedTemporaryFile(suffix=".pdf") as arquivo:
            arquivo.write(conteudo)
            arquivo.flush()
            yield Path(arquivo.name)

    def _conferir_paginas(self, caminho: Path) -> int:
        total = int(pdfinfo_from_path(str(caminho))["Pages"])
        if total > self._config.paginas_maximas_ocr:
            raise ExtracaoImpossivel(
                MENSAGEM_PAGINAS.format(limite=self._config.paginas_maximas_ocr)
            )
        return total

    def _ler_pagina(self, caminho: Path, numero: int, prazo: float) -> str:
        # Uma página por vez, em tons de cinza: a memória fica em uma página (~4 MB a 200 dpi).
        imagem = self._rasterizar(caminho, numero, self._tempo_restante(prazo))
        return self._ler_imagem(imagem, self._tempo_restante(prazo))

    def _rasterizar(self, caminho: Path, numero: int, timeout_s: float) -> Image:
        try:
            imagens = convert_from_path(
                caminho,
                dpi=self._config.dpi_ocr,
                first_page=numero,
                last_page=numero,
                grayscale=True,
                # O pdf2image só aceita segundos inteiros.
                timeout=ceil(timeout_s),
            )
        except PDFPopplerTimeoutError as erro:
            raise ExtracaoImpossivel(MENSAGEM_PRAZO_OCR) from erro
        return imagens[0]

    def _ler_imagem(self, imagem: Image, timeout_s: float) -> str:
        try:
            texto: str = pytesseract.image_to_string(
                imagem, lang=self._config.idioma_ocr, timeout=timeout_s
            )
        except RuntimeError as erro:
            # O pytesseract sinaliza o timeout com um RuntimeError genérico; só a mensagem o distingue.
            if str(erro) != TIMEOUT_TESSERACT:
                raise
            raise ExtracaoImpossivel(MENSAGEM_PRAZO_OCR) from erro
        return texto

    def _iniciar_prazo(self) -> float:
        # Relógio monotônico: um ajuste de hora do sistema no meio do OCR não mexe no prazo.
        return monotonic() + self._config.prazo_ocr_s

    def _tempo_restante(self, prazo: float) -> float:
        restante = prazo - monotonic()
        if restante <= 0:
            raise ExtracaoImpossivel(MENSAGEM_PRAZO_OCR)
        return restante
