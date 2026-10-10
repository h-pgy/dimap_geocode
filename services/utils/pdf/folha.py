from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from services.utils.pdf.forma import VetorNomeado, desenhar_forma
from services.utils.pdf.models import EstiloTexto, EstiloTraco, TamanhoPagina


class Folha:
    """UMA página sendo pintada. Ela sabe que número é e quantas há no total — é isso que permite
    'Página X de Y' sem ninguém contar página."""

    def __init__(self, canvas: Canvas, tamanho: TamanhoPagina, pagina: int, total: int) -> None:
        self._canvas = canvas
        self.tamanho = tamanho
        self.pagina = pagina
        self.total = total

    def texto(self, x_mm: float, y_mm: float, conteudo: str, estilo: EstiloTexto) -> None:
        self._canvas.setFont(estilo.fonte, estilo.corpo_pt)
        self._canvas.setFillColor(estilo.cor)
        self._canvas.drawString(x_mm * mm, self._y(y_mm), conteudo)

    # ALTERADO nesta SPEC: recebe o `VetorNomeado` no lugar de desenho + nome soltos, e delega a
    # escrita do form. `y_mm` continua sendo o TOPO do desenho, medido do alto da folha.
    def vetor(self, x_mm: float, y_mm: float, vetor: VetorNomeado) -> None:
        desenhar_forma(
            self._canvas,
            vetor,
            x_mm * mm,
            # A altura entra na conta: a origem do reportlab é o canto INFERIOR.
            self._y(y_mm) - vetor.desenho.height,
        )

    def retangulo(
        self,
        x_mm: float,
        y_mm: float,
        largura_mm: float,
        altura_mm: float,
        estilo: EstiloTraco,
    ) -> None:
        self._canvas.setStrokeColor(estilo.cor)
        self._canvas.setLineWidth(estilo.espessura_mm * mm)
        # `y_mm` é o TOPO, como em `texto` e `vetor`; o reportlab recebe o canto inferior, e a altura
        # entra na conta uma vez só, aqui.
        self._canvas.rect(
            x_mm * mm,
            self._y(y_mm) - altura_mm * mm,
            largura_mm * mm,
            altura_mm * mm,
            stroke=1,
            fill=0,
        )

    def _y(self, y_mm: float) -> float:
        # A inversão do eixo, num lugar só: y=0 é o topo da folha para quem chama.
        return (self.tamanho.altura_mm - y_mm) * mm
