---
spec: localizacao_lote/004
versao: v1
atualizado_em: 2026-09-15
testes_tdd: false
implementado: false
markers_obrigatorios: []
changelog:
  - v1: versão inicial
---

# SPEC localizacao_lote/004 — Revisão do conjunto de lotes do desenho

## 1 · User story
Quem desenhou um terreno revisa, na tabela da gaveta inferior, os lotes que o desenho cruzou,
destacando cada um no mapa e tirando os que entraram por engano, no contexto de um traço que pegou
vizinhos por uma lasca, para chegar ao conjunto que de fato compõe o terreno.

## 2 · Condições de pronto
- [ ] Selecionar uma linha da tabela **destaca o polígono daquele lote** no mapa e apaga o destaque
      do anterior; só um lote fica destacado por vez.
- [ ] Cada linha tem uma **lixeira**; acioná-la tira o lote da tabela **e** do mapa, sem reenquadrar
      o mapa.
- [ ] A gaveta lateral do desenho passa a contar **só os lotes que restaram**.
- [ ] Tirar lotes em sequência acumula: um lote tirado não volta ao tirar o próximo.
- [ ] Tirar o último lote mostra o estado de falta escrito na tabela.
- [ ] Um identificador de lote que não está no desenho, mandado como removido, **não muda** o
      conjunto — e nenhum lote de fora do desenho entra por ele.
- [ ] O design da tabela simplificada, do destaque e da lixeira foi aprovado no mock e as peças novas
      portadas para o tema e o styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
