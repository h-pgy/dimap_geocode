from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from services.utils.pdf.models import EstiloTexto, TamanhoPagina


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

    def vetor(self, x_mm: float, y_mm: float, desenho: Drawing, nome: str) -> None:
        # O vetor vira Form XObject: escrito UMA vez no arquivo e só REFERENCIADO a cada página.
        if nome not in self._formas():
            self._canvas.beginForm(nome)
            # A altura entra na conta: a origem do reportlab é o canto INFERIOR.
            renderPDF.draw(desenho, self._canvas, x_mm * mm, self._y(y_mm) - desenho.height)
            self._canvas.endForm()
            self._formas().add(nome)
        self._canvas.doForm(nome)

    def _formas(self) -> set[str]:
        # O registro vive no CANVAS, não na folha: há uma folha por página e um canvas por
        # documento, e é o canvas que guarda os forms já escritos.
        return self._canvas.__dict__.setdefault("_formas_escritas", set())

    def _y(self, y_mm: float) -> float:
        # A inversão do eixo, num lugar só: y=0 é o topo da folha para quem chama.
        return (self.tamanho.altura_mm - y_mm) * mm
