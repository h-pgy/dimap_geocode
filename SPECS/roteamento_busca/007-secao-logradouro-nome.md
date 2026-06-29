---
spec: roteamento-busca/007
versao: v1
atualizado_em: 2026-06-28
implementado: false
changelog:
  - v1: versão inicial
---

# SPEC roteamento-busca/007 — Seção de sugestões de logradouro por nome (pluga o literal matcher no roteador)

- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como usuário, quando eu começar a digitar o **nome de um logradouro** (com ou sem o tipo, ex.:
`PAULISTA`, `AV PAULISTA`, `RUA DIREITA`) na barra de pesquisa única da home, quero ver — já a cada
tecla — **sugestões de logradouros** cujo nome contém o que digitei, agrupadas na sua própria seção,
lado a lado com as demais (logradouro por codlog, lote por contribuinte), para escolher rapidamente o
logradouro certo sem precisar dizer ao sistema que estou buscando por nome e sem digitar o nome
inteiro.

Esta iteração **encaixa a seção de logradouro-por-nome** na estrutura extensível do roteador
(roteamento-busca/005), espelhando exatamente o que a roteamento-busca/006 fez para o contribuinte:
o roteador já classifica a entrada como `LOGRADOURO` e emite um `LogradouroParse` (com
`tipo_logradouro` e `nome`); o domínio do match literal **já existe** (`match_logradouro_literal`).
Falta apenas a **interface** que adapta o candidato em DTO, chama o domínio e renderiza a seção.

## Critérios de aceite

- [ ] Existe um **renderer** `secao_logradouro` no app `logradouro_matcher` que recebe o candidato
      **`LogradouroParse`** (do roteador) e devolve **sempre** uma **`SecaoResultado`** (título + HTML
      do *partial*) — o mesmo contrato que o registro do `search` já espera
      (`apps/search/secoes.py`), sem admitir `None` (a busca literal sempre produz uma seção).
- [ ] O renderer **adapta** o `LogradouroParse` para **`LiteralLogradouroQuery`** passando o texto
      **como digitado**: `nome` ← `candidato.nome` e `tipo` ← `candidato.tipo_logradouro` quando houver
      (tipo vazio vira **`None`**, nunca `""`).
- [ ] O renderer chama o domínio **`match_logradouro_literal`** (instância singleton de
      `LiteralLogradouroMatcher`, exposta no `__init__.py` de `services/domain/logradouros_match`) com
      o DTO, **sem** reimplementar nenhuma lógica de matching.
- [ ] O registro extensível do `search` (`REGISTRO_SECOES`) passa a mapear
      **`TipoEntrada.LOGRADOURO` → `secao_logradouro`**, **sem alterar** o laço de `rotear_busca` nem o
      *partial* agregador `_sugestoes.html` (a estrutura da 005 é reaproveitada como está).
- [ ] O título da seção identifica o critério, distinto da seção de codlog — ex.:
      **"Logradouro (por nome)"** (a seção de codlog permanece "Logradouro (por codlog)").
- [ ] O `logradouro_matcher` tem um *partial* próprio `resultados_logradouro.html` que recebe o
      **`LiteralLogradouroResult`** (lista de **`LogradouroMatch`** + flag `ignorou_filtro_tipo`) e
      renderiza cada logradouro exibindo pelo menos o **nome do logradouro** e o **codlog**; lista
      vazia exibe um aviso de "nenhum logradouro encontrado".
