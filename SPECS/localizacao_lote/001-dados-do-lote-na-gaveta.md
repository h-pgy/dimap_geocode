---
spec: localizacao_lote/001
versao: v5
atualizado_em: 2026-09-17
testes_tdd: true
implementado: true
markers_obrigatorios: []
changelog:
  - v1: versão inicial
  - v2: gaveta aberta tira a lateral esquerda do encaixe da bancada de desenho
  - v3: gaveta mostra o endereço cadastrado numa string só, com o codlog à parte
  - v4: gaveta aberta vira parede para o arrasto da bancada, que não entra nem fica sob ela
  - v5: sem entidade buscada a gaveta não existe, e a esquerda só é dela enquanto houver entidade
---

# SPEC localizacao_lote/001 — Dados do lote na gaveta lateral

## 1 · User story
Quem usa a busca abre a gaveta lateral do lote resolvido no contexto da home para ler os dados
cadastrais dele sem tirar o mapa da tela.

## 2 · Condições de pronto
- [ ] Resolver um lote — clique numa sugestão de contribuinte, de endereço cadastrado ou Enter na
      barra — desenha o polígono **e abre a gaveta lateral** com os dados daquele lote, sem login.
- [ ] A gaveta mostra: **SQL** (`SSS.QQQ.LLLL-D`), o endereço cadastrado **numa linha só**
      (logradouro, número e complemento), o **codlog em campo próprio**, setor/quadra/lote, tipo de
      quadra e de lote, condomínio, uso, área de terreno, área construída, CIB e a **situação do
      lançamento**.
- [ ] Atributo que a base não traz sai como **"não informado"**, nunca como campo em branco nem
      `None`.
- [ ] Lote sem dígito do SQL (lote municipal, lote-mãe de condomínio) mostra o setor/quadra/lote e
      diz que **não há contribuinte** — nunca inventa um SQL.
- [ ] A situação do lançamento diz **"Lançamento ativo"** só para lote com SQL e situação `ATIVO`
      no cadastro; qualquer outro caso diz "Sem lançamento ativo".
- [ ] Sem entidade buscada — na home recém-aberta ou depois de uma busca que resolve logradouro ou
      endereço — a gaveta **não aparece, nem a paleta**.
- [ ] Lote sem geometria cadastrada continua respondendo o aviso de hoje, e a gaveta não abre.
- [ ] Com a gaveta presente, aberta ou recolhida, a bancada de desenho **não encaixa à esquerda**:
      se estava encaixada ali quando a gaveta aparece, passa para a **lateral direita** e lá
      permanece. Sem gaveta, a esquerda volta a aceitar o encaixe.
- [ ] Com a gaveta aberta, a bancada **não entra na área dela**: arrastada contra a gaveta, para
      rente à borda, solta e deitada; se estava solta sobre essa área quando a gaveta abre, é
      empurrada para fora dela.
- [ ] O design da gaveta do lote foi aprovado no mock e as peças novas portadas para o tema e o
      styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
A entidade é o **lote fiscal** como a camada `lote_cidadao` do GeoSampa o descreve. A pergunta que
esta SPEC faz ao [LoteGeocoder](../geocodificacao/002-lote-geocod-poligono.md) é "o que mais essa
mesma feature já traz?": os atributos cadastrais chegam na **mesma** requisição que traz o polígono,
e nada é consultado a mais. A casca da gaveta é a da SPEC [design/013](../design/013-gaveta-lateral-e-paleta.md).

A [bancada de desenho](../design/018-bancada-desenho.md) divide a mesma borda esquerda do mapa; a
pergunta que esta SPEC faz a ela é "quais bordas estão livres para o encaixe?".

**`services/domain/lote_geocod/models.py`** — `LoteAttributes` inteiro, com o que muda marcado.

