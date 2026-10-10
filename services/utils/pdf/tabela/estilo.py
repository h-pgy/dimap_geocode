from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import TableStyle

from ..models import Grade
from .regras import RegraTabela


class EstiloTabela:
    """Callable: as regras declaradas viram um `TableStyle` só. A tipografia vem de quem chama (o
    tema do §002), nunca daqui."""

    def __init__(
        self,
        celula: ParagraphStyle,
        cabecalho: ParagraphStyle,
        regras: tuple[RegraTabela, ...] = (),
    ) -> None:
        self.celula = celula
        self.cabecalho = cabecalho
        self._regras = regras

    def __call__(self, grade: Grade) -> TableStyle:
        return TableStyle([comando for regra in self._regras for comando in regra(grade)])
