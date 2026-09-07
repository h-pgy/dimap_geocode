from typing import Any

from reportlab.pdfgen.canvas import Canvas

from services.utils.pdf.documento_marcado import MarcacaoDocumento
from services.utils.pdf.folha import Folha
from services.utils.pdf.models import TamanhoPagina


class CanvasMarcado(Canvas):
    """Guarda cada página em vez de emiti-la, e só no `save` — com o total na mão — decide qual
    marcação vale em cada uma e a pinta."""

    def __init__(
        self,
        *args: object,
        marcacao: MarcacaoDocumento,
        tamanho: TamanhoPagina,
        **kwargs: object,
    ):
        super().__init__(*args, **kwargs)
        self._paginas: list[dict[str, Any]] = []
        self._marcacao = marcacao
        self._tamanho = tamanho

    def showPage(self) -> None:  # noqa: N802 — assinatura do reportlab
        self._paginas.append(dict(self.__dict__))
        # Sem reiniciar a página, o estado do canvas não se separa entre uma e outra e o
        # documento sai com menos páginas do que o conteúdo pede.
        self._startPage()

    def save(self) -> None:
        total = len(self._paginas)
        for numero, estado in enumerate(self._paginas, start=1):
            self.__dict__.update(estado)
            self._pintar(numero, total)
            super().showPage()
        super().save()

    def _pintar(self, numero: int, total: int) -> None:
        marcacao = self._marcacao.para(numero, total)
        folha = Folha(self, self._tamanho, pagina=numero, total=total)
        corpo: list[Any] = self._code
        # O fundo tem de ficar SOB o corpo. Como o corpo já desenhou, esvazia-se o código da
        # página, pinta-se o fundo e devolve-se o corpo por cima — a ordem no content stream é a
        # ordem de empilhamento do PDF. Sem isto a marca de fundo cobriria o que o documento diz.
        self._code: list[Any] = []
        marcacao.pintar_fundo(folha)
        self._code = self._code + corpo
        marcacao.pintar_bordas(folha)
