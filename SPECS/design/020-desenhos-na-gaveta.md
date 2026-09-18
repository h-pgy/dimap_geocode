---
spec: design/020
versao: v4
atualizado_em: 2026-09-17
testes_tdd: true
implementado: true
changelog:
  - v1: versão inicial
  - v2: "[bugfix] círculo chegava à gaveta como ponto: a conversão não trocava a camada no mapa"
  - v3: ponto passa a mostrar a posição em graus decimais, com graus-minutos-segundos no hover; ações ganham swell
  - v4: clicar num desenho no mapa marca a linha dele na gaveta, e os não selecionados deixam de ser atenuados
---

# SPEC design/020 — Os desenhos da bancada na gaveta

## 1 · User story
O servidor da DIMAP escolhe um dos traços que fez na bancada, no contexto da gaveta lateral da home,
para dizer sobre qual geometria as ações vão operar.

## 2 · Condições de pronto
- [ ] Concluir um desenho na bancada abre a gaveta lateral com **um poço por tipo desenhado** —
      ponto, linha e polígono, nessa ordem —, cada poço listando os desenhos do seu tipo, sem login.
- [ ] A linha de cada desenho mostra a medida dele: **área** no polígono, **comprimento** na linha.
- [ ] A linha do ponto mostra a **posição** dele em graus decimais com sinal — latitude, longitude —, e o
      hover sobre ela mostra a mesma posição em **graus, minutos e segundos**, com hemisfério.
- [ ] O **último desenhado** de um tipo nasce selecionado no poço dele, e desenhar de outro tipo
      **não muda** a seleção dos demais poços.
- [ ] O desenho selecionado de cada poço aparece no mapa **realçado** — traço mais grosso ou ponto
      maior, por cima dos demais — e os demais mantêm o **traço normal** de quando foram desenhados;
      trocar a seleção troca o realce na mesma hora.
- [ ] Clicar num desenho no mapa, sem ferramenta da bancada na mão, **marca a linha dele** no poço
      do seu tipo — com o mesmo destaque da marca pela gaveta — e abre a gaveta se estava recolhida.
- [ ] Apagar um desenho tira a linha do poço; apagado o último do tipo, **o poço some**; apagados
      todos, **a gaveta some**.
- [ ] Modificar geometria já desenhada — vértices, mover, girar, recortar — **refaz as medidas** da
      lista ao sair do modo de modificação.
- [ ] A gaveta dos desenhos ocupa a gaveta da entidade: concluir um desenho **troca** o que estava
      nela, e recolher pela paleta não perde a lista.
- [ ] O design do poço e da linha selecionável foi aprovado no mock e as peças novas portadas para o
      tema e o styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
