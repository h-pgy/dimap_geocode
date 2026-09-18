---
spec: localizacao_lote/001
versao: v6
atualizado_em: 2026-09-18
testes_tdd: true
implementado: true
markers_obrigatorios: []
changelog:
  - v1: versão inicial
  - v2: gaveta aberta tira a lateral esquerda do encaixe da bancada de desenho
  - v3: gaveta mostra o endereço cadastrado numa string só, com o codlog à parte
  - v4: gaveta aberta vira parede para o arrasto da bancada, que não entra nem fica sob ela
  - v5: sem entidade buscada a gaveta não existe, e a esquerda só é dela enquanto houver entidade
  - v6: gaveta passa a ser montada por uma classe e confronta a área do polígono com a do cadastro
---

# SPEC localizacao_lote/001 — Dados do lote na gaveta lateral

## 1 · User story
Quem usa a busca abre a gaveta lateral do lote resolvido no contexto da home para ler os dados
cadastrais dele e conferir se a área declarada no cadastro bate com a do polígono, sem tirar o mapa
da tela.

## 2 · Condições de pronto
- [ ] Resolver um lote — clique numa sugestão de contribuinte, de endereço cadastrado ou Enter na
      barra — desenha o polígono **e abre a gaveta lateral** com os dados daquele lote, sem login.
- [ ] A gaveta mostra: **SQL** (`SSS.QQQ.LLLL-D`), o endereço cadastrado **numa linha só**
      (logradouro, número e complemento), o **codlog em campo próprio**, setor/quadra/lote, tipo de
      quadra e de lote, condomínio, uso, área de terreno, área construída, CIB e a **situação do
      lançamento**.
- [ ] A gaveta mostra a **área do polígono**, medida em metros no EPSG:31983, ao lado da área de
      terreno do cadastro, e a **diferença percentual** entre elas com sinal: `+` quando o polígono é
      maior que o cadastro, `−` quando é menor. Sem área de terreno no cadastro (nula ou zero), a
      diferença sai "não informado".
- [ ] Diferença acima de **5%** em módulo sai marcada como **erro** (vermelho); acima de **2%** e até
      5%, como **alerta** (amarelo); até 2%, sem marca.
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
mesma feature já traz?": os atributos cadastrais e o polígono chegam na **mesma** requisição, e nada
é consultado a mais. A casca da gaveta é a da SPEC [design/013](../design/013-gaveta-lateral-e-paleta.md).

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

**`services/domain/lote_geocod/gaveta.py`** — NOVO nesta SPEC: o que a gaveta do lote mostra. Cada
dado é um campo medido ou um método derivado; o template só decide a apresentação.

```python
LIMITE_ALERTA_PCT = 2.0
LIMITE_ERRO_PCT = 5.0


class DivergenciaArea(StrEnum):
    """Quanto a área do polígono se afasta da área de terreno declarada no cadastro."""

    TOLERAVEL = "toleravel"  # |diferença| ≤ 2%
    ALERTA = "alerta"        # 2% < |diferença| ≤ 5%
    ERRO = "erro"            # |diferença| > 5%


class GavetaLote(BaseModel):
    """O lote como a gaveta o apresenta: os atributos do cadastro e o que se mede no polígono."""

    lote: LoteAttributes
    area_poligono_m2: float = Field(ge=0)  # medida no CRS métrico, não declarada

    @computed_field
    @property
    def diferenca_area_pct(self) -> float | None:
        # Base no cadastro: + = polígono maior que o declarado. Sem área declarada não há base.
        if not self.lote.area_terreno_m2:
            return None
        declarada = self.lote.area_terreno_m2
        return (self.area_poligono_m2 - declarada) / declarada * 100

    @computed_field
    @property
    def divergencia_area(self) -> DivergenciaArea | None:
        if self.diferenca_area_pct is None:
            return None
        modulo = abs(self.diferenca_area_pct)
        if modulo > LIMITE_ERRO_PCT:
            return DivergenciaArea.ERRO
        if modulo > LIMITE_ALERTA_PCT:
            return DivergenciaArea.ALERTA
        return DivergenciaArea.TOLERAVEL
```

**Mock:** [001-mock-dados-do-lote-na-gaveta.html](001-mock-dados-do-lote-na-gaveta.html) — leia a
skill `mock`.

## 4 · Fora de escopo
- Lote condominial: as unidades (SQLs) do condomínio e como a gaveta as mostra — sem dono ainda
  (provável caso particular da certidão "a menor").
