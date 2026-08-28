"""Testes de services/scripts/ortofotos_fundo/gerador.py (SPEC design/010): a idempotência do
disco — ortofoto existente não é rebuscada, salvo `forcar` — e a gravação em tons de cinza.
"""

from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

from config.pontos_fundo import PontoFundo
from services.integrations.wms import WmsConnectionConfig
from services.scripts.ortofotos_fundo.contrato import OrtofotoConfig
from services.scripts.ortofotos_fundo.gerador import GeradorOrtofotosFundo

CHAVE = "se"


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

    WmsFetcherClass.assert_called_once()
    fetcher_instance.assert_called_once()
    assert resultado.geradas == [CHAVE]


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
