from pathlib import Path
from typing import Any

from django.conf import settings

from apps.mapping.limpeza import Limpeza
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

GEOJSON_VAZIO: dict[str, Any] = {"type": "FeatureCollection", "features": []}
COOKIE_ORTOFOTO_FUNDO = "ortofoto_fundo"


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


def ortofoto_do_fundo(em_tela: str | None) -> str | None:
    """A ortofoto do fundo à deriva (SPEC design/010 v8): a que já está na tela de quem navega,
    enquanto ela existir no disco — só a primeira tela e o rodízio sorteiam."""
    disponiveis = ortofotos_disponiveis()
    if not disponiveis:
        return None
    if em_tela in disponiveis:
        return em_tela
    return sortear_diferente(disponiveis, None)


def contexto_mapa(geometria: dict[str, Any], cor: str, enquadrar: bool = True) -> dict[str, Any]:
    """Monta o contexto de payload de um resultado: geometria GeoJSON 4326 + cor, sem WMS
    (o mapa singleton já existe). Agnóstico de domínio — só geometria pronta."""
    return {"payload": {"geometria": geometria, "cor": cor, "enquadrar": enquadrar}}


def contexto_resultado_acao(
    acao: str,
    desenho: Desenho,
    geojson: dict[str, Any],
    limpeza_ao_fechar: Limpeza,
    enquadrar: bool = True,
) -> dict[str, Any]:
    """O contexto de toda resposta de ação: o do mapa, na cor única dos resultados de ação, o slug de
    quem abriu o contexto, o desenho sobre o qual ele opera e a limpeza que o ✕ da gaveta dispara."""
    return contexto_mapa(geojson, MAP_COR_RESULTADO_ACAO, enquadrar) | {
        "acao": acao,
        "desenho": desenho.id_bancada,
        "limpeza_ao_fechar": limpeza_ao_fechar,
    }


def contexto_encerramento_acao() -> dict[str, Any]:
    # FeatureCollection vazia: o aplicarResultado tira a camada anterior e não põe nada.
    return contexto_mapa(GEOJSON_VAZIO, MAP_COR_RESULTADO_ACAO, enquadrar=False)


def contexto_aviso(mensagem: str) -> dict[str, Any]:
    """Contexto do partial de aviso do mapping: só a mensagem pronta (agnóstico de domínio)."""
    return {"mensagem": mensagem}
