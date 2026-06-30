---
spec: match-logradouros/006
versao: v1
atualizado_em: 2026-06-29
implementado: true
changelog:
  - v1: versão inicial
---

# SPEC match-logradouros/006 — Seleção de logradouro carrega codlog + dígito verificador

- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como consumidor futuro da resolução de geometria do logradouro (a linha), quero que o **clique numa
sugestão de logradouro** — tanto na lista **por nome** quanto na lista **por codlog** — envie ao
servidor o **codlog (5 dígitos) _e_ o dígito verificador (DV)**, e não apenas o codlog, para que o
logradouro seja identificado pelo seu **código completo** (os 6 dígitos do cadastro da PMSP) na hora
de resolver a linha — evitando ambiguidade e re-resolução desnecessária.

Hoje a seleção de logradouro (roteamento_busca/008) posta **só o codlog de 5 dígitos**. O DV existe
no cadastro (é o 6º caractere do `codlog` bruto no parquet, já extraído por `CodlogMatcher` como
`dv`), mas é **descartado** no caminho por nome (`LogradouroCatalog._rows` fatia `c[:5]` — patch p2
da 008) e **não é enviado** por nenhuma das duas listas de sugestão. Esta iteração faz o DV
**fluir do catálogo até o `hx-vals`** e ser **recebido e validado** pelo DTO de seleção.

## Critérios de aceite

- [ ] O DTO de saída do domínio de logradouro **`LogradouroMatchOutput`** passa a carregar o
      **`dv`** (dígito verificador, 1 dígito), ao lado de `codlog` (5 dígitos), `tipo_codigo` e
      `nome_logradouro` — **espelhando** `CodlogMatchOutput` (que já tem `codlog` + `dv`).
- [ ] O **`codlog` permanece com 5 dígitos** (não desfazer o patch p2 da 008): o DV é um **campo
      separado**, extraído do **6º caractere** do `codlog` bruto do parquet, do mesmo modo que
      `CodlogMatcher` faz (`codlog=[:5]`, `dv=[5]`).
- [ ] A fonte do DV é o **`LogradouroCatalog`**: a linha do catálogo (`LogradouroRow`) passa a expor
      o DV junto do codlog, lendo-o do `codlog` bruto de 6 caracteres — **uma normalização única** da
      origem, consumida por todos os matchers (não há parsing de codlog espalhado).
- [ ] **Ambos os matchers** que produzem `LogradouroMatchOutput` preenchem o `dv`: o **literal**
      (`LiteralLogradouroMatcher`, usado nas sugestões) e o **fuzzy** (`LogradouroMatcher`, usado no
      match final). Nenhum dos dois reimplementa o fatiamento do codlog — ambos recebem o DV já
      resolvido pelo catálogo.
- [ ] A lista de sugestões de **logradouro por nome** (`resultados_logradouro.html`) e a de
      **logradouro por codlog** (`resultados_codlog.html`), ao clicar num item, postam no `hx-vals`
      **codlog _e_ dígito verificador** para a rota de seleção de logradouro
      (`logradouro_matcher:selecionar`) — não mais só o codlog.
- [ ] O DTO de seleção **`LogradouroSelection`** (em `apps/logradouro_matcher/schemas.py`) ganha o
      campo do **dígito verificador** (1 dígito, padrão `^\d$`), mantendo o `codlog` em `^\d{1,5}$`.
      A view `selecionar` lê o DV do `POST` e o repassa ao DTO; `ValidationError` continua borbulhando
      ao middleware (sem `try/except`).
- [ ] O *partial* de confirmação `_selecao.html` exibe o **código completo** do logradouro
      selecionado (codlog + DV, ex.: `12345-6`), refletindo que a seleção agora carrega o DV.
- [ ] Tipagem integral; `mypy` limpo. As respostas seguem sendo *partials* HTML (§3.1).

## Contexto e decisões de arquitetura

Esta SPEC cruza **domínio** (`services/domain/logradouros_match`) e **interface/orquestração**
(`apps/logradouro_matcher` + *partials*), mas é uma iteração coesa: "carregar o DV junto do codlog
na seleção do logradouro". O épico é o de **match de logradouros** — por isso a SPEC mora em
`SPECS/match_logradouros/` (e não em `roteamento_busca/`, onde nasceu a seleção clicável da 008).

