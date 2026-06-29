from typing import Protocol

from .codlog import CodlogIdentifier
from .contribuinte import ContribuinteIdentifier
from .endereco import EnderecoIdentifier
from .endereco_codlog import CodlogNumeroIdentifier
from .logradouro import LogradouroIdentifier
from .models import Candidato, RoteamentoQuery, RoteamentoResult, TipoEntrada

PRIORIDADE_TIPOS: tuple[TipoEntrada, ...] = (
    TipoEntrada.CONTRIBUINTE,
    TipoEntrada.ENDERECO_CODLOG,
    TipoEntrada.ENDERECO,
    TipoEntrada.CODLOG,
    TipoEntrada.LOGRADOURO,
)


class Identifier(Protocol):
    def __call__(self, texto: str, finished_typing: bool) -> Candidato | None: ...


class EntradaRouter:
    def __init__(self, identifiers: tuple[Identifier, ...] | None = None) -> None:
        self._identifiers: tuple[Identifier, ...] = identifiers or (
            ContribuinteIdentifier(),
            CodlogNumeroIdentifier(),
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
        candidatos.sort(key=lambda c: PRIORIDADE_TIPOS.index(c.tipo))
        return RoteamentoResult(texto=query.texto, candidatos=candidatos)


rotear_entrada = EntradaRouter()
