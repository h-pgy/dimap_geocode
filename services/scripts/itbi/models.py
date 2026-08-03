from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from services.integrations.itbi import ItbiPortalConfig


class ItbiConfig(BaseModel):
    portal: ItbiPortalConfig = Field(default_factory=ItbiPortalConfig)


class ColetaStats(BaseModel):
    anos_baixados: list[int] = Field(default_factory=list)
    falhas_por_ano: dict[int, str] = Field(default_factory=dict)


class ParseStats(BaseModel):
    anos_parseados: list[int] = Field(default_factory=list)
    falhas_por_ano: dict[int, str] = Field(default_factory=dict)
    # Estavam na planilha e não no MAPA_COLUNAS: é o texto que se cola lá para adotá-las.
    colunas_desconhecidas_por_ano: dict[int, list[str]] = Field(default_factory=dict)
    # Estavam no MAPA_COLUNAS e não na planilha: saem nulas no parquet daquele ano.
    colunas_ausentes_por_ano: dict[int, list[str]] = Field(default_factory=dict)


class ConsolidacaoStats(BaseModel):
    anos_no_parquet: list[int] = Field(default_factory=list)
    total_records: int = 0


class DivergenciasEsquema(BaseModel):
    """O que a planilha de um ano tem a mais e a menos que o MAPA_COLUNAS, acumulado entre abas."""

    desconhecidas: list[str] = Field(default_factory=list)
    ausentes: list[str] = Field(default_factory=list)

    def acrescentar(self, desconhecidas: list[str], ausentes: list[str]) -> None:
        self.desconhecidas.extend(c for c in desconhecidas if c not in self.desconhecidas)
        self.ausentes.extend(c for c in ausentes if c not in self.ausentes)


class ColetaItbi(BaseModel):
    stats: ColetaStats


class ParseItbi(BaseModel):
    stats: ParseStats


class ConsolidacaoItbi(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    stats: ConsolidacaoStats
    dados: pd.DataFrame
    linhas_por_ano: dict[int, int] = Field(default_factory=dict)


class ItbiResult(BaseModel):
    coleta: ColetaStats
    parse: ParseStats
    consolidacao: ConsolidacaoStats
    output_path: Path
    linhas_por_ano: dict[int, int] | None = None  # só apurado com verbose

    @property
    def anos_desatualizados(self) -> list[int]:
        """No parquet com dado de uma carga anterior: não baixou OU não parseou agora."""
        atualizados = set(self.coleta.anos_baixados) & set(self.parse.anos_parseados)
        return sorted(set(self.consolidacao.anos_no_parquet) - atualizados)

    def para_metadados(self) -> dict[str, Any]:
        """O que sobrevive ao terminal: é daqui que sai o log do daemon dias depois."""
        return {
            "coleta": self.coleta.model_dump(mode="json"),
            "parse": self.parse.model_dump(mode="json"),
            "consolidacao": self.consolidacao.model_dump(mode="json"),
            "anos_desatualizados": self.anos_desatualizados,
            "linhas_por_ano": self.linhas_por_ano,
        }
