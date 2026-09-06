"""
Testes do domínio do registro de ações (SPEC painel/002): a tradução da query string em
`BuscaExecucoes`, a paginação em memória e o motor genérico de listagem sobre `LinhaExecucao`.

Domínio puro — sem banco e sem Django: as linhas chegam materializadas em DTOs.
"""

from datetime import date, timedelta

from services.domain.listagem_gestao import (
    JANELA_PADRAO_DIAS,
    BuscaExecucoes,
    ColunaExecucao,
    ConsultaExecucoes,
    FiltroColuna,
    LinhaExecucao,
    Pagina,
    listar_execucoes,
    paginar,
)

HOJE = date(2026, 9, 5)


def _linha(
    pk: int,
    servidor: str = "Marina Toledo",
    acao: str = "Cadastrar servidor",
) -> LinhaExecucao:
    return LinhaExecucao(
        pk=pk,
        momento="05/09/2026 14:32",
        servidor=servidor,
        servidor_pk=pk,
        unidade="DIMAP-1",
        unidade_pk=7,
        cor_unidade="#0077B6",
        cargo="AFTM",
        acao=acao,
        autorizado=True,
    )


# ---------------------------------------------------------------------------
# BuscaExecucoes.de_parametros
# ---------------------------------------------------------------------------


def test_busca_sem_criterio_nasce_nos_trinta_dias_e_sem_recorte() -> None:
    unidades = frozenset({7, 11})

    # Query string vazia (carga inicial) e com selects em branco (formulário submetido sem
    # escolha) — as duas formas precisam resolver para o mesmo período e para `None`, nunca
    # id inválido nem `ValidationError`.
    de_carga_inicial = BuscaExecucoes.de_parametros({}, hoje=HOJE, unidades_lidas=unidades)
    de_selects_em_branco = BuscaExecucoes.de_parametros(
        {"perfil": "", "cargo_base": "", "cargo_comissao": ""},
        hoje=HOJE,
        unidades_lidas=unidades,
    )

    for busca in (de_carga_inicial, de_selects_em_branco):
        assert busca.unidades_lidas == unidades
        assert busca.inicio == HOJE - timedelta(days=JANELA_PADRAO_DIAS)
        assert busca.fim == HOJE
        assert busca.perfil_id is None
        assert busca.cargo_base_id is None
        assert busca.cargo_comissao_id is None


# ---------------------------------------------------------------------------
# paginar
# ---------------------------------------------------------------------------


def test_paginacao_fatia_e_prende_o_numero_nos_limites() -> None:
    linhas = [_linha(pk) for pk in range(120)]

    pagina_1 = paginar(linhas, numero=1, tamanho=50)
    pagina_3 = paginar(linhas, numero=3, tamanho=50)
    abaixo_do_minimo = paginar(linhas, numero=0, tamanho=50)
    acima_do_maximo = paginar(linhas, numero=999, tamanho=50)
    vazia: Pagina[LinhaExecucao] = paginar([], numero=1, tamanho=50)

    assert pagina_1.total_paginas == 3
    assert pagina_1.total_linhas == 120
    assert len(pagina_1.linhas) == 50
    assert len(pagina_3.linhas) == 20
    assert abaixo_do_minimo.numero == 1
    assert acima_do_maximo.numero == 3
    assert vazia.numero == 1
    assert vazia.total_paginas == 1
    assert vazia.linhas == ()


# ---------------------------------------------------------------------------
# O cabeçalho filtra e ordena dentro do que a busca devolveu
# ---------------------------------------------------------------------------


def test_cabecalho_filtra_e_ordena_dentro_das_linhas_da_busca() -> None:
    linhas = [
        _linha(1, servidor="Marina Toledo", acao="Cadastrar servidor"),
        _linha(2, servidor="Paulo Rezende", acao="Extinguir unidade"),
        _linha(3, servidor="Marina Costa", acao="Editar cadastro"),
    ]

    por_servidor = listar_execucoes(
        linhas,
        ConsultaExecucoes(filtros=[FiltroColuna(coluna=ColunaExecucao.SERVIDOR, termo="marina")]),
    )
    por_acao_descendente = listar_execucoes(
        linhas,
        ConsultaExecucoes(ordenar_por=ColunaExecucao.ACAO, descendente=True),
    )

    assert [linha.pk for linha in por_servidor] == [1, 3]
    assert [linha.acao for linha in por_acao_descendente] == [
        "Extinguir unidade",
        "Editar cadastro",
        "Cadastrar servidor",
    ]
