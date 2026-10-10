from functools import partial
from io import BytesIO

from pydantic import BaseModel, ConfigDict
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, SimpleDocTemplate

from services.utils.pdf.documento_marcado import MarcacaoDocumento
from services.utils.pdf.models import A4, FormatoPagina, TamanhoPagina
from services.utils.pdf.numeracao import CanvasMarcado


class DocumentoPdfInput(BaseModel):
    # `Flowable` é do reportlab e não tem schema Pydantic — ver Caveats da SPEC documentos_oficiais/001.
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    titulo: str
    corpo: tuple[Flowable, ...]
    marcacao: MarcacaoDocumento
    formato: FormatoPagina = A4


class DocumentoPdf:
    """Callable: o que fluir pelo corpo, dentro da moldura que a marcação deixou, vira PDF."""

    def __call__(self, pedido: DocumentoPdfInput) -> bytes:
        return self.pipeline(pedido)

    def pipeline(self, pedido: DocumentoPdfInput) -> bytes:
        buffer = BytesIO()
        # Sem `onFirstPage`/`onLaterPages`: as duas camadas são pintadas pelo canvas, na volta.
        # Aqui o corpo só flui dentro da moldura, sem saber que marcação vai receber.
        self._montar(buffer, pedido).build(
            list(pedido.corpo),
            canvasmaker=partial(
                CanvasMarcado,
                marcacao=pedido.marcacao,
                tamanho=self._tamanho(pedido),
            ),
        )
        return buffer.getvalue()

    def _tamanho(self, pedido: DocumentoPdfInput) -> TamanhoPagina:
        return pedido.formato.orientar(pedido.marcacao.orientacao())

    def _montar(self, buffer: BytesIO, pedido: DocumentoPdfInput) -> SimpleDocTemplate:
        tamanho = self._tamanho(pedido)
        margens = pedido.marcacao.margens(tamanho)
        return SimpleDocTemplate(
            buffer,
            pagesize=(tamanho.largura_mm * mm, tamanho.altura_mm * mm),
            leftMargin=margens.esquerda_mm * mm,
            rightMargin=margens.direita_mm * mm,
            topMargin=margens.superior_mm * mm,
            bottomMargin=margens.inferior_mm * mm,
            title=pedido.titulo,
        )


gerar_pdf = DocumentoPdf()
