---
spec: roteamento_busca/011
versao: v2
atualizado_em: 2026-07-03
implementado: true
changelog:
  - v2: "patch 001 — badge de condomínio e propagação de cd_condominio/is_condominio no template resultados_endereco_lote.html"
  - v1: versão inicial
---

# SPEC roteamento_busca/011 — Informação de condomínio na lista de sugestões de contribuinte

- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como usuário da busca simples, ao digitar um número de contribuinte e ver a lista de sugestões de
lotes, quero saber **quais lotes são condominiais** (e qual é o código do condomínio de cada um),
para que ao clicar numa sugestão eu saiba que estou selecionando um lote condominial específico — e
para que, numa iteração futura, o sistema consiga filtrar a geocodificação apenas pelo condomínio
que escolhi (em vez de trazer todos os condomínios da mesma quadra com lote `0000`).

## Critérios de aceite

- [x] O catalog de contribuintes (`ContribuinteCatalog`) expõe uma **coluna booleana
      `is_condominio`** no DataFrame cacheado, derivada de `cd_condominio != '00'` (a coluna
      `cd_condominio` já existe no parquet como `str`; `'00'` significa "não é condomínio").
- [x] O model `ContribuinteMatchOutput` tem dois novos atributos: **`cd_condominio: str`** (o
      código do condomínio como string, ex. `'00'`, `'01'`) e **`is_condominio: bool`**.
- [x] A função `mapear_resultados` em `parser.py` popula os dois novos atributos a partir das
      colunas do DataFrame (`cd_condominio` e `is_condominio`).
- [x] O model `ContribuinteParse` (em `services/domain/roteamento_busca/models.py`) ganha os
      atributos **`cd_condominio: str | None`** e **`is_condominio: bool | None`** com defaults
      `None`, pois o parse da entrada digitada não tem essa informação — ela só chega quando o
      matcher retorna os resultados.
- [x] O `ContribuinteIdentifier` (em `contribuinte.py`) é **refatorado**: a função `__call__`
      atual concentra validação de codlog, extração de dígitos, montagem do parse e aplicação de
      regras em um único corpo; deve ser separada em métodos menores com nomes semânticos (ex.:
      `_parece_codlog`, `_extrair_digitos`, `_montar_parse`) para legibilidade, **sem alterar o
      comportamento externo**.
- [x] O template `resultados_contribuinte.html` propaga `cd_condominio` e `is_condominio` no
      `hx-vals` de cada `<li>` (o POST vai para `lote_geocoder:geocodificar`, que hoje ignora
      esses campos — a SPEC seguinte os consumirá), e exibe um **badge visual** (ex.:
      "Cond. 03") quando `is_condominio` é verdadeiro, para que o usuário distinga lotes
      condominiais dos demais na lista.

## Contexto e decisões de arquitetura

Esta SPEC toca **três camadas** na vertical:

1. **Domínio (`services/`)** — adiciona a coluna computada `is_condominio` no catalog, estende
   o DTO de saída do matcher e o DTO de parse do roteador, e refatora o identifier de
   contribuinte para legibilidade.
2. **Interface (template)** — atualiza o partial `resultados_contribuinte.html` para exibir
   badge de condomínio e propagar os campos no `hx-vals`.
3. **Persistência** — nenhuma alteração; os dados já existem no parquet (`cd_condominio`).

### Por que uma coluna materializada no catalog em vez de computed_field no model?

A coluna `is_condominio` é derivada de `cd_condominio != '00'`, que poderia ser uma propriedade
computada do `ContribuinteMatchOutput`. No entanto, materializar no DataFrame traz dois
benefícios futuros:

- Na **busca detalhada** será possível filtrar `df[df["is_condominio"]]` *antes* do match,
  evitando iterar sobre lotes não condominiais — filtro de coluna booleana em pandas é O(n)
  vetorizado, muito mais rápido que computar por linha.
- Qualquer outro consumidor do catalog (futuros matchers, exports) herda a coluna sem
  recomputar.

### Padrão do número de contribuinte

- Lote **condominial**: `<SETOR-3d><QUADRA-3d><0000>-<COND-2d>` — lote sempre `0000`,
  condomínio ≠ `00` (ex.: `001.002.0000-03`).
- Lote **não condominial**: `<SETOR-3d><QUADRA-3d><LOTE-4d>-<00>` — condomínio sempre `00`
  (ex.: `001.002.0015-00`).

### Fluxo dos dados (de onde vem, para onde vai)

```
parquet (cd_condominio str)
  → ContribuinteCatalog.enderecos_fiscais (coluna is_condominio adicionada)
    → ContribuinteMatcher → mapear_resultados → list[ContribuinteMatchOutput]
      → secao_contribuinte passa resultados direto ao template (valores reais do DB)
        → template exibe badge + propaga cd_condominio/is_condominio no hx-vals
          → POST para lote_geocoder:geocodificar (SPEC seguinte consome esses campos)
```