- Confronto de áreas próprio do lote condominial (fração ideal × polígono do lote-mãe) — sem dono ainda.
- Confronto da área construída — sem dono ainda; o polígono é do terreno.
- Mini-mapa dentro da gaveta — sem dono ainda; o polígono fica no mapa de fundo.
- Dados de fora da camada `lote_cidadao` (valor venal, ITBI, histórico) — sem dono ainda.
- Codlog clicável que abre a busca de logradouros por aquele codlog — sem dono ainda.
- Ações sobre o lote na gaveta — SPEC [certidao_lancamento/001](../certidao_lancamento/001-certidao-de-um-lote.md).

## 5 · Peças de referência a compor
- `@services/domain/lote_geocod` → `LoteGeocoder`: feature do lote por setor/quadra/lote.
- `@services/domain/geometry` → `reprojetar`, `para_geos`: a medida no CRS métrico.
- `@services/domain/desenho/gaveta.py` → `MontarGavetaDesenhos`: o molde de gaveta montada por classe callable.
- `@apps/lote_geocoder/views.py` → `geocodificar_lote`: ponto único que a sugestão e o Enter já usam.
- `@templates/mapping/_mapa.html` → payload do mapa singleton; segue agnóstico de domínio.
- `@static/src/tema-dimap.dev.css` → `.gaveta-lateral*`, `.paleta-gaveta`, `.card-well`, `.valor-ausente`, `.gaveta-lateral-toggle`.
- `@templates/core/design_system.html` → markup de referência da gaveta lateral; `badge-warning` e `badge-error`.
- `@static/src/js/mapa/desenho/arrasto.js` → `inicializarArrasto`: encaixe, `posicionarLivre`, `reancorar` e os `ganchos` da bancada.
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

