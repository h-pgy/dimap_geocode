"""Testes automatizados da SPEC design/020: montagem da gaveta de desenhos da bancada."""

import pytest

from services.domain.desenho.gaveta import GavetaDesenhosInput, MontarGavetaDesenhos
from services.domain.desenho.models import Desenho, Grandeza, Hemisferio, TipoDesenho
from services.domain.geometry import LineGeometry, PointGeometry, PolygonGeometry, reprojetar

CRS_MAPA = 4326
CRS_METRICO = 31983
CRS_GEOGRAFICO = 4674


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _ponto(id_bancada: str, origem: tuple[float, float] = (333000.0, 7395000.0)) -> Desenho:
    x0, y0 = origem
    geometria = reprojetar(PointGeometry(type="Point", coordinates=[x0, y0]), CRS_METRICO, CRS_MAPA)
    return Desenho(id_bancada=id_bancada, geometria=geometria)


def _ponto_em_graus(id_bancada: str, longitude: float, latitude: float) -> Desenho:
    geometria = PointGeometry(type="Point", coordinates=[longitude, latitude])
    return Desenho(id_bancada=id_bancada, geometria=geometria)


def _linha(
    id_bancada: str,
    origem: tuple[float, float] = (333000.0, 7395000.0),
    comprimento: float = 100.0,
) -> Desenho:
    x0, y0 = origem
    inicio = reprojetar(PointGeometry(type="Point", coordinates=[x0, y0]), CRS_METRICO, CRS_MAPA)
    fim = reprojetar(
        PointGeometry(type="Point", coordinates=[x0 + comprimento, y0]), CRS_METRICO, CRS_MAPA
    )
    geometria = LineGeometry(type="LineString", coordinates=[inicio.coordinates, fim.coordinates])
    return Desenho(id_bancada=id_bancada, geometria=geometria)


def _poligono(
    id_bancada: str,
    origem: tuple[float, float] = (333000.0, 7395000.0),
    lado: float = 100.0,
) -> Desenho:
    x0, y0 = origem
    metrico = PolygonGeometry(
        type="Polygon",
        coordinates=[[
            [x0, y0],
            [x0 + lado, y0],
            [x0 + lado, y0 + lado],
            [x0, y0 + lado],
            [x0, y0],
        ]],
    )
    geometria = reprojetar(metrico, CRS_METRICO, CRS_MAPA)
    return Desenho(id_bancada=id_bancada, geometria=geometria)


def _gaveta_desenhos_input(
    desenhos: tuple[Desenho, ...],
    id_selecionado: str | None = None,
) -> GavetaDesenhosInput:
    return GavetaDesenhosInput(
        desenhos=desenhos,
        id_selecionado=id_selecionado,
        crs_mapa=CRS_MAPA,
        crs_metrico=CRS_METRICO,
        crs_geografico=CRS_GEOGRAFICO,
    )


# ---------------------------------------------------------------------------
# Poços por tipo, na ordem da bancada
# ---------------------------------------------------------------------------


def test_poco_por_tipo_na_ordem_da_bancada() -> None:
    entrada = _gaveta_desenhos_input((_ponto("1"), _poligono("2"), _poligono("3")))
    gaveta = MontarGavetaDesenhos()(entrada)
    assert [poco.tipo for poco in gaveta.pocos] == [TipoDesenho.PONTO, TipoDesenho.POLIGONO]


# ---------------------------------------------------------------------------
# Grandezas: área no polígono, comprimento na linha, posição no ponto
# ---------------------------------------------------------------------------


def test_cada_tipo_mostra_a_sua_grandeza() -> None:
    # A latitude está na borda em que arredondar os segundos à parte daria 60,000″.
    ponto = _ponto_em_graus("1", longitude=-46.633308, latitude=-23.9999999999)
    entrada = _gaveta_desenhos_input((ponto, _linha("2"), _poligono("3")))
    gaveta = MontarGavetaDesenhos()(entrada)
    por_tipo = {poco.tipo: poco.desenhos[0] for poco in gaveta.pocos}

    assert por_tipo[TipoDesenho.PONTO].medida is None
    posicao = por_tipo[TipoDesenho.PONTO].posicao
    assert posicao is not None
    latitude = posicao.latitude
    longitude = posicao.longitude
    assert (latitude.graus, latitude.minutos, latitude.hemisferio) == (24, 0, Hemisferio.SUL)
    assert latitude.segundos == pytest.approx(0.0)
    assert (longitude.graus, longitude.minutos, longitude.hemisferio) == (46, 37, Hemisferio.OESTE)
    assert longitude.segundos == pytest.approx(59.909)
    assert posicao.latitude.graus_decimais == pytest.approx(-24.0)

    medida_linha = por_tipo[TipoDesenho.LINHA].medida
    assert medida_linha is not None
    assert medida_linha.grandeza is Grandeza.COMPRIMENTO
    assert medida_linha.valor == pytest.approx(100.0, rel=0.01)
    assert medida_linha.unidade == "m"

    medida_poligono = por_tipo[TipoDesenho.POLIGONO].medida
    assert medida_poligono is not None
    assert medida_poligono.grandeza is Grandeza.AREA
    assert medida_poligono.valor == pytest.approx(10_000.0, rel=0.01)
    assert medida_poligono.unidade == "m²"


# ---------------------------------------------------------------------------
# Seleção única na gaveta: só a escolha do usuário, que desenho novo não toma
# ---------------------------------------------------------------------------


def test_sem_escolha_a_gaveta_nasce_sem_selecao() -> None:
    entrada = _gaveta_desenhos_input((_ponto("1"), _poligono("2"), _poligono("3")))
    gaveta = MontarGavetaDesenhos()(entrada)
    assert gaveta.id_selecionado is None


def test_escolha_sobrevive_a_desenho_novo() -> None:
    entrada = _gaveta_desenhos_input(
        (_poligono("1"), _poligono("2"), _poligono("3"), _ponto("9")),
        id_selecionado="2",
    )
    gaveta = MontarGavetaDesenhos()(entrada)
    assert gaveta.id_selecionado == "2"


def test_escolha_apagada_deixa_a_gaveta_sem_selecao() -> None:
    entrada = _gaveta_desenhos_input((_poligono("1"), _poligono("2")), id_selecionado="3")
    gaveta = MontarGavetaDesenhos()(entrada)
    assert gaveta.id_selecionado is None
