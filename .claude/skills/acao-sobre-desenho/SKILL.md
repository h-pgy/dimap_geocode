---
name: acao-sobre-desenho
description: Como construir algo que opera sobre um desenho da bancada no DIMAP GeoCoder — a consulta aberta ou o ato administrativo oferecido no poço de um tipo de desenho (ponto, linha, polígono). Cobre o registro de desenho e o router que monta os poços, como a rota pinça o desenho selecionado e a geometria atual dele no mapa, a resposta pela base de resultado de ação, e a coreografia das gavetas quando a lateral e a inferior estão abertas juntas (contexto de ação, busca recolhida, troca por fade, volta à bancada). Use SEMPRE que a tarefa ou a SPEC fizer um desenho do mapa ser input de uma consulta ou de uma ação, ou mexer no registro de desenho, na gaveta de resultado ou no contexto de ação.
---

# Ação sobre desenho — registro, seleção, resposta e gavetas

O desenho da bancada (SPEC `design/020`) é uma entidade territorial como as outras: pode ser o input
de uma consulta ou de um ato administrativo. O padrão nasceu na SPEC
[`localizacao_lote/003`](../../../SPECS/localizacao_lote/003-lotes-do-desenho.md) (v6), com a
consulta "Lotes intersectados". **É a fonte de verdade**: os snippets dela são a referência de código, e
esta skill é o raciocínio de como repetir o padrão.

> **Confira o `implementado:` da SPEC 003 antes de assumir que uma peça existe.** Enquanto ela estiver
> `false`, `registro_desenho.py`, `acoes_desenho.py`, `_resultado_acao.html`, `contexto_acao.js`,
> `troca_gaveta.js` e `interacao_resultado.js` podem ainda não estar no repositório. Nesse caso, a
> SPEC nova depende da 003, e isso vai declarado nela.

A promessa do padrão: **a próxima coisa sobre desenho é uma linha no registro, uma rota, o corpo da
gaveta inferior e as `properties` das features.** Se a sua implementação está mexendo em
`_gaveta_desenhos.html`, no router, no `envio.js` ou na base de resultado, pare e releia a §7.

---

## 1 · Duas naturezas: consulta ou ato

Um poço oferece dois tipos de item, como o `ItemLivre` × `ItemAcao` do painel.

| | `ConsultaSobreDesenho` | `AcaoSobreDesenho` |
|---|---|---|
| O que é | rota **aberta**, só lê dado público | **ato administrativo** (§3.5 do CLAUDE.md) |
| Quem vê o botão | todos, inclusive anônimo | quem tem a caneta (`slugs_liberados`) |
| Está no `REGISTRO` de competências? | **não** — não é concedível | **sim** — é uma `AcaoImplementada` |
| Proteção da rota | nenhuma; a exceção de rota aberta vai **declarada na SPEC** | `@acao_protegida`, registro da execução — skill `acao-administrativa` |
| Exemplo | "Lotes intersectados" (SPEC 003) | amostragem de ofertas sobre um polígono (futuro) |

Critério: se existe um perfil que **não** pode executá-la, é ato. Se qualquer um pode, é consulta,
e inscrevê-la no `REGISTRO` só polui o catálogo e as telas de concessão.

## 2 · Antes de escrever: o que perguntar ao usuário

Se a SPEC ou o pedido não disserem, **pergunte em bloco, de uma vez**; sem resposta, siga o default e
**diga qual adotou**.

