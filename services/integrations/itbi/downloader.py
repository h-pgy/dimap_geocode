from collections.abc import Callable
from pathlib import Path
from typing import Any

from services.utils.http import HttpFetchError
from services.utils.io import escrever_atomico

from .constants import TAMANHO_CHUNK
from .exceptions import ItbiDownloadError
from .models import PlanilhaItbi


class ItbiPlanilhaDownloader:
    """Callable: a planilha de um ano → um arquivo em disco, escrito atomicamente."""

    def __init__(self, fetcher: Callable[..., Any]) -> None:
        self._fetcher = fetcher

    def __call__(self, planilha: PlanilhaItbi, destino: Path) -> Path:
        # O erro do utilitário morre aqui: para fora deste pacote só sai exceção da ITBI.
        try:
            resposta = self._fetcher(planilha.url, stream=True)
        except HttpFetchError as exc:
            raise ItbiDownloadError(f"planilha de {planilha.ano}: {exc}") from exc
        # Atômico: uma queda no meio não substitui o xlsx bom do ano por um truncado.
        return escrever_atomico(destino, lambda tmp: self._gravar(resposta, tmp))

    def _gravar(self, resposta: Any, destino: Path) -> None:
        with open(destino, "wb") as arquivo:
            for pedaco in resposta.iter_content(chunk_size=TAMANHO_CHUNK):
                arquivo.write(pedaco)
