---
spec: match-logradouros/001
versao: v1
atualizado_em: 2026-06-21
changelog: v1 - inicial
---

# SPEC match-logradouros/001 — Normalizador de texto (string → string)

## User story
Como desenvolvedor do projeto, quero uma função única de normalização de texto — recebe uma
string e devolve uma string limpa e padronizada —, para que qualquer comparação textual no
sistema use sempre a mesma forma normalizada, em um único lugar.

## Critérios de aceite
- [ ] Existe uma classe normalizadora em `services/utils/<submódulo de normalização>` que é
      **callable**: `__call__(self, text: str) -> str`. Recebe uma string, devolve uma string.
- [ ] O `__call__` aplica, em sequência, um **pipeline** de etapas de limpeza que são **métodos da
      própria classe** nomeados no padrão **`_clean_<n>_<nome_semantico>`** (ex.:
      `_clean_1_remover_pontuacao`), onde `<n>` é um inteiro `>= 1` que **define a ordem** de
      aplicação e `<nome_semantico>` descreve o que a etapa faz. O número manda na ordem; o sufixo
      existe para legibilidade.
- [ ] O pipeline é montado por **introspecção** na construção: todos os métodos começados por
      `_clean` são descobertos e ordenados pelo número. Não há lista/registro manual de etapas.
- [ ] As checagens da construção são **decompostas em métodos de responsabilidade única** — um por
      tipo de checagem — e agregadas por um método (ex.: `_checar_metodos_pipeline`); a **ordenação**
      fica separada da checagem de sequência em um método próprio (ex.: `_ordenar_e_checar`), que
      devolve as etapas já ordenadas. O `_build_pipeline` apenas orquestra essas chamadas.
- [ ] A construção **valida o nome** de cada método descoberto com um **regex**
      (`^_clean_(\d+)_[a-z][a-z0-9_]*$`): um método começado por `_clean` que não tenha número
      **e** nome semântico levanta erro claro.
- [ ] A construção valida que a numeração é uma **sequência contígua a partir de 1, sem pular
      números** e que **não há dois métodos com o mesmo número**.
- [ ] A construção **valida a assinatura** de cada etapa: todas devem ter exatamente
      `(text: str) -> str`. Assinatura divergente levanta erro.
- [ ] **Todas essas validações acontecem no `__init__`** (na instanciação), com **erro semântico e
      claro** sobre o problema — nunca esperando o `__call__` rodar para quebrar.
- [ ] A classe é **instanciável sem nenhum parâmetro externo** (`__init__(self)`).
- [ ] A instância é criada **uma vez no `__init__.py` do submódulo** e exposta para fora **como
      função** (ex.: `normalize_text = NomeDaClasse()`). O resto do projeto importa e chama essa
      função; **não** instancia a classe nem alcança o módulo interno.
- [ ] Comportamento desta versão — e **apenas** isto:
      - remove **caracteres que são pontuação/símbolos** (preserva letras e dígitos);
      - troca **`ç`/`Ç` → `c`/`C`**;
      - **remove os acentos das letras, preservando a letra-base** (água → agua, égua → egua,
        avô → avo, São → Sao);
      - converte para **CAIXA ALTA**;
      - **colapsa espaços em branco** — espaços duplos, tabulações e quebras de linha viram um
        único espaço — e remove espaços nas pontas.
- [ ] A função é **idempotente**: `normalize_text(normalize_text(x)) == normalize_text(x)`.
- [ ] `mypy` passa limpo sobre o submódulo; tipagem integral.

## Contexto e decisões de arquitetura

### Camada
Mora **exclusivamente em `services/`** — em `services/utils/` (§7.1: utilitários de escopo geral,
sem domínio). **Não** depende do Django. **Não** é um management command e **não** toca `apps/`.
A unidade de trabalho é puramente string de entrada → string de saída; o normalizador não conhece
nenhum domínio nem nenhum consumidor específico.

