---
spec: match-logradouros/002
versao: v2
atualizado_em: 2026-06-21
changelog: |
  v3 - codigo do script reorganizado para melhorar legibilidade e reuso
  v2 - adiciona utils de I/O para JSON (services/utils/io/json.py) e config
       compartilhado de _DATA_DIR (services/utils/io/config.py); o script passa
       a usar read_json_from_data em vez de json.load direto
  v1 - inicial
---

# SPEC match-logradouros/001 — Aumentar tipos de logradouro com variações por teclado

## User story
Como desenvolvedor do pipeline de dados, quero rodar um management command que expanda o
dicionário de tipos de logradouro com variações geradas por erros de digitação baseados na
proximidade de teclas no teclado QWERTY ABNT2, para que o sistema de matching tolere erros
típicos de digitação ao identificar o tipo de logradouro em um endereço livre.

## Critérios de aceite

### `services/utils/io/config.py` (novo)
- [ ] Existe um arquivo `config.py` em `services/utils/io/` que define a constante `_DATA_DIR`
      como o diretório `data/` na raiz do projeto, calculado de forma dinâmica e portável:
      `Path(__file__).resolve().parents[3] / "data"`.
- [ ] `_DATA_DIR` é a **única** definição de caminho para o diretório `data/` em todo o submódulo
      `services/utils/io/`. Nenhum outro módulo do submódulo define esse caminho de forma
      independente.

### `services/utils/io/parquet.py` (atualização)
- [ ] O módulo `parquet.py` **remove** sua definição local de `_DATA_DIR` e passa a importá-la
      de `.config`. Comportamento existente de `read_parquet_from_data` e `write_parquet_to_data`
      não muda.

### `services/utils/io/json.py` (novo)
- [ ] Existe um módulo `json.py` em `services/utils/io/` com duas **funções genéricas**:
      - `read_json_from_folder(folder: Path, filename: str) -> dict[str, Any]` — lê o arquivo
        `folder / filename` e retorna o conteúdo deserializado.
      - `write_json_to_folder(folder: Path, filename: str, data: dict[str, Any]) -> None` —
        serializa `data` e salva em `folder / filename` com `ensure_ascii=False` e `indent=2`.
- [ ] Ambas as funções genéricas usam encoding `utf-8` explicitamente.
- [ ] O módulo define dois **partials** via `functools.partial`, fixando `folder=_DATA_DIR`:
      - `read_json_from_data = partial(read_json_from_folder, _DATA_DIR)` — assinatura efetiva
        `(filename: str) -> dict[str, Any]`.
      - `write_json_to_data = partial(write_json_to_folder, _DATA_DIR)` — assinatura efetiva
        `(filename: str, data: dict[str, Any]) -> None`.
- [ ] Os partials são os **únicos símbolos exportados** pelo `__init__.py` de
      `services/utils/io/` para o resto do projeto. As funções genéricas são detalhe de
      implementação do módulo.
- [ ] `mypy` passa limpo; tipagem integral.

### Command de aumento (`apps/logradouro_matcher`)
- [ ] O command valida que todos os `values` únicos do JSON de entrada existem como
      `cd_tipo_logradouro` no parquet `nomes_logradouros.parquet`; tipos presentes no parquet mas
      ausentes no JSON são reportados como `WARNING` em amarelo no stdout do Django
      (`self.stdout.write(self.style.WARNING(...))`).
- [ ] O script lê o dicionário de entrada via **`read_json_from_data`** — não abre o arquivo
      diretamente nem monta caminho manualmente.
- [ ] Cada chave do dicionário passa por **`normalize_text`** antes de qualquer geração de
      variação. Após a normalização, as chaves estão em caixa alta, sem pontuação, sem acentos
      e sem cedilha.
- [ ] Para cada chave normalizada, o script gera todas as permutações de **um único caractere**
      substituído por um vizinho no teclado QWERTY ABNT2 (uma substituição por vez, em cada
      posição de letra do nome).
