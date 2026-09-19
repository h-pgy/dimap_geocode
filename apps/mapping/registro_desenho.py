from apps.lotes_mais_proximos.desenho_declarado import CONSULTA_LOTES_INTERSECTADOS
from apps.mapping.acoes_desenho import RegistroDesenho


def _construir_registro() -> RegistroDesenho:
    return RegistroDesenho(
        itens=(CONSULTA_LOTES_INTERSECTADOS,),
    )


REGISTRO_DESENHO = _construir_registro()
