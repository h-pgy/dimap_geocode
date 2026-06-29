---
spec: roteamento-busca/002
versao: v5
atualizado_em: 2026-06-28
changelog:
  - v1: versão inicial
  - v2: refatora ContribuinteMatcher para separação de responsabilidades no __call__
  - v3: move o parâmetro limite para o contrato de entrada ContribuinteMatchInput
  - v4: altera ContribuinteMatcher para usar a propriedade cacheada _dataframe com @ttl_cached_property
  - v5: aceita entrada PARCIAL por nível (setor 1-3, quadra 1-3, lote 1-4) e casa por PREFIXO
        (startswith), não mais por igualdade exata — suporta sugestões durante a digitação
        (ver roteamento-busca/006)
---

# SPEC roteamento-busca/002 — Módulo de busca e correspondência de contribuintes - filtro_contribuinte

## User story
Como usuário, desejo buscar lotes filtrando por setor, quadra e lote — **mesmo com a numeração ainda
incompleta** —, para acessar metadados de domínio de forma direta e receber sugestões enquanto digito.

## Critérios de aceite
- [ ] Validar no contrato de entrada que o campo setor possui de **um a três** dígitos (entrada parcial permitida).
- [ ] Validar no contrato de entrada que o campo quadra possui de **um a três** dígitos (entrada parcial permitida).
- [ ] Validar no contrato de entrada que o campo lote possui de **um a quatro** dígitos (entrada parcial permitida).
- [ ] Rejeitar requisição no contrato de entrada caso o lote seja informado e a quadra não seja informada.
- [ ] Retornar resultados casados por **prefixo de setor** quando somente este campo for preenchido.
- [ ] Retornar resultados casados por **prefixo de setor e de quadra** quando ambos forem preenchidos.
- [ ] Retornar resultados casados por **prefixo de setor, quadra e lote** quando os três atributos forem preenchidos.
- [ ] Aplicar o `limite` ao conjunto casado por prefixo (válido para qualquer profundidade informada).
- [ ] Garantir que valor já completo case por prefixo **exatamente** como casaria por igualdade (sem regressão para entradas completas).
- [ ] Mapear colunas do arquivo parquet para os atributos correspondentes no contrato de saída.

## Contexto e decisões de arquitetura
O módulo aloca-se em services/domain, isolado de regras de interface web e orquestração HTTP. A leitura de dados ocorre no arquivo parquet mantido no diretório data, utilizando a função utilitária padronizada de I/O do sistema para garantir o encapsulamento do acesso ao sistema de arquivos. O processamento utiliza a biblioteca pandas para filtragem em memória, casando cada nível informado (setor, quadra, lote) **por prefixo (`startswith`)** sobre os códigos armazenados como strings zero-padded — assim a busca aceita numeração incompleta digitada pelo usuário e suporta sugestões a cada tecla (consumido pela roteamento-busca/006). Contratos de entrada e saída utilizam modelos Pydantic para garantir tipagem e sanitização antes do processamento.

## Peças de referência a compor
- @services/utils/io -> read_parquet_from_data: utilizar para leitura padronizada do arquivo de cache.
- Arquivo data/enderecos_fiscais.parquet com a carga consolidada dos dados fiscais.
- Modelos da biblioteca Pydantic para estruturação de contratos de entrada e saída.