> **Por que o DV é do domínio, não do template.** O DV faz parte do **código oficial** do logradouro
> (6 dígitos no cadastro). Extraí-lo é regra de leitura do dado, e o projeto já a tem num lugar só:
> `CodlogMatcher` (`codlog=[:5]`, `dv=[5]`). Esta SPEC **centraliza** essa mesma leitura no
> `LogradouroCatalog`, de onde os dois matchers (literal e fuzzy) bebem — em vez de fatiar codlog no
> template ou em cada matcher. Isso respeita §7.1 (normalização/leitura única) e §3.2 (sem regra de
> negócio no template).

> **Por que `codlog` continua com 5 dígitos.** O patch p2 da roteamento_busca/008 corrigiu um 422:
> `LogradouroSelection.codlog` é `^\d{1,5}$`, e postar 6 dígitos quebrava a validação. A solução
> **não** é alargar o codlog para 6 — é manter o codlog em 5 e enviar o **DV como campo próprio**,
> simétrico ao `CodlogMatchOutput`. Assim domínio, DTO e UI ficam consistentes.

> **Por que ambos os matchers mudam juntos.** `LogradouroMatchOutput` é o contrato compartilhado pelo
> matcher literal (sugestões) e pelo fuzzy (match final). Ao ganhar o campo `dv`, os dois pontos de
> construção precisam preenchê-lo — caso contrário um deles quebra a tipagem/validação. Como ambos
> constroem o output a partir do `LogradouroRow` do catálogo, basta o catálogo expor o DV e cada
> matcher repassá-lo.

### Fluxo

```
LogradouroCatalog._rows lê o parquet (codlog bruto = 6 chars)
   → LogradouroRow{ codlog=[:5], dv=[5], cd_tipo_logradouro, nm_logradouro }
        │
        ├─ LiteralLogradouroMatcher._build  → LogradouroMatchOutput{ codlog, dv, ... }  (sugestões por nome)
        └─ LogradouroMatcher._build_result  → LogradouroMatchOutput{ codlog, dv, ... }  (match fuzzy final)

resultados_logradouro.html / resultados_codlog.html
   <li hx-vals='{"codlog": "{{ r.codlog }}", "digito_verificador": "{{ r.dv }}"}'> …
        │  POST → logradouro_matcher:selecionar
        ▼
selecionar(request): LogradouroSelection(codlog=…, digito_verificador=…)
   → render _selecao.html  (exibe codlog-DV)
```

## Peças de referência a compor

- `@services/domain/codlog_match` → `CodlogMatcher` / `CodlogMatchOutput`: **padrão** de extração do
  DV (`codlog=[:5]`, `dv=[5]`) e do contrato `codlog` + `dv`. Espelhar, não recriar.
- `@services/domain/logradouros_match/catalog.py` → `LogradouroCatalog._rows` /
  `linhas_por_nome` / `linhas_do_tipo` / `todas_as_linhas`: ponto único onde o `LogradouroRow` é
  montado a partir do parquet — é aqui que o DV passa a ser lido.
- `@services/domain/logradouros_match/models.py` → `LogradouroRow` e `LogradouroMatchOutput`:
  contratos a estender com o `dv`.
- `@services/domain/logradouros_match/literal_matcher.py` (`_build`) e
  `@services/domain/logradouros_match/matcher.py` (`_build_result`): os **dois** pontos que
  constroem `LogradouroMatchOutput` — ambos repassam `dv=row.dv`.
- `@apps/logradouro_matcher/schemas.py` → `LogradouroSelection`: DTO a estender com o DV.
- `@apps/logradouro_matcher/views.py` → `selecionar`: lê o DV do `POST` e monta o DTO.
- `@templates/logradouro_matcher/partials/resultados_logradouro.html` e
  `@templates/logradouro_matcher/partials/resultados_codlog.html` → as duas listas que postam a
  seleção: incluir o DV no `hx-vals`.
