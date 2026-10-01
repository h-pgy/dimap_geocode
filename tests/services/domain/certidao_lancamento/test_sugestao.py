from django.contrib.gis.geos import GEOSGeometry, Polygon

from services.domain.certidao_lancamento.models import TipoDespacho
from services.domain.certidao_lancamento.sugestao import (
    SugerirTipoDespacho,
    SugestaoDespachoInput,
)

CRS_METRICO = 31983
FRACAO_MINIMA_CONTIDA = 0.99

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _retangulo(x0: float, y0: float, largura: float, altura: float) -> GEOSGeometry:
    retangulo = Polygon.from_bbox((x0, y0, x0 + largura, y0 + altura))
    retangulo.srid = CRS_METRICO
    return retangulo


def _sugerir(desenho: GEOSGeometry, *lotes: GEOSGeometry) -> TipoDespacho:
    sugerir_tipo = SugerirTipoDespacho()
    return sugerir_tipo(
        SugestaoDespachoInput(
            desenho=desenho,
            lotes=lotes,
            fracao_minima_contida=FRACAO_MINIMA_CONTIDA,
        )
    )


# ---------------------------------------------------------------------------
# Sugestão do tipo de despacho
# ---------------------------------------------------------------------------


def test_sugestao_de_tipo_pela_geometria() -> None:
    desenho = _retangulo(0.0, 0.0, 100.0, 100.0)
    lote_dentro = _retangulo(10.0, 10.0, 20.0, 20.0)
    outro_dentro = _retangulo(40.0, 10.0, 20.0, 20.0)

    # O desenho contém todos os lotes
    assert _sugerir(desenho, lote_dentro, outro_dentro) is TipoDespacho.LANCAMENTO_EM_MAIOR_AREA

    # Um lote com metade fora basta para o desenho só intersectar o conjunto
    lote_cortado = _retangulo(90.0, 10.0, 20.0, 20.0)
    assert _sugerir(desenho, lote_dentro, lote_cortado) is TipoDespacho.LANCAMENTO_PARCIAL

    # Lote rente à divisa, com 0,5% da área fora: abaixo da folga, segue contido
    lote_rente = _retangulo(-0.1, 10.0, 20.0, 20.0)
    assert _sugerir(desenho, lote_dentro, lote_rente) is TipoDespacho.LANCAMENTO_EM_MAIOR_AREA

    # Com 2% fora, passa da folga
    lote_alem_da_folga = _retangulo(-0.4, 10.0, 20.0, 20.0)
    assert _sugerir(desenho, lote_dentro, lote_alem_da_folga) is TipoDespacho.LANCAMENTO_PARCIAL
