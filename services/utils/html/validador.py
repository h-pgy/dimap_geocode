from html.parser import HTMLParser

from .models import ErroHtml, ResultadoValidacaoHtml

# Elementos vazios não entram na pilha e não podem ser fechados.
ELEMENTOS_VAZIOS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
)


class _ColetorTags(HTMLParser):
    """Adaptador do HTMLParser da stdlib — a única herança do módulo, confinada aqui.
    O HTMLParser é leniente por natureza: quem julga é este coletor, não ele."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.abertas: list[tuple[str, int]] = []
        self.erros: list[ErroHtml] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ELEMENTOS_VAZIOS:
            return
        linha, _ = self.getpos()
        self.abertas.append((tag, linha))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # <br/> e <img/> são forma válida. Sem este override o HTMLParser dispara start E end,
        # e o end cairia em handle_endtag como "fecha uma tag que não foi aberta".
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        linha, coluna = self.getpos()
        if tag in ELEMENTOS_VAZIOS:
            self._erro(tag, linha, coluna, f"<{tag}> é elemento vazio e não se fecha")
            return
        if not self.abertas:
            self._erro(tag, linha, coluna, f"</{tag}> fecha uma tag que não foi aberta")
            return
        ultima, linha_abertura = self.abertas[-1]
        if ultima != tag:
            # Não desempilha: <b><i></b></i> deve acusar o aninhamento errado, não "consertá-lo".
            self._erro(tag, linha, coluna, f"</{tag}> fecha antes de <{ultima}>, aberta na linha {linha_abertura}")
            return
        self.abertas.pop()

    def _erro(self, tag: str, linha: int, coluna: int, mensagem: str) -> None:
        self.erros.append(ErroHtml(tag=tag, linha=linha, coluna=coluna, mensagem=mensagem))


class ValidadorHtml:
    """Callable: recebe marcação, devolve o veredito. Boa-formação apenas — não sanitiza."""

    def __call__(self, html: str) -> ResultadoValidacaoHtml:
        coletor = _ColetorTags()
        coletor.feed(html)
        coletor.close()  # fecha o buffer: tag cortada no fim do texto vira erro, não silêncio
        nao_fechadas = tuple(
            ErroHtml(tag=tag, linha=linha, coluna=0, mensagem=f"<{tag}> foi aberta e não foi fechada")
            for tag, linha in coletor.abertas
        )
        return ResultadoValidacaoHtml(erros=(*coletor.erros, *nao_fechadas))


# Instância única do módulo: o validador não guarda estado entre chamadas — o coletor, que guarda,
# nasce e morre dentro do __call__. Quem consome usa como função, sem construir nada.
validar_html = ValidadorHtml()
