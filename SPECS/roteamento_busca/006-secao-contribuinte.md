---
spec: roteamento-busca/006
versao: v2
atualizado_em: 2026-06-29
implementado: true
changelog:
  - v1: versão inicial
  - v2: tipo de lote (cd_tipo_lote) passa a fluir ponta a ponta — exibido em cada sugestão E propagado pelo clique (hx-vals → LoteSelection → view selecionar), pois a geocodificação do lote (geocodificacao/002) filtra por cd_tipo_lote e precisa do tipo escolhido
---

# SPEC roteamento-busca/006 — Seção de sugestões de contribuinte (pluga o match de lote no roteador)

- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como usuário, quando eu começar a digitar um **número de contribuinte** (setor / quadra / lote) na
barra de pesquisa única da home, quero ver — já a cada tecla, **mesmo com a numeração incompleta** —
**sugestões de lotes** que começam com o que digitei, agrupadas na sua própria seção, lado a lado com
as demais (logradouro por codlog), para escolher rapidamente o lote certo sem precisar dizer ao sistema
que estou buscando um contribuinte e sem ter de digitar o número inteiro.

Esta iteração **encaixa a seção de contribuinte** na estrutura extensível criada na roteamento-busca/005
(o roteador já classifica a entrada como `CONTRIBUINTE`) **e estende o domínio de match** para aceitar
busca **incompleta/por prefixo** — base do comportamento de sugestão "comecei a digitar `001.002` e já
recebo 5 lotes que casam".

## Critérios de aceite

- [ ] O domínio **`services/domain/contribuinte_match`** é **estendido para aceitar entrada incompleta
      por nível**, sempre na ordem **setor → quadra → lote**:
      - `ContribuinteMatchInput` passa a aceitar **valores parciais**: `setor` com **1 a 3** dígitos,
        `quadra` com **1 a 3**, `lote` com **1 a 4** (e `dv` com 1 a 2). A regra de dependência
        permanece: **lote exige quadra** e **quadra exige setor** (setor é obrigatório).
      - `ContribuinteMatcher` passa a casar por **prefixo** (`startswith`) em cada nível informado, e
        **não** mais por igualdade exata — combinando os níveis presentes (setor, e quadra/lote quando
        houver) e aplicando o `limite` ao resultado.
      - O prefixo é **geral**: um valor já completo (ex.: setor com 3 dígitos) casa por prefixo
        exatamente como casaria por igualdade — não há regressão para entradas completas.
- [ ] O match incompleto depende dos códigos estarem **armazenados como strings zero-padded** (mesma
      normalização da carga); o `startswith` opera sobre essas strings.
