from services.integrations.wfs import WfsFeatureCollection
from services.scripts.enderecos_fiscais.extractor import EnderecosFiscaisExtractor
from services.scripts.enderecos_fiscais.models import EnderecosFiscaisRequest


def _page(props_list: list[dict[str, object]]) -> WfsFeatureCollection:
    return WfsFeatureCollection.model_validate({
        "type": "FeatureCollection",
        "numberMatched": len(props_list),
        "features": [{"type": "Feature", "properties": p} for p in props_list],
    })


def _req() -> EnderecosFiscaisRequest:
    return EnderecosFiscaisRequest(layer_name="lote_cidadao")


def test_extracts_addresses_and_keeps_nulls() -> None:
    pages = [_page([{
        "cd_identificador": "57088",
        "nm_logradouro_completo": "RAMOS DE AZEVEDO",
        "cd_numero_porta": "81",
        "tx_complemento_endereco": None,
    }])]
    rows = EnderecosFiscaisExtractor(lambda req: iter(pages))(_req())
    assert len(rows) == 1
    assert rows[0].cd_identificador == "57088"
    assert rows[0].nm_logradouro_completo == "RAMOS DE AZEVEDO"
    assert rows[0].tx_complemento_endereco is None


def test_ignores_records_without_cd_identificador() -> None:
    pages = [_page([
        {"cd_identificador": None, "nm_logradouro_completo": "RUA A"},
        {"cd_identificador": "57089", "nm_logradouro_completo": "RUA B"},
    ])]
    rows = EnderecosFiscaisExtractor(lambda req: iter(pages))(_req())
    assert len(rows) == 1
    assert rows[0].cd_identificador == "57089"


def test_accumulates_across_pages() -> None:
    pages = [
        _page([{"cd_identificador": "57088"}]),
        _page([{"cd_identificador": "57089"}]),
    ]
    rows = EnderecosFiscaisExtractor(lambda req: iter(pages))(_req())
    assert len(rows) == 2
