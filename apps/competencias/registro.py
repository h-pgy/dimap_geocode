from .schemas import RegistroAcoes


def _construir_registro() -> RegistroAcoes:
    """Ponto único de montagem: inscrever ação é acrescentar uma linha aqui.
    Privado — quem consome o catálogo entra pela constante `REGISTRO`."""
    # Nasce vazio: a primeira ação chega junto da SPEC que a implementa.
    return RegistroAcoes(acoes=())


# Porta única do catálogo: uma instância por processo, no idioma dos catálogos de services/domain.
REGISTRO = _construir_registro()
