---
spec: roteamento_busca/014
versao: v1
atualizado_em: 2026-07-06
implementado: true
changelog:
  - v1: versão inicial
---

# SPEC roteamento_busca/014 — Fallback fuzzy no fluxo endereço-lote (endereço fiscal cadastrado)

- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como usuário da busca, quando digito um endereço com erro no nome da rua (ex.:
"avenida palista, 347") cujo endereço correto ("avenida paulista, 347") **existe no cadastro
fiscal de contribuintes**, quero que o sistema corrija o logradouro por aproximação, reconheça
que aquele número é um imóvel cadastrado e me ofereça esse **lote fiscal** como a primeira
sugestão (e como o resultado do Enter) — em vez de silenciosamente cair na geocodificação por
interpolação (ponto). E quero **ver o grau de certeza** do logradouro que ele corrigiu.

## Critérios de aceite
- [ ] Digitar `avenida palista, 347` (nome com erro, número que existe na base fiscal) e aguardar
      o keyup exibe a seção **"Endereço cadastrado (lote)"** com o imóvel correspondente, cada
      item com o **grau de certeza** do logradouro corrigido visível (badge "≈ 87%").
- [ ] Essa seção continua vindo **acima** da seção de endereço geocodificado (ponto), como já
      ocorre hoje pela prioridade do roteador — o efeito é que o lote fiscal "vai para cima".
- [ ] Enter em `avenida palista, 347` renderiza o **polígono do lote** fiscal cadastrado (não o
      ponto interpolado), acionando o melhor match fuzzy do logradouro.
- [ ] A consulta à base fiscal continua sendo **lookup exato por codlog + número** (`isin` +
      `startswith`) — nenhum fuzzy roda sobre a base de contribuintes (performance).
- [ ] O grau de certeza exibido é o do **logradouro** (o número + codlog na base fiscal é match
      exato, sem incerteza); quando o logradouro resolve pelo **literal**, nenhum badge de score
      aparece (idêntico a hoje).
- [ ] O fuzzy do logradouro só roda quando o literal devolve vazio: entradas cujo logradouro
      resolve pelo literal produzem exatamente a mesma seção/resultado de hoje.
- [ ] Nas sugestões (keyup) vale o tamanho mínimo de nome do modo `sugestao`; no Enter/commit
      não há mínimo — mesma regra de tamanho da SPEC 013.
- [ ] Endereço cujo logradouro nem por fuzzy passa do threshold, ou cujo número não existe na
      base fiscal, mantém o comportamento atual: seção omitida e, no Enter, segue ao próximo
      candidato (tipicamente o ponto interpolado ou o aviso).

## Contexto e decisões de arquitetura

Esta SPEC fecha exatamente o buraco que a **SPEC 013** deixou fora de escopo
("Fallback fuzzy no fluxo do endereço-lote"). A 013 levou o resolvedor fuzzy de logradouro
(`resolver_logradouro`) aos fluxos de **logradouro** (`LogradouroParse`) e **endereço-ponto**
(`EnderecoParse`), mas **não** ao fluxo **endereço-lote** (`EnderecoLoteParse`), que continua
resolvendo o logradouro só pelo **literal**.

Boa parte da infra já existe e **não muda**:

- O roteador já emite um candidato `EnderecoLoteParse` ("Endereço cadastrado (lote)") em paralelo
  ao `EnderecoParse`, e em `PRIORIDADE_TIPOS` o `ENDERECO_LOTE` **já precede** o `ENDERECO`. Ou
  seja, "ir para cima" já é a ordenação atual — tanto na lista de sugestões quanto no loop do
  `comitar`. Esta SPEC **não mexe no roteamento**.
- A consulta fiscal (`match_endereco_fiscal`) já é **lookup exato** por codlog + número. Continua
  igual — nada de fuzzy na base de contribuintes.

O que muda é **como o logradouro é resolvido** dentro desse fluxo:

- **Orquestração (apps `lote_matcher` e `search`).** Hoje `_resolver_codlogs` resolve o nome do
  logradouro via `match_logradouro_literal` (literal-only). Passa a usar o **`resolver_logradouro`**
  (o mesmo motor literal-primeiro-depois-fuzzy da 013), carregando o **score** de cada codlog
  resolvido. A composição "resolve logradouro → checa base fiscal" **cruza dois domínios**
  (`logradouros_match` + `contribuinte_match`); ela já vive na **orquestração** (a view compõe as
  duas chamadas) e **continua lá** — sem criar acoplamento entre os dois domínios em `services/`
  (§3.3, §10.1). Os DTOs de saída do domínio (`ContribuinteMatchOutput`) **não mudam**.
- **Orquestração isolada numa classe própria.** Essa cola (dispatch por forma de entrada,
  resolução de codlogs, montagem/ordenação das sugestões e escolha do partial) **não é view** e
  hoje está espalhada em funções soltas no `views.py`. Como os passos são super coesos —
  compartilham a resolução de codlogs e a lista de sugestões entre o keyup (seção) e o Enter
  (commit) — a SPEC os consolida numa **classe orquestradora** (`OrquestradorEnderecoLote`) que
  **existe só para orquestrar os dois branches endereço-lote da view**. Ela vive num **módulo
  utilitário próprio do app** (ex.: `apps/lote_matcher/secoes.py`, espelhando
  `apps/search/secoes.py`), mantendo o `views.py` só com as views. O nome do arquivo é decisão de
  implementação; o que a SPEC fixa é a **separação** (orquestração composável fora das views) e a
  **coesão** (uma classe, não funções soltas). A classe **não** conhece `request` nem devolve
  `HttpResponse`: as views a chamam e traduzem o resultado.
  Ao criar esse módulo, o **`secao_contribuinte`** (hoje também solto no `views.py` do
  `lote_matcher`) **migra junto**, por consistência — todo o *section-building* do app fica no
  módulo, o `views.py` fica só com as views. É movimentação de organização: a **lógica** do
  `secao_contribuinte` **não muda** e ele **não** faz parte do escopo funcional desta SPEC (segue
  função, não entra na classe do fluxo endereço-lote).
- **Associação do score.** O resolvedor devolve N logradouros candidatos, cada um com `codlog` +
  `score`. O `match_endereco_fiscal` recebe todos esses codlogs (lookup exato) e devolve os
  imóveis. O score do logradouro é **reassociado** a cada resultado fiscal pelo codlog (o
  `codlog5` — 5 dígitos — bate com o `codlog` que o resolvedor devolve). O par
  **(resultado fiscal + score do logradouro)** é um dado de **apresentação**: mora num pequeno DTO
  na **camada de app**, não no domínio. As sugestões ficam ordenadas com o **maior score no topo**
  (no caminho literal, sem score, mantém a ordem atual).
- **Proveniência fuzzy explícita no DTO.** O DTO de apresentação (`EnderecoLoteSugestao`) não deixa
  a origem do match apenas subentendida em "score é `None`". Ele expõe um atributo semântico
  próprio — **`veio_de_fuzzy`** — que **"sobe" do logradouro** (a incerteza é do logradouro
  corrigido por aproximação, não do imóvel, que é match exato). O atributo é um `computed_field`
  derivado do `score` (fonte única): `True` **somente** quando o logradouro foi resolvido por fuzzy
  (score presente); `False` quando resolveu pelo **literal** ou veio da **forma codlog** (ambos
  exatos, sem score). Assim, quem lê o DTO (template, ordenação, testes) pergunta
  `sugestao.veio_de_fuzzy` em vez de reinterpretar `score is not None` em cada ponto.
- **Modo `sugestao` | `commit`.** `_resolver_codlogs` passa a declarar o modo, exatamente como a
  013: `sugestao` no keyup (guarda de tamanho mínimo do nome, já embutida no resolvedor) e
  `commit` no Enter (sem mínimo). No commit, `_acionar_candidato` escolhe o resultado fiscal do
  **logradouro de maior score** (o "melhor match fuzzy").
- **Branch de codlog exato inalterado.** `EnderecoLoteParse` também aceita a forma por **codlog**
  (`match_codlog`): código é identificador exato, **não ganha fuzzy nem score** (score `None`).

Fluxo resumido:

```
keyup → rotear_busca → secao_endereco_lote(EnderecoLoteParse)   [seção acima de secao_endereco]
  └─ _resolver_codlogs(modo=sugestao)
       forma nome  → resolver_logradouro (literal → fuzzy)  → codlogs + score
       forma codlog→ match_codlog                            → codlogs (score None)
     match_endereco_fiscal(codlogs, numero_padronizado)      [lookup EXATO na base fiscal]
     junta score do logradouro por codlog → ordena por score desc → badge "≈ X%"

Enter → comitar → candidatos ordenados (ENDERECO_LOTE antes de ENDERECO)
  └─ EnderecoLoteParse → _resolver_codlogs(modo=commit) → match_endereco_fiscal
        escolhe o imóvel do logradouro de MAIOR score → geocodificar_lote → POLÍGONO
     (vazio → próximo candidato: EnderecoParse → ponto interpolado, ou aviso)
```

Ponto importante: o **caso especial do endereço fiscal exato** (pop-up ponto-vs-polígono do
CLAUDE.md §1) **não** é objeto desta SPEC — aqui a seção endereço-lote já representa o desfecho
"polígono do lote", e a coexistência com a seção de ponto é a que o roteador já entrega. Esta SPEC
só garante que o fuzzy do logradouro **também** alimenta esse fluxo.

## Peças de referência a compor
- `@services/domain/logradouros_match` → `resolver_logradouro` / `ResolucaoLogradouroQuery` /
  `ResolucaoLogradouroItem` (com `score` e `modo`): o resolvedor literal-primeiro-depois-fuzzy da
  SPEC 013. **Reusar como está**, no lugar do `match_logradouro_literal`.
- `@services/domain/contribuinte_match` → `match_endereco_fiscal` / `EnderecoFiscalMatchInput` /
  `ContribuinteMatchOutput`: o lookup **exato** por codlog + número na base fiscal. **Inalterado.**
- `@services/domain/codlog_match` → `match_codlog`: resolução exata da forma por codlog do
  `EnderecoLoteParse`. **Inalterado** (sem score).
- `@apps/lote_matcher/views.py` → `_resolver_codlogs` e `secao_endereco_lote` (hoje funções soltas
  no `views.py`): a lógica que esta SPEC **consolida e move** para uma classe orquestradora
  (`OrquestradorEnderecoLote`) num módulo utilitário próprio do app — é onde a troca literal →
  resolvedor acontece e o score é associado ao resultado fiscal.
- `@apps/search/views.py` → `_acionar_candidato` (branch `EnderecoLoteParse`): commit passa a
  resolver o logradouro por fuzzy e a escolher o imóvel do logradouro de maior score.
- `@services/domain/roteamento_busca` → `EnderecoLoteParse` (`logradouro`, `codlog`,
  `numero_padronizado`): DTO de entrada, **inalterado**.
- Partial `@templates/lote_matcher/partials/resultados_endereco_lote.html`: passa a exibir o badge
  de grau de certeza quando houver score.
- Partial `@templates/logradouro_matcher/partials/resultados_logradouro.html`: **referência visual**
  do badge de score já aprovado na 013 (`≈ {{ score|floatformat:0 }}%`) — reusar o mesmo padrão.
- Skill `componentes-frontend` (estilo do badge de certeza).

## Snippets sugeridos

