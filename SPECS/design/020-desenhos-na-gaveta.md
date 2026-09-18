---
spec: design/020
versao: v8
atualizado_em: 2026-09-18
testes_tdd: true
implementado: true
changelog:
  - v1: versão inicial
  - v2: "[bugfix] círculo chegava à gaveta como ponto: a conversão não trocava a camada no mapa"
  - v3: ponto passa a mostrar a posição em graus decimais, com graus-minutos-segundos no hover; ações ganham swell
  - v4: clicar num desenho no mapa marca a linha dele na gaveta, e os não selecionados deixam de ser atenuados
  - v5: a linha selecionada ganha um X que apaga o desenho depois de confirmação
  - v6: a gaveta ganha o botão "Limpar desenhos", que apaga todos os desenhos do mapa de uma vez
  - v7: limpar desenhos passa a pedir confirmação, com a contagem por tipo do que será apagado
  - v8: a gaveta passa a ter uma seleção só, e as ações de um poço aparecem só quando o selecionado é dele
---

# SPEC design/020 — Os desenhos da bancada na gaveta

## 1 · User story
O servidor da DIMAP escolhe um dos traços que fez na bancada, no contexto da gaveta lateral da home,
para dizer sobre qual geometria as ações vão operar.

## 2 · Condições de pronto
- [ ] Concluir um desenho na bancada abre a gaveta lateral com **um poço por tipo desenhado** —
      ponto, linha e polígono, nessa ordem —, cada poço listando os desenhos do seu tipo, sem login.
- [ ] A linha de cada desenho mostra a medida dele: **área** no polígono, **comprimento** na linha; a
      do ponto mostra a **posição** em graus decimais com sinal — latitude, longitude —, e o hover sobre
      ela a mesma posição em **graus, minutos e segundos**, com hemisfério.
- [ ] A gaveta tem **no máximo um desenho selecionado**, entre todos os poços: marcar um desmarca o
      que estava marcado em qualquer poço. Desenho novo **nasce sem seleção** e não muda a que existe;
      apagado o selecionado, a gaveta fica **sem seleção**.
- [ ] As ações de um poço **só aparecem** quando o desenho selecionado é daquele poço — um ponto para
      as ações de ponto, um polígono para as de polígono; sem seleção, nenhum poço mostra ação.
- [ ] O desenho selecionado aparece no mapa **realçado** — traço mais grosso ou ponto maior, por cima
      dos demais — e os demais mantêm o **traço normal** de quando foram desenhados; trocar a seleção
      troca o realce na mesma hora.
- [ ] Clicar num desenho no mapa, sem ferramenta da bancada na mão, **marca a linha dele** no poço
      do seu tipo — com o mesmo destaque da marca pela gaveta — e abre a gaveta se estava recolhida.
- [ ] Apagar um desenho — pela borracha da bancada ou pela gaveta — tira o traço do mapa e a linha do
      poço; apagado o último do tipo, **o poço some**; apagados todos, **a gaveta some**. Abaixo do
      último poço, à direita, **Limpar desenhos** pergunta se confirma, mostrando **quantos desenhos
      de cada tipo** serão apagados, na cor do tipo; só a confirmação apaga todos, e a gaveta some.
- [ ] A linha selecionada traz um **X** no canto superior direito, e as demais reservam o lugar dele
      sem mostrá-lo; clicar no X **pergunta se confirma** a deleção, com o item seguindo selecionado
      na gaveta e realçado no mapa enquanto a pergunta está aberta. Só a confirmação apaga:
      **cancelar**, `Esc` ou clicar fora da pergunta a fecha sem mudar nada.
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

    @property
    def rotulo(self) -> str:   # ALTERADO nesta SPEC: o nome do tipo como se lê, com acento
        return ROTULO_POR_TIPO[self]


ROTULO_POR_TIPO = {
    TipoDesenho.PONTO: "ponto",
    TipoDesenho.LINHA: "linha",
    TipoDesenho.POLIGONO: "polígono",
}


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


class PocoDesenhos(BaseModel):   # ALTERADO nesta SPEC: a seleção sai do poço
    """Um poço da gaveta: os desenhos de um tipo."""

    tipo: TipoDesenho
    desenhos: tuple[DesenhoMedido, ...] = Field(min_length=1)


