from enum import StrEnum
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from services.utils.assinatura import ResultadoConferencia

from .constants import TAMANHO_MAXIMO_BYTES, TAMANHO_MAXIMO_MB, VERSAO_ENVELOPE


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


class EstadoDocumento(StrEnum):
    """O que o arquivo E o acervo, juntos, conseguem afirmar. `EstadoSelo` (SPEC 006) é o que o
    arquivo diz sozinho; estes quatro são o que a tela mostra."""

    CONFERE = "confere"
    NAO_CONFERE = "nao_confere"
    SEM_SELO = "sem_selo"
    # Selo íntegro de código que o acervo não conhece. Não é documento adulterado: ou o segredo
    # vazou, ou o documento saiu de uma base que não é esta.
    DESCONHECIDO = "desconhecido"


class RegistroDocumento(BaseModel):
    """A linha do acervo como o domínio a enxerga — sem `Model`, sem `QuerySet`. Quem a monta é a
    view, que é quem pode tocar no banco."""

    model_config = ConfigDict(frozen=True)

    codigo: str
    emitido_em: AwareDatetime
    # O envelope guardado, achatado como a selagem o escreveu: na página do código não há arquivo
    # para conferir, e é daqui que sai a ficha.
    envelope: dict[str, Any]


class FichaDoAto(BaseModel):
    """O que a tela afirma sobre o ato quando ele confere. Envelopa o `AutorDoAto` da SPEC 007 em vez
    de recopiar nome, cargo e unidade."""

    model_config = ConfigDict(frozen=True)

    codigo: str
    autor: AutorDoAto
    assinado_em: AwareDatetime
    # Os nomes que a ação declarou públicos, já resolvidos em valores.
    publicos: dict[str, Any]


class ConferenciaInput(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    # O que o arquivo afirmou sozinho, inteiro — não os campos dele soltos.
    resultado_selo: ResultadoConferencia
    # E só então o que é do processo: `None` quando o código não está no acervo.
    registro: RegistroDocumento | None = None


class ConferenciaOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    estado: EstadoDocumento
    # O que o arquivo diz chamar-se, mesmo quando não confere: é por ele que se acha o original.
    codigo: str | None = None
    # Preenchida só no estado CONFERE: fora dele, dizer quem assinou é repetir o que o arquivo alega.
    ficha: FichaDoAto | None = None
    # Se existe original guardado para oferecer a quem estiver logado.
    tem_original: bool = False


class TamanhoDoUpload(BaseModel):
    """A porta do upload em rota aberta. Só o tamanho: ele vem do cabeçalho do multipart, e é o que
    permite recusar o arquivo antes de os bytes irem para a memória."""

    model_config = ConfigDict(frozen=True)

    tamanho: int

    @field_validator("tamanho")
    @classmethod
    def cabe_no_limite(cls, valor: int) -> int:
        if valor <= 0:
            raise ValueError("Escolha o arquivo PDF a conferir.")
        if valor > TAMANHO_MAXIMO_BYTES:
            raise ValueError(f"O arquivo passa de {TAMANHO_MAXIMO_MB} MB.")
        return valor
