from typing import Protocol

from services.utils.ambiente import definidos

from .cache import CacheGeocodificacaoLike
from .exceptions import ProvedorDesconhecidoError
from .geocodificador import GeocodificadorExterno
from .models import PoliticaGeocodificacao, Provedor
from .provedores import CONSTRUTORES, PROVEDOR_PADRAO, ProvedoresSettingsLike
from .validador import ValidadorGeocodificacao


class GeocodificacaoSettingsLike(Protocol):
    GEOCODIFICACAO_EXTERNA_PROVEDOR: str | None
    GEOCODIFICACAO_EXTERNA_IDIOMA: str | None
    GEOCODIFICACAO_EXTERNA_PAIS: str | None
    GEOCODIFICACAO_EXTERNA_UF: str | None
    GEOCODIFICACAO_EXTERNA_MUNICIPIO: str | None
    GEOCODIFICACAO_EXTERNA_PRECISAO_MINIMA: str | None
    GEOCODIFICACAO_EXTERNA_VALIDADE_DIAS: int | None


class ComposicaoSettingsLike(GeocodificacaoSettingsLike, ProvedoresSettingsLike, Protocol):
    """O ambiente de quem compõe: o geral mais o que os provedores inscritos leem, sem nomeá-los."""


def build_politica(source: GeocodificacaoSettingsLike) -> PoliticaGeocodificacao:
    return definidos(
        PoliticaGeocodificacao,
        {
            "idioma": source.GEOCODIFICACAO_EXTERNA_IDIOMA,
            "pais": source.GEOCODIFICACAO_EXTERNA_PAIS,
            "uf": source.GEOCODIFICACAO_EXTERNA_UF,
            "municipio": source.GEOCODIFICACAO_EXTERNA_MUNICIPIO,
            "precisao_minima": source.GEOCODIFICACAO_EXTERNA_PRECISAO_MINIMA,
            "validade_dias": source.GEOCODIFICACAO_EXTERNA_VALIDADE_DIAS,
        },
    )


def escolher_provedor(source: GeocodificacaoSettingsLike) -> Provedor:
    nome = source.GEOCODIFICACAO_EXTERNA_PROVEDOR
    if nome is None:
        return PROVEDOR_PADRAO
    try:
        return Provedor(nome)
    except ValueError:
        conhecidos = ", ".join(p.value for p in Provedor)
        raise ProvedorDesconhecidoError(
            f"{repr(nome)} não é um provedor; use um de: {conhecidos}"
        ) from None


def build_geocodificador_externo(
    source: ComposicaoSettingsLike,
    cache: CacheGeocodificacaoLike | None = None,
) -> GeocodificadorExterno | None:
    # None = provedor escolhido sem configuração; quem consome decide o que oferecer sem ele
    construir = CONSTRUTORES[escolher_provedor(source)]
    politica = build_politica(source)
    provedor = construir(source, politica)
    if provedor is None:
        return None
    # a mesma política para quem consulta e para quem valida
    return GeocodificadorExterno(provedor, cache, ValidadorGeocodificacao(politica))
