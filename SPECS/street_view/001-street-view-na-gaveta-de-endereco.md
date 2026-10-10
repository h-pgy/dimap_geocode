---
spec: street_view/001
versao: v3
atualizado_em: 2026-10-10
testes_tdd: true
implementado: true
changelog:
  - v1: versão inicial
  - v2: alinhada ao mock aprovado — o controle é o item "Visão da rua" do poço de ações, que passa a abrigar também o lote mais próximo
  - v3: a SPEC street_view/002 troca a janela à parte pelo panorama na gaveta inferior; saem o link, o redirect, o aviso de pop-up e o janela_popup.js
---

# SPEC street_view/001 — Street View em janela à parte, a partir da gaveta de endereço

## 1 · User story
O servidor logado na plataforma abre o Street View do Google numa janela à parte, no contexto de um
endereço localizado pela busca, para ver a rua e a fachada sem perder o mapa e a gaveta.

## 2 · Condições de pronto
- [ ] Logado, a **gaveta do endereço** traz, no **poço de ações**, o item **"Visão da rua"**.
- [ ] Logado, a **gaveta do endereço externo** traz o mesmo item.
- [ ] Nas duas gavetas, o **lote mais próximo** é item do mesmo poço, no lugar do botão largo.
- [ ] Sem login, a gaveta do endereço **não traz** o controle.
- [ ] Acionar o controle abre, numa **janela separada do navegador**, o Google Maps no panorama mais
      próximo do **ponto do endereço**; o mapa e a gaveta da plataforma ficam como estavam.
- [ ] Se o navegador **bloquear a janela**, a plataforma mostra o aviso padrão, em tom de erro, dizendo
      para liberar os pop-ups; a gaveta **recolhe** para o aviso aparecer, e a alça a reabre.
- [ ] A rota do panorama **exige login**: sem ele, leva ao login e não devolve endereço do Google.
- [ ] Coordenada ausente ou malformada é **recusada**, sem redirecionar a lugar nenhum.
- [ ] Sem JavaScript, o controle abre o mesmo destino em **nova aba**.
- [ ] O design do controle nas duas gavetas foi aprovado no mock e as peças novas portadas para o tema
      e o styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
