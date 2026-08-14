"""
Testes da listagem de servidores (SPEC user_admin/013): o filtro casa texto pela normalização
única do projeto, filtros de colunas diferentes se somam e a ordenação vale nas duas direções.

Domínio puro — sem banco e sem Django: as linhas chegam materializadas em DTO.
"""

from services.domain.servidores_listagem import (
    ColunaServidor,
    ConsultaServidores,
    FiltroColuna,
    LinhaServidor,
    listar_servidores,
)


def _linha(
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


def test_filtro_casa_texto_normalizado() -> None:
    linhas = [
        _linha("Íris Sant'Anna"),
        _linha("João São Paulo"),
        _linha("Marina Salles"),
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


def test_filtros_de_colunas_diferentes_se_somam() -> None:
    linhas = [
        _linha("Marina Salles", unidade="DIMAP-1"),
        _linha("Marina Costa", unidade="DIMAP-2"),
        _linha("Paulo Assunção", unidade="DIMAP-1"),
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


def test_ordena_por_coluna_em_ambas_as_direcoes() -> None:
    linhas = [
        _linha("Célia Gonçalves"),
        _linha("Antônia Nóbrega"),
        _linha("Ricardo Aparício"),
    ]

    ascendente = listar_servidores(
        linhas,
        ConsultaServidores(ordenar_por=ColunaServidor.NOME),
    )
    descendente = listar_servidores(
        linhas,
        ConsultaServidores(
            ordenar_por=ColunaServidor.NOME,
            descendente=True,
        ),
    )

    assert [linha.nome for linha in ascendente] == [
        "Antônia Nóbrega",
        "Célia Gonçalves",
        "Ricardo Aparício",
    ]
    assert list(reversed(descendente)) == ascendente
