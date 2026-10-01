from enum import StrEnum
from typing import Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from services.domain.documento_selado import EnvelopeAto
from services.domain.lote_geocod.models import LoteAttributes
from services.domain.planta_localizacao.models import PlantaLocalizacao

PADRAO_PROCESSO_SEI = r"^\d{4}\.\d{4}/\d{7}-\d$"
PADRAO_CPF_CNPJ = r"^(\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})$"


class SentidoDespacho(StrEnum):
    """Se o pedido foi atendido. É o que a ficha pública do documento declara."""

    DEFERIDO = "deferido"
    INDEFERIDO = "indeferido"

    @property
    def rotulo(self) -> str:
        match self:
            case SentidoDespacho.DEFERIDO:
                return "Deferido"
            case SentidoDespacho.INDEFERIDO:
                return "Indeferido"


class TipoDespacho(StrEnum):
    """Os despachos do modelo da DIMAP. Vários tipos têm o mesmo sentido: o tipo diz o texto, o
    sentido diz se a solicitação foi atendida."""

    POSSUI_LANCAMENTO = "possui_lancamento"
    LANCAMENTO_EM_MAIOR_AREA = "lancamento_em_maior_area"
    LANCAMENTO_PARCIAL = "lancamento_parcial"
    IMOVEL_NAO_LOCALIZADO = "imovel_nao_localizado"
    PEDIDO_DE_ACESSO_A_INFORMACAO = "pedido_de_acesso_a_informacao"

    # `match` exaustivo: tipo novo sem `case` é erro do mypy antes de qualquer teste rodar.
    @property
    def sentido(self) -> SentidoDespacho:
        match self:
            case (
                TipoDespacho.POSSUI_LANCAMENTO
                | TipoDespacho.LANCAMENTO_EM_MAIOR_AREA
                | TipoDespacho.LANCAMENTO_PARCIAL
            ):
                return SentidoDespacho.DEFERIDO
            case TipoDespacho.IMOVEL_NAO_LOCALIZADO | TipoDespacho.PEDIDO_DE_ACESSO_A_INFORMACAO:
                return SentidoDespacho.INDEFERIDO

    @property
    def descricao(self) -> str:
        match self:
            case TipoDespacho.POSSUI_LANCAMENTO:
                return "possui lançamento"
            case TipoDespacho.LANCAMENTO_EM_MAIOR_AREA:
                return "lançamento em maior área"
            case TipoDespacho.LANCAMENTO_PARCIAL:
                return "lançamento parcial"
            case TipoDespacho.IMOVEL_NAO_LOCALIZADO:
                return "imóvel não localizado"
            case TipoDespacho.PEDIDO_DE_ACESSO_A_INFORMACAO:
                return "equivale a pedido de acesso à informação"

    @property
    def rotulo(self) -> str:
        return f"{self.sentido.rotulo} · {self.descricao}"


class PedidoCertidao(BaseModel):
    """O que o modal colhe: quem pede, em qual processo e o despacho do auditor."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    processo: str = Field(pattern=PADRAO_PROCESSO_SEI)
    interessado: str = Field(min_length=3, max_length=200)
    cpf_cnpj: str | None = Field(default=None, pattern=PADRAO_CPF_CNPJ)
    sentido: SentidoDespacho
    tipo_despacho: TipoDespacho
    incluir_ressalva: bool = False
    incluir_planta: bool = False
    observacoes: str = Field(default="", max_length=2000)

    @field_validator("cpf_cnpj", mode="before")
    @classmethod
    def _vazio_eh_ausente(cls, valor: object) -> object:
        return None if valor == "" else valor

    @model_validator(mode="after")
    def _texto_eh_do_sentido(self) -> Self:
        # A chave e o texto chegam separados: trocar a chave deixa marcado o texto do outro sentido.
        if self.tipo_despacho.sentido is not self.sentido:
            raise ValueError(f"Escolha um dos textos de despacho {self.sentido.rotulo.lower()}.")
        return self


class CertidaoLancamentoInput(BaseModel):
    """Tudo já apurado: o domínio do documento não vai ao WFS nem ao banco."""

    model_config = ConfigDict(frozen=True)

    envelope: EnvelopeAto
    pedido: PedidoCertidao
    imovel: LoteAttributes
    planta: PlantaLocalizacao | None
    # O instante da leitura do lote no GeoSampa: é ele, e não o da assinatura, que o rodapé declara.
    consultado_em: AwareDatetime
    base_url: str

    @model_validator(mode="after")
    def _imovel_certificavel(self) -> Self:
        if self.imovel.is_condominio:
            raise ValueError("Lote condominial: a certidão ainda não é emitida pelo sistema.")
        if not self.imovel.possui_lancamento:
            raise ValueError("O lote não possui lançamento ativo no cadastro.")
        return self

    @model_validator(mode="after")
    def _planta_segue_o_pedido(self) -> Self:
        # O sentido só sugere o mapa: quem decide é o auditor, pelo pedido.
        if self.pedido.incluir_planta and self.planta is None:
            raise ValueError("O pedido inclui o mapa, e a planta de localização não veio.")
        if not self.pedido.incluir_planta and self.planta is not None:
            raise ValueError("O pedido não inclui o mapa.")
        return self
