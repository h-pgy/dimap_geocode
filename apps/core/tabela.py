"""
As tabelas de gestão na fronteira HTTP: a query string traduzida no DTO do domínio, o que cada
coluna leva para o template (rótulo, termo em vigor e aria-sort) e o par que o campo oculto de
ordenação carrega. Mora aqui, e não no contexto de um app, porque as duas listagens — servidores e
unidades — desenham o mesmo cabeçalho sobre a mesma `ConsultaListagem`; o que muda entre elas é só
o enum de colunas e o rótulo de cada uma.
"""

from collections.abc import Mapping
from typing import Any

from services.domain.listagem_gestao import ColunaT, ConsultaListagem, FiltroColuna

# Valores do aria-sort (WAI-ARIA); o relevo da seta é afordância e não carrega a semântica sozinho.
ORDEM_ASCENDENTE = "ascending"
ORDEM_DESCENDENTE = "descending"
# O par que o campo oculto do cabeçalho carrega — o mesmo que o JavaScript da seta escreve.
DESCENDENTE_LIGADO = "1"
DESCENDENTE_DESLIGADO = "0"
# Os dois campos ocultos que o cabeçalho manda junto com os filtros.
PARAMETRO_ORDENAR_POR = "ordenar_por"
PARAMETRO_DESCENDENTE = "descendente"


def consulta_da_listagem(
    parametros: Mapping[str, str],
    enum_coluna: type[ColunaT],
) -> ConsultaListagem[ColunaT]:
    """Traduz a query string da listagem no DTO do domínio: um filtro por coluna que respondeu."""
    filtros = [
        FiltroColuna(coluna=coluna, termo=parametros[coluna])
        for coluna in enum_coluna
        if parametros.get(coluna, "").strip()
    ]
    # model_validate porque os valores chegam como texto: coluna inválida vira ValidationError e o
    # PydanticValidationMiddleware responde por ela.
    return ConsultaListagem[enum_coluna].model_validate(  # type: ignore[valid-type]
        {
            "filtros": filtros,
            # Cabeçalho em repouso manda campo vazio; para o domínio, é ausência de ordenação.
            "ordenar_por": parametros.get(PARAMETRO_ORDENAR_POR) or None,
            "descendente": parametros.get(PARAMETRO_DESCENDENTE) or False,
        }
    )


def colunas_da_tabela(
    consulta: ConsultaListagem[ColunaT],
    enum_coluna: type[ColunaT],
    rotulos: Mapping[ColunaT, str],
) -> list[dict[str, Any]]:
    """As colunas viajam com o termo e a ordem em vigor: carregada com filtro na query string, a
    página nasce com as peças afundadas e a seta entintada, sem JavaScript de estado."""
    termos = {filtro.coluna: filtro.termo for filtro in consulta.filtros}
    return [
        {
            "slug": coluna.value,
            "rotulo": rotulos[coluna],
            "termo": termos.get(coluna, ""),
            "ordem": _ordem_da_coluna(coluna, consulta),
        }
        for coluna in enum_coluna
    ]


def marca_descendente(consulta: ConsultaListagem[ColunaT]) -> str:
    return DESCENDENTE_LIGADO if consulta.descendente else DESCENDENTE_DESLIGADO


def _ordem_da_coluna(coluna: ColunaT, consulta: ConsultaListagem[ColunaT]) -> str:
    # Vazio = sem ordem; o template só escreve aria-sort quando há ordenação nesta coluna.
    if consulta.ordenar_por != coluna:
        return ""
    return ORDEM_DESCENDENTE if consulta.descendente else ORDEM_ASCENDENTE
