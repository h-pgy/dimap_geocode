import pytest
from pydantic import ValidationError

from services.integrations.wfs import WfsFeatureCollection
from services.domain.lote_geocod import (
    LoteGeocoder,
    LoteGeocodInput,
    LoteAttributes,
    LoteFeature,
)
from services.domain.geometry import PolygonGeometry

# ---------------------------------------------------------------------------
# LoteGeocodInput — validação e uppercase de tipo_lote
# ---------------------------------------------------------------------------


def test_input_aceita_campos_validos() -> None:
    e = LoteGeocodInput(
        setor="005", quadra="003", lote="0048", tipo_lote="F",
        layer_name="lote_cidadao", output_crs=4326,
    )
    assert e.setor == "005"
    assert e.quadra == "003"
    assert e.lote == "0048"
    assert e.tipo_lote == "F"


def test_input_tipo_lote_minusculo_vira_maiusculo() -> None:
    e = LoteGeocodInput(
        setor="005", quadra="003", lote="0048", tipo_lote="f",
        layer_name="lote_cidadao", output_crs=4326,
    )
    assert e.tipo_lote == "F"


def test_input_tipo_lote_misto_vira_maiusculo() -> None:
    e = LoteGeocodInput(
        setor="005", quadra="003", lote="0048", tipo_lote="Fm",
        layer_name="lote_cidadao", output_crs=4326,
    )
    assert e.tipo_lote == "FM"


def test_input_rejeita_setor_com_2_digitos() -> None:
    with pytest.raises(ValidationError):
        LoteGeocodInput(setor="05", quadra="003", lote="0048", tipo_lote="F",
                        layer_name="l", output_crs=4326)


def test_input_rejeita_setor_com_4_digitos() -> None:
    with pytest.raises(ValidationError):
        LoteGeocodInput(setor="0050", quadra="003", lote="0048", tipo_lote="F",
                        layer_name="l", output_crs=4326)


def test_input_rejeita_setor_com_letra() -> None:
    with pytest.raises(ValidationError):
        LoteGeocodInput(setor="00A", quadra="003", lote="0048", tipo_lote="F",
                        layer_name="l", output_crs=4326)


def test_input_rejeita_quadra_com_2_digitos() -> None:
    with pytest.raises(ValidationError):
        LoteGeocodInput(setor="005", quadra="03", lote="0048", tipo_lote="F",
                        layer_name="l", output_crs=4326)


def test_input_rejeita_lote_com_3_digitos() -> None:
    with pytest.raises(ValidationError):
        LoteGeocodInput(setor="005", quadra="003", lote="048", tipo_lote="F",
                        layer_name="l", output_crs=4326)


def test_input_rejeita_lote_com_5_digitos() -> None:
    with pytest.raises(ValidationError):
        LoteGeocodInput(setor="005", quadra="003", lote="00480", tipo_lote="F",
                        layer_name="l", output_crs=4326)


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

POLYGON_GEOM: dict[str, object] = {
    "type": "Polygon",
    "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
}

