from collections.abc import Callable
from html import escape
from typing import Any

from .models import (
    Botao,
    Destaque,
    Divisor,
    Imagem,
    Paragrafo,
    Subtitulo,
    Tabela,
    Titulo,
)
from .tema import TEMA_EMAIL


def _texto(bruto: str) -> str:
    # HTML escrito na mão fica fora do autoescape do Django: o escape passa a ser daqui,
    # para todo valor interpolado.
    return escape(bruto)


class EscritorTitulo:
    def __call__(self, bloco: Titulo) -> str:
        return f'<h1 style="{TEMA_EMAIL["titulo"]}">{_texto(bloco.texto)}</h1>'


class EscritorSubtitulo:
    def __call__(self, bloco: Subtitulo) -> str:
        return f'<h2 style="{TEMA_EMAIL["subtitulo"]}">{_texto(bloco.texto)}</h2>'


class EscritorParagrafo:
    def __call__(self, bloco: Paragrafo) -> str:
        return f'<p style="{TEMA_EMAIL["paragrafo"]}">{_texto(bloco.texto)}</p>'


class EscritorDestaque:
    def __call__(self, bloco: Destaque) -> str:
        estilo = TEMA_EMAIL["valor_mono"] if bloco.monoespacado else TEMA_EMAIL["valor"]
        return (
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
            f'<tr><td style="{TEMA_EMAIL["poco"]}">'
            f'<span style="{TEMA_EMAIL["overline"]}">{_texto(bloco.rotulo)}</span><br>'
            f'<span style="{estilo}">{_texto(bloco.valor)}</span>'
            "</td></tr></table>"
        )


class EscritorTabela:
    def __call__(self, bloco: Tabela) -> str:
        return self.pipeline(bloco)

    def pipeline(self, bloco: Tabela) -> str:
        partes = ['<table role="presentation" width="100%" cellpadding="0" cellspacing="0">']
        if bloco.cabecalho:
            partes.append(self._linha(bloco.cabecalho, TEMA_EMAIL["celula_cabecalho"]))
        partes.extend(self._linha(linha, TEMA_EMAIL["celula"]) for linha in bloco.linhas)
        partes.append("</table>")
        return "".join(partes)

    def _linha(self, celulas: tuple[str, ...], estilo: str) -> str:
        return "<tr>" + "".join(f'<td style="{estilo}">{_texto(c)}</td>' for c in celulas) + "</tr>"


class EscritorImagem:
    def __call__(self, bloco: Imagem) -> str:
        # width como ATRIBUTO, não CSS: é o que o Outlook obedece.
        largura = f' width="{bloco.largura}"' if bloco.largura is not None else ""
        return (
            f'<img src="{bloco.url}" alt="{_texto(bloco.alternativo)}"{largura} '
            f'style="{TEMA_EMAIL["imagem"]}">'
        )


class EscritorBotao:
    def __call__(self, bloco: Botao) -> str:
        return f'<a href="{bloco.url}" style="{TEMA_EMAIL["botao"]}">{_texto(bloco.rotulo)}</a>'


class EscritorDivisor:
    def __call__(self, bloco: Divisor) -> str:
        return f'<hr style="{TEMA_EMAIL["divisor"]}">'


# O registro é a única lista de tipos do módulo: bloco novo entra aqui e em lugar nenhum mais.
ESCRITORES: dict[str, Callable[[Any], str]] = {
    "titulo": EscritorTitulo(),
    "subtitulo": EscritorSubtitulo(),
    "paragrafo": EscritorParagrafo(),
    "destaque": EscritorDestaque(),
    "tabela": EscritorTabela(),
    "imagem": EscritorImagem(),
    "botao": EscritorBotao(),
    "divisor": EscritorDivisor(),
}
