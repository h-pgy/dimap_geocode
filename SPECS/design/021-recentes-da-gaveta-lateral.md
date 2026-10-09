---
spec: design/021
versao: v1
atualizado_em: 2026-10-09
testes_tdd: false
implementado: false
changelog:
  - v1: versão inicial
---

# SPEC design/021 — Recentes da gaveta lateral

## 1 · User story
Quem trabalha no mapa volta, pelo rodapé da gaveta lateral, a uma das últimas gavetas que abriu, no
contexto de um fluxo em que cada busca ou consulta toma o lugar da anterior, para retomar a entidade
que estava vendo sem refazer a busca.

## 2 · Condições de pronto
- [ ] Abrir um lote, um endereço, um endereço externo ou um logradouro — por sugestão da busca, pelo
      Enter ou por consulta do poço dos desenhos — põe a gaveta nos **recentes**, que guardam as
      **cinco últimas** sem repetir a mesma entidade: reaberta, ela volta ao topo.
- [ ] Toda gaveta lateral traz, no rodapé, o **voltar**: um clique devolve a gaveta anterior **e o
      desenho dela no mapa**, como estavam quando foram abertos, **sem consultar a base oficial nem o
      provedor externo**. Voltar de novo devolve a gaveta de onde se saiu.
- [ ] Do voltar sobe a **lista dos recentes**, cada um com o **glifo do tipo** de gaveta e o
      **resumo** dela — o SQL do lote, o endereço, o nome e o codlog do logradouro; escolher um o
      devolve do mesmo jeito.
- [ ] Na primeira gaveta, sem outra a que voltar, o voltar **não responde** ao clique nem ao teclado,
      e a lista não abre.
- [ ] A gaveta devolvida **pede de novo as ações** dela: quem ganhou ou perdeu competência depois de
      abri-la vê as ações de agora.
- [ ] A **gaveta dos desenhos** entra nos recentes enquanto houver desenho no mapa; voltar a ela a
      remonta com os desenhos **como estão agora** e o último desenho selecionado. Apagado o último
      desenho, ela sai dos recentes.
- [ ] Com a **gaveta inferior** aberta ou recolhida, o voltar e a lista não respondem ao clique nem ao
      teclado, e uma **interrogação** diz que é preciso fechar a gaveta de resultado; fechada pelo ✕,
      eles voltam. O lote aberto pela tabela dela **não entra** nos recentes.
- [ ] Com a gaveta inferior aberta ou recolhida, as **ações do poço dos desenhos** ficam do mesmo
      jeito, com a mesma interrogação — inclusive "Lotes intersectados" sobre outro polígono. A
      tabela e os controles da gaveta inferior e as ações do lote aberto por ela seguem funcionando.
- [ ] Trocar de um endereço para outro **funde o conteúdo** da gaveta, como já acontece entre lotes.
- [ ] O design do rodapé, da lista, dos glifos de tipo e do estado travado foi aprovado no mock, e as
      peças foram portadas para o tema e o styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
Uma **cena** é o que a gaveta lateral e o mapa mostram juntos sobre uma entidade: a gaveta e o desenho
dela na camada de resultado. Os **recentes** são as últimas gavetas abertas na sessão de quem usa o
mapa.

As gavetas são as da [gaveta do lote](../localizacao_lote/001-dados-do-lote-na-gaveta.md), do
[endereço](../localizacao_lote/002-lote-mais-proximo-do-endereco.md), do
[endereço externo](../geocodificacao_externa/003-endereco-externo-no-mapa-e-na-gaveta.md), do
[logradouro](../geocodificacao/006-gaveta-do-logradouro.md) e dos
[desenhos](020-desenhos-na-gaveta.md). A pergunta que esta SPEC faz a cada uma é "como você se
identifica e como se resume numa linha?". Ao [contexto de ação](../localizacao_lote/003-lotes-do-desenho.md)
ela pergunta "há gaveta inferior?".

**`services/domain/recentes/models.py`** — NOVO.

