---
spec: localizacao_lote/004
versao: v7
atualizado_em: 2026-09-18
testes_tdd: true
implementado: true
markers_obrigatorios: []
changelog:
  - v1: versão inicial
  - v2: submódulo `lote_espacial` renomeado para `lotes_mais_proximos`
  - v3: o conjunto passa a ser guardado na sessão, e a revisão se reduz à lixeira sobre o resultado da SPEC 003
  - v4: a gaveta ganha "Limpar lotes", e o ✕ de toda gaveta de resultado passa a fechar pela limpeza que a ação declara
  - v5: clicar no lote no mapa também marca a linha dele na tabela e a traz para o foco
  - v6: a linha marcada vai para a primeira posição da tabela, que rola ao topo
  - v7: a linha sobe deslizando, com a pincagem da tabela de unidades
---

# SPEC localizacao_lote/004 — Revisão do conjunto de lotes do desenho

## 1 · User story
Quem desenhou um terreno tira, na tabela da gaveta inferior, os lotes que o desenho cruzou por
engano — um a um ou todos de uma vez —, no contexto de um traço que pegou vizinhos por uma lasca, para
chegar ao conjunto que de fato compõe o terreno.

## 2 · Condições de pronto
- [x] Cada linha da tabela tem uma **lixeira**; acioná-la tira o lote da tabela **e** do mapa, sem
      reenquadrar o mapa, sem abrir a gaveta do lote e **sem consultar o GeoServer**, e o resumo da
      gaveta passa a contar **só os lotes que restaram**.
- [x] Tirar lotes em sequência acumula: um lote tirado não volta ao tirar o próximo.
- [x] Tirar o último lote mostra um estado de falta escrito **próprio**, distinto do desenho que não
      cruza lote algum.
- [x] **"Limpar lotes"** abre um aviso que diz **quantos lotes estão na tela**; confirmado, tira todos
      da tabela e do mapa, sem consultar o GeoServer, e a gaveta **fica aberta** no estado de falta do
      conjunto esvaziado. Cancelado, nada muda.
- [x] **Fechar** a gaveta pelo ✕ faz a gaveta **descer como ao recolher** e só então abre o aviso,
      dizendo que todos os lotes serão tirados. Cancelado, a gaveta volta a subir. Confirmado, a paleta
      e o aviso somem **com fade**, os lotes saem do mapa, a busca volta e o conjunto é descartado da
      sessão. **Recolher** a gaveta não pede nem descarta nada.
- [x] Com o conjunto já vazio, "Limpar lotes" não aparece, e o ✕ fecha **sem aviso**, com a gaveta
      descendo.
- [x] Acionar "Lotes intersectados" de novo **recomeça** o conjunto, com todos os lotes do desenho.
- [x] Um identificador de lote que não está no conjunto, mandado para remoção, **não muda** o conjunto.
- [x] Remover ou limpar a partir de um resultado que **não é o vigente** na sessão (substituído por
      consulta de outra aba, ou já descartado) é recusado com aviso em português, e o conjunto vigente
      fica intacto; fechar a gaveta desse resultado só a fecha naquela aba.
- [x] Clicar num lote **no mapa** marca a linha dele na tabela como **ativa** (a marca `data-ativo` da
      `.table-onsen`), a **sobe deslizando** até a primeira posição, como na tabela de unidades, e rola a tabela ao topo, para a lixeira ficar à
      mão e a linha nunca ficar sob o cabeçalho; a linha antes ativa perde a marca. A marca e a
      ordem voltam ao normal quando a tabela é trocada (revisão, nova consulta).
- [x] A lixeira da linha da tabela existe como átomo no tema e no styleguide, com o visual da lixeira
      da bancada, antes de qualquer template da aplicação usá-la.

