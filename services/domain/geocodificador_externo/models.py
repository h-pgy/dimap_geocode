from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from services.domain.geometry import GeoFeature, PointGeometry
from services.utils.normalization import normalize_text

# o índice único da chave tem teto de tamanho no banco: o tipo recusa antes
TAMANHO_MAX_CONSULTA = 500


class Provedor(StrEnum):
    GOOGLE = "google"

    @property
    def rotulo(self) -> str:
        match self:
            case Provedor.GOOGLE:
                return "Google"


class Precisao(StrEnum):
    # a ordem de declaração é o nível: do menos ao mais preciso
    APROXIMADA = "aproximada"
    LOGRADOURO = "logradouro"
    INTERPOLADA = "interpolada"
    IMOVEL = "imovel"

    @property
    def nivel(self) -> int:
        return list(Precisao).index(self)

    @property
    def rotulo(self) -> str:
        match self:
            case Precisao.APROXIMADA:
                return "Aproximada"
            case Precisao.LOGRADOURO:
                return "Centro da via"
            case Precisao.INTERPOLADA:
                return "Interpolada na via"
            case Precisao.IMOVEL:
                return "No imóvel"


class EnderecoExternoAttributes(BaseModel):
    """O endereço como um provedor externo o encontrou."""

    endereco_formatado: str
    logradouro: str | None = None
    numero: str | None = None  # como o provedor escreve: "100", "100-A"
    bairro: str | None = None
    municipio: str | None = None
    uf: str | None = None
    cep: str | None = None
    provedor: Provedor
    precisao: Precisao


EnderecoExternoFeature = GeoFeature[PointGeometry, EnderecoExternoAttributes]


class ConsultaGeocodificacao(BaseModel):
    texto: str = Field(min_length=1, max_length=TAMANHO_MAX_CONSULTA)

    @property
    def chave(self) -> str:
        """Duas consultas com a mesma chave são a mesma consulta."""
        return normalize_text(self.texto)


class GeocodificacaoExterna(BaseModel):
    """O vínculo entre o que a pessoa digitou e o endereço que um provedor encontrou para aquilo."""

    consulta: ConsultaGeocodificacao
    endereco: EnderecoExternoFeature
    # quando o provedor foi chamado: servir do cache não o muda
    consultado_em: AwareDatetime


class PoliticaGeocodificacao(BaseModel):
    """O recorte de toda consulta externa: cada provedor o traduz na sua requisição."""

    model_config = ConfigDict(frozen=True)

    idioma: str = "pt-BR"
    pais: str = "BR"
    uf: str = "SP"
    municipio: str = "São Paulo"
    precisao_minima: Precisao = Precisao.INTERPOLADA
    validade_dias: int = Field(default=30, gt=0)
