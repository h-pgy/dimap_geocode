import random
import time
from collections.abc import Mapping
from typing import Any

import requests
from requests import Response, Session

from .exceptions import HttpFetchError, HttpStatusError
from .models import HttpRetryPolicy


class HttpFetcher:
    """Callable: GET com retry. Devolve a resposta; quem a interpreta é o chamador."""

    def __init__(
        self,
        policy: HttpRetryPolicy,
        *,
        session: Session | None = None,
        user_agent: str | None = None,
        headers: Mapping[str, str] | None = None,
        verbose: bool = False,
    ) -> None:
        self._policy = policy
        # Session e não requests.get solto: os headers valem para todas as chamadas e a
        # conexão é reaproveitada nos downloads de uma mesma carga.
        self._session = session or Session()
        if user_agent is not None:
            self._session.headers["User-Agent"] = user_agent
        if headers:
            self._session.headers.update(headers)  # depois: header cru vence o atalho
        self._verbose = verbose

    def __call__(self, url: str, **kwargs: Any) -> Response:
        # kwargs vai direto para o session.get: stream, params, headers da chamada.
        kwargs.setdefault("timeout", self._policy.request_timeout_seconds)
        for tentativa in range(self._policy.max_retries + 1):  # range FINITO → sem loop infinito
            resposta = self._tentar(url, tentativa, **kwargs)
            if resposta is not None:
                return resposta
        raise AssertionError("loop de retry terminou sem retornar nem levantar")

    def _tentar(self, url: str, tentativa: int, **kwargs: Any) -> Response | None:
        """A resposta boa, ou None quando ainda há tentativa; esgotado, levanta."""
        try:
            resposta = self._session.get(url, **kwargs)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            self._esperar_ou_desistir(url, repr(exc), tentativa)
            return None

        if resposta.status_code in self._policy.status_para_retry:
            self._esperar_ou_desistir(url, f"HTTP {resposta.status_code}", tentativa)
            return None

        try:
            resposta.raise_for_status()  # status fora da lista: definitivo, repetir não ajuda
        except requests.exceptions.HTTPError as exc:
            raise HttpStatusError(f"{url}: HTTP {resposta.status_code}") from exc
        return resposta

    def _esperar_ou_desistir(self, url: str, motivo: str, tentativa: int) -> None:
        total = self._policy.max_retries + 1
        if self._verbose:
            print(f"HTTP falha ({tentativa + 1}/{total}) em {url}: {motivo}")
        if tentativa >= self._policy.max_retries:
            raise HttpFetchError(f"{url}: {motivo} após {total} tentativas")
        time.sleep(
            random.uniform(
                self._policy.retry_wait_min_seconds,
                self._policy.retry_wait_max_seconds,
            )
        )
