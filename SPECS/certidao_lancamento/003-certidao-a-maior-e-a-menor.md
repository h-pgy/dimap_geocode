---
spec: certidao_lancamento/003
versao: v4
atualizado_em: 2026-09-30
testes_tdd: false
implementado: false
markers_obrigatorios: [artefato]
changelog:
  - v1: versão inicial
  - v2: submódulo `lote_espacial` renomeado para `lotes_mais_proximos`
  - v3: a modalidade passa a ser derivada do conjunto guardado na sessão, e não da apuração
  - v4: a modalidade dá lugar à medida de cada lote, que alimenta a sugestão de tipo de despacho da SPEC 002 com um único limiar
---

# SPEC certidao_lancamento/003 — Participação de cada lote no desenho

## 1 · User story
O auditor fiscal com a concessão emite a certidão de um terreno desenhado sabendo quanto de cada lote
o desenho ocupa, no contexto de um terreno que ocupa lotes inteiros ou só parte deles, para obter a
declaração com a proporção de cada lote e o tipo de despacho sugerido a partir dessas medidas.

## 2 · Condições de pronto
- [ ] Cada lote do conjunto traz a **área do lote**, a **área de intersecção** com o desenho e o
      **percentual** que a intersecção representa da área do lote, medidos uma vez, na consulta, no
      CRS métrico.
- [ ] Um lote está **inteiro** no desenho quando a fração contida atinge o limiar configurado — o mesmo
      que a SPEC 002 usa —; abaixo dele, é **parcial**.
- [ ] A tabela da gaveta inferior mostra o percentual de cada lote, e o resumo dela conta quantos estão
      inteiros e quantos são parciais.
- [ ] Tirar um lote na tabela **recalcula o resumo** com os lotes que restaram, sem consultar o
      GeoServer.
- [ ] O modal do conjunto sugere o tipo de despacho a partir dessas medidas — **"em maior área"** com
      todos os lotes inteiros, **"parcial"** com algum parcial —, sem reprojetar geometria.
- [ ] A declaração do conjunto traz, para cada imóvel, área do lote, área contida e percentual,
      medidos na releitura da emissão.
- [ ] O design da coluna de percentual e do resumo na gaveta foi aprovado no mock e as peças novas
      portadas para o tema e o styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