MULTIPOLYGON_GEOM: dict[str, object] = {
    "type": "MultiPolygon",
    "coordinates": [
        [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
        [[[2.0, 2.0], [3.0, 2.0], [3.0, 3.0], [2.0, 3.0], [2.0, 2.0]]],
    ],
}

_PROPS_COMPLETAS: dict[str, object] = {
    "cd_identificador": "POL001",
    "cd_setor_fiscal": "005",
    "cd_quadra_fiscal": "003",
    "cd_lote": "0048",
    "cd_tipo_lote": "F",
    "cd_tipo_quadra": "U",
    "cd_condominio": None,
}


def _page(features_raw: list[dict[str, object]]) -> WfsFeatureCollection:
    return WfsFeatureCollection.model_validate({
        "type": "FeatureCollection",
        "numberMatched": len(features_raw),
        "features": features_raw,
    })


def _feat(
    props: dict[str, object],
    geom: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "type": "Feature",
        "geometry": geom if geom is not None else POLYGON_GEOM,
        "properties": props,
    }


def _entrada(
    setor: str = "005",
    quadra: str = "003",
    lote: str = "0048",
    tipo_lote: str = "F",
    output_crs: int = 4326,
) -> LoteGeocodInput:
    return LoteGeocodInput(
        setor=setor,
        quadra=quadra,
        lote=lote,
        tipo_lote=tipo_lote,
        layer_name="lote_cidadao",
        output_crs=output_crs,
    )


def _geocoder(pages: list[WfsFeatureCollection]) -> LoteGeocoder:
    return LoteGeocoder(lambda _req: iter(pages))


# ---------------------------------------------------------------------------
# Tradução de atributos
# ---------------------------------------------------------------------------


def test_traduz_todos_os_atributos_obrigatorios() -> None:
    pages = [_page([_feat(_PROPS_COMPLETAS)])]
    resultado = _geocoder(pages)(_entrada())
    assert len(resultado) == 1
    attrs = resultado[0].attributes
    assert attrs.id_poligono == "POL001"
    assert attrs.setor == "005"
    assert attrs.quadra == "003"
    assert attrs.lote == "0048"
    assert attrs.tipo_lote == "F"


def test_traduz_atributos_opcionais_presentes() -> None:
    pages = [_page([_feat(_PROPS_COMPLETAS)])]
    attrs = _geocoder(pages)(_entrada())[0].attributes
    assert attrs.tipo_quadra == "U"
    assert attrs.condominio is None


def test_opcional_tipo_quadra_ausente_fica_none() -> None:
    props = {k: v for k, v in _PROPS_COMPLETAS.items() if k != "cd_tipo_quadra"}
    pages = [_page([_feat(props)])]
    attrs = _geocoder(pages)(_entrada())[0].attributes
    assert attrs.tipo_quadra is None


def test_opcional_condominio_preenchido() -> None:
    props: dict[str, object] = {**_PROPS_COMPLETAS, "cd_condominio": "COND001"}
    pages = [_page([_feat(props)])]
    attrs = _geocoder(pages)(_entrada())[0].attributes
    assert attrs.condominio == "COND001"


# ---------------------------------------------------------------------------
# Envelope: geometry + crs
# ---------------------------------------------------------------------------


def test_geometry_e_polygongeometry() -> None:
    pages = [_page([_feat(_PROPS_COMPLETAS)])]
    resultado = _geocoder(pages)(_entrada())
    assert isinstance(resultado[0].geometry, PolygonGeometry)
    assert resultado[0].geometry.type == "Polygon"


def test_aceita_multipolygon() -> None:
    pages = [_page([_feat(_PROPS_COMPLETAS, geom=MULTIPOLYGON_GEOM)])]
    resultado = _geocoder(pages)(_entrada())
    assert len(resultado) == 1
    assert resultado[0].geometry.type == "MultiPolygon"


def test_crs_ecoa_output_crs_injetado() -> None:
    pages = [_page([_feat(_PROPS_COMPLETAS)])]
    resultado = _geocoder(pages)(_entrada(output_crs=31983))
    assert resultado[0].crs == 31983


def test_resultado_e_lote_feature() -> None:
    pages = [_page([_feat(_PROPS_COMPLETAS)])]
    resultado = _geocoder(pages)(_entrada())
    assert isinstance(resultado[0], LoteFeature)  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Múltiplas feições / paginação
# ---------------------------------------------------------------------------


def test_retorna_todas_as_feicoes_sem_dedup() -> None:
    f1 = _feat({**_PROPS_COMPLETAS, "cd_identificador": "POL001"})
    f2 = _feat({**_PROPS_COMPLETAS, "cd_identificador": "POL002"})
    f3 = _feat({**_PROPS_COMPLETAS, "cd_identificador": "POL003"})
    pages = [_page([f1, f2]), _page([f3])]
    resultado = _geocoder(pages)(_entrada())
    assert len(resultado) == 3
    ids = {r.attributes.id_poligono for r in resultado}
    assert ids == {"POL001", "POL002", "POL003"}


def test_feicoes_duplicadas_sao_retornadas_sem_dedup() -> None:
    feat = _feat(_PROPS_COMPLETAS)
    pages = [_page([feat, feat])]
    resultado = _geocoder(pages)(_entrada())
    assert len(resultado) == 2


# ---------------------------------------------------------------------------
# Descarte de feições inválidas
# ---------------------------------------------------------------------------


def test_descarta_feicao_sem_geometria() -> None:
    feat: dict[str, object] = {"type": "Feature", "geometry": None, "properties": _PROPS_COMPLETAS}
    pages = [_page([feat])]
    assert _geocoder(pages)(_entrada()) == []


def test_descarta_feicao_sem_id_poligono() -> None:
    props = {k: v for k, v in _PROPS_COMPLETAS.items() if k != "cd_identificador"}
    pages = [_page([_feat(props)])]
    assert _geocoder(pages)(_entrada()) == []


def test_descarta_feicao_sem_setor() -> None:
    props = {k: v for k, v in _PROPS_COMPLETAS.items() if k != "cd_setor_fiscal"}
    pages = [_page([_feat(props)])]
    assert _geocoder(pages)(_entrada()) == []


def test_descarta_feicao_sem_quadra() -> None:
    props = {k: v for k, v in _PROPS_COMPLETAS.items() if k != "cd_quadra_fiscal"}
    pages = [_page([_feat(props)])]
    assert _geocoder(pages)(_entrada()) == []


def test_descarta_feicao_sem_lote() -> None:
    props = {k: v for k, v in _PROPS_COMPLETAS.items() if k != "cd_lote"}
    pages = [_page([_feat(props)])]
    assert _geocoder(pages)(_entrada()) == []


def test_descarta_feicao_sem_tipo_lote() -> None:
    props = {k: v for k, v in _PROPS_COMPLETAS.items() if k != "cd_tipo_lote"}
    pages = [_page([_feat(props)])]
    assert _geocoder(pages)(_entrada()) == []


def test_descarta_geometria_nao_poligono() -> None:
    geom_linha: dict[str, object] = {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}
    pages = [_page([_feat(_PROPS_COMPLETAS, geom=geom_linha)])]
    assert _geocoder(pages)(_entrada()) == []


def test_descarta_poligono_com_anel_aberto() -> None:
    geom_invalida: dict[str, object] = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]],  # anel aberto
    }
    pages = [_page([_feat(_PROPS_COMPLETAS, geom=geom_invalida)])]
    assert _geocoder(pages)(_entrada()) == []