**`services/domain/lote_geocod/gaveta.py`** — a classe que monta a [GavetaLote](#3--domínio). Cada
dado medido é um método-passo; os derivados já são métodos do model.

```python
class GavetaLoteInput(BaseModel):
    lote: LoteFeature  # a feature inteira: atributos, polígono e o CRS em que ele chegou
    crs_metrico: int   # vem da orquestração (settings); o domínio não crava 31983


class MontarGavetaLote:
    def __call__(self, entrada: GavetaLoteInput) -> GavetaLote:
        return self.pipeline(entrada)

    def pipeline(self, entrada: GavetaLoteInput) -> GavetaLote:
        return GavetaLote(
            lote=entrada.lote.attributes,
            area_poligono_m2=self._area_poligono_m2(entrada),
        )

    def _area_poligono_m2(self, entrada: GavetaLoteInput) -> float:
        # O polígono chega no CRS do mapa (graus); área só faz sentido no CRS métrico.
        projetado = reprojetar(entrada.lote.geometry, entrada.lote.crs, entrada.crs_metrico)
        return para_geos(projetado, entrada.crs_metrico).area
```

**`apps/lote_geocoder/views.py`** — a resposta é o mapa **e** a gaveta, que a view pede montada.

```python
MAP_INTERPOLATION_CRS: int = settings.MAP_INTERPOLATION_CRS


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
    gaveta = MontarGavetaLote()(
        GavetaLoteInput(lote=features[0], crs_metrico=MAP_INTERPOLATION_CRS)
    )
    return render(
        request,
        "lote_geocoder/partials/_resultado_lote.html",
        contexto_mapa(geojson, MAP_COR_POLIGONO) | {"gaveta": gaveta},
    )
```

**`apps/lotes_mais_proximos/views.py`** — o outro caminho que abre a gaveta do lote monta a mesma
classe; a distância segue à parte, porque é do processo de busca, não do lote.

```python
gaveta = MontarGavetaLote()(
    GavetaLoteInput(lote=proximo.lote, crs_metrico=MAP_INTERPOLATION_CRS)
)
return contexto_mapa(geojson, MAP_COR_POLIGONO) | {
    "gaveta": gaveta,
    "distancia_m": proximo.distancia_m,
    "origem_busca": origem,
}
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
  {% include "lote_geocoder/partials/_gaveta_lote.html" with gaveta=gaveta %}
</div>
```

**`templates/lote_geocoder/partials/_gaveta_lote.html`** — o template lê a `GavetaLote`; o "não
informado", o sinal e a cor da faixa moram aqui, uma vez.

```html
<p>{{ gaveta.lote.endereco_completo|default:"não informado" }}</p>
<p class="text-code text-sm">{% if gaveta.lote.sql %}SQL {{ gaveta.lote.sql }}{% else %}Sem contribuinte{% endif %}</p>

<p class="text-overline">Área do polígono</p>
<p>{{ gaveta.area_poligono_m2|floatformat:0 }} m²</p>
<p class="text-overline">Área de terreno (cadastro)</p>
<p>{% if gaveta.lote.area_terreno_m2 is not None %}{{ gaveta.lote.area_terreno_m2|floatformat:0 }} m²{% else %}não informado{% endif %}</p>

{# O sinal "+" é apresentação: floatformat só escreve o "−". A faixa escolhe o token, nunca o número. #}
{% with d=gaveta.diferenca_area_pct faixa=gaveta.divergencia_area %}
  {% if d is None %}
    <p class="valor-ausente">não informado</p>
  {% else %}
    <span class="badge badge-soft {% if faixa == 'erro' %}badge-error{% elif faixa == 'alerta' %}badge-warning{% endif %}">
      {% if d > 0 %}+{% endif %}{{ d|floatformat:1 }}%
    </span>
  {% endif %}
{% endwith %}

<p>{% if gaveta.lote.possui_lancamento %}Lançamento ativo{% else %}Sem lançamento ativo{% endif %}</p>
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
que, se isso ocorrer, os atributos e a área do polígono exibidos podem ser os de um só dos polígonos
desenhados.

`area_terreno_m2` e `area_construida_m2` são as áreas **declaradas no cadastro**; só a de terreno é
confrontada com o polígono. O polígono do `lote_cidadao` é o do terreno, e não há geometria que meça
área construída. O custo é que a área construída segue exibida sem nada que acuse divergência dela.

A área do polígono é a área plana no EPSG:31983 (UTM 23S), não a geodésica. É o CRS nativo do
GeoSampa e o mesmo que o projeto já usa para medir, via `MAP_INTERPOLATION_CRS`. O custo é a
distorção de escala da projeção em São Paulo, da ordem de décimos de milésimo, desprezível diante do
limiar de 2%.

Os limiares de 2% e 5% são constantes do domínio, não configuração. A tolerância é regra da DIMAP e
fica versionada e revisável como código. O custo é que mudar a tolerância exige deploy.

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

O §2 e o §8 passam do teto de 10 da skill `specs`. O confronto de áreas é um dado a mais da mesma
gaveta, e separá-lo numa SPEC própria dividiria um único template entre duas iterações. O custo é uma
SPEC mais longa de revisar a cada mudança da gaveta.

## 8 · Testes (TDD)
- `test_feature_para_lote_le_atributos_cadastrais` — digito, complemento, situação, uso, áreas e
  CIB saem das properties da feature para o `LoteAttributes`.
- `test_endereco_completo_junta_complemento_so_quando_existe` — com complemento, `AV PAULISTA, 100 —
  APTO 12`; sem ele, só `AV PAULISTA, 100`, sem separador sobrando.
- `test_sql_so_existe_com_digito` — sem `cd_digito_sql`, `sql` é `None`; com ele, `SSS.QQQ.LLLL-D`.
- `test_possui_lancamento_exige_sql_e_situacao_ativa` — ativo sem dígito, e com dígito sem situação,
  não possuem lançamento.
- `test_area_do_poligono_medida_no_crs_metrico` — um retângulo de 20 × 30 m construído no 31983 e
  entregue à `MontarGavetaLote` no 4326 mede 600 m² (±0,5).
- `test_diferenca_de_area_tem_base_no_cadastro_e_sinal` — polígono de 525 m² contra cadastro de 500
  dá `+5,0`; contra 625 dá `−16,0`; cadastro nulo ou zero dá `None`.
- `test_divergencia_de_area_nas_bordas` — 2,0% é tolerável, 2,1% é alerta, 5,0% é alerta, 5,1% é
  erro, e o mesmo com sinal negativo.
- `test_geocodificar_lote_abre_gaveta_com_sql` — POST em `lote_geocoder:geocodificar` com fetcher
  fake devolve o payload do mapa e o fragmento OOB `#gaveta-entidade` com o SQL, o toggle marcado e a
  diferença de área com sinal marcada como erro quando passa de 5%.
- `test_gaveta_mostra_nao_informado_para_atributo_ausente` — área de terreno nula renderiza "não
  informado" na área e na diferença, e a área do polígono segue exibida.
- `test_lote_sem_contribuinte_nao_inventa_sql` — lote municipal renderiza "Sem contribuinte".
- `test_resultado_de_endereco_tira_a_gaveta` — o partial do ponto traz o OOB `#gaveta-entidade` vazio,
  sem `.gaveta-lateral` nem `.paleta-gaveta`.
- `test_lote_sem_geometria_nao_abre_gaveta` — sem feature, a resposta é o aviso, sem `#gaveta-entidade`.
- `test_home_sem_entidade_nao_traz_gaveta` — GET na home anônima traz `#gaveta-entidade` vazio, sem
  `.gaveta-lateral` nem `.paleta-gaveta`, e o `#bancada-conjunto` no mesmo documento.
