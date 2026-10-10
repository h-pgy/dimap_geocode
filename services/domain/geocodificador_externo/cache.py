from typing import Protocol

from .models import ConsultaGeocodificacao, GeocodificacaoExterna


class CacheGeocodificacaoLike(Protocol):
    """Onde as geocodificações ficam guardadas: no máximo uma por chave, seja de que provedor for."""

    def buscar(self, consulta: ConsultaGeocodificacao) -> GeocodificacaoExterna | None:
        """A guardada para a chave, vencida ou não, no CRS em que foi guardada."""
        ...

    def guardar(self, geocodificacao: GeocodificacaoExterna) -> None:
        """Guarda, tomando o lugar da que houver para a mesma chave."""
        ...


class SemCache:
    def buscar(self, consulta: ConsultaGeocodificacao) -> GeocodificacaoExterna | None:
        return None

    def guardar(self, geocodificacao: GeocodificacaoExterna) -> None:
        return None
