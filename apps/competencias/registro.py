from apps.unidades.acoes_declaradas import (
    ACAO_CRIAR_UNIDADE,
    ACAO_CRIAR_UNIDADE_RAIZ,
    ACAO_EDITAR_UNIDADE,
)
from apps.user_admin.acoes_declaradas import (
    ACAO_CRIAR_SERVIDOR,
    ACAO_EDITAR_SERVIDOR,
    ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR,
    ACAO_TORNAR_ADMINISTRADOR,
)

from .acoes_declaradas import ACAO_CONCEDER, ACAO_DEFINIR_ATRIBUICAO
from .schemas import RegistroAcoes


def _construir_registro() -> RegistroAcoes:
    """Ponto único de montagem: inscrever ação é acrescentar uma linha aqui.
    Privado — quem consome o catálogo entra pela constante `REGISTRO`."""
    return RegistroAcoes(
        acoes=(
            ACAO_DEFINIR_ATRIBUICAO,
            ACAO_CONCEDER,
            ACAO_CRIAR_SERVIDOR,
            ACAO_EDITAR_SERVIDOR,
            ACAO_TORNAR_ADMINISTRADOR,
            ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR,
            ACAO_CRIAR_UNIDADE,
            ACAO_EDITAR_UNIDADE,
            ACAO_CRIAR_UNIDADE_RAIZ,
        )
    )


# Porta única do catálogo: uma instância por processo, no idioma dos catálogos de services/domain.
REGISTRO = _construir_registro()
