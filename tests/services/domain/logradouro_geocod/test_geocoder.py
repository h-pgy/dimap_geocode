import pytest
from pydantic import ValidationError

from services.integrations.wfs import WfsFeatureCollection
from services.domain.logradouro_geocod import (
    LogradouroGeocoder,
    LogradouroGeocodInput,
    SegmentoLogradouroAttributes,
    SegmentoLogradouroFeature,
)
from services.domain.geometry import LineGeometry

# ---------------------------------------------------------------------------
# LogradouroGeocodInput — validação e campo calculado
# ---------------------------------------------------------------------------


def test_input_aceita_6_digitos() -> None:
    e = LogradouroGeocodInput(codlog="156566", layer_name="l", output_crs=4326)
    assert e.codlog == "156566"
    assert e.codlog_int == 156566


def test_input_rejeita_5_digitos() -> None:
    with pytest.raises(ValidationError):
        LogradouroGeocodInput(codlog="15656", layer_name="l", output_crs=4326)


def test_input_rejeita_7_digitos() -> None:
    with pytest.raises(ValidationError):
        LogradouroGeocodInput(codlog="1565660", layer_name="l", output_crs=4326)


def test_input_rejeita_letras() -> None:
    with pytest.raises(ValidationError):
        LogradouroGeocodInput(codlog="15656X", layer_name="l", output_crs=4326)


def test_input_rejeita_vazio() -> None:
    with pytest.raises(ValidationError):
        LogradouroGeocodInput(codlog="", layer_name="l", output_crs=4326)

# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

LINESTRING_GEOM = {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}

_PROPS_COMPLETAS: dict[str, object] = {
    "cd_identificador": "SEG001",
    "codlog": 156566,
    "cd_tipo_logradouro": "AV",
    "nm_logradouro": "PAULISTA",
    "cd_titulo_logradouro": "DR",
    "tx_preposicao_logradouro": "DE",
    "cd_numero_inicial_par": "2",
    "cd_numero_final_par": "610",
    "cd_numero_inicial_impar": "1",
    "cd_numero_final_impar": "609",
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
        "geometry": geom if geom is not None else LINESTRING_GEOM,
        "properties": props,
    }


def _entrada(codlog: str = "156566", output_crs: int = 4326) -> LogradouroGeocodInput:
    return LogradouroGeocodInput(
        codlog=codlog,
        layer_name="segmento_logradouro",
        output_crs=output_crs,
    )


def _geocoder(pages: list[WfsFeatureCollection]) -> LogradouroGeocoder:
    return LogradouroGeocoder(lambda _req: iter(pages))


# ---------------------------------------------------------------------------
# Tradução de atributos
# ---------------------------------------------------------------------------


def test_traduz_todos_os_atributos_obrigatorios() -> None:
    pages = [_page([_feat(_PROPS_COMPLETAS)])]
    resultado = _geocoder(pages)(_entrada())
    assert len(resultado) == 1
    attrs = resultado[0].attributes
    assert attrs.id_segmento == "SEG001"
    assert attrs.codlog == "156566"
    assert attrs.cd_tipo_logradouro == "AV"
    assert attrs.nome_logradouro == "PAULISTA"


def test_traduz_atributos_opcionais_de_texto() -> None:
    pages = [_page([_feat(_PROPS_COMPLETAS)])]
    attrs = _geocoder(pages)(_entrada())[0].attributes
    assert attrs.titulo == "DR"
    assert attrs.preposicao == "DE"


def test_traduz_numeracao_para_int() -> None:
    pages = [_page([_feat(_PROPS_COMPLETAS)])]
    attrs = _geocoder(pages)(_entrada())[0].attributes
    assert attrs.numero_inicial_par == 2
    assert attrs.numero_final_par == 610
    assert attrs.numero_inicial_impar == 1
    assert attrs.numero_final_impar == 609


def test_numeracao_none_permanece_none() -> None:
    props: dict[str, object] = {**_PROPS_COMPLETAS, "cd_numero_inicial_par": None}
    pages = [_page([_feat(props)])]
    attrs = _geocoder(pages)(_entrada())[0].attributes
    assert attrs.numero_inicial_par is None


