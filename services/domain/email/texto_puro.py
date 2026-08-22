from .models import (
    Botao,
    ConteudoEmail,
    Destaque,
    Divisor,
    Imagem,
    Paragrafo,
    Subtitulo,
    Tabela,
    Titulo,
)


def _cabecalho(bloco: Tabela) -> tuple[tuple[str, ...], ...]:
    return (bloco.cabecalho,) if bloco.cabecalho else ()


class RenderizadorTextoPuro:
    """Callable: ConteudoEmail → o corpo em texto. Bloco que não diz nada em texto não entra."""

    def __call__(self, conteudo: ConteudoEmail) -> str:
        return "\n\n".join(self.pipeline(conteudo))

    def pipeline(self, conteudo: ConteudoEmail) -> list[str]:
        blocos = [texto for bloco in conteudo.blocos if (texto := self._escrever(bloco))]
        blocos.append(conteudo.rodape)
        return blocos

    def _escrever(self, bloco: object) -> str:
        match bloco:
            case Titulo() | Subtitulo() | Paragrafo():
                return bloco.texto
            case Destaque():
                return f"{bloco.rotulo}: {bloco.valor}"
            case Tabela():
                # Sem moldura: cada linha vira uma linha de texto com as células separadas.
                return "\n".join(" | ".join(linha) for linha in (*_cabecalho(bloco), *bloco.linhas))
            case Imagem():
                return f"[imagem: {bloco.alternativo}]"
            case Botao():
                # O botão não existe em texto: sobra o rótulo e a URL inteira, clicável no cliente.
                return f"{bloco.rotulo}: {bloco.url}"
            case Divisor():
                return ""  # a pausa já é o parágrafo em branco do join
        raise AssertionError(f"bloco sem forma em texto: {bloco!r}")


renderizar_texto_puro = RenderizadorTextoPuro()