- [ ] Quando `ignorou_filtro_tipo` for **`True`** (o tipo digitado não foi reconhecido e o match caiu
      para todos os tipos), o *partial* exibe um **aviso discreto** ao usuário (ex.: "tipo não
      reconhecido — mostrando todos os logradouros"); quando `False`, nenhum aviso aparece.
- [ ] Entrada **ambígua** continua coerente: uma entrada que gere candidatos `LOGRADOURO` **e**
      `ENDERECO` (ou outros) faz **cada** seção aparecer no seu próprio `<section>`, sem interferência.
- [ ] A **rota POST direta de codlog** (`buscar_codlog` em `apps/logradouro_matcher`), criada apenas
      para teste na roteamento-busca/004, é **removida** — junto com a entrada correspondente no
      `urls.py` do app e a inclusão agora obsoleta em `config/urls.py`. O único consumidor das seções
      passa a ser o roteador, via registro (espelhando o desenho da 006, que não tem rota direta).
- [ ] A pasta de templates do `logradouro_matcher` já é descoberta pelo Tailwind 4 (o `@source` de
      `apps/` e `templates/` cobre por *glob*; confirmar que não é preciso novo `@source`).
- [ ] Respostas são **partials HTML** (§3.1) — nunca JSON. `ValidationError` propaga ao middleware
      (infraestrutura/001); o renderer **não** faz `try/except`.
- [ ] Tipagem integral; `mypy` limpo.

## Contexto e decisões de arquitetura

Esta SPEC mexe **só na camada de interface** do app `logradouro_matcher` (renderer + *partial*) e no
**registro** do `search`. A camada de **domínio já está pronta**: `LiteralLogradouroMatcher`
(`services/domain/logradouros_match/literal_matcher.py`) faz o match por substring sobre os nomes
normalizados do catálogo, com filtro opcional por tipo e *fallback* sinalizado por
`ignorou_filtro_tipo`. O roteador (roteamento-busca/001) já emite `LogradouroParse` com
`tipo_logradouro`/`nome` (parciais ou completos). Esta SPEC apenas **compõe** essas peças.

> **Por que a interface é fina (§3.2 / §3.3).** "Casar um nome de logradouro" é regra de negócio de
> matching e já vive no domínio (`match_logradouro_literal`). A view só **adapta** o candidato em DTO
> Pydantic e chama o domínio — espelhando `secao_codlog` (004/005) e `secao_contribuinte` (006).

> **Por que a seção sempre aparece.** Como o match literal é por substring com `limite`, qualquer
> nome digitado já produz sugestões (ou uma lista vazia com aviso). Logo `secao_logradouro` **sempre**
> devolve `SecaoResultado` — o contrato de seção da 005 é reaproveitado sem alteração e o laço de
> `rotear_busca` não muda; basta **adicionar a entrada no registro** (idêntico à 006).

> **Por que remover a rota direta de codlog.** A `buscar_codlog` (004) existia só para teste manual da
> view; com o roteador (005) consumindo os renderers via `REGISTRO_SECOES`, ela não tem mais
> consumidor. Mantê-la deixaria uma rota órfã. A busca **detalhada** (campos segmentados, com rotas
> diretas próprias) é assunto de SPEC futura — não desta. Resultado: o `logradouro_matcher` fica
> coerente com o `lote_matcher`, que nunca teve rota direta.

### Fluxo

```
Home (core): barra única já instrumentada (roteamento-busca/005)
   │  POST: termo_pesquisa, tipo_evento   →   #sugestoes-busca
   ▼
search.views.rotear_busca (orquestração — já existe, inalterada)
   • RoteamentoQuery(...) ; result = rotear_entrada(query)
   • para cada candidato: render_secao = REGISTRO_SECOES.get(candidato.tipo)
        - CODLOG        → secao_codlog         (004/005)
        - CONTRIBUINTE  → secao_contribuinte   (006)
        - LOGRADOURO    → secao_logradouro     (ESTA SPEC)
   • render _sugestoes.html (uma <section> por seção)
                                                            ▼
logradouro_matcher.views.secao_logradouro(candidato: LogradouroParse) -> SecaoResultado
   • monta LiteralLogradouroQuery(nome=candidato.nome, tipo=candidato.tipo_logradouro or None)
   • resultado = match_logradouro_literal(dto)   # domínio: substring + filtro tipo + limite
   • render_to_string("logradouro_matcher/partials/resultados_logradouro.html", {resultado})
   • SecaoResultado(titulo="Logradouro (por nome)", html=...)
```

### Princípios aplicados (§3, §10, §11)

- **§3.1 HATEOAS:** o renderer produz *partial* HTML; nenhuma montagem de UI por JS/JSON.
- **§3.2 / §3.3 Isolamento:** a regra de matching está no domínio; a interface só adapta o candidato
  em DTO Pydantic e chama o domínio. O domínio não conhece request.
- **§7.1 Normalização única:** o match literal já opera sobre os nomes normalizados do catálogo
  (mesma normalização de preparação e consulta) — esta SPEC não reintroduz normalização própria.
- **§10.1 SRP / §10.4 Composição:** um renderer por tipo, registrado no `search`; o
  `logradouro_matcher` cuida do domínio de logradouro (codlog + nome), sem cruzar lote/contribuinte.
- **§11:** `ValidationError` tratado pelo middleware (infra/001); *partial* sem `extends`; pasta de
  template coberta por `@source`.

## Peças de referência a compor

- `@services/domain/logradouros_match` → `match_logradouro_literal` (singleton de
  `LiteralLogradouroMatcher`), `LiteralLogradouroQuery`, `LiteralLogradouroResult`, `LogradouroMatch`:
  **invocar e consumir** — o matching literal já está pronto, não recriar.
- `@services/domain/roteamento_busca` → `LogradouroParse` (candidato, com `tipo_logradouro`/`nome` que
  podem vir parciais) e `TipoEntrada.LOGRADOURO`: entrada do renderer e chave do registro.
- `@apps/search/views.py` → `REGISTRO_SECOES`: **estender** com a entrada de logradouro (o laço de
  `rotear_busca` **não muda**).
- `@apps/search/secoes.py` → `SecaoResultado`: contrato de seção compartilhado, **importado** pelo
  renderer (não redefinir).
- `@apps/logradouro_matcher/views.py` → `secao_codlog` / `_render_codlog`: **padrão** de renderer a
  espelhar; aqui também se **remove** `buscar_codlog`.
- `@apps/lote_matcher/views.py` → `secao_contribuinte`: padrão mais recente (sem rota direta) a
  espelhar.
- `@templates/logradouro_matcher/partials/resultados_codlog.html` e
  `@templates/lote_matcher/partials/resultados_contribuinte.html` → padrão do *partial* de `ul` de
  sugestões a espelhar para logradouro por nome.
- `@templates/search/partials/_sugestoes.html` → agregador genérico: **reutilizado tal como está**.
- **SPEC infraestrutura/001** (`PydanticValidationMiddleware`) → trata `ValidationError`; sem
  `try/except` na view.

## Snippets sugeridos

### Renderer do logradouro por nome (`apps/logradouro_matcher/views.py`)

```python
# direção de implementação — adaptar sem violar §3 nem §10
from django.template.loader import render_to_string

from apps.search.secoes import SecaoResultado
from services.domain.logradouros_match import LiteralLogradouroQuery, match_logradouro_literal
from services.domain.roteamento_busca import LogradouroParse

TITULO_LOGRADOURO = "Logradouro (por nome)"


def _render_logradouro(dto: LiteralLogradouroQuery) -> str:
    resultado = match_logradouro_literal(dto)
    return render_to_string(
        "logradouro_matcher/partials/resultados_logradouro.html",
        {"resultado": resultado},
    )


def secao_logradouro(candidato: LogradouroParse) -> SecaoResultado:
    dto = LiteralLogradouroQuery(
        nome=candidato.nome,
        tipo=candidato.tipo_logradouro or None,
    )
    return SecaoResultado(titulo=TITULO_LOGRADOURO, html=_render_logradouro(dto))


# `buscar_codlog` e seu @require_POST são REMOVIDOS (rota de teste sem consumidor).
```

### Registro estendido (`apps/search/views.py`)

```python
from apps.logradouro_matcher.views import secao_codlog, secao_logradouro
from apps.lote_matcher.views import secao_contribuinte
from services.domain.roteamento_busca import TipoEntrada

# laço de rotear_busca permanece o da 005 — só o registro cresce
REGISTRO_SECOES: dict[TipoEntrada, SectionRenderer] = {
    TipoEntrada.CODLOG: secao_codlog,
    TipoEntrada.CONTRIBUINTE: secao_contribuinte,
    TipoEntrada.LOGRADOURO: secao_logradouro,
}
```

### Limpeza das rotas (`apps/logradouro_matcher/urls.py` + `config/urls.py`)

```python
# apps/logradouro_matcher/urls.py — sem a rota de teste, o app fica sem rotas diretas
# (espelha o lote_matcher, que não tem urls.py). Remover a entrada `buscar_codlog`; se
# o urlpatterns ficar vazio, remover o arquivo e o include correspondente em config/urls.py.

# config/urls.py — remover:
#   path("", include("apps.logradouro_matcher.urls")),
```

### Partial de sugestões (`templates/logradouro_matcher/partials/resultados_logradouro.html`)

```htmldjango
{# fragmento HTMX, sem extends — recebe: resultado (LiteralLogradouroResult) #}
{% if resultado.ignorou_filtro_tipo %}
  <p class="text-warning text-xs py-1">Tipo não reconhecido — mostrando todos os logradouros.</p>
{% endif %}
{% if resultado.logradouros %}
  <ul class="divide-y divide-base-300">
    {% for r in resultado.logradouros %}
      <li class="py-3 flex items-baseline gap-4">
        <span class="font-mono text-sm text-base-content/60 w-16 shrink-0">{{ r.codlog }}</span>
        <span class="font-medium">{{ r.nome_logradouro }}</span>
      </li>
    {% endfor %}
  </ul>
{% else %}
  <p class="text-base-content/60 text-sm py-4">Nenhum logradouro encontrado.</p>
{% endif %}
```

## Fora de escopo

- **Busca por fuzzy match** (`match_logradouro` / `LogradouroMatcher`): as sugestões durante a
  digitação usam o **match literal** (substring); o fuzzy é o caminho do match final quando nenhuma
  sugestão é clicada — assunto de outra SPEC.
- **Busca detalhada** (campos segmentados de logradouro: tipo + nome) e qualquer **rota direta** do
  `logradouro_matcher` para o nome: o único consumidor agora é o roteador via registro.
- **Resolução de geometria** do logradouro (linha) e **renderização no mapa Leaflet** — esta SPEC só
  produz a lista de sugestões.
- **Clique numa sugestão** para confirmar o match / disparar a busca final.
- **Seção de endereço** (`ENDERECO`) — outra SPEC.
- **Estilização final** das seções/`ul` e do aviso de tipo (DaisyUI detalhado) — refinada em SPEC de
  UI.
- **Ranqueamento/ordenação sofisticada** das sugestões (além da ordem natural do catálogo + `limite`).

## Notas de teste

- POST `termo_pesquisa="PAULISTA"`, `tipo_evento="keyup"` → 200; a `<section>` "Logradouro (por
  nome)" traz até `limite` logradouros cujo nome contém `PAULISTA`.
- POST `termo_pesquisa="AV PAULISTA"` (tipo reconhecido) → a seção filtra pelo tipo `AV` e
  **não** exibe o aviso de tipo (`ignorou_filtro_tipo=False`).
- POST `termo_pesquisa="XPTO PAULISTA"` (tipo não reconhecido) → a seção exibe o **aviso discreto** e
  lista logradouros de todos os tipos que contêm `PAULISTA` (`ignorou_filtro_tipo=True`).
- POST com nome sem correspondência → a seção aparece com "Nenhum logradouro encontrado".
- `candidato.tipo_logradouro` vazio chega como `None` ao `LiteralLogradouroQuery`, não `""`.
- Entrada que gere `LOGRADOURO` **e** `ENDERECO` → a seção de logradouro aparece no seu `<section>`.
- Regressão 005/006: as seções de codlog e contribuinte continuam funcionando; o laço de
  `rotear_busca` não mudou.
- Regressão da remoção: GET/POST na antiga rota `buscar-codlog/` retorna **404** (rota removida); a
  home e o fluxo do roteador continuam intactos.

## Patches

_Nenhum patch registrado até o momento._
