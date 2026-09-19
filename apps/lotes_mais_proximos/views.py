import json
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST
from pydantic import BaseModel, field_validator

from apps.lotes_mais_proximos.contexto import camada_lotes, contexto_lotes_do_desenho
from apps.mapping.context import contexto_aviso, contexto_mapa
from services.domain.desenho import Desenho
from services.domain.geometry import (
    GeoFeature,
    PointGeometry,
    PolygonGeometry,
    to_geojson_feature_collection,
)
from services.domain.geometry.models import GeoJsonProperties
from services.domain.lote_geocod import (
    GavetaLoteInput,
    LotePorIdentificador,
    LotePorIdentificadorInput,
    MontarGavetaLote,
)
from services.domain.lotes_mais_proximos import (
    BuscarLotesDoDesenho,
    DesenhoGrandeDemaisError,
    DesenhoInvalidoError,
    LoteMaisProximo,
    LoteMaisProximoInput,
    LoteProximo,
    LotesDoDesenhoInput,
    NenhumLoteProximoError,
)
from services.integrations.wfs import build_fetcher

MAP_COR_PONTO: str = settings.MAP_COR_PONTO
MAP_COR_POLIGONO: str = settings.MAP_COR_POLIGONO
MAP_COR_POLIGONO_CONDOMINIO: str = settings.MAP_COR_POLIGONO_CONDOMINIO
MAP_INTERPOLATION_CRS: int = settings.MAP_INTERPOLATION_CRS
MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
LOTE_MAIS_PROXIMO_RAIO_M: float = settings.LOTE_MAIS_PROXIMO_RAIO_M
LOTES_DESENHO_AREA_MAXIMA_M2: float = settings.LOTES_DESENHO_AREA_MAXIMA_M2
WFS_LAYER_LOTE_CIDADAO: str = settings.WFS_LAYER_LOTE_CIDADAO

TEMPLATE_RESULTADO_MAIS_PROXIMO = "lotes_mais_proximos/partials/_resultado_mais_proximo.html"
TEMPLATE_RESULTADO_DESENHO = "lotes_mais_proximos/partials/_resultado_desenho.html"
TEMPLATE_RECUSA_ACAO = "mapping/_recusa_acao.html"
TEMPLATE_GAVETA_LOTE = "lote_geocoder/partials/_gaveta_lote.html"

MSG_LOTE_NAO_ENCONTRADO = "O lote não foi encontrado no cadastro: ele pode ter saído da base."

# O raio sai da mesma constante que alimentou a consulta; a exceção não precisa carregá-lo de volta.
MSG_SEM_LOTE_PROXIMO = (
    "Nenhum lote situado neste logradouro foi encontrado "
    "a {raio_m:.0f} metros do ponto de busca."
)


class ConsultaLoteMaisProximo(BaseModel):
    """O formulário da gaveta. lon/lat malformados morrem no PydanticValidationMiddleware."""

    lon: float
    lat: float
    codlog: str
    # Rótulo do endereço de origem, só para a gaveta ler — como `score`, é apresentação.
    origem: str = ""


class ConsultaLotesDoDesenho(BaseModel):
    """O formulário da gaveta: o único radio marcado e a geometria que o envio.js enxertou."""

    id_bancada: str
    desenho: PolygonGeometry

    @field_validator("desenho", mode="before")
    @classmethod
    def _do_json(cls, valor: object) -> object:
        # Sem o envio.js o campo não chega: vira ValidationError e cai no middleware.
        return json.loads(valor) if isinstance(valor, str) else valor


def _properties_lote(f: GeoFeature[Any, Any]) -> GeoJsonProperties:
    cor_condominio = (
        MAP_COR_POLIGONO_CONDOMINIO if getattr(f.attributes, "is_condominio", False) else None
    )
    return GeoJsonProperties(
        popup_html=render_to_string(
            "lote_geocoder/partials/_popup_lote.html", {"a": f.attributes}
        ),
        rotulo=f"{f.attributes.setor}.{f.attributes.quadra}.{f.attributes.lote}",
        cor=cor_condominio,
    )