| Pergunta | Default |
|---|---|
| **Consulta ou ato?** (§1) | Consulta, se só lê dado público. Na dúvida, pergunte: muda a rota inteira. |
| **Sobre quais tipos de desenho?** (`tipos`, pelo menos um) | Só o tipo que a regra de domínio aceita. Nunca "todos" por conveniência. |
| **Nome, tooltip e slug** | Nenhum: o slug decide a pasta do SVG e, no ato, é chave do registro. |
| **Glifo do ícone** (variante `pequeno`) | Proponha em palavras e **espere o ok** antes de gravar o SVG (skill `painel`). |
| **O resultado vai ao mapa com gaveta inferior?** | Sim, pela base `_resultado_acao.html` (§5). Outro formato de resultado pede outra base, e isso é SPEC própria. |
| **As features do resultado abrem gaveta lateral?** Qual? | Se a entidade já tem gaveta (lote, logradouro…), reusa a gaveta dela, intacta. |
| **Limites de conferência** (área máxima, validade da geometria…) | Toda conferência que evita ida inútil à rede vem **antes** da rede, com mensagem em português. |
| **Ato: estrutural? alcance? operação e alvo?** | As perguntas da skill `acao-administrativa` §2. O alvo do registro é o desenho (`alvo_tipo="desenho"`) ou a entidade que ele resolveu — pergunte. |

## 3 · Os passos

### 3.1 Declarar no app da ação

Cada app declara o que oferece sobre desenho num módulo próprio, como declara ações em
`acoes_declaradas.py`.

```python
# apps/<app>/desenho_declarado.py
CONSULTA_X = ConsultaSobreDesenho(
    slug="<app>.<nome>",                 # PADRAO_SLUG: é ele que encontra o SVG
    nome="Rótulo do botão",
    tooltip="O que a consulta devolve.",
    url_name="<app>:<rota>",             # tem de resolver sem argumentos
    tipos=frozenset({TipoDesenho.POLIGONO}),
)
```

Ato: a `AcaoImplementada` já declarada em `acoes_declaradas.py` e inscrita no `REGISTRO` de
competências **é envolvida**, nunca redeclarada:

```python
AcaoSobreDesenho(acao=ACAO_X, tipos=frozenset({TipoDesenho.POLIGONO}))
```

O ícone mora em `static/src/acoes/<app>/<nome>/icones/pequeno.svg` (mesmo gabarito das ações; o poço
usa a variante **pequena** via `{% icone_acao item.slug "pequeno" %}`). No ato, `PEQUENO` precisa
estar em `variantes_icone` do contrato.

### 3.2 Inscrever no registro de desenho

```python
# apps/mapping/registro_desenho.py — o ÚNICO ponto de inscrição
def _construir_registro() -> RegistroDesenho:
    return RegistroDesenho(
        itens=(
            CONSULTA_LOTES_INTERSECTADOS,
            CONSULTA_X,                                   # a linha nova
        )
    )
```

Sem autodiscover, pelo mesmo motivo do `REGISTRO` de competências: a inscrição fica num ponto só,
revisável em code review. A ordem da tupla é a ordem dos botões no poço.

### 3.3 O router — não se mexe

`OfertarNoPoco` (`apps/mapping/acoes_desenho.py`) recebe `OfertaPocoInput(tipo, slugs_liberados)` e
devolve os `ItemPoco` do registro cujo `tipos` contém o tipo do poço **e** que estão liberados
(consulta sempre, ato só com o slug nos liberados). Ele converge as duas naturezas no mesmo `ItemPoco`,
e o template do poço não sabe qual é qual.

A view da gaveta dos desenhos chama o router **uma vez por poço** e entrega pares `(poco, itens)`;
`slugs_liberados(request.user)` devolve vazio para anônimo. **O router filtra, a rota decide**: não
mostrar o botão é UX, a barreira do ato é o `@acao_protegida`.

O router mora em `apps/mapping`, não em `services/`, porque opera sobre `AcaoImplementada` e
`url_name`, peças da camada Django (caveat da SPEC 003).

### 3.4 A rota: pinçar o desenho selecionado

O botão do poço já sai pronto do `_poco_desenhos.html`:

```html
<button type="button" class="card-well item-menu item-menu-swell" title="{{ item.tooltip }}"
        hx-post="{% url item.url_name %}" hx-include=".linha-desenho__marca:checked"
        hx-target="#resultado-busca" hx-swap="innerHTML">
```

O que a rota recebe, e por quê:

