from pydantic import BaseModel, computed_field

from services.utils.fuzzy_matcher import FuzzyMatchResult


class LogradouroMatchQuery(BaseModel):
    texto: str
    limite: int = 5


class LogradouroRow(BaseModel):
    codlog: str
    cd_tipo_logradouro: str
    nm_logradouro: str


class LogradouroMatchOutput(BaseModel):
    codlog: str
    tipo_codigo: str
    nome_logradouro: str


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
