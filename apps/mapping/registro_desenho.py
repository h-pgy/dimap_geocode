from apps.logradouro_mais_proximo.desenho_declarado import CONSULTA_LOGRADOURO_MAIS_PROXIMO
from apps.lotes_mais_proximos.desenho_declarado import CONSULTA_LOTES_INTERSECTADOS
from apps.mapping.acoes_desenho import RegistroDesenho


def _construir_registro() -> RegistroDesenho:
    return RegistroDesenho(
        itens=(
            CONSULTA_LOTES_INTERSECTADOS,
            CONSULTA_LOGRADOURO_MAIS_PROXIMO,
        ),
    )


REGISTRO_DESENHO = _construir_registro()