class GavetaDesenhos(BaseModel):   # ALTERADO nesta SPEC: a seleção, única, passa a ser da gaveta
    """O que a gaveta mostra: um poço por tipo com desenho, na ordem da bancada, e o desenho marcado —
    se houver."""

    pocos: tuple[PocoDesenhos, ...] = ()
    id_selecionado: str | None = None

    @model_validator(mode="after")
    def _selecionado_esta_na_gaveta(self) -> Self:
        ids = {m.desenho.id_bancada for poco in self.pocos for m in poco.desenhos}
        if self.id_selecionado is not None and self.id_selecionado not in ids:
            raise ValueError("O desenho selecionado não está na gaveta.")
        return self
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
- `@templates/competencias/partials/_modal_remover.html` → `.modal-glass` + `.modal-box-glass`: a pergunta de confirmação que já existe.
- `@static/src/tema-dimap.dev.css` → `.btn-etched` + `.btn-etched-swell`: o botão gravado do "limpar filtros", que incha e acende em água sob o ponteiro.
- Sprite de glifos → `#glifo-x`: o X.
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
deles segue marcado.

```python
class GavetaDesenhosInput(BaseModel):
    desenhos: tuple[Desenho, ...]
    id_selecionado: str | None = None   # ALTERADO: o que a gaveta tinha marcado antes deste redesenho
    crs_mapa: int
    crs_metrico: int
    crs_geografico: int   # ALTERADO: onde a posição do ponto é lida

    @field_validator("desenhos", mode="before")
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
            PocoDesenhos(tipo=tipo, desenhos=do_tipo)
            for tipo in TipoDesenho
            if (do_tipo := tuple(m for m in medidos if m.desenho.tipo is tipo))
        )
        return GavetaDesenhos(pocos=pocos, id_selecionado=self._selecionado(entrada))   # ALTERADO

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

    def _selecionado(self, entrada: GavetaDesenhosInput) -> str | None:
        # ALTERADO. A seleção é só a escolha do usuário: desenho novo não a toma, e apagado o
        # escolhido ninguém assume — a gaveta fica sem seleção, e nenhum poço oferece ação.
        existentes = {desenho.id_bancada for desenho in entrada.desenhos}
        return entrada.id_selecionado if entrada.id_selecionado in existentes else None
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
        id_selecionado=request.POST.get("selecionado") or None,   # ALTERADO: vazio é "nenhum"
        crs_mapa=MAP_OUTPUT_CRS,
        crs_metrico=MAP_INTERPOLATION_CRS,
        crs_geografico=MAP_GEOGRAPHIC_CRS,   # ALTERADO: setting nova, SIRGAS 2000 geográfico (4674)
    )
    gaveta = MontarGavetaDesenhos()(entrada)
    return render(request, TEMPLATE_GAVETA_DESENHOS, {"gaveta": gaveta})
```

**`templates/mapping/_poco_desenhos.html`** — o poço está dentro do formulário da gaveta: o radio
carrega o `id_bancada` do traço, e o rodapé é onde a SPEC da ação pendura o botão dela. Cada linha leva
o X e a pergunta de confirmação dela.

```html
{# ALTERADO: <div>, não <form> — radios de formulários diferentes não formam um grupo só. #}
<div class="poco-desenhos card-well">
  {% for medido in poco.desenhos %}
    <label class="linha-desenho">
      <input type="radio" name="id_bancada" class="linha-desenho__marca"
             value="{{ medido.desenho.id_bancada }}"
             {% if medido.desenho.id_bancada == gaveta.id_selecionado %}checked{% endif %}>
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
      {# NOVO: o X está em toda linha — nas não marcadas fica invisível, só guardando o lugar. #}
      {# O invoker abre o <dialog> na top layer sem JS: a gaveta de vidro não o prende. #}
      <button type="button" class="linha-desenho__apagar etched"
              commandfor="apagar-desenho-{{ medido.desenho.id_bancada }}" command="show-modal"
              aria-label="Apagar {{ poco.tipo }} {{ forloop.counter }}">
        <svg viewBox="0 0 24 24"><use href="#glifo-x"/></svg>
      </button>
    </label>
    {# NOVO. Fora do <label>: clique dentro da pergunta não pode chegar ao radio. #}
    <dialog id="apagar-desenho-{{ medido.desenho.id_bancada }}" class="modal modal-glass" closedby="any">
      <div class="modal-box modal-box-glass glass-panel-thick">
        <p class="text-overline">Apagar desenho</p>
        <p>{{ poco.tipo|capfirst }} {{ forloop.counter }}</p>
        <div class="modal-action">
          <button type="button" class="btn btn-glass btn-sm"
                  commandfor="apagar-desenho-{{ medido.desenho.id_bancada }}" command="close">Cancelar</button>
          {# O value é o id_bancada: é por ele que o JS acha a camada a tirar do mapa. #}
          <button type="button" class="btn btn-onsen btn-sm linha-desenho__confirmar-apagar"
                  value="{{ medido.desenho.id_bancada }}"
                  commandfor="apagar-desenho-{{ medido.desenho.id_bancada }}" command="close">Apagar</button>
        </div>
      </div>
    </dialog>
  {% endfor %}
  {# Vazio nesta iteração: é a âncora que a ação do tipo preenche (localizacao_lote/003). #}
  {# O CSS a recolhe enquanto o radio marcado não for deste poço; a ação põe o .poco-desenhos__acoes-recorte dentro. #}
  <div class="poco-desenhos__acoes" id="acoes-desenho-{{ poco.tipo }}"></div>
</div>
```

