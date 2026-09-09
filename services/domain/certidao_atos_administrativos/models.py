from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from services.domain.documento_selado import EnvelopeAto
from services.domain.listagem_gestao import LinhaExecucao

JANELA_MAXIMA_DIAS = 365


class BuscaAtosProprios(BaseModel):
    """O recorte da certidão. Mesma propriedade de segurança do `BuscaExecucoes`: o primeiro campo é
    o delimitador do universo, sem default — esquecê-lo é erro de tipo, nunca certidão alheia."""

    model_config = ConfigDict(frozen=True)

    perfil_id: int
    inicio: date
    fim: date
    # Os slugs escolhidos no modal. Vazio quer dizer todos — critério em branco não estreita nada,
    # como no `BuscaExecucoes`.
    acoes: frozenset[str] = frozenset()

    @model_validator(mode="after")
    def periodo_coerente(self) -> Self:
        if self.fim < self.inicio:
            raise ValueError("A data final do período não pode ser anterior à inicial.")
        if (self.fim - self.inicio).days > JANELA_MAXIMA_DIAS:
            raise ValueError(f"O período da certidão não pode passar de {JANELA_MAXIMA_DIAS} dias.")
        return self


class RecorteDeclarado(BaseModel):
    """Os critérios, já redigidos para sair impressos. A certidão que não declara o que recortou faz
    o leitor confundir "não praticou" com "não foi pedido"."""

    model_config = ConfigDict(frozen=True)

    inicio: date
    fim: date
    # Os NOMES das ações escolhidas, não os slugs: o slug é chave de código, não texto de papel.
    tipos: tuple[str, ...] = ()


class CertidaoAtosInput(BaseModel):
    """Recebe as linhas já lidas: o domínio do documento não vai ao banco, e é isso que o torna
    testável sem Django."""

    model_config = ConfigDict(frozen=True)

    # O ato inteiro, não os campos dele soltos: é ele que carrega autor, código e instante.
    envelope: EnvelopeAto
    recorte: RecorteDeclarado
    # A linha do rastro como o sistema já a materializa — a mesma que a tela do registro mostra.
    atos: tuple[LinhaExecucao, ...] = ()
    # O que é do processo: o endereço do ambiente, que o domínio não conhece.
    base_url: str