def test_numeracao_string_vazia_vira_none() -> None:
    props: dict[str, object] = {**_PROPS_COMPLETAS, "cd_numero_final_par": ""}
    pages = [_page([_feat(props)])]
    attrs = _geocoder(pages)(_entrada())[0].attributes
    assert attrs.numero_final_par is None


def test_titulo_ausente_fica_none() -> None:
    props = {k: v for k, v in _PROPS_COMPLETAS.items() if k != "cd_titulo_logradouro"}
    pages = [_page([_feat(props)])]
    attrs = _geocoder(pages)(_entrada())[0].attributes
    assert attrs.titulo is None


# ---------------------------------------------------------------------------
# Envelope: geometry + crs
# ---------------------------------------------------------------------------


def test_geometry_e_linegeometry() -> None:
    pages = [_page([_feat(_PROPS_COMPLETAS)])]
    resultado = _geocoder(pages)(_entrada())
    assert isinstance(resultado[0].geometry, LineGeometry)
    assert resultado[0].geometry.type == "LineString"


def test_crs_ecoa_output_crs_injetado() -> None:
    pages = [_page([_feat(_PROPS_COMPLETAS)])]
    resultado = _geocoder(pages)(_entrada(output_crs=31983))
    assert resultado[0].crs == 31983


def test_resultado_e_segmento_logradouro_feature() -> None:
    pages = [_page([_feat(_PROPS_COMPLETAS)])]
    resultado = _geocoder(pages)(_entrada())
    assert isinstance(resultado[0], SegmentoLogradouroFeature)


# ---------------------------------------------------------------------------
# Múltiplos segmentos / paginação
# ---------------------------------------------------------------------------


def test_retorna_todos_os_segmentos_de_um_codlog() -> None:
    seg1 = _feat({**_PROPS_COMPLETAS, "cd_identificador": "SEG001"})
    seg2 = _feat({**_PROPS_COMPLETAS, "cd_identificador": "SEG002"})
    seg3 = _feat({**_PROPS_COMPLETAS, "cd_identificador": "SEG003"})
    pages = [_page([seg1, seg2]), _page([seg3])]
    resultado = _geocoder(pages)(_entrada())
    assert len(resultado) == 3
    ids = {r.attributes.id_segmento for r in resultado}
    assert ids == {"SEG001", "SEG002", "SEG003"}


def test_sem_deduplicacao_de_segmentos() -> None:
    feat = _feat(_PROPS_COMPLETAS)
    pages = [_page([feat, feat])]
    resultado = _geocoder(pages)(_entrada())
    assert len(resultado) == 2


# ---------------------------------------------------------------------------
# Descarte de feições inválidas
# ---------------------------------------------------------------------------


def test_descarta_feicao_sem_geometria() -> None:
    feat_sem_geom: dict[str, object] = {"type": "Feature", "geometry": None, "properties": _PROPS_COMPLETAS}
    pages = [_page([feat_sem_geom])]
    assert _geocoder(pages)(_entrada()) == []


def test_descarta_feicao_sem_id_segmento() -> None:
    props = {k: v for k, v in _PROPS_COMPLETAS.items() if k != "cd_identificador"}
    pages = [_page([_feat(props)])]
    assert _geocoder(pages)(_entrada()) == []


def test_descarta_feicao_sem_codlog() -> None:
    props = {k: v for k, v in _PROPS_COMPLETAS.items() if k != "codlog"}
    pages = [_page([_feat(props)])]
    assert _geocoder(pages)(_entrada()) == []


def test_descarta_feicao_sem_tipo_logradouro() -> None:
    props = {k: v for k, v in _PROPS_COMPLETAS.items() if k != "cd_tipo_logradouro"}
    pages = [_page([_feat(props)])]
    assert _geocoder(pages)(_entrada()) == []


def test_descarta_feicao_sem_nome_logradouro() -> None:
    props = {k: v for k, v in _PROPS_COMPLETAS.items() if k != "nm_logradouro"}
    pages = [_page([_feat(props)])]
    assert _geocoder(pages)(_entrada()) == []


def test_descarta_geometria_nao_linha() -> None:
    geom_ponto = {"type": "Point", "coordinates": [0.0, 0.0]}
    pages = [_page([_feat(_PROPS_COMPLETAS, geom=geom_ponto)])]
    assert _geocoder(pages)(_entrada()) == []


