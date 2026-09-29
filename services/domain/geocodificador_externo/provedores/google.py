from collections.abc import Callable

from services.domain.geometry import PointGeometry

# o erro é comum a todos os provedores; o Google entra como namespace
from services.integrations.geocodificador_externo import ClienteGeocodificacaoError, google

from ..exceptions import ProvedorIndisponivelError
from ..models import (
    ConsultaGeocodificacao,
    EnderecoExternoAttributes,
    EnderecoExternoFeature,
    PoliticaGeocodificacao,
    Precisao,
    Provedor,
)
from ..porta import ProvedorGeocodificacao

PRECISAO_POR_GRANULARITY: dict[google.Granularity, Precisao] = {
    "ROOFTOP": Precisao.IMOVEL,
    "RANGE_INTERPOLATED": Precisao.INTERPOLADA,
    "GEOMETRIC_CENTER": Precisao.LOGRADOURO,
    "APPROXIMATE": Precisao.APROXIMADA,
    "GRANULARITY_UNSPECIFIED": Precisao.APROXIMADA,
}

# vence o primeiro tipo presente no resultado
TIPOS_LOGRADOURO = ("route",)
TIPOS_NUMERO = ("street_number",)
TIPOS_BAIRRO = ("sublocality_level_1", "sublocality", "neighborhood")
TIPOS_MUNICIPIO = ("administrative_area_level_2", "locality")
TIPOS_UF = ("administrative_area_level_1",)
TIPOS_CEP = ("postal_code",)

ClienteLike = Callable[[google.GeocodeRequest], google.GeocodeResponse]


class ProvedorGoogle(ProvedorGeocodificacao):
    provedor = Provedor.GOOGLE

    def __init__(self, politica: PoliticaGeocodificacao, cliente: ClienteLike) -> None:
        super().__init__(politica)
        self._cliente = cliente

    def __call__(self, consulta: ConsultaGeocodificacao) -> list[EnderecoExternoFeature]:
        return self.pipeline(consulta)

    def pipeline(self, consulta: ConsultaGeocodificacao) -> list[EnderecoExternoFeature]:
        requisicao = self._montar_requisicao(consulta)
        resposta = self._consultar(requisicao)
        return [self._resultado_para_endereco(r) for r in resposta.results]

    def _montar_requisicao(self, consulta: ConsultaGeocodificacao) -> google.GeocodeRequest:
        # a v4 não filtra por componente: o recorte da política vai no endereço estruturado
        p = self.politica
        return google.GeocodeRequest(
            address=google.PostalAddress(
                address_lines=[consulta.texto],
                locality=p.municipio,
                administrative_area=p.uf,
                region_code=p.pais,
            ),
            language_code=p.idioma,
            region_code=p.pais.lower(),  # ccTLD
        )

    def _consultar(self, requisicao: google.GeocodeRequest) -> google.GeocodeResponse:
        try:
            return self._cliente(requisicao)
        except ClienteGeocodificacaoError as exc:
            raise ProvedorIndisponivelError(str(exc)) from exc

    def _resultado_para_endereco(self, r: google.GeocodeResult) -> EnderecoExternoFeature:
        return EnderecoExternoFeature(
            geometry=PointGeometry(
                type="Point",
                coordinates=[r.location.longitude, r.location.latitude],
            ),
            attributes=EnderecoExternoAttributes(
                endereco_formatado=r.formatted_address,
                logradouro=self._componente(r, TIPOS_LOGRADOURO),
                numero=self._componente(r, TIPOS_NUMERO),
                bairro=self._componente(r, TIPOS_BAIRRO),
                municipio=self._componente(r, TIPOS_MUNICIPIO),
                uf=self._componente(r, TIPOS_UF, curto=True),
                cep=self._componente(r, TIPOS_CEP),
                provedor=self.provedor,
                precisao=PRECISAO_POR_GRANULARITY[r.granularity],
            ),
            crs=google.CRS,
        )

    def _componente(
        self,
        r: google.GeocodeResult,
        tipos: tuple[str, ...],
        curto: bool = False,
    ) -> str | None:
        for tipo in tipos:
            for componente in r.address_components:
                if tipo in componente.types:
                    return componente.short_text if curto else componente.long_text
        return None
