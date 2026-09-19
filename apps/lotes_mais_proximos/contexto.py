from typing import Any

from django.conf import settings
from django.urls import reverse

from apps.lotes_mais_proximos.desenho_declarado import CONSULTA_LOTES_INTERSECTADOS
from apps.lotes_mais_proximos.sessao import ConjuntoNaSessao
from apps.mapping.context import contexto_resultado_acao
from apps.mapping.limpeza import AvisoDeLimpeza, Limpeza
from services.domain.geometry import GeoFeature, to_geojson_feature_collection
from services.domain.geometry.models import GeoJsonProperties
from services.domain.lotes_mais_proximos import CamadaLotes, ConjuntoDeLotes

WFS_LAYER_LOTE_CIDADAO: str = settings.WFS_LAYER_LOTE_CIDADAO
WFS_LOTE_CIDADAO_CAMPO_GEOMETRIA: str = settings.WFS_LOTE_CIDADAO_CAMPO_GEOMETRIA
MAP_INTERPOLATION_CRS: int = settings.MAP_INTERPOLATION_CRS
MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS

PERGUNTA_LIMPAR = "Tirar todos os lotes do conjunto?"
PERGUNTA_FECHAR = "Fechar a gaveta? Todos os lotes serão tirados."


def camada_lotes() -> CamadaLotes:
    # MAP_INTERPOLATION_CRS (31983, métrico) dobra como CRS da camada de lotes: mesma unidade
    # que já serve a interpolação do endereço, sem introduzir um segundo CRS métrico no projeto.
    return CamadaLotes(
        nome=WFS_LAYER_LOTE_CIDADAO,
        campo_geometria=WFS_LOTE_CIDADAO_CAMPO_GEOMETRIA,
        crs_camada=MAP_INTERPOLATION_CRS,
        crs_saida=MAP_OUTPUT_CRS,
    )


def url_detalhe_do_lote(id_poligono: str) -> str:
    return f"{reverse('lotes_mais_proximos:detalhe_do_lote')}?id={id_poligono}"


def _properties_lote_do_desenho(lote: GeoFeature[Any, Any]) -> GeoJsonProperties:
    sql = lote.attributes.sql
    return GeoJsonProperties(
        id=lote.attributes.id_poligono,
        rotulo=f"SQL {sql}" if sql else "Sem contribuinte",
        url_ficha=url_detalhe_do_lote(lote.attributes.id_poligono),
    )


def _contagem(conjunto: ConjuntoDeLotes) -> str:
    total = len(conjunto.lotes)
    return f"{total} lote{'s' if total != 1 else ''} na tela"


def _limpeza(url_name: str, guardado: ConjuntoNaSessao, pergunta: str) -> Limpeza:
    # Conjunto vazio não tem o que perder: sem aviso, o ✕ fecha direto (e "Limpar lotes" some).
    aviso = (
        AvisoDeLimpeza(pergunta=pergunta, contagem=_contagem(guardado.conjunto))
        if guardado.conjunto.lotes
        else None
    )
    return Limpeza(url=reverse(url_name), vals={"chave": guardado.chave}, aviso=aviso)


def _contexto_conjunto(guardado: ConjuntoNaSessao, enquadrar: bool) -> dict[str, Any]:
    conjunto = guardado.conjunto
    geojson = to_geojson_feature_collection(conjunto.lotes, _properties_lote_do_desenho)
    contexto = contexto_resultado_acao(
        CONSULTA_LOTES_INTERSECTADOS.slug,
        conjunto.apurado.desenho,
        geojson,
        limpeza_ao_fechar=_limpeza("lotes_mais_proximos:fechar_conjunto", guardado, PERGUNTA_FECHAR),
        enquadrar=enquadrar,
    )
    return contexto | {
        "conjunto": conjunto,
        "chave": guardado.chave,
        "limpar_lotes": _limpeza("lotes_mais_proximos:limpar_conjunto", guardado, PERGUNTA_LIMPAR),
    }


def contexto_lotes_do_desenho(guardado: ConjuntoNaSessao) -> dict[str, Any]:
    return _contexto_conjunto(guardado, enquadrar=True)


def contexto_revisao_do_conjunto(guardado: ConjuntoNaSessao) -> dict[str, Any]:
    # Tirar lotes não pode levar o mapa para longe de onde a pessoa está olhando.
    return _contexto_conjunto(guardado, enquadrar=False)
