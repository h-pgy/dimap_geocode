---
spec: roteamento-busca/003
versao: v1
atualizado_em: 2026-06-26
changelog:
  - v1: versão inicial
---

# SPEC roteamento-busca/003 — Módulo de busca e correspondência de codlog - filtro_codlog

## User story
Como usuário, desejo buscar logradouros filtrando por código de logradouro (codlog), parcial ou completo, para obter as informações do logradouro de forma direta.

## Critérios de aceite
- [ ] Rejeitar requisição no contrato de entrada caso `input_codlog` tenha mais de 5 dígitos.
- [ ] Rejeitar requisição no contrato de entrada caso `input_codlog` seja vazio ou contenha caracteres não numéricos.
- [ ] Rejeitar requisição no contrato de entrada caso `digito_verificador` tenha mais de 1 dígito ou contenha caracteres não numéricos.
- [ ] Realizar busca por prefixo (`startswith`) quando `input_codlog` tiver menos de 5 dígitos.
- [ ] Realizar busca por igualdade (`equals`) quando `input_codlog` tiver exatamente 5 dígitos.
- [ ] A busca opera apenas sobre os 5 primeiros dígitos da coluna `codlog` do parquet.
- [ ] Retornar no máximo `limite` resultados.
- [ ] Mapear cada linha resultante para o contrato de saída com os campos: `codlog`, `dv`, `tipo_logradouro`, `nome_logradouro` e a propriedade calculada `nome_completo`.
- [ ] O campo `codlog` da saída contém apenas os 5 primeiros dígitos da coluna original.
- [ ] O campo `dv` da saída contém apenas o 6º dígito da coluna original.
- [ ] A propriedade `nome_completo` concatena `tipo_logradouro` e `nome_logradouro`.

## Contexto e decisões de arquitetura

O módulo aloca-se em `services/domain`, isolado de regras de interface web e orquestração HTTP. Segue o mesmo padrão estabelecido pelo módulo `contribuinte_match` (SPEC 002): classe callable com `__call__`, contrato de entrada/saída via Pydantic e carregamento preguiçoso do parquet via `@ttl_cached_property`.

A coluna `codlog` do parquet tem 6 dígitos: os 5 primeiros são o código do logradouro; o 6º é o dígito verificador. A separação é feita na saída (mapeamento), não no dado bruto.

**Busca em duas modalidades:**
- `input_codlog` com 1–4 dígitos → `startswith` (prefixo): útil para sugestões durante digitação.
- `input_codlog` com 5 dígitos → igualdade exata sobre os primeiros 5 dígitos.

**Dígito verificador:** o campo `digito_verificador` existe no contrato de entrada mas **não é usado na busca nesta versão**. Um método de validação (`_validar_dv`) é declarado no modelo Pydantic como ponto de extensão para quando a lógica do DV for especificada.

**Coluna auxiliar `_codlog5`:** para evitar recomputação a cada busca, o DataFrame cacheado pelo `@ttl_cached_property` já inclui uma coluna `_codlog5` com os 5 primeiros dígitos de `codlog`, derivada uma única vez no carregamento.

**Carregamento dos dados:** o DataFrame é carregado de forma preguiçosa e cacheado por `@ttl_cached_property`, evitando leitura do disco a cada instanciação — mesmo padrão da SPEC 002 (v4).

## Peças de referência a compor
- `@services/utils/cache` → `ttl_cached_property`: usar para cache preguiçoso do DataFrame.
- `@services/utils/io` → `read_parquet_from_data`: usar para leitura padronizada do parquet.
- Arquivo `data/nomes_logradouros.parquet` com as colunas: `codlog` (str, 6 dígitos), `cd_tipo_logradouro` (str), `nm_logradouro` (str).
- Modelos da biblioteca Pydantic para estruturação dos contratos de entrada e saída.

## Snippets sugeridos

```python
import pandas as pd
from pydantic import BaseModel, Field
from services.utils.cache import ttl_cached_property
from services.utils.io import read_parquet_from_data

NOME_ARQUIVO_PADRAO = "nomes_logradouros.parquet"


class CodlogMatchInput(BaseModel):
    input_codlog: str = Field(pattern=r"^\d{1,5}$")
    digito_verificador: str | None = Field(default=None, pattern=r"^\d$")
    limite: int = Field(default=5, gt=0)

    def _validar_dv(self) -> bool:
        """Ponto de extensão: validar se digito_verificador é consistente
        com input_codlog segundo a fórmula do DV. A implementar."""
        raise NotImplementedError


class CodlogMatchOutput(BaseModel):
    codlog: str          # primeiros 5 dígitos da coluna codlog
    dv: str              # 6º dígito da coluna codlog
    tipo_logradouro: str
    nome_logradouro: str

    @property
    def nome_completo(self) -> str:
        return f"{self.tipo_logradouro} {self.nome_logradouro}"


class CodlogMatcher:
    def __init__(self, nome_arquivo: str = NOME_ARQUIVO_PADRAO) -> None:
        self._nome_arquivo = nome_arquivo

    @ttl_cached_property(ttl_seconds=3600)
    def _dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame(read_parquet_from_data(self._nome_arquivo))
        df["_codlog5"] = df["codlog"].str[:5]
        return df

    def __call__(self, payload: CodlogMatchInput) -> list[CodlogMatchOutput]:
        df = self._filtrar(payload.input_codlog)
        return self._mapear_resultados(df.head(payload.limite))

    def _filtrar(self, input_codlog: str) -> pd.DataFrame:
        if len(input_codlog) < 5:
            return self._dataframe[self._dataframe["_codlog5"].str.startswith(input_codlog)]
        return self._dataframe[self._dataframe["_codlog5"] == input_codlog]

    def _mapear_resultados(self, dataframe: pd.DataFrame) -> list[CodlogMatchOutput]:
        resultados: list[CodlogMatchOutput] = []
        for _, linha in dataframe.iterrows():
            resultados.append(
                CodlogMatchOutput(
                    codlog=str(linha["codlog"])[:5],
                    dv=str(linha["codlog"])[5],
                    tipo_logradouro=str(linha["cd_tipo_logradouro"]),
                    nome_logradouro=str(linha["nm_logradouro"]),
                )
            )
        return resultados


match_codlog = CodlogMatcher()
```

## Fora de escopo

- Validação da conta do dígito verificador (stub declarado, implementação futura).
- Busca por nome de logradouro (texto livre / fuzzy) — pertence a outro módulo.
- Consumo e orquestração pela interface web, views e componentes HTMX.
- Conversão espacial e persistência em PostGIS.

## Notas de teste

Verificar busca por prefixo com 1, 2, 3 e 4 dígitos retornando apenas logradouros cujo codlog começa com o prefixo informado. Verificar busca exata com 5 dígitos. Verificar que o limite é respeitado. Verificar que `codlog` na saída contém exatamente 5 dígitos e `dv` contém exatamente 1. Verificar que `nome_completo` concatena corretamente `tipo_logradouro` e `nome_logradouro`. Verificar rejeição de `input_codlog` com 6+ dígitos e com caracteres não numéricos. Verificar rejeição de `digito_verificador` com 2+ dígitos.

## Patches

_Nenhum patch registrado até o momento._