A participação de um lote é a medida da intersecção entre ele e o [Desenho](../localizacao_lote/003-lotes-do-desenho.md#3--domínio),
apurada no CRS métrico da camada e guardada junto do lote. "Inteiro" e "parcial" são fatos da
geometria e moram no domínio da consulta; o que eles significam para um despacho é da certidão, que
os traduz em [TipoDespacho](001-certidao-de-um-lote.md#3--domínio) pela sugestão da
[SPEC 002](002-certidao-do-conjunto.md#3--domínio).

**`services/domain/lotes_mais_proximos/models.py`** — `LoteNoDesenho` novo, `LotesDoDesenho` e
`ConjuntoDeLotes` inteiros.

```python
class LoteNoDesenho(BaseModel):
    """Um lote e o quanto dele o desenho ocupa. Áreas medidas da geometria, no CRS métrico."""

    model_config = ConfigDict(frozen=True)

    lote: LoteFeature              # geometria já no CRS do mapa
    area_lote_m2: float = Field(gt=0)
    area_intersecao_m2: float = Field(ge=0)

    @computed_field
    @property
    def fracao_contida(self) -> float:
        return min(1.0, self.area_intersecao_m2 / self.area_lote_m2)

    def eh_inteiro(self, fracao_minima: float) -> bool:
        return self.fracao_contida >= fracao_minima


class LotesDoDesenho(BaseModel):
    """O que a consulta apurou: o desenho, a área dele e os lotes que ele cruza."""

    desenho: Desenho
    area_m2: float = Field(gt=0)
    # ALTERADO nesta SPEC: cada lote vem com a sua participação no desenho.
    lotes: tuple[LoteNoDesenho, ...] = ()


class ConjuntoDeLotes(BaseModel):
    """O que a consulta apurou e o que a pessoa tirou. Remover é o único gesto — nada se acrescenta."""

    model_config = ConfigDict(frozen=True)

    apurado: LotesDoDesenho
    removidos: frozenset[str] = frozenset()

    @property
    def lotes(self) -> tuple[LoteNoDesenho, ...]:   # ALTERADO nesta SPEC: a participação vem junto
        return tuple(
            item for item in self.apurado.lotes
            if item.lote.attributes.id_poligono not in self.removidos
        )
```

**`services/domain/certidao_lancamento/sugestao.py`** — `SugestaoDespachoInput` inteiro e o pipeline do
`SugerirTipoDespacho` (SPEC 002).

```python
class SugestaoDespachoInput(BaseModel):
    """Se cada lote que restou está inteiro no desenho. Quem mede é a consulta; aqui só se traduz."""

    model_config = ConfigDict(frozen=True)

    # ALTERADO nesta SPEC: a resposta da medida guardada, no lugar das geometrias a reprojetar no modal.
    lotes_inteiros: tuple[bool, ...] = Field(min_length=1)


class SugerirTipoDespacho:
    def pipeline(self, entrada: SugestaoDespachoInput) -> TipoDespacho:
        if all(entrada.lotes_inteiros):
            return TipoDespacho.LANCAMENTO_EM_MAIOR_AREA
        return TipoDespacho.LANCAMENTO_PARCIAL
```

**`services/domain/certidao_lancamento/models.py`** — `ConjuntoDesenhado` inteiro.

```python
class ConjuntoDesenhado(ObjetoCertidao):
    tipo: Literal["conjunto_desenhado"] = "conjunto_desenhado"
    # ALTERADO nesta SPEC: a participação de cada lote, não só o lote.
    participacoes: tuple[ParticipacaoCertificada, ...] = Field(min_length=1)
    area_desenho_m2: float = Field(gt=0)

    @property
    def imoveis(self) -> tuple[LoteAttributes, ...]:
        return tuple(p.imovel for p in self.participacoes)


class ParticipacaoCertificada(BaseModel):
    """O que a certidão imprime de cada lote. Guardado, não derivado: é o valor do dia da emissão."""

    model_config = ConfigDict(frozen=True)

    imovel: LoteAttributes
    area_lote_m2: float = Field(gt=0)
    area_intersecao_m2: float = Field(ge=0)
    fracao_contida: float = Field(ge=0, le=1)
```

**Mock:** [003-mock-certidao-a-maior-e-a-menor.html](003-mock-certidao-a-maior-e-a-menor.html) — leia a
skill `mock`.

## 4 · Fora de escopo
- Lote condominial dentro do conjunto — sem dono ainda.
- Percentual do **desenho** que cai em cada lote (intersecção sobre a área do desenho) — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/lotes_mais_proximos/do_desenho.py` → `BuscarLotesDoDesenho`, `ConferirDesenho` (SPEC localizacao_lote/003).
- `@services/domain/lotes_mais_proximos/conjunto.py` → `RemoverDoConjunto` (SPEC localizacao_lote/004), `RelerConjunto` (SPEC 002).
- `@services/domain/geometry` → `reprojetar` (SPEC localizacao_lote/002), `para_geos` (design/020).
- `@services/domain/certidao_lancamento/sugestao.py` → `SugerirTipoDespacho` (SPEC 002).
- `@services/domain/certidao_lancamento/certidao` → `MontarCertidaoLancamento` (SPECs 001 e 002).
- `@apps/certidao_lancamento/emissao.py` → `emitir_certidao_do_conjunto` (SPEC 002).
- Skills: `ontologia`, `documento-oficial`, `mock`, `escrever-testes`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/lotes_mais_proximos/do_desenho.py`** — a consulta passa a vir no CRS métrico;
mede e só então reprojeta.

```python
    def _consultar(self, projetado: PolygonGeometry, camada: CamadaLotes) -> tuple[LoteNoDesenho, ...]:
        request = WfsFeatureRequest(
            nome_camada=camada.nome,
            # ALTERADO: no CRS da camada, e não do mapa — área em grau não é área.
            srs_name=f"EPSG:{camada.crs_camada}",
            cql_filter=CqlFilter(predicates=[
                CqlIntersects(field=camada.campo_geometria, wkt=_wkt(projetado, camada.crs_camada)),
            ]),
            count=PAGE_SIZE,
        )
        desenho = para_geos(projetado, camada.crs_camada)
        return tuple(
            self._participacao(lote, desenho, camada)
            for page in self.fetcher(request)
            for feature in page.features
            if (lote := feature_para_lote(feature, camada.crs_camada)) is not None
        )

    def _participacao(self, lote: LoteFeature, desenho: GEOSGeometry, camada: CamadaLotes) -> LoteNoDesenho:
        poligono = para_geos(lote.geometry, camada.crs_camada)
        return LoteNoDesenho(
            lote=_reprojetar_lote(lote, camada.crs_saida),
            area_lote_m2=poligono.area,
            # Intersecção de GEOS e não o INTERSECTS do servidor: o servidor diz SE cruza, não QUANTO.
            area_intersecao_m2=poligono.intersection(desenho).area,
        )
```

Quem lia `lote.attributes` ou `lote.geometry` de um item do conjunto passa a ler `item.lote.…`: o
`RemoverDoConjunto` e o `RelerConjunto`, o `_properties_lote_do_desenho` e a `_tabela_conjunto.html`,
e, da SPEC 002, `conferir_confirmados`, `geometrias_metricas`, `sqls_do_conjunto` e os `confirmados`
do `_modal_conjunto.html`. O `_corpo_do_despacho` da SPEC 002, que lia `ConjuntoDesenhado(lotes=…)`,
passa a ler `objeto.imoveis`.

**`apps/certidao_lancamento/views.py`** — ALTERADO nesta SPEC: a sugestão lê a medida guardada na
sessão; o modal não reprojeta mais nada.

```python
def valores_iniciais_do_conjunto(conjunto: ConjuntoDeLotes) -> dict[str, Any]:
    sugerir_tipo = SugerirTipoDespacho()
    sugerido = sugerir_tipo(SugestaoDespachoInput(
        lotes_inteiros=tuple(item.eh_inteiro(LOTE_FRACAO_MINIMA_CONTIDA) for item in conjunto.lotes),
    ))
    return {**VALORES_INICIAIS, "tipo_despacho": sugerido}
```

**`apps/certidao_lancamento/emissao.py`** — o objeto da certidão sai do conjunto relido: as medidas do
dia da emissão.

```python
def conjunto_desenhado(lido: ConjuntoLido) -> ConjuntoDesenhado:
    conjunto = lido.conjunto
    return ConjuntoDesenhado(
        participacoes=tuple(
            ParticipacaoCertificada(
                imovel=item.lote.attributes,
                area_lote_m2=item.area_lote_m2,
                area_intersecao_m2=item.area_intersecao_m2,
                fracao_contida=item.fracao_contida,
            )
            for item in conjunto.lotes
        ),
        area_desenho_m2=conjunto.apurado.area_m2,
    )
```

**`services/domain/certidao_lancamento/certidao/certidao_builder.py`** — ALTERADO nesta SPEC: a tabela do
conjunto ganha as três medidas.

```python
    def _identificacao(self, objeto: LoteUnico | ConjuntoDesenhado) -> tuple[Bloco, ...]:
        match objeto:
            case LoteUnico():
                return ()
            case ConjuntoDesenhado(participacoes=participacoes, area_desenho_m2=area):
                return (
                    Paragrafo(texto=IDENTIFICACAO_CONJUNTO.format(area=formatar_area(area))),
                    Tabela(
                        colunas=(
                            ColunaFixa(largura_mm=34.0),
                            ColunaFluida(),
                            ColunaFixa(largura_mm=24.0, alinhamento=Alinhamento.DIREITA),
                            ColunaFixa(largura_mm=24.0, alinhamento=Alinhamento.DIREITA),
                            ColunaFixa(largura_mm=18.0, alinhamento=Alinhamento.DIREITA),
                        ),
                        cabecalho=("Contribuinte", "Endereço", "Área do lote (m²)", "Área contida (m²)", "% do lote"),
                        linhas=tuple(self._linha(p) for p in participacoes),
                    ),
                )

    def _linha(self, p: ParticipacaoCertificada) -> tuple[str, ...]:
        return (
            p.imovel.sql or "",
            p.imovel.endereco,
            formatar_area(p.area_lote_m2),
            formatar_area(p.area_intersecao_m2),
            formatar_percentual(p.fracao_contida),   # "37,42%"
        )
```

**`services/domain/certidao_lancamento/certidao/constants.py`**

```python
# Sem citar a planta: sem o mapa no pedido, ela não existe (SPEC 001).
IDENTIFICACAO_CONJUNTO = (
    "Os imóveis objeto desta declaração compõem a área desenhada, com {area} m², e são os relacionados "
    "abaixo, com a parte de cada um que o desenho ocupa."
)
```

**`apps/lotes_mais_proximos/contexto.py`** — o limiar entra pela orquestração, como a área máxima, e é o
único: a gaveta e o modal da certidão leem a mesma constante.

```python
LOTE_FRACAO_MINIMA_CONTIDA: float = settings.LOTE_FRACAO_MINIMA_CONTIDA   # 0.99 por padrão
```

**`templates/lotes_mais_proximos/partials/_tabela_conjunto.html`** e **`_resumo_conjunto.html`** — a
coluna nova e a contagem; os dois voltam a cada lixeira (SPEC localizacao_lote/004).

```html
<td class="tabular-nums text-right">{{ item.fracao_contida|percentual }}</td>
```

```html
<span>{{ resumo.inteiros }} inteiro{{ resumo.inteiros|pluralize }} · {{ resumo.parciais }} parcia{{ resumo.parciais|pluralize:"l,is" }}</span>
```

## 7 · Caveats
A área do lote usada no percentual é a **da geometria**, não a `area_terreno_m2` do cadastro. A
intersecção só pode ser medida na geometria, e dividir por um número de outra origem daria
percentuais acima de 100%. O custo é que a certidão pode trazer área de lote diferente da área
cadastrada que a gaveta do lote mostra.

"Inteiro" e "parcial" moram em `lotes_mais_proximos`, e o tipo de despacho só na certidão: a gaveta
conta lotes, e o modal traduz a contagem em sugestão. A busca não conhece ação alguma (§3.5 do
CLAUDE.md), e o limiar é um só. O custo é que quem lê o resumo da gaveta precisa saber que "todos
inteiros" é o que o modal vai sugerir como "em maior área".

A sugestão do modal usa as medidas guardadas na sessão, e a certidão imprime as da releitura da
emissão. O modal não vai ao GeoServer (SPEC 002), e a releitura é a que vale. O custo é a sugestão
poder divergir da medida impressa quando a camada muda entre os dois — o tipo, porém, já é o que o
auditor escolheu.

A busca do desenho passa a pedir os lotes no CRS métrico e a reprojetar cada um para o mapa no
servidor, com uma intersecção GEOS por lote. É o que dá área em metro quadrado sem uma segunda
consulta, e a revisão reaproveita as medidas guardadas na sessão. O custo é trabalho proporcional ao
número de lotes na consulta e na releitura da emissão, contido pela área máxima do desenho.

## 8 · Testes (TDD)
- `test_participacao_mede_intersecao_e_fracao_do_lote` — lote 20×20 com metade dentro dá 400 m²,
  200 m² e fração 0,5.
- `test_lote_inteiro_a_partir_do_limiar` — 0,995 com limiar 0,99 é inteiro; 0,989 é parcial.
- `test_sugestao_em_maior_area_so_com_todos_inteiros` — todos inteiros sugerem "em maior área"; um
  inteiro e um parcial sugerem "parcial"; desenho dividido entre A (0,40) e B (0,15) sugere "parcial".
- `test_busca_mede_no_crs_metrico_e_devolve_lotes_no_crs_do_mapa` — o request pede `EPSG:31983` e os
  lotes devolvidos estão em 4326.
- `test_tirar_o_lote_parcial_muda_a_sugestao` — conjunto com um inteiro e um parcial sugere "parcial";
  `RemoverDoConjunto` tirando o parcial deixa um conjunto que sugere "em maior área".
- `test_tabela_e_resumo_mostram_percentual_e_contagem` — a tabela traz `50,00%` e o resumo da gaveta
  inferior conta inteiros e parciais, também na resposta da lixeira, sem citar tipo de despacho.
- `test_modal_do_conjunto_sugere_sem_reprojetar` — o modal marca o tipo sugerido sem chamar
  `reprojetar` *(marker `banco`)*.
- `test_certidao_do_conjunto_traz_areas_e_percentuais_por_lote` — uma linha por lote com área do lote,
  área contida e percentual, medidos na releitura.
- `test_amostra_conjunto_com_participacoes` — PDF "em maior área" e PDF "parcial", ambos com a tabela
  das medidas, para conferência *(marker `artefato`)*.
