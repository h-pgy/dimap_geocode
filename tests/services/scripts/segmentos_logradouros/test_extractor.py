from services.integrations.wfs import WfsFeatureCollection
from services.scripts.segmentos_logradouros.extractor import SegmentosLogradourosExtractor
from services.scripts.segmentos_logradouros.models import SegmentosLogradourosRequest


def _page(props_list: list[dict[str, object]]) -> WfsFeatureCollection:
    return WfsFeatureCollection.model_validate({
        "type": "FeatureCollection",
        "numberMatched": len(props_list),
        "features": [{"type": "Feature", "properties": p} for p in props_list],
    })


def _req() -> SegmentosLogradourosRequest:
    return SegmentosLogradourosRequest(layer_name="v_logradouro_segmento")


def test_extracts_segments_and_keeps_nulls() -> None:
    pages = [_page([{
        "codlog": "168610",
        "cd_identificador": 57088,
        "cd_numero_inicial_par": None,
        "cd_numero_final_par": None,
        "cd_numero_inicial_impar": 81,
        "cd_numero_final_impar": 181,
    }])]
    rows = SegmentosLogradourosExtractor(lambda req: iter(pages))(_req())
    assert len(rows) == 1
    assert rows[0].codlog == "168610"
    assert rows[0].cd_identificador == "57088"
    assert rows[0].cd_numero_inicial_par is None
    assert rows[0].cd_numero_final_par is None
    assert rows[0].cd_numero_inicial_impar == "81"
    assert rows[0].cd_numero_final_impar == "181"


def test_ignores_records_with_missing_mandatory_keys() -> None:
    pages = [_page([
        {"codlog": None, "cd_identificador": 1234},
        {"codlog": "300000", "cd_identificador": None},
    ])]
    rows = SegmentosLogradourosExtractor(lambda req: iter(pages))(_req())
    assert len(rows) == 0


def test_accumulates_without_deduplication() -> None:
    pages = [
        _page([{"codlog": "168610", "cd_identificador": 57088}]),
        _page([{"codlog": "168610", "cd_identificador": 57088}]),
    ]
    rows = SegmentosLogradourosExtractor(lambda req: iter(pages))(_req())
    assert len(rows) == 2