```python
# apps/lote_matcher — DTO de APRESENTAÇÃO (camada de app, não domínio): junta o resultado fiscal
# exato ao grau de certeza do logradouro que o resolveu.
class EnderecoLoteSugestao(BaseModel):
    resultado: ContribuinteMatchOutput
    # grau de certeza do LOGRADOURO; None = logradouro exato (literal) ou forma codlog.
    score: float | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def veio_de_fuzzy(self) -> bool:
        # semântica que "sobe" do logradouro: True só quando o logradouro foi resolvido
        # por fuzzy (score presente). Literal e forma codlog são exatos -> False.
        return self.score is not None


# Módulo utilitário próprio do app (ex.: apps/lote_matcher/secoes.py) — NÃO é view.
# As funções de resolução são super coesas (compartilham a resolução de codlogs e a montagem
# de sugestões entre o keyup e o commit), então viram métodos de UMA classe que existe só para
# orquestrar os dois branches da view no fluxo endereço-lote. A view chama a classe; a classe
# nunca vira view (não recebe request nem devolve HttpResponse).

class OrquestradorEnderecoLote:
    """Orquestra os branches endereço-lote da busca — e existe SÓ para isso.

    Dois pontos de entrada, um por branch da view:
      - `secao`         : keyup → monta a seção "Endereço cadastrado (lote)" (ou None).
      - `melhor_sugestao`: Enter/commit → a sugestão de maior score (ou None).
    Ambos compartilham o pipeline privado `_sugestoes`, que compõe a cola cross-domínio
    (logradouros_match/codlog_match → contribuinte_match). Essa composição cruza domínios e por
    isso vive na orquestração do app (§3.3, §10.1), não em services/. Não implementa regra de
    matching — delega aos serviços de domínio (que são classes) e só decide o quê chamar e o que
    devolver. Sem `request`, sem estado: é a cola do branch isolada num objeto coeso.

    Obs.: dois métodos públicos (em vez de um único `__call__`, §10.4) porque são dois branches
    de view genuinamente distintos; o `__call__/pipeline` seria forçado com um flag de modo.
    """

    def secao(self, candidato: EnderecoLoteParse) -> SecaoResultado | None:
        sugestoes = self._sugestoes(candidato, modo="sugestao")
        if not sugestoes:
            return None  # seção OMITIDA (como hoje)
        html = render_to_string(
            "lote_matcher/partials/resultados_endereco_lote.html", {"sugestoes": sugestoes}
        )
        return SecaoResultado(titulo=TITULO_ENDERECO_LOTE, html=html)

    def melhor_sugestao(self, candidato: EnderecoLoteParse) -> EnderecoLoteSugestao | None:
        sugestoes = self._sugestoes(candidato, modo="commit")  # já ordenadas por score desc
        return sugestoes[0] if sugestoes else None

    def _sugestoes(self, candidato: EnderecoLoteParse, modo: str) -> list[EnderecoLoteSugestao]:
        codlog_score = self._resolver_codlogs(candidato, modo)
        if not codlog_score:
            return []
        resultados = match_endereco_fiscal(EnderecoFiscalMatchInput(
            codlogs=list(codlog_score), numero_padronizado=candidato.numero_padronizado,
        ))
        sugestoes = [
            EnderecoLoteSugestao(resultado=r, score=codlog_score.get(r.codlog[:5]))
            for r in resultados
        ]
        # maior certeza no topo; literal (score None) mantém a ordem atual
        sugestoes.sort(key=lambda s: s.score if s.score is not None else float("inf"), reverse=True)
        return sugestoes

    def _resolver_codlogs(
        self, candidato: EnderecoLoteParse, modo: str
    ) -> dict[str, float | None]:
        # O EnderecoLoteParse chega em DUAS formas mutuamente exclusivas (validador
        # _exatamente_uma_forma do DTO). Despacho pela forma: codlog presente => logradouro JÁ
        # identificado por código exato (não roda fuzzy); ausente => veio por nome, a resolver.
        # Ambos devolvem codlog -> score (None = logradouro exato; preenchido = fuzzy).
        if candidato.codlog is not None:
            return self._codlogs_do_codlog_exato(candidato.codlog)
        assert candidato.logradouro is not None
        return self._codlogs_do_nome_do_logradouro(candidato.logradouro, modo)

    def _codlogs_do_codlog_exato(self, codlog: CodlogParse) -> dict[str, float | None]:
        # Logradouro JÁ identificado por código: identificador exato -> lookup direto, NENHUM
        # fuzzy roda, score sempre None.
        resultados = match_codlog(CodlogMatchInput(
            input_codlog=codlog.codlog,
            digito_verificador=codlog.digito_verificador or None,
        ))
        return {r.codlog: None for r in resultados}

    def _codlogs_do_nome_do_logradouro(
        self, logradouro: LogradouroParse, modo: str
    ) -> dict[str, float | None]:
        # Logradouro por nome (texto livre): resolve literal-primeiro-depois-fuzzy (motor da 013).
        # score None nos codlogs vindos do literal; preenchido nos que vieram do fuzzy.
        resolucao = resolver_logradouro(ResolucaoLogradouroQuery(
            nome=logradouro.nome,
            tipo=logradouro.tipo_logradouro or None,
            modo=modo,
        ))
        return {item.logradouro.codlog: item.score for item in resolucao.itens}


# instância única exposta pelo módulo (mesmo padrão dos serviços de domínio); a view importa isto
orquestrador_endereco_lote = OrquestradorEnderecoLote()
```