**Ponto-chave:** a função `secao_contribuinte` já recebe `ContribuinteParse` (entrada do
usuário, com `cd_condominio=None`), mas **não passa o parse para o template** — ela chama o
matcher e entrega `list[ContribuinteMatchOutput]` como `resultados`. Os objetos
`ContribuinteMatchOutput` já vêm com `cd_condominio` e `is_condominio` reais do DataFrame.
**Nenhuma alteração é necessária em `secao_contribuinte`** para que o template acesse os
valores corretos.

O template propaga `cd_condominio` e `is_condominio` no `hx-vals` do POST para
`lote_geocoder:geocodificar`. A view `geocodificar` atual **ignora** esses campos (cria
`LoteGeocodInput` só com `setor/quadra/lote/tipo_lote`) — usá-los para filtrar a
geocodificação é objetivo da **SPEC seguinte**. Nesta SPEC, basta que os dados estejam
**visíveis** na lista de sugestões e **disponíveis no POST** para consumo futuro.

### Refactor do ContribuinteIdentifier

O `__call__` atual faz tudo num só corpo:

1. Detecta se parece codlog (guarda contra `12345-1` ser tratado como contribuinte).
2. Extrai dígitos puros removendo separadores.
3. Valida comprimento e tipo.
4. Monta o `ContribuinteParse`.
5. Aplica regras de validação.

Cada passo vira um método privado com nome semântico. O fluxo fica:

```python
def __call__(self, texto, finished_typing) -> ContribuinteParse | None:
    bruto = texto.strip()
    if self._parece_codlog(bruto):
        return None
    digitos = self._extrair_digitos(bruto)
    if digitos is None:
        return None
    parse = self._montar_parse(digitos)
    if not self._validar_regras(parse):
        return None
    return parse
```

**Sem mudança de comportamento externo** — puro refactor.

## Peças de referência a compor

- `services/domain/contribuinte_match/catalog.py` → `ContribuinteCatalog`: adicionar coluna
  `is_condominio` no DataFrame cacheado `enderecos_fiscais`.
- `services/domain/contribuinte_match/models.py` → `ContribuinteMatchOutput`: estender com
  `cd_condominio` e `is_condominio`.
- `services/domain/contribuinte_match/parser.py` → `mapear_resultados`: popular os novos
  atributos a partir do DataFrame.
- `services/domain/roteamento_busca/models.py` → `ContribuinteParse`: adicionar
  `cd_condominio` e `is_condominio` com defaults.
- `services/domain/roteamento_busca/contribuinte.py` → `ContribuinteIdentifier`: refatorar
  `__call__` em métodos menores.
- `templates/lote_matcher/partials/resultados_contribuinte.html`: propagar `cd_condominio` e
  `is_condominio` no `hx-vals` e exibir badge de condomínio.

## Snippets sugeridos

### Catalog — coluna booleana materializada

```python
# em ContribuinteCatalog.enderecos_fiscais — enderecos_fiscais_com_chave herda via .copy()
df["is_condominio"] = df["cd_condominio"] != "00"
```

### ContribuinteMatchOutput — novos atributos

```python
class ContribuinteMatchOutput(BaseModel):
    # ... atributos existentes ...
    cd_condominio: str
    is_condominio: bool
```

### mapear_resultados — popular novos atributos

```python
ContribuinteMatchOutput(
    # ... campos existentes ...
    cd_condominio=str(linha["cd_condominio"]),
    is_condominio=bool(linha["is_condominio"]),
)
```

### ContribuinteParse — defaults None

```python
class ContribuinteParse(BaseModel):
    # ... campos existentes ...
    cd_condominio: str | None = None
    is_condominio: bool | None = None
```

### ContribuinteIdentifier refatorado

```python
class ContribuinteIdentifier:
    def __init__(self, regras: tuple[RegraContribuinte, ...] = REGRAS_CONTRIBUINTE) -> None:
        self._regras = regras

    def __call__(self, texto: str, finished_typing: bool) -> ContribuinteParse | None:
        bruto = texto.strip()
        if self._parece_codlog(bruto):
            return None
        digitos = self._extrair_digitos(bruto)
        if digitos is None:
            return None
        parse = self._montar_parse(digitos)
        if not self._validar_regras(parse):
            return None
        return parse

    def _parece_codlog(self, bruto: str) -> bool:
        """Guarda: '12345-1' (codlog com DV) não deve ser tratado como contribuinte."""
        return "." not in bruto and DASH_CODLOG.fullmatch(bruto) is not None

    def _extrair_digitos(self, bruto: str) -> str | None:
        """Remove separadores e valida que o resultado é numérico com tamanho válido."""
        digitos = SEPARADORES.sub("", bruto)
        if not digitos or not digitos.isdigit() or len(digitos) > COMP_COM_DV:
            return None
        return digitos

    def _montar_parse(self, digitos: str) -> ContribuinteParse:
        return ContribuinteParse(
            setor=digitos[0:3],
            quadra=digitos[3:6],
            lote=digitos[6:10],
            dv=digitos[10:12],
        )

    def _validar_regras(self, parse: ContribuinteParse) -> bool:
        return all(regra(parse) for regra in self._regras)
```

