"""
Testes do motor unificado de listagem de gestão (SPEC user_admin/013 e 019):
- Filtragem com normalização canônica de texto (sem diferenciar acentos/caixa/pontuação).
- Combinação cumulativa de filtros de múltiplas colunas.
- Ordenação bidirecional (ascendente e descendente).
- Extração de consulta tipada a partir de parâmetros da requisição (de_parametros).
- Compatibilidade genérica com LinhaUnidade e LinhaServidor.

Domínio puro — sem banco e sem Django: as linhas chegam materializadas em DTOs.
"""

from services.domain.listagem_gestao import (
    ColunaServidor,
    ColunaUnidade,
    ConsultaListagem,
    ConsultaServidores,
    ConsultaUnidades,
    FiltroColuna,
    LinhaServidor,
    LinhaUnidade,
    listar_servidores,
    listar_unidades,
)


def _unidade(
    sigla: str,
    nome: str,
    tipo: str = "Divisão",
    titular_nome: str | None = None,
    pai_sigla: str | None = None,
    exige_alta_adm: bool = False,
) -> LinhaUnidade:
    return LinhaUnidade(
        pk=abs(hash(sigla)) % 10_000,
        sigla=sigla,
        nome=nome,
        tipo=tipo,
        exige_alta_administracao=exige_alta_adm,
        cor_hex="#0077B6",
        titular_pk=1 if titular_nome else None,
        titular_nome=titular_nome,
        pai_pk=2 if pai_sigla else None,
        pai_sigla=pai_sigla,
    )


def _servidor(
    nome: str,
    unidade: str = "DIMAP-1",
    cargo: str = "Arquiteto",
) -> LinhaServidor:
    return LinhaServidor(
        pk=abs(hash(nome)) % 10_000,
        nome=nome,
        rf="999900",
        unidade=unidade,
        unidade_pk=abs(hash(unidade)) % 10_000,
        cor_unidade="#0077B6",
        cargo=cargo,
        comissao="",
        impedido=False,
    )


# ---------------------------------------------------------------------------
# Filtragem de Unidades
# ---------------------------------------------------------------------------


def test_filtro_unidades_casa_texto_normalizado() -> None:
    linhas = [
        _unidade("DIMAP", "Divisão de Mapeamento"),
        _unidade("DICAD", "Divisão de Informações Cadastrais"),
        _unidade("SUREM", "Subsecretaria da Receita Municipal"),
    ]

    por_acento = listar_unidades(
        linhas,
        ConsultaUnidades(
            filtros=[FiltroColuna(coluna=ColunaUnidade.NOME, termo="informacoes")]
        ),
    )
    por_sigla = listar_unidades(
        linhas,
        ConsultaUnidades(
            filtros=[FiltroColuna(coluna=ColunaUnidade.SIGLA, termo="dim")]
        ),
    )

    assert [linha.sigla for linha in por_acento] == ["DICAD"]
    assert [linha.sigla for linha in por_sigla] == ["DIMAP"]


def test_filtros_multiplos_de_unidades_se_somam() -> None:
    linhas = [
        _unidade("DIMAP", "Divisão de Mapeamento", tipo="Divisão", titular_nome="Beatriz Silva"),
        _unidade("DICAD", "Divisão de Cadastro", tipo="Divisão", titular_nome="Carlos Silva"),
        _unidade("SUREM", "Subsecretaria da Receita", tipo="Subsecretaria", titular_nome="Mariana Silva"),
    ]

    resultado = listar_unidades(
        linhas,
        ConsultaUnidades(
            filtros=[
                FiltroColuna(coluna=ColunaUnidade.TIPO, termo="divisao"),
                FiltroColuna(coluna=ColunaUnidade.TITULAR, termo="silva"),
            ]
        ),
    )

    assert [linha.sigla for linha in resultado] == ["DIMAP", "DICAD"]


# ---------------------------------------------------------------------------
# Filtragem de Servidores
# ---------------------------------------------------------------------------