### Decisão: normalização única
O CLAUDE.md (§7.1, §11) define a normalização como **uma só função**, usada em qualquer matching
textual — tanto na preparação de dados quanto na consulta. Centralizá-la aqui é o que evita o erro
clássico de normalizar de formas diferentes em pontos diferentes do sistema. Esta SPEC entrega
essa peça fundacional; os consumidores virão em SPECs próprias.

### Decisão: pipeline por introspecção de `_clean*`
A normalização é uma sequência de transformações pequenas e independentes. Modelá-la como um
**pipeline descoberto por introspecção** (`padrão command/pipeline simplificado`: um callable como
**ponto de entrada único** que executa etapas internas) deixa a extensão trivial — adicionar uma
transformação = adicionar um método `_clean_<n>_<nome>`, sem mexer no encadeamento. Esse é o
sentido de "command" aqui: o **padrão de projeto** (um objeto-ação invocável), **não** um
management command do Django.

### Decisão: ordem explícita via nomes numerados + sufixo semântico
A ordem das etapas é parte do contrato, então **não** se confia em acaso de nome (ordem
alfabética) nem em registro manual. As etapas são nomeadas `_clean_<n>_<nome_semantico>` (ex.:
`_clean_1_remover_pontuacao`, `_clean_3_remover_acentos`): o **número manda na ordem**, o
**sufixo** dá legibilidade ao que cada etapa faz.

### Decisão: checagens decompostas + ordenação separada
O `_build_pipeline` é **fino** e só orquestra:
1. **descobre** os candidatos (`_descobrir_candidatos` — métodos começados por `_clean`);
2. **checa** cada um via um agregador (`_checar_metodos_pipeline`), que chama uma checagem de
   responsabilidade única por regra: nome/regex (`_checar_nome`, devolve o número), assinatura
   (`_checar_assinatura`) e número repetido (`_checar_duplicado`);
3. **ordena e checa a sequência** (`_ordenar_e_checar`), que valida a contiguidade `1..n` e
   devolve as etapas já na ordem.

Tudo roda no `__init__`: o normalizador **falha na instanciação** com mensagem semântica clara
(qual método, qual problema), em vez de quebrar silenciosamente durante o `__call__`. Adicionar
uma etapa = criar `_clean_<próximo número>_<nome>` com a assinatura certa; nada mais a mexer.

> **Nota sobre cedilha × acentos.** A remoção de acentos (`_clean_3_remover_acentos`) usa
> decomposição Unicode (NFD) e, por consequência, **também removeria a cedilha**. A etapa
> dedicada de cedilha (`_clean_2_cedilha_para_c`) roda **antes** e existe para deixar a intenção
> explícita; tecnicamente é redundante com a remoção de acentos. Se a redundância incomodar, dá
> para dobrar tudo em `_clean_3` e remover a etapa de cedilha — decisão de implementação.

### Decisão: exposição como função, não como classe
A instância nasce no `__init__.py` do submódulo e é exportada como `normalize_text`. O contrato
público é a **função**; a classe é detalhe de implementação. Consumidores importam pelo
`__init__.py` exposto (§11), nunca alcançando o módulo interno.

## Peças de referência a compor
Nenhuma — é uma peça **fundacional nova**. Não compõe nada pré-existente nem é composta por
ninguém dentro do escopo desta SPEC (os consumidores chegam em SPECs próprias).

## Snippets sugeridos