1. **`id_bancada`** — o `hx-include` pesca o **único** radio `name="id_bancada"` marcado na gaveta
   inteira. Os radios de todos os poços estão num `<form>` só (`_gaveta_desenhos.html`), então formam
   um grupo: há no máximo um marcado, e ele pode ser de qualquer poço.
2. **`desenho`** — o `envio.js` (`inicializarEnvio`), no `htmx:configRequest`, acha a camada do
   Geoman cujo `L.Util.stamp` é o `id_bancada` e enxerta `JSON.stringify(camada.toGeoJSON().geometry)`.
   A geometria vem **do mapa no momento do clique**, não do HTML da gaveta: é o traço como está agora,
   inclusive depois de editado. **Nunca leia a geometria de um atributo do HTML.**

A seleção muda no navegador sem ida ao servidor, então o servidor não sabe qual poço tem o marcado.
Por isso:

- o router oferece o item **a todo poço do tipo**, e é o **CSS** que o mostra só no poço do
  selecionado: `.poco-desenhos:has(.linha-desenho__marca:checked) .poco-desenhos__acoes` abre a
  âncora; sem marcado, ela recolhe; sem itens, a âncora sai `:empty` e o `empty:hidden` a esconde
  (por isso não pode haver espaço entre a âncora e o `{% if itens %}`);
- com o botão à vista, o marcado é sempre deste poço — mas a **rota confere o tipo mesmo assim**:
  um POST forjado pode mandar qualquer geometria.

A view traduz o formulário num DTO e constrói o `Desenho` do domínio:

```python
class ConsultaX(BaseModel):
    id_bancada: str
    desenho: PolygonGeometry          # o tipo que a rota aceita; ponto/linha → ValidationError

    @field_validator("desenho", mode="before")
    @classmethod
    def _do_json(cls, valor: object) -> object:
        return json.loads(valor) if isinstance(valor, str) else valor


@require_POST
def x(request: HttpRequest) -> HttpResponse:
    consulta = ConsultaX.model_validate(request.POST.dict())
    entrada = XInput(
        desenho=Desenho(id_bancada=consulta.id_bancada, geometria=consulta.desenho),
        crs_mapa=MAP_OUTPUT_CRS,      # o desenho não carrega CRS: vem da orquestração
        ...
    )
    try:
        resultado = ExecutarX(...)(entrada)
    except (ErroDeConferenciaA, ErroDeConferenciaB) as erro:   # exceções de regra, não de validação
        return render(request, "mapping/_recusa_acao.html", contexto_aviso(str(erro)))
    return render(request, TEMPLATE_RESULTADO_X, contexto_x(resultado))
```

- **Sem `try/except` de validação**: DTO malformado (sem `desenho`, tipo errado, JSON quebrado) cai no
  `PydanticValidationMiddleware`. O `try/except` acima é de **regra de domínio** que a rota traduz em
  aviso.
- O input de domínio **também** recusa o tipo errado (`model_validator` como o `_so_poligono` da 003):
  o domínio não confia na view.
- Ato: `@acao_protegida(ACAO_X)` por cima, e `registrar_ato` na view (skill `acao-administrativa`).

### 3.5 O domínio

Em `services/domain/<submódulo>/`, callable com `pipeline`, DTO nas duas pontas. Duas regras do
padrão:

- **Conferência antes da rede.** Reprojete para o CRS métrico, confira validade e limites e só então
  consulte o WFS (`ConferirDesenho` da 003 é o modelo). O GeoServer não paga por desenho que vai ser
  recusado, e a recusa tem mensagem em português que cita o limite.
- **Reprojeção centralizada** (`reprojetar`, `para_geos` de `services.domain.geometry`); CRS vindo da
  orquestração, nunca hardcoded.

## 4 · A resposta: a base de resultado de ação

Toda ação que devolve resultado ao mapa responde estendendo **`templates/mapping/_resultado_acao.html`**.
A home reage à resposta sem saber qual ação foi. A ação só escreve:

