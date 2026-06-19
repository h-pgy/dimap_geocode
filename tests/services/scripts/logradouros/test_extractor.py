from services.integrations.wfs import WfsFeatureCollection
from services.scripts.logradouros.extractor import NomesLogradourosExtractor
from services.scripts.logradouros.models import NomesLogradourosRequest


def _page(props_list: list[dict[str, object]]) -> WfsFeatureCollection:
    return WfsFeatureCollection.model_validate({
        "type": "FeatureCollection",
        "numberMatched": len(props_list),
        "features": [{"type": "Feature", "properties": p} for p in props_list],
    })


def _req() -> NomesLogradourosRequest:
    return NomesLogradourosRequest(layer_name="v_logradouro_segmento", data_folder=".")


def test_dedups_triples_across_pages() -> None:
    pages = [
        _page([
            {"codlog": "168610", "cd_tipo_logradouro": "PC", "nm_logradouro": "RAMOS DE AZEVEDO"},
            {"codlog": "168610", "cd_tipo_logradouro": "PC", "nm_logradouro": "RAMOS DE AZEVEDO"},
        ]),
        _page([{"codlog": "100000", "cd_tipo_logradouro": "R", "nm_logradouro": "DIREITA"}]),
    ]
    rows = NomesLogradourosExtractor(lambda req: iter(pages))(_req())
    assert len(rows) == 2
    assert rows[0].codlog == "100000"


def test_skips_rows_without_codlog_and_converts_nulls_to_empty_strings() -> None:
    pages = [_page([
        {"codlog": None, "cd_tipo_logradouro": "R", "nm_logradouro": "SEM CODLOG"},
        {"codlog": "200000", "cd_tipo_logradouro": None, "nm_logradouro": None},
    ])]
    rows = NomesLogradourosExtractor(lambda req: iter(pages))(_req())
    assert [r.codlog for r in rows] == ["200000"]
    assert rows[0].cd_tipo_logradouro == "" and rows[0].nm_logradouro == ""


def test_ignores_geometry_when_present() -> None:
    pages = [_page([{
        "codlog": "168610",
        "cd_tipo_logradouro": "PC",
        "nm_logradouro": "RAMOS DE AZEVEDO",
        "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
    }])]
    rows = NomesLogradourosExtractor(lambda req: iter(pages))(_req())
    assert rows[0].nm_logradouro == "RAMOS DE AZEVEDO"
