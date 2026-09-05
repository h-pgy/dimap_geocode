from collections.abc import Sequence
from typing import Generic
from services.domain.listagem_gestao.models import (
    ColunaCargo,
    ColunaCargoBase,
    ColunaExecucao,
    ColunaServidor,
    ColunaT,
    ColunaUnidade,
    ConsultaListagem,
    FiltroColuna,
    LinhaCargo,
    LinhaCargoBase,
    LinhaExecucao,
    LinhaServidor,
    LinhaT,
    LinhaUnidade,
)
from services.utils.normalization import normalize_text


class ListadorTabela(Generic[LinhaT, ColunaT]):
    """Filtra e ordena uma coleção de linhas materializadas em memória."""

    def __call__(
        self,
        linhas: Sequence[LinhaT],
        consulta: ConsultaListagem[ColunaT],
    ) -> list[LinhaT]:
        resultado = list(linhas)
        for filtro in consulta.filtros:
            resultado = self._filtrar_coluna(resultado, filtro)
        if consulta.ordenar_por is not None:
            resultado = self._ordenar(resultado, consulta.ordenar_por, consulta.descendente)
        return resultado

    def _filtrar_coluna(
        self,
        linhas: list[LinhaT],
        filtro: FiltroColuna[ColunaT],
    ) -> list[LinhaT]:
        termo = normalize_text(filtro.termo)
        if not termo:
            return linhas
        return [
            linha
            for linha in linhas
            if termo in self._chave(linha, filtro.coluna)
        ]

    def _ordenar(
        self,
        linhas: list[LinhaT],
        coluna: ColunaT,
        descendente: bool,
    ) -> list[LinhaT]:
        return sorted(
            linhas,
            key=lambda linha: self._chave(linha, coluna),
            reverse=descendente,
        )

    def _chave(self, linha: LinhaT, coluna: ColunaT) -> str:
        campo = getattr(coluna, "value", str(coluna))
        valor = getattr(linha, campo, "")
        return normalize_text(str(valor or ""))


ListarServidores = ListadorTabela[LinhaServidor, ColunaServidor]
ListarUnidades = ListadorTabela[LinhaUnidade, ColunaUnidade]
ListarCargos = ListadorTabela[LinhaCargo, ColunaCargo]
ListarCargosBase = ListadorTabela[LinhaCargoBase, ColunaCargoBase]
ListarExecucoes = ListadorTabela[LinhaExecucao, ColunaExecucao]

listar_servidores = ListarServidores()
listar_unidades = ListarUnidades()
listar_cargos = ListarCargos()
listar_cargos_base = ListarCargosBase()
listar_execucoes = ListarExecucoes()
