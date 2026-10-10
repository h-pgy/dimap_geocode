---
spec: street_view/002
versao: v2
atualizado_em: 2026-10-09
testes_tdd: false
implementado: false
changelog:
  - v1: versão inicial
  - v2: a gaveta do panorama passa a ser puxável
---

# SPEC street_view/002 — Street View na gaveta inferior, com o pino que anda no mapa

## 1 · User story
O servidor logado na plataforma percorre o Street View do Google na gaveta inferior, no contexto de um
endereço localizado pela busca, para ver a rua sem sair do mapa e marcar nele a posição que
escolher.

## 2 · Condições de pronto
- [ ] Logado, acionar **"Visão da rua"** na gaveta do endereço ou do endereço externo abre o panorama
      do Google **na gaveta inferior**, com o mapa à vista acima dela; nenhuma janela é aberta.
- [ ] O panorama abre na **imagem oficial do Google** mais próxima do ponto do endereço, com a câmera
      virada para ele; foto esférica enviada por usuário não conta como imagem. No mapa, o ponto do
      endereço dá lugar a um **pino**, na cor do ponto, sobre a posição da câmera.
- [ ] **Andar no panorama move o pino**, e o mapa se desloca para mantê-lo fora da área coberta pelas
      gavetas; **puxar a gaveta** pela alça dá mais ou menos altura ao panorama, e o pino segue fora
      da área coberta.
- [ ] **Arrastar o pino** e soltá-lo leva o panorama à imagem mais próxima do lugar; sem imagem dentro
      do raio, o pino volta para onde estava e a gaveta avisa.
- [ ] Sem imagem perto do endereço, com o Google fora do ar ou sem chave configurada, a gaveta mostra o
      **estado de falta escrito**, sem pino, e o ponto do endereço fica como estava.
- [ ] Enquanto o Street View está aberto, a busca, o Voltar e as ações que trocam a cena **não
      respondem**; só o "Selecionar esta posição" e o ✕ da gaveta o encerram.
- [ ] **"Selecionar esta posição"** fecha o Street View e transforma o pino num **ponto desenhado**
      onde a câmera está: a gaveta lateral passa à dos desenhos, com ele selecionado e as ações do
      ponto oferecidas, e o endereço segue alcançável pelo Voltar.
- [ ] Fechar pelo **✕** descarta a caminhada: o pino sai, e o ponto e a gaveta do endereço ficam como
      estavam antes de abrir.
- [ ] As rotas **exigem login**: sem ele, levam ao login e a chave do Google não aparece na resposta;
      coordenada ausente ou malformada é **recusada**.
- [ ] O design da gaveta do panorama, do pino e do estado de falta foi aprovado no mock e as peças
      novas portadas para o tema e o styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
