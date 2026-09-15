---
spec: localizacao_lote/001
versao: v1
atualizado_em: 2026-09-15
testes_tdd: false
implementado: false
markers_obrigatorios: []
changelog:
  - v1: versão inicial
---

# SPEC localizacao_lote/001 — Dados do lote na gaveta lateral

## 1 · User story
Quem usa a busca abre a gaveta lateral do lote resolvido no contexto da home para ler os dados
cadastrais dele sem tirar o mapa da tela.

## 2 · Condições de pronto
- [ ] Resolver um lote — clique numa sugestão de contribuinte, de endereço cadastrado ou Enter na
      barra — desenha o polígono **e abre a gaveta lateral** com os dados daquele lote, sem login.
- [ ] A gaveta mostra: **SQL** (`SSS.QQQ.LLLL-D`), endereço cadastrado (logradouro, número,
      complemento, codlog-DV), setor/quadra/lote, tipo de quadra e de lote, condomínio, uso, área de
      terreno, área construída, CIB e a **situação do lançamento**.
- [ ] Atributo que a base não traz sai como **"não informado"**, nunca como campo em branco nem
      `None`.
- [ ] Lote sem dígito do SQL (lote municipal, lote-mãe de condomínio) mostra o setor/quadra/lote e
      diz que **não há contribuinte** — nunca inventa um SQL.
- [ ] A situação do lançamento diz **"Lançamento ativo"** só para lote com SQL e situação `ATIVO`
      no cadastro; qualquer outro caso diz "Sem lançamento ativo".
- [ ] Com a home recém-aberta, a gaveta recolhida mostra a paleta, e aberta sem entidade mostra o
      **estado de falta escrito**.
- [ ] Nova busca que resolve **outro tipo** de resultado (logradouro, endereço) não deixa na gaveta
      os dados do lote anterior.
- [ ] Lote sem geometria cadastrada continua respondendo o aviso de hoje, e a gaveta não abre.
- [ ] O design da gaveta do lote foi aprovado no mock e as peças novas portadas para o tema e o
      styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
A entidade é o **lote fiscal** como a camada `lote_cidadao` do GeoSampa o descreve. A pergunta que
esta SPEC faz ao [LoteGeocoder](../geocodificacao/002-lote-geocod-poligono.md) é "o que mais essa
mesma feature já traz?": os atributos cadastrais chegam na **mesma** requisição que traz o polígono,
e nada é consultado a mais. A casca da gaveta é a da SPEC [design/013](../design/013-gaveta-lateral-e-paleta.md).

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
- Ações sobre o lote na gaveta — SPEC [certidao_lancamento/001](../certidao_lancamento/001-certidao-de-um-lote.md).

## 5 · Peças de referência a compor
- `@services/domain/lote_geocod` → `LoteGeocoder`: feature do lote por setor/quadra/lote.
- `@apps/lote_geocoder/views.py` → `geocodificar_lote`: ponto único que a sugestão e o Enter já usam.
- `@templates/mapping/_mapa.html` → payload do mapa singleton; segue agnóstico de domínio.
- `@static/src/tema-dimap.dev.css` → `.gaveta-lateral*`, `.paleta-gaveta`, `.card-well`, `.gaveta-vazia`.
- `@templates/core/design_system.html` → markup de referência da gaveta lateral.
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
TEMPLATE_RESULTADO_LOTE = "lote_geocoder/partials/_resultado_lote.html"


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
        TEMPLATE_RESULTADO_LOTE,
        contexto_mapa(geojson, MAP_COR_POLIGONO) | {"lote": features[0].attributes},
    )
```

**`templates/lote_geocoder/partials/_resultado_lote.html`** — organismo: mapa + gaveta fora de banda.

```html
{% include "mapping/_mapa.html" %}
{# O conteúdo da gaveta chega por OOB; o toggle vem marcado porque abrir é estado do servidor. #}
<div id="gaveta-entidade" hx-swap-oob="innerHTML">
  {% include "lote_geocoder/partials/_gaveta_lote.html" with lote=lote %}
</div>
```

**`templates/lote_geocoder/partials/_gaveta_lote.html`** — o "não informado" mora no template, uma vez.

```html
<p class="text-code text-sm">{% if lote.sql %}SQL {{ lote.sql }}{% else %}Sem contribuinte{% endif %}</p>
<p class="text-overline">Área de terreno</p>
<p>{% if lote.area_terreno_m2 is not None %}{{ lote.area_terreno_m2|floatformat:0 }} m²{% else %}não informado{% endif %}</p>
<p>{% if lote.possui_lancamento %}Lançamento ativo{% else %}Sem lançamento ativo{% endif %}</p>
```

**`apps/address_geocoder/views.py` e `apps/logradouro_geocoder/views.py`** — resultado de outro
tipo esvazia a gaveta.

```html
{# templates/mapping/_gaveta_vazia_oob.html — incluído pelos resultados que não são lote #}
<div id="gaveta-entidade" hx-swap-oob="innerHTML">
  {% include "core/partials/_gaveta_sem_entidade.html" %}
</div>
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

## 8 · Testes (TDD)
- `test_feature_para_lote_le_atributos_cadastrais` — digito, complemento, situação, uso, áreas e
  CIB saem das properties da feature para o `LoteAttributes`.
- `test_sql_so_existe_com_digito` — sem `cd_digito_sql`, `sql` é `None`; com ele, `SSS.QQQ.LLLL-D`.
- `test_possui_lancamento_exige_sql_e_situacao_ativa` — ativo sem dígito, e com dígito sem situação,
  não possuem lançamento.
- `test_geocodificar_lote_abre_gaveta_com_sql` — POST em `lote_geocoder:geocodificar` com fetcher
  fake devolve o payload do mapa e o fragmento OOB `#gaveta-entidade` com o SQL e o toggle marcado.
- `test_gaveta_mostra_nao_informado_para_atributo_ausente` — área nula renderiza "não informado".
- `test_lote_sem_contribuinte_nao_inventa_sql` — lote municipal renderiza "Sem contribuinte".
- `test_resultado_de_endereco_esvazia_gaveta` — o partial do ponto traz o OOB com o estado de falta.
- `test_lote_sem_geometria_nao_abre_gaveta` — sem feature, a resposta é o aviso, sem `#gaveta-entidade`.
- `test_home_sem_login_traz_gaveta_recolhida` — GET na home anônima traz a casca com o estado de falta.
