from collections.abc import Callable
from typing import Protocol

from services.integrations.geocodificador_externo import google
from services.utils.ambiente import definidos

from .exceptions import ProvedorDesconhecidoError
from .geocodificador import GeocodificadorExterno
from .models import PoliticaGeocodificacao, Provedor
from .porta import ProvedorGeocodificacao
from .provedores import ProvedorGoogle

PROVEDOR_PADRAO = Provedor.GOOGLE


class GeocodificacaoSettingsLike(google.SettingsLike, Protocol):
    GEOCODIFICACAO_EXTERNA_PROVEDOR: str | None
    GEOCODIFICACAO_EXTERNA_IDIOMA: str | None
    GEOCODIFICACAO_EXTERNA_PAIS: str | None
    GEOCODIFICACAO_EXTERNA_UF: str | None
    GEOCODIFICACAO_EXTERNA_MUNICIPIO: str | None
    GEOCODIFICACAO_EXTERNA_PRECISAO_MINIMA: str | None


# devolve None quando o provedor não está configurado (sem token)
ConstrutorProvedor = Callable[
    [GeocodificacaoSettingsLike, PoliticaGeocodificacao],
    ProvedorGeocodificacao | None,
]


def build_politica(source: GeocodificacaoSettingsLike) -> PoliticaGeocodificacao:
    return definidos(
        PoliticaGeocodificacao,
        {
            "idioma": source.GEOCODIFICACAO_EXTERNA_IDIOMA,
            "pais": source.GEOCODIFICACAO_EXTERNA_PAIS,
            "uf": source.GEOCODIFICACAO_EXTERNA_UF,
            "municipio": source.GEOCODIFICACAO_EXTERNA_MUNICIPIO,
            "precisao_minima": source.GEOCODIFICACAO_EXTERNA_PRECISAO_MINIMA,
        },
    )


def _provedor_google(
    source: GeocodificacaoSettingsLike,
    politica: PoliticaGeocodificacao,
) -> ProvedorGeocodificacao | None:
    cliente = google.build_cliente(source)
    return None if cliente is None else ProvedorGoogle(politica, cliente)


CONSTRUTORES: dict[Provedor, ConstrutorProvedor] = {
    Provedor.GOOGLE: _provedor_google,
}


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
    source: GeocodificacaoSettingsLike,
) -> GeocodificadorExterno | None:
    # None = provedor escolhido sem configuração; quem consome decide o que oferecer sem ele
    construir = CONSTRUTORES[escolher_provedor(source)]
    provedor = construir(source, build_politica(source))
    return None if provedor is None else GeocodificadorExterno(provedor)