```python
SITUACAO_ATIVA = "ATIVO"


class LoteAttributes(BaseModel):
    """O lote fiscal como a camada o cadastra."""

    id_poligono: str
    setor: str
    quadra: str
    lote: str
    tipo_lote: str
    # ALTERADO nesta SPEC: dígito do SQL. None = lote sem contribuinte (municipal, lote-mãe de condomínio).
    digito: str | None = None
    codlog: str | None = None
    nome_logradouro: str = ""
    numero_porta: str = ""
    # ALTERADO nesta SPEC: complemento do endereço cadastrado. None = não informado.
    complemento: str | None = None
    tipo_quadra: str | None = None
    condominio: str | None = None
    # ALTERADO nesta SPEC: tx_situ_lote. None = a camada não informa (típico do lote sem SQL).
    situacao: str | None = None
    # ALTERADO nesta SPEC: dc_tipo_uso_imovel.
    uso: str | None = None
    # ALTERADO nesta SPEC: áreas cadastradas em m². São do cadastro fiscal, não medidas do polígono.
    area_terreno_m2: float | None = None
    area_construida_m2: float | None = None
    # ALTERADO nesta SPEC: cd_cib.
    cib: str | None = None

    @computed_field
    @property
    def is_condominio(self) -> bool:
        return self.condominio is not None and self.condominio != "00"

    @computed_field
    @property
    def endereco(self) -> str:
        partes = [p for p in (self.nome_logradouro, self.numero_porta) if p]
        return ", ".join(partes)

    # NOVO nesta SPEC: o endereço inteiro, como a gaveta o lê. `endereco` segue sem complemento,
    # que a certidão do conjunto põe em coluna própria.
    @computed_field
    @property
    def endereco_completo(self) -> str:
        partes = [p for p in (self.endereco, self.complemento) if p]
        return " — ".join(partes)

    # ALTERADO nesta SPEC: o número de contribuinte só existe com dígito.
    @computed_field
    @property
    def sql(self) -> str | None:
        if self.digito is None:
            return None
        return f"{self.setor}.{self.quadra}.{self.lote}-{self.digito}"

    # ALTERADO nesta SPEC: "possui lançamento" é o lote ATIVO no cadastro, com contribuinte.
    @computed_field
    @property
    def possui_lancamento(self) -> bool:
        return self.sql is not None and self.situacao == SITUACAO_ATIVA
```

**Mock:** [001-mock-dados-do-lote-na-gaveta.html](001-mock-dados-do-lote-na-gaveta.html) — leia a
skill `mock`.

## 4 · Fora de escopo
- Lote condominial: as unidades (SQLs) do condomínio e como a gaveta as mostra — sem dono ainda
  (provável caso particular da certidão "a menor").
- Mini-mapa dentro da gaveta — sem dono ainda; o polígono fica no mapa de fundo.
- Dados de fora da camada `lote_cidadao` (valor venal, ITBI, histórico) — sem dono ainda.
- Codlog clicável que abre a busca de logradouros por aquele codlog — sem dono ainda.
- Ações sobre o lote na gaveta — SPEC [certidao_lancamento/001](../certidao_lancamento/001-certidao-de-um-lote.md).

## 5 · Peças de referência a compor
- `@services/domain/lote_geocod` → `LoteGeocoder`: feature do lote por setor/quadra/lote.
- `@apps/lote_geocoder/views.py` → `geocodificar_lote`: ponto único que a sugestão e o Enter já usam.
- `@templates/mapping/_mapa.html` → payload do mapa singleton; segue agnóstico de domínio.
- `@static/src/tema-dimap.dev.css` → `.gaveta-lateral*`, `.paleta-gaveta`, `.card-well`.
- `@templates/core/design_system.html` → markup de referência da gaveta lateral.
- `@static/src/js/mapa/desenho/arrasto.js` → `inicializarArrasto`: encaixe, `posicionarLivre`, `reancorar` e os `ganchos` da bancada.
- `@static/src/tema-dimap.dev.css` → `.gaveta-lateral-toggle`: o checkbox que é o estado aberto/recolhido da gaveta.
- Skills: `mock`, `componentes-frontend`, `ontologia`, `test-django-views`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/lote_geocod/geocoder.py`** — os atributos novos saem da mesma feature.

```python
# As chaves opcionais seguem num dicionário só: acrescentar atributo é uma linha aqui, e o
# `_feature_para_lote` não cresce um `if` por campo.
_OPCIONAIS: dict[str, str] = {
    "cd_tipo_quadra": "tipo_quadra",
    "cd_condominio": "condominio",
    "cd_logradouro": "codlog",
    "nm_logradouro_completo": "nome_logradouro",
    "cd_numero_porta": "numero_porta",
    "cd_digito_sql": "digito",
    "tx_complemento_endereco": "complemento",
    "tx_situ_lote": "situacao",
    "dc_tipo_uso_imovel": "uso",
    "qt_area_terreno": "area_terreno_m2",
    "qt_area_construida": "area_construida_m2",
    "cd_cib": "cib",
}
```

**`apps/lote_geocoder/views.py`** — a resposta passa a ser o mapa **e** a gaveta.

```python
def geocodificar_lote(
    request: HttpRequest,
    setor: str,
    quadra: str,
    lote: str,
    tipo_lote: str,
    cod_condominio: str | None,
) -> HttpResponse:
    entrada = LoteGeocodInput(...)
    features = LoteGeocoder(build_fetcher(settings))(entrada)
    if not features:
        return render(request, "mapping/_aviso.html", contexto_aviso(MSG_SEM_GEOMETRIA))
    geojson = to_geojson_feature_collection(features, _properties)
    # A gaveta fala de UM lote: o primeiro polígono é o lote pedido (ver Caveats).
    return render(
        request,
        "lote_geocoder/partials/_resultado_lote.html",
        contexto_mapa(geojson, MAP_COR_POLIGONO) | {"lote": features[0].attributes},
    )
