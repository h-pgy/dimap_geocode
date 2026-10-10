from services.domain.desenho import Desenho
from services.domain.geometry import PolygonGeometry, reprojetar
from services.domain.lote_geocod import LoteAttributes, LoteFeature
from services.domain.lotes_mais_proximos import (
    BuscarLotesDoDesenho,
    CamadaLotes,
    ConjuntoDeLotes,
    EsvaziarConjunto,
    LotesDoDesenho,
    LotesDoDesenhoInput,
    ReleituraDoConjuntoInput,
    RelerConjunto,
    RemocaoDoConjuntoInput,
    RemoverDoConjunto,
)
from services.integrations.wfs import WfsFeatureCollection, WfsFeatureRequest

CRS_MAPA = 4326
CRS_METRICO = 31983
X0_UTM = 333000.0
Y0_UTM = 7395000.0
AREA_MAXIMA_M2 = 250_000.0

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


# ---------------------------------------------------------------------------
# Reler: builders
# ---------------------------------------------------------------------------


def _retangulo_no_mapa(x0: float, largura: float, altura: float) -> PolygonGeometry:
    anel = [
        [x0, Y0_UTM],
        [x0 + largura, Y0_UTM],
        [x0 + largura, Y0_UTM + altura],
        [x0, Y0_UTM + altura],
        [x0, Y0_UTM],
    ]
    metrico = PolygonGeometry(type="Polygon", coordinates=[anel])
    return reprojetar(metrico, CRS_METRICO, CRS_MAPA)


def _camada() -> CamadaLotes:
    return CamadaLotes(
        nome="lote_cidadao",
        campo_geometria="ge_poligono",
        crs_camada=CRS_METRICO,
        crs_saida=CRS_MAPA,
    )


def _feicao(id_poligono: str, logradouro: str = "RUA AUGUSTA") -> dict[str, object]:
    return {
        "type": "Feature",
        "geometry": _retangulo_no_mapa(X0_UTM, 10.0, 10.0).model_dump(),
        "properties": {
            "cd_identificador": id_poligono,
            "cd_setor_fiscal": "005",
            "cd_quadra_fiscal": "003",
            "cd_lote": "0048",
            "cd_tipo_lote": "F",
            "nm_logradouro_completo": logradouro,
        },
    }


def _pagina(feicoes: list[dict[str, object]]) -> WfsFeatureCollection:
    return WfsFeatureCollection.model_validate(
        {"type": "FeatureCollection", "numberMatched": len(feicoes), "features": feicoes}
    )


def _lotes_do_desenho_input(desenho: Desenho) -> LotesDoDesenhoInput:
    return LotesDoDesenhoInput(
        desenho=desenho,
        crs_mapa=CRS_MAPA,
        camada=_camada(),
        area_maxima_m2=AREA_MAXIMA_M2,
    )


def _conjunto_consultado(
    feicoes: list[dict[str, object]],
    removidos: frozenset[str],
) -> ConjuntoDeLotes:
    desenho = Desenho(id_bancada="7", geometria=_retangulo_no_mapa(X0_UTM, 100.0, 50.0))
    buscar_lotes = BuscarLotesDoDesenho(lambda _req: iter([_pagina(feicoes)]))
    apurado = buscar_lotes(_lotes_do_desenho_input(desenho))
    return ConjuntoDeLotes(apurado=apurado, removidos=removidos)


# ---------------------------------------------------------------------------
# Reler
# ---------------------------------------------------------------------------


def test_reler_conjunto_mantem_so_os_escolhidos() -> None:
    # A pessoa consultou três lotes e tirou o 3: escolheu o 1 e o 2
    conjunto = _conjunto_consultado(
        [_feicao("1"), _feicao("2"), _feicao("3")],
        removidos=frozenset({"3"}),
    )
    # Hoje a camada mudou o endereço do 1, perdeu o 2 e ganhou o 4 sob o mesmo desenho
    consultas: list[WfsFeatureRequest] = []

    def geosampa_de_hoje(req: WfsFeatureRequest) -> list[WfsFeatureCollection]:
        consultas.append(req)
        return [_pagina([_feicao("1", logradouro="RUA NOVA"), _feicao("3"), _feicao("4")])]

    reler = RelerConjunto(BuscarLotesDoDesenho(geosampa_de_hoje))

    relido = reler(
        ReleituraDoConjuntoInput(
            conjunto=conjunto,
            crs_mapa=CRS_MAPA,
            camada=_camada(),
            area_maxima_m2=AREA_MAXIMA_M2,
        )
    )

    # Uma consulta só, a mesma INTERSECTS sobre o desenho guardado
    assert len(consultas) == 1
    assert consultas[0].cql_filter.to_cql().startswith("INTERSECTS(ge_poligono, POLYGON((")  # type: ignore[union-attr]
    assert relido.apurado.desenho == conjunto.apurado.desenho

    # Do que foi escolhido, volta só o que a camada ainda tem — com os atributos de hoje
    assert _ids(relido) == ["1"]
    assert relido.lotes[0].attributes.nome_logradouro == "RUA NOVA"
    # O que o desenho cruza hoje e não foi escolhido fica de fora: o tirado e o que apareceu depois
    assert relido.removidos == frozenset({"3", "4"})