## Snippets sugeridos
```python
import pandas as pd
from pydantic import BaseModel, Field, model_validator
from services.utils.cache import ttl_cached_property
from services.utils.io import read_parquet_from_data

class ContribuinteMatchInput(BaseModel):
    setor: str = Field(pattern=r"^\d{1,3}$")
    quadra: str | None = Field(default=None, pattern=r"^\d{1,3}$")
    lote: str | None = Field(default=None, pattern=r"^\d{1,4}$")
    dv: str | None = Field(default=None, pattern=r"^\d{1,2}$")
    limite: int = Field(default=5, gt=0)

    @model_validator(mode="after")
    def _validar_dependencia_quadra_lote(self) -> "ContribuinteMatchInput":
        if self.lote and not self.quadra:
            raise ValueError("A quadra deve ser informada quando o lote for preenchido.")
        return self

class ContribuinteMatchOutput(BaseModel):
    id_poligono: str
    setor: str
    quadra: str
    lote: str
    digito: str | None
    codlog: str
    logradouro: str
    numero: str
    complemento: str | None
    tipo_quadra: str
    tipo_lote: str

class ContribuinteMatcher:
    def __init__(self, nome_arquivo: str = "enderecos_fiscais.parquet"):
        self._nome_arquivo = nome_arquivo

    @ttl_cached_property(ttl_seconds=3600)
    def _dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(read_parquet_from_data(self._nome_arquivo))

    def __call__(self, payload: ContribuinteMatchInput) -> list[ContribuinteMatchOutput]:
        # casa por PREFIXO em cada nível informado (setor -> quadra -> lote), combinando-os
        df = self._dataframe
        mask = df["cd_setor_fiscal"].str.startswith(payload.setor)
        if payload.quadra:
            mask &= df["cd_quadra_fiscal"].str.startswith(payload.quadra)
        if payload.lote:
            mask &= df["cd_lote"].str.startswith(payload.lote)
        return self._mapear_resultados(df[mask].head(payload.limite))

    def _mapear_resultados(self, dataframe: pd.DataFrame) -> list[ContribuinteMatchOutput]:
        resultados = []
        for _, linha in dataframe.iterrows():
            resultados.append(
                ContribuinteMatchOutput(
                    id_poligono=str(linha["cd_identificador"]),
                    setor=str(linha["cd_setor_fiscal"]),
                    quadra=str(linha["cd_quadra_fiscal"]),
                    lote=str(linha["cd_lote"]),
                    digito=str(linha["cd_digito_sql"]) if pd.notna(linha["cd_digito_sql"]) else None,
                    codlog=str(linha["cd_logradouro"]),
                    logradouro=str(linha["nm_logradouro_completo"]),
                    numero=str(linha["cd_numero_porta"]),
                    complemento=str(linha["tx_complemento_endereco"]) if pd.notna(linha["tx_complemento_endereco"]) else None,
                    tipo_quadra=str(linha["cd_tipo_quadra"]),
                    tipo_lote=str(linha["cd_tipo_lote"])
                )
            )
        return resultados

```

## Fora de escopo

Consumo e orquestração de dados pela interface web. Formatação de resultados em componentes HTMX ou construção de views. Conversão espacial e persistência das geometrias em PostGIS.

## Notas de teste

Verificar comportamento do validador Pydantic perante inserção de atributos com comprimentos incompatíveis (acima do máximo por nível: setor >3, quadra >3, lote >4) e perante entradas parciais válidas (1-2 dígitos). Verificar lançamento de exceção ao prover lote sem a quadra correspondente. Verificar o casamento por prefixo: setor parcial (ex.: `"0"`) casa todos os setores que começam com o prefixo, limitado por `limite`; valor já completo casa por prefixo exatamente como por igualdade (regressão). Assegurar tratamento de valores nulos nas colunas de dígito verificador e complemento de endereço durante o mapeamento para saída.

## Patches

- 2026-06-24 (v2): refatora `ContribuinteMatcher.__call__` para atuar apenas como dispatcher, delegando filtragem a `_busca_setor`, `_busca_quadra` e `_busca_lote` (cada um compondo o anterior) e mapeamento a `_mapear_resultados`.
- 2026-06-24 (v3): move `limite` de parâmetro do `__call__` para campo do `ContribuinteMatchInput` (`Field(default=5, gt=0)`), mantendo o contrato de entrada como fonte única dos parâmetros da busca.
- 2026-06-26 (v4): altera `ContribuinteMatcher` para inicializar de forma preguiçosa (lazy) usando a propriedade cacheada `@ttl_cached_property` para o `_dataframe`.
- 2026-06-28 (v5): aceita entrada **parcial por nível** — `ContribuinteMatchInput` passa a `setor` `^\d{1,3}$`, `quadra` `^\d{1,3}$`, `lote` `^\d{1,4}$`, `dv` `^\d{1,2}$` (regra "lote exige quadra" mantida) — e o `ContribuinteMatcher` casa por **prefixo** (`startswith`) em cada nível informado, combinando-os e aplicando `limite`, em vez de igualdade exata. Substitui os helpers `_busca_setor`/`_busca_quadra`/`_busca_lote` por uma máscara combinada no `__call__`. Habilita as sugestões durante a digitação da roteamento-busca/006; entradas completas continuam casando como antes.