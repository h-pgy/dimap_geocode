---
spec: roteamento-busca/002
versao: v3
atualizado_em: 2026-06-24
changelog:
  - v1: versão inicial
  - v2: refatora ContribuinteMatcher para separação de responsabilidades no __call__
  - v3: move o parâmetro limite para o contrato de entrada ContribuinteMatchInput
---

# SPEC roteamento-busca/002 — Módulo de busca e correspondência de contribuintes - filtro_contribuinte

## User story
Como usuário, desejo buscar lotes filtrando por setor, quadra e lote, para acessar metadados de domínio de forma direta.

## Critérios de aceite
- [ ] Validar no contrato de entrada que o campo setor possui exatos três dígitos.
- [ ] Validar no contrato de entrada que o campo quadra possui três dígitos.
- [ ] Validar no contrato de entrada que o campo lote possui quatro dígitos.
- [ ] Rejeitar requisição no contrato de entrada caso o lote seja informado e a quadra não seja informada.
- [ ] Retornar resultados filtrados apenas por setor quando somente este campo for preenchido.
- [ ] Retornar resultados filtrados por setor e quadra quando ambos forem preenchidos.
- [ ] Retornar resultados filtrados por setor, quadra e lote quando os três atributos forem preenchidos.
- [ ] Mapear colunas do arquivo parquet para os atributos correspondentes no contrato de saída.

## Contexto e decisões de arquitetura
O módulo aloca-se em services/domain, isolado de regras de interface web e orquestração HTTP. A leitura de dados ocorre no arquivo parquet mantido no diretório data, utilizando a função utilitária padronizada de I/O do sistema para garantir o encapsulamento do acesso ao sistema de arquivos. O processamento utiliza a biblioteca pandas para filtragem em memória. Contratos de entrada e saída utilizam modelos Pydantic para garantir tipagem e sanitização antes do processamento.

## Peças de referência a compor
- @services/utils/io -> read_parquet_from_data: utilizar para leitura padronizada do arquivo de cache.
- Arquivo data/enderecos_fiscais.parquet com a carga consolidada dos dados fiscais.
- Modelos da biblioteca Pydantic para estruturação de contratos de entrada e saída.

## Snippets sugeridos
```python
import pandas as pd
from pydantic import BaseModel, Field, model_validator
from services.utils.io import read_parquet_from_data

class ContribuinteMatchInput(BaseModel):
    setor: str = Field(pattern=r"^\d{3}$")
    quadra: str | None = Field(default=None, pattern=r"^\d{3}$")
    lote: str | None = Field(default=None, pattern=r"^\d{4}$")
    dv: str | None = Field(default=None, pattern=r"^\d{2}$")
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
        self._dataframe = pd.DataFrame(read_parquet_from_data(nome_arquivo))

    def __call__(self, payload: ContribuinteMatchInput) -> list[ContribuinteMatchOutput]:
        if payload.lote:
            df = self._busca_lote(payload.setor, payload.quadra, payload.lote)
        elif payload.quadra:
            df = self._busca_quadra(payload.setor, payload.quadra).head(payload.limite)
        else:
            df = self._busca_setor(payload.setor).head(payload.limite)
        return self._mapear_resultados(df)

    def _busca_setor(self, setor: str) -> pd.DataFrame:
        return self._dataframe[self._dataframe["cd_setor_fiscal"] == setor]

    def _busca_quadra(self, setor: str, quadra: str) -> pd.DataFrame:
        df = self._busca_setor(setor)
        return df[df["cd_quadra_fiscal"] == quadra]

    def _busca_lote(self, setor: str, quadra: str, lote: str) -> pd.DataFrame:
        df = self._busca_quadra(setor, quadra)
        return df[df["cd_lote"] == lote]

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

Verificar comportamento do validador Pydantic perante inserção de atributos com comprimentos incompatíveis. Verificar lançamento de exceção ao prover lote sem a quadra correspondente. Assegurar tratamento de valores nulos nas colunas de dígito verificador e complemento de endereço durante o mapeamento para saída.

## Patches

- 2026-06-24 (v2): refatora `ContribuinteMatcher.__call__` para atuar apenas como dispatcher, delegando filtragem a `_busca_setor`, `_busca_quadra` e `_busca_lote` (cada um compondo o anterior) e mapeamento a `_mapear_resultados`.
- 2026-06-24 (v3): move `limite` de parâmetro do `__call__` para campo do `ContribuinteMatchInput` (`Field(default=5, gt=0)`), mantendo o contrato de entrada como fonte única dos parâmetros da busca.

```

```