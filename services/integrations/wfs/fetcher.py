from __future__ import annotations

from json import JSONDecodeError
from typing import Generator

import requests

from .exceptions import WfsHttpError, WfsInvalidResponseError
from .models import WfsConnectionConfig, WfsFeatureCollection, WfsFeatureRequest


class WfsFetcher:
    """Cliente WFS callable, paginado e agnóstico de Django (config injetada)."""

    def __init__(self, config: WfsConnectionConfig, *, verbose: bool = False) -> None:
        self.config = config
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

    def _get_page(self, request: WfsFeatureRequest, start_index: int) -> WfsFeatureCollection:
        params = self._base_params(request)
        params["startIndex"] = start_index
        if self.verbose:
            print(f"WFS GET {self.config.url_base} :: {params}")
        resp = requests.get(self.config.url_base, params=params)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            raise WfsHttpError(str(exc), response=resp) from exc
        try:
            payload = resp.json()
        except JSONDecodeError:
            raise WfsInvalidResponseError(f"Resposta não é JSON válido: {resp.text[:500]}")
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
