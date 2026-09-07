from pydantic import BaseModel, ConfigDict
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable


class VetorNomeado(BaseModel):
    """Um desenho e o NOME sob o qual ele entra no arquivo. O nome identifica o desenho, nunca o
    lugar em que ele aparece: é isso que faz o mesmo símbolo em toda página ser uma referência só,
    e dois símbolos diferentes na mesma página não se confundirem."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    desenho: Drawing
    nome: str


class DesenharForma:
    """Callable: escreve o vetor no arquivo na primeira vez que ele aparece e, daí em diante, só o
    referencia. `x` e `y` são o canto INFERIOR esquerdo, em pontos, no eixo do reportlab."""

    def __call__(self, canvas: Canvas, vetor: VetorNomeado, x: float, y: float) -> None:
        return self.pipeline(canvas, vetor, x, y)

    def pipeline(self, canvas: Canvas, vetor: VetorNomeado, x: float, y: float) -> None:
        self._escrever_uma_vez(canvas, vetor)
        self._referenciar(canvas, vetor.nome, x, y)

    def _escrever_uma_vez(self, canvas: Canvas, vetor: VetorNomeado) -> None:
        if vetor.nome in self._formas(canvas):
            return
        canvas.beginForm(vetor.nome)
        # Na ORIGEM do form, e não na posição final: quem posiciona é a translação da referência, e é
        # ela que permite o mesmo desenho aparecer em pontos diferentes sem um form por ponto.
        renderPDF.draw(vetor.desenho, canvas, 0, 0)
        canvas.endForm()
        self._formas(canvas).add(vetor.nome)

    def _referenciar(self, canvas: Canvas, nome: str, x: float, y: float) -> None:
        # `doForm` desenha no estado gráfico corrente: transladar antes é o que posiciona a
        # referência, e o `saveState` é o que impede a translação de vazar para o resto da página.
        canvas.saveState()
        canvas.translate(x, y)
        canvas.doForm(nome)
        canvas.restoreState()

    def _formas(self, canvas: Canvas) -> set[str]:
        # O registro vive no CANVAS: há um canvas por documento, e é ele que guarda os forms já
        # escritos.
        return canvas.__dict__.setdefault("_formas_escritas", set())


class VetorReferenciado(Flowable):
    """O mesmo vetor, agora no FLUXO do corpo. `Drawing` também é `Flowable`, mas se reescreve por
    ocorrência; este referencia, e é o que permite repetir o símbolo sem repetir os bytes."""

    def __init__(self, vetor: VetorNomeado) -> None:
        super().__init__()
        self._vetor = vetor
        self.width = vetor.desenho.width
        self.height = vetor.desenho.height
        self.hAlign = "CENTER"

    def wrap(self, largura_disponivel: float, altura_disponivel: float) -> tuple[float, float]:
        return self.width, self.height

    def draw(self) -> None:
        # A origem do canvas já é o canto inferior esquerdo do flowable quando o platypus chama
        # `draw`: a translação restante é zero.
        desenhar_forma(self.canv, self._vetor, 0.0, 0.0)


desenhar_forma = DesenharForma()
