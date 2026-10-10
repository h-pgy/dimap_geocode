"""Testes de apps/certidao_lancamento/emissao.py (SPEC certidao_lancamento/002): as geometrias do
conjunto no CRS métrico e as camadas da planta que elas alimentam."""

import pytest

from apps.certidao_lancamento.emissao import (
    camadas_da_planta_do_conjunto,
    geometrias_metricas,
)
from services.domain.desenho import Desenho
from services.domain.geometry import PolygonGeometry, reprojetar
from services.domain.lote_geocod import LoteAttributes, LoteFeature
from services.domain.lotes_mais_proximos import ConjuntoDeLotes, LotesDoDesenho
from services.domain.planta_localizacao import EstiloGeometria

CRS_MAPA = 4326
CRS_METRICO = 31983
X0_UTM = 333_000.0
Y0_UTM = 7_395_000.0

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _retangulo_metrico(x0: float, largura: float, altura: float) -> PolygonGeometry:
    anel = [
        [x0, Y0_UTM],
        [x0 + largura, Y0_UTM],
        [x0 + largura, Y0_UTM + altura],
        [x0, Y0_UTM + altura],
        [x0, Y0_UTM],
    ]
    return PolygonGeometry(type="Polygon", coordinates=[anel])


def _lote(id_poligono: str, x0: float) -> LoteFeature:
    return LoteFeature(
        geometry=_retangulo_metrico(x0, 20.0, 20.0),
        attributes=LoteAttributes(
            id_poligono=id_poligono,
            setor="005",
            quadra="003",
            lote="0048",
            tipo_lote="F",
        ),
        crs=CRS_METRICO,
    )


def _conjunto() -> ConjuntoDeLotes:
    desenho_no_mapa = reprojetar(_retangulo_metrico(X0_UTM - 10.0, 60.0, 40.0), CRS_METRICO, CRS_MAPA)
    apurado = LotesDoDesenho(
        desenho=Desenho(id_bancada="7", geometria=desenho_no_mapa),
        area_m2=2400.0,
        lotes=(_lote("1001", X0_UTM), _lote("1002", X0_UTM + 20.0)),
    )
    return ConjuntoDeLotes(apurado=apurado)


def _primeiro_vertice(poligono: PolygonGeometry) -> list[float]:
    return poligono.coordinates[0][0]  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Planta do conjunto
# ---------------------------------------------------------------------------


def test_planta_do_conjunto_poe_desenho_em_destaque_sobre_lotes_de_contexto() -> None:
    # O desenho está no CRS do mapa; os lotes, no da camada
    geometrias = geometrias_metricas(_conjunto(), crs_mapa=CRS_MAPA, crs_metrico=CRS_METRICO)

    camadas = camadas_da_planta_do_conjunto(geometrias)

    assert [camada.estilo for camada in camadas] == [
        EstiloGeometria.CONTEXTO,
        EstiloGeometria.DESTAQUE,
    ]
    lotes, desenho = camadas
    # Os dois chegam à planta no mesmo CRS métrico
    assert len(lotes.geometrias) == 2
    assert _primeiro_vertice(lotes.geometrias[0]) == pytest.approx([X0_UTM, Y0_UTM], abs=0.01)
    assert _primeiro_vertice(lotes.geometrias[1]) == pytest.approx([X0_UTM + 20.0, Y0_UTM], abs=0.01)
    assert len(desenho.geometrias) == 1
    assert _primeiro_vertice(desenho.geometrias[0]) == pytest.approx([X0_UTM - 10.0, Y0_UTM], abs=0.01)
