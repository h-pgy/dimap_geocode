from pathlib import Path
from typing import Any

from django.conf import settings

from config.pontos_fundo import PontoFundo
from services.domain.desenho import Desenho
from services.utils.sorteio import sortear_diferente

WMS_URL: str = settings.WMS_URL
WMS_VERSION: str = settings.WMS_VERSION
WMS_BASES: list[dict[str, str | int]] = settings.WMS_BASES
MAP_CENTRO_DEFAULT: list[float] = settings.MAP_CENTRO_DEFAULT
MAP_ZOOM_DEFAULT: int = settings.MAP_ZOOM_DEFAULT
MAP_TILES_PUBLICOS_URL: str = settings.MAP_TILES_PUBLICOS_URL
MAP_TILES_PUBLICOS_SUBDOMINIOS: str = settings.MAP_TILES_PUBLICOS_SUBDOMINIOS
MAP_TILES_PUBLICOS_ATRIBUICAO: str = settings.MAP_TILES_PUBLICOS_ATRIBUICAO
MAP_TILES_PUBLICOS_ZOOM_MAXIMO: int = settings.MAP_TILES_PUBLICOS_ZOOM_MAXIMO
MAP_FUNDO_PONTOS: dict[str, PontoFundo] = settings.MAP_FUNDO_PONTOS
MAP_FUNDO_DIR: Path = settings.MAP_FUNDO_DIR
MAP_COR_RESULTADO_ACAO: str = settings.MAP_COR_RESULTADO_ACAO


def contexto_mapa_base() -> dict[str, Any]:
    """Contexto do canvas singleton da home: base WMS + centro/zoom, sem geometria.
    O mapa nasce uma única vez na home; resultados chegam depois como payload (§ contexto_mapa)."""
    return {
        "wms": {"url": WMS_URL, "version": WMS_VERSION, "bases": WMS_BASES},
        "config": {"centro": MAP_CENTRO_DEFAULT, "zoom": MAP_ZOOM_DEFAULT},
    }


_CACHE_ORTOFOTOS: tuple[str, ...] | None = None


def ortofotos_disponiveis() -> tuple[str, ...]:
    """Interseção do catálogo com o disco: ponto sem PNG gerado não entra no sorteio.
    Só fixa o cache em memória quando encontrar fotos no disco, evitando congelar o processo
    com uma lista vazia caso o servidor web suba antes do comando de geração rodar."""
    global _CACHE_ORTOFOTOS
    if _CACHE_ORTOFOTOS is not None:
        return _CACHE_ORTOFOTOS

    encontradas = tuple(
        chave for chave in MAP_FUNDO_PONTOS if (MAP_FUNDO_DIR / f"{chave}.png").exists()
    )
    if encontradas:
        _CACHE_ORTOFOTOS = encontradas
    return encontradas


def _cache_clear() -> None:
    global _CACHE_ORTOFOTOS
    _CACHE_ORTOFOTOS = None


ortofotos_disponiveis.cache_clear = _cache_clear  # type: ignore[attr-defined]


def contexto_fundo_admin() -> dict[str, Any]:
    """Contexto do fundo à deriva da área administrativa: ortofoto pré-gerada sorteada, sem
    nenhuma requisição ao GeoSampa em tempo de request (SPEC design/010)."""
    disponiveis = ortofotos_disponiveis()
    return {"ortofoto_fundo": sortear_diferente(disponiveis, None) if disponiveis else None}


def contexto_mapa(geometria: dict[str, Any], cor: str) -> dict[str, Any]:
    """Monta o contexto de payload de um resultado: geometria GeoJSON 4326 + cor, sem WMS
    (o mapa singleton já existe). Agnóstico de domínio — só geometria pronta."""
    return {"payload": {"geometria": geometria, "cor": cor}}


def contexto_resultado_acao(acao: str, desenho: Desenho, geojson: dict[str, Any]) -> dict[str, Any]:
    """O contexto de toda resposta de ação: o do mapa, na cor única dos resultados de ação, o slug de
    quem abriu o contexto e o desenho sobre o qual ele opera."""
    return contexto_mapa(geojson, MAP_COR_RESULTADO_ACAO) | {
        "acao": acao,
        "desenho": desenho.id_bancada,
    }


def contexto_aviso(mensagem: str) -> dict[str, Any]:
    """Contexto do partial de aviso do mapping: só a mensagem pronta (agnóstico de domínio)."""
    return {"mensagem": mensagem}
