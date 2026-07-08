---
spec: roteamento_busca/013
versao: v2
atualizado_em: 2026-07-06
implementado: true
changelog:
  - v1: versão inicial
  - v2: fuzzy também nas sugestões (keyup) quando o literal vem vazio, exibindo grau de
        certeza por item; resolvedor passa a devolver itens com score e a distinguir modo
        sugestão/commit (guarda de tamanho mínimo do nome só na sugestão)
---

# SPEC roteamento_busca/013 — Fallback fuzzy na busca (sugestões e commit)

- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como usuário da busca, quero que, quando digito um nome de logradouro com erro (ex.:
"avenida palista" ou "avenida palista, 100") e o match literal não encontra nada, o sistema me
mostre nas sugestões **quais** logradouros parecidos encontrou e **com qual grau de certeza** —
e, se eu pressionar Enter mesmo assim, que busque direto o melhor deles (linha do logradouro,
ou ponto do endereço quando digitei também um número), para nunca ficar sem feedback por causa
de um erro de digitação.

## Critérios de aceite
- [x] Digitar `avenida palista` (literal vazio) e aguardar o keyup exibe sugestões vindas do
      fuzzy, cada uma com seu **grau de certeza** visível, e a seção sinaliza que são
      resultados **aproximados**.
- [x] Clicar numa sugestão fuzzy aciona a mesma seleção de hoje (geocodifica o item clicado).
- [x] Enter em `avenida palista` (sem clicar em sugestão) renderiza a **linha** da Avenida
      Paulista no mapa (melhor match fuzzy), sem depender de a lista ter aparecido.
- [x] Enter em `avenida palista, 100` (e também na forma sem vírgula `avenida palista 100`)
      renderiza o **ponto** geocodificado do número 100 da Avenida Paulista.
- [x] O fuzzy só roda quando o match literal devolve vazio: buscas que hoje resolvem pelo
      literal continuam com exatamente o mesmo resultado e as sugestões literais não mudam.
- [x] Nas sugestões, o fuzzy só roda a partir de um tamanho mínimo de nome digitado (evita
      ruído e custo no início da digitação); no Enter/commit não há tamanho mínimo.
- [x] Entrada sem nenhum match razoável (melhor score fuzzy abaixo do threshold) continua sem
      seção de sugestão e, no Enter, responde o aviso atual de "não foi possível localizar".
- [x] O fuzzy do token de tipo roda sobre as variações aumentadas de tipo de logradouro
      (que já incluem erros de digitação), e o fuzzy do nome roda preferencialmente restrito
      ao universo do tipo resolvido.

## Contexto e decisões de arquitetura

Hoje tanto as sugestões de keyup (`secao_logradouro`, `secao_endereco`) quanto o Enter
(`comitar` → `_acionar_candidato`) usam apenas o `match_logradouro_literal`
(prefixo/substring sobre nome normalizado). Quando o usuário erra a digitação, o literal
devolve vazio: a seção de sugestão é **omitida** (usuário sem feedback nenhum) e o Enter cai
no aviso de "sem resultado" — mesmo existindo um logradouro obviamente próximo.

O motor fuzzy para isso **já existe e está ocioso**: `match_logradouro` (`LogradouroMatcher`,
SPEC match_logradouros/004) resolve o token de tipo por levenshtein sobre as variações
aumentadas de tipo (dicionário que já embute erros de digitação: "avnida" → AV etc.), restringe
o universo de nomes ao tipo resolvido e roda jaro_winkler sobre os nomes, com fallback global.
Esta SPEC **não cria matching novo** — ela compõe o que existe em um ponto único de decisão,
consumido pelos dois fluxos (sugestão e commit).

Camadas envolvidas:

- **Domínio (`services/domain/logradouros_match`):** nasce um *resolvedor* de logradouro — a
  regra "tenta literal; se vazio, tenta fuzzy; aceita itens só acima de um threshold" é regra
  de negócio e por isso mora no domínio, não na view. O resolvedor é uma classe callable
  (§10.4) que **compõe** o `LiteralLogradouroMatcher`, o `LogradouroMatcher` e o
  `LogradouroCatalog` existentes, com DTO Pydantic nas duas pontas. Decisões:
  - O resultado é uma lista de **itens com score** (`score` preenchido quando a origem é
    fuzzy, `None` no literal) + flag `usou_fuzzy` — é o que permite à UI exibir o grau de
    certeza e sinalizar "aproximado".
  - No caminho fuzzy, os itens vêm dos **top-N nomes** do `match_nome` (não só do melhor),
    cada um resolvido para suas linhas via catálogo — as sugestões mostram alternativas,
    não um único palpite.
  - A query declara o **modo** (`sugestao` | `commit`): no modo sugestão há um tamanho
    mínimo de nome para acionar o fuzzy (constante do módulo); no commit, não — Enter é
    intenção explícita, busca-se sempre. Threshold de aceite e tamanho mínimo são
    constantes `UPPER_CASE` do módulo.
