from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from services.utils.io import write_dataframe
from services.utils.normalization import normalize_text

from .constants import (
    COLUNA_ANO,
    COLUNA_FINANCIAMENTO_TIPO,
    COLUNA_IS_FINANCIAMENTO,
    COLUNA_MES,
    COLUNAS_DATA,
    COLUNAS_NUMERICAS,
    COLUNAS_TEXTO,
    MAPA_COLUNAS,
    MESES,
    NOME_PARQUET,
    OFFSET_LINHA_EXCEL,
    PADRAO_ABA,
    PADRAO_NOME_XLSX,
    TETO_LINHAS_DESCARTADAS,
)
from .disco import anos_em_disco
from .models import DescarteLinhas, DivergenciasEsquema, ParseItbi, ParseStats, RelatorioAno
from .patchers import PATCHERS_ITBI, ItbiPatcher, patch_all

# Os dois lados do casamento passam pela normalização única (§6.1) — a fonte tem acento,
# parênteses e caixa instável entre anos.
MAPA_NORMALIZADO: dict[str, str] = {
    normalize_text(cabecalho): saida for cabecalho, saida in MAPA_COLUNAS.items()
}
COLUNAS_SAIDA: list[str] = list(MAPA_COLUNAS.values())


class ItbiParser:
    """ETAPA 2: um xlsx por vez → um parquet por ano.

    NÃO conhece o portal nem a coleta: parseia o que estiver em disco.
    """

    def __init__(self, patchers: Sequence[ItbiPatcher] = PATCHERS_ITBI) -> None:
        self._patchers = patchers
        self._parseados: list[int] = []
        self._falhas: dict[int, str] = {}
        self._desconhecidas: dict[int, list[str]] = {}
        self._ausentes: dict[int, list[str]] = {}
        self._descartadas: dict[int, int] = {}
        self._descartes: dict[int, list[str]] = {}

    def __call__(self, originais: Path, parseados: Path) -> ParseItbi:
        return self.pipeline(originais, parseados)

    def pipeline(self, originais: Path, parseados: Path) -> ParseItbi:
        self._parsear(originais, parseados)
        return ParseItbi(
            stats=ParseStats(
                anos_parseados=sorted(self._parseados),
                falhas_por_ano=self._falhas,
                colunas_desconhecidas_por_ano=self._desconhecidas,
                colunas_ausentes_por_ano=self._ausentes,
                linhas_descartadas_por_ano=self._descartadas,
                descartes_por_ano=self._descartes,
            )
        )

    def _parsear(self, originais: Path, parseados: Path) -> None:
        for ano, xlsx in sorted(anos_em_disco(originais, PADRAO_NOME_XLSX).items()):
            relatorio = RelatorioAno()
            try:
                quadro = self._ler_planilha(xlsx, ano, relatorio)
            except Exception as exc:
                # O parquet do ano NÃO é tocado: a carga anterior continua valendo, e é ela
                # que a consolidação vai usar. Vinte anos de planilha manual — abortar porque
                # 2011 parou de converter seria nunca mais atualizar 2026.
                self._falhas[ano] = f"{type(exc).__name__}: {exc}"
                continue
            # Só chega aqui o ano que parseou INTEIRO: a escrita é a última operação.
            write_dataframe(quadro, NOME_PARQUET.format(ano=ano), folder=parseados)
            self._parseados.append(ano)
            self._registrar(ano, relatorio)

    def _registrar(self, ano: int, relatorio: RelatorioAno) -> None:
        if relatorio.divergencias.desconhecidas:
            self._desconhecidas[ano] = relatorio.divergencias.desconhecidas
        if relatorio.divergencias.ausentes:
            self._ausentes[ano] = relatorio.divergencias.ausentes
        if relatorio.descarte.descartadas:
            self._descartadas[ano] = relatorio.descarte.descartadas
            self._descartes[ano] = relatorio.descarte.localizacoes

    def _ler_planilha(self, xlsx: Path, ano: int, relatorio: RelatorioAno) -> pd.DataFrame:
        abas = pd.read_excel(xlsx, sheet_name=None, dtype=object)
        quadros = [
            self._aba_para_quadro(aba, nome, ano, mes, relatorio)
            for nome, aba in abas.items()
            if (mes := self._mes_da_aba(nome)) is not None
        ]
        if not quadros:
            raise ValueError(f"{xlsx.name}: nenhuma aba no padrão MÊS-ANO")
        self._checar_teto(xlsx, relatorio.descarte)
        return pd.concat(quadros, ignore_index=True)

    def _checar_teto(self, xlsx: Path, descarte: DescarteLinhas) -> None:
        """Perder muita linha não é linha ruim, é esquema que mudou — aí o ano cai inteiro."""
        if not descarte.excede_teto():
            return
        raise ValueError(
            f"{xlsx.name}: {descarte.descartadas} de {descarte.lidas} linhas não convertem "
            f"({descarte.fracao:.1%}) — acima do teto de {TETO_LINHAS_DESCARTADAS:.0%}"
        )

    def _mes_da_aba(self, nome: str) -> int | None:
        """Aba fora do padrão (resumo, notas, planilha vazia) é ignorada em silêncio."""
        encontrado = PADRAO_ABA.match(normalize_text(nome))
        if encontrado is None:
            return None
        return MESES.index(encontrado.group(1)) + 1

    def _aba_para_quadro(
        self,
        aba: pd.DataFrame,
        nome: str,
        ano: int,
        mes: int,
        relatorio: RelatorioAno,
    ) -> pd.DataFrame:
        # Os consertos vêm ANTES do casamento: o que a fonte estraga é o cabeçalho.
        aba = patch_all(aba, ano, self._patchers)
        quadro = self._renomear(aba, relatorio.divergencias)
        quadro = self._descartar_invalidas(quadro, nome, relatorio.descarte)
        quadro = self._converter_tipos(quadro)
        return self._derivar(quadro, ano, mes)

    def _descartar_invalidas(
        self,
        quadro: pd.DataFrame,
        nome: str,
        descarte: DescarteLinhas,
    ) -> pd.DataFrame:
        """Linha digitada com célula a mais empurra texto para coluna numérica: ela sai inteira."""
        invalidas = pd.Series(False, index=quadro.index)
        for coluna in COLUNAS_NUMERICAS:
            invalidas |= self._nao_converte(quadro[coluna], pd.to_numeric)
        for coluna in COLUNAS_DATA:
            invalidas |= self._nao_converte(quadro[coluna], pd.to_datetime)
        descarte.registrar(
            nome,
            [int(indice) + OFFSET_LINHA_EXCEL for indice in quadro.index[invalidas]],
            len(quadro),
        )
        return quadro[~invalidas].copy()

    def _nao_converte(self, serie: pd.Series, conversao: Callable[..., Any]) -> pd.Series:
        # O coerce entra só para LOCALIZAR a linha ruim: nulo de parser não chega ao parquet,
        # porque a linha inteira sai. Célula vazia continua distinguível de valor não entendido.
        return conversao(serie, errors="coerce").isna() & serie.notna()

    def _renomear(self, aba: pd.DataFrame, divergencias: DivergenciasEsquema) -> pd.DataFrame:
        mapa: dict[str, str] = {}
        desconhecidas: list[str] = []
        for cabecalho in (str(coluna) for coluna in aba.columns):
            saida = MAPA_NORMALIZADO.get(normalize_text(cabecalho))
            if saida is None:
                desconhecidas.append(cabecalho)
                continue
            mapa[cabecalho] = saida

        quadro = aba.rename(columns=mapa)
        ausentes = [saida for saida in COLUNAS_SAIDA if saida not in mapa.values()]
        divergencias.acrescentar(desconhecidas, ausentes)
        for coluna in ausentes:
            # Um ano com esquema diferente não derruba a carga: a coluna sai nula.
            quadro[coluna] = None
        return quadro[COLUNAS_SAIDA].copy()

    def _converter_tipos(self, quadro: pd.DataFrame) -> pd.DataFrame:
        for coluna in COLUNAS_NUMERICAS:
            quadro[coluna] = self._converter(quadro, coluna, pd.to_numeric)
        for coluna in COLUNAS_DATA:
            quadro[coluna] = self._converter(quadro, coluna, pd.to_datetime)
        # O texto também é declarado: sem isso o esquema do parquet dependeria do que o pyarrow
        # inferir das primeiras linhas de cada ano, e os anos deixariam de concatenar.
        for coluna in COLUNAS_TEXTO:
            quadro[coluna] = quadro[coluna].astype("string")
        return quadro

    def _converter(
        self,
        quadro: pd.DataFrame,
        coluna: str,
        conversao: Callable[..., Any],
    ) -> pd.Series:
        # errors="raise": com coerce, o valor que o parser não entendeu viraria nulo e ficaria
        # indistinguível de célula vazia — o dado degradaria em silêncio.
        try:
            return conversao(quadro[coluna], errors="raise")
        except (ValueError, TypeError) as exc:
            # O erro nu não diz em qual das colunas declaradas o ano caiu, e é essa mensagem
            # que sobra nos metadados dias depois.
            raise ValueError(f"coluna '{coluna}': {exc}") from exc

    def _derivar(self, quadro: pd.DataFrame, ano: int, mes: int) -> pd.DataFrame:
        # O ano é sempre o do portal, que viaja no nome do arquivo; o da aba só a reconhece.
        quadro[COLUNA_ANO] = ano
        quadro[COLUNA_MES] = mes
        tipo = quadro[COLUNA_FINANCIAMENTO_TIPO]
        quadro[COLUNA_IS_FINANCIAMENTO] = tipo.fillna("").astype(str).str.strip().ne("")
        return quadro
