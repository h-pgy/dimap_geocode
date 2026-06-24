import re
from typing import Protocol

from .models import ContribuinteParse

SEPARADORES = re.compile(r"[.\-\s]")
DASH_CODLOG = re.compile(r"\d{1,5}-\d")
COMP_LOTE = 10
COMP_COM_DV = 12


class RegraContribuinte(Protocol):
    def __call__(self, parse: ContribuinteParse) -> bool: ...


# ponto de extensão — vazio por ora.
# Ex. futuro: lambda p: not p.setor or int(p.setor[0]) <= 4
REGRAS_CONTRIBUINTE: tuple[RegraContribuinte, ...] = ()


class ContribuinteIdentifier:
    def __init__(self, regras: tuple[RegraContribuinte, ...] = REGRAS_CONTRIBUINTE) -> None:
        self._regras = regras

    def __call__(self, texto: str, finished_typing: bool) -> ContribuinteParse | None:
        # finished_typing não afeta códigos — completude é por nº de dígitos
        bruto = texto.strip()
        if "." not in bruto and DASH_CODLOG.fullmatch(bruto):
            return None
        digitos = SEPARADORES.sub("", bruto)
        if not digitos or not digitos.isdigit() or len(digitos) > COMP_COM_DV:
            return None
        parse = ContribuinteParse(
            setor=digitos[0:3],
            quadra=digitos[3:6],
            lote=digitos[6:10],
            dv=digitos[10:12],
        )
        if not all(regra(parse) for regra in self._regras):
            return None
        return parse
