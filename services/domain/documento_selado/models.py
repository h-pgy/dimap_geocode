from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from .constants import VERSAO_ENVELOPE


class AutorDoAto(BaseModel):
    """Quem praticou, com a lotação e os cargos do dia. Texto, não referência: o envelope precisa
    dizer o mesmo daqui a dez anos, com a pessoa já aposentada e a unidade já extinta."""

    model_config = ConfigDict(frozen=True)

    nome: str
    # Não vai impressa em quadro nenhum: ela identifica a lotação no envelope e no timbre da folha.
    unidade: str
    cargo_base: str
    cargo_comissao: str | None = None
    # Preenchido só quando o ato foi praticado em substituição: descrever o ato pelo cargo de quem
    # assinou, sem dizer por quem ele respondia, atribui a competência à pessoa errada.
    substituindo: str | None = None


class AlvoDoAto(BaseModel):
    """Sobre o quê. Texto nos dois campos, como em `ExecucaoAcao`: o alvo é lote, logradouro,
    servidor ou unidade conforme a ação, e tipá-lo por entidade amarraria o envelope ao catálogo de
    entidades territoriais."""

    model_config = ConfigDict(frozen=True)

    tipo: str
    identificador: str


class EnvelopeAto(BaseModel):
    """O núcleo é obrigatório — é ele que faz o envelope descrever um ato, e não um arquivo qualquer.
    `extras` é o que cada ação acrescenta."""

    model_config = ConfigDict(frozen=True)

    versao: int = VERSAO_ENVELOPE
    codigo: str
    # O slug do contrato da ação (`<app>.<nome>`), que é o identificador estável dela.
    acao: str
    operacao: str = ""
    autor: AutorDoAto
    alvo: AlvoDoAto
    # Com fuso: "10:32" sem dizer de onde não descreve instante nenhum.
    emitido_em: AwareDatetime
    campos_publicos: tuple[str, ...] = ()
    extras: dict[str, Any] = Field(default_factory=dict)


class SeloImpresso(BaseModel):
    """O que vai IMPRESSO nos dois quadros, já redigido. Derivado do envelope, e não digitado ao
    lado dele: é o que impede o papel de dizer uma coisa e o arquivo, outra."""

    model_config = ConfigDict(frozen=True)

    chamada: str
    # O que o QR diz, inteiro.
    url_conferencia: str
    # O mesmo endereço sem o esquema: é o que se lê no papel e o que alguém digita.
    link_impresso: str
    assinante: str
    # Já resolvido: o de comissão quando existe, o base quando não.
    cargo: str
    substituindo: str | None = None
    # "8 de setembro de 2026, às 14h32min" — a data como ela sai impressa.
    data_por_extenso: str


class SeloImpressoInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    # O ato inteiro, não os campos dele soltos.
    envelope: EnvelopeAto
    # E só então o que é do processo: o endereço do ambiente, que o domínio não conhece.
    base_url: str