- [ ] O app **`lote_matcher`** é **criado** (app fino: views/renderer e templates próprios; sem regra
      de negócio), registrado em `INSTALLED_APPS`, conforme o papel do §6 do CLAUDE.md ("busca de lote
      por nº de contribuinte → polígono").
- [ ] Existe um **renderer** `secao_contribuinte` no `lote_matcher` que recebe o candidato
      **`ContribuinteParse`** (do roteador) e devolve **sempre** uma **`SecaoResultado`** (título + HTML
      do *partial*) — o mesmo contrato que o registro do `search` já espera (`apps/search/secoes.py`),
      **sem** precisar admitir `None` (a busca por prefixo sempre produz uma seção).
- [ ] O renderer **adapta** o `ContribuinteParse` para `ContribuinteMatchInput` passando os dígitos
      **como digitados** (parciais): `setor` (sempre presente), e `quadra`/`lote`/`dv` quando houver —
      campos vazios viram **`None`**, nunca `""`.
- [ ] O registro extensível do `search` (`REGISTRO_SECOES`) passa a mapear
      **`TipoEntrada.CONTRIBUINTE` → `secao_contribuinte`**, **sem alterar** o laço de `rotear_busca`
      nem o *partial* agregador `_sugestoes.html` (a estrutura da 005 é reaproveitada como está).
- [ ] O `lote_matcher` tem um *partial* próprio `resultados_contribuinte.html` que recebe a lista de
      **`ContribuinteMatchOutput`** e renderiza cada lote (máscara `setor.quadra.lote-dv` + **tipo de
      lote** (`r.tipo_lote`) + endereço: logradouro, número e complemento quando houver); lista vazia
      exibe um aviso de "nenhum lote encontrado". O `tipo_lote` já existe em `ContribuinteMatchOutput`
      e é exibido como um rótulo/badge ao lado da numeração, para o usuário distinguir lotes de tipos
      diferentes (fiscal, municipal etc.) antes de clicar na sugestão.
- [ ] **O `tipo_lote` é propagado pelo clique, não só exibido.** O `hx-vals` de cada sugestão passa a
      incluir `tipo_lote` (junto de `setor/quadra/lote/dv`), de modo que o POST de seleção carregue o
      tipo escolhido. Em consequência, o DTO **`LoteSelection`** ganha o campo **`tipo_lote`** e a view
      **`selecionar`** passa a lê-lo do POST. Isso é necessário porque a **geocodificação do lote**
      (geocodificacao/002) filtra a feição por `cd_tipo_lote` — sem o tipo escolhido, a seleção não tem
      informação suficiente para a busca final do polígono. O `tipo_lote` selecionado é obrigatório na
      seleção (vem sempre da sugestão clicada).
- [ ] Entrada **ambígua** continua coerente: para uma entrada numérica que gere candidatos `CODLOG`
      **e** `CONTRIBUINTE`, **ambas** as seções podem aparecer (codlog desde a 005; contribuinte a
      partir desta SPEC), cada uma no seu `<section>`.
- [ ] A pasta de templates do novo app é descoberta pelo Tailwind 4 (o `@source` de `apps/` e
      `templates/` já cobre por *glob*; confirmar que não é preciso novo `@source`).
- [ ] Respostas são **partials HTML** (§3.1) — nunca JSON. `ValidationError` propaga ao middleware
      (infraestrutura/001); a view do roteador **não** faz `try/except`.
- [ ] Tipagem integral; `mypy` limpo.

## Contexto e decisões de arquitetura

Esta SPEC mexe em **duas camadas**: estende o **domínio** (`services/domain/contribuinte_match`) para
busca por prefixo e cria a **interface** (app `lote_matcher` + *partial*) que encaixa o resultado na
barra única como uma seção. O roteamento (`rotear_entrada`, roteamento-busca/001) já emite candidatos
`ContribuinteParse` parciais (setor/quadra/lote/dv podem vir incompletos) — faltava (a) o domínio saber
casar com essa numeração incompleta e (b) um app de interface para o tipo contribuinte (a 005 só cobriu
codlog).

> **Por que o match por prefixo é do domínio (§3.2 / §7.3).** "Casar uma numeração parcial de
> contribuinte" é **regra de negócio de matching**, igual à do codlog — pertence a `services/domain`,
> não à view. A view só **adapta** o candidato em DTO e chama o domínio. Por isso a mudança principal é
> no `ContribuinteMatcher`/`ContribuinteMatchInput`, e a interface fica fina.

> **Localização (§6 do CLAUDE.md).** O §6 reserva o app **`lote_matcher`** para a "busca de lote por
> número de contribuinte → polígono". É o app que faltava: a 005 criou o `search` (agregador) e
> reaproveitou o `logradouro_matcher` (codlog). Esta SPEC cria o `lote_matcher` **fino**, espelhando o
> padrão do `logradouro_matcher` (renderer + *partial* próprio).

### Por que a interface volta a ser simples (sempre devolve seção)

Com o domínio casando por **prefixo**, qualquer numeração parcial — desde o primeiro dígito do setor —
já produz sugestões (limitadas por `limite`). Logo o `secao_contribuinte` **sempre** devolve uma
`SecaoResultado` (com a lista, ou com "nenhum lote encontrado" se nada casar). Não é preciso o desenho
anterior de "renderer pode devolver `None`": o contrato de seção da 005 é reaproveitado **sem
alteração**, e o laço de `rotear_busca` não muda — basta **adicionar a entrada no registro**.

### Fluxo

```
Home (core): barra única já instrumentada (roteamento-busca/005)
   │  POST: termo_pesquisa, tipo_evento   →   #sugestoes-busca
   ▼
search.views.rotear_busca (orquestração — já existe, inalterada)
   • RoteamentoQuery(...) ; result = rotear_entrada(query)
   • para cada candidato: render_secao = REGISTRO_SECOES.get(candidato.tipo)
        - CODLOG        → secao_codlog        (005)
        - CONTRIBUINTE  → secao_contribuinte  (ESTA SPEC)
   • render _sugestoes.html (uma <section> por seção)
                                                            ▼
lote_matcher.views.secao_contribuinte(candidato: ContribuinteParse) -> SecaoResultado
   • monta ContribuinteMatchInput(setor, quadra?, lote?, dv?)  (parciais; vazios = None)
   • resultados = match_contribuinte(dto)        # domínio: prefixo por nível + limite
   • render_to_string("lote_matcher/partials/resultados_contribuinte.html", {resultados})
   • SecaoResultado(titulo="Lote (por nº de contribuinte)", html=...)
```

### Princípios aplicados (§3, §10, §11)

- **§3.1 HATEOAS:** o renderer produz *partial* HTML; nenhuma montagem de UI por JS/JSON.
- **§3.2 / §3.3 Isolamento:** a **regra de matching (prefixo)** está no domínio; a interface só adapta
  o candidato em DTO Pydantic e chama o domínio. O domínio não conhece request.
- **§7.1 Normalização única:** o casamento por prefixo se apoia nos códigos já normalizados/zero-padded
  na carga — preparação e consulta usam a mesma representação.
- **§10.1 SRP / §10.4 Composição:** um renderer por tipo, registrado no `search`; o app de contribuinte
  não cruza o domínio de logradouro/codlog.
- **§11:** `ValidationError` tratado pelo middleware (infra/001); *partials* prefixados com `_` quando
  aplicável; pasta de template coberta por `@source`.

## Peças de referência a compor

- `@services/domain/contribuinte_match` → `ContribuinteMatchInput`, `ContribuinteMatcher`,
  `match_contribuinte`, `ContribuinteMatchOutput`: **estendidos nesta SPEC** para aceitar entrada
  parcial e casar por prefixo (ver Snippets). A estrutura de leitura do parquet e o mapeamento de saída
  são **reaproveitados**.
- `@services/domain/roteamento_busca` → `ContribuinteParse` (candidato, com `setor/quadra/lote/dv` que
  já podem vir parciais) e `TipoEntrada.CONTRIBUINTE`: entrada do renderer e chave do registro.
- `@apps/search/views.py` → `REGISTRO_SECOES`: **estender** com a entrada de contribuinte (o laço de
  `rotear_busca` **não muda**).
- `@apps/search/secoes.py` → `SecaoResultado`: contrato de seção compartilhado, **importado** pelo novo
  renderer (não redefinir).
- `@apps/logradouro_matcher/views.py` → `secao_codlog` / `_render_codlog`: **padrão** de renderer +
  *partial* a espelhar no `lote_matcher`.
- `@templates/logradouro_matcher/partials/resultados_codlog.html` → padrão do *partial* de `ul` de
  sugestões a espelhar para contribuinte.
- `@templates/search/partials/_sugestoes.html` → agregador genérico: **reutilizado tal como está**;
  não muda.
- `@apps/logradouro_matcher` (apps.py, __init__.py, estrutura) → padrão de **app fino** a espelhar na
  criação do `lote_matcher`.
- **SPEC infraestrutura/001** (`PydanticValidationMiddleware`) → trata `ValidationError`; sem
  `try/except` na view.

## Snippets sugeridos

### Domínio: input parcial + match por prefixo (`services/domain/contribuinte_match`)

```python
# models.py — patterns passam a aceitar valores PARCIAIS por nível
from pydantic import BaseModel, Field, model_validator


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
```

```python
# matcher.py — casa por PREFIXO em cada nível informado, combinando-os, e aplica o limite
def __call__(self, payload: ContribuinteMatchInput) -> list[ContribuinteMatchOutput]:
    df = self._dataframe
    mask = df["cd_setor_fiscal"].str.startswith(payload.setor)
    if payload.quadra:
        mask &= df["cd_quadra_fiscal"].str.startswith(payload.quadra)
    if payload.lote:
        mask &= df["cd_lote"].str.startswith(payload.lote)
    selecionados = df[mask].head(payload.limite)   # opcional: ordenar antes p/ sugestões estáveis
    return self._mapear_resultados(selecionados)
```

### Renderer do contribuinte (`apps/lote_matcher/views.py`)

```python
# direção de implementação — adaptar sem violar §3 nem §10
from django.template.loader import render_to_string

from apps.search.secoes import SecaoResultado
from services.domain.contribuinte_match import ContribuinteMatchInput, match_contribuinte
from services.domain.roteamento_busca import ContribuinteParse

TITULO_CONTRIBUINTE = "Lote (por nº de contribuinte)"


def _render_contribuinte(dto: ContribuinteMatchInput) -> str:
    resultados = match_contribuinte(dto)
    return render_to_string(
        "lote_matcher/partials/resultados_contribuinte.html",
        {"resultados": resultados},
    )


def secao_contribuinte(candidato: ContribuinteParse) -> SecaoResultado:
    dto = ContribuinteMatchInput(
        setor=candidato.setor,
        quadra=candidato.quadra or None,
        lote=candidato.lote or None,
        dv=candidato.dv or None,
    )
    return SecaoResultado(titulo=TITULO_CONTRIBUINTE, html=_render_contribuinte(dto))
```

### Registro estendido (`apps/search/views.py`)

```python
from apps.logradouro_matcher.views import secao_codlog
from apps.lote_matcher.views import secao_contribuinte
from services.domain.roteamento_busca import TipoEntrada

# laço de rotear_busca permanece o da 005 — só o registro cresce
REGISTRO_SECOES: dict[TipoEntrada, SectionRenderer] = {
    TipoEntrada.CODLOG: secao_codlog,
    TipoEntrada.CONTRIBUINTE: secao_contribuinte,
}
```

### Partial de sugestões (`templates/lote_matcher/partials/resultados_contribuinte.html`)

```htmldjango
{# fragmento HTMX, sem extends — recebe: resultados (list[ContribuinteMatchOutput]) #}
{% if resultados %}
  <ul class="divide-y divide-base-300">
    {% for r in resultados %}
      {# tipo_lote vai tanto no badge (exibição) quanto no hx-vals (propagação ao clicar) #}
      <li class="py-3 flex items-baseline gap-4 cursor-pointer hover:bg-base-200"
          hx-post="{% url 'lote_matcher:selecionar' %}"
          hx-vals='{"setor": "{{ r.setor }}", "quadra": "{{ r.quadra }}", "lote": "{{ r.lote }}", "dv": "{{ r.digito|default:"" }}", "tipo_lote": "{{ r.tipo_lote }}"}'
          hx-target="#resultado-busca"
          hx-swap="innerHTML"
      >
        <span class="font-mono text-sm text-base-content/60 w-32 shrink-0">
          {{ r.setor }}.{{ r.quadra }}.{{ r.lote }}{% if r.digito %}-{{ r.digito }}{% endif %}
        </span>
        <span class="badge badge-sm badge-ghost shrink-0">{{ r.tipo_lote }}</span>
        <span class="font-medium">
          {{ r.logradouro }}, {{ r.numero }}{% if r.complemento %} — {{ r.complemento }}{% endif %}
        </span>
      </li>
    {% endfor %}
  </ul>
{% else %}
  <p class="text-base-content/60 text-sm py-4">Nenhum lote encontrado.</p>
{% endif %}
```

### Seleção carrega o tipo de lote (`apps/lote_matcher/schemas.py` + `views.py`)

```python
# schemas.py — LoteSelection ganha tipo_lote, para alimentar a geocodificação (geocodificacao/002)
class LoteSelection(BaseModel):
    setor: str = Field(pattern=r"^\d{1,3}$")
    quadra: str = Field(pattern=r"^\d{1,3}$")
    lote: str = Field(pattern=r"^\d{1,4}$")
    dv: str | None = Field(default=None, pattern=r"^\d{1,2}$")
    tipo_lote: str  # obrigatório: vem sempre da sugestão clicada (hx-vals)
```

```python
# views.py — selecionar passa a ler tipo_lote do POST
selecao = LoteSelection(
    setor=request.POST.get("setor", ""),
    quadra=request.POST.get("quadra", ""),
    lote=request.POST.get("lote", ""),
    dv=request.POST.get("dv") or None,
    tipo_lote=request.POST.get("tipo_lote", ""),
)
```

## Fora de escopo

- **Busca detalhada** (campos segmentados de contribuinte) e qualquer **rota direta**
  (`buscar_contribuinte` + `urls.py` do `lote_matcher`): o único consumidor agora é o roteador via
  registro; a rota direta da busca detalhada entra em SPEC própria.
- **Resolução de geometria** do lote (polígono) e **renderização no mapa Leaflet** — esta SPEC só
  produz a **lista de sugestões**.
- **Clique numa sugestão** para confirmar o match / disparar a busca final.
- **Pop-up de endereço fiscal exato** (ponto vs. polígono) — roadmap fase 1, item 4.
- **Algoritmo do dígito verificador** do contribuinte: segue placeholder no domínio (não participa do
  match).
- **Ranqueamento/ordenação sofisticada** das sugestões por prefixo (além de uma ordenação estável
  simples) — refinável em SPEC futura.
- **Renderers de endereço e de logradouro por nome (fuzzy)** — outras SPECs.
- **Estilização final** das seções/`ul` (DaisyUI detalhado) — refinada em SPEC de UI.

## Notas de teste

- **Domínio (prefixo):** `ContribuinteMatchInput(setor="0")` → casa todos os setores que começam com
  `0`, limitado a `limite`. `setor="001", quadra="02"` → casa setor `001` e quadra começando com `02`.
- **Domínio (completo, regressão):** `setor="001", quadra="002", lote="0003"` → mesmo resultado que o
  match exato anterior (prefixo de valor completo == igualdade).
- **Domínio (dependência):** `lote` sem `quadra` → `ValidationError` (regra mantida).
- **Domínio (vazio):** prefixo sem correspondência → lista vazia (não erro).
- POST `termo_pesquisa="001.002"`, `tipo_evento="keyup"` → 200; a `<section>` "Lote (por nº de
  contribuinte)" traz até `limite` lotes cuja numeração começa com `001.002`.
