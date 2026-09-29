from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from services.utils.http import HttpRetryPolicy

URL_GEOCODING = "https://geocode.googleapis.com/v4/geocode/address"
CABECALHO_CHAVE = "X-Goog-Api-Key"
CRS: int = 4326

# chamada síncrona dentro da busca: timeout curto e uma única repetição
RETRY = HttpRetryPolicy(
    request_timeout_seconds=10.0,
    max_retries=1,
    status_para_retry=(500, 502, 503, 504),
)

Granularity = Literal[
    "GRANULARITY_UNSPECIFIED",
    "ROOFTOP",
    "RANGE_INTERPOLATED",
    "GEOMETRIC_CENTER",
    "APPROXIMATE",
]

CAMEL_CASE = ConfigDict(alias_generator=to_camel, validate_by_name=True)


class PostalAddress(BaseModel):
    """O `PostalAddress` da requisição: só os campos que a DIMAP preenche."""

    address_lines: list[str] = Field(min_length=1)
    locality: str | None = None
    administrative_area: str | None = None
    region_code: str | None = None  # CLDR: "BR"


class GeocodeRequest(BaseModel):
    address: PostalAddress
    language_code: str | None = None
    region_code: str | None = None  # ccTLD: "br"

    def to_query_params(self) -> dict[str, str | list[str]]:
        # o token não entra aqui: vai no header, e a requisição pode ser logada sem risco
        todos: dict[str, str | list[str] | None] = {
            "address.addressLines": self.address.address_lines,
            "address.locality": self.address.locality,
            "address.administrativeArea": self.address.administrative_area,
            "address.regionCode": self.address.region_code,
            "languageCode": self.language_code,
            "regionCode": self.region_code,
        }
        # parâmetro vazio é diferente de parâmetro ausente
        return {nome: valor for nome, valor in todos.items() if valor is not None}


class LatLng(BaseModel):
    model_config = CAMEL_CASE

    latitude: float
    longitude: float


class AddressComponent(BaseModel):
    model_config = CAMEL_CASE

    long_text: str
    short_text: str | None = None  # a API só o manda quando há abreviação
    types: list[str]


class GeocodeResult(BaseModel):
    model_config = CAMEL_CASE

    formatted_address: str
    location: LatLng
    granularity: Granularity = "GRANULARITY_UNSPECIFIED"  # o JSON omite o valor padrão do enum
    address_components: list[AddressComponent] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)


class GeocodeResponse(BaseModel):
    model_config = CAMEL_CASE

    results: list[GeocodeResult] = Field(default_factory=list)  # sem resultado, pode vir omitida