```python
# apps/search/views.py — branch EnderecoLoteParse de _acionar_candidato (commit)
if isinstance(candidato, EnderecoLoteParse):
    sugestao = orquestrador_endereco_lote.melhor_sugestao(candidato)  # já resolve fuzzy + ordena
    if sugestao is None:
        return None
    fiscal = sugestao.resultado
    return geocodificar_lote(
        request, fiscal.setor, fiscal.quadra, fiscal.lote, fiscal.tipo_lote,
        fiscal.cd_condominio if fiscal.is_condominio else None,
    )
```

```html
<!-- resultados_endereco_lote.html — recebe: sugestoes (list[EnderecoLoteSugestao]) -->
{% for s in sugestoes %}
  {% with r=s.resultado %}
  <li class="suggestion-item items-baseline gap-4"
      hx-post="{% url 'lote_geocoder:geocodificar' %}"
      hx-vals='{"setor": "{{ r.setor }}", "quadra": "{{ r.quadra }}", "lote": "{{ r.lote }}", "tipo_lote": "{{ r.tipo_lote }}", "cd_condominio": "{{ r.cd_condominio }}", "is_condominio": "{{ r.is_condominio }}"}'
      hx-target="#resultado-busca" hx-swap="innerHTML">
    <span class="font-medium">{{ r.logradouro }} …, {{ r.numero }}</span>
    <span class="ml-auto flex items-center gap-2 shrink-0">
      {% if s.veio_de_fuzzy %}
        <span class="badge badge-info badge-soft badge-sm" title="Grau de certeza">≈ {{ s.score|floatformat:0 }}%</span>
      {% endif %}
      <span class="badge badge-poligono badge-sm">{{ r.tipo_lote }}</span>
    </span>
  </li>
  {% endwith %}
{% endfor %}
```

## Fora de escopo
- Roteamento (`EnderecoLoteParse` vs `EnderecoParse`, prioridade dos tipos) — inalterado.
- Qualquer fuzzy sobre a **base fiscal de contribuintes** — o lookup por codlog + número continua
  exato (performance).
- O **pop-up ponto-vs-polígono** do endereço fiscal exato (CLAUDE.md §1 / roadmap fase 4) — a
  coexistência das seções ponto e lote já é entregue pelo roteador; a decisão interativa é iteração
  própria.
- Feedback visual do Enter (lista visível + animação) — SPEC design/002.
- Fuzzy para a forma **codlog** do `EnderecoLoteParse` — código é identificador exato.
- Ajuste de threshold/algoritmo do resolvedor — usa-se o motor da 013 como está.

## Notas de teste
(Só quando explicitamente solicitado — CLAUDE.md §13.)
- `secao_endereco_lote` com "avenida palista, 347" (nome com erro, número na base fiscal) →
  seção presente, itens com badge de score, maior score no topo.
- `secao_endereco_lote` com logradouro que resolve pelo **literal** → resposta idêntica à atual
  (sem badge de score).
- `secao_endereco_lote` com número inexistente na base fiscal → seção omitida (mesmo com fuzzy
  resolvendo o logradouro).
- Modo sugestão com nome curto (abaixo do mínimo) → seção omitida sem rodar fuzzy; modo commit
  com nome curto → roda fuzzy.
- `comitar` com "avenida palista, 347" → renderiza polígono do lote (não o ponto); escolhe o
  imóvel do logradouro de maior score quando há mais de um codlog fuzzy.
- Forma por **codlog** do endereço-lote → inalterada, sem score.
- Regressão: entradas que já resolviam o endereço-lote pelo literal produzem a mesma resposta.

## Patches

_Nenhum patch registrado até o momento._
