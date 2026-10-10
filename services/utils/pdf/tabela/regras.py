from abc import ABC, abstractmethod

from reportlab.lib.colors import Color
from reportlab.lib.units import mm

from ..models import ComandoTabela, Grade


class RegraTabela(ABC):
    """Um traço visual da tabela: recebe a grade e devolve os comandos dele."""

    @abstractmethod
    def __call__(self, grade: Grade) -> tuple[ComandoTabela, ...]: ...


class FundoDoCabecalho(RegraTabela):
    def __init__(self, cor: Color) -> None:
        self._cor = cor

    def __call__(self, grade: Grade) -> tuple[ComandoTabela, ...]:
        # Tabela sem cabeçalho existe (par rótulo/valor), e pintar a linha 0 nela apagaria um dado.
        if grade.linhas_cabecalho == 0:
            return ()
        return (("BACKGROUND", (0, 0), (-1, grade.linhas_cabecalho - 1), self._cor),)


class ZebraDoCorpo(RegraTabela):
    """Alternância só no corpo: o cabeçalho tem o fundo dele e ficaria fora de fase se entrasse."""

    def __init__(self, cor: Color, cor_alternada: Color) -> None:
        self._cores = [cor, cor_alternada]

    def __call__(self, grade: Grade) -> tuple[ComandoTabela, ...]:
        return (("ROWBACKGROUNDS", (0, grade.linhas_cabecalho), (-1, -1), self._cores),)


class GradeDeLinhas(RegraTabela):
    def __init__(self, cor: Color, espessura_pt: float) -> None:
        self._cor = cor
        self._espessura_pt = espessura_pt

    def __call__(self, grade: Grade) -> tuple[ComandoTabela, ...]:
        return (("GRID", (0, 0), (-1, -1), self._espessura_pt, self._cor),)


class Respiro(RegraTabela):
    """O ar dentro da célula — em milímetros, como todo o resto do módulo."""

    def __init__(self, horizontal_mm: float, vertical_mm: float) -> None:
        self._horizontal_mm = horizontal_mm
        self._vertical_mm = vertical_mm

    def __call__(self, grade: Grade) -> tuple[ComandoTabela, ...]:
        return (
            ("LEFTPADDING", (0, 0), (-1, -1), self._horizontal_mm * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), self._horizontal_mm * mm),
            ("TOPPADDING", (0, 0), (-1, -1), self._vertical_mm * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), self._vertical_mm * mm),
        )
