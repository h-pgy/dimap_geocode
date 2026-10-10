from abc import ABC, abstractmethod

from pydantic import BaseModel, SecretStr

from services.utils.http import HttpFetcher


class ClienteGeocodificacao[Req: BaseModel, Resp: BaseModel](ABC):
    def __init__(self, token: SecretStr, fetcher: HttpFetcher) -> None:
        self.token = token
        self._fetcher = fetcher

    @abstractmethod
    def __call__(self, requisicao: Req) -> Resp:
        """A resposta do provedor, tipada; toda falha sai como `ClienteGeocodificacaoError`."""
