from functools import cached_property
from typing import Literal, Self

from pydantic import BaseModel, computed_field

from services.domain.logradouro import Logradouro
from services.utils.fuzzy_matcher import FuzzyMatchResult


class LogradouroMatchQuery(BaseModel):
    texto: str
    limite: int = 5


class LogradouroRow(BaseModel):
    codlog: str
    dv: str
    tipo_logradouro: str
    titulo: str | None = None
    titulo_por_extenso: str | None = None
    preposicao: str | None = None
    nm_logradouro: str

    @property
    def logradouro(self) -> Logradouro:
        return Logradouro(
            codlog=f"{self.codlog}{self.dv}",
            tipo_logradouro=self.tipo_logradouro,
            titulo=self.titulo,
            preposicao=self.preposicao,
            nome_logradouro=self.nm_logradouro,
        )

    # Memoizado: o literal percorre o catálogo inteiro a cada tecla.
    @cached_property
    def textos_de_busca(self) -> tuple[str, ...]:
        logradouro = self.logradouro
        por_extenso = logradouro.model_copy(update={"titulo": self.titulo_por_extenso or self.titulo})
        return tuple(
            dict.fromkeys((self.nm_logradouro, logradouro.denominacao, por_extenso.denominacao))
        )


class LogradouroMatchOutput(BaseModel):
    codlog: str
    dv: str
    tipo_codigo: str
    titulo: str | None = None
    preposicao: str | None = None
    nome_logradouro: str

    @property
    def logradouro(self) -> Logradouro:
        return Logradouro(
            codlog=f"{self.codlog}{self.dv}",
            tipo_logradouro=self.tipo_codigo,
            titulo=self.titulo,
            preposicao=self.preposicao,
            nome_logradouro=self.nome_logradouro,
        )

    @classmethod
    def da_linha(cls, row: LogradouroRow) -> Self:
        return cls(
            codlog=row.codlog,
            dv=row.dv,
            tipo_codigo=row.tipo_logradouro,
            titulo=row.titulo,
            preposicao=row.preposicao,
            nome_logradouro=row.nm_logradouro,
        )


class LogradouroMatchResult(BaseModel):
    match_tipo: FuzzyMatchResult | None
    match_nome: FuzzyMatchResult
    logradouros: list[LogradouroMatchOutput]
    ignorou_filtro_tipo: bool

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resultado_multiplo(self) -> bool:
        return len(self.logradouros) > 1

    @computed_field  # type: ignore[prop-decorator]
    @property
    def codlogs(self) -> list[str]:
        return [m.codlog for m in self.logradouros]

    @property
    def nome_logradouro(self) -> str | None:
        item = self.match_nome.best_match
        return item.original_string if item else None


class LiteralLogradouroQuery(BaseModel):
    nome: str
    tipo: str | None = None
    limite: int = 5


class LiteralLogradouroResult(BaseModel):
    logradouros: list[LogradouroMatchOutput]
    ignorou_filtro_tipo: bool


class ResolucaoLogradouroQuery(BaseModel):
    nome: str
    tipo: str | None = None
    limite: int = 5
    modo: Literal["sugestao", "commit"] = "commit"


class ResolucaoLogradouroItem(BaseModel):
    logradouro: LogradouroMatchOutput
    score: float | None = None  # None = veio do literal; preenchido = grau de certeza fuzzy


class ResolucaoLogradouroResult(BaseModel):
    itens: list[ResolucaoLogradouroItem]
    usou_fuzzy: bool
    ignorou_filtro_tipo: bool = False