- POST `termo_pesquisa="01"` (setor parcial) → a seção **aparece** com lotes cujo setor começa com `01`
  (diferente do desenho antigo, que escondia a seção).
- Entrada numérica ambígua (`CODLOG` **e** `CONTRIBUINTE`) → ambas as seções aparecem.
- `quadra`/`lote`/`dv` vazios do candidato chegam como `None` ao `ContribuinteMatchInput`, não `""`.
- Regressão 005: a seção de codlog continua funcionando; o laço de `rotear_busca` não mudou.

## Patches

- **v2 (2026-06-29):** o **tipo de lote** (`cd_tipo_lote`) passa a fluir **ponta a ponta**, motivado
  pela geocodificacao/002, que filtra a feição do lote por `cd_tipo_lote` e portanto exige o tipo
  escolhido para a busca final do polígono. Duas frentes:
  - **Exibição:** o *partial* `resultados_contribuinte.html` mostra o `tipo_lote` (badge ao lado da
    numeração), para o usuário distinguir lotes de tipos diferentes (fiscal, municipal etc.) antes de
    clicar. O campo já existia em `ContribuinteMatchOutput.tipo_lote` (mapeado de `cd_tipo_lote` no
    `ContribuinteMatcher`) — nada muda no domínio nem no registro de seções.
  - **Propagação:** o `hx-vals` de cada sugestão passa a incluir `tipo_lote`; o DTO `LoteSelection`
    ganha o campo `tipo_lote` e a view `selecionar` passa a lê-lo do POST. Assim a seleção do lote já
    carrega o tipo, deixando a seleção pronta para alimentar a `LoteGeocodInput` (geocodificacao/002)
    sem ter de reconsultar a base só para descobrir o tipo. Continua sendo só interface/orquestração
    (§3.3) — sem regra de negócio nova.
