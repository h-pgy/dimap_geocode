"""Testes de services/scripts/ortofotos_fundo/gerador.py (SPEC design/010): a idempotência do
disco — ortofoto existente não é rebuscada, salvo `forcar` —, a gravação em tons de cinza e o
GeoSampa fora do ar virando pendência em vez de erro.
"""

from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from config.pontos_fundo import PontoFundo
from services.integrations.wms import (
    WmsConnectionConfig,
    WmsConnectionError,
    WmsHttpError,
    WmsMapRequest,
    WmsTimeoutError,
)
from services.scripts.ortofotos_fundo.contrato import OrtofotoConfig
from services.scripts.ortofotos_fundo.gerador import GeradorOrtofotosFundo

CHAVE = "se"
LARGURA_ORTOFOTO_PX = 2000


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _png_rgb_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (4, 4), color=(10, 20, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


def _config(destino: Path, **overrides: object) -> OrtofotoConfig:
    defaults: dict[str, object] = {
        "pontos": {CHAVE: PontoFundo(descricao="Praça da Sé — Centro", lat=-23.5505, lng=-46.6333)},
        "conexao": WmsConnectionConfig(
            vector_url="https://wms.test/ows",
            raster_url="https://wms.test/raster",
        ),
        "destino": destino,
        "camada": "geoportal:ORTO_RGB_2020",
        "metros_por_pixel": 4.4,
        "largura_px": 8,
        "altura_px": 8,
        "crs_entrada": 4326,
        "crs_saida": 31983,
    }
    defaults.update(overrides)
    return OrtofotoConfig(**defaults)


def _wms_fetcher_instance() -> Mock:
    return Mock(return_value=Mock(content=_png_rgb_bytes()))


def _pontos(*chaves: str) -> dict[str, PontoFundo]:
    return {chave: PontoFundo(descricao=chave, lat=-23.5505, lng=-46.6333) for chave in chaves}


# ---------------------------------------------------------------------------
# Idempotência do disco
# ---------------------------------------------------------------------------


def test_geracao_pula_ortofoto_existente(tmp_path: Path) -> None:
    (tmp_path / f"{CHAVE}.png").write_bytes(_png_rgb_bytes())
    config = _config(tmp_path)

    with patch("services.scripts.ortofotos_fundo.gerador.WmsFetcher") as WmsFetcherClass:
        resultado = GeradorOrtofotosFundo()(config)

    WmsFetcherClass.assert_not_called()
    assert resultado.puladas == [CHAVE]
    assert resultado.geradas == []


def test_geracao_forcada_rebusca(tmp_path: Path) -> None:
    (tmp_path / f"{CHAVE}.png").write_bytes(_png_rgb_bytes())
    config = _config(tmp_path, forcar=True)
    fetcher_instance = _wms_fetcher_instance()

    with patch(
        "services.scripts.ortofotos_fundo.gerador.WmsFetcher",
        return_value=fetcher_instance,
    ) as WmsFetcherClass:
        resultado = GeradorOrtofotosFundo()(config)

    WmsFetcherClass.assert_called()
    assert resultado.geradas == [CHAVE]
    assert resultado.puladas == []


# ---------------------------------------------------------------------------
# Gravação em tons de cinza
# ---------------------------------------------------------------------------


def test_ortofoto_gravada_em_tons_de_cinza(tmp_path: Path) -> None:
    config = _config(tmp_path)
    fetcher_instance = _wms_fetcher_instance()

    with patch(
        "services.scripts.ortofotos_fundo.gerador.WmsFetcher",
        return_value=fetcher_instance,
    ):
        GeradorOrtofotosFundo()(config)

    imagem_gravada = Image.open(tmp_path / f"{CHAVE}.png")
    assert imagem_gravada.mode == "L"


# ---------------------------------------------------------------------------
# GeoSampa fora do ar
# ---------------------------------------------------------------------------


def test_geosampa_fora_do_ar_nao_pede_ortofoto(tmp_path: Path) -> None:
    config = _config(tmp_path, pontos=_pontos("a", "b"), largura_px=LARGURA_ORTOFOTO_PX)
    fetcher_instance = Mock(side_effect=WmsConnectionError("WMS inacessível"))

    with patch(
        "services.scripts.ortofotos_fundo.gerador.WmsFetcher",
        return_value=fetcher_instance,
    ):
        resultado = GeradorOrtofotosFundo()(config)

    larguras_pedidas = [chamada.args[0].width for chamada in fetcher_instance.call_args_list]
    assert LARGURA_ORTOFOTO_PX not in larguras_pedidas
    assert list(tmp_path.iterdir()) == []
    assert resultado.geradas == []
    assert resultado.pendentes == ["a", "b"]
    assert resultado.indisponibilidade == "WMS inacessível"


def test_queda_no_meio_preserva_as_geradas(tmp_path: Path) -> None:
    config = _config(tmp_path, pontos=_pontos("a", "b", "c"))
    resposta = Mock(content=_png_rgb_bytes())
    # Sonda, ponto "a" e então a queda no ponto "b".
    fetcher_instance = Mock(side_effect=[resposta, resposta, WmsTimeoutError("sem resposta")])

    with patch(
        "services.scripts.ortofotos_fundo.gerador.WmsFetcher",
        return_value=fetcher_instance,
    ):
        resultado = GeradorOrtofotosFundo()(config)

    assert (tmp_path / "a.png").exists()
    assert resultado.geradas == ["a"]
    assert resultado.pendentes == ["b", "c"]


def test_erro_que_nao_e_indisponibilidade_propaga(tmp_path: Path) -> None:
    config = _config(tmp_path)
    fetcher_instance = Mock(side_effect=WmsHttpError("400 Bad Request"))

    with patch(
        "services.scripts.ortofotos_fundo.gerador.WmsFetcher",
        return_value=fetcher_instance,
    ):
        with pytest.raises(WmsHttpError):
            GeradorOrtofotosFundo()(config)


# ---------------------------------------------------------------------------
# Anúncio do download
# ---------------------------------------------------------------------------


def test_download_e_anunciado_antes_de_comecar(tmp_path: Path) -> None:
    avisos: list[str] = []
    avisos_a_cada_requisicao: list[int] = []

    def _responder(requisicao: WmsMapRequest) -> Mock:
        avisos_a_cada_requisicao.append(len(avisos))
        return Mock(content=_png_rgb_bytes())

    with patch(
        "services.scripts.ortofotos_fundo.gerador.WmsFetcher",
        return_value=Mock(side_effect=_responder),
    ):
        GeradorOrtofotosFundo(avisar=avisos.append)(_config(tmp_path))
        anunciados_na_primeira_geracao = len(avisos)
        GeradorOrtofotosFundo(avisar=avisos.append)(_config(tmp_path))

    assert avisos_a_cada_requisicao[0] == 1
    assert "GeoSampa" in avisos[0]
    assert CHAVE in avisos[1]
    assert len(avisos) == anunciados_na_primeira_geracao
