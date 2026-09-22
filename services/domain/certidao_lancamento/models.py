from typing import Any, Self
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from services.domain.documento_selado import EnvelopeAto
from services.domain.lote_geocod.models import LoteAttributes
from services.domain.planta_localizacao.models import PlantaLocalizacao

PADRAO_PROCESSO_SEI = r"^\d{4}\.\d{4}/\d{7}-\d$"


class PedidoCertidao(BaseModel):
    """O que o modal colhe: quem pede e em qual processo. É o que instrui a certidão junto com o lote."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    processo: str = Field(pattern=PADRAO_PROCESSO_SEI)
    interessado: str = Field(min_length=3, max_length=200)


class CertidaoLancamentoInput(BaseModel):
    """Tudo já apurado: o domínio do documento não vai ao WFS nem ao banco."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    envelope: EnvelopeAto
    pedido: PedidoCertidao
    imovel: LoteAttributes
    planta: PlantaLocalizacao | Any
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