O traço é o que a [bancada](018-bancada-desenho.md) produz, com a cor por tipo que ela já
define; a pergunta que esta SPEC faz a ela é só "o que está no mapa agora?". A reprojeção é a de
[localizacao_lote/002](../localizacao_lote/002-lote-mais-proximo-do-endereco.md#3--domínio).

**`services/domain/desenho/models.py`**

```python
class TipoDesenho(StrEnum):
    PONTO = "ponto"
    LINHA = "linha"
    POLIGONO = "poligono"


TIPO_POR_GEOMETRIA = {
    "Point": TipoDesenho.PONTO,
    "LineString": TipoDesenho.LINHA,
    "MultiLineString": TipoDesenho.LINHA,
    "Polygon": TipoDesenho.POLIGONO,
    "MultiPolygon": TipoDesenho.POLIGONO,
}


class Desenho(BaseModel):
    """Um traço da bancada, no CRS do mapa. `id_bancada` é a camada no mapa: é o que liga a linha da
    lista ao traço destacado."""

    model_config = ConfigDict(frozen=True)

    id_bancada: str = Field(pattern=r"^\d+$")
    geometria: PointGeometry | LineGeometry | PolygonGeometry

    @computed_field
    @property
    def tipo(self) -> TipoDesenho:
        return TIPO_POR_GEOMETRIA[self.geometria.type]


class Grandeza(StrEnum):
    AREA = "area"
    COMPRIMENTO = "comprimento"


class Medida(BaseModel):
    """Quanto o traço mede. Guardada: depende do CRS métrico, que não mora no desenho."""

    grandeza: Grandeza
    valor: float = Field(gt=0)

    @computed_field
    @property
    def unidade(self) -> str:
        return "m²" if self.grandeza is Grandeza.AREA else "m"


class Eixo(StrEnum):
    LATITUDE = "latitude"
    LONGITUDE = "longitude"


class Hemisferio(StrEnum):
    NORTE = "N"
    SUL = "S"
    LESTE = "L"
    OESTE = "O"


class Coordenada(BaseModel):
    """Um eixo da posição, em graus decimais com sinal. Hemisfério, graus, minutos e segundos derivam
    dele — os três últimos arredondados ao milésimo de segundo."""

    eixo: Eixo
    graus_decimais: float = Field(ge=-180, le=180)

    @computed_field
    @property
    def hemisferio(self) -> Hemisferio: ...

    @computed_field
    @property
    def graus(self) -> int: ...

    @computed_field
    @property
    def minutos(self) -> int: ...

    @computed_field
    @property
    def segundos(self) -> float: ...


class Posicao(BaseModel):
    """Onde o ponto está, no CRS geográfico. Guardada: depende do CRS, que não mora no desenho."""

    latitude: Coordenada
    longitude: Coordenada


class DesenhoMedido(BaseModel):
    desenho: Desenho
    medida: Medida | None = None   # None no ponto, que não tem extensão
    posicao: Posicao | None = None   # ALTERADO nesta SPEC: campo novo — só no ponto


class PocoDesenhos(BaseModel):
    """Um poço da gaveta: os desenhos de um tipo e qual deles está marcado."""

    tipo: TipoDesenho
    desenhos: tuple[DesenhoMedido, ...] = Field(min_length=1)
    id_selecionado: str

    @model_validator(mode="after")
    def _selecionado_esta_no_poco(self) -> Self:
        if self.id_selecionado not in {m.desenho.id_bancada for m in self.desenhos}:
            raise ValueError("O desenho selecionado não está no poço.")
        return self


class GavetaDesenhos(BaseModel):
    """O que a gaveta mostra: um poço por tipo com desenho, na ordem da bancada."""

    pocos: tuple[PocoDesenhos, ...] = ()
```

**Mock:** [020-mock-desenhos-na-gaveta.html](020-mock-desenhos-na-gaveta.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Ações sobre o desenho selecionado: polígono → [localizacao_lote/003](../localizacao_lote/003-lotes-do-desenho.md); ponto e linha — sem dono ainda.
- Enquadrar o mapa no desenho selecionado ao marcá-lo — sem dono ainda.
- Clicar num desenho com a gaveta ocupada pela entidade de uma busca, devolvendo a ela a lista dos desenhos — sem dono ainda.
- Nome próprio dado à mão a um desenho, no lugar do rótulo por ordem — sem dono ainda.
- Perímetro do polígono ao lado da área — sem dono ainda.
- Sobrevivência dos desenhos a uma recarga da página — sem dono ainda, como já rege design/018.

## 5 · Peças de referência a compor
- `@static/src/js/mapa/desenho/bancada.js` → handlers de `pm:create`/`pm:remove` e a conversão do círculo em polígono.
- `@static/src/js/mapa/desenho/ferramentas.js` → `COR_PONTO`, `COR_LINHA`, `COR_POLIGONO`: a tinta por tipo, que o destaque não redefine.
- `@services/domain/lotes_mais_proximos/mais_proximo.py` → `_para_geos`: a conversão para `GEOSGeometry` a promover.
- `@services/domain/geometry` → `reprojetar`, `PointGeometry`, `LineGeometry`, `PolygonGeometry`.
- `@templates/lote_geocoder/partials/_gaveta_lote.html` → a casca da gaveta: cabeçalho, corpo rolável, paleta.
- `@static/src/js/mapa/desenho/ferramentas.js` → `ferramentaAtiva`: quem está na mão, lido do plugin.
- `@static/src/tema-dimap.dev.css` → `.card-well`, `.gaveta-lateral*`, `.scroll-etched`, `.tooltip`: o tooltip já tematizado.
- `@templates/core/home.html` → `.badge-ponto`, `.badge-linha`, `.badge-poligono`: a marca de tipo que já existe.
- Skills: `mock`, `componentes-frontend`, `leaflet-geoman`, `htmx`, `ontologia`, `test-django-views`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/geometry/conversao.py`** — a conversão promovida, que três submódulos já fazem.

```python
def para_geos(geometria: PointGeometry | LineGeometry | PolygonGeometry, srid: int) -> GEOSGeometry:
    geos = GEOSGeometry(json.dumps(geometria.model_dump()))
    geos.srid = srid
    return geos
```

**`services/domain/geometry/reprojecao.py`** — a linha entra no que a função aceita.

```python
def reprojetar[G: (PointGeometry, LineGeometry, PolygonGeometry)](  # ALTERADO: LineGeometry
    geometria: G,
    origem: int,
    destino: int,
) -> G: ...
```

**`services/domain/desenho/gaveta.py`** — as duas regras da iteração: o que cada traço mede e qual
deles nasce marcado.

```python
class GavetaDesenhosInput(BaseModel):
    desenhos: tuple[Desenho, ...]
    ids_selecionados: tuple[str, ...] = ()   # o que cada poço já tinha marcado antes deste redesenho
    crs_mapa: int
    crs_metrico: int
    crs_geografico: int   # ALTERADO: onde a posição do ponto é lida

    @field_validator("desenhos", "ids_selecionados", mode="before")
    @classmethod
    def _do_json(cls, valor: object) -> object:
        # O formulário manda texto: JSON malformado vira ValidationError e cai no middleware.
        return json.loads(valor) if isinstance(valor, str) else valor


GRANDEZA_POR_TIPO = {
    TipoDesenho.LINHA: Grandeza.COMPRIMENTO,
    TipoDesenho.POLIGONO: Grandeza.AREA,
}


class MontarGavetaDesenhos:
    def __call__(self, entrada: GavetaDesenhosInput) -> GavetaDesenhos:
        return self.pipeline(entrada)

    def pipeline(self, entrada: GavetaDesenhosInput) -> GavetaDesenhos:
        medidos = tuple(self._medir(desenho, entrada) for desenho in entrada.desenhos)
        # A ordem dos poços é a do enum — ponto, linha, polígono —, e tipo sem desenho não vira poço.
        pocos = tuple(
            self._poco(tipo, do_tipo, entrada.ids_selecionados)
            for tipo in TipoDesenho
            if (do_tipo := tuple(m for m in medidos if m.desenho.tipo is tipo))
        )
        return GavetaDesenhos(pocos=pocos)

    def _medir(self, desenho: Desenho, entrada: GavetaDesenhosInput) -> DesenhoMedido:
        grandeza = GRANDEZA_POR_TIPO.get(desenho.tipo)
        if grandeza is None:
            return DesenhoMedido(desenho=desenho, posicao=self._localizar(desenho, entrada))  # ALTERADO
        projetado = reprojetar(desenho.geometria, entrada.crs_mapa, entrada.crs_metrico)
        geos = para_geos(projetado, entrada.crs_metrico)
        valor = geos.area if grandeza is Grandeza.AREA else geos.length
        return DesenhoMedido(desenho=desenho, medida=Medida(grandeza=grandeza, valor=valor))

    def _localizar(self, desenho: Desenho, entrada: GavetaDesenhosInput) -> Posicao:
        # NOVO. GeoJSON é (x, y): longitude primeiro.
        longitude, latitude = reprojetar(
            desenho.geometria, entrada.crs_mapa, entrada.crs_geografico
        ).coordinates
        return Posicao(
            latitude=Coordenada(eixo=Eixo.LATITUDE, graus_decimais=latitude),
            longitude=Coordenada(eixo=Eixo.LONGITUDE, graus_decimais=longitude),
        )

    def _poco(
        self,
        tipo: TipoDesenho,
        do_tipo: tuple[DesenhoMedido, ...],
        escolhidos: tuple[str, ...],
    ) -> PocoDesenhos:
        # A escolha do usuário vale enquanto o desenho existir; caindo ele, o último desenhado
        # daquele tipo assume — e é por isso que desenhar um ponto não desmarca o polígono.
        escolhido = next(
            (m.desenho.id_bancada for m in do_tipo if m.desenho.id_bancada in escolhidos),
            do_tipo[-1].desenho.id_bancada,
        )
        return PocoDesenhos(tipo=tipo, desenhos=do_tipo, id_selecionado=escolhido)
```

**`services/domain/desenho/models.py`** — o sinal escolhe o hemisfério, e a conversão para
graus-minutos-segundos parte de um inteiro de milésimos de segundo: arredondar cada parte separado
deixaria `59,9997″` virar `60,000″`.

```python
HEMISFERIOS = {   # (positivo, negativo)
    Eixo.LATITUDE: (Hemisferio.NORTE, Hemisferio.SUL),
    Eixo.LONGITUDE: (Hemisferio.LESTE, Hemisferio.OESTE),
}
MILESIMOS_POR_GRAU = 3_600_000
MILESIMOS_POR_MINUTO = 60_000


class Coordenada(BaseModel):
    ...

    @computed_field
    @property
    def hemisferio(self) -> Hemisferio:
        positivo, negativo = HEMISFERIOS[self.eixo]
        return negativo if self.graus_decimais < 0 else positivo

    @property
    def _milesimos(self) -> int:
        return round(abs(self.graus_decimais) * MILESIMOS_POR_GRAU)

    @computed_field
    @property
    def graus(self) -> int:
        return self._milesimos // MILESIMOS_POR_GRAU

    @computed_field
    @property
    def minutos(self) -> int:
        return self._milesimos % MILESIMOS_POR_GRAU // MILESIMOS_POR_MINUTO

    @computed_field
    @property
    def segundos(self) -> float:
        return self._milesimos % MILESIMOS_POR_MINUTO / 1000
```

**`apps/mapping/views.py`** — uma rota aberta, que só monta a gaveta.

```python
@require_POST
def desenhos_da_bancada(request: HttpRequest) -> HttpResponse:
    entrada = GavetaDesenhosInput(
        desenhos=request.POST.get("desenhos", "[]"),
        ids_selecionados=request.POST.get("selecionados", "[]"),
        crs_mapa=MAP_OUTPUT_CRS,
        crs_metrico=MAP_INTERPOLATION_CRS,
        crs_geografico=MAP_GEOGRAPHIC_CRS,   # ALTERADO: setting nova, SIRGAS 2000 geográfico (4674)
    )
    gaveta = MontarGavetaDesenhos()(entrada)
    return render(request, TEMPLATE_GAVETA_DESENHOS, {"gaveta": gaveta})
```

**`templates/mapping/_poco_desenhos.html`** — cada poço é um formulário: o radio carrega o
`id_bancada` do traço, e o rodapé é onde a SPEC da ação pendura o botão dela.

```html
<form class="poco-desenhos card-well">
  {% for medido in poco.desenhos %}
    <label class="linha-desenho">
      <input type="radio" name="id_bancada" class="linha-desenho__marca"
             value="{{ medido.desenho.id_bancada }}"
             {% if medido.desenho.id_bancada == poco.id_selecionado %}checked{% endif %}>
      <span class="linha-desenho__rotulo">{{ poco.tipo|capfirst }} {{ forloop.counter }}</span>
      {% if medido.medida %}
        <span class="linha-desenho__medida">{{ medido.medida.valor|floatformat:0 }} {{ medido.medida.unidade }}</span>
      {% endif %}
      {# ALTERADO: o ponto mostra a posição; o tooltip do tema carrega os segundos. #}
      {% if medido.posicao %}
        {% with lat=medido.posicao.latitude lon=medido.posicao.longitude %}
          {# Ponto decimal, não vírgula: a vírgula já separa latitude de longitude. #}
          <span class="linha-desenho__medida tooltip tooltip-left"
                data-tip="{{ lat.graus }}°{{ lat.minutos|stringformat:'02d' }}′{% if lat.segundos < 10 %}0{% endif %}{{ lat.segundos|floatformat:3 }}″ {{ lat.hemisferio }} · {{ lon.graus }}°{{ lon.minutos|stringformat:'02d' }}′{% if lon.segundos < 10 %}0{% endif %}{{ lon.segundos|floatformat:3 }}″ {{ lon.hemisferio }}">
            {{ lat.graus_decimais|stringformat:'.3f' }}, {{ lon.graus_decimais|stringformat:'.3f' }}
          </span>
        {% endwith %}
      {% endif %}
    </label>
  {% endfor %}
  {# Vazio nesta iteração: é a âncora que a ação do tipo preenche por OOB (localizacao_lote/003). #}
  <div class="poco-desenhos__acoes" id="acoes-desenho-{{ poco.tipo }}"></div>
</form>
```

**`static/src/js/mapa/desenho/sincronia.js`** — cola de Leaflet → HTMX. A coleção é **lida do
plugin** a cada envio; nada de lista paralela no navegador.

```javascript
// Registrada DEPOIS da bancada: o handler de pm:create dela já converteu o círculo em polígono
// quando este roda.
export function inicializarSincronia(mapa, container) {
  const marcados = () =>
    Array.from(document.querySelectorAll(".linha-desenho__marca:checked")).map((radio) => radio.value);

  const enviar = () => {
    const desenhos = mapa.pm.getGeomanLayers().map((camada) => ({
      id_bancada: String(L.Util.stamp(camada)),
      geometria: camada.toGeoJSON().geometry,
    }));
    htmx.ajax("POST", container.dataset.urlDesenhos, {
      target: "#gaveta-entidade",
      swap: "innerHTML",
      values: {
        desenhos: JSON.stringify(desenhos),
        selecionados: JSON.stringify(marcados()),
      },
    });
  };

  ["pm:create", "pm:remove", "pm:cut"].forEach((evento) => mapa.on(evento, enviar));
  // Durante a modificação a geometria ainda muda: a medida se refaz quando o modo se fecha.
  ["pm:globaleditmodetoggled", "pm:globaldragmodetoggled", "pm:globalrotatemodetoggled"].forEach(
    (evento) => mapa.on(evento, (dado) => { if (!dado.enabled) enviar(); }),
  );
}
```

**`static/src/js/mapa/desenho/envio.js`** — callback de evento HTMX: a ação submete o `id_bancada`
marcado, e a geometria é lida do mapa no momento do envio.

```javascript
// Ler a camada aqui, e não no HTML da gaveta, é o que faz a ação receber o traço COMO ELE ESTÁ
// AGORA — inclusive depois de editado — em vez do que estava na tela quando a lista foi montada.
export function inicializarEnvio(mapa) {
  document.body.addEventListener("htmx:configRequest", (evento) => {
    const id = evento.detail.parameters.id_bancada;
    if (!id) return;
    const camada = mapa.pm.getGeomanLayers().find((c) => String(L.Util.stamp(c)) === String(id));
    if (camada) evento.detail.parameters.desenho = JSON.stringify(camada.toGeoJSON().geometry);
  });
}
```

**`static/src/js/mapa/desenho/catalogo.js`** — a tinta por tipo sai das entranhas do adaptador e
passa a ser catálogo, que é onde a tabela do design/018 já mora.

```javascript
export const CORES_DESENHO = { ponto: "#00B4D8", linha: "#0F766E", poligono: "#D84F7F" };
```

**`static/src/js/mapa/desenho/catalogo.js`** — o traço normal, que a ferramenta usa ao desenhar, e
o realce do selecionado, que só soma ênfase sobre ele.

```javascript
export const TRACO_POR_TIPO = {
  linha: { normal: { weight: 5, opacity: 1 }, selecionado: { weight: 8, opacity: 1 } },
  poligono: {
    normal: { weight: 3, opacity: 1, fillOpacity: 0.35 },
    selecionado: { weight: 6, opacity: 1, fillOpacity: 0.55 },
  },
};
// Marcador não passa de opacidade 1: o realce do ponto é tamanho.
export const DIAMETRO_PONTO = { normal: 14, selecionado: 22 };
```

**`static/src/js/mapa/desenho/destaque.js`** — utilitário de Leaflet: repinta o que já está no mapa.
O ícone do ponto sai de `iconePonto(estado)` em `ferramentas.js`, o mesmo que a ferramenta usa ao
desenhar.

```javascript
function pintar(camada, selecionado) {
  const tipo = tipoDaCamada(camada);   // Rectangle herda de Polygon, e Polyline não
  const estado = selecionado ? "selecionado" : "normal";
  if (tipo === "ponto") {
    camada.setIcon(iconePonto(estado));
    camada.setZIndexOffset(selecionado ? Z_PONTO_SELECIONADO : 0);
    return;
  }
  const cor = CORES_DESENHO[tipo];
  camada.setStyle({ color: cor, fillColor: cor, ...TRACO_POR_TIPO[tipo][estado] });
  if (selecionado) camada.bringToFront();
}

export function destacarSelecionados(mapa) {
  const marcados = new Set(
    Array.from(document.querySelectorAll(".linha-desenho__marca:checked")).map((radio) => radio.value),
  );
  mapa.pm.getGeomanLayers().forEach((camada) => {
    pintar(camada, marcados.has(String(L.Util.stamp(camada))));
  });
}
```

**`static/src/js/mapa/desenho/selecao.js`** — o caminho de volta: o clique no traço marca o radio
dele. Quem repinta continua sendo o `change` do radio; o mapa não guarda seleção nenhuma.

```javascript
// Um ouvinte no mapa, e não um por camada: camada que ouve click vira alvo do Leaflet, e o marcador
// (bubblingMouseEvents: false) engoliria o clique — inclusive o cursor do Geoman, que cria o vértice.
export function inicializarSelecao(mapa) {
  mapa.on("click", (evento) => selecionar(mapa, evento));
}

function selecionar(mapa, evento) {
  // Com ferramenta na mão o clique é do plugin: vértice, arrasto, apagar.
  if (mapa.pm.globalDrawModeEnabled() || ferramentaAtiva(mapa)) return;
  // O traço clicado é achado pelo elemento DOM dele; resultado da busca não tem linha na gaveta.
  const alvo = evento.originalEvent.target;
  const camada = mapa.pm.getGeomanLayers().find((c) => c.getElement()?.contains(alvo));
  if (!camada) return;
  const radio = document.querySelector(`.linha-desenho__marca[value="${L.Util.stamp(camada)}"]`);
  if (!radio) return;

  // O clique é no desenho que a gaveta lista: não chega ao "clique fora" do design/019.
  L.DomEvent.stopPropagation(evento.originalEvent);
  radio.checked = true;
  radio.dispatchEvent(new Event("change", { bubbles: true }));   // destaque no mapa, como pela gaveta
  abrirGaveta(radio.closest(".gaveta-lateral"));
  radio.closest(".linha-desenho").scrollIntoView({ block: "nearest" });
}

// Mesmo gesto da paleta: o checkbox e o change que a bancada escuta para se reacomodar.
function abrirGaveta(gaveta) {
  const toggle = gaveta.querySelector(".gaveta-lateral-toggle");
  if (toggle.checked) return;
  toggle.checked = true;
  toggle.dispatchEvent(new Event("change", { bubbles: true }));
}
```

**`static/src/js/mapa/init.js`** — a sincronia entra depois da bancada, e o destaque reage à marca e
ao assentamento do swap.

```javascript
inicializarBancadaDesenho(mapa);
inicializarSincronia(mapa, container);   // NOVO nesta SPEC
inicializarEnvio(mapa);                  // NOVO nesta SPEC
inicializarSelecao(mapa);                // NOVO nesta SPEC
document.addEventListener("change", (evento) => {
  if (evento.target.matches(".linha-desenho__marca")) destacarSelecionados(mapa);
});
document.body.addEventListener("htmx:afterSettle", () => destacarSelecionados(mapa));
```

**`static/src/tema-dimap.dev.css`** — as peças novas do mock: o átomo `.linha-desenho` (com
`.linha-desenho__marca`, `__rotulo` e `__medida`) e a molécula `.poco-desenhos`, composta sobre o
`.card-well`. A linha marcada lê o próprio radio (`:has(.linha-desenho__marca:checked)`) — nenhum
estado de seleção em JavaScript. E a variante `.item-menu-swell`, empilhada sobre o `.item-menu` da
linha de ação, que incha sob o ponteiro sem alterar o `.item-menu`.

## 7 · Caveats
A coleção inteira sobe a cada mudança, e o servidor não guarda nada entre um envio e o outro. A home
não tem sessão de trabalho, e guardar desenho criaria estado que ninguém limpa. Custo: o GeoJSON de
tudo que está no mapa viaja a cada traço criado, apagado ou modificado.

A identidade de cada desenho é o `L.Util.stamp` da camada do Leaflet, não um id de domínio. É o único
identificador que existe enquanto o desenho não é submetido a lugar nenhum. Custo: a seleção não
sobrevive a uma recarga da página, e o id não serve de referência para nada fora da sessão do
navegador.

O formulário do poço não é autossuficiente: ele submete só o `id_bancada` marcado, e a geometria é
enxertada por um callback `htmx:configRequest`. O traço vive no navegador, e lê-lo no envio entrega à
ação o desenho como ele está no mapa, não como estava quando a lista foi montada. Custo: sem
JavaScript, o botão de uma ação manda um id que o servidor não sabe resolver.

A gaveta dos desenhos ocupa o `#gaveta-entidade` e substitui o que a busca tiver posto lá. O mapa tem
uma gaveta lateral só, e disputá-la seria inventar uma segunda casca. Custo: quem desenha sobre um
lote localizado perde a ficha dele da tela e precisa buscar de novo.

`htmx.ajax` é chamado de dentro de callbacks do Leaflet-Geoman. É cola entre as duas bibliotecas e
não carrega estado de domínio, que é o que o §7.2 do CLAUDE.md permite. Custo: um ponto em que a
requisição não nasce de atributo HTMX no markup.

A posição do ponto é lida em SIRGAS 2000 geográfico (4674), e não no CRS do mapa (4326). SIRGAS 2000
é o referencial oficial do Brasil, o mesmo do CRS métrico. O custo é uma setting nova e um datum
diferente do mapa, que o milésimo de segundo (≈3 cm) pode chegar a mostrar.

O clique num desenho para a propagação do evento nativo. É o jeito de o clique no traço não ser lido
como "fora da gaveta" pelo design/019 sem que este conheça o Leaflet. Custo: nenhum outro ouvinte de
`click` no `document` vê esse clique — a torrezinha do encaixe aberta, por exemplo, não se fecha nele.

Os testes do §8 não cobrem JavaScript: o projeto não tem infraestrutura de teste de JS nem de render,
como já registrado em design/017 e design/018. Custo: o destaque no mapa, a marca pelo clique no
desenho e o refazer das medidas ao fechar o modo de modificação só têm prova no smoke test manual.

## 8 · Testes (TDD)
- `test_poco_por_tipo_na_ordem_da_bancada` — dois polígonos e um ponto viram dois poços, o do ponto
  antes do de polígono, e nenhum poço de linha.
- `test_cada_tipo_mostra_a_sua_grandeza` — quadrado e traço conhecidos em 4326 dão a área em m² e o
  comprimento em m no CRS métrico; o ponto vem sem medida e com a posição em graus-minutos-segundos e
  hemisfério, inclusive na borda em que os segundos arredondados chegariam a 60
  (`-23.9999999999` → `24°00′00,000″ S`).
- `test_ultimo_desenhado_do_tipo_nasce_selecionado` — sem escolha anterior, o marcado de cada poço é
  o último desenho daquele tipo na coleção.
- `test_escolha_do_usuario_sobrevive_a_desenho_de_outro_tipo` — com o polígono do meio escolhido, a
  chegada de um ponto novo mantém o polígono marcado.
- `test_escolha_apagada_devolve_a_selecao_ao_ultimo` — id escolhido que não está mais na coleção faz
  o último do tipo assumir.
- `test_desenhos_da_bancada_abrem_a_gaveta_sem_login` — POST anônimo devolve a gaveta com um poço por
  tipo e um radio por desenho, o do selecionado marcado.
- `test_radio_carrega_o_id_da_camada` — cada radio traz o `id_bancada` do seu desenho no `value`, que
  é o que a ação submete.
- `test_colecao_vazia_nao_devolve_gaveta` — POST sem desenho algum devolve corpo vazio, e a gaveta
  sai de cena.
- `test_home_carrega_a_sincronia_dos_desenhos` — a home declara a URL da rota no container do mapa e
  carrega `desenho/sincronia.js` como módulo.
- `test_styleguide_registra_as_pecas_do_poco` — `/design_system` renderiza `.poco-desenhos` e
  `.linha-desenho`.