- [ ] O mapa de vizinhança cobre as 26 letras (A–Z), em **CAIXA ALTA**, e só contém vizinhos em
      `[A-Z0-9]` — sem caracteres especiais.
- [ ] Variações que já existam como chave no conjunto de entrada são descartadas (sem duplicatas).
- [ ] O resultado — entradas originais normalizadas + variações — é salvo em
      `tipos_logradouro_cache.parquet` via `write_parquet_to_data`, com colunas `nome_tipo`
      (string) e `cd_tipo_logradouro` (string).
- [ ] O command imprime em verde (`self.style.SUCCESS`) ao concluir: total de entradas originais,
      total de variações geradas e total de linhas salvas no parquet.
- [ ] O command é idempotente: rodar duas vezes produz o mesmo arquivo de saída.
- [ ] `mypy` passa limpo; tipagem integral.

## Contexto e decisões de arquitetura

### Camadas envolvidas
Esta SPEC toca exclusivamente o pipeline de dados — não há view, template nem lógica de
request/response. As camadas são:

- **`services/utils/io/`** — config compartilhado de `_DATA_DIR`, novos utilitários de JSON, e
  atualização do módulo de parquet para importar o config.
- **`apps/logradouro_matcher/management/commands/`** — command fino (parsing + chamada ao script
  + feedback). Sem lógica de negócio.
- **`services/scripts/`** — script puro com toda a lógica de geração de variações e validação.
  Não importa nada do Django.
- **`data/`** — lê `tipos_logradouro_aumentado.json` e `nomes_logradouros.parquet`; escreve
  `tipos_logradouro_cache.parquet`.

### Decisão: `_DATA_DIR` centralizado em `config.py`
Tanto o módulo de parquet quanto o de JSON precisam do mesmo caminho `data/`. Defini-lo em dois
lugares é um convite a desincronização. O `config.py` é a **fonte única de verdade** para esse
caminho dentro de `services/utils/io/`. O cálculo dinâmico via `Path(__file__).resolve().parents[3]`
garante portabilidade independente de onde o projeto estiver montado:

```
<project_root>/
└── services/
    └── utils/
        └── io/
            └── config.py   ← __file__
                               parents[0] = services/utils/io
                               parents[1] = services/utils
                               parents[2] = services
                               parents[3] = <project_root>  ✓
```

### Decisão: funções genéricas + partials (mesmo padrão do parquet)
As funções `read_json_from_folder` / `write_json_to_folder` operam sobre qualquer `Path`, o que
as torna testáveis com diretórios temporários sem tocar em `data/`. Os partials fixam `_DATA_DIR`
e são o que o resto do projeto usa — expondo uma interface de um argumento só (`filename`) para
leitura e dois (`filename`, `data`) para escrita, idêntica em forma à dos utilitários de parquet.

### Decisão: normalizar as chaves via `normalize_text` antes de gerar variações
As chaves do JSON chegam com grafia variada ("Rua", "Praça"). Ao passá-las por `normalize_text`
(entregue por `normalizacao-texto/001`), o script garante que o que grava no parquet e o que
buscará em runtime foram submetidos **à mesma transformação**. O mapa de vizinhança opera em caixa
alta — logo, após a normalização, o lookup de vizinhos é direto.

### Decisão: o script não faz nenhuma normalização própria
Toda preparação de string é responsabilidade de `normalize_text`. Sem conversão de caixa, remoção
de acento, substituição de cedilha ou pontuação no corpo do script além da chamada a
`normalize_text`.

### Decisão: mapa de vizinhança em caixa alta
Consistente com a saída do normalizador. Lookup direto: `vizinhos.get(ch, "")`, sem conversão.

### Decisão: uma substituição por posição
Suficiente para erros típicos com volume controlado. Combinações de duas trocas ou mais explodem
exponencialmente e não são credíveis como erros humanos únicos.