def test_valida_e_invalida_na_mesma_pagina() -> None:
    valida = _feat(_PROPS_COMPLETAS)
    invalida: dict[str, object] = {"type": "Feature", "geometry": None, "properties": _PROPS_COMPLETAS}
    pages = [_page([valida, invalida])]
    assert len(_geocoder(pages)(_entrada())) == 1


# ---------------------------------------------------------------------------
# WfsFeatureRequest montado
# ---------------------------------------------------------------------------


def test_request_cql_filter_tem_quatro_predicados_and() -> None:
    capturado: list[object] = []

    def fake_fetcher(req: object) -> list[WfsFeatureCollection]:
        capturado.append(req)
        return []

    _geocoder.__class__  # só para confirmar o tipo
    LoteGeocoder(fake_fetcher)(_entrada(
        setor="005", quadra="003", lote="0048", tipo_lote="F"
    ))
    req = capturado[0]
    assert hasattr(req, "cql_filter")
    cql = req.cql_filter.to_cql()  # type: ignore[union-attr]
    assert "cd_setor_fiscal" in cql
    assert "'005'" in cql
    assert "cd_quadra_fiscal" in cql
    assert "'003'" in cql
    assert "cd_lote" in cql
    assert "'0048'" in cql
    assert "cd_tipo_lote" in cql
    assert "'F'" in cql
    assert cql.count(" AND ") == 3


