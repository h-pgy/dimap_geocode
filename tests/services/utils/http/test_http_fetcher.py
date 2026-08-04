from typing import Any
from unittest.mock import Mock

import pytest

from services.utils.http import HttpFetcher, HttpFetchError, HttpRetryPolicy

URL = "https://portal.test/documents/itbi_2025.xlsx"


def _politica(max_retries: int) -> HttpRetryPolicy:
    # Espera zero: o que se testa é quantas vezes repete, não quanto tempo dorme.
    return HttpRetryPolicy(
        max_retries=max_retries,
        retry_wait_min_seconds=0.0,
        retry_wait_max_seconds=0.0,
        status_para_retry=(429, 500, 502, 503, 504),
    )


def _resposta(status: int) -> Mock:
    resposta = Mock()
    resposta.status_code = status
    resposta.raise_for_status.return_value = None
    return resposta


def _session(*respostas: Any) -> Mock:
    # Dublê de transporte: a Session é ponto de composição do cliente (§7.1), então o teste
    # injeta a dela em vez de espionar o módulo por dentro.
    session = Mock()
    session.headers = {}
    session.get.side_effect = list(respostas)
    return session


def test_http_fetcher_repete_em_503_e_levanta_erro_proprio_ao_esgotar() -> None:
    politica = _politica(max_retries=2)
    session = _session(*[_resposta(503)] * 3)

    with pytest.raises(HttpFetchError) as excinfo:
        HttpFetcher(politica, session=session)(URL)

    assert session.get.call_count == 3, "503 é transitório: tem que repetir até o limite"
    # A mensagem é o que sobra no metadado dias depois — sem URL e tentativas, não diz nada.
    assert URL in str(excinfo.value)
    assert "3" in str(excinfo.value)

    ok = _resposta(200)
    session = _session(_resposta(503), ok)
    fetcher = HttpFetcher(politica, session=session, user_agent="DIMAP GeoCoder (teste)")

    assert fetcher(URL, stream=True) is ok
    assert session.get.call_count == 2

    # A identificação vale para todas as chamadas, e o kwargs da chamada chega ao get com o
    # timeout da política como default.
    assert session.headers["User-Agent"] == "DIMAP GeoCoder (teste)"
    _, kwargs = session.get.call_args
    assert kwargs["stream"] is True
    assert kwargs["timeout"] == politica.request_timeout_seconds