```html
{% extends "mapping/_resultado_acao.html" %}
{% block titulo %}Rótulo{% endblock %}
{% block resumo %}...{% endblock %}   {# badge do desenho, contagem, medida #}
{% block corpo %}
  <section class="gaveta-coluna">
    {# table.table-onsen.table-onsen-compacta; cada linha: #}
    <tr data-id-feature="{{ item.id }}"
        hx-get="{% url '<app>:detalhe' %}?id={{ item.id }}"
        hx-target="#gaveta-entidade" hx-swap="innerHTML">…</tr>
    {# {% empty %} → .gaveta-vazia com o estado de falta escrito #}
  </section>
{% endblock %}
```

E o contexto:

```python
def _properties_x(item: ...) -> GeoJsonProperties:
    return GeoJsonProperties(
        id=item.id,                                            # == data-id-feature da linha
        rotulo=...,
        url_ficha=f"{reverse('<app>:detalhe')}?id={item.id}",   # a gaveta que o clique no mapa abre
    )


def contexto_x(resultado: ...) -> dict[str, Any]:
    geojson = to_geojson_feature_collection(resultado.itens, _properties_x)
    # O desenho de origem vai na marca do contexto: é ele que fica inerte ao clique (§5.4).
    contexto = contexto_resultado_acao(CONSULTA_X.slug, resultado.desenho, geojson)
    return contexto | {"resultado": resultado}
```

O que a base já faz, e a ação **não repete**:

| Peça | O que faz |
|---|---|
| `{% include "mapping/_mapa.html" %}` | o payload do mapa, na cor única `MAP_COR_RESULTADO_ACAO` (via `contexto_resultado_acao`) |
| OOB `#gaveta-inferior-conteudo` | a gaveta inferior **rasa**, com o toggle `#gaveta-resultado` **já marcado**: o swap abre a gaveta, sem JS, e ela sobe do rodapé. Dentro da placa, o `#gaveta-resultado-recolhida` (alça recolhe, paleta reabre) e o ✕ gravado, que fecha (§5.2) |
| `_recolher_gaveta_oob.html` com `toggle="gaveta-desenhos-toggle"` | recolhe a gaveta dos desenhos (só o toggle é trocado; o conteúdo fica no DOM e a paleta reabre) |
| `_contexto_acao_oob.html` com `encerra_com="#gaveta-resultado"` | a marca do contexto de ação, com o slug e o desenho de origem (§5.4) |

A recusa responde por **`mapping/_recusa_acao.html`**: o aviso do mapa + a gaveta dos desenhos
recolhida, para o aviso (que mora na busca) ficar à vista. Sem payload de mapa.

**A ligação linha ↔ feature é o `id`.** `properties.id` no GeoJSON e `data-id-feature` na linha têm de
ser o mesmo valor; `properties.url_ficha` e o `hx-get` da linha têm de apontar para a mesma rota. É
isso que o `interacao_resultado.js` usa, sem saber de que entidade se trata.

A rota de detalhe devolve a gaveta lateral **existente** da entidade, intacta, e essa gaveta precisa
de `data-gaveta="<tipo>-<id>"` na raiz `.gaveta-lateral` (§5.3).

## 5 · As gavetas juntas: a coreografia

Três superfícies convivem: a **gaveta lateral** (`#gaveta-entidade`, que mostra uma coisa por vez: a
bancada **ou** uma entidade), a **gaveta inferior** de resultado (`#gaveta-inferior-conteudo`) e a
**barra de busca** (`.search-hero`). Nenhum estado mora em cookie nem em variável JS de domínio: são
toggles e uma marca no DOM, que o servidor manda e o CSS lê.

### 5.1 A máquina de estados