def test_descarta_linestring_com_um_ponto() -> None:
    geom_invalida = {"type": "LineString", "coordinates": [[0.0, 0.0]]}
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


def test_request_usa_cql_eq_com_codlog() -> None:
    capturado: list[object] = []

    def fake_fetcher(req: object) -> list[WfsFeatureCollection]:
        capturado.append(req)
        return []

    LogradouroGeocoder(fake_fetcher)(_entrada(codlog="156566"))
    assert len(capturado) == 1
    req = capturado[0]
    assert hasattr(req, "cql_filter")
    assert req.cql_filter is not None
    cql = req.cql_filter.to_cql()
    assert "156566" in cql
    assert "codlog" in cql
    # codlog é inteiro no GeoSampa → sem aspas no CQL
    assert "'156566'" not in cql


def test_request_srs_name_derivado_do_output_crs() -> None:
    capturado: list[object] = []

    def fake_fetcher(req: object) -> list[WfsFeatureCollection]:
        capturado.append(req)
        return []

    LogradouroGeocoder(fake_fetcher)(_entrada(output_crs=4326))
    assert capturado[0].srs_name == "EPSG:4326"  # type: ignore[attr-defined]


def test_request_srs_name_outro_crs() -> None:
    capturado: list[object] = []

    def fake_fetcher(req: object) -> list[WfsFeatureCollection]:
        capturado.append(req)
        return []

    LogradouroGeocoder(fake_fetcher)(_entrada(output_crs=31983))
    assert capturado[0].srs_name == "EPSG:31983"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Integração — WFS GeoSampa real
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIntegracaoGeoSampa:
    """Testa o geocoder contra o WFS real do GeoSampa.
    Execute com: pytest -m integration
    """

    def _build_geocoder(self) -> LogradouroGeocoder:
        from services.integrations.wfs import WfsConnectionConfig, WfsFetcher

        config = WfsConnectionConfig(
            domain="wfs.geosampa.prefeitura.sp.gov.br",
            endpoint="geoserver/geoportal/wfs",
            namespace="geoportal",
        )
        return LogradouroGeocoder(WfsFetcher(config))

    def test_paulista_retorna_multiplos_segmentos(self) -> None:
        geocoder = self._build_geocoder()
        resultado = geocoder(LogradouroGeocodInput(
            codlog="156566",
            layer_name="segmento_logradouro",
            output_crs=4326,
        ))
        assert len(resultado) > 1, "Av. Paulista deve ter mais de um segmento"

    def test_paulista_todos_com_codlog_correto(self) -> None:
        geocoder = self._build_geocoder()
        resultado = geocoder(LogradouroGeocodInput(
            codlog="156566",
            layer_name="segmento_logradouro",
            output_crs=4326,
        ))
        assert all(r.attributes.codlog == "156566" for r in resultado)

    def test_paulista_geometria_e_linestring(self) -> None:
        geocoder = self._build_geocoder()
        resultado = geocoder(LogradouroGeocodInput(
            codlog="156566",
            layer_name="segmento_logradouro",
            output_crs=4326,
        ))
        assert all(isinstance(r.geometry, LineGeometry) for r in resultado)

    def test_paulista_crs_4326(self) -> None:
        geocoder = self._build_geocoder()
        resultado = geocoder(LogradouroGeocodInput(
            codlog="156566",
            layer_name="segmento_logradouro",
            output_crs=4326,
        ))
        assert all(r.crs == 4326 for r in resultado)

    def test_paulista_atributos_obrigatorios_preenchidos(self) -> None:
        geocoder = self._build_geocoder()
        resultado = geocoder(LogradouroGeocodInput(
            codlog="156566",
            layer_name="segmento_logradouro",
            output_crs=4326,
        ))
        for r in resultado:
            assert r.attributes.id_segmento
            assert r.attributes.codlog
            assert r.attributes.cd_tipo_logradouro
            assert r.attributes.nome_logradouro

    def test_codlog_inexistente_retorna_lista_vazia(self) -> None:
        geocoder = self._build_geocoder()
        resultado = geocoder(LogradouroGeocodInput(
            codlog="000000",
            layer_name="segmento_logradouro",
            output_crs=4326,
        ))
        assert resultado == []