- `@templates/logradouro_matcher/partials/_selecao.html` → partial de confirmação: exibir codlog+DV.
- **SPEC roteamento_busca/008** (seleção clicável, patches p1/p2): contexto direto desta iteração —
  o DTO em `schemas.py` e o codlog de 5 dígitos vêm de lá.
- **SPEC infraestrutura/001** (`PydanticValidationMiddleware`) + skill `pydantic-validation-errors`:
  `ValidationError` vira 422 automaticamente; a view não usa `try/except`.

## Snippets sugeridos

```python
# services/domain/logradouros_match/models.py — DTOs ganham o dv
class LogradouroRow(BaseModel):
    codlog: str            # 5 dígitos
    dv: str                # 1 dígito (6º char do codlog bruto)
    cd_tipo_logradouro: str
    nm_logradouro: str


class LogradouroMatchOutput(BaseModel):
    codlog: str            # 5 dígitos
    dv: str                # 1 dígito
    tipo_codigo: str
    nome_logradouro: str
```

```python
# services/domain/logradouros_match/catalog.py — _rows lê o DV junto do codlog
return [
    LogradouroRow(codlog=c[:5], dv=c[5], cd_tipo_logradouro=t, nm_logradouro=n)
    for c, t, n in zip(codlogs, tipos, nomes)
]
```

```python
# literal_matcher._build  e  matcher._build_result — ambos repassam o dv
LogradouroMatchOutput(
    codlog=row.codlog,
    dv=row.dv,
    tipo_codigo=row.cd_tipo_logradouro,
    nome_logradouro=row.nm_logradouro,
)
```

```python
# apps/logradouro_matcher/schemas.py — seleção carrega o DV
class LogradouroSelection(BaseModel):
    codlog: str = Field(pattern=r"^\d{1,5}$")
    digito_verificador: str = Field(pattern=r"^\d$")
```

```python
# apps/logradouro_matcher/views.py — selecionar lê o DV do POST
selecao = LogradouroSelection(
    codlog=request.POST.get("codlog", ""),
    digito_verificador=request.POST.get("digito_verificador", ""),
)
```

```htmldjango
{# resultados_logradouro.html / resultados_codlog.html — <li> posta codlog + DV #}
<li
  class="py-3 flex items-baseline gap-4 cursor-pointer hover:bg-base-200"
  hx-post="{% url 'logradouro_matcher:selecionar' %}"
  hx-vals='{"codlog": "{{ r.codlog }}", "digito_verificador": "{{ r.dv }}"}'
  hx-target="#resultado-busca"
  hx-swap="innerHTML"
>
  …
</li>
```

## Fora de escopo

- **Resolução de geometria do logradouro** (a linha) e plotagem no mapa Leaflet — a seleção continua
  *stub* (imprime/confirma), como na 008. O DV apenas passa a estar disponível para a iteração futura.
- **Validação do DV pela fórmula** (consistência entre codlog e dígito): o DTO só valida o **formato**
  (1 dígito). A checagem algorítmica do DV (o `_validar_dv` de `CodlogMatchInput`, ainda
  `NotImplementedError`) é assunto de outra SPEC.
- **Seleção de lote e de endereço**: esta SPEC mexe só na seleção de **logradouro**.
- **Busca detalhada** (campos segmentados) e qualquer rota direta nova.
- **Estilização final** do `_selecao.html`/listas.

## Notas de teste

<Só para referência futura — não implementar agora.>

- Clique numa sugestão de logradouro **por nome** posta `codlog` (5 díg.) **e** `digito_verificador`
  (1 díg.) corretos; idem para a lista **por codlog**.
- `LogradouroMatchOutput` produzido pelo matcher **literal** e pelo **fuzzy** traz o `dv` coerente com
  o 6º caractere do codlog bruto.
- `LogradouroSelection` rejeita DV vazio ou com mais de 1 dígito → 422 via middleware (não 500).
- `codlog` continua com 5 dígitos (regressão do patch p2 da 008 — nada de 6 dígitos no POST).
- `_selecao.html` exibe o código completo (ex.: `12345-6`).
- `mypy` limpo após o novo campo nos DTOs e nos dois pontos de construção.

## Patches

_Nenhum patch registrado até o momento._