### Decisão: caracteres fora do mapa não geram variação nessa posição
Se `ch` não está no mapa (espaços, dígitos), o script pula aquela posição — o restante do nome
continua gerando variações normalmente.

### Fluxo resumido
```
[command] augment_logradouro_types
    │
    ▼
[script] augment_tipos_logradouro.run()
    │
    ├─ 1. read_json_from_data("tipos_logradouro_aumentado.json")  →  dict[str, str]
    │       └─ para cada chave: normalize_text(chave)
    │
    ├─ 2. read_parquet_from_data("nomes_logradouros.parquet")
    │       └─ extrai cd_tipo_logradouro únicos
    │            └─ tipos no parquet mas ausentes nos values → WARNING (amarelo)
    │
    ├─ 3. Para cada chave normalizada:
    │       para cada posição i onde chave[i] está no mapa:
    │             para cada vizinho v: variação = chave[:i] + v + chave[i+1:]
    │                  se variação não está no conjunto de chaves originais → acumula
    │
    ├─ 4. Monta df (nome_tipo, cd_tipo_logradouro), originais + variações, sem duplicatas
    │
    ├─ 5. write_parquet_to_data("tipos_logradouro_cache.parquet", df)
    │
    └─ 6. Retorna AugmentStats: n_original, n_variacoes, n_total, tipos_nao_mapeados
```

## Peças de referência a compor
- **`normalize_text`** — entregue por `normalizacao-texto/001`. Importar pelo `__init__.py` do
  seu submódulo; não alcançar o módulo interno.
- **`read_json_from_data`** / **`write_json_to_data`** — **entregues por esta SPEC** em
  `services/utils/io/json.py`. Usar para todo I/O de JSON; não abrir arquivos diretamente.
- **`read_parquet_from_data`** / **`write_parquet_to_data`** — pré-existentes em
  `services/utils/io/parquet.py`. Usar para todo I/O de parquet.
- **`data/tipos_logradouro_aumentado.json`** — dicionário de entrada (chave = nome por extenso,
  value = código do tipo, ex.: `"Rua": "R"`, `"Avenida": "AV"`).
- **`data/nomes_logradouros.parquet`** — base de logradouros; coluna `cd_tipo_logradouro` usada
  apenas para validação de códigos.

## Snippets sugeridos

### `services/utils/io/config.py`
```python
# services/utils/io/config.py
from pathlib import Path

# Raiz do projeto: services/utils/io/ está três níveis abaixo de <project_root>/
_DATA_DIR: Path = Path(__file__).resolve().parents[3] / "data"
```

### `services/utils/io/json.py`
```python
# services/utils/io/json.py
import json
from functools import partial
from pathlib import Path
from typing import Any

from .config import _DATA_DIR


# ---------- funções genéricas (testáveis com qualquer folder) ----------

def read_json_from_folder(folder: Path, filename: str) -> dict[str, Any]:
    with open(folder / filename, encoding="utf-8") as f:
        return json.load(f)


def write_json_to_folder(
    folder: Path, filename: str, data: dict[str, Any]
) -> None:
    with open(folder / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------- partials para data/ (uso público) ----------

read_json_from_data:  Any = partial(read_json_from_folder,  _DATA_DIR)
write_json_to_data: Any = partial(write_json_to_folder, _DATA_DIR)
```

> **Nota de tipagem:** `functools.partial` tem suporte limitado a mypy para preservar a assinatura
> tipada do partial. Usar `Any` temporariamente ou considerar `TypeAlias` + cast conforme a versão
> do mypy em uso.

### `services/utils/io/parquet.py` (trecho a atualizar)
```python
# remover a definição local de _DATA_DIR e substituir por:
from .config import _DATA_DIR

# o restante do módulo não muda
```

### `services/utils/io/__init__.py` (trecho relevante)
```python
from .json import read_json_from_data, write_json_to_data
from .parquet import read_parquet_from_data, write_parquet_to_data

__all__ = [
    "read_json_from_data",
    "write_json_to_data",
    "read_parquet_from_data",
    "write_parquet_to_data",
]
```