O ponto é o [PointGeometry](../geocodificacao/003-address-geocod-ponto.md) que as duas entidades de
endereço carregam — o endereço interpolado
([EnderecoAttributes](../localizacao_lote/002-lote-mais-proximo-do-endereco.md#3--domínio)) e o
[EnderecoExternoFeature](../geocodificacao_externa/002-geocodificador-externo-agnostico.md#3--domínio).
A pergunta que esta SPEC faz a eles é uma só: "onde você está?".

Nasce o submódulo `street_view`, que responde "qual o endereço do panorama mais próximo deste ponto?".
Ele não consulta nada: monta o link documentado do Google Maps (Maps URLs), que dispensa chave.

**Mock:** [001-mock-street-view-na-gaveta-de-endereco.html](001-mock-street-view-na-gaveta-de-endereco.html)
— leia a skill `mock`.

## 4 · Fora de escopo
- Street View a partir do lote, pelo ponto da testada na rua em que ele está lançado — sem dono ainda.
- Street View a partir das demais entidades — sem dono ainda.
- Câmera virada para o imóvel no endereço interpolado, pelo lado da via que a paridade indica — sem
  dono ainda.
- Panorama embutido na própria plataforma — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/geometry` → `reprojetar`, `PointGeometry`: o ponto e a troca de CRS.
- `@apps/lotes_mais_proximos/views.py` → `ConsultaLoteMaisProximoDoPonto`: molde do DTO `lon`/`lat` que chega da gaveta.
- `@apps/geocodificacao_externa/views.py` → `selecionar`: molde de rota que exige só login.
- `@apps/core/middleware.py` → `PydanticValidationMiddleware`: a recusa (422) da coordenada malformada.
- `@apps/mapping/context.py` → `contexto_aviso`; `@templates/mapping/_aviso.html`: o aviso padrão, com `tom="error"`.
- `@templates/mapping/_recolher_gaveta_oob.html` → o toggle desmarcado por OOB, que tira a gaveta da frente do aviso.
- `@templates/address_geocoder/partials/_gaveta_endereco.html` → `ponto.coordinates.N|unlocalize`: como a gaveta escreve a coordenada.
- `@tests/apps/geocodificacao_externa/test_views.py` → o request logado sem banco.
- Skills: `mock`, `componentes-frontend`, `htmx`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/street_view/models.py`**

```python
class LinkStreetViewInput(BaseModel):
    ponto: PointGeometry
    crs_ponto: int
    crs_street_view: int  # o CRS em que o Google lê o viewpoint


class LinkStreetView(BaseModel):
    url: str
```

**`services/domain/street_view/link.py`**

```python
URL_BASE = "https://www.google.com/maps/@"
CASAS_DECIMAIS = 6  # ~10 cm: mais que isso é ruído na URL


class MontarLinkStreetView:
    def __call__(self, entrada: LinkStreetViewInput) -> LinkStreetView:
        return self.pipeline(entrada)

    def pipeline(self, entrada: LinkStreetViewInput) -> LinkStreetView:
        ponto = reprojetar(entrada.ponto, entrada.crs_ponto, entrada.crs_street_view)
        return LinkStreetView(url=self._montar_url(ponto))

    def _montar_url(self, ponto: PointGeometry) -> str:
        # GeoJSON guarda (lon, lat); o Google lê o viewpoint como "lat,lon" — é a inversão que quebra
        lon, lat = ponto.coordinates
        lat_arredondada = round(lat, CASAS_DECIMAIS)
        lon_arredondada = round(lon, CASAS_DECIMAIS)
        # sem `heading`: o Google vira a câmera do panorama para o viewpoint
        parametros = {
            "api": "1",            # obrigatório: sem ele o Google ignora os demais parâmetros
            "map_action": "pano",
            "viewpoint": f"{lat_arredondada},{lon_arredondada}",
        }
        # urlencode escreve a vírgula como %2C, como a documentação do Maps URLs pede
        return f"{URL_BASE}?{urlencode(parametros)}"
```

**`config/settings.py`**

```python
STREET_VIEW_CRS = 4326
```

**`apps/street_view/urls.py`** — app novo, montado em `street-view/`.

```python
app_name = "street_view"

urlpatterns = [
    path("abrir/", views.abrir, name="abrir"),
    path("popup-bloqueado/", views.popup_bloqueado, name="popup_bloqueado"),
]
```

**`apps/street_view/views.py`**

```python
MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
STREET_VIEW_CRS: int = settings.STREET_VIEW_CRS

TEMPLATE_AVISO_POPUP_BLOQUEADO = "street_view/partials/_aviso_popup_bloqueado.html"

MSG_POPUP_BLOQUEADO = (
    "O navegador bloqueou a janela da Visão da rua. "
    "Libere os pop-ups para este site e tente de novo."
)


class ConsultaStreetView(BaseModel):
    lon: float
    lat: float


class AvisoPopupBloqueado(BaseModel):
    # o id do toggle da gaveta de onde o clique saiu; a forma barra qualquer coisa que não seja id
    toggle: str = Field(pattern=r"^[a-z][a-z0-9-]*$")


@login_required  # basta estar autenticado: sem contrato de ação
@require_GET
def abrir(request: HttpRequest) -> HttpResponse:
    # lon/lat ausentes ou malformados morrem no PydanticValidationMiddleware, antes do redirect
    consulta = ConsultaStreetView.model_validate(request.GET.dict())
    entrada = LinkStreetViewInput(
        ponto=PointGeometry(type="Point", coordinates=[consulta.lon, consulta.lat]),
        crs_ponto=MAP_OUTPUT_CRS,
        crs_street_view=STREET_VIEW_CRS,
    )
    montar_link = MontarLinkStreetView()
    link = montar_link(entrada)
    # o destino é sempre URL_BASE + números: a rota não redireciona para onde o cliente mandar
    return redirect(link.url)


@login_required
@require_GET
def popup_bloqueado(request: HttpRequest) -> HttpResponse:
    # a mensagem mora no servidor: o script só pede o partial, não monta aviso nenhum
    aviso = AvisoPopupBloqueado.model_validate(request.GET.dict())
    contexto = contexto_aviso(MSG_POPUP_BLOQUEADO, tom="error") | {"toggle": aviso.toggle}
    return render(request, TEMPLATE_AVISO_POPUP_BLOQUEADO, contexto)
```

**`templates/street_view/partials/_aviso_popup_bloqueado.html`** — com a gaveta aberta a busca sai de
cena e levaria o aviso junto; por isso o mesmo response recolhe a gaveta.

```html
{% include "mapping/_aviso.html" %}
{% include "mapping/_recolher_gaveta_oob.html" with toggle=toggle %}
```

**`templates/street_view/partials/_item_street_view.html`** — o item do poço; as classes saem do mock.

```html
{% load l10n %}
{% if request.user.is_authenticated %}
  <a
    href="{% url 'street_view:abrir' %}?lon={{ ponto.coordinates.0|unlocalize }}&lat={{ ponto.coordinates.1|unlocalize }}"
    target="_blank"
    rel="noopener noreferrer"
    data-janela-popup
    data-aviso-bloqueio="{% url 'street_view:popup_bloqueado' %}?toggle={{ toggle }}"
  >Visão da rua</a>
{% endif %}
```

**`templates/address_geocoder/partials/_gaveta_endereco.html`** e
**`templates/geocodificacao_externa/partials/_gaveta_endereco_externo.html`** — cada gaveta já tem
`ponto` no contexto e diz o id do próprio toggle. O formulário do lote mais próximo vira a lista do
poço, e o item do Street View entra nela.

```html
<div class="card-well poco-acoes">
  <p class="text-overline poco-acoes__titulo">Ações</p>
  <form class="poco-acoes__lista" hx-post="…" hx-target="#resultado-busca" hx-swap="innerHTML">
    <!-- campos ocultos e o botão "Lote mais próximo", como já eram -->
    {% include "street_view/partials/_item_street_view.html" with toggle="gaveta-endereco-toggle" %}
  </form>
</div>
```

**`static/src/js/ui/janela_popup.js`** — carregado pela `core/home.html`.

```javascript
const FEICOES = "popup,width=1100,height=720";
const ALVO_AVISO = "#resultado-busca";

function abrirJanela(link) {
  // Sem `noopener` nas feições: com ele o window.open devolve sempre null, e o bloqueio
  // ficaria indistinguível de uma janela aberta.
  const janela = window.open(link.href, "_blank", FEICOES);
  if (janela === null) {
    // Bloqueado: o aviso é um partial do servidor, como qualquer outro aviso da busca.
    htmx.ajax("GET", link.dataset.avisoBloqueio, { target: ALVO_AVISO, swap: "innerHTML" });
    return;
  }
  // A página do Google não precisa — nem deve — alcançar a janela da plataforma.
  janela.opener = null;
}

// Delegado no body: a gaveta chega por swap do HTMX, depois da carga da página.
document.body.addEventListener("click", (evento) => {
  const link = evento.target.closest("a[data-janela-popup]");
  if (link === null) return;
  // Sem este script o link segue valendo: target="_blank" abre o mesmo destino em nova aba.
  evento.preventDefault();
  abrirJanela(link);
});
```

## 7 · Caveats
O panorama abre no site do Google, por link do Maps URLs, e não embutido pela Maps JavaScript API. Os
termos do Google Maps Platform vedam exibir Street View e mapa não-Google na mesma tela (3.2.3(e)), e o
link dispensa chave, cota e billing. O custo é não controlar a interface nem saber se há panorama perto
do ponto: sem cobertura, o Google mostra o que tiver, e a plataforma não avisa.

O link não leva `heading`. Sem ele o Google vira a câmera do panorama para o `viewpoint`, o que já
aponta para o imóvel quando o ponto está sobre ele. O custo é o endereço interpolado, cujo ponto fica
no eixo da via: ali a câmera abre na direção que o Google escolher, que pode não ser a do imóvel.

A rota exige só login (`@login_required`), sem contrato de ação, perfil nem registro de execução, como
a geocodificação externa. Não há competência a conceder: qualquer servidor autenticado pode abrir, e o
destino é conteúdo público do Google (§3.5). O custo é não haver rastro de quem abriu o quê, e promover
isso a ação concedida por cargo × unidade pedir contrato, ícones e card no painel.

A rota `abrir` responde um redirecionamento, não um partial HTML (§3.1). O destino é uma página do
Google numa janela própria, e não há estado da aplicação a devolver. O custo é uma rota fora da regra
de que toda rota devolve partial.

O `janela_popup.js` é um quarto caso de JavaScript, fora dos três do §7.2, aprovado pelo usuário.
Janela com tamanho próprio e detecção de bloqueio só existem por `window.open`; o HTML sozinho abre
aba. O custo é um script que não é callback do HTMX, utilitário do Leaflet nem estado visual de
controle.

A janela abre sem `noopener`, e o script zera `opener` logo em seguida. É o retorno do `window.open`
que denuncia o bloqueio, e `noopener` o torna sempre nulo. O custo é que bloqueador que devolve uma
janela falsa passa sem aviso.

O id do toggle a recolher chega pela URL do aviso, escrito pelo template de cada gaveta. Assim o
`street_view` não conhece id de gaveta nenhuma. O custo é uma rota que desmarca o toggle que o cliente
nomear, limitada só pela forma do id.

As gavetas de `address_geocoder` e `geocodificacao_externa` incluem um partial de `street_view`. A
inclusão fica no template, como o formulário do lote mais próximo, e as views da busca não importam
nada do app novo (§3.5). O custo é que remover o app `street_view` quebra as duas gavetas.

O ponto chega pela query string, sem recálculo no servidor, como no lote mais próximo. Recalcular o
endereço externo custaria uma segunda chamada paga ao provedor. O custo é que quem está logado abre o
Street View em qualquer coordenada, o que o Google já oferece a qualquer pessoa.

## 8 · Testes (TDD)
A janela em si — tamanho, bloqueio pelo navegador, e o mapa da plataforma intacto ao lado — é conferida
pelo usuário no navegador; os testes fixam o destino, o aviso e quem os recebe.

**Domínio** — `tests/services/domain/street_view/test_link.py`
- `test_link_escreve_latitude_antes_da_longitude` — ponto `[-46.6559, -23.5614]` em 4326 vira
  `viewpoint=-23.5614%2C-46.6559`, com `api=1` e `map_action=pano`, sobre a URL do Google Maps.
- `test_link_reprojeta_ponto_de_crs_metrico` — o mesmo lugar dado em 31983 gera um `viewpoint` em
  graus, a menos de um metro do esperado.

**Rotas** — `tests/apps/street_view/test_views.py`
- `test_abrir_logado_redireciona_ao_panorama_do_ponto` — GET com `lon` e `lat` responde 302 cujo
  destino é o link do Google com o `viewpoint` do ponto.
- `test_abrir_anonimo_vai_para_o_login` — GET sem login responde 302 para o login, sem o Google no
  destino.
- `test_abrir_com_coordenada_malformada_e_recusado` — parametrizado: `lon=abc` e `lat` ausente
  respondem 422, sem cabeçalho de redirecionamento.
- `test_popup_bloqueado_responde_aviso_de_erro_e_recolhe_a_gaveta` — GET com
  `toggle=gaveta-endereco-toggle` devolve o aviso em `alert-error` com a mensagem de liberar pop-ups e
  o OOB desse toggle desmarcado.

**Gavetas** — nos `test_views.py` de `address_geocoder` e `geocodificacao_externa`
- `test_gaveta_do_endereco_logado_traz_o_controle_do_street_view` — o OOB da gaveta traz o link para
  `street_view:abrir` com o `lon` e o `lat` do ponto, `target="_blank"`, `data-janela-popup` e a URL do
  aviso de bloqueio com `toggle=gaveta-endereco-toggle`.
- `test_gaveta_do_endereco_anonimo_nao_traz_o_controle` — o mesmo resultado, sem login, não traz o
  link.
- `test_gaveta_do_endereco_externo_traz_o_controle_do_street_view` — idem na gaveta do endereço
  externo, com `toggle=gaveta-endereco-externo-toggle`.
