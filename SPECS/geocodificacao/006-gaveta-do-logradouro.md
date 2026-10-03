---
spec: geocodificacao/006
versao: v3
atualizado_em: 2026-10-02
testes_tdd: true
implementado: true
changelog:
  - v1: versão inicial
  - v2: testes TDD escritos e SPEC implementada.
  - v3: o nome completo nas sugestões é renumerado para geocodificacao/007
---

# SPEC geocodificacao/006 — Gaveta do logradouro

## 1 · User story
Quem localiza um logradouro no mapa, pela busca ou pelo logradouro mais próximo de um ponto desenhado,
abre a gaveta dele, no contexto de uma linha que sozinha só diz o nome, para ver a identidade, a
extensão e a faixa de numeração do logradouro inteiro.

## 2 · Condições de pronto
- [ ] A busca por logradouro, por nome ou por codlog, desenha a linha como hoje e abre a **gaveta do
      logradouro**, em vez de esvaziar a gaveta lateral.
- [ ] O "Logradouro mais próximo" ([SPEC 005](005-logradouro-mais-proximo-do-ponto.md)) abre a mesma
      gaveta, que toma o lugar da gaveta dos desenhos; clicar num desenho volta à bancada.
- [ ] A gaveta mostra o nome completo no cabeçalho, a denominação (o nome com título e preposição,
      sem o tipo), o codlog e o tipo, a **extensão em km** e a quantidade de segmentos, e o **menor e
      o maior número do logradouro inteiro**, somados os dois lados de todos os segmentos. Logradouro
      sem numeração diz isso por escrito.
- [ ] O nome completo do logradouro é **tipo, título, preposição e nome** — `R DA CONSOLACAO`,
      `AV BRIG LUIS ANTONIO`, `AV PAULISTA` — e sai igual na gaveta do logradouro, no pop-up e no
      rótulo do segmento, e na gaveta, no pop-up e no rótulo do endereço.
- [ ] Abrir a gaveta não consulta o WFS de novo: ela sai dos segmentos que a resposta já trouxe.
- [ ] O design da gaveta foi aprovado no mock e a gaveta está no styleguide.

## 3 · Domínio
O logradouro é o da [geocodificação por codlog](001-logradouro-geocod-linha.md): os
`SegmentoLogradouroFeature` de um codlog. Esta SPEC dá nome à entidade que os segmentos repetem, faz
dela o único lugar do nome do logradouro e apura o que só existe no conjunto dos segmentos. A pergunta
que ela faz ao endereço da [geocodificação por interpolação](003-address-geocod-ponto.md) é "de que
logradouro você é?".

**`services/domain/logradouro/models.py`** — NOVO: a entidade, fora dos matchers e dos geocoders.

```python
class Logradouro(BaseModel):
    """O logradouro como entidade: a identidade que todos os seus segmentos repetem."""

    codlog: str                      # 6 dígitos, o último é o DV
    tipo_logradouro: str
    titulo: str | None = None
    preposicao: str | None = None
    nome_logradouro: str

    @computed_field
    @property
    def denominacao(self) -> str:
        # O nome sem o tipo: "BRIG LUIS ANTONIO", "DA CONSOLACAO". Sem título e preposição o nome fica incompleto.
        partes = [self.titulo, self.preposicao, self.nome_logradouro]
        return " ".join(p for p in partes if p)

    @computed_field
    @property
    def nome_completo(self) -> str:
        # A única regra do nome do logradouro no sistema: "AV BRIG LUIS ANTONIO", "R DA CONSOLACAO".
        # O catálogo de nomes tem logradouro sem tipo: sem ele, sai só a denominação.
        partes = [self.tipo_logradouro, self.denominacao]
        return " ".join(p for p in partes if p)
```

**`services/domain/logradouro_geocod/models.py`** — `SegmentoLogradouroAttributes` inteiro, com o que
muda marcado.

```python
class SegmentoLogradouroAttributes(BaseModel):
    """Atributos do segmento de logradouro (camada `attributes` da feature)."""

    id_segmento: str
    codlog: str
    tipo_logradouro: str
    nome_logradouro: str
    titulo: str | None = None
    preposicao: str | None = None
    numero_inicial_par: int | None = None
    numero_final_par: int | None = None
    numero_inicial_impar: int | None = None
    numero_final_impar: int | None = None

    # NOVO nesta SPEC: o único ponto que monta a entidade a partir do segmento.
    # `@property`, não `@computed_field`: a entidade não entra no dump do segmento.
    @property
    def logradouro(self) -> Logradouro:
        return Logradouro(
            codlog=self.codlog,
            tipo_logradouro=self.tipo_logradouro,
            titulo=self.titulo,
            preposicao=self.preposicao,
            nome_logradouro=self.nome_logradouro,
        )
```

