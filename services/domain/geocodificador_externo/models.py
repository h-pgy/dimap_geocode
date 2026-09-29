from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from services.domain.geometry import GeoFeature, PointGeometry


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


class PoliticaGeocodificacao(BaseModel):
    """O recorte de toda consulta externa: cada provedor o traduz na sua requisição."""

    model_config = ConfigDict(frozen=True)

    idioma: str = "pt-BR"
    pais: str = "BR"
    uf: str = "SP"
    municipio: str = "São Paulo"
    precisao_minima: Precisao = Precisao.INTERPOLADA


class ConsultaGeocodificacao(BaseModel):
    texto: str = Field(min_length=1)