```

**`templates/core/home.html`** — a home nasce com o lugar da gaveta vazio: sem casca, sem paleta.

```html
<div id="gaveta-entidade"></div>
```

**`templates/lote_geocoder/partials/_resultado_lote.html`** — organismo: mapa + gaveta fora de banda.

```html
{% include "mapping/_mapa.html" %}
{# A gaveta inteira chega por OOB — casca, toggle marcado e paleta: existir é estado do servidor. #}
<div id="gaveta-entidade" hx-swap-oob="innerHTML">
  {% include "lote_geocoder/partials/_gaveta_lote.html" with lote=lote %}
</div>
```

**`templates/lote_geocoder/partials/_gaveta_lote.html`** — o "não informado" mora no template, uma vez.

```html
<p>{{ lote.endereco_completo|default:"não informado" }}</p>
<p class="text-overline">Codlog</p>
<p class="text-code">{{ lote.codlog|default:"não informado" }}</p>
<p class="text-code text-sm">{% if lote.sql %}SQL {{ lote.sql }}{% else %}Sem contribuinte{% endif %}</p>
<p class="text-overline">Área de terreno</p>
<p>{% if lote.area_terreno_m2 is not None %}{{ lote.area_terreno_m2|floatformat:0 }} m²{% else %}não informado{% endif %}</p>
<p>{% if lote.possui_lancamento %}Lançamento ativo{% else %}Sem lançamento ativo{% endif %}</p>
```

**`templates/mapping/_sem_gaveta_oob.html`** — incluído pelos resultados de logradouro e endereço:
tira a gaveta de cena.

```html
<div id="gaveta-entidade" hx-swap-oob="innerHTML"></div>
```

**`static/src/js/mapa/desenho/arrasto.js`** — a bancada pergunta por gancho se a esquerda está
tomada e quanto dela, e continua sem saber o que é gaveta.

```javascript
export function inicializarArrasto(refs, ganchos) {
  // ALTERADO: ganchos novos. `esquerdaTomada() -> boolean` bloqueia o encaixe;
  // `recuoEsquerdo() -> px` é a parede do arrasto (0 = sem parede).
  const { fecharSubmenus, recolherFerramentas, renderizar, esquerdaTomada, recuoEsquerdo } = ganchos;
  ...
  // ALTERADO: o piso do `left` deixa de ser 0.
  function posicionarLivre(x, y) {
    const limite = telaMapa.getBoundingClientRect();
    const caixa = conjunto.getBoundingClientRect();
    conjunto.style.left = limitar(x - limite.left, recuoEsquerdo(), limite.width - caixa.width) + "px";
    conjunto.style.top = limitar(y - limite.top, 0, limite.height - caixa.height) + "px";
  }

  function encaixarNaBorda(ponteiroX, ponteiroY) {
    ...
    let dock = null;
    // ALTERADO: esquerda tomada não aceita encaixe; o ponteiro ali cai no ramo "solta e deitada".
    if (x < MARGEM_ENCAIXE && !esquerdaTomada()) dock = "left";
    else if (limite.width - x < MARGEM_ENCAIXE) dock = "right";
    ...
  }

  // NOVO: chamado quando a gaveta aparece ou abre. Encaixada à esquerda, a bancada vai para a
  // direita (mesmo eixo, só reancorar); solta atrás da parede, é empurrada até ela.
  function desocuparEsquerda() {
    if (conjunto.dataset.dock === "left") {
      reancorar("right");
      renderizar();
      return;
    }
    const recuo = recuoEsquerdo();
    const solta = conjunto.classList.contains("bancada-conjunto--solta");
    if (solta && parseFloat(conjunto.style.left) < recuo) conjunto.style.left = recuo + "px";
  }

  return { desocuparEsquerda };
}
```

**`static/src/js/mapa/desenho/bancada.js`** — o estado da gaveta é **lido do DOM**, nunca guardado
em paralelo.

```javascript
// Consulta a cada vez: o OOB cria e destrói a gaveta inteira.
function gavetaDaEntidade() {
  return document.querySelector("#gaveta-entidade > .gaveta-lateral");
}

function recuoDaGaveta() {
  const gaveta = gavetaDaEntidade();
  if (!gaveta || !gaveta.querySelector(":scope > .gaveta-lateral-toggle:checked")) return 0;
  return gaveta.offsetWidth;
}

const arrasto = inicializarArrasto(
  { conjunto, alca, barra, telaMapa },
  {
    fecharSubmenus: ...,
    recolherFerramentas: ...,
    renderizar,
    esquerdaTomada: () => gavetaDaEntidade() !== null,
    recuoEsquerdo: recuoDaGaveta,
  },
);

function acompanharGaveta() {
  if (gavetaDaEntidade()) arrasto.desocuparEsquerda();
}
// Clique na paleta dispara `change`; a gaveta criada pelo servidor (OOB) não dispara, então o
// assentamento do swap também confere.
document.addEventListener("change", (evento) => {
  if (evento.target.matches(".gaveta-lateral-toggle")) acompanharGaveta();
});
document.body.addEventListener("htmx:afterSettle", acompanharGaveta);
```

## 7 · Caveats
A gaveta mostra o primeiro polígono quando a camada devolve mais de um para o mesmo
setor/quadra/lote/tipo. Não há regra de domínio que diga qual deles é "o lote" nesse caso. O custo é
que, se isso ocorrer, os atributos exibidos podem ser os de um só dos polígonos desenhados.

`area_terreno_m2` e `area_construida_m2` são as áreas **declaradas no cadastro**, não a área do
polígono. É o que o cadastro fiscal afirma, e é o que a certidão vai citar. O custo é que as duas
podem divergir da geometria desenhada, sem que nada na gaveta acuse isso.

`possui_lancamento` lê o texto `tx_situ_lote` contra a constante `ATIVO`. A camada não publica o
domínio de valores dessa coluna, e só `ATIVO` e nulo foram observados. O custo é que um valor novo
no GeoSampa (por exemplo, `ATIVO PARCIAL`) sai como "sem lançamento", calado.

A `bancada.js` passa a conhecer a gaveta pelos seletores `#gaveta-entidade > .gaveta-lateral` e
`.gaveta-lateral-toggle`, enquanto o `arrasto.js` só recebe os ganchos `esquerdaTomada` e
`recuoEsquerdo`. A presença da casca e o checkbox já são o estado da gaveta, e lê-los evita uma cópia
desse estado em JS. O custo é que renomear o alvo ou as classes desliga a regra em silêncio, sem erro
no console.

Quando a gaveta sai de cena, a bancada que foi desalojada para a direita não volta à esquerda. Voltar
exigiria guardar em JS o encaixe anterior, um estado que hoje não existe. O custo é que quem preferia a
bancada à esquerda precisa arrastá-la de volta a cada vez que uma entidade for buscada.

Os testes do §8 não cobrem o encaixe condicionado à gaveta, pelo mesmo motivo já registrado em
design/018: o projeto não tem teste de JS. O custo é que a condição só é provada no smoke test manual,
e o §8 fixa apenas o seletor de que o JS depende.

## 8 · Testes (TDD)
- `test_feature_para_lote_le_atributos_cadastrais` — digito, complemento, situação, uso, áreas e
  CIB saem das properties da feature para o `LoteAttributes`.
- `test_endereco_completo_junta_complemento_so_quando_existe` — com complemento, `AV PAULISTA, 100 —
  APTO 12`; sem ele, só `AV PAULISTA, 100`, sem separador sobrando.
- `test_sql_so_existe_com_digito` — sem `cd_digito_sql`, `sql` é `None`; com ele, `SSS.QQQ.LLLL-D`.
- `test_possui_lancamento_exige_sql_e_situacao_ativa` — ativo sem dígito, e com dígito sem situação,
  não possuem lançamento.
- `test_geocodificar_lote_abre_gaveta_com_sql` — POST em `lote_geocoder:geocodificar` com fetcher
  fake devolve o payload do mapa e o fragmento OOB `#gaveta-entidade` com o SQL e o toggle marcado.
- `test_gaveta_mostra_nao_informado_para_atributo_ausente` — área nula renderiza "não informado".
- `test_lote_sem_contribuinte_nao_inventa_sql` — lote municipal renderiza "Sem contribuinte".
- `test_resultado_de_endereco_tira_a_gaveta` — o partial do ponto traz o OOB `#gaveta-entidade` vazio,
  sem `.gaveta-lateral` nem `.paleta-gaveta`.
- `test_lote_sem_geometria_nao_abre_gaveta` — sem feature, a resposta é o aviso, sem `#gaveta-entidade`.
- `test_home_sem_entidade_nao_traz_gaveta` — GET na home anônima traz `#gaveta-entidade` vazio, sem
  `.gaveta-lateral` nem `.paleta-gaveta`, e o `#bancada-conjunto` no mesmo documento.