| Momento | Lateral | Inferior | Busca | Quem faz |
|---|---|---|---|---|
| Bancada, desenho selecionado | desenhos, aberta, botão no poço | — | visível | `selecao.js`, CSS do poço |
| Aciona a ação | desenhos **recolhida** | **aberta**, rasa | **recolhida** | OOBs da base (§4) |
| Ação recusada | desenhos recolhida | — (a que houver fica) | visível, com o aviso | `_recusa_acao.html` |
| Clica numa linha ou numa feature | **gaveta da entidade**, acima da inferior | continua aberta | recolhida | `hx-get`/`url_ficha` → `#gaveta-entidade` |
| Clica em outra linha/feature | a entidade nova **troca por fade**, sem recolher | aberta | recolhida | `troca_gaveta.js` |
| Clica no desenho de **origem**, fora das features | nada: vale como clique no mapa vazio | aberta | recolhida | `selecao.js` lê `data-desenho` da marca |
| Clica em **outro** desenho fora das features | **desenhos**, com ele selecionado | aberta | recolhida | `selecao.js` → `pedirGavetaDesenhos` |
| Aciona de novo com outro polígono | desenhos recolhida | resultado **trocado** | recolhida | a mesma resposta |
| Recolhe a inferior (alça) | volta à **altura inteira** | fora da tela, só a **paleta** na borda | recolhida | CSS do `#gaveta-resultado-recolhida` |
| Puxa pela paleta | termina acima da inferior | **aberta** de novo, subindo devagar | recolhida | idem |
| Fecha a inferior (✕) | como estava | fechada, sem paleta | **volta** | `contexto_acao.js` apaga a marca |

### 5.2 Lateral acima da inferior

A gaveta inferior de resultado é a variante **`.gaveta-inferior-rasa`**, de **altura fixa**
(`--gaveta-rasa-altura`). Com ela aberta, a regra da home encurta a lateral:

```css
.tela-home:has(.gaveta-toggle:checked + .gaveta-inferior-rasa) .gaveta-lateral {
  bottom: calc(var(--gaveta-rasa-altura) + 0.75rem);
}
```

É a medida conhecida que deixa a lateral parar acima da inferior **sem JS**. Não troque a rasa por
uma inferior de altura variável: a lateral passaria a cobrir a tabela. Em telas `< 48rem` a regra não
vale.

**Recolher não é fechar.** A alça marca o `.gaveta-inferior-recolher`, que mora **dentro** da placa e é
lido por `:has(> …)`: a placa sai da tela, sobra a `.paleta-gaveta-inferior` (a paleta da lateral
virada para o rodapé) e a lateral volta à altura inteira. O `.gaveta-toggle` de fora, que encerra o
contexto (§5.4), **só o ✕ desmarca**. Não aponte a alça para o `#gaveta-resultado`: recolher a tabela
custaria o resultado, que só volta refazendo a ação.

### 5.2.1 A bancada fora do rodapé

Com gaveta inferior presente, aberta ou recolhida, o rodapé é dela, como a esquerda é da gaveta
lateral, e pelo mesmo mecanismo do `arrasto.js`: o `bancada.js` entrega `rodapeTomado` e
`recuoInferior` (ao lado de `esquerdaTomada` e `recuoEsquerdo`), e chama `desocuparRodape` quando a
gaveta chega, abre ou recolhe. A bancada encaixada embaixo vai para a direita; a solta atrás da gaveta
sobe acima dela; largar perto do rodapé não encaixa. Ela segue arrastável para qualquer outro lugar e
não volta sozinha ao rodapé quando a gaveta fecha.

### 5.3 A troca da gaveta lateral

O `troca_gaveta.js`, no `htmx:beforeSwap` do `#gaveta-entidade`, compara o `data-gaveta` da raiz
atual com o da resposta e marca o alvo com `data-troca-gaveta`:

- **`entrada`**: a lateral estava fechada, e a nova desliza;
- **`troca`**: estava aberta com **outra** coisa, e só o conteúdo do painel funde (`swap:150ms settle:200ms`);
- **`mesma`**: a mesma gaveta redesenhada (a bancada a cada traço), sem animação.

Por isso **toda gaveta que entra no `#gaveta-entidade` precisa de `data-gaveta` na raiz**:
`"desenhos"` na bancada, `"lote-{{ id }}"` na do lote, `"<tipo>-{{ id }}"` na sua. Sem ele, duas
entidades diferentes contam como "mesma" e a troca não anima.