**`static/src/js/mapa/desenho/sincronia.js`** — cola de Leaflet → HTMX. A coleção é **lida do
plugin** a cada envio; nada de lista paralela no navegador.

```javascript
// Registrada DEPOIS da bancada: o handler de pm:create dela já converteu o círculo em polígono
// quando este roda.
export function inicializarSincronia(mapa, container) {
  // ALTERADO: um radio marcado no máximo; string vazia é "nenhum".
  const marcado = () => document.querySelector(".linha-desenho__marca:checked")?.value ?? "";

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
        selecionado: marcado(),
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

**`templates/mapping/_gaveta_desenhos.html`** — o conteúdo da gaveta é um formulário só, que faz de
todos os radios um grupo: marcar um desmarca o de qualquer poço. O botão de limpar fecha o conteúdo,
depois do último poço. Peça pronta do tema: nada de CSS novo.

```html
{# ALTERADO: <form>, não <div>. A ação submete o único id_bancada marcado. #}
<form class="gaveta-lateral-conteudo">
  {% for poco in gaveta.pocos %}
    {% include "mapping/_poco_desenhos.html" with poco=poco %}
  {% endfor %}
  {# NOVO. self-end: o conteúdo é coluna flex, e o botão encosta à direita. #}
  <button type="button" class="btn-etched btn-etched-swell etched self-end"
          commandfor="limpar-desenhos" command="show-modal">
    Limpar desenhos
  </button>
  {# NOVO. A mesma pergunta do X, com a contagem de cada poço na badge da cor do tipo. #}
  <dialog id="limpar-desenhos" class="modal modal-glass" closedby="any">
    <div class="modal-box modal-box-glass glass-panel-thick">
      <p class="text-overline">Limpar desenhos</p>
      <p>Apagar todos os desenhos do mapa?</p>
      {% for poco in gaveta.pocos %}
        {% with total=poco.desenhos|length %}
          <span class="badge badge-{{ poco.tipo }} badge-sm">{{ total }} {{ poco.tipo.rotulo }}{{ total|pluralize }}</span>
        {% endwith %}
      {% endfor %}
      <div class="modal-action">
        <button type="button" class="btn btn-glass btn-sm" commandfor="limpar-desenhos" command="close">Cancelar</button>
        <button type="button" class="btn btn-onsen btn-sm" data-limpar-desenhos
                commandfor="limpar-desenhos" command="close">Apagar todos</button>
      </div>
    </div>
  </dialog>
</form>
```

**`static/src/js/mapa/desenho/apagar.js`** — utilitário de Leaflet: a confirmação tira a camada do
mapa, o limpar tira todas, e os dois avisam pelo mesmo evento da borracha do Geoman. Quem refaz a
gaveta continua sendo a sincronia.

```javascript
export function inicializarApagar(mapa) {
  document.addEventListener("click", (evento) => {
    const confirmar = evento.target.closest(".linha-desenho__confirmar-apagar");
    if (confirmar) apagar(mapa, confirmar.value);
    if (evento.target.closest("[data-limpar-desenhos]")) limpar(mapa);   // NOVO
  });
}

function apagar(mapa, id) {
  const camada = mapa.pm.getGeomanLayers().find((c) => String(L.Util.stamp(c)) === id);
  if (!camada) return;
  mapa.removeLayer(camada);
  // removeLayer não dispara pm:remove: disparado à mão, a bancada se reacomoda e a sincronia
  // reenvia a coleção exatamente como na borracha.
  mapa.fire("pm:remove", { layer: camada, shape: camada.pm.getShape() });
}

// NOVO. Um pm:remove só, depois de tirar todas: a sincronia reenvia a coleção — já vazia — uma
// vez, em vez de uma requisição por camada disputando a gaveta.
function limpar(mapa) {
  mapa.pm.getGeomanLayers().forEach((camada) => mapa.removeLayer(camada));
  mapa.fire("pm:remove", { layer: null });
}
```

**`static/src/js/mapa/init.js`** — a sincronia entra depois da bancada, e o destaque reage à marca e
ao assentamento do swap.

```javascript
inicializarBancadaDesenho(mapa);
inicializarSincronia(mapa, container);   // NOVO nesta SPEC
inicializarEnvio(mapa);                  // NOVO nesta SPEC
inicializarSelecao(mapa);                // NOVO nesta SPEC
inicializarApagar(mapa);                 // NOVO nesta SPEC
document.addEventListener("change", (evento) => {
  if (evento.target.matches(".linha-desenho__marca")) destacarSelecionados(mapa);
});
document.body.addEventListener("htmx:afterSettle", () => destacarSelecionados(mapa));
```

**`static/src/tema-dimap.dev.css`** — as peças novas do mock: o átomo `.linha-desenho` (com
`.linha-desenho__marca`, `__rotulo` e `__medida`) e a molécula `.poco-desenhos`, composta sobre o
`.card-well`. A linha marcada lê o próprio radio (`:has(.linha-desenho__marca:checked)`) — nenhum
estado de seleção em JavaScript. E a variante `.item-menu-swell`, empilhada sobre o `.item-menu` da
linha de ação, que incha sob o ponteiro sem alterar o `.item-menu`. O átomo `.linha-desenho` ganha o
elemento `__apagar`: o X gravado em cinza de rocha, `invisible` fora da linha marcada, que sob o
ponteiro incha e acende em água — a receita do `.btn-etched-swell`. A molécula `.poco-desenhos`
recolhe o `__acoes` enquanto não tiver radio marcado — de novo pelo `:has`, sem JavaScript —, com a
grade `0fr → 1fr` do `.painel-onsen` animando a altura em `ease-in-out`. O elemento novo
`__acoes-recorte` é o filho da grade que a ação preenche (localizacao_lote/003):

```css
/* ALTERADO nesta SPEC: recolhido, a margem negativa devolve o gap do poço e o invisible tira do Tab. */
.poco-desenhos__acoes {
  @apply grid -mt-1.5 opacity-0 invisible transition-all duration-300 ease-in-out empty:hidden;
  grid-template-rows: 0fr;
}
.poco-desenhos:has(.linha-desenho__marca:checked) .poco-desenhos__acoes {
  @apply mt-0 opacity-100 visible;
  grid-template-rows: 1fr;
}
/* NOVO. Sem padding, senão a trilha não chega a zero; o clip-margin deixa a sombra da placa vazar. */
.poco-desenhos__acoes-recorte {
  @apply min-h-0 overflow-clip;
  overflow-clip-margin: 1.5rem;
}
```

## 7 · Caveats
A coleção inteira sobe a cada mudança, e o servidor não guarda nada entre um envio e o outro. A home
não tem sessão de trabalho, e guardar desenho criaria estado que ninguém limpa. Custo: o GeoJSON de
tudo que está no mapa viaja a cada traço criado, apagado ou modificado.

A identidade de cada desenho é o `L.Util.stamp` da camada do Leaflet, não um id de domínio. É o único
identificador que existe enquanto o desenho não é submetido a lugar nenhum. Custo: a seleção não
sobrevive a uma recarga da página, e o id não serve de referência para nada fora da sessão do
navegador.

O formulário da gaveta não é autossuficiente: ele submete só o `id_bancada` marcado, e a geometria é
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

O átomo `.linha-desenho`, já implementado, é alterado: toda linha reserva a coluna do X. A alteração
foi pedida pelo usuário, e o X invisível é o que mantém as medidas alinhadas entre linha marcada e não
marcada. Custo: toda tela que compõe `.linha-desenho` passa a ter essa coluna.

A molécula `.poco-desenhos`, já implementada, é alterada: as ações dela ficam escondidas por CSS
enquanto o poço não tiver o desenho selecionado. A alteração foi pedida pelo usuário, e a seleção
muda no navegador sem ida ao servidor, então só o `:has` do radio acompanha a troca. Custo: o botão da
ação continua no DOM de todo poço — esconder é UX, e quem recusa a execução continua sendo a rota.

Os poços dividem um formulário só, o da gaveta, e o poço deixa de ser formulário. É o que faz dos
radios um grupo único sem JavaScript. Custo: a ação de um poço submete o formulário da gaveta inteira
— hoje só o `id_bancada` marcado, mas qualquer campo novo em outro poço passa a ir junto.

A deleção pela gaveta dispara `pm:remove` à mão, sem passar pelo modo de remoção do Geoman — no
limpar, um evento só e sem camada. Assim a bancada e a sincronia reagem a um evento só, sem um segundo
caminho de reenvio. Custo: `apagar.js` depende do nome e do formato de um evento do plugin, e uma
troca de versão que o altere, ou um ouvinte novo que leia a camada do evento, o quebra em silêncio.

A pergunta de confirmação é um `<dialog>` por linha — mais um para o limpar —, aberto pelos atributos `command`/`commandfor`, e
fecha no clique fora por `closedby`. É o que põe a pergunta na top layer, acima do vidro da gaveta,
sem uma linha de JS para abri-la. Custo: exige navegador recente — onde `closedby` faltar, a pergunta
só fecha pelo Cancelar ou pelo `Esc` —, e a marcação da pergunta se repete a cada desenho.

Os testes do §8 não cobrem JavaScript: o projeto não tem infraestrutura de teste de JS nem de render,
como já registrado em design/017 e design/018. Custo: o destaque no mapa, a marca pelo clique no
desenho, a deleção pela gaveta, o esconder das ações sem seleção e o refazer das medidas ao fechar o
modo de modificação só têm prova no smoke test manual.

## 8 · Testes (TDD)
- `test_poco_por_tipo_na_ordem_da_bancada` — dois polígonos e um ponto viram dois poços, o do ponto
  antes do de polígono, e nenhum poço de linha.
- `test_cada_tipo_mostra_a_sua_grandeza` — quadrado e traço conhecidos em 4326 dão a área em m² e o
  comprimento em m no CRS métrico; o ponto vem sem medida e com a posição em graus-minutos-segundos e
  hemisfério, inclusive na borda em que os segundos arredondados chegariam a 60
  (`-23.9999999999` → `24°00′00,000″ S`).
- `test_sem_escolha_a_gaveta_nasce_sem_selecao` — sem escolha anterior, a gaveta vem sem desenho
  selecionado, mesmo com desenhos de mais de um tipo.
- `test_escolha_sobrevive_a_desenho_novo` — com o polígono do meio escolhido, a chegada de um ponto
  novo mantém o polígono como o selecionado da gaveta.
- `test_escolha_apagada_deixa_a_gaveta_sem_selecao` — id escolhido que não está mais na coleção deixa
  a gaveta sem seleção, sem outro desenho assumir.
- `test_desenhos_da_bancada_abrem_a_gaveta_sem_login` — POST anônimo devolve a gaveta com um poço por
  tipo e um radio por desenho, todos num formulário só e só o do escolhido marcado, e o botão de
  limpar depois do último poço, cuja pergunta traz a contagem de cada tipo na badge dele (`1 ponto`,
  `1 polígono`).
- `test_linha_carrega_o_id_da_camada` — cada radio traz o `id_bancada` do seu desenho no `value`, que
  é o que a ação submete, e toda linha tem um X que abre a pergunta cujo botão de confirmar leva o
  mesmo `id_bancada`.
- `test_colecao_vazia_nao_devolve_gaveta` — POST sem desenho algum devolve corpo vazio, e a gaveta
  sai de cena.
- `test_home_carrega_a_sincronia_dos_desenhos` — a home declara a URL da rota no container do mapa e
  carrega `desenho/sincronia.js` como módulo.
- `test_styleguide_registra_as_pecas_do_poco` — `/design_system` renderiza `.poco-desenhos` e
  `.linha-desenho`.
