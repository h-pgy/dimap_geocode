from collections.abc import Callable
from typing import Protocol

from services.integrations.geocodificador_externo import google

from ..models import PoliticaGeocodificacao, Provedor
from ..porta import ProvedorGeocodificacao
from .google import build_provedor_google

PROVEDOR_PADRAO = Provedor.GOOGLE


class ProvedoresSettingsLike(google.SettingsLike, Protocol):
    """O que os provedores inscritos leem do ambiente."""


# devolve None quando o provedor não está configurado (sem token)
ConstrutorProvedor = Callable[
    [ProvedoresSettingsLike, PoliticaGeocodificacao],
    ProvedorGeocodificacao | None,
]

CONSTRUTORES: dict[Provedor, ConstrutorProvedor] = {
    Provedor.GOOGLE: build_provedor_google,
}
