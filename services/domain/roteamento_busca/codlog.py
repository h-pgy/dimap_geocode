import re
from typing import Protocol

from .models import CodlogParse

DASH_CODLOG = re.compile(r"\d{1,5}-\d")
COMP_CODLOG = 6


class RegraCodlog(Protocol):
    def __call__(self, parse: CodlogParse) -> bool: ...


# ponto de extensão — vazio por ora.
REGRAS_CODLOG: tuple[RegraCodlog, ...] = ()


class CodlogIdentifier:
    def __init__(self, regras: tuple[RegraCodlog, ...] = REGRAS_CODLOG) -> None:
        self._regras = regras

    def __call__(self, texto: str, finished_typing: bool) -> CodlogParse | None:
        # finished_typing não afeta códigos — completude é por nº de dígitos
        bruto = texto.strip()
        if "." in bruto:
            return None
        if "-" in bruto and not DASH_CODLOG.fullmatch(bruto):
            return None
        digitos = bruto.replace("-", "").replace(" ", "")
        if not digitos or not digitos.isdigit() or len(digitos) > COMP_CODLOG:
            return None
        parse = CodlogParse(codlog=digitos[0:5], digito_verificador=digitos[5:6])
        if not all(regra(parse) for regra in self._regras):
            return None
        return parse