```python
# services/utils/<submódulo de normalização>/normalizer.py
import inspect
import re
import unicodedata
from collections.abc import Callable

_CLEAN_PREFIX = "_clean"
_CLEAN_PATTERN = re.compile(r"^_clean_(\d+)_[a-z][a-z0-9_]*$")  # _clean_<n>_<nome_semantico>
_PUNCT_AND_SYMBOLS = re.compile(r"[^\w\s]", flags=re.UNICODE)    # o que não é letra/dígito/_/espaço
_UNDERSCORE = re.compile(r"_")
_WHITESPACE = re.compile(r"\s+")

_Etapa = Callable[[str], str]


def _expected_signature() -> inspect.Signature:
    return inspect.Signature(
        parameters=[
            inspect.Parameter("text", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=str),
        ],
        return_annotation=str,
    )


class TextNormalizer:
    """
    Normalizador de texto (string -> string). Padrão command/pipeline simplificado:
    __call__ é o ponto de entrada único e aplica, em ordem, os métodos _clean_<n>_<nome>.
    Não é um management command do Django — é só um callable em services.
    """

    def __init__(self) -> None:
        self._pipeline: list[_Etapa] = self._build_pipeline()

    # ---------- construção do pipeline (orquestra, fino) ----------
    def _build_pipeline(self) -> list[_Etapa]:
        candidatos = self._descobrir_candidatos()
        numerados = self._checar_metodos_pipeline(candidatos)
        return self._ordenar_e_checar(numerados)

    def _descobrir_candidatos(self) -> list[tuple[str, _Etapa]]:
        return [
            (name, method)
            for name, method in inspect.getmembers(self, predicate=inspect.ismethod)
            if name.startswith(_CLEAN_PREFIX)
        ]

    # ---------- checagens: uma por regra + um agregador ----------
    def _checar_metodos_pipeline(
        self, candidatos: list[tuple[str, _Etapa]]
    ) -> dict[int, tuple[str, _Etapa]]:
        numerados: dict[int, tuple[str, _Etapa]] = {}
        for name, method in candidatos:
            numero = self._checar_nome(name)
            self._checar_assinatura(name, method)
            self._checar_duplicado(name, numero, numerados)
            numerados[numero] = (name, method)
        if not numerados:
            raise ValueError("Nenhuma etapa '_clean_<n>_<nome>' encontrada no normalizador.")
        return numerados

    def _checar_nome(self, name: str) -> int:
        m = _CLEAN_PATTERN.match(name)
        if m is None:
            raise ValueError(
                f"Etapa de limpeza '{name}' não segue o padrão obrigatório "
                f"'_clean_<n>_<nome_semantico>' (n inteiro >= 1). Renomeie o método."
            )
        return int(m.group(1))

    def _checar_assinatura(self, name: str, method: _Etapa) -> None:
        if inspect.signature(method) != _expected_signature():
            raise TypeError(
                f"'{name}' deve ter assinatura (text: str) -> str; "
                f"recebido {inspect.signature(method)}."
            )

    def _checar_duplicado(
        self, name: str, numero: int, numerados: dict[int, tuple[str, _Etapa]]
    ) -> None:
        if numero in numerados:
            outro = numerados[numero][0]
            raise ValueError(
                f"Número de etapa duplicado: '{name}' e '{outro}' usam o índice {numero}. "
                f"Cada etapa deve ter um número único."
            )

    # ---------- ordenação + checagem de sequência ----------
    def _ordenar_e_checar(self, numerados: dict[int, tuple[str, _Etapa]]) -> list[_Etapa]:
        ordenados = sorted(numerados)
        esperado = list(range(1, len(ordenados) + 1))
        if ordenados != esperado:
            faltando = sorted(set(esperado) - set(ordenados))
            raise ValueError(
                f"Sequência de etapas inválida: encontrados {ordenados}, esperado {esperado} "
                f"(contígua a partir de 1, sem pular números). Faltando: {faltando}."
            )
        return [numerados[n][1] for n in ordenados]

    # ---------- ponto de entrada ----------
    def __call__(self, text: str) -> str:
        for etapa in self._pipeline:
            text = etapa(text)
        return text

    # ---------- etapas (o número define a ORDEM; o sufixo é semântico) ----------
    def _clean_1_remover_pontuacao(self, text: str) -> str:
        # remove caracteres que SÃO pontuação/símbolos; preserva letras e dígitos
        text = _PUNCT_AND_SYMBOLS.sub(" ", text)
        return _UNDERSCORE.sub(" ", text)

    def _clean_2_cedilha_para_c(self, text: str) -> str:
        return text.replace("ç", "c").replace("Ç", "C")

    def _clean_3_remover_acentos(self, text: str) -> str:
        # remove os diacríticos das letras, preservando a letra-base: água -> agua, avô -> avo
        decomposto = unicodedata.normalize("NFD", text)
        sem_marcas = "".join(c for c in decomposto if not unicodedata.combining(c))
        return unicodedata.normalize("NFC", sem_marcas)

    def _clean_4_caixa_alta(self, text: str) -> str:
        return text.upper()

    def _clean_5_colapsar_espacos(self, text: str) -> str:
        return _WHITESPACE.sub(" ", text).strip()
```

