from pydantic import BaseModel, ConfigDict
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, Table, TableStyle

from .models import EstiloTraco


class QuadroInput(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    conteudo: tuple[Flowable, ...]
    largura_mm: float
    traco: EstiloTraco
    respiro_mm: float


class QuadroPdf:
    """Callable: flowables → um quadro emoldurado, centrado na largura do corpo. Uma célula só: quem
    reparte espaço e quebra página é a `Table` do reportlab, e reimplementar `wrap`/`split` num
    flowable próprio seria refazer o que ela já faz."""

    def __call__(self, pedido: QuadroInput) -> Flowable:
        return self.pipeline(pedido)

    def pipeline(self, pedido: QuadroInput) -> Flowable:
        quadro = Table([[list(pedido.conteudo)]], colWidths=[pedido.largura_mm * mm])
        quadro.setStyle(self._estilo(pedido))
        # Centrado na moldura do corpo, e não encostado na margem esquerda.
        quadro.hAlign = "CENTER"
        return quadro

    def _estilo(self, pedido: QuadroInput) -> TableStyle:
        respiro = pedido.respiro_mm * mm
        return TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), pedido.traco.espessura_mm * mm, pedido.traco.cor),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), respiro),
                ("RIGHTPADDING", (0, 0), (-1, -1), respiro),
                ("TOPPADDING", (0, 0), (-1, -1), respiro),
                ("BOTTOMPADDING", (0, 0), (-1, -1), respiro),
            ]
        )


quadro_pdf = QuadroPdf()