**`services/domain/address_geocod/models.py`** — `EnderecoAttributes` inteiro, com o que muda marcado.

```python
class EnderecoAttributes(BaseModel):
    """Proveniência do ponto geocodificado (camada `attributes` da feature)."""

    # ALTERADO nesta SPEC: a entidade inteira no lugar de codlog, tipo, título e nome soltos.
    logradouro: Logradouro
    numero: int
    id_segmento: str            # segmento que originou a interpolação
    # faixa do lado (par/ímpar) do segmento escolhido, no dia da geocodificação
    numeracao_inicial: int
    numeracao_final: int
    # REMOVIDO nesta SPEC: `nome_completo`. O nome do endereço é `logradouro.nome_completo`.
```

**`services/domain/logradouro_geocod/gaveta.py`**

```python
class FaixaNumeracao(BaseModel):
    """O menor e o maior número do logradouro inteiro: os dois lados de todos os segmentos."""

    menor: int = Field(gt=0)
    maior: int = Field(gt=0)


class GavetaLogradouro(BaseModel):
    """O logradouro como a gaveta o apresenta: a identidade e o que se apura no conjunto dos segmentos."""

    logradouro: Logradouro
    extensao_m: float = Field(ge=0)          # soma dos eixos, medida no CRS métrico
    quantidade_segmentos: int = Field(ge=1)
    numeracao: FaixaNumeracao | None = None  # None: nenhum segmento numerado

    @computed_field
    @property
    def extensao_km(self) -> float:
        return self.extensao_m / 1000
```