```python
# services/utils/<submódulo de normalização>/__init__.py
from .normalizer import TextNormalizer

# instância única, exposta como FUNÇÃO para o resto do projeto
normalize_text = TextNormalizer()

__all__ = ["normalize_text"]
```

```python
# consumo em qualquer lugar do projeto:
from services.utils.<submódulo de normalização> import normalize_text

normalize_text("  Av.  Paulista ")   # -> "AV PAULISTA"
normalize_text("Praça da Sé")         # -> "PRACA DA SE"  (ç -> c e acentos removidos)
normalize_text("água, égua e avô")    # -> "AGUA EGUA E AVO"
```

## Fora de escopo
- **Variações de caixa** ou geração de variantes de digitação: não é papel do normalizador.
- Qualquer **consumidor** específico ou lógica de domínio: a unidade aqui é string → string.
- Qualquer coisa em `apps/` ou management command.

## Notas de teste
- **Callable string → string:** `normalize_text("texto")` retorna `str`.
- **Pipeline numerado:** o pipeline montado contém os métodos `_clean_<n>_<nome>` ordenados pelo
  número (`_clean_1_...` → `_clean_2_...` → …), não por ordem alfabética.
- **Decomposição das checagens:** garantir que existe um método por checagem (nome, assinatura,
  duplicado), um agregador (`_checar_metodos_pipeline`) e a ordenação separada
  (`_ordenar_e_checar`); o `_build_pipeline` só orquestra.
- **Validações na construção (todas levantam na instanciação, não no `__call__`):**
  - **Nome fora do padrão:** uma subclasse com `_clean_6` (sem nome semântico) ou
    `_clean_punctuation` (sem número) levanta `ValueError` apontando o método.
  - **Número pulado:** etapas com números `1,2,3,4,5,7` (falta `6`) levantam `ValueError`
    indicando a sequência esperada e o que falta.
  - **Número duplicado:** dois métodos com o mesmo índice (ex.: `_clean_1_a` e `_clean_1_b`)
    levantam `ValueError` identificando ambos e o índice repetido.
  - **Assinatura divergente:** um `_clean_<n>_<nome>` com `(self, text, extra)` ou retorno ≠ `str`
    levanta `TypeError` apontando o método e a assinatura recebida.
- **Comportamento:**
  - `"  Av.  Paulista "` → `"AV PAULISTA"`
  - `"Rua\tda\nEsquina"` → `"RUA DA ESQUINA"` (tab e newline viram espaço único)
  - `"R. Direita, 123!"` → `"R DIREITA 123"` (pontuação removida, dígitos preservados)
  - `"Praça da Sé"` → `"PRACA DA SE"` (`ç` → `c` e acentos removidos)
  - `"água, égua e avô"` → `"AGUA EGUA E AVO"` (acentos das letras removidos, letra-base mantida)
  - `"AÇAÍ"` → `"ACAI"`
  - `"a_b"` → `"A B"` (underscore tratado como caractere a remover)
- **Idempotência:** aplicar duas vezes dá o mesmo resultado.
- **Sem parâmetros:** a classe instancia com `NomeDaClasse()` sem argumentos.
- **Exposição como função:** `from ... import normalize_text` é diretamente callable; o consumidor
  não precisa instanciar a classe.

## Patches
(nenhum ainda)