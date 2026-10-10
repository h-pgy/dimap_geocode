from pydantic import ValidationError
from requests import Response

from services.utils.http import HttpFetchError

from ..base import ClienteGeocodificacao
from ..exceptions import RespostaInvalidaError, TransporteError
from .models import CABECALHO_CHAVE, URL_GEOCODING, GeocodeRequest, GeocodeResponse


class Cliente(ClienteGeocodificacao[GeocodeRequest, GeocodeResponse]):
    def __call__(self, requisicao: GeocodeRequest) -> GeocodeResponse:
        return self.pipeline(requisicao)

    def pipeline(self, requisicao: GeocodeRequest) -> GeocodeResponse:
        http = self._buscar(requisicao)
        return self._validar(http)

    def _buscar(self, requisicao: GeocodeRequest) -> Response:
        # único ponto onde a chave é aberta: vai no header, nunca na URL
        cabecalho = {CABECALHO_CHAVE: self.token.get_secret_value()}
        try:
            return self._fetcher(
                URL_GEOCODING,
                params=requisicao.to_query_params(),
                headers=cabecalho,
            )
        except HttpFetchError as exc:
            raise TransporteError(str(exc)) from exc

    def _validar(self, http: Response) -> GeocodeResponse:
        try:
            return GeocodeResponse.model_validate_json(http.content)
        except ValidationError as exc:
            raise RespostaInvalidaError(str(exc)) from exc
