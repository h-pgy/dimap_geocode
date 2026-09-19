from services.domain.desenho import Desenho
from services.domain.geometry import PolygonGeometry
from services.domain.lote_geocod import LoteAttributes, LoteFeature
from services.domain.lotes_mais_proximos import (
    ConjuntoDeLotes,
    EsvaziarConjunto,
    LotesDoDesenho,
    RemocaoDoConjuntoInput,
    RemoverDoConjunto,
)

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _poligono() -> PolygonGeometry:
    anel = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]
    return PolygonGeometry(type="Polygon", coordinates=[anel])


def _lote(id_poligono: str) -> LoteFeature:
    return LoteFeature(
        geometry=_poligono(),
        attributes=LoteAttributes(
            id_poligono=id_poligono,
            setor="005",
            quadra="003",
            lote="0048",
            tipo_lote="F",
        ),
        crs=4326,
    )


def _conjunto(*ids: str) -> ConjuntoDeLotes:
    apurado = LotesDoDesenho(
        desenho=Desenho(id_bancada="7", geometria=_poligono()),
        area_m2=1000.0,
        lotes=tuple(_lote(id_poligono) for id_poligono in ids),
    )
    return ConjuntoDeLotes(apurado=apurado)


def _ids(conjunto: ConjuntoDeLotes) -> list[str]:
    return [lote.attributes.id_poligono for lote in conjunto.lotes]


# ---------------------------------------------------------------------------
# Remover
# ---------------------------------------------------------------------------


def test_remover_tira_o_lote_e_mantem_a_ordem() -> None:
    entrada = RemocaoDoConjuntoInput(conjunto=_conjunto("1", "2", "3"), id_poligono="2")

    revisado = RemoverDoConjunto()(entrada)

    assert _ids(revisado) == ["1", "3"]
    assert revisado.removidos == frozenset({"2"})


def test_remover_id_de_fora_do_conjunto_nao_muda_nada() -> None:
    conjunto = _conjunto("1", "2")

    revisado = RemoverDoConjunto()(RemocaoDoConjuntoInput(conjunto=conjunto, id_poligono="99"))

    assert revisado == conjunto


# ---------------------------------------------------------------------------
# Esvaziar
# ---------------------------------------------------------------------------


def test_esvaziar_tira_todos_e_preserva_o_apurado() -> None:
    conjunto = _conjunto("1", "2")

    esvaziado = EsvaziarConjunto()(conjunto)

    assert esvaziado.lotes == ()
    assert esvaziado.removidos == frozenset({"1", "2"})
    assert len(esvaziado.apurado.lotes) == 2