### Mapa de vizinhança QWERTY ABNT2 (CAIXA ALTA)
```python
# services/scripts/augment_tipos_logradouro.py
# Layout físico:
#   1 2 3 4 5 6 7 8 9 0
#    Q W E R T Y U I O P
#     A S D F G H J K L Ç
#      Z X C V B N M
# Ç representada como "C" — coerente com normalize_text.

QWERTY_ABNT2_NEIGHBORS: dict[str, str] = {
    "Q": "12WAS",   "W": "23QEASD",  "E": "34WRSDF",  "R": "45ETDFG",
    "T": "56RYFGH", "Y": "67TUGHJ",  "U": "78YIHJK",  "I": "89UOJKL",
    "O": "90IPKLC", "P": "0OLC",
    "A": "QWSZ",    "S": "QWEADZXC", "D": "WERSFXCV", "F": "ERTDGCVB",
    "G": "RTYFHVBN","H": "TYUGJBNM", "J": "YUIHKNM",  "K": "UIOJLM",
    "L": "IOPKC",
    "Z": "ASX",     "X": "ASDZC",    "C": "SDFXV",    "V": "CDFGB",
    "B": "VNFGH",   "N": "BGHJM",    "M": "NJHK",
}
```

### Script (esqueleto)
```python
# services/scripts/augment_tipos_logradouro.py
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from services.utils.io import read_json_from_data, read_parquet_from_data, write_parquet_to_data
from services.utils.<submódulo de normalização> import normalize_text

INPUT_JSON_NAME     = "tipos_logradouro_aumentado.json"
INPUT_PARQUET_NAME  = "nomes_logradouros.parquet"
OUTPUT_PARQUET_NAME = "tipos_logradouro_cache.parquet"
COL_CODIGO = "cd_tipo_logradouro"
COL_NOME   = "nome_tipo"

# (QWERTY_ABNT2_NEIGHBORS definido acima)


@dataclass
class AugmentStats:
    n_original: int
    n_variacoes: int
    n_total: int
    tipos_nao_mapeados: list[str] = field(default_factory=list)


def _gerar_variacoes(nome: str, vizinhos: dict[str, str]) -> set[str]:
    """
    `nome` já vem normalizado (CAIXA ALTA, sem acento, sem cedilha, sem pontuação);
    o mapa também é CAIXA ALTA, então o lookup é direto. Para cada posição i onde
    nome[i] está no mapa, gera variações substituindo nome[i] por cada vizinho.
    Não inclui o próprio nome.
    """
    variacoes: set[str] = set()
    for i, ch in enumerate(nome):
        for vizinho in vizinhos.get(ch, ""):
            variacoes.add(nome[:i] + vizinho + nome[i + 1:])
    variacoes.discard(nome)
    return variacoes


def run(
    input_json_name:     str = INPUT_JSON_NAME,
    input_parquet_name:  str = INPUT_PARQUET_NAME,
    output_parquet_name: str = OUTPUT_PARQUET_NAME,
) -> AugmentStats:
    """
    1. read_json_from_data(input_json_name) → aplica normalize_text a cada chave
    2. read_parquet_from_data(input_parquet_name) → valida cd_tipo_logradouro
    3. gera variações via _gerar_variacoes
    4. monta df (nome_tipo, cd_tipo_logradouro) sem duplicatas
    5. write_parquet_to_data(output_parquet_name, df)
    6. retorna AugmentStats
    """
    ...
```