**Mock:** [006-mock-gaveta-do-logradouro.html](006-mock-gaveta-do-logradouro.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Ações na gaveta do logradouro — sem dono ainda.
- Tipo do logradouro por extenso ("Avenida" em vez de "AV") — sem dono ainda.
- Extensão real das avenidas de pista dupla (§7) — sem dono ainda.
- Distância entre o ponto desenhado e o logradouro — sem dono ainda.
- Nome completo nas sugestões da busca, por nome e por codlog (§7) — [SPEC 008](008-nome-completo-nas-sugestoes.md).

## 5 · Peças de referência a compor
- `@services/domain/lote_geocod/gaveta.py` → `MontarGavetaLote`: molde da gaveta com medida apurada no CRS métrico.
- `@services/domain/geometry` → `reprojetar`, `para_geos`: o eixo no CRS métrico, para medir.
- `@apps/logradouro_geocoder/views.py` → `geocodificar_codlog`: a resposta do logradouro, que a busca e a SPEC 005 já usam.
- `@templates/address_geocoder/partials/_gaveta_endereco.html`: molde da nova, com o cartão de identidade e o codlog.
- `@static/src/tema-dimap.dev.css` → `.gaveta-lateral*`, `.paleta-gaveta`, `.card-well`, `.icon-bubble`, `.valor-ausente`: o organismo de gaveta lateral a compor.
- `@templates/core/design_system.html` → a gaveta lateral do lote no styleguide: o lugar onde a do logradouro entra.
- Skills: `ontologia`, `mock`, `componentes-frontend`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/logradouro_geocod/gaveta.py`** — a gaveta se monta dos segmentos que a resposta
do logradouro já tem.

```python
class GavetaLogradouroInput(BaseModel):
    segmentos: list[SegmentoLogradouroFeature] = Field(min_length=1)
    crs_metrico: int

    # A gaveta lê a identidade do primeiro segmento e soma todos: segmentos de dois logradouros
    # dariam o nome de um com a extensão e a numeração dos dois. Molde: o validador do GavetaDesenhos.
    @model_validator(mode="after")
    def _um_so_logradouro(self) -> Self:
        codlogs = {segmento.attributes.codlog for segmento in self.segmentos}
        if len(codlogs) > 1:
            raise ValueError("Os segmentos são de mais de um logradouro.")
        return self


class MontarGavetaLogradouro:
    def __call__(self, entrada: GavetaLogradouroInput) -> GavetaLogradouro:
        return self.pipeline(entrada)

    def pipeline(self, entrada: GavetaLogradouroInput) -> GavetaLogradouro:
        return GavetaLogradouro(
            logradouro=entrada.segmentos[0].attributes.logradouro,
            extensao_m=self._extensao_m(entrada),
            quantidade_segmentos=len(entrada.segmentos),
            numeracao=self._numeracao(entrada.segmentos),
        )

    def _extensao_m(self, entrada: GavetaLogradouroInput) -> float:
        extensao_m = 0.0
        for segmento in entrada.segmentos:
            # Cada segmento diz o próprio CRS; a medida é sempre no métrico.
            eixo = reprojetar(segmento.geometry, segmento.crs, entrada.crs_metrico)
            extensao_m += para_geos(eixo, entrada.crs_metrico).length
        return extensao_m

    def _numeracao(self, segmentos: list[SegmentoLogradouroFeature]) -> FaixaNumeracao | None:
        numeros: list[int] = []
        for segmento in segmentos:
            a = segmento.attributes
            extremos = [
                a.numero_inicial_par,
                a.numero_final_par,
                a.numero_inicial_impar,
                a.numero_final_impar,
            ]
            # Zero é como a camada marca o lado sem numeração: não é o número 0.
            numeros.extend(n for n in extremos if n)
        if not numeros:
            return None
        return FaixaNumeracao(menor=min(numeros), maior=max(numeros))
```

**`services/domain/address_geocod/geocoder.py`** — o endereço recebe a entidade do segmento escolhido.

```python
def _montar_feature(
    self,
    ponto: Point,
    escolhido: SegmentoLogradouroFeature,
    entrada: AddressGeocodInput,
    paridade: Paridade,
) -> EnderecoFeature:
    a = escolhido.attributes
    return EnderecoFeature(
        geometry=PointGeometry(type="Point", coordinates=[ponto.x, ponto.y]),
        attributes=EnderecoAttributes(
            logradouro=a.logradouro,   # ALTERADO: a entidade inteira, preposição inclusa
            numero=entrada.numero,
            id_segmento=a.id_segmento,
            numeracao_inicial=limite_inicial(a, paridade),
            numeracao_final=limite_final(a, paridade),
        ),
        crs=entrada.output_crs,
    )
```

**`apps/logradouro_geocoder/views.py`** — a resposta do logradouro passa a abrir a gaveta; a busca e a
SPEC 005 a recebem juntas, sem mudar nada nelas.

```python
def _properties(f: GeoFeature[Any, Any]) -> GeoJsonProperties:
    return GeoJsonProperties(
        popup_html=render_to_string(
            "logradouro_geocoder/partials/_popup_segmento.html", {"a": f.attributes}
        ),
        rotulo=f.attributes.logradouro.nome_completo,   # ALTERADO
        cor=None,
    )


def geocodificar_codlog(request: HttpRequest, codlog: str) -> HttpResponse:
    ...
    if not features:
        return render(...)   # o aviso de hoje, sem mudança
    montar_gaveta = MontarGavetaLogradouro()   # NOVO
    gaveta = montar_gaveta(
        GavetaLogradouroInput(
            segmentos=features,
            crs_metrico=MAP_INTERPOLATION_CRS,
        ),
    )
    geojson = to_geojson_feature_collection(features, _properties)
    contexto = contexto_mapa(geojson, MAP_COR_LINHA) | {"gaveta": gaveta}
    return render(request, TEMPLATE_RESULTADO_LOGRADOURO, contexto)
```

**`apps/address_geocoder/views.py`** — o rótulo do endereço lê o nome da entidade.

```python
rotulo=f"{a.logradouro.nome_completo}, {a.numero}",   # ALTERADO
```

**`templates/logradouro_geocoder/partials/_resultado_logradouro.html`** — organismo: mapa + gaveta fora
de banda, como o resultado do lote. O `mapping/_sem_gaveta_oob.html` perde o último consumidor e é
apagado.

```html
{% include "mapping/_mapa.html" %}
<div id="gaveta-entidade" hx-swap-oob="innerHTML">
  {% include "logradouro_geocoder/partials/_gaveta_logradouro.html" with gaveta=gaveta %}
</div>
```

**`templates/logradouro_geocoder/partials/_gaveta_logradouro.html`** — a raiz que o fade da troca lê,
tirada do objeto como no lote; o corpo é o do mock.

```html
<div class="gaveta-lateral" data-gaveta="logradouro-{{ gaveta.logradouro.codlog }}">
  <input type="checkbox" id="gaveta-logradouro-toggle" class="gaveta-lateral-toggle" checked>
  ...
  <p class="text-sm font-medium mt-2">{{ gaveta.logradouro.nome_completo }}</p>
```

**Templates que exibem o nome** — todos leem `nome_completo` da entidade; nenhum compõe tipo e nome.

```html
{# logradouro_geocoder/partials/_popup_segmento.html — o título solto sai: já está no nome #}
<span class="font-bold text-madeira-700">{{ a.logradouro.nome_completo }}</span><br>
<span class="text-code text-xs">codlog {{ a.codlog }}</span>

{# address_geocoder/partials/_popup_endereco.html #}
<span class="font-bold text-madeira-700">{{ a.logradouro.nome_completo }}, {{ a.numero }}</span><br>
<span class="text-code text-xs">codlog {{ a.logradouro.codlog }}</span>

{# address_geocoder/partials/_gaveta_endereco.html — cabeçalho, cartão de identidade e a origem da consulta #}
<p class="text-sm font-medium mt-2">{{ endereco.logradouro.nome_completo }}, {{ endereco.numero }}</p>
<p class="font-bold leading-tight">{{ endereco.logradouro.nome_logradouro }}</p>
<p class="text-code text-sm">{{ endereco.logradouro.codlog }}</p>
<input type="hidden" name="codlog" value="{{ endereco.logradouro.codlog }}">
<input type="hidden" name="origem" value="{{ endereco.logradouro.nome_completo }}, {{ endereco.numero }}">
```

## 7 · Caveats
A gaveta nasce na resposta da busca, e não na da ação da SPEC 005. É a gaveta da entidade, que vale para
quem chega a ela por qualquer caminho. O custo é a busca por logradouro mudar junto: ela deixa de
esvaziar a gaveta lateral e passa a abrir esta.

A extensão é a soma dos eixos da camada. A camada desenha um eixo por pista nas avenidas de pista
dupla, e não há atributo que diga qual eixo é o par de qual. O custo é a extensão dessas avenidas sair
quase em dobro: a Av. Paulista dá 5,4 km para cerca de 2,8 km reais.

A identidade do logradouro na gaveta é a do primeiro segmento. Segmentos do mesmo codlog repetem a
mesma identidade, e só uma inconsistência da camada faria um deles divergir no nome ou no tipo. O custo
é que, se isso ocorrer, a gaveta mostra o nome do primeiro segmento sem acusar a divergência.

Número zero na faixa de um segmento é tratado como lado sem numeração. É assim que a camada marca o
lado vazio. O custo é um imóvel de número 0, se existir, não contar para o menor número.

O `SegmentoLogradouroAttributes` mantém a identidade em campos soltos e entrega o `Logradouro` por um
atributo derivado. Recompor o segmento sobre a entidade mexeria na busca, na geocodificação de
endereço e nos catálogos. O custo é a identidade do logradouro existir em dois tipos, ligados por um
único ponto de montagem.

O `Logradouro` mora em `services/domain/logradouro/`, que a geocodificação de logradouro e a de
endereço passam a importar. Os matchers, que vão compô-lo na SPEC 008, não podem depender de um
geocoder. O custo é um submódulo a mais, só com a entidade.

As sugestões da busca seguem com regra própria de nome até a SPEC 008: o `CodlogMatchOutput.nome_completo`
e os templates de sugestão por nome juntam só tipo e nome. O catálogo `nomes_logradouros.parquet` não
traz título nem preposição, e trazê-los muda a extração e exige nova carga. O custo é a sugestão
`AV LUIS ANTONIO` abrir a gaveta `AV BRIG LUIS ANTONIO`.

## 8 · Testes (TDD)
- `test_nome_completo_do_logradouro_junta_titulo_e_preposicao` — `R` + preposição `DA` + `CONSOLACAO`
  dá `R DA CONSOLACAO`; `AV` + título `BRIG` + `LUIS ANTONIO` dá `AV BRIG LUIS ANTONIO`; sem título nem
  preposição, `AV PAULISTA`; sem tipo, só a denominação — nunca com espaço sobrando.
- `test_gaveta_logradouro_apura_extensao_e_numeracao_do_logradouro_inteiro` — dois segmentos de 30 m e
  40 m no CRS métrico, com faixas `2–10` (par), `0–0` (ímpar) e `1–25` (ímpar), dão extensão de 70 m e
  numeração `1–25`; segmentos sem numeração dão `numeracao` `None`.
- `test_geocodificar_abre_a_gaveta_do_logradouro` — POST anônimo com um codlog devolve o payload do
  mapa e, no OOB do `#gaveta-entidade`, a gaveta de `data-gaveta="logradouro-<codlog>"`, com o nome
  completo, o codlog, a extensão em km e a faixa de numeração, consultando o WFS uma vez só.
- `test_gaveta_do_endereco_mostra_o_nome_completo_do_logradouro` — endereço interpolado num segmento
  com título e preposição traz o nome completo no cabeçalho da gaveta e no pop-up.
- O `test_do_ponto_devolve_a_linha_do_logradouro_mais_proximo` da SPEC 005 passa a conferir essa gaveta
  no `#gaveta-entidade`, em vez de vazio.
