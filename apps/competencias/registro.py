from .acoes_declaradas import ACAO_DEFINIR_ATRIBUICAO
from .schemas import RegistroAcoes


def _construir_registro() -> RegistroAcoes:
    """Ponto único de montagem: inscrever ação é acrescentar uma linha aqui.
    Privado — quem consome o catálogo entra pela constante `REGISTRO`."""
    return RegistroAcoes(acoes=(ACAO_DEFINIR_ATRIBUICAO,))


# Porta única do catálogo: uma instância por processo, no idioma dos catálogos de services/domain.
REGISTRO = _construir_registro()