O conjunto é o [LotesDoDesenho](003-lotes-do-desenho.md#3--domínio) com uma escolha humana por cima.
Os lotes do conjunto **não são guardados**: são a consulta ao desenho menos os que a pessoa tirou, e
é essa derivação que a SPEC [certidao_lancamento/002](../certidao_lancamento/002-certidao-do-conjunto.md)
refaz no servidor na hora de emitir.

**`services/domain/lote_espacial/models.py`** — `ConjuntoDeLotes` novo e `LotesDoDesenho` inteiro.

```python
class ConjuntoDeLotes(BaseModel):
    """O que a pessoa decidiu: o desenho e os lotes que ela tirou. Remover é o único gesto — nada se acrescenta."""

    model_config = ConfigDict(frozen=True)

    desenho: Desenho
    removidos: frozenset[str] = frozenset()   # id_poligono dos lotes tirados


class LotesDoDesenho(BaseModel):
    # ALTERADO nesta SPEC: carrega o conjunto (desenho + removidos) em vez do desenho solto.
    conjunto: ConjuntoDeLotes
    area_m2: float = Field(gt=0)
    # Já descontados os removidos.
    lotes: tuple[LoteFeature, ...] = ()
```

**`services/domain/geometry/models.py`** — `GeoJsonProperties` inteiro.

```python
class GeoJsonProperties(BaseModel):
    popup_html: str | None = None
    rotulo: str | None = None
    cor: str | None = None
    # ALTERADO nesta SPEC: identificador da feature, para o mapa achar o polígono que a tabela destaca.
    id: str | None = None
```

**Mock:** [004-mock-revisao-do-conjunto.html](004-mock-revisao-do-conjunto.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Desfazer uma remoção — sem dono ainda; refazer a busca pelo botão do desenho recomeça o conjunto.
- Acrescentar lote que o desenho não cruza — sem dono ainda.
- Destacar a linha da tabela ao clicar no polígono do mapa (o caminho inverso) — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/lote_espacial/do_desenho.py` → `BuscarLotesDoDesenho` (SPEC 003).
- `@templates/lote_espacial/partials/_resultado_desenho.html` → o organismo de mapa + gavetas (SPEC 003).
- `@static/src/js/mapa/camada_resultado.js` → `adicionarResultado`: a camada que recebe o destaque.
- `@apps/mapping/context.py` → `contexto_mapa`.
- `@static/src/tema-dimap.dev.css` → `.table-onsen`, `.gaveta-inferior`, `.btn-glass`.
- Skills: `mock`, `componentes-frontend`, `leaflet-map`, `test-django-views`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/lote_espacial/conjunto.py`** — a derivação que a emissão da certidão repete.

```python
class RevisaoConjuntoInput(BaseModel):
    conjunto: ConjuntoDeLotes
    camada: CamadaLotes
    area_maxima_m2: float = Field(gt=0)


class RevisarConjunto:
    def __init__(self, buscar: Callable[[LotesDoDesenhoInput], LotesDoDesenho]) -> None:
        self._buscar = buscar

    def __call__(self, entrada: RevisaoConjuntoInput) -> LotesDoDesenho:
        return self.pipeline(entrada)

    def pipeline(self, entrada: RevisaoConjuntoInput) -> LotesDoDesenho:
        apurado = self._buscar(LotesDoDesenhoInput(
            desenho=entrada.conjunto.desenho,
            camada=entrada.camada,
            area_maxima_m2=entrada.area_maxima_m2,
        ))
        # Filtrar DEPOIS da consulta: o que o cliente manda só consegue tirar, nunca pôr. Um id
        # forjado que não está no desenho simplesmente não casa com nada.
        restantes = tuple(
            lote for lote in apurado.lotes
            if lote.attributes.id_poligono not in entrada.conjunto.removidos
        )
        return LotesDoDesenho(
            conjunto=entrada.conjunto,
            area_m2=apurado.area_m2,
            lotes=restantes,
        )
```

**`services/domain/lote_espacial/do_desenho.py`** — a busca da SPEC 003 passa a devolver o conjunto
sem removidos.

```python
        return LotesDoDesenho(
            conjunto=ConjuntoDeLotes(desenho=entrada.desenho),
            area_m2=area,
            lotes=lotes,
        )
```

**`apps/mapping/context.py`** e **`static/src/js/mapa/camada_resultado.js`** — o reenquadramento vira
opção do payload.

```python
def contexto_mapa(geometria: dict[str, Any], cor: str, enquadrar: bool = True) -> dict[str, Any]:
    return {"payload": {"geometria": geometria, "cor": cor, "enquadrar": enquadrar}}
```

```javascript
export function adicionarResultado(map, geometria, corPadrao, enquadrar = true) {
  const camada = L.geoJSON(geometria, { /* estilo, pointToLayer, onEachFeature como hoje */ }).addTo(map);
  if (enquadrar) enquadrarCamada(map, camada);
  return camada;
}
```

**`apps/lote_espacial/views.py`**

```python
@require_POST
def remover_do_conjunto(request: HttpRequest) -> HttpResponse:
    removidos = frozenset(request.POST.getlist("removidos"))
    remover = request.POST.get("remover", "")
    conjunto = ConjuntoDeLotes(
        desenho=_desenho(request.POST),
        removidos=removidos | {remover},
    )
    revisar = RevisarConjunto(BuscarLotesDoDesenho(build_fetcher(settings)))
    resultado = revisar(RevisaoConjuntoInput(
        conjunto=conjunto,
        camada=camada_lotes(),
        area_maxima_m2=LOTES_DESENHO_AREA_MAXIMA_M2,
    ))
    # enquadrar=False: tirar um lote não pode fazer o mapa pular para longe de onde a pessoa está olhando.
    return render(request, TEMPLATE_RESULTADO_DESENHO, contexto_lotes_do_desenho(resultado, enquadrar=False))
```

**`templates/lote_espacial/partials/_tabela_lotes.html`** — o conjunto viaja no formulário.

```html
<form id="conjunto-lotes" hx-post="{% url 'lote_espacial:remover_do_conjunto' %}" hx-target="#resultado-busca">
  <input type="hidden" name="desenho" value="{{ desenho_json }}">
  {% for id in conjunto.removidos %}<input type="hidden" name="removidos" value="{{ id }}">{% endfor %}
  <table class="table-onsen">
    {% for lote in lotes %}
      <tr>
        <td><input type="radio" name="lote_destacado" value="{{ lote.attributes.id_poligono }}"
                   hx-get="{% url 'lote_espacial:detalhe_do_lote' %}?id={{ lote.attributes.id_poligono }}"
                   hx-target="#gaveta-detalhe" hx-trigger="change"></td>
        <td class="text-code">{{ lote.attributes.sql|default:"sem contribuinte" }}</td>
        <td>{{ lote.attributes.endereco }}</td>
        <td><button type="submit" name="remover" value="{{ lote.attributes.id_poligono }}" aria-label="Tirar do conjunto">…</button></td>
      </tr>
    {% endfor %}
  </table>
</form>
```

**`static/src/js/mapa/destaque.js`** — utilitário de Leaflet: o estado de "qual está destacado" é o
radio marcado no DOM, não uma variável.

```javascript
export function destacarLote(camada, id, estilos) {
  camada.eachLayer((layer) => {
    const destacado = layer.feature.properties.id === id;
    layer.setStyle(destacado ? estilos.destaque : estilos.base);
    if (destacado) layer.bringToFront();
  });
}

// htmx:afterSwap e change do radio chamam destacarLote com o value do radio marcado.
```

## 7 · Caveats
Cada lixeira refaz a consulta `INTERSECTS` no WFS em vez de filtrar uma lista guardada. É o que
mantém o servidor sem estado e impede que o cliente acrescente lote ao conjunto. O custo é uma ida
ao GeoServer por clique, e o conjunto pode mudar entre dois cliques se a camada mudar nesse meio.

O destaque do polígono é JavaScript de estado visual (`setStyle`), acionado pelo radio da tabela.
Ele é utilitário de Leaflet, e o que está selecionado continua lido do DOM. O custo é o único ponto
desta SPEC que o teste automatizado não alcança: quem o aprova é o mock.

`GeoJsonProperties` ganha `id`, que todo resultado do mapa passa a poder carregar. O destaque
precisa achar a feature pelo identificador de domínio, e o Leaflet não tem outro elo com a linha da
tabela. O custo é um campo a mais no contrato do mapa, que só os lotes do desenho preenchem por
enquanto.

## 8 · Testes (TDD)
- `test_conjunto_deriva_lotes_do_desenho_menos_removidos` — de três lotes apurados, com um removido,
  saem dois, na ordem da consulta.
- `test_removido_de_fora_do_desenho_nao_muda_o_conjunto` — id que a consulta não devolveu deixa os
  lotes iguais aos da consulta.
- `test_remover_devolve_tabela_sem_o_lote_e_mapa_sem_enquadrar` — a resposta não tem a linha do lote
  removido, o payload não tem a feature dele e traz `enquadrar: false`.
- `test_removidos_acumulam_no_formulario` — com um removido anterior e um novo, a resposta traz os
  dois como `removidos` ocultos.
- `test_resumo_do_desenho_conta_so_os_restantes` — o OOB da gaveta lateral cita a quantidade restante.
- `test_remover_ultimo_lote_mostra_estado_de_falta` — tabela vazia renderiza o estado de falta.
- `test_payload_do_desenho_carrega_id_do_poligono` — cada feature do payload tem `properties.id`.