- **Orquestração (sugestões — `apps/logradouro_matcher` e `apps/address_geocoder`):**
  `secao_logradouro` e `secao_endereco` trocam o literal pelo resolvedor. Com `usou_fuzzy`,
  os partials de resultados exibem o score por item (ex.: badge "≈ 87%") e o título da seção
  sinaliza aproximação. A seleção por clique não muda de mecânica (mesmos endpoints de
  `selecionar`).
- **Orquestração (commit — `apps/search`):** `_acionar_candidato` troca, nos branches
  `LogradouroParse` e `EnderecoParse`, a chamada direta ao literal pela chamada ao resolvedor
  em modo commit. O restante é intocado: com codlog resolvido, `LogradouroParse` segue para
  `geocodificar_codlog` (linha) e `EnderecoParse` para `geocodificar_endereco` (ponto com o
  número). Os branches de código exato (`CODLOG`, `CONTRIBUINTE`, `ENDERECO_CODLOG`,
  `ENDERECO_LOTE`) **não** ganham fuzzy — código é identificador exato (CLAUDE.md §1).

Ponto importante: a detecção de "nome de rua + número = endereço" **já é feita pelo router**
(`EnderecoParse` embute um `LogradouroParse` + `numero`). Esta SPEC não mexe no roteamento —
só no que acontece quando o match literal do logradouro falha.

Custo do fuzzy no keyup: mitigado por (1) só rodar com literal vazio; (2) tamanho mínimo de
nome no modo sugestão; (3) o universo do nome ser restrito ao tipo resolvido no caminho comum;
(4) o debounce de 300ms já existente no `hx-trigger`.

O feedback visual do Enter (lista aparecer por um tempo + animação do item selecionado) é
iteração de frontend à parte — **SPEC design/002**, que se aplica a todos os tipos de busca.

Fluxo resumido:

```
keyup → rotear_busca → secao_logradouro / secao_endereco
  └─ resolver_logradouro(modo=sugestao)
       literal com resultado → sugestões literais (como hoje, sem score)
       literal vazio + nome ≥ mínimo → fuzzy → sugestões aproximadas com score
       abaixo do threshold / nome curto → seção omitida (como hoje)

Enter → comitar → rotear_entrada → candidatos ordenados
  ├─ LogradouroParse → resolver_logradouro(modo=commit)
  │     literal vazio? → match_logradouro (fuzzy: tipo aumentado → nome no universo do tipo)
  │     score ≥ threshold → codlog → geocodificar_codlog → LINHA
  └─ EnderecoParse → resolver_logradouro(modo=commit) [mesma peça]
        codlog resolvido → geocodificar_endereco(codlog, numero) → PONTO
  (resolvedor devolve vazio → próximo candidato → sem nada: aviso atual)
```

## Peças de referência a compor
- `@services/domain/logradouros_match` → `LogradouroMatcher` / `match_logradouro`: o motor
  fuzzy completo (tipo aumentado + nome por tipo + fallback global). **Reusar como está.**
- `@services/domain/logradouros_match` → `LiteralLogradouroMatcher` /
  `match_logradouro_literal`: o caminho literal que continua sendo a primeira tentativa.
- `@services/domain/logradouros_match` → `LogradouroCatalog` (instância única `_catalog` do
  módulo, e `linhas_por_nome`): resolve os top-N nomes do fuzzy para linhas com codlog; o
  resolvedor compõe as instâncias já expostas no `__init__.py`.
- `@services/utils/fuzzy_matcher` → `FuzzyMatchResult`/`FuzzyMatchItem` (scores por item);
  a SPEC não chama `fuzzy_match` diretamente — consome via `LogradouroMatcher`.
- `@apps/search/views.py` → `comitar` e `_acionar_candidato`: orquestração do Enter; só os
  branches `LogradouroParse` e `EnderecoParse` mudam.
- `@apps/logradouro_matcher/views.py` → `secao_logradouro` + partial
  `resultados_logradouro.html`; `@apps/address_geocoder/views.py` → `secao_endereco` +
  partial `resultados_endereco_nome.html`: pontos de sugestão que passam a usar o resolvedor
  e a exibir score quando fuzzy.
- `@apps/logradouro_geocoder` → `geocodificar_codlog` e `@apps/address_geocoder` →
  `geocodificar_endereco`: destinos inalterados após resolver o codlog.
- `@services/domain/roteamento_busca` → `LogradouroParse`, `EnderecoParse`: DTOs de entrada
  que alimentam o resolvedor (tipo_logradouro + nome; numero no caso do endereço).
- Skill `componentes-frontend` (badge/estilo do grau de certeza nos partials).

## Snippets sugeridos