### 5.4 O contexto de ação

A marca é o slot `<div id="contexto-acao" hidden>` da `core/home.html`, preenchido por OOB com
`data-contexto-acao="<slug>"`, `data-desenho="<id_bancada>"` e `data-encerra-com="#gaveta-resultado"`.
O CSS esconde a busca enquanto a marca existe; o `contexto_acao.js` só a apaga quando o controle
apontado por `data-encerra-com` é desmarcado.

O `data-desenho` é o desenho de **origem** do resultado, e quem o declara é o servidor
(`contexto_resultado_acao` recebe o `Desenho`). Enquanto a marca existe, o `selecao.js` ignora o clique
nele: um polígono que cruza a rua tem vãos sem lote, e o clique ali o reselecionaria e o traria por
cima das features, que deixariam de ser clicáveis. A regra acaba junto com o contexto. Não tente
deduzir a origem no JS pelo radio marcado: ele também existe sob resultado de busca comum.

Consequência: **fechar a gaveta inferior pelo ✕ é o único jeito de encerrar o contexto** — recolher
não encerra. Um contexto encerrado por outro caminho deixa a busca recolhida até recarregar. Se a sua
ação precisar de outro jeito de encerrar, é outro `encerra_com`, não JS novo.

### 5.5 A volta à bancada

Com a lateral mostrando uma entidade, o radio do desenho não está no DOM. O `selecao.js`, ao não
achar o radio de um desenho que **não** é o de origem (§5.4), pede a gaveta dos desenhos de volta por
`pedirGavetaDesenhos(id)` (exportado de
`sincronia.js`), já com ele selecionado. Para voltar sem clicar no mapa, há a paleta.

## 6 · O mapa com resultado

O `interacao_resultado.js` é chamado pelo `aplicarResultado` do `init.js` a cada resultado:

- **os desenhos descem** (`bringToBack`) e ficam mais transparentes (`fillOpacity: 0.2`): o clique
  sobre uma feature é da feature, e o clique em outro desenho fora delas volta à bancada;
- feature com `url_ficha` abre a gaveta dela no `#gaveta-entidade` e vira a **escolhida**;
- linha da tabela sob o ponteiro acende a feature de mesmo `id` (**ponteiro**); a clicada vira a
  **escolhida**, com realce mais forte, até outra ser escolhida. O escolhido zera a cada resultado.

**O resultado não é desenho.** O `mapa.pm.getGeomanLayers()` do plugin devolve **toda** camada
vetorial do mapa, não só os traços da bancada. Por isso o `camada_resultado.js` cria o resultado com
`pmIgnore: true` (e `snapIgnore: false`, para o encaixe continuar valendo): sem isso ele seria repintado
na tinta do desenho pelo `destaque.js`, rebaixado junto com os desenhos, listado na gaveta dos desenhos
e apagado pelo "Limpar desenhos". Camada nova que vá ao mapa fora da bancada precisa da mesma opção.

Todo resultado de ação usa a mesma cor, `MAP_COR_RESULTADO_ACAO`, distinta das tintas dos desenhos, e
o halo `.realce-resultado(-forte)` é escrito nessa tinta. **Não dê cor própria à sua ação**: é a cor
que separa, sem legenda, o que a pessoa traçou do que o sistema devolveu.

## 7 · O que a ação nova escreve, e o que ela não toca

**Escreve:**
- `apps/<app>/desenho_declarado.py` (consulta) ou o envelope `AcaoSobreDesenho` (ato);
- uma linha em `apps/mapping/registro_desenho.py`;
- o SVG `pequeno` em `static/src/acoes/<app>/<nome>/icones/`;
- a rota (DTO com `id_bancada` + `desenho`), o submódulo de domínio, o contexto com
  `contexto_resultado_acao` e `properties` com `id` + `url_ficha`;
- o template que estende `_resultado_acao.html`, só com título, resumo e corpo;
- a rota de detalhe, se as features abrem uma entidade que ainda não tem uma, com `data-gaveta` na raiz.