```python
LIMITE_RECENTES = 5


class TipoGaveta(StrEnum):
    """Os tipos de gaveta lateral: é o tipo que escolhe o glifo."""

    LOTE = "lote"
    ENDERECO = "endereco"
    ENDERECO_EXTERNO = "endereco_externo"
    LOGRADOURO = "logradouro"
    DESENHOS = "desenhos"

    @property
    def rotulo(self) -> str:
        return ROTULO_POR_TIPO[self]   # "Lote fiscal", "Endereço", "Endereço externo", ...


class Etiqueta(BaseModel):
    """Como uma gaveta lateral se identifica e se resume numa linha."""

    model_config = ConfigDict(frozen=True)

    chave: str = Field(min_length=1)    # a mesma do `data-gaveta`: mesma chave, mesma gaveta
    tipo: TipoGaveta
    resumo: str = Field(min_length=1)   # "SQL 012.345.0067-8", "AV PAULISTA, 1000"


class Cena(BaseModel):
    """O que o voltar devolve como estava: a gaveta já renderizada e o desenho dela no mapa."""

    gaveta: str             # o HTML da gaveta; o domínio não o lê
    mapa: dict[str, Any]    # o payload do mapa: geometria, cor e enquadramento


class Recente(BaseModel):
    """Uma gaveta aberta há pouco."""

    etiqueta: Etiqueta
    cena: Cena | None = None   # None: espelho do mapa, que não se guarda — pede-se de novo a ele


class Recentes(BaseModel):
    """As últimas gavetas abertas, da mais recente à mais antiga, uma por chave."""

    itens: tuple[Recente, ...] = Field(default=(), max_length=LIMITE_RECENTES)

    @model_validator(mode="after")
    def _uma_por_chave(self) -> Self:
        chaves = [recente.etiqueta.chave for recente in self.itens]
        if len(chaves) != len(set(chaves)):
            raise ValueError("Os recentes repetem uma gaveta.")
        return self

    def de_chave(self, chave: str) -> Recente | None:
        return next((r for r in self.itens if r.etiqueta.chave == chave), None)

    def fora(self, chave: str) -> tuple[Recente, ...]:
        """Os recentes menos a gaveta que está na tela: o primeiro é o destino do voltar."""
        return tuple(r for r in self.itens if r.etiqueta.chave != chave)
```

A etiqueta de cada gaveta:

| Gaveta | `chave` | `resumo` |
|---|---|---|
| Lote | `lote-<id_poligono>` | `SQL <sql>`, ou `Sem contribuinte` |
| Endereço | `endereco-<codlog>-<numero>` | `<nome completo do logradouro>, <numero>` |
| Endereço externo | `externo-<slug do endereço formatado>` | o endereço formatado |
| Logradouro | `logradouro-<codlog>` | `<nome completo> · <codlog>` |
| Desenhos | `desenhos` | `<n> desenho(s)` |

O que entra na `Cena` é a informação pública da entidade. O que depende de quem está olhando — as
ações oferecidas por perfil, o estado de um ato — não faz parte dela: a gaveta o pede por carga
assíncrona a cada vez que é mostrada.

A camada de resultado do mapa tem um dono por vez: a gaveta inferior, enquanto houver uma, aberta ou
recolhida; sem ela, a entidade da gaveta lateral. Trocar a cena — abrir uma entidade, voltar a uma,
acionar o poço dos desenhos — é entregar a camada a outro dono, e só existe quando o dono é a lateral.