```python
# services/domain/logradouros_match — direção do resolvedor (adaptar sem violar §3/§10)
FUZZY_ACCEPT_THRESHOLD = 80.0
FUZZY_MIN_CHARS_SUGESTAO = 4


class ResolucaoLogradouroQuery(BaseModel):
    nome: str
    tipo: str | None = None
    limite: int = 5
    modo: Literal["sugestao", "commit"] = "commit"


class ResolucaoLogradouroItem(BaseModel):
    logradouro: LogradouroMatchOutput
    score: float | None = None  # None = veio do literal; preenchido = grau de certeza fuzzy


class ResolucaoLogradouroResult(BaseModel):
    itens: list[ResolucaoLogradouroItem]
    usou_fuzzy: bool


class LogradouroResolver:
    def __init__(
        self,
        literal: LiteralLogradouroMatcher,
        fuzzy: LogradouroMatcher,
        catalog: LogradouroCatalog,
        threshold: float = FUZZY_ACCEPT_THRESHOLD,
    ) -> None: ...

    def __call__(self, query: ResolucaoLogradouroQuery) -> ResolucaoLogradouroResult:
        return self._pipeline(query)

    def _pipeline(self, query: ResolucaoLogradouroQuery) -> ResolucaoLogradouroResult:
        literal = self._tentar_literal(query)
        if literal.logradouros:
            return self._result_literal(literal)
        if not self._fuzzy_permitido(query):
            return ResolucaoLogradouroResult(itens=[], usou_fuzzy=False)
        return self._tentar_fuzzy(query)

    def _fuzzy_permitido(self, query: ResolucaoLogradouroQuery) -> bool:
        return query.modo == "commit" or len(query.nome.strip()) >= FUZZY_MIN_CHARS_SUGESTAO

    def _tentar_fuzzy(self, query: ResolucaoLogradouroQuery) -> ResolucaoLogradouroResult:
        texto = f"{query.tipo} {query.nome}".strip() if query.tipo else query.nome
        resultado = self._fuzzy(LogradouroMatchQuery(texto=texto, limite=query.limite))
        # top-N nomes acima do threshold → linhas via catálogo, carregando o score de cada nome
        itens = [
            ResolucaoLogradouroItem(logradouro=self._to_output(row), score=m.similarity_score)
            for m in resultado.match_nome.matches
            if m.similarity_score >= self._threshold
            for row in self._linhas_do_nome(m.original_string, resultado)
        ]
        return ResolucaoLogradouroResult(itens=itens[: query.limite], usou_fuzzy=True)
```

```python
# apps/search/views.py — branches afetados de _acionar_candidato (direção)
if isinstance(candidato, LogradouroParse):
    item = _primeiro(resolver_logradouro(ResolucaoLogradouroQuery(
        nome=candidato.nome, tipo=candidato.tipo_logradouro or None, modo="commit",
    )).itens)
    if item is None:
        return None
    logr = item.logradouro
    return geocodificar_codlog(request, f"{logr.codlog}{logr.dv}")

if isinstance(candidato, EnderecoParse):
    item_end = _primeiro(resolver_logradouro(ResolucaoLogradouroQuery(
        nome=candidato.logradouro.nome,
        tipo=candidato.logradouro.tipo_logradouro or None,
        modo="commit",
    )).itens)
    if item_end is None:
        return None
    logr_end = item_end.logradouro
    return geocodificar_endereco(request, f"{logr_end.codlog}{logr_end.dv}", candidato.numero)
```

```html
<!-- partials de sugestão — direção do grau de certeza (usar skill componentes-frontend) -->
{% if item.score is not None %}
  <span class="badge badge-sm" title="Similaridade">≈ {{ item.score|floatformat:0 }}%</span>
{% endif %}
```

## Fora de escopo
- O **feedback visual do Enter** (lista visível por um tempo + animação do item acionado) —
  SPEC design/002, transversal a todos os tipos de busca.
- Fuzzy para códigos exatos (codlog, contribuinte, endereço-codlog, endereço-lote).
- UI de "você quis dizer…?" além do badge de score/título de seção aproximada.
- Ajuste fino do threshold ou troca de algoritmo do `LogradouroMatcher` — usa-se o motor
  como está.
- Fallback fuzzy no fluxo do endereço-lote ("Rua X, s/n") — depende de decidir como o fuzzy
  interage com o match fiscal; fica para SPEC própria se necessário.
- Cache/otimização adicional do fuzzy por keyup (se o custo real incomodar, é iteração
  própria).

## Notas de teste
(Só quando explicitamente solicitado — CLAUDE.md §13.)
- Resolvedor: literal com resultado → não chama fuzzy e itens vêm sem score; literal vazio +
  fuzzy acima do threshold → itens com score e `usou_fuzzy=True`; abaixo do threshold →
  vazio; modo sugestão com nome curto → vazio sem rodar fuzzy; modo commit com nome curto →
  roda fuzzy.
- Sugestões: `rotear_busca` com "avenida palista" devolve seção com badges de score;
  com literal resolvendo, resposta idêntica à atual.
- `comitar` com "avenida palista" → resposta renderiza linha (status 200, partial do mapa);
  com "avenida palista, 100" → ponto; com texto sem match plausível → partial de aviso.
- Regressão: entradas que resolviam pelo literal produzem a mesma resposta de antes.
- Borda: candidato `EnderecoParse` cujo fuzzy resolve, mas o número não geocodifica →
  comportamento atual de seguir ao próximo candidato/aviso.

## Patches

_Nenhum patch registrado até o momento._
