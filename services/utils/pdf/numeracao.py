from typing import Any

from reportlab.pdfgen.canvas import Canvas

from services.utils.pdf.documento_marcado import MarcacaoDocumento
from services.utils.pdf.folha import Folha
from services.utils.pdf.models import TamanhoPagina


class CanvasMarcado(Canvas):
    """Guarda cada página em vez de emiti-la, e só no `save` — com o total na mão — decide qual
    marcação vale em cada uma e a pinta."""

    _code: list[Any]

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
        fim_do_corpo = len(self._code)
        marcacao.pintar_fundo(folha)
        # O fundo fica SOB o corpo, e quem empilha é a ordem no content stream: pinta-se depois e
        # gira-se o código. Esvaziar `_code` antes faz o reportlab zerar os forms que o corpo usa.
        self._code = self._code[fim_do_corpo:] + self._code[:fim_do_corpo]
        marcacao.pintar_bordas(folha)