O ponto é o [PointGeometry](../geocodificacao/003-address-geocod-ponto.md) que as duas entidades de
endereço carregam, como na [SPEC 001](001-street-view-na-gaveta-de-endereco.md#3--domínio). O ponto
desenhado em que o pino se transforma é o
[Desenho](../design/020-desenhos-na-gaveta.md#3--domínio) de tipo ponto da bancada, e a pergunta que
esta SPEC faz a ele é nenhuma: ela o cria no mapa, e a bancada o trata como qualquer outro. A gaveta
é a [gaveta inferior puxável](../design/022-gaveta-inferior-puxavel.md), a quem esta SPEC pergunta "a
altura mudou?".

O submódulo `street_view` responde "o que a plataforma pede ao Google para este ponto?". O
`PedidoPanorama` toma o lugar do `LinkStreetView` da SPEC 001.

```python
class PedidoPanorama(BaseModel):
    alvo: PointGeometry  # o ponto do endereço, já no CRS em que o Google lê coordenadas
    raio_m: float        # até onde o Google procura a imagem mais próxima do alvo
```

**Mock:** [002-mock-street-view-na-gaveta-inferior.html](002-mock-street-view-na-gaveta-inferior.html)
— leia a skill `mock`.

## 4 · Fora de escopo
- Street View a partir de um ponto desenhado na bancada, como consulta do poço do ponto — sem dono
  ainda.
- Street View a partir do lote, pelo ponto da testada na rua em que ele está lançado — sem dono ainda.
- Câmera virada para o imóvel no endereço interpolado, pelo lado da via que a paridade indica — sem
  dono ainda.
- Direção da câmera desenhada no pino — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/geometry` → `reprojetar`, `PointGeometry`: o ponto e a troca de CRS.
- `@templates/mapping/_resultado_acao.html` → a anatomia da gaveta inferior que chega aberta por swap (toggle marcado, alça, cabeçalho, corpo).
- `@static/src/tema-dimap.dev.css` → `.gaveta-inferior-puxavel`, `--gaveta-puxavel-partida`; `@static/src/js/ui/puxar_gaveta.js` → `gaveta-inferior:puxada`: a gaveta que se puxa pela alça e o aviso de que a altura mudou.
- `@templates/mapping/_contexto_acao_oob.html` → a marca do contexto, que recolhe a busca e arma a trava da cena.
- `@templates/mapping/_fechar_gaveta.html` + `@apps/mapping/models` → `Limpeza`: o ✕ que fecha pela rota, sem pergunta quando `aviso=None`.
- `@static/src/js/ui/trava_cena.js` → `data-troca-cena`: o que não responde enquanto a marca existe.
- `@static/src/tema-dimap.dev.css` → `.gaveta-vazia`: o estado de falta escrito.
- `@templates/mapping/_glifos_desenho.html` → `#glifo-ponto`: o desenho do pino.
- `@static/src/js/mapa/desenho/ferramentas.js` → `iconePonto`; `@static/src/js/mapa/desenho/sincronia.js` → `pedirGavetaDesenhos`: o ponto desenhado e a gaveta que o lista.
- Skills: `mock`, `componentes-frontend`, `acao-sobre-desenho` (§5), `leaflet-map`, `leaflet-geoman`, `htmx`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/street_view/models.py`** — o [PedidoPanorama](#3--domínio) e o DTO da operação.

```python
class PedidoPanoramaInput(BaseModel):
    ponto: PointGeometry
    crs_ponto: int
    crs_street_view: int
    raio_m: float
```

**`services/domain/street_view/pedido.py`** — substitui o `link.py`.

```python
class MontarPedidoPanorama:
    def __call__(self, entrada: PedidoPanoramaInput) -> PedidoPanorama:
        # uma etapa só: não há pipeline a orquestrar
        alvo = reprojetar(entrada.ponto, entrada.crs_ponto, entrada.crs_street_view)
        return PedidoPanorama(alvo=alvo, raio_m=entrada.raio_m)
```

**`config/settings.py`**

```python
STREET_VIEW_CRS = 4326
# o raio padrão do próprio Google: mais que isso, a imagem já é de outra quadra
STREET_VIEW_RAIO_M = 50.0
# chave de NAVEGADOR da Maps JavaScript API; vazia desliga o panorama. Não é o GOOGLE_GEOCODING_TOKEN
GOOGLE_MAPS_BROWSER_KEY = SecretStr(_env.google_maps_browser_key)
```

**`apps/street_view/urls.py`** — saem `popup-bloqueado/` e o redirect.

```python
urlpatterns = [
    path("abrir/", views.abrir, name="abrir"),
    path("fechar/", views.fechar, name="fechar"),
]
```

**`apps/street_view/views.py`**

```python
MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
STREET_VIEW_CRS: int = settings.STREET_VIEW_CRS
STREET_VIEW_RAIO_M: float = settings.STREET_VIEW_RAIO_M
GOOGLE_MAPS_BROWSER_KEY: SecretStr = settings.GOOGLE_MAPS_BROWSER_KEY

SLUG_CONTEXTO = "street-view"
TEMPLATE_GAVETA = "street_view/partials/_gaveta_panorama.html"
TEMPLATE_ENCERRAMENTO = "street_view/partials/_encerramento.html"

# as faltas são escritas pelo servidor e chegam ocultas: o script só revela a que aconteceu
MSG_SEM_IMAGEM = "O Google não tem imagem de rua a até {raio} m deste ponto."
MSG_SEM_IMAGEM_NO_DESTINO = "Não há imagem de rua a até {raio} m de onde o pino foi solto."
MSG_INDISPONIVEL = "A Visão da rua está indisponível no momento."


class ConsultaStreetView(BaseModel):
    lon: float
    lat: float


@login_required  # basta estar autenticado: sem contrato de ação
@require_GET
def abrir(request: HttpRequest) -> HttpResponse:
    # lon/lat ausentes ou malformados morrem no PydanticValidationMiddleware
    consulta = ConsultaStreetView.model_validate(request.GET.dict())
    entrada = PedidoPanoramaInput(
        ponto=PointGeometry(type="Point", coordinates=[consulta.lon, consulta.lat]),
        crs_ponto=MAP_OUTPUT_CRS,
        crs_street_view=STREET_VIEW_CRS,
        raio_m=STREET_VIEW_RAIO_M,
    )
    montar_pedido = MontarPedidoPanorama()
    pedido = montar_pedido(entrada)
    contexto = {
        "pedido": pedido,
        # vazia, o template não escreve o palco: a gaveta abre direto na falta "indisponível"
        "chave": GOOGLE_MAPS_BROWSER_KEY.get_secret_value(),
        "faltas": _faltas(pedido.raio_m),
        "acao": SLUG_CONTEXTO,
        "desenho": "",  # o contexto não nasceu de um desenho: nenhum fica inerte ao clique
        "limpeza_ao_fechar": Limpeza(url=reverse("street_view:fechar"), aviso=None),
    }
    return render(request, TEMPLATE_GAVETA, contexto)


@login_required
@require_POST
def fechar(request: HttpRequest) -> HttpResponse:
    # o corpo vazio esvazia a gaveta; o OOB apaga a marca do contexto e solta a trava da cena
    return render(request, TEMPLATE_ENCERRAMENTO)
```

**`templates/street_view/partials/_gaveta_panorama.html`** — o alvo do swap é o
`#gaveta-inferior-conteudo`; as classes da variante saem do mock.

```html
{% load l10n %}
<input type="checkbox" id="gaveta-street-view" class="gaveta-toggle" checked>
<aside class="glass-drawer-bottom gaveta-inferior gaveta-inferior-rasa gaveta-inferior-puxavel …" role="dialog" aria-labelledby="gaveta-street-view-titulo">
  <header class="gaveta-cabecalho items-center">
    <h2 id="gaveta-street-view-titulo">Visão da rua</h2>
    {% if chave %}
      <!-- fecha pela mesma rota do ✕; a marca é o que diz ao script para deixar o ponto desenhado.
           Nasce desabilitado: o script o libera quando a imagem chega -->
      <button type="button" class="btn btn-onsen btn-sm" data-selecionar-posicao disabled
              hx-post="{{ limpeza_ao_fechar.url }}"
              hx-target="#gaveta-inferior-conteudo" hx-swap="innerHTML swap:500ms">
        Selecionar esta posição
      </button>
    {% endif %}
    {% include "mapping/_fechar_gaveta.html" %}
  </header>
  <div class="gaveta-corpo">
    {% if chave %}
      <!-- o palco: tudo que o script precisa chega como atributo, nada como JSON -->
      <div data-street-view
           data-chave="{{ chave }}"
           data-lat="{{ pedido.alvo.coordinates.1|unlocalize }}"
           data-lon="{{ pedido.alvo.coordinates.0|unlocalize }}"
           data-raio="{{ pedido.raio_m|unlocalize }}"></div>
    {% endif %}
    <!-- sem chave, "indisponivel" já chega à vista; as demais, ocultas -->
    {% for falta in faltas %}
      <div class="gaveta-vazia" data-falta="{{ falta.motivo }}" {% if chave or falta.motivo != "indisponivel" %}hidden{% endif %}>
        {{ falta.mensagem }}
      </div>
    {% endfor %}
  </div>
</aside>
{% include "mapping/_contexto_acao_oob.html" %}
```

**`templates/street_view/partials/_encerramento.html`**

```html
<div id="contexto-acao" hidden hx-swap-oob="true"></div>
```

**`templates/street_view/partials/_item_street_view.html`** — de link a botão HTMX.

```html
{% load l10n %}
{% if request.user.is_authenticated %}
  <button type="button" class="btn btn-onsen btn-sm"
          hx-get="{% url 'street_view:abrir' %}"
          hx-vals='{"lon": "{{ ponto.coordinates.0|unlocalize }}", "lat": "{{ ponto.coordinates.1|unlocalize }}"}'
          hx-target="#gaveta-inferior-conteudo" hx-swap="innerHTML">
    Visão da rua
  </button>
{% endif %}
```

**`templates/address_geocoder/partials/_gaveta_endereco.html`** e
**`templates/geocodificacao_externa/partials/_gaveta_endereco_externo.html`** — a lista do poço ganha a
marca da trava: com o Street View aberto, nem o lote mais próximo nem um segundo "Visão da rua"
respondem.

```html
<form class="poco-acoes__lista" data-troca-cena hx-post="…">
```

**`static/src/js/mapa/street_view.js`** — iniciado pelo `init.js`, que entrega o mapa e o par
`ocultarResultado` / `devolverResultado` (tira a camada de resultado do mapa sem destruí-la, e a põe
de volta).

```javascript
const ESTADO = { panorama: null, servico: null, pino: null, emTela: null, selecionada: false };

// O script do Google entra uma vez, no primeiro panorama: quem não abre o Street View não o baixa.
function carregarGoogle(chave) { /* injeta o <script> e resolve com google.maps */ }

async function abrir(palco) {
  const alvo = { lat: Number(palco.dataset.lat), lng: Number(palco.dataset.lon) };
  const raio = Number(palco.dataset.raio);
  const maps = await carregarGoogle(palco.dataset.chave).catch(() => null);
  if (maps === null) return revelarFalta("indisponivel");
  ESTADO.servico = new maps.StreetViewService();
  // procurar pede só acervo oficial e de rua (sources GOOGLE + OUTDOOR): foto esférica de usuário
  // não tem por onde andar. getPanorama rejeita quando não há imagem no raio: é a falta "sem_imagem"
  const achado = await procurar(alvo, raio).catch(() => null);
  if (achado === null) return revelarFalta("sem_imagem");
  ESTADO.panorama = new maps.StreetViewPanorama(palco, {
    pano: achado.location.pano,
    // a câmera nasce virada para o endereço; sem isso o Google escolhe o sentido da via
    pov: { heading: maps.geometry.spherical.computeHeading(achado.location.latLng, alvo), pitch: 0 },
  });
  // só agora o ponto do endereço sai de cena: na falta, ele fica como estava
  ocultarResultado();
  ESTADO.pino = criarPino(achado.location.latLng, raio);
  ESTADO.panorama.addListener("position_changed", acompanhar);
}

// Andou no panorama → o pino anda, e o mapa o mantém fora da área coberta pelas gavetas.
function acompanhar() {
  // recém-criado, o panorama ainda não tem posição: o pino fica onde nasceu
  const posicao = ESTADO.panorama.getPosition();
  if (posicao) ESTADO.pino.setLatLng([posicao.lat(), posicao.lng()]);
  mapa.panInside(ESTADO.pino.getLatLng(), areaLivre());
}

// A gaveta foi puxada (evento gaveta-inferior:puxada) → o palco mudou de tamanho e a área livre do
// mapa também: o panorama relê o palco e o pino volta para fora das gavetas.
function acomodar() {
  if (ESTADO.panorama === null) return;
  google.maps.event.trigger(ESTADO.panorama, "resize");
  acompanhar();
}

// Soltou o pino → o panorama vai à imagem mais próxima; sem imagem, o pino volta.
async function soltar(raio) {
  const destino = ESTADO.pino.getLatLng();
  const achado = await procurar({ lat: destino.lat, lng: destino.lng }, raio).catch(() => null);
  if (achado === null) {
    acompanhar();
    return revelarFalta("sem_imagem_no_destino");
  }
  // setPano dispara position_changed: é o acompanhar que assenta o pino sobre a imagem achada
  ESTADO.panorama.setPano(achado.location.pano);
}

// O clique em [data-selecionar-posicao] só levanta a marca; quem fecha é a rota, pelo hx-post.
function marcarSelecao() {
  ESTADO.selecionada = true;
}

// A gaveta saiu do DOM. Selecionada, a posição vira ponto desenhado, pelo mesmo evento do traço
// feito à mão; fechada pelo ✕, o pino sai e o ponto do endereço volta.
function encerrar() {
  if (ESTADO.pino !== null) {
    const posicao = ESTADO.pino.getLatLng();
    mapa.removeLayer(ESTADO.pino);
    if (ESTADO.selecionada) {
      const ponto = L.marker(posicao, { icon: iconePonto("normal") }).addTo(mapa);
      mapa.fire("pm:create", { shape: "Marker", layer: ponto, selecionado: String(L.Util.stamp(ponto)) });
    } else {
      devolverResultado();
    }
  }
  ESTADO.panorama = null;
  ESTADO.pino = null;
  ESTADO.emTela = null;
  ESTADO.selecionada = false;
}

// Callback de evento do HTMX: o palco que chegou abre, o que sumiu encerra.
function conferir() {
  const palco = document.querySelector("[data-street-view]");
  if (palco === ESTADO.emTela) return;
  if (ESTADO.emTela !== null) encerrar();
  ESTADO.emTela = palco;
  if (palco !== null) abrir(palco);
}
```

**`static/src/js/mapa/desenho/sincronia.js`** — o envio que o `pm:create` dispara passa a aceitar a
seleção pedida pelo evento; no traço feito à mão ela não vem, e vale a que já estava marcada.

```javascript
mapa.on("pm:create", (evento) => pedirGavetaDesenhos(evento.selecionado ?? marcado()));
```

## 7 · Caveats
O panorama é embutido pela Maps JavaScript API na mesma tela do mapa Leaflet, o que os termos do Google
Maps Platform vedam (3.2.3(e): Street View e mapa não-Google na mesma tela). A janela à parte da SPEC
001 quebrava o contexto de trabalho, e o usuário decidiu embutir ciente da cláusula. O custo é o risco
de suspensão do projeto no Google Cloud, que derruba junto o que mais usar chave do mesmo projeto.

A chave da Maps JavaScript API vai ao navegador de quem está logado, num atributo do partial. Chave de
navegador é pública por natureza, e a proteção dela é a restrição por referrer e por API feita no
Google Console, não o segredo. O custo é uma chave que qualquer servidor logado consegue ler, ao
contrário do `GOOGLE_GEOCODING_TOKEN`, que nunca sai do servidor.

Cada panorama aberto é cobrado no SKU Dynamic Street View depois da franquia mensal; andar e arrastar o
pino trocam a imagem do mesmo panorama. Na escala do sistema o uso cabe na franquia, e a plataforma não
conta aberturas. O custo é que o teto de gasto só existe se for posto como cota no Google Console.

A existência de imagem é descoberta no navegador, pelo `StreetViewService`, e não no servidor. A
alternativa exigiria uma integração nova e uma ida ao servidor a cada pino solto — descartada. O custo
é que a falta de cobertura não é testável no pytest e o domínio nunca sabe qual panorama foi mostrado.

A posição da câmera vive só no navegador enquanto o Street View está aberto, e chega ao servidor apenas
quando é selecionada, como desenho da bancada. Mandá-la ao servidor a cada passo seria uma requisição por
passo sem nada a responder. O custo é que recarregar a página no meio da caminhada perde a posição, e
que não há registro de por onde a pessoa andou.

O pino recebe a posição do Google sem reprojeção no JavaScript. O Leaflet e o Google falam ambos em
graus WGS84, e o `STREET_VIEW_CRS` e o `MAP_OUTPUT_CRS` são hoje o mesmo. O custo é que trocar o CRS do
mapa quebra a ida do panorama ao pino sem que nenhum teste acuse (§7.2).

O `street_view.js` é mais um caso de JavaScript fora dos três do §7.2, a aprovar pelo usuário junto com
esta SPEC. O panorama é um componente do Google que só existe em JavaScript, e ligá-lo ao pino é
trabalho de evento dos dois lados. O custo é o maior script da home que não é utilitário puro do
Leaflet, com estado de interface próprio (panorama, pino, palco em tela).

O Street View abre um contexto de ação (`#contexto-acao`) sem ser ação: usa a marca para recolher a
busca e travar a troca de cena, com um slug que não está em registro nenhum. É o mecanismo que já
impede duas cenas de disputarem a gaveta inferior e a camada de resultado. O custo é que quem ler a
marca esperando um slug de ação inscrita encontra `street-view`.

As rotas exigem só login, sem contrato de ação, perfil nem registro de execução, como na SPEC 001. O
conteúdo é público do Google e não há competência a conceder (§3.5). O custo é não haver rastro de quem
abriu o quê, e promover isso a ação concedida pedir contrato, ícones e card no painel.

Selecionar a posição são duas idas ao servidor: a rota `fechar` esvazia a gaveta e apaga a marca, e a
bancada pede a gaveta dos desenhos em seguida. Uma rota só obrigaria o `street_view` a montar a gaveta dos
desenhos, que é do `mapping` — descartado. O custo é um instante em que a gaveta do endereço ainda está
na lateral com o ponto já desenhado no mapa, e uma rota `fechar` que não sabe se a posição foi
selecionada ou descartada.

## 8 · Testes (TDD)
O panorama, o pino que anda, o arrasto, a falta de imagem e a transformação em ponto desenhado
e o descarte pelo ✕ acontecem no navegador e são conferidos pelo usuário; os testes fixam o que o servidor entrega e a
quem.

**Domínio** — `tests/services/domain/street_view/test_pedido.py`
- `test_pedido_reprojeta_alvo_de_crs_metrico` — um ponto dado em 31983 vira `alvo` em graus, a menos de
  um metro do lugar esperado, e o raio pedido é o da entrada.

**Rotas** — `tests/apps/street_view/test_views.py`
- `test_abrir_logado_devolve_a_gaveta_do_panorama` — GET com `lon` e `lat` responde 200 com o toggle da
  gaveta marcado, a placa com a classe `gaveta-inferior-puxavel`, o palco com `data-lat`, `data-lon`,
  `data-raio` e `data-chave` do pedido, o botão
  "Selecionar esta posição" desabilitado e apontado para `street_view:fechar`, e o OOB do
  `#contexto-acao` com `data-contexto-acao="street-view"`.
- `test_abrir_traz_as_faltas_escritas_e_ocultas` — a gaveta traz as três faltas com `hidden`, e a de
  imagem cita o raio em metros.
- `test_abrir_sem_chave_abre_na_falta_indisponivel` — com a chave vazia a gaveta vem sem o palco, sem
  o botão de selecionar e com a falta `indisponivel` à vista.
- `test_abrir_anonimo_vai_para_o_login` — GET sem login responde 302 para o login, sem a chave no
  corpo nem no destino.
- `test_abrir_com_coordenada_malformada_e_recusado` — parametrizado: `lon=abc` e `lat` ausente
  respondem 422, sem gaveta.
- `test_fechar_esvazia_a_gaveta_e_encerra_o_contexto` — POST logado devolve só o OOB do
  `#contexto-acao` sem `data-contexto-acao`; anônimo vai para o login.

**Gavetas** — nos `test_views.py` de `address_geocoder` e `geocodificacao_externa`
- `test_gaveta_do_endereco_logado_traz_o_item_do_street_view` — o item é um botão com `hx-get` para
  `street_view:abrir`, o `lon` e o `lat` do ponto no `hx-vals` e alvo `#gaveta-inferior-conteudo`, dentro
  de uma lista com `data-troca-cena`.
- `test_gaveta_do_endereco_anonimo_nao_traz_o_item` — o mesmo resultado, sem login, não traz o botão.
- `test_gaveta_do_endereco_externo_traz_o_item_do_street_view` — idem na gaveta do endereço externo.