def test_filtro_servidores_casa_texto_normalizado() -> None:
    linhas = [
        _servidor("Íris Sant'Anna"),
        _servidor("João São Paulo"),
        _servidor("Marina Salles"),
    ]

    por_apostrofo = listar_servidores(
        linhas,
        ConsultaServidores(
            filtros=[FiltroColuna(coluna=ColunaServidor.NOME, termo="sant anna")]
        ),
    )
    por_acento = listar_servidores(
        linhas,
        ConsultaServidores(
            filtros=[FiltroColuna(coluna=ColunaServidor.NOME, termo="sao")]
        ),
    )

    assert [linha.nome for linha in por_apostrofo] == ["Íris Sant'Anna"]
    assert [linha.nome for linha in por_acento] == ["João São Paulo"]


def test_filtros_multiplos_de_servidores_se_somam() -> None:
    linhas = [
        _servidor("Marina Salles", unidade="DIMAP-1"),
        _servidor("Marina Costa", unidade="DIMAP-2"),
        _servidor("Paulo Assunção", unidade="DIMAP-1"),
    ]

    resultado = listar_servidores(
        linhas,
        ConsultaServidores(
            filtros=[
                FiltroColuna(coluna=ColunaServidor.NOME, termo="marina"),
                FiltroColuna(coluna=ColunaServidor.UNIDADE, termo="dimap-1"),
            ]
        ),
    )

    assert [linha.nome for linha in resultado] == ["Marina Salles"]


# ---------------------------------------------------------------------------
# Ordenação de Unidades e Servidores
# ---------------------------------------------------------------------------


def test_ordena_unidades_por_coluna_em_ambas_as_direcoes() -> None:
    linhas = [
        _unidade("SUREM", "Subsecretaria da Receita"),
        _unidade("DECAD", "Coordenação de Cadastro"),
        _unidade("DIMAP", "Divisão de Mapeamento"),
    ]

    ascendente = listar_unidades(
        linhas,
        ConsultaUnidades(ordenar_por=ColunaUnidade.SIGLA),
    )
    descendente = listar_unidades(
        linhas,
        ConsultaUnidades(ordenar_por=ColunaUnidade.SIGLA, descendente=True),
    )

    assert [linha.sigla for linha in ascendente] == ["DECAD", "DIMAP", "SUREM"]
    assert [linha.sigla for linha in descendente] == ["SUREM", "DIMAP", "DECAD"]


def test_ordena_servidores_por_coluna_em_ambas_as_direcoes() -> None:
    linhas = [
        _servidor("Célia Gonçalves"),
        _servidor("Antônia Nóbrega"),
        _servidor("Ricardo Aparício"),
    ]

    ascendente = listar_servidores(
        linhas,
        ConsultaServidores(ordenar_por=ColunaServidor.NOME),
    )
    descendente = listar_servidores(
        linhas,
        ConsultaServidores(ordenar_por=ColunaServidor.NOME, descendente=True),
    )

    assert [linha.nome for linha in ascendente] == [
        "Antônia Nóbrega",
        "Célia Gonçalves",
        "Ricardo Aparício",
    ]
    assert list(reversed(descendente)) == ascendente


# ---------------------------------------------------------------------------
# Fábrica de ConsultaListagem a partir de parâmetros (de_parametros)
# ---------------------------------------------------------------------------


def test_consulta_de_parametros_extrai_filtros_e_ordenacao() -> None:
    parametros = {
        "sigla": "DIMAP",
        "tipo": "divisao",
        "ordenar_por": "nome",
        "descendente": "1",
        "parametro_estranho": "ignorado",
    }

    consulta = ConsultaUnidades.de_parametros(parametros, ColunaUnidade)

    assert len(consulta.filtros) == 2
    assert consulta.filtros[0].coluna == ColunaUnidade.SIGLA
    assert consulta.filtros[0].termo == "DIMAP"
    assert consulta.filtros[1].coluna == ColunaUnidade.TIPO
    assert consulta.filtros[1].termo == "divisao"
    assert consulta.ordenar_por == ColunaUnidade.NOME
    assert consulta.descendente is True