### Template — badge de condomínio + propagação

```html
<li class="py-3 flex items-baseline gap-4 cursor-pointer hover:bg-base-200"
    hx-post="{% url 'lote_geocoder:geocodificar' %}"
    hx-vals='{"setor": "{{ r.setor }}", "quadra": "{{ r.quadra }}", "lote": "{{ r.lote }}", "tipo_lote": "{{ r.tipo_lote }}", "cd_condominio": "{{ r.cd_condominio }}", "is_condominio": "{{ r.is_condominio }}"}'
    hx-target="#resultado-busca"
    hx-swap="innerHTML"
>
  <span class="font-mono text-sm text-base-content/60 w-32 shrink-0">
    {{ r.setor }}.{{ r.quadra }}.{{ r.lote }}{% if r.digito %}-{{ r.digito }}{% endif %}
  </span>
  <span class="badge badge-sm badge-ghost shrink-0">{{ r.tipo_lote }}</span>
  {% if r.is_condominio %}
    <span class="badge badge-sm badge-info shrink-0">Cond. {{ r.cd_condominio }}</span>
  {% endif %}
  <span class="font-medium">
    {{ r.logradouro }}, {{ r.numero }}{% if r.complemento %} — {{ r.complemento }}{% endif %}
  </span>
</li>
```



## Fora de escopo

- **Filtrar a geocodificação por condomínio** — o `LoteGeocoder` e a view `geocodificar`
  continuam buscando por `setor/quadra/lote/tipo_lote` sem filtrar por `cd_condominio`. Essa
  melhoria (a "dor" de buscar `0000` e trazer todos os condomínios da quadra) é a próxima SPEC.
- **Busca direta por condomínio na entrada** — quando o próprio usuário digita um número de
  contribuinte condominial (padrão `<SETOR><QUADRA>0000-<COND>`), o parse já teria como
  identificar que é condomínio e popular `cd_condominio`/`is_condominio` no `ContribuinteParse`.
  Isso ficará para uma SPEC futura — por ora os campos ficam `None` no parse e são preenchidos
  apenas pelos resultados do matcher.
- **Busca detalhada com filtro "apenas condomínios"** — a coluna `is_condominio` no catalog
  habilita esse cenário, mas a UI de busca detalhada não existe ainda.
- **Alterações no `LoteGeocoder` ou no `LoteGeocodInput`** — nenhum atributo de condomínio é
  adicionado ao fluxo de geocodificação nesta SPEC.
- **Testes unitários** — ver Notas de teste.

## Notas de teste

- **`ContribuinteCatalog`**: verificar que o DataFrame retornado por `enderecos_fiscais` tem a
  coluna `is_condominio` com tipo `bool`, e que um registro com `cd_condominio='00'` tem
  `is_condominio=False` enquanto `cd_condominio='03'` tem `is_condominio=True`.
- **`mapear_resultados`**: com um DataFrame de fixture contendo `cd_condominio` e
  `is_condominio`, verificar que o `ContribuinteMatchOutput` sai com os valores corretos.
- **`ContribuinteIdentifier`**: refactor é puro — os mesmos inputs produzem os mesmos outputs.
  Rodar os testes existentes (se houver) garante não-regressão.
- **Template**: smoke test manual — digitar um contribuinte condominial (ex.: `001.002.0000`)
  e confirmar que o badge "Cond. XX" aparece na sugestão; digitar um não-condominial e
  confirmar que o badge não aparece.

## Patches

### Patch 001 (v2) — Badge de condomínio em `resultados_endereco_lote.html`

O template `resultados_endereco_lote.html` não foi atualizado junto com
`resultados_contribuinte.html` na implementação original. Faltavam:

1. **`hx-vals`**: propagação de `cd_condominio` e `is_condominio` no POST para
   `lote_geocoder:geocodificar`.
2. **Badge visual**: `{% if r.is_condominio %}<span class="badge badge-sm badge-info shrink-0">Cond. {{ r.cd_condominio }}</span>{% endif %}`
   após o badge de `tipo_lote`.

A view `secao_endereco_lote` não precisou de alteração — já passa
`list[ContribuinteMatchOutput]` (que contém `cd_condominio` e `is_condominio`) ao template.
