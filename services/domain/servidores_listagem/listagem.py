"""
Filtro e ordenação da listagem de servidores (SPEC user_admin/013). Domínio puro sobre DTOs já
materializados — são dezenas de registros, e a regra que interessa (o casamento textual) é a
normalização única do §6.1, na preparação e na consulta.
"""

from services.domain.servidores_listagem.models import (
    ColunaServidor,
    ConsultaServidores,
    FiltroColuna,
    LinhaServidor,
)
from services.utils.normalization import normalize_text


class ListarServidores:
    """Filtra e ordena as linhas já materializadas — dezenas de registros, sem ORM no domínio."""

    def __call__(
        self,
        linhas: list[LinhaServidor],
        consulta: ConsultaServidores,
    ) -> list[LinhaServidor]:
        return self.pipeline(linhas, consulta)

    def pipeline(
        self,
        linhas: list[LinhaServidor],
        consulta: ConsultaServidores,
    ) -> list[LinhaServidor]:
        filtradas = self._filtrar(linhas, consulta.filtros)
        return self._ordenar(filtradas, consulta.ordenar_por, consulta.descendente)

    def _filtrar(
        self,
        linhas: list[LinhaServidor],
        filtros: list[FiltroColuna],
    ) -> list[LinhaServidor]:
        # Filtros de colunas diferentes se somam: a linha atende a todos ou não entra.
        return [
            linha
            for linha in linhas
            if all(self._atende(linha, filtro) for filtro in filtros)
        ]

    def _atende(self, linha: LinhaServidor, filtro: FiltroColuna) -> bool:
        return normalize_text(filtro.termo) in self._chave(linha, filtro.coluna)

    def _ordenar(
        self,
        linhas: list[LinhaServidor],
        coluna: ColunaServidor | None,
        descendente: bool,
    ) -> list[LinhaServidor]:
        if coluna is None:
            return linhas
        return sorted(
            linhas,
            key=lambda linha: self._chave(linha, coluna),
            reverse=descendente,
        )

    def _chave(self, linha: LinhaServidor, coluna: ColunaServidor) -> str:
        # A mesma normalização das duas pontas: sem ela "Álvaro" cairia depois de "Zuleica" na
        # ordenação e "sant anna" não acharia "Sant'Anna" no filtro.
        return normalize_text(getattr(linha, coluna.value))


listar_servidores = ListarServidores()
