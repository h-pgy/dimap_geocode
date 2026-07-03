from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, computed_field, model_validator

from services.utils.normalization import chave_numero_porta


class TipoEntrada(StrEnum):
    CONTRIBUINTE = "contribuinte"
    CODLOG = "codlog"
    LOGRADOURO = "logradouro"
    ENDERECO = "endereco"
    ENDERECO_CODLOG = "endereco_codlog"
    ENDERECO_LOTE = "endereco_lote"


class RoteamentoStatus(StrEnum):
    UNICO = "unico"
    AMBIGUO = "ambiguo"
    IMPOSSIVEL = "impossivel"
    VAZIO = "vazio"


class ContribuinteParse(BaseModel):
    tipo: Literal[TipoEntrada.CONTRIBUINTE] = TipoEntrada.CONTRIBUINTE
    setor: str
    quadra: str
    lote: str
    dv: str
    cd_condominio: str | None = None
    is_condominio: bool | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def setor_completo(self) -> bool:
        return len(self.setor) == 3

    @computed_field  # type: ignore[prop-decorator]
    @property
    def quadra_completo(self) -> bool:
        return len(self.quadra) == 3

    @computed_field  # type: ignore[prop-decorator]
    @property
    def lote_completo(self) -> bool:
        return len(self.lote) == 4

    @computed_field  # type: ignore[prop-decorator]
    @property
    def dv_completo(self) -> bool:
        return len(self.dv) == 2

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completo(self) -> bool:
        return self.setor_completo and self.quadra_completo and self.lote_completo

    @property
    def digitos(self) -> str:
        return f"{self.setor}{self.quadra}{self.lote}{self.dv}"

    @property
    def mascara(self) -> str:
        base = ".".join(p for p in (self.setor, self.quadra, self.lote) if p)
        return f"{base}-{self.dv}" if self.dv else base

    def calcular_dv(self) -> str:
        raise NotImplementedError("DV do contribuinte: algoritmo a definir.")


class CodlogParse(BaseModel):
    tipo: Literal[TipoEntrada.CODLOG] = TipoEntrada.CODLOG
    codlog: str
    digito_verificador: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def codlog_completo(self) -> bool:
        return len(self.codlog) == 5

    @computed_field  # type: ignore[prop-decorator]
    @property
    def dv_completo(self) -> bool:
        return len(self.digito_verificador) == 1

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completo(self) -> bool:
        return self.codlog_completo

    @property
    def mascara(self) -> str:
        return f"{self.codlog}-{self.digito_verificador}" if self.digito_verificador else self.codlog

    def calcular_dv(self) -> str:
        raise NotImplementedError("DV do codlog: algoritmo a definir.")


class LogradouroParse(BaseModel):
    tipo: Literal[TipoEntrada.LOGRADOURO] = TipoEntrada.LOGRADOURO
    tipo_logradouro: str
    nome: str
    entrada_finalizada: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tipo_completo(self) -> bool:
        return bool(self.tipo_logradouro)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def nome_completo(self) -> bool:
        return bool(self.nome)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completo(self) -> bool:
        return self.nome_completo and (self.tipo_completo or self.entrada_finalizada)


class EnderecoParse(BaseModel):
    tipo: Literal[TipoEntrada.ENDERECO] = TipoEntrada.ENDERECO
    logradouro: LogradouroParse
    numero: int
    numero_bruto: str  # token do número como digitado — auditabilidade, sem uso no match

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completo(self) -> bool:
        return self.logradouro.completo and self.numero > 0


class EnderecoCodlogParse(BaseModel):
    tipo: Literal[TipoEntrada.ENDERECO_CODLOG] = TipoEntrada.ENDERECO_CODLOG
    codlog: CodlogParse
    numero: int
    numero_bruto: str  # token do número como digitado — auditabilidade, sem uso no match

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completo(self) -> bool:
        return self.codlog.completo and self.numero > 0


class EnderecoLoteParse(BaseModel):
    tipo: Literal[TipoEntrada.ENDERECO_LOTE] = TipoEntrada.ENDERECO_LOTE
    logradouro: LogradouroParse | None = None
    codlog: CodlogParse | None = None
    numero_bruto: str  # a entrada original do usuário, como digitada ("s/n", "10-A", "100")

    @model_validator(mode="after")
    def _exatamente_uma_forma(self) -> "EnderecoLoteParse":
        if (self.logradouro is None) == (self.codlog is None):
            raise ValueError("Informe logradouro OU codlog (exatamente um).")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def numero_padronizado(self) -> str:
        """numero_bruto após normalize_text + match de "sem número" (a chave de porta).

        Derivado do bruto (não é um segundo campo de entrada). O matcher fiscal consome
        ISTO direto; a coluna do catalog usa a MESMA chave_numero_porta (single-source, §7.1).
        Ex.: "s/n" -> "SN"; "10-A" -> "10A"; "100" -> "100".
        """
        return chave_numero_porta(self.numero_bruto)


Candidato = Annotated[
    ContribuinteParse
    | CodlogParse
    | LogradouroParse
    | EnderecoParse
    | EnderecoCodlogParse
    | EnderecoLoteParse,
    Field(discriminator="tipo"),
]


class RoteamentoQuery(BaseModel):
    texto: str
    finished_typing: bool = False


class RoteamentoResult(BaseModel):
    texto: str
    candidatos: list[Candidato]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def status(self) -> RoteamentoStatus:
        if not self.candidatos:
            return RoteamentoStatus.VAZIO if not self.texto.strip() else RoteamentoStatus.IMPOSSIVEL
        return RoteamentoStatus.UNICO if len(self.candidatos) == 1 else RoteamentoStatus.AMBIGUO

    @property
    def match(self) -> Candidato | None:
        return self.candidatos[0] if len(self.candidatos) == 1 else None

    @property
    def tipos(self) -> list[TipoEntrada]:
        return [c.tipo for c in self.candidatos]