**Mock:** [021-mock-recentes-da-gaveta-lateral.html](021-mock-recentes-da-gaveta-lateral.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Recentes por aba do navegador (§7) — sem dono ainda.
- O lote aberto pela tabela da gaveta inferior como cena dos recentes — sem dono ainda.
- Validade da cena: reconsultar a base depois de um prazo (§7) — sem dono ainda.
- Voltar a um resultado anterior da gaveta inferior — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/lotes_mais_proximos/sessao.py` → `guardar_conjunto`, `conjunto_vigente`: molde do DTO gravado na sessão e relido por `model_validate`.
- `@apps/mapping/context.py` → `contexto_mapa`: o payload do mapa que a cena guarda.
- `@templates/mapping/_mapa.html`: o payload na resposta; a cena devolvida passa por ele.
- `@templates/lote_geocoder/partials/_gaveta_lote.html` → o `hx-get` com `hx-trigger="load"` das ações: molde da carga assíncrona do rodapé.
- `@static/src/js/ui/troca_gaveta.js`: lê o `data-gaveta` da raiz, que passa a ser a chave da etiqueta.
- `@static/src/js/mapa/desenho/sincronia.js` → `pedirGavetaDesenhos`: remonta a gaveta dos desenhos a partir do mapa.
- `@templates/mapping/_contexto_acao_oob.html` → `#contexto-acao`: a marca de que há gaveta inferior, que a trava lê.
- `@static/src/tema-dimap.dev.css` → `.torre-ajustes`, `.btn-etched`, `.tooltip`, `.gaveta-lateral*`, e `@templates/mapping/_glifos_mapa.html`: as peças e a folha de glifos a compor no rodapé.
- Skills: `ontologia`, `mock`, `componentes-frontend`, `htmx`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/recentes/recentes.py`** — a regra dos recentes. Devolver uma cena é abrir de novo o
que já está na lista: a mesma operação.

```python
class AberturaInput(BaseModel):
    recentes: Recentes
    recente: Recente


class AbrirNosRecentes:
    def __call__(self, entrada: AberturaInput) -> Recentes:
        return self.pipeline(entrada)

    def pipeline(self, entrada: AberturaInput) -> Recentes:
        # `fora` tira a de mesma chave: reabrir não duplica, e vale a cena mais nova.
        demais = entrada.recentes.fora(entrada.recente.etiqueta.chave)
        # O corte derruba a mais antiga quando a sexta entra.
        itens = (entrada.recente, *demais)[:LIMITE_RECENTES]
        return Recentes(itens=itens)


class RetiradaInput(BaseModel):
    recentes: Recentes
    chave: str


class TirarDosRecentes:
    def __call__(self, entrada: RetiradaInput) -> Recentes:
        return Recentes(itens=entrada.recentes.fora(entrada.chave))
```

**`apps/mapping/recentes.py`** — a sessão e a resposta de toda entidade localizada.

```python
CHAVE_SESSAO = "mapping.recentes"
TEMPLATE_CENA = "mapping/_cena.html"


def recentes_da_sessao(sessao: SessionBase) -> Recentes:
    bruto = sessao.get(CHAVE_SESSAO)
    if bruto is None:
        return Recentes()
    try:
        return Recentes.model_validate(bruto)
    except ValidationError:
        # Sessão gravada por outra versão do modelo: recomeça vazia, em vez de derrubar a tela.
        return Recentes()


def abrir_nos_recentes(sessao: SessionBase, recente: Recente) -> None:
    abertura = AberturaInput(recentes=recentes_da_sessao(sessao), recente=recente)
    sessao[CHAVE_SESSAO] = AbrirNosRecentes()(abertura).model_dump(mode="json")


def responder_cena(
    request: HttpRequest,
    etiqueta: Etiqueta,
    template_gaveta: str,
    contexto: dict[str, Any],
) -> HttpResponse:
    # A gaveta é renderizada uma vez só: o mesmo texto vai para a sessão e para a resposta.
    gaveta = render_to_string(template_gaveta, contexto | {"etiqueta": etiqueta}, request)
    cena = Cena(gaveta=gaveta, mapa=contexto["payload"])
    abrir_nos_recentes(request.session, Recente(etiqueta=etiqueta, cena=cena))
    return render(request, TEMPLATE_CENA, contexto_cena(cena))


def contexto_cena(cena: Cena) -> dict[str, Any]:
    return {"payload": cena.mapa, "gaveta": cena.gaveta}
```

**`templates/mapping/_cena.html`** — a resposta única de abrir e de devolver. Os cinco
`_resultado_*.html` (lote, endereço, endereço externo, logradouro, lote mais próximo), que só juntavam
o mapa e o OOB da gaveta, perdem o consumidor e são apagados.

```html
{% include "mapping/_mapa.html" %}
{# `safe`: o texto saiu dos templates do projeto, com autoescape, e veio da sessão do servidor. #}
<div id="gaveta-entidade" hx-swap-oob="innerHTML">{{ gaveta|safe }}</div>
```

**`apps/lote_geocoder/views.py`** — uma gaveta aderindo: a etiqueta e a troca do `render`.

```python
def etiqueta_do_lote(lote: LoteAttributes) -> Etiqueta:
    return Etiqueta(
        chave=f"lote-{lote.id_poligono}",
        tipo=TipoGaveta.LOTE,
        resumo=f"SQL {lote.sql}" if lote.sql else "Sem contribuinte",
    )


def geocodificar_lote(...) -> HttpResponse:
    ...
    contexto = contexto_mapa(geojson, MAP_COR_POLIGONO) | {"gaveta": gaveta}
    # ALTERADO: a resposta passa pela cena, que a guarda nos recentes.
    return responder_cena(request, etiqueta_do_lote(gaveta.lote), TEMPLATE_GAVETA_LOTE, contexto)
```

As demais respostas de entidade fazem a mesma troca, cada uma com a sua etiqueta (§3). É no ponto em
que a gaveta é renderizada que ela entra nos recentes, e por isso a sugestão, o Enter e a consulta do
poço chegam juntos:

| Onde a gaveta é renderizada | Etiqueta |
|---|---|
| `apps/lote_geocoder/views.py` → `geocodificar_lote` | lote |
| `apps/lotes_mais_proximos/views.py` → `mais_proximo`, `mais_proximo_do_ponto` | lote |
| `apps/address_geocoder/views.py` → `renderizar_endereco` | endereço |
| `apps/geocodificacao_externa/views.py` → `geocodificar_externo` | endereço externo |
| `apps/logradouro_geocoder/views.py` → `geocodificar_codlog` | logradouro |

O `detalhe_do_lote`, que a tabela da gaveta inferior chama, passa a `etiqueta` ao template e segue
respondendo com o `render` da gaveta: sem `responder_cena`, não entra nos recentes.

**Templates das gavetas laterais** — a raiz lê a chave da etiqueta, e o rodapé entra por carga
própria. Vale para as cinco gavetas; endereço e endereço externo ganham o `data-gaveta` que não tinham.

```html
<div class="gaveta-lateral" data-gaveta="{{ etiqueta.chave }}">
  ...
    <div class="gaveta-lateral-corpo" data-scroll-etched>...</div>
    {% include "mapping/_rodape_gaveta.html" with chave=etiqueta.chave %}
  </div>
```

**`templates/mapping/_rodape_gaveta.html`** — o rodapé não faz parte da cena guardada: a cada vez que
a gaveta é mostrada ele busca os recentes de agora.

```html
<footer class="gaveta-lateral-rodape"
        hx-get="{% url 'mapping:recentes' %}?chave={{ chave|urlencode }}"
        hx-trigger="load" hx-target="this" hx-swap="innerHTML"></footer>
```

**`apps/mapping/views.py`** — o rodapé, a devolução e a gaveta dos desenhos.

```python
class GavetaNaTela(BaseModel):
    chave: str


@require_GET
def recentes(request: HttpRequest) -> HttpResponse:
    """Rota aberta: lê só os recentes da sessão de quem pede."""
    na_tela = GavetaNaTela.model_validate(request.GET.dict())
    demais = recentes_da_sessao(request.session).fora(na_tela.chave)
    return render(request, TEMPLATE_RECENTES, {"demais": demais})


class PedidoDeCena(BaseModel):
    chave: str


@require_POST
def devolver_cena(request: HttpRequest) -> HttpResponse:
    """Rota aberta: devolve só o que a sessão de quem pede guardou."""
    pedido = PedidoDeCena.model_validate(request.POST.dict())
    recente = recentes_da_sessao(request.session).de_chave(pedido.chave)
    # Sessão expirada, ou cena que saiu da lista por outra aba: aviso, e o mapa não muda.
    if recente is None or recente.cena is None:
        return render(request, TEMPLATE_AVISO, contexto_aviso(MSG_CENA_FORA_DOS_RECENTES))
    # A devolvida volta ao topo: é o que faz o voltar seguinte trazer a gaveta de onde se saiu.
    abrir_nos_recentes(request.session, recente)
    return render(request, TEMPLATE_CENA, contexto_cena(recente.cena))


@require_POST
def desenhos_da_bancada(request: HttpRequest) -> HttpResponse:
    ...
    gaveta = MontarGavetaDesenhos()(entrada)
    etiqueta = etiqueta_dos_desenhos(gaveta)
    # NOVO: entra sem cena — é o mapa que a remonta — e sai quando não sobra desenho.
    if gaveta.pocos:
        abrir_nos_recentes(request.session, Recente(etiqueta=etiqueta))
    else:
        tirar_dos_recentes(request.session, etiqueta.chave)
    ...
```

**`templates/mapping/_recentes.html`** — o que o rodapé carrega. O `data-troca-cena` marca o que
entrega a camada do mapa a outro dono; a interrogação fica fora dele, senão o `inert` a calaria junto.
A marcação é a do mock; aqui só os atributos que carregam regra.

```html
{% with anterior=demais.0 %}
  <div class="voltar-gaveta" data-troca-cena>
    {# sem `anterior`, o voltar sai `disabled` e a lista não é renderizada #}
    {% include "mapping/_recente.html" with recente=anterior %}       {# o voltar #}
    {% for recente in demais %}
      {% include "mapping/_recente.html" with recente=recente %}     {# a lista que sobe #}
    {% endfor %}
  </div>
  <span class="dica-trava tooltip" data-tip="Feche a gaveta de resultado para trocar de entidade."></span>
{% endwith %}
```

**`templates/mapping/_recente.html`** — os dois gatilhos: a cena guardada volta pelo servidor; a
gaveta dos desenhos, pelo mapa.

```html
{% if recente.cena %}
  <button type="button"
          hx-post="{% url 'mapping:devolver_cena' %}" hx-vals='{"chave": "{{ recente.etiqueta.chave }}"}'
          hx-target="#resultado-busca" hx-swap="innerHTML">
{% else %}
  <button type="button" data-pedir-desenhos>
{% endif %}
    <svg viewBox="0 0 24 24"><use href="#glifo-gaveta-{{ recente.etiqueta.tipo }}"/></svg>
    <span>{{ recente.etiqueta.resumo }}</span>
  </button>
```

**`templates/mapping/_poco_desenhos.html`** — toda ação do poço troca a cena: a lista delas ganha a
marca, e a interrogação entra no cabeçalho da placa.

```html
<div class="placa-lista__cabecalho">
  <span class="text-overline">Ações</span>
  <span class="dica-trava tooltip" data-tip="Feche a gaveta de resultado para acionar outra consulta."></span>
  ...
</div>
<div class="placa-lista__conteudo" data-troca-cena>
```

**`static/src/js/ui/trava_cena.js`** — NOVO. A gaveta que está na tela quando a gaveta inferior abre
foi renderizada antes dela: quem a trava é o navegador, lendo a marca que o servidor mandou.

```js
const MARCA = "#contexto-acao[data-contexto-acao]";

function travar() {
  const travado = document.querySelector(MARCA) !== null;
  // `inert` tira o controle do ponteiro, do teclado e do leitor de tela de uma vez.
  document.querySelectorAll("[data-troca-cena]").forEach((peca) => { peca.inert = travado; });
}

// A cada resposta assentada: cobre a marca que chega, a que sai e o rodapé que carrega depois.
export function inicializarTravaCena() {
  htmx.on("htmx:afterSettle", travar);
}
```

**`static/src/js/mapa/desenho/sincronia.js`** — a volta à gaveta dos desenhos, com o último desenho
selecionado. A seleção muda no navegador sem ida ao servidor, e por isso é ele quem a lembra.

```js
let ultimoMarcado = "";

export function pedirGavetaDesenhos(selecionado) {
  if (!mapaDaBancada) return;
  ultimoMarcado = selecionado;   // NOVO
  ...
}

// NOVO, dentro de inicializarSincronia:
document.addEventListener("change", (evento) => {
  if (evento.target.matches(".linha-desenho__marca")) ultimoMarcado = evento.target.value;
});
document.addEventListener("click", (evento) => {
  if (evento.target.closest("[data-pedir-desenhos]")) pedirGavetaDesenhos(ultimoMarcado);
});
```

**`static/src/tema-dimap.dev.css`** — o estado, sem a pele: a interrogação só existe enquanto a gaveta
inferior é dona do mapa. A aparência do `[inert]` e da interrogação é a do mock.

```css
.dica-trava { @apply hidden; }
.tela-home:has(#contexto-acao[data-contexto-acao]) .dica-trava { @apply inline-flex; }
```

## 7 · Caveats
A cena guarda o HTML da gaveta, e não os dados dela. Cada gaveta tem modelo e template próprios, e
guardar o texto pronto dispensa um contrato de serialização por tipo de gaveta. O custo é a cena não
ser revalidada: um lote alterado na base, ou um template mudado num deploy, só aparecem quando a
entidade é buscada de novo.

A `Cena` leva HTML dentro de um DTO do domínio (§3.3 do CLAUDE.md) e o devolve por `safe`. A regra dos
cinco e o que ela descarta precisam andar juntos, e o `popup_html` do `GeoJsonProperties` já é texto
renderizado no domínio. O custo é o domínio carregar conteúdo de apresentação que não lê, e a resposta
confiar na integridade da sessão.

Os recentes moram na sessão do Django. É estado do servidor, sem lista no navegador (§3.1), e vale
para todos os processos do servidor web. O custo é duplo: a sessão é lida inteira por toda requisição
que a toca, e cinco cenas com o desenho de uma avenida longa a deixam grande, sem teto por tamanho; e
ela é do navegador, não da aba, de modo que duas abas compartilham a mesma lista.

A gaveta dos desenhos é a única sem cena. Ela é o espelho do que está no mapa, e as ações do poço saem
filtradas por perfil no próprio HTML dela. O custo é o item dos recentes ter dois gatilhos, e a volta
a ela depender de JavaScript sem teste automatizado.

A trava é o atributo `inert`, posto por JavaScript de estado visual (§7.2, mediante aprovação). A
gaveta que está na tela quando a gaveta inferior abre foi renderizada antes dela, e CSS sozinho tira o
ponteiro mas não o teclado. O custo é mais um módulo sem teste automatizado.

Esta SPEC muda uma condição da localizacao_lote/003: acionar "Lotes intersectados" de novo, com a
gaveta inferior aberta, deixa de trocar o resultado, e o mesmo vale para as consultas das SPECs
geocodificacao/005 e 008. Trocar o conjunto por esse caminho descartava os lotes já tirados sem passar
pelo aviso de fechar, e a consulta sobre ponto trocava a camada do mapa por baixo da tabela. O custo é
um passo a mais para consultar outro desenho — fechar a gaveta —, e as três SPECs e a skill
`acao-sobre-desenho` ganharem versão nova na implementação.

Guardar só informação pública na cena é disciplina de quem escreve a gaveta, não tipo. O template é
livre para pôr qualquer coisa no HTML. O custo é que uma gaveta nova que renderize ação por perfil
direto no corpo a congela na cena, e só o teste da gaveta do lote vigia isso.

O rodapé entra por carga própria, e não junto da gaveta. Dentro da cena guardada ele traria a lista do
dia em que a gaveta foi aberta. O custo é uma requisição a mais por gaveta mostrada, e por traço na
gaveta dos desenhos.

`recentes` e `devolver_cena` são rotas abertas. Elas não são ato administrativo, a informação das
gavetas é pública (§3.5), e cada uma lê só a sessão de quem pede. O custo é o visitante anônimo passar
a ter sessão gravada no banco, com até cinco cenas, a partir da primeira gaveta que abre.

## 8 · Testes (TDD)
- `test_abrir_poe_no_topo_sem_repetir_e_guarda_cinco` — abrir a sexta gaveta derruba a mais antiga;
  abrir uma chave que já está na lista a leva ao topo com a cena nova, sem duplicar.
- `test_devolver_cena_reenvia_gaveta_e_mapa_sem_consultar_a_base` — POST do lote com fetcher fake e,
  depois, `devolver_cena` com a chave dele: a resposta traz o mesmo payload de mapa e a mesma gaveta
  no OOB do `#gaveta-entidade`, e o fetcher foi chamado uma vez só.
- `test_cada_gaveta_de_entidade_entra_nos_recentes` — lote, lote mais próximo, endereço, endereço
  externo e logradouro: aberta a gaveta, a raiz traz o `data-gaveta` da tabela do §3, e o rodapé de
  outra gaveta a lista com o glifo do tipo e o resumo.
- `test_voltar_alterna_entre_as_duas_ultimas` — na primeira gaveta o voltar sai `disabled` e sem
  lista; aberta a segunda, ele aponta para a primeira; devolvida a primeira, aponta para a segunda.
- `test_gaveta_devolvida_pede_as_acoes_de_novo` — a gaveta do lote aberta por quem tem competência é
  guardada com o `hx-get` de `hx-trigger="load"` das ações, e sem nenhum botão de ação no corpo.
- `test_gaveta_dos_desenhos_entra_sem_cena_e_sai_sem_desenho` — POST dos desenhos com um ponto a põe
  nos recentes com `data-pedir-desenhos` e sem `hx-post`; POST com a coleção vazia a tira.
- `test_lote_da_tabela_nao_entra_nos_recentes` — o `detalhe_do_lote` devolve a gaveta com
  `data-gaveta` e rodapé, e os recentes da sessão ficam como estavam.
- `test_o_que_troca_a_cena_declara_a_trava` — o voltar, a lista e as ações do poço dos desenhos saem
  dentro de `data-troca-cena`, com a interrogação fora dele; os controles da gaveta inferior e o poço
  de ações do lote, não.
- `test_cena_fora_dos_recentes_vira_aviso` — `devolver_cena` com chave que não está na sessão responde
  o aviso, sem payload de mapa.
- `test_sessao_de_outro_formato_recomeca_vazia` — sessão com recentes que o modelo não valida não
  derruba a resposta: a gaveta abre e a lista recomeça dela.

O JavaScript — o `inert` da trava e a volta à gaveta dos desenhos — não tem teste automatizado e fica
no smoke test manual (§7).
