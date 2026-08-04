from typing import ClassVar

import pandas as pd

from services.utils.normalization import normalize_text

from ..constants import MAPA_COLUNAS
from .base import ItbiPatcher

# JAN-2024 e OUT-2024 — levantado na primeira carga completa.
ANOS_CABECALHO_NO_RODAPE: tuple[int, ...] = (2024,)

# O layout da planilha do portal, na ordem em que as colunas aparecem. NÃO é derivado do
# MAPA_COLUNAS: aquele descreve o que publicamos, este descreve o que a fonte entrega — e a fonte
# tem `Bairro`, que não mapeamos.
CABECALHOS_CANONICOS: tuple[str, ...] = (
    "N° do Cadastro (SQL)",
    "Nome do Logradouro",
    "Número",
    "Complemento",
    "Bairro",
    "Referência",
    "CEP",
    "Natureza de Transação",
    "Valor de Transação (declarado pelo contribuinte)",
    "Data de Transação",
    "Valor Venal de Referência",
    "Proporção Transmitida (%)",
    "Valor Venal de Referência (proporcional)",
    "Base de Cálculo adotada",
    "Tipo de Financiamento",
    "Valor Financiado",
    "Cartório de Registro",
    "Matrícula do Imóvel",
    "Situação do SQL",
    "Área do Terreno (m2)",
    "Testada (m)",
    "Fração Ideal",
    "Área Construída (m2)",
    "Uso (IPTU)",
    "Descrição do uso (IPTU)",
    "Padrão (IPTU)",
    "Descrição do padrão (IPTU)",
    "ACC (IPTU)",
)

CABECALHOS_CONHECIDOS: frozenset[str] = frozenset(
    normalize_text(cabecalho) for cabecalho in MAPA_COLUNAS
)


class PatcherCabecalhoNoRodape(ItbiPatcher):
    """A aba foi publicada com a linha de título no FIM, e a primeira transação virou o cabeçalho.

    O teto do descarte por linha não pega este defeito: ele não produz linha que não converte,
    produz coluna nula — a aba inteira entraria vazia. A linha de título que ficou no corpo,
    essa sim, o teto descarta sozinho, porque texto não converte nas colunas numéricas.
    """

    anos: ClassVar[tuple[int, ...]] = ANOS_CABECALHO_NO_RODAPE

    def aplicar(self, aba: pd.DataFrame) -> pd.DataFrame:
        if self._tem_cabecalho(aba) or len(aba.columns) > len(CABECALHOS_CANONICOS):
            return aba
        # A transação promovida a cabeçalho não volta: a leitura já destruiu os valores dela
        # (célula vazia virou "Unnamed: N", valor repetido ganhou sufixo). É uma linha por aba.
        return aba.set_axis(list(CABECALHOS_CANONICOS[: len(aba.columns)]), axis=1)

    def _tem_cabecalho(self, aba: pd.DataFrame) -> bool:
        """Um casamento basta: é a assinatura que separa aba sã de aba com título no rodapé."""
        return any(
            normalize_text(str(coluna)) in CABECALHOS_CONHECIDOS for coluna in aba.columns
        )