def test_request_srs_name_derivado_do_output_crs() -> None:
    capturado: list[object] = []

    def fake_fetcher(req: object) -> list[WfsFeatureCollection]:
        capturado.append(req)
        return []

    LoteGeocoder(fake_fetcher)(_entrada(output_crs=4326))
    assert capturado[0].srs_name == "EPSG:4326"  # type: ignore[attr-defined]


def test_request_srs_name_outro_crs() -> None:
    capturado: list[object] = []

    def fake_fetcher(req: object) -> list[WfsFeatureCollection]:
        capturado.append(req)
        return []

    LoteGeocoder(fake_fetcher)(_entrada(output_crs=31983))
    assert capturado[0].srs_name == "EPSG:31983"  # type: ignore[attr-defined]


def test_request_nome_camada_vem_da_entrada() -> None:
    capturado: list[object] = []

    def fake_fetcher(req: object) -> list[WfsFeatureCollection]:
        capturado.append(req)
        return []

    entrada = LoteGeocodInput(
        setor="005", quadra="003", lote="0048", tipo_lote="F",
        layer_name="camada_especial", output_crs=4326,
    )
    LoteGeocoder(fake_fetcher)(entrada)
    assert capturado[0].nome_camada == "camada_especial"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Integração — WFS GeoSampa real
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIntegracaoGeoSampa:
    """Testa o geocoder de lote contra o WFS real do GeoSampa.
    Execute com: pytest -m integration
    """

    def _build_geocoder(self) -> LoteGeocoder:
        from services.integrations.wfs import WfsConnectionConfig, WfsFetcher

        config = WfsConnectionConfig(
            domain="wfs.geosampa.prefeitura.sp.gov.br",
            endpoint="geoserver/geoportal/wfs",
            namespace="geoportal",
        )
        return LoteGeocoder(WfsFetcher(config))

    def _entrada_real(self, output_crs: int = 4326) -> LoteGeocodInput:
        return LoteGeocodInput(
            setor="005",
            quadra="003",
            lote="0048",
            tipo_lote="F",
            layer_name="lote_cidadao",
            output_crs=output_crs,
        )

    def test_retorna_pelo_menos_uma_feicao(self) -> None:
        resultado = self._build_geocoder()(self._entrada_real())
        assert len(resultado) >= 1, "Lote 005/003/0048/F deve retornar ao menos uma feição"

    def test_atributos_obrigatorios_preenchidos(self) -> None:
        resultado = self._build_geocoder()(self._entrada_real())
        for r in resultado:
            assert r.attributes.id_poligono
            assert r.attributes.setor
            assert r.attributes.quadra
            assert r.attributes.lote
            assert r.attributes.tipo_lote

    def test_numeracao_corresponde_ao_input(self) -> None:
        resultado = self._build_geocoder()(self._entrada_real())
        for r in resultado:
            assert r.attributes.setor == "005"
            assert r.attributes.quadra == "003"
            assert r.attributes.lote == "0048"
            assert r.attributes.tipo_lote == "F"

    def test_geometry_e_poligono(self) -> None:
        resultado = self._build_geocoder()(self._entrada_real())
        for r in resultado:
            assert isinstance(r.geometry, PolygonGeometry)
            assert r.geometry.type in ("Polygon", "MultiPolygon")

    def test_crs_4326(self) -> None:
        resultado = self._build_geocoder()(self._entrada_real())
        assert all(r.crs == 4326 for r in resultado)

    def test_tipo_lote_minusculo_e_normalizado(self) -> None:
        """Garante que 'f' minúsculo é convertido para 'F' e a consulta funciona."""
        entrada = LoteGeocodInput(
            setor="005", quadra="003", lote="0048", tipo_lote="f",
            layer_name="lote_cidadao", output_crs=4326,
        )
        resultado = self._build_geocoder()(entrada)
        assert len(resultado) >= 1

    def test_lote_inexistente_retorna_lista_vazia(self) -> None:
        entrada = LoteGeocodInput(
            setor="999", quadra="999", lote="9999", tipo_lote="F",
            layer_name="lote_cidadao", output_crs=4326,
        )
        resultado = self._build_geocoder()(entrada)
        assert resultado == []
