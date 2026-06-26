from typing import Protocol

from .codlog import CodlogIdentifier
from .contribuinte import ContribuinteIdentifier
from .endereco import EnderecoIdentifier
from .logradouro import LogradouroIdentifier
from .models import Candidato, RoteamentoQuery, RoteamentoResult


class Identifier(Protocol):
    def __call__(self, texto: str, finished_typing: bool) -> Candidato | None: ...


class EntradaRouter:
    def __init__(self, identifiers: tuple[Identifier, ...] | None = None) -> None:
        self._identifiers: tuple[Identifier, ...] = identifiers or (
            ContribuinteIdentifier(),
            CodlogIdentifier(),
            LogradouroIdentifier(),
            EnderecoIdentifier(),
        )

    def __call__(self, query: RoteamentoQuery) -> RoteamentoResult:
        bruto = query.texto.strip()
        candidatos = [
            c
            for ident in self._identifiers
            if (c := ident(bruto, query.finished_typing)) is not None
        ]
        return RoteamentoResult(texto=query.texto, candidatos=candidatos)


rotear_entrada = EntradaRouter()