### Command (esqueleto)
```python
# apps/logradouro_matcher/management/commands/augment_logradouro_types.py
from django.core.management.base import BaseCommand

from services.scripts.augment_tipos_logradouro import AugmentStats, run


class Command(BaseCommand):
    help = (
        "Expande o dicionário de tipos de logradouro com variações por "
        "erros de digitação (vizinhança QWERTY ABNT2) e salva em parquet."
    )

    def handle(self, *args: object, **options: object) -> None:
        stats: AugmentStats = run()

        for tipo in stats.tipos_nao_mapeados:
            self.stdout.write(
                self.style.WARNING(
                    f"AVISO: tipo '{tipo}' presente em nomes_logradouros.parquet "
                    f"mas ausente no dicionário de mapeamento."
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído. "
                f"Entradas originais: {stats.n_original} | "
                f"Variações geradas: {stats.n_variacoes} | "
                f"Total no parquet: {stats.n_total}"
            )
        )
```

## Fora de escopo
- **Qualquer normalização de string** além da chamada a `normalize_text`: sem conversão de caixa,
  remoção de acento, substituição de cedilha ou remoção de pontuação no script.
- **Variações de caixa** (alta/baixa): `normalize_text` garante caixa alta antes de qualquer
  geração.
- **Suporte a outros formatos de entrada** além de `dict[str, Any]` no `read_json_from_folder`.
- Geração de variações para o **nome do logradouro** (ex.: "PAULISTA" → "PUALISTA").
- Variações com **mais de uma substituição simultânea** por nome.
- Variações por **transposição de caracteres** (ex.: "RUA" → "RAU").
- Variações em posições com **caracteres fora do mapa** (dígitos, espaços).
- Qualquer lógica de **matching em runtime** — este script apenas pré-computa e persiste.
- Modificação de modelo Django ou criação de migration.

## Notas de teste

### `services/utils/io/config.py`
- `_DATA_DIR` aponta para `<project_root>/data/` independente de onde o processo é iniciado.

### `services/utils/io/json.py`
- **Round-trip:** `write_json_to_folder(tmp, "f.json", d)` seguido de `read_json_from_folder(tmp, "f.json")` retorna um dict igual a `d`.
- **Unicode preservado:** chaves e valores com acentos e caracteres especiais sobrevivem ao round-trip (`ensure_ascii=False`).
- **Partials expõem a assinatura reduzida:** `read_json_from_data("arquivo.json")` (1 arg) e `write_json_to_data("arquivo.json", d)` (2 args).
- **Funções genéricas testáveis** com diretório temporário, sem depender de `data/` real.

### Command de aumento
- **Caso feliz:** parquet com colunas `nome_tipo`/`cd_tipo_logradouro`, tudo em caixa alta, sem
  duplicatas; rodar duas vezes produz o mesmo resultado (idempotência).
- **Normalização aplicada:** `"Av. Paulista"` → `"AV PAULISTA"`; `"Praça"` → `"PRACA"`;
  `"Servidão"` → `"SERVIDAO"`.
- **Warning:** `cd_tipo_logradouro` presente no parquet mas ausente dos values do JSON emite
  WARNING (amarelo); o command conclui normalmente.
- **Variações de "RUA":** posição 0 (`R`, vizinhos `45ETDFG`) → `"4UA"`, `"5UA"`, `"EUA"`,
  `"TUA"`, `"DUA"`, `"FUA"`, `"GUA"`; posição 1 (`U`, `78YIHJK`) → `"R7A"`, `"R8A"`, `"RYA"`,
  `"RIA"`, `"RHA"`, `"RJA"`, `"RKA"`; posição 2 (`A`, `QWSZ`) → `"RUQ"`, `"RUW"`, `"RUS"`,
  `"RUZ"`.
- **Fora do mapa pulado:** posição com dígito ou espaço não gera variação.
- **Sem duplicatas:** variação coincidente com outra chave normalizada aparece uma única vez.
- **Cobertura do mapa:** 26 letras (A–Z) como chave; nenhum valor fora de `[A-Z0-9]`.

## Patches

1. Todo o código do script foi reorganizado em submódulos (arquivos.py) para melhorar legibilidade e reuso e manter padrão com os outros scripts.