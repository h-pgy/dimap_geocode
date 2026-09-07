from abc import ABC, abstractmethod
from collections.abc import Callable
from html import escape
from typing import Any

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Flowable, ListFlowable, ListItem, Paragraph

from services.utils.pdf import TabelaInput, carregar_vetor, tabela_pdf

from .models import BlocoTextual, Imagem, Lista, Paragrafo, Subtitulo, Tabela, Tema, Titulo


def _texto(bruto: str) -> str:
    # `Paragraph` interpreta marcação própria do reportlab: o escape é daqui, como no e-mail.
    return escape(bruto)


class EscritorTexto[B: BlocoTextual](ABC):
    """Base dos blocos de uma linha de texto. A herança define interface e nada mais: o que varia
    é o estilo, e `__call__` é o mesmo para os três."""

    def __init__(self, tema: Tema) -> None:
        self._tema = tema

    def __call__(self, bloco: B) -> Flowable:
        return Paragraph(_texto(bloco.texto), self._estilo(bloco))

    @abstractmethod
    def _estilo(self, bloco: B) -> ParagraphStyle: ...


class EscritorTitulo(EscritorTexto[Titulo]):
    def _estilo(self, bloco: Titulo) -> ParagraphStyle:
        return self._tema.estilos["titulo"]


class EscritorSubtitulo(EscritorTexto[Subtitulo]):
    def _estilo(self, bloco: Subtitulo) -> ParagraphStyle:
        return self._tema.estilos[f"subtitulo_{bloco.nivel}"]


class EscritorParagrafo(EscritorTexto[Paragrafo]):
    def _estilo(self, bloco: Paragrafo) -> ParagraphStyle:
        return self._tema.estilos["paragrafo_recuado" if bloco.recuado else "paragrafo"]


class EscritorLista:
    def __init__(self, tema: Tema) -> None:
        self._tema = tema

    def __call__(self, bloco: Lista) -> Flowable:
        return self.pipeline(bloco)

    def pipeline(self, bloco: Lista) -> Flowable:
        # `bulletType="1"` numera pela POSIÇÃO na lista: o número não é dado do bloco, e duas
        # listas seguidas recomeçam do 1 sem ninguém zerar contador.
        return ListFlowable(
            [ListItem(self._item(texto)) for texto in bloco.itens],
            bulletType="1" if bloco.ordenada else "bullet",
            bulletFontName=self._tema.estilos["item"].fontName,
            leftIndent=24,
        )

    def _item(self, texto: str) -> Flowable:
        return Paragraph(_texto(texto), self._tema.estilos["item"])


class EscritorTabela:
    """O bloco diz o que a tabela contém; o estilo é do tema, e a medida é do motor da SPEC 002."""

    def __init__(self, tema: Tema) -> None:
        self._tema = tema

    def __call__(self, bloco: Tabela) -> Flowable:
        return self.pipeline(bloco)

    def pipeline(self, bloco: Tabela) -> Flowable:
        return tabela_pdf(self._pedido(bloco))

    def _pedido(self, bloco: Tabela) -> TabelaInput:
        # Texto CRU, sem `_texto`: o `TabelaPdf` escapa cada célula ao montar o `Paragraph`.
        # Escapar aqui também sairia `&amp;` no papel.
        return TabelaInput(
            colunas=bloco.colunas,
            cabecalho=bloco.cabecalho,
            linhas=bloco.linhas,
            estilo=self._tema.estilo_tabela,
        )


class EscritorImagem:
    """SVG, não raster: o vetor é o que o motor carrega (SPEC 001), e é o que mantém o arquivo leve
    quando a mesma imagem se repete."""

    def __init__(self, tema: Tema) -> None:
        self._tema = tema

    def __call__(self, bloco: Imagem) -> Flowable:
        return self.pipeline(bloco)

    def pipeline(self, bloco: Imagem) -> Flowable:
        # `Drawing` já É um `Flowable`: o vetor entra no fluxo do corpo sem embrulho nenhum.
        desenho = carregar_vetor(bloco.caminho, bloco.largura_mm)
        desenho.hAlign = "CENTER"
        return desenho


def montar_escritores(tema: Tema) -> dict[str, Callable[[Any], Flowable]]:
    # O registro é a única lista de tipos do módulo: bloco novo entra aqui e em lugar nenhum mais.
    return {
        "titulo": EscritorTitulo(tema),
        "subtitulo": EscritorSubtitulo(tema),
        "paragrafo": EscritorParagrafo(tema),
        "lista": EscritorLista(tema),
        "tabela": EscritorTabela(tema),
        "imagem": EscritorImagem(tema),
    }
