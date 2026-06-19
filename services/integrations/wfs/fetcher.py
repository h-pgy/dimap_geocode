import random
import time
from json import JSONDecodeError
from typing import Generator, NoReturn

import requests

from .exceptions import WfsConnectionError, WfsHttpError, WfsInvalidResponseError, WfsTimeoutError
from .models import WfsConnectionConfig, WfsFeatureCollection, WfsFeatureRequest, WfsRetryPolicy


class WfsFetcher:
    """Cliente WFS callable, paginado e agnóstico de Django (config injetada)."""

    def __init__(
        self,
        config: WfsConnectionConfig,
        *,
        retry_policy: WfsRetryPolicy | None = None,
        verbose: bool = False,
    ) -> None:
        self.config = config
        self.retry_policy = retry_policy or WfsRetryPolicy()
        self.verbose = verbose
        self.features_fetched_count = 0

    def _base_params(self, request: WfsFeatureRequest) -> dict[str, str | int]:
        return {
            "service": self.config.service,
            "version": self.config.version,
            "request": "GetFeature",
            "typeName": f"{self.config.namespace}:{request.nome_camada}",
            **request.to_query_params(),
        }

    def _request_with_retries(self, params: dict[str, str | int]) -> requests.Response:
        policy = self.retry_policy
        for attempt_number in range(policy.max_retries + 1):  # range FINITO → sem loop infinito
            try:
                return requests.get(
                    self.config.url_base,
                    params=params,
                    timeout=policy.request_timeout_seconds,
                )
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                self._handle_network_failure(exc, attempt_number)
        raise AssertionError("loop de retry terminou sem retornar nem levantar")

    def _handle_network_failure(
        self, exc: requests.exceptions.RequestException, attempt_number: int
    ) -> None:
        """Destino de uma falha de rede: esgotou os retries → levanta; senão → espera e repete."""
        policy = self.retry_policy
        if self.verbose:
            print(
                f"WFS falha de rede (tentativa {attempt_number + 1}/{policy.max_retries + 1}): {exc!r}"
            )
        if attempt_number >= policy.max_retries:
            self._raise_network_error(exc)
        time.sleep(random.uniform(
            policy.retry_wait_min_seconds,
            policy.retry_wait_max_seconds,
        ))

    def _raise_network_error(self, exc: requests.exceptions.RequestException) -> NoReturn:
        """Traduz a falha de rede na exception própria. Timeout testado primeiro porque
        ConnectTimeout herda de ambos Timeout e ConnectionError."""
        total_attempts = self.retry_policy.max_retries + 1
        if isinstance(exc, requests.exceptions.Timeout):
            raise WfsTimeoutError(
                f"WFS não respondeu (timeout={self.retry_policy.request_timeout_seconds}s) "
                f"após {total_attempts} tentativas"
            ) from exc
        raise WfsConnectionError(
            f"Falha de conexão com o WFS após {total_attempts} tentativas"
        ) from exc

    def _get_page(self, request: WfsFeatureRequest, start_index: int) -> WfsFeatureCollection:
        params = self._base_params(request)
        params["startIndex"] = start_index
        if self.verbose:
            print(f"WFS GET {self.config.url_base} :: {params}")
        resp = self._request_with_retries(params)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            raise WfsHttpError(str(exc), response=resp) from exc
        try:
            payload = resp.json()
        except JSONDecodeError:
            raise WfsInvalidResponseError(f"Resposta não é JSON válido: {resp.text}")
        return WfsFeatureCollection.model_validate(payload)

    def fetch_feature_batches(
        self, request: WfsFeatureRequest
    ) -> Generator[WfsFeatureCollection, None, None]:
        start_index = request.start_index or 0
        self.features_fetched_count = 0
        while True:
            page = self._get_page(request, start_index)
            if not page.features:
                break
            n = len(page.features)
            self.features_fetched_count += n
            start_index += n
            yield page
            if page.number_matched is not None and self.features_fetched_count >= page.number_matched:
                break

    def __call__(
        self, request: WfsFeatureRequest
    ) -> Generator[WfsFeatureCollection, None, None]:
        return self.fetch_feature_batches(request)
