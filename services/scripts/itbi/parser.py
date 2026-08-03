from collections.abc import Callable
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
    PADRAO_ABA,
    PADRAO_NOME_XLSX,
)
from .disco import anos_em_disco
from .models import DivergenciasEsquema, ParseItbi, ParseStats

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

    def __init__(self) -> None:
        self._parseados: list[int] = []
        self._falhas: dict[int, str] = {}
        self._desconhecidas: dict[int, list[str]] = {}
        self._ausentes: dict[int, list[str]] = {}

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
            )
        )

    def _parsear(self, originais: Path, parseados: Path) -> None:
        for ano, xlsx in sorted(anos_em_disco(originais, PADRAO_NOME_XLSX).items()):
            divergencias = DivergenciasEsquema()
            try:
                quadro = self._ler_planilha(xlsx, ano, divergencias)
            except Exception as exc:
                # O parquet do ano NÃO é tocado: a carga anterior continua valendo, e é ela
                # que a consolidação vai usar. Vinte anos de planilha manual — abortar porque
                # 2011 parou de converter seria nunca mais atualizar 2026.
                self._falhas[ano] = f"{type(exc).__name__}: {exc}"
                continue
            # Só chega aqui o ano que parseou INTEIRO: a escrita é a última operação.
            write_dataframe(quadro, NOME_PARQUET.format(ano=ano), folder=parseados)
            self._parseados.append(ano)
            self._registrar_divergencias(ano, divergencias)

    def _registrar_divergencias(self, ano: int, divergencias: DivergenciasEsquema) -> None:
        if divergencias.desconhecidas:
            self._desconhecidas[ano] = divergencias.desconhecidas
        if divergencias.ausentes:
            self._ausentes[ano] = divergencias.ausentes

    def _ler_planilha(
        self,
        xlsx: Path,
        ano: int,
        divergencias: DivergenciasEsquema,
    ) -> pd.DataFrame:
        abas = pd.read_excel(xlsx, sheet_name=None, dtype=object)
        quadros = [
            self._aba_para_quadro(aba, ano, mes, divergencias)
            for nome, aba in abas.items()
            if (mes := self._mes_da_aba(nome)) is not None
        ]
        if not quadros:
            raise ValueError(f"{xlsx.name}: nenhuma aba no padrão MÊS-ANO")
        return pd.concat(quadros, ignore_index=True)

    def _mes_da_aba(self, nome: str) -> int | None:
        """Aba fora do padrão (resumo, notas, planilha vazia) é ignorada em silêncio."""
        encontrado = PADRAO_ABA.match(normalize_text(nome))
        if encontrado is None:
            return None
        return MESES.index(encontrado.group(1)) + 1

    def _aba_para_quadro(
        self,
        aba: pd.DataFrame,
        ano: int,
        mes: int,
        divergencias: DivergenciasEsquema,
    ) -> pd.DataFrame:
        quadro = self._renomear(aba, divergencias)
        quadro = self._converter_tipos(quadro)
        return self._derivar(quadro, ano, mes)

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