## 3 · Domínio
O conjunto é o [LotesDoDesenho](003-lotes-do-desenho.md#3--domínio) que a consulta apurou, com a
escolha humana por cima. Ele fica guardado na sessão de quem desenhou, da consulta até a próxima
consulta ou até a gaveta ser fechada.

**`services/domain/lotes_mais_proximos/models.py`**

```python
class ConjuntoDeLotes(BaseModel):
    """O que a consulta apurou e o que a pessoa tirou. Remover é o único gesto — nada se acrescenta."""

    model_config = ConfigDict(frozen=True)

    apurado: LotesDoDesenho
    removidos: frozenset[str] = frozenset()   # id_poligono dos lotes tirados

    @property
    def lotes(self) -> tuple[LoteFeature, ...]:
        # Derivado: a ordem é a da consulta, e os removidos ficam registrados para quem precisar deles.
        return tuple(
            lote for lote in self.apurado.lotes
            if lote.attributes.id_poligono not in self.removidos
        )
```

## 4 · Fora de escopo
- Desfazer uma remoção ou uma limpeza — sem dono ainda; refazer a consulta recomeça o conjunto.
- Acrescentar lote que o desenho não cruza — sem dono ainda.
- Mais de um conjunto vivo por sessão — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/lotes_mais_proximos/do_desenho.py` → `BuscarLotesDoDesenho`: a apuração que vira o conjunto.
- `@apps/lotes_mais_proximos/contexto.py` → `contexto_lotes_do_desenho`, `_properties_lote_do_desenho`.
- `@apps/mapping/context.py` → `contexto_resultado_acao`, `contexto_aviso`.
- `@templates/mapping/_mapa.html` → o payload do mapa, que a remoção reenvia.
- `@templates/mapping/_gaveta_desenhos.html` → "Limpar desenhos" e o `<dialog id="limpar-desenhos">`: o modelo do botão e do aviso.
- `@static/src/js/mapa/interacao_resultado.js` → o realce linha ↔ lote; **alterado** com o aval do usuário (§6): `escolher` passa a marcar a linha.
- `@static/src/tema-dimap.dev.css` → `.table-onsen-compacta`, `.gaveta-vazia`, `.btn-etched-swell`, `.modal-glass`, e o `tr[data-ativo="true"]` da `.table-onsen` (já existe; nada de CSS novo).
- Skills: `acao-sobre-desenho`, `componentes-frontend`, `htmx`, `test-django-views`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/lotes_mais_proximos/conjunto.py`**

```python
class RemocaoDoConjuntoInput(BaseModel):
    conjunto: ConjuntoDeLotes
    id_poligono: str = Field(pattern=r"^\d+$")


class RemoverDoConjunto:
    def __call__(self, entrada: RemocaoDoConjuntoInput) -> ConjuntoDeLotes:
        return self.pipeline(entrada)

    def pipeline(self, entrada: RemocaoDoConjuntoInput) -> ConjuntoDeLotes:
        # Só se tira o que a consulta apurou: um id de fora devolve o conjunto como estava.
        apurados = {lote.attributes.id_poligono for lote in entrada.conjunto.apurado.lotes}
        if entrada.id_poligono not in apurados:
            return entrada.conjunto
        return entrada.conjunto.model_copy(
            update={"removidos": entrada.conjunto.removidos | {entrada.id_poligono}},
        )


class EsvaziarConjunto:
    def __call__(self, conjunto: ConjuntoDeLotes) -> ConjuntoDeLotes:
        # Limpar é remover tudo o que foi apurado: o conjunto continua vivo, vazio, e a tabela
        # cai no estado de falta do conjunto esvaziado — não no do desenho sem lote.
        apurados = frozenset(lote.attributes.id_poligono for lote in conjunto.apurado.lotes)
        return conjunto.model_copy(update={"removidos": apurados})
```

**`apps/lotes_mais_proximos/sessao.py`** — a sessão guarda **um** conjunto, marcado por uma chave que
viaja na tabela. Chave diferente é resultado de outra aba, já substituído.

```python
CHAVE_SESSAO = "lotes_mais_proximos.conjunto"


class ConjuntoNaSessao(BaseModel):
    chave: str   # uuid4().hex, gerado a cada consulta
    conjunto: ConjuntoDeLotes


def guardar_conjunto(sessao: SessionBase, guardado: ConjuntoNaSessao) -> None:
    sessao[CHAVE_SESSAO] = guardado.model_dump(mode="json")


def conjunto_vigente(sessao: SessionBase, chave: str) -> ConjuntoDeLotes | None:
    bruto = sessao.get(CHAVE_SESSAO)
    if bruto is None:
        return None
    guardado = ConjuntoNaSessao.model_validate(bruto)
    return guardado.conjunto if guardado.chave == chave else None


def descartar_conjunto(sessao: SessionBase, chave: str) -> None:
    # Só o vigente sai: fechar a gaveta de uma aba antiga não apaga o conjunto da aba nova.
    if conjunto_vigente(sessao, chave) is not None:
        del sessao[CHAVE_SESSAO]
```

**`apps/mapping/limpeza.py`** — o que o ✕ da gaveta inferior limpa. **Toda ação com resultado no mapa
declara a sua**: fechar é sempre uma ida à rota da ação, que limpa o estado dela e responde com o
encerramento comum.

```python
class AvisoDeLimpeza(BaseModel):
    pergunta: str
    contagem: str   # o que vai sair, como se lê no badge: "12 lotes na tela"


class Limpeza(BaseModel):
    url: str                          # rota já resolvida pela orquestração
    vals: dict[str, str] = {}         # o que a rota precisa para achar o estado (a chave do conjunto)
    aviso: AvisoDeLimpeza | None      # None: não há o que perder, e o ✕ fecha sem perguntar

    @property
    def hx_vals(self) -> str:
        # O template só interpola: o JSON do hx-vals sai daqui, escapado pelo autoescape do Django.
        return json.dumps(self.vals)
```

**`apps/mapping/context.py`** e **`static/src/js/mapa/camada_resultado.js`** — o reenquadramento vira
opção do payload, ligada por padrão; o `aplicarResultado` do `init.js` repassa `data.enquadrar`. O
`contexto_resultado_acao` passa a **exigir** a limpeza, sem default.

```python
GEOJSON_VAZIO = {"type": "FeatureCollection", "features": []}


def contexto_mapa(geometria: dict[str, Any], cor: str, enquadrar: bool = True) -> dict[str, Any]:
    return {"payload": {"geometria": geometria, "cor": cor, "enquadrar": enquadrar}}


def contexto_resultado_acao(
    acao: str,
    desenho: Desenho,
    geojson: dict[str, Any],
    limpeza_ao_fechar: Limpeza,   # NOVO: obrigatório — a ação que não declarar não compila no mypy
    enquadrar: bool = True,
) -> dict[str, Any]:
    return contexto_mapa(geojson, MAP_COR_RESULTADO_ACAO, enquadrar) | {
        "acao": acao,
        "desenho": desenho.id_bancada,
        "limpeza_ao_fechar": limpeza_ao_fechar,
    }


def contexto_encerramento_acao() -> dict[str, Any]:
    # FeatureCollection vazia: o aplicarResultado de hoje tira a camada anterior e não põe nada.
    return contexto_mapa(GEOJSON_VAZIO, MAP_COR_RESULTADO_ACAO, enquadrar=False)
```

```javascript
export function adicionarResultado(map, geometria, corPadrao, enquadrar = true) {
  const camada = L.geoJSON(geometria, { /* FORA_DA_BANCADA, style, pointToLayer, onEachFeature como hoje */ }).addTo(map);
  if (enquadrar) enquadrarCamada(map, camada);   // o fitBounds/setView de hoje, extraído
  return camada;
}
```

**`templates/mapping/_resultado_acao.html`** — o ✕ sai da base para um bloco cujo padrão é o fechar
comum. A marca do contexto perde o `encerra_com`: quem a apaga passa a ser o encerramento, e o
`static/src/js/ui/contexto_acao.js` sai.

```html
<header class="gaveta-cabecalho items-center">
  <div class="min-w-0 flex items-baseline gap-3 flex-wrap">…título e resumo, como hoje…</div>
  {% block controles %}{% include "mapping/_fechar_gaveta.html" %}{% endblock %}
</header>
…
{% include "mapping/_contexto_acao_oob.html" %}   {# ALTERADO: sem encerra_com #}
```

**`templates/mapping/_fechar_gaveta.html`** — com aviso, o ✕ abre o `<dialog>`; sem, posta direto.
Nos dois casos a resposta entra **no `#gaveta-inferior-conteudo` com atraso de swap**: é o intervalo em
que o CSS anima a saída.

```html
{% with limpeza=limpeza_ao_fechar %}
  {% if limpeza.aviso %}
    <button type="button" class="btn-etched btn-etched-swell etched self-center" aria-label="Fechar"
            commandfor="aviso-fechar-gaveta" command="show-modal">…✕…</button>
    {% include "mapping/_aviso_limpeza.html" with id="aviso-fechar-gaveta" fecha_gaveta=True %}
  {% else %}
    <button type="button" class="btn-etched btn-etched-swell etched self-center" aria-label="Fechar"
            hx-post="{{ limpeza.url }}" hx-vals='{{ limpeza.hx_vals }}'
            hx-target="#gaveta-inferior-conteudo" hx-swap="innerHTML swap:…ms">…✕…</button>
  {% endif %}
{% endwith %}
```

**`templates/mapping/_aviso_limpeza.html`** — o `<dialog>` do "Limpar desenhos", para toda limpeza. O
aviso de fechar leva a classe que recolhe a gaveta enquanto está aberto e **não** se fecha ao
confirmar: ele some junto da gaveta, no fade do swap.

```html
<dialog id="{{ id }}" class="modal modal-glass {% if fecha_gaveta %}gaveta-inferior-aviso-fechar{% endif %}" closedby="any">
  <div class="modal-box modal-box-glass glass-panel-thick p-6 flex flex-col gap-5">
    <div>
      <p class="text-overline">{{ rotulo|default:"Fechar" }}</p>
      <p class="text-[18px] font-bold text-rocha-950">{{ limpeza.aviso.pergunta }}</p>
    </div>
    <span class="badge badge-sm …">{{ limpeza.aviso.contagem }}</span>
    <div class="modal-action">
      <button type="button" class="btn btn-glass btn-sm" commandfor="{{ id }}" command="close">Cancelar</button>
      {% if fecha_gaveta %}
        <button type="button" class="btn btn-onsen btn-sm" hx-disabled-elt="this"
                hx-post="{{ limpeza.url }}" hx-vals='{{ limpeza.hx_vals }}'
                hx-target="#gaveta-inferior-conteudo" hx-swap="innerHTML swap:…ms">Tirar todos e fechar</button>
      {% else %}
        <button type="button" class="btn btn-onsen btn-sm" commandfor="{{ id }}" command="close"
                hx-post="{{ limpeza.url }}" hx-vals='{{ limpeza.hx_vals }}'
                hx-target="#resultado-busca" hx-swap="innerHTML">Tirar todos</button>
      {% endif %}
    </div>
  </div>
</dialog>
```

**`static/src/tema-dimap.dev.css`** — estados novos da `.gaveta-inferior-rasa`, ao lado do recolhido
(que não muda): o aviso de fechar aberto recolhe a placa, e o swap do encerramento faz o fade. Sem JS.

```css
/* Aviso de fechar aberto: a placa desce como recolhida e a paleta aparece; o aviso entra depois dela. */
.gaveta-toggle:checked + .gaveta-inferior-rasa:has(.gaveta-inferior-aviso-fechar[open]) { @apply translate-y-full; }
.gaveta-toggle:checked + .gaveta-inferior-rasa:has(.gaveta-inferior-aviso-fechar[open]) > .paleta-gaveta-inferior { @apply opacity-100; }
.gaveta-inferior-aviso-fechar[open] { /* transition-delay casado com a descida — valor acertado no smoke test */ }

/* Encerramento em curso (.htmx-swapping no alvo): a placa desce, paleta e aviso somem em fade. */
#gaveta-inferior-conteudo.htmx-swapping .gaveta-inferior-rasa { @apply translate-y-full; }
#gaveta-inferior-conteudo.htmx-swapping :is(.paleta-gaveta-inferior, .gaveta-inferior-aviso-fechar) { @apply opacity-0; }
```

**`templates/mapping/_encerramento_acao.html`** — a resposta comum de toda limpeza ao fechar. O corpo
vazio é o que esvazia a gaveta, no fim do atraso; o mapa e a marca vão por OOB.

```html
<div id="resultado-busca" hx-swap-oob="innerHTML">{% include "mapping/_mapa.html" %}</div>
<div id="contexto-acao" hidden hx-swap-oob="true"></div>
```

**`apps/lotes_mais_proximos/views.py`** — a consulta da SPEC 003 passa a guardar o conjunto; remover,
limpar e fechar são rotas **abertas**: revisam dado público e não são ato administrativo.

```python
@require_POST
def lotes_do_desenho(request: HttpRequest) -> HttpResponse:
    ...
    try:
        apurado = BuscarLotesDoDesenho(build_fetcher(settings))(entrada)
    except (DesenhoInvalidoError, DesenhoGrandeDemaisError) as erro:
        return render(request, TEMPLATE_RECUSA_ACAO, contexto_aviso(str(erro)))
    guardado = ConjuntoNaSessao(chave=uuid4().hex, conjunto=ConjuntoDeLotes(apurado=apurado))   # NOVO
    guardar_conjunto(request.session, guardado)                                                 # NOVO
    return render(request, TEMPLATE_RESULTADO_DESENHO, contexto_lotes_do_desenho(guardado))     # ALTERADO


class RemocaoDoConjunto(BaseModel):
    chave: str
    id_poligono: str


class ConjuntoAlvo(BaseModel):
    chave: str


@require_POST
def remover_do_conjunto(request: HttpRequest) -> HttpResponse:
    """Rota aberta (SPEC localizacao_lote/004): revisão de dado público, sem ato administrativo."""
    remocao = RemocaoDoConjunto.model_validate(request.POST.dict())
    conjunto = conjunto_vigente(request.session, remocao.chave)
    if conjunto is None:
        return render(request, TEMPLATE_AVISO, contexto_aviso(MSG_CONJUNTO_NAO_VIGENTE))
    revisado = RemoverDoConjunto()(RemocaoDoConjuntoInput(conjunto=conjunto, id_poligono=remocao.id_poligono))
    guardado = ConjuntoNaSessao(chave=remocao.chave, conjunto=revisado)
    guardar_conjunto(request.session, guardado)
    return render(request, TEMPLATE_REVISAO_DO_CONJUNTO, contexto_revisao_do_conjunto(guardado))


@require_POST
def limpar_conjunto(request: HttpRequest) -> HttpResponse:
    """Rota aberta (SPEC localizacao_lote/004): revisão de dado público, sem ato administrativo."""
    alvo = ConjuntoAlvo.model_validate(request.POST.dict())
    conjunto = conjunto_vigente(request.session, alvo.chave)
    if conjunto is None:
        return render(request, TEMPLATE_AVISO, contexto_aviso(MSG_CONJUNTO_NAO_VIGENTE))
    guardado = ConjuntoNaSessao(chave=alvo.chave, conjunto=EsvaziarConjunto()(conjunto))
    guardar_conjunto(request.session, guardado)
    # A mesma resposta da lixeira: payload sem reenquadrar + OOB do resumo, da tabela e dos controles.
    return render(request, TEMPLATE_REVISAO_DO_CONJUNTO, contexto_revisao_do_conjunto(guardado))


@require_POST
def fechar_conjunto(request: HttpRequest) -> HttpResponse:
    """Rota aberta (SPEC localizacao_lote/004): a limpeza ao fechar dos lotes intersectados."""
    alvo = ConjuntoAlvo.model_validate(request.POST.dict())
    descartar_conjunto(request.session, alvo.chave)
    # Responde igual com chave vigente ou não: a aba que fecha sempre limpa o próprio mapa.
    return render(request, TEMPLATE_ENCERRAMENTO_ACAO, contexto_encerramento_acao())
```

**`apps/lotes_mais_proximos/contexto.py`** — o mapa e a tabela saem dos lotes **restantes**; a revisão
não reenquadra; as duas limpezas saem do mesmo conjunto.

```python
def _contagem(conjunto: ConjuntoDeLotes) -> str:
    total = len(conjunto.lotes)
    return f"{total} lote{'s' if total != 1 else ''} na tela"


def _limpeza(url_name: str, guardado: ConjuntoNaSessao, pergunta: str) -> Limpeza:
    # Conjunto vazio não tem o que perder: sem aviso, o ✕ fecha direto (e "Limpar lotes" some).
    aviso = AvisoDeLimpeza(pergunta=pergunta, contagem=_contagem(guardado.conjunto)) if guardado.conjunto.lotes else None
    return Limpeza(url=reverse(url_name), vals={"chave": guardado.chave}, aviso=aviso)


def _contexto_conjunto(guardado: ConjuntoNaSessao, enquadrar: bool) -> dict[str, Any]:
    conjunto = guardado.conjunto
    geojson = to_geojson_feature_collection(conjunto.lotes, _properties_lote_do_desenho)
    contexto = contexto_resultado_acao(
        CONSULTA_LOTES_INTERSECTADOS.slug,
        conjunto.apurado.desenho,
        geojson,
        limpeza_ao_fechar=_limpeza("lotes_mais_proximos:fechar_conjunto", guardado, PERGUNTA_FECHAR),
        enquadrar=enquadrar,
    )
    return contexto | {
        "conjunto": conjunto,
        "chave": guardado.chave,
        "limpar_lotes": _limpeza("lotes_mais_proximos:limpar_conjunto", guardado, PERGUNTA_LIMPAR),
    }


def contexto_lotes_do_desenho(guardado: ConjuntoNaSessao) -> dict[str, Any]:
    return _contexto_conjunto(guardado, enquadrar=True)


def contexto_revisao_do_conjunto(guardado: ConjuntoNaSessao) -> dict[str, Any]:
    # Tirar lotes não pode levar o mapa para longe de onde a pessoa está olhando.
    return _contexto_conjunto(guardado, enquadrar=False)
```

**`templates/lotes_mais_proximos/partials/_resultado_desenho.html`** — resumo, tabela e controles saem
para partials próprios, com id, para a revisão trocá-los fora de banda.

```html
{% extends "mapping/_resultado_acao.html" %}
{% block titulo %}Lotes intersectados{% endblock %}
{% block resumo %}{% include "lotes_mais_proximos/partials/_resumo_conjunto.html" %}{% endblock %}
{% block controles %}{% include "lotes_mais_proximos/partials/_controles_conjunto.html" %}{% endblock %}
{% block corpo %}{% include "lotes_mais_proximos/partials/_tabela_conjunto.html" %}{% endblock %}
```

**`templates/lotes_mais_proximos/partials/_controles_conjunto.html`** — "Limpar lotes" ao lado do fechar
comum; o aviso conta os lotes **restantes**, por isso o bloco inteiro volta por OOB a cada revisão.

```html
<div id="controles-conjunto" class="flex items-center gap-2" {% if oob %}hx-swap-oob="true"{% endif %}>
  {% if limpar_lotes.aviso %}
    <button type="button" class="btn-etched btn-etched-swell etched"
            commandfor="aviso-limpar-lotes" command="show-modal">Limpar lotes</button>
    {% include "mapping/_aviso_limpeza.html" with id="aviso-limpar-lotes" limpeza=limpar_lotes rotulo="Limpar lotes" %}
  {% endif %}
  {% include "mapping/_fechar_gaveta.html" %}
</div>
```

**`templates/lotes_mais_proximos/partials/_revisao_do_conjunto.html`** — resposta da lixeira e do
"Limpar lotes": o payload do mapa e os três partials com `oob`; a gaveta inferior não refaz a entrada.

```html
{% include "mapping/_mapa.html" %}
{% include "lotes_mais_proximos/partials/_resumo_conjunto.html" with oob=True %}
{% include "lotes_mais_proximos/partials/_controles_conjunto.html" with oob=True %}
{% include "lotes_mais_proximos/partials/_tabela_conjunto.html" with oob=True %}
```

**`templates/lotes_mais_proximos/partials/_tabela_conjunto.html`** — o `hx-swap-oob` só existe na
revisão: dentro da resposta da consulta, a tabela já chega pelo OOB da base.

```html
<section id="tabela-conjunto" class="gaveta-coluna" {% if oob %}hx-swap-oob="true"{% endif %}>
  {% for lote in conjunto.lotes %}
    <tr data-id-feature="{{ lote.attributes.id_poligono }}"
        hx-get="{% url 'lotes_mais_proximos:detalhe_do_lote' %}?id={{ lote.attributes.id_poligono }}"
        hx-target="#gaveta-entidade" hx-swap="innerHTML">
      …  {# SQL, endereço, lançamento, como na SPEC 003 #}
      <td>
        {# stopPropagation: o clique na lixeira não chega à linha, que abriria a gaveta do lote que está saindo. #}
        <button type="button" aria-label="Tirar do conjunto"
                hx-post="{% url 'lotes_mais_proximos:remover_do_conjunto' %}"
                hx-vals='{"chave": "{{ chave }}", "id_poligono": "{{ lote.attributes.id_poligono }}"}'
                hx-target="#resultado-busca" hx-swap="innerHTML"
                hx-on:click="event.stopPropagation()">…</button>
      </td>
    </tr>
  {% empty %}
    {% if conjunto.apurado.lotes %}
      …  {# .gaveta-vazia: todos os lotes foram tirados do conjunto #}
    {% else %}
      …  {# .gaveta-vazia: o desenho não cruza lote algum (SPEC 003) #}
    {% endif %}
  {% endfor %}
</section>
```

**`static/src/js/mapa/interacao_resultado.js`** — o `escolher` passa a marcar a linha; só o clique **no
mapa** a leva ao topo, porque quem clicou na linha já a está vendo.

```javascript
const LINHAS = "#gaveta-inferior-conteudo tr[data-id-feature]";

function marcarLinha(id, { aoTopo }) {
  document.querySelectorAll(`${LINHAS}[data-ativo]`).forEach((tr) => tr.removeAttribute("data-ativo"));
  const linha = [...document.querySelectorAll(LINHAS)].find((tr) => tr.dataset.idFeature === id);
  if (!linha) return;
  linha.setAttribute("data-ativo", "true");
  if (!aoTopo) return;
  pincarLinha(linha);   // static/src/js/ui/pincar_linha.js: clone que desliza, na pele de .table-flutuante-clone
}

function escolher(id, opcoes = { aoTopo: false }) {
  estado.idEscolhido = id;
  marcarLinha(id, opcoes);
  realcar();
}
// No clique da feature: escolher(id, { aoTopo: true }).
```

## 7 · Caveats
O conjunto é guardado na sessão, com os lotes e as geometrias que a consulta apurou. É o que deixa cada
remoção sem ida ao GeoServer e mantém do lado do servidor o que pode ser tirado, sem que o cliente
consiga acrescentar lote. O custo é uma sessão que cresce com o desenho — limitada pela área máxima da
SPEC 003 — e é regravada a cada lixeira.

A sessão guarda um conjunto só, e a chave que viaja na tabela diz se ele é o vigente. Guardar um por
aba faria a sessão crescer sem limite, sem um momento claro de limpeza. O custo é que duas abas não
revisam dois terrenos ao mesmo tempo: a mais antiga passa a receber o aviso de resultado não vigente.

O conjunto guardado não é revalidado contra a camada de lotes. Ele descreve o cadastro no momento da
consulta, e revalidar a cada remoção seria a ida ao GeoServer que a sessão evita. O custo é tabela e
mapa descrevendo lote que tenha mudado na camada até a próxima consulta.

A revisão reenvia o payload do mapa inteiro, sem reenquadrar, em vez de apagar a feature no
JavaScript. O mapa só se desenha a partir do servidor, e `contexto_mapa` ganha o `enquadrar`, que todo
resultado passa a poder carregar. O custo é o realce da feature escolhida zerar a cada remoção.

`remover_do_conjunto`, `limpar_conjunto` e `fechar_conjunto` são rotas abertas, como a consulta que
as origina. Tirar lotes revisa dado público e não pratica ato algum: o ato é o que a SPEC
[certidao_lancamento/002](../certidao_lancamento/002-certidao-do-conjunto.md) fizer com o conjunto. O
custo é qualquer visitante gravar um conjunto na própria sessão.

A lixeira para a propagação do próprio clique com um `hx-on:click`. Sem isso, o clique chega
à `<tr>` e abre a gaveta do lote que está saindo. O custo é JavaScript inline no template, que, como o
`enquadrar`, só tem prova no smoke test manual.

A base `_resultado_acao.html` e o `contexto_resultado_acao`, peças já implementadas, mudam com o aval
do usuário: o ✕ de toda gaveta de resultado passa a fechar pela `Limpeza` que a ação declara, e o
`contexto_acao.js` com o `encerra_com` sai. Fechar passa a pedir confirmação e a limpar estado do
servidor, e um caminho só de encerramento evita que a marca do contexto seja apagada por dois
mecanismos. O custo é fechar custar uma ida ao servidor a toda ação, mesmo à que nada guarda, e a gaveta
não fechar sem rede.

A saída animada é só CSS: o aviso aberto recolhe a placa por `:has(dialog[open])`, e o atraso do swap
deixa a `.htmx-swapping` do htmx no alvo pelo tempo do fade. É estado visual de controle sem JS
algum. O custo é a duração da animação morar em dois lugares — na transição do tema e no `swap:…ms`
do `_fechar_gaveta.html` — que podem divergir, e a coreografia só ter prova no smoke test manual.

A pincagem reaproveita a pele de `.table-flutuante-clone` (SPEC user_admin/021), mas com JS próprio
(`pincar_linha.js`): o de unidades é amarrado aos ids daquela tabela, e alterá-lo pede aval. O custo é a
mecânica do clone existir duas vezes. A marca da linha, a troca de posição dela e a rolagem são estado visual de controle em JavaScript, com aprovação do usuário (§7.2
do CLAUDE.md): reordenar a linha e rolar a tabela não têm saída em CSS. `interacao_resultado.js`, peça já
implementada, muda com o aval do usuário. O custo é não haver teste automatizado: a prova é o smoke
test manual (clicar num lote no mapa, com a linha dentro e fora da área visível da tabela, e depois numa linha da tabela).

## 8 · Testes (TDD)
- `test_remover_tira_o_lote_e_mantem_a_ordem` — de três lotes apurados, remover um deixa dois em
  `conjunto.lotes`, na ordem da consulta, e o removido em `removidos`.
- `test_remover_id_de_fora_do_conjunto_nao_muda_nada` — id que a consulta não apurou devolve o conjunto
  igual ao de entrada.
- `test_lotes_do_desenho_guarda_o_conjunto_na_sessao` — POST da consulta grava na sessão o conjunto com
  todos os lotes e sem removidos; cada lixeira, o "Limpar lotes" e o aviso de fechar levam a chave
  dele, e o aviso de fechar aponta para `fechar_conjunto`.
- `test_refazer_a_consulta_recomeca_o_conjunto` — depois de uma remoção, novo POST da consulta devolve
  todos os lotes e grava o conjunto sem removidos, com chave nova.
- `test_remover_devolve_tabela_resumo_e_mapa_sem_o_lote_sem_consultar_o_wfs` — com fetcher que falha se
  chamado, a resposta traz o payload sem a feature e com `enquadrar: false`, o OOB da tabela sem a
  linha, o OOB do resumo e dos controles com a quantidade restante, e nenhum OOB da base de resultado.
- `test_remocoes_acumulam` — duas remoções seguidas deixam os dois lotes fora da tabela, do payload e
  da sessão.
- `test_remover_ultimo_lote_mostra_falta_do_conjunto` — tabela vazia depois de remoção traz o estado de
  falta do conjunto esvaziado, não o do desenho sem lote; os controles não trazem "Limpar lotes" nem
  aviso, e o ✕ posta direto em `fechar_conjunto`.
- `test_limpar_esvazia_o_conjunto_sem_consultar_o_wfs` — com fetcher que falha se chamado, a resposta
  traz o payload sem features e com `enquadrar: false`, a tabela no estado de falta do conjunto
  esvaziado, e a sessão com todos os apurados em `removidos`, sob a mesma chave.
- `test_fechar_descarta_o_conjunto_e_encerra_o_contexto` — POST de `fechar_conjunto` devolve corpo
  vazio, o OOB do `#resultado-busca` com payload sem features, e o OOB da marca do contexto sem
  atributos; tira o conjunto da sessão, e uma remoção seguinte com a mesma chave é recusada com o aviso.
- `test_chave_nao_vigente_nao_mexe_no_conjunto_vigente` — com chave diferente da guardada, remover e
  limpar devolvem o aviso, sem payload, e o fechar devolve o encerramento; nos três, a sessão continua
  com o conjunto de antes.
