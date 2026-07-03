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
        if self._parece_codlog(bruto):
            return None
        digitos = self._extrair_digitos(bruto)
        if digitos is None:
            return None
        parse = self._montar_parse(digitos)
        if not self._validar_regras(parse):
            return None
        return parse

    def _parece_codlog(self, bruto: str) -> bool:
        """Guarda: '12345-1' (codlog com DV) não deve ser tratado como contribuinte."""
        return "." not in bruto and DASH_CODLOG.fullmatch(bruto) is not None

    def _extrair_digitos(self, bruto: str) -> str | None:
        """Remove separadores e valida que o resultado é numérico com tamanho válido."""
        digitos = SEPARADORES.sub("", bruto)
        if not digitos or not digitos.isdigit() or len(digitos) > COMP_COM_DV:
            return None
        return digitos

    def _montar_parse(self, digitos: str) -> ContribuinteParse:
        return ContribuinteParse(
            setor=digitos[0:3],
            quadra=digitos[3:6],
            lote=digitos[6:10],
            dv=digitos[10:12],
        )

    def _validar_regras(self, parse: ContribuinteParse) -> bool:
        return all(regra(parse) for regra in self._regras)
