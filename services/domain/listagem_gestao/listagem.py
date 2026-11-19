from collections.abc import Sequence
from typing import Generic
from services.domain.listagem_gestao.models import (
    ColunaCargo,
    ColunaCargoBase,
    ColunaExecucao,
    ColunaFaq,
    ColunaServidor,
    ColunaT,
    ColunaTipoUnidade,
    ColunaUnidade,
    ConsultaListagem,
    FiltroColuna,
    LinhaCargo,
    LinhaCargoBase,
    LinhaExecucao,
    LinhaFaq,
    LinhaServidor,
    LinhaT,
    LinhaTipoUnidade,
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


class ListarFaqs:
    """A tabela genérica, salvo a última edição: ordena pela data, e a nunca editada vai para o fim."""

    def __init__(self) -> None:
        self.listador = ListadorTabela[LinhaFaq, ColunaFaq]()

    def __call__(
        self,
        linhas: Sequence[LinhaFaq],
        consulta: ConsultaListagem[ColunaFaq],
    ) -> list[LinhaFaq]:
        if consulta.ordenar_por is not ColunaFaq.EDITADO_EM:
            return self.listador(linhas, consulta)
        filtradas = self.listador(linhas, consulta.model_copy(update={"ordenar_por": None}))
        editadas = sorted(
            (linha for linha in filtradas if linha.editado_em is not None),
            key=lambda linha: linha.editado_em,  # type: ignore[arg-type,return-value]
            reverse=consulta.descendente,
        )
        return editadas + [linha for linha in filtradas if linha.editado_em is None]


ListarServidores = ListadorTabela[LinhaServidor, ColunaServidor]
ListarUnidades = ListadorTabela[LinhaUnidade, ColunaUnidade]
ListarTiposUnidade = ListadorTabela[LinhaTipoUnidade, ColunaTipoUnidade]
ListarCargos = ListadorTabela[LinhaCargo, ColunaCargo]
ListarCargosBase = ListadorTabela[LinhaCargoBase, ColunaCargoBase]
ListarExecucoes = ListadorTabela[LinhaExecucao, ColunaExecucao]

listar_servidores = ListarServidores()
listar_unidades = ListarUnidades()
listar_tipos_unidade = ListarTiposUnidade()
listar_cargos = ListarCargos()
listar_cargos_base = ListarCargosBase()
listar_execucoes = ListarExecucoes()
listar_faqs = ListarFaqs()