def _ponto_feature(ponto: PointGeometry) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": ponto.model_dump(),
        "properties": GeoJsonProperties(cor=MAP_COR_PONTO).model_dump(exclude_none=True),
    }


def _contexto_mais_proximo(
    ponto: PointGeometry, proximo: LoteProximo, origem: str
) -> dict[str, Any]:
    lote_geojson = to_geojson_feature_collection([proximo.lote], _properties_lote)
    geojson = {
        "type": "FeatureCollection",
        "features": [_ponto_feature(ponto), *lote_geojson["features"]],
    }
    gaveta = MontarGavetaLote()(
        GavetaLoteInput(lote=proximo.lote, crs_metrico=MAP_INTERPOLATION_CRS)
    )
    return contexto_mapa(geojson, MAP_COR_POLIGONO) | {
        "gaveta": gaveta,
        "distancia_m": proximo.distancia_m,
        "origem_busca": origem,
    }


@require_POST
def mais_proximo(request: HttpRequest) -> HttpResponse:
    consulta = ConsultaLoteMaisProximo.model_validate(request.POST.dict())
    entrada = LoteMaisProximoInput(
        ponto=PointGeometry(type="Point", coordinates=[consulta.lon, consulta.lat]),
        codlog=consulta.codlog,
        raio_m=LOTE_MAIS_PROXIMO_RAIO_M,
        camada=camada_lotes(),
    )
    try:
        proximo = LoteMaisProximo(build_fetcher(settings))(entrada)
    except NenhumLoteProximoError:
        return render(
            request,
            "mapping/_aviso.html",
            contexto_aviso(MSG_SEM_LOTE_PROXIMO.format(raio_m=LOTE_MAIS_PROXIMO_RAIO_M)),
        )
    return render(
        request,
        TEMPLATE_RESULTADO_MAIS_PROXIMO,
        _contexto_mais_proximo(entrada.ponto, proximo, consulta.origem),
    )


@require_POST
def lotes_do_desenho(request: HttpRequest) -> HttpResponse:
    """Rota aberta (SPEC localizacao_lote/003): consulta de dado público, sem ato administrativo."""
    consulta = ConsultaLotesDoDesenho.model_validate(request.POST.dict())
    entrada = LotesDoDesenhoInput(
        desenho=Desenho(id_bancada=consulta.id_bancada, geometria=consulta.desenho),
        crs_mapa=MAP_OUTPUT_CRS,
        camada=camada_lotes(),
        area_maxima_m2=LOTES_DESENHO_AREA_MAXIMA_M2,
    )
    try:
        resultado = BuscarLotesDoDesenho(build_fetcher(settings))(entrada)
    except (DesenhoInvalidoError, DesenhoGrandeDemaisError) as erro:
        return render(request, TEMPLATE_RECUSA_ACAO, contexto_aviso(str(erro)))
    return render(request, TEMPLATE_RESULTADO_DESENHO, contexto_lotes_do_desenho(resultado))


@require_GET
def detalhe_do_lote(request: HttpRequest) -> HttpResponse:
    """Rota aberta (SPEC localizacao_lote/003): a gaveta pública do lote, pelo polígono."""
    entrada = LotePorIdentificadorInput(
        id_poligono=request.GET.get("id", ""),
        layer_name=WFS_LAYER_LOTE_CIDADAO,
        output_crs=MAP_OUTPUT_CRS,
    )
    lote = LotePorIdentificador(build_fetcher(settings))(entrada)
    if lote is None:
        return render(request, "mapping/_aviso.html", contexto_aviso(MSG_LOTE_NAO_ENCONTRADO))
    gaveta = MontarGavetaLote()(GavetaLoteInput(lote=lote, crs_metrico=MAP_INTERPOLATION_CRS))
    return render(request, TEMPLATE_GAVETA_LOTE, {"gaveta": gaveta})
