import io

import segno
from segno.encoder import DataOverflowError

from .models import QrCodeInput, QrCodeSvg


class GerarQrCode:
    """Callable: conteúdo → o símbolo em SVG. Vetor, e não raster: o QR é uma malha de quadrados, e
    quem o amplia ou o imprime em 600 dpi não pode receber pixel."""

    def __call__(self, pedido: QrCodeInput) -> QrCodeSvg:
        return self.pipeline(pedido)

    def pipeline(self, pedido: QrCodeInput) -> QrCodeSvg:
        simbolo = self._codificar(pedido)
        # `symbol_size` já conta o silêncio dos dois lados: é a matriz como ela vai para o
        # arquivo, e é essa conta que a largura impressa divide. `scale=1` mantém o resultado
        # inteiro; o `int()` só resolve o tipo que a lib devolve (`int | float`) sem arredondar.
        lado_bruto, _ = simbolo.symbol_size(scale=1, border=pedido.silencio_modulos)
        modulos = int(lado_bruto)
        return QrCodeSvg(svg=self._svg(simbolo, pedido), modulos=modulos)

    def _codificar(self, pedido: QrCodeInput) -> segno.QRCode:
        # `make_qr`, e não `make`: `make` degrada conteúdo curto para Micro QR, que boa parte dos
        # leitores de celular não lê. O nível declarado é o MÍNIMO — a biblioteca o eleva quando
        # a sobra cabe no mesmo símbolo.
        try:
            return segno.make_qr(pedido.conteudo, error=pedido.correcao.value)
        except DataOverflowError as erro:
            raise ValueError(
                f"Conteúdo de {len(pedido.conteudo)} caracteres não cabe em nenhum QR Code: {erro}"
            ) from erro

    def _svg(self, simbolo: segno.QRCode, pedido: QrCodeInput) -> bytes:
        buffer = io.BytesIO()
        # `scale=1`: cada módulo é uma unidade no SVG, e quem dá tamanho é a página. A declaração
        # XML e as classes CSS saem porque o svglib não as usa e só engordam os bytes.
        simbolo.save(
            buffer,
            kind="svg",
            scale=1,
            border=pedido.silencio_modulos,
            xmldecl=False,
            svgclass=None,
            lineclass=None,
        )
        return buffer.getvalue()


gerar_qr_code = GerarQrCode()