**Não toca:** o router, `_gaveta_desenhos.html`, `_poco_desenhos.html`, `envio.js`, `selecao.js`,
`sincronia.js`, a base `_resultado_acao.html` e os seus OOBs, `contexto_acao.js`, `troca_gaveta.js`,
`interacao_resultado.js` e as regras de CSS da §5. São peças de todas as ações: mudar uma delas é
mudar todas (§3.4 do CLAUDE.md). Se a ação não cabe nelas, **pare e pergunte**. A resposta costuma
ser uma SPEC de base nova, não um remendo.

E, como em toda ação: **a busca nunca conhece a ação.**

## 8 · Testes TDD que o padrão pede

Escolha os que se aplicam e liste-os na §8 da SPEC. Os de segurança do ato seguem à parte, pela
bateria da skill `acao-administrativa` §6.

| Teste | Fixa |
|---|---|
| poço oferece só o que opera sobre o tipo (registro fake) | `tipos` respeitado pelo router |
| ato só sai com o slug nos liberados; consulta sai com liberados vazios | a filtragem por caneta |
| POST da gaveta traz o botão com `hx-post` da rota e `hx-include=".linha-desenho__marca:checked"` no poço do tipo; o poço de outro tipo tem a âncora **vazia** | a inscrição chegou ao HTML, e o `empty:hidden` funciona |
| conferência recusa sem chamar o fetcher fake | conferência antes da rede |
| resposta traz payload com `id` e `url_ficha` em cada feature, OOB da inferior com `#gaveta-resultado` marcado e `data-id-feature` igual ao `id`, OOB do toggle dos desenhos desmarcado, OOB do `#contexto-acao` com o slug | o contrato com a home |
| recusa devolve aviso + toggle dos desenhos desmarcado, **sem** payload de mapa; desenho do tipo errado é recusado pela validação; nenhum consulta o WFS | a recusa e a defesa contra POST forjado |
| detalhe devolve a gaveta da entidade com `data-gaveta` na raiz | a troca por fade vai funcionar |

O JavaScript (ordem das camadas, realce, clique na feature, volta à bancada, fade, fim do contexto)
**não tem teste automatizado** e fica no smoke test manual. Declare isso nos Caveats da SPEC.

## 9 · Erros comuns

- **Ler a geometria do HTML** ou mandá-la num `hx-vals`: o traço editado depois da montagem da gaveta
  chega velho. Quem enxerta é o `envio.js`, na hora do envio.
- **Filtrar pela seleção no servidor.** O servidor não sabe qual poço está com a seleção; quem mostra
  só no poço certo é o CSS.
- **Confiar no botão para garantir o tipo.** A rota e o domínio recusam o tipo errado.
- **Inscrever a consulta no `REGISTRO` de competências** para "aproveitar" a maquinaria: ela vira
  concedível e some para o anônimo.
- **Redeclarar a `AcaoImplementada`** dentro do `AcaoSobreDesenho` em vez de envolver a constante.
- **Espaço entre a âncora `.poco-desenhos__acoes` e o `{% if itens %}`**: a âncora deixa de ser
  `:empty` e aparece vazia.
- **Cor própria no resultado**, ou `properties.id` diferente do `data-id-feature`: o realce não liga
  linha e feature.
- **Gaveta lateral nova sem `data-gaveta`** na raiz.
- **Camada no mapa sem `pmIgnore`** fora da bancada: o Geoman a trata como desenho (§6).
- **Chamar `contexto_resultado_acao` sem o desenho de origem**: o polígono volta a cobrir as features
  quando clicado num vão (§5.4).
- **Resolver no JS o que é da resposta**: abrir a inferior, recolher a lateral e marcar o contexto
  são OOBs do servidor. JS novo, só estado visual de controle, e com aprovação do usuário (§7.2 do
  CLAUDE.md).
- **Refazer a busca ao editar o polígono**: está fora do escopo do padrão. O resultado é de um clique.
