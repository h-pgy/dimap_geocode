---
spec: certidao_lancamento/003
versao: v2
atualizado_em: 2026-09-17
testes_tdd: false
implementado: false
markers_obrigatorios: [artefato]
changelog:
  - v1: versão inicial
  - v2: submódulo `lote_espacial` renomeado para `lotes_mais_proximos`
---

# SPEC certidao_lancamento/003 — Certidão "a maior" e "a menor"

## 1 · User story
O auditor fiscal com a concessão emite a certidão de um terreno desenhado sabendo quanto de cada lote
o desenho ocupa, no contexto de um terreno que contém lotes inteiros ou que cabe dentro de um ou mais
lotes, para obter a certidão na modalidade certa, "a maior" ou "a menor", com a proporção de cada
lote declarada.

## 2 · Condições de pronto
- [ ] Cada lote do conjunto traz a **área do lote**, a **área de intersecção** com o desenho e o
      **percentual** que a intersecção representa da área do lote.
- [ ] Um lote é **totalmente contido** quando o percentual atinge o limiar configurado; abaixo dele, é
      **parcialmente contido**.
- [ ] Com algum lote totalmente contido, o conjunto é da modalidade **"a maior"**; sem nenhum, é
      **"a menor"** — inclusive o desenho que cai parte no lote A e parte no lote B.
- [ ] A tabela da gaveta inferior mostra o percentual de cada lote, e a gaveta do desenho mostra a
      **modalidade**.
- [ ] Tirar um lote na tabela **recalcula a modalidade** com os lotes que restaram.
- [ ] A certidão "a maior" declara que os imóveis compõem a área desenhada e traz, para cada um,
      área do lote, área contida e percentual.
- [ ] A certidão "a menor" declara que a área desenhada **está contida** nos imóveis relacionados e traz
      os mesmos três valores por imóvel.
- [ ] A modalidade sai no título da certidão e no envelope do ato, e a certidão de um lote pela
      gaveta segue sem modalidade.
- [ ] O design da coluna de percentual e da modalidade na gaveta foi aprovado no mock e as peças
      novas portadas para o tema e o styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
A participação de um lote é a medida da intersecção entre ele e o [Desenho](../localizacao_lote/003-lotes-do-desenho.md#3--domínio),
apurada no CRS métrico da camada. A modalidade **não é escolha de ninguém**: é derivada das
participações dos lotes que restaram depois da revisão da SPEC [localizacao_lote/004](../localizacao_lote/004-revisao-do-conjunto.md).

**`services/domain/lotes_mais_proximos/models.py`** — `LoteNoDesenho` novo e `LotesDoDesenho` inteiro.

```python
class ModalidadeConjunto(StrEnum):
    A_MAIOR = "a_maior"   # o desenho contém ao menos um lote inteiro
    A_MENOR = "a_menor"   # o desenho cabe dentro dos lotes que toca


class LoteNoDesenho(BaseModel):
    """Um lote e o quanto dele o desenho ocupa. Áreas medidas da geometria, no CRS métrico."""

    model_config = ConfigDict(frozen=True)

    lote: LoteFeature              # geometria já no CRS do mapa
    area_lote_m2: float = Field(gt=0)
    area_intersecao_m2: float = Field(ge=0)

    @computed_field
    @property
    def percentual_contido(self) -> float:
        return min(100.0, 100.0 * self.area_intersecao_m2 / self.area_lote_m2)


class LotesDoDesenho(BaseModel):
    conjunto: ConjuntoDeLotes
    area_m2: float = Field(gt=0)
    # ALTERADO nesta SPEC: cada lote vem com a sua participação no desenho.
    lotes: tuple[LoteNoDesenho, ...] = ()
    # ALTERADO nesta SPEC: o limiar é do processo, mas a modalidade precisa dele para ser derivada.
    limiar_totalmente_contido: float = Field(gt=0, le=100)

    # ALTERADO nesta SPEC
    @computed_field
    @property
    def modalidade(self) -> ModalidadeConjunto | None:
        if not self.lotes:
            return None
        if any(l.percentual_contido >= self.limiar_totalmente_contido for l in self.lotes):
            return ModalidadeConjunto.A_MAIOR
        return ModalidadeConjunto.A_MENOR
```

**`services/domain/certidao_lancamento/models.py`** — `ConjuntoDesenhado` inteiro.

```python
class ConjuntoDesenhado(ObjetoCertidao):
    tipo: Literal["conjunto_desenhado"] = "conjunto_desenhado"
    # ALTERADO nesta SPEC: a participação de cada lote, não só o lote.
    participacoes: tuple[ParticipacaoCertificada, ...] = Field(min_length=1)
    area_desenho_m2: float = Field(gt=0)
    # ALTERADO nesta SPEC: a modalidade apurada no dia da emissão, que vai para o papel e para o envelope.
    modalidade: ModalidadeConjunto

    @property
    def imoveis(self) -> tuple[LoteAttributes, ...]:
        return tuple(p.imovel for p in self.participacoes)


class ParticipacaoCertificada(BaseModel):
    """O que a certidão imprime de cada lote. Guardado, não derivado: é o valor do dia da emissão."""

    model_config = ConfigDict(frozen=True)

    imovel: LoteAttributes
    area_lote_m2: float = Field(gt=0)
    area_intersecao_m2: float = Field(ge=0)
    percentual_contido: float = Field(ge=0, le=100)
```

**Mock:** [003-mock-certidao-a-maior-e-a-menor.html](003-mock-certidao-a-maior-e-a-menor.html) — leia a
skill `mock`.

## 4 · Fora de escopo
- Lote condominial como caso de "a menor" (a unidade é parte do condomínio) — sem dono ainda.
- Percentual do **desenho** que cai em cada lote (intersecção sobre a área do desenho) — sem dono ainda.
- Escolher a modalidade à mão contra a apurada — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/lotes_mais_proximos/do_desenho.py` → `BuscarLotesDoDesenho`, `ConferirDesenho` (SPEC localizacao_lote/003).
- `@services/domain/lotes_mais_proximos/conjunto.py` → `RevisarConjunto` (SPEC localizacao_lote/004).
- `@services/domain/geometry/reprojecao.py` → `reprojetar` (SPEC localizacao_lote/002).
- `@services/domain/certidao_lancamento/certidao.py` → `MontarCertidaoLancamento` (SPECs 001 e 002).
- `@apps/certidao_lancamento/emissao.py` → `emitir_certidao_do_conjunto` (SPEC 002).
- `@templates/lotes_mais_proximos/partials/_tabela_lotes.html` e `_gaveta_desenho.html` (SPECs localizacao_lote/003 e 004).
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
            cql_filter=CqlFilter(predicates=[CqlIntersects(field=camada.campo_geometria, wkt=_wkt(projetado))]),
            count=PAGE_SIZE,
        )
        desenho = GEOSGeometry(json.dumps(projetado.model_dump()))
        return tuple(
            self._participacao(lote, desenho, camada)
            for page in self.fetcher(request)
            for feature in page.features
            if (lote := feature_para_lote(feature, camada.crs_camada)) is not None
        )

    def _participacao(self, lote: LoteFeature, desenho: GEOSGeometry, camada: CamadaLotes) -> LoteNoDesenho:
        poligono = GEOSGeometry(json.dumps(lote.geometry.model_dump()))
        return LoteNoDesenho(
            lote=_reprojetar_lote(lote, camada.crs_saida),
            area_lote_m2=poligono.area,
            # Intersecção de GEOS e não o INTERSECTS do servidor: o servidor diz SE cruza, não QUANTO.
            area_intersecao_m2=poligono.intersection(desenho).area,
        )
```

**`services/domain/certidao_lancamento/certidao.py`** — o texto por modalidade.

```python
TITULO_POR_MODALIDADE = {
    ModalidadeConjunto.A_MAIOR: "Certidão de Existência de Lançamento — a maior",
    ModalidadeConjunto.A_MENOR: "Certidão de Existência de Lançamento — a menor",
}
ABERTURA_POR_MODALIDADE = {
    ModalidadeConjunto.A_MAIOR: (
        "A área delimitada na planta de localização, com {area} m², compreende os imóveis relacionados "
        "abaixo, na proporção indicada para cada um."
    ),
    ModalidadeConjunto.A_MENOR: (
        "A área delimitada na planta de localização, com {area} m², está contida nos imóveis relacionados "
        "abaixo, na proporção indicada para cada um."
    ),
}


    def _identificacao_conjunto(self, objeto: ConjuntoDesenhado) -> tuple[Bloco, ...]:
        abertura = ABERTURA_POR_MODALIDADE[objeto.modalidade]
        area = formatar_area(objeto.area_desenho_m2)
        return (
            Paragrafo(texto=abertura.format(area=area)),
            Tabela(
                colunas=(
                    ColunaFixa(largura_mm=34.0),
                    ColunaFluida(),
                    ColunaFixa(largura_mm=24.0, alinhamento=Alinhamento.DIREITA),
                    ColunaFixa(largura_mm=24.0, alinhamento=Alinhamento.DIREITA),
                    ColunaFixa(largura_mm=18.0, alinhamento=Alinhamento.DIREITA),
                ),
                cabecalho=("Contribuinte", "Endereço", "Área do lote (m²)", "Área contida (m²)", "% do lote"),
                linhas=tuple(self._linha(p) for p in objeto.participacoes),
            ),
        )

    def _linha(self, p: ParticipacaoCertificada) -> tuple[str, ...]:
        return (
            p.imovel.sql or "",
            p.imovel.endereco,
            formatar_area(p.area_lote_m2),
            formatar_area(p.area_intersecao_m2),
            formatar_percentual(p.percentual_contido),   # "37,42%"
        )
```

**`apps/lotes_mais_proximos/contexto.py`** — o limiar entra pela orquestração, como a área máxima.

```python
LOTE_LIMIAR_TOTALMENTE_CONTIDO: float = settings.LOTE_LIMIAR_TOTALMENTE_CONTIDO   # 99.0 por padrão
```

**`templates/lotes_mais_proximos/partials/_tabela_lotes.html`** — a coluna nova.

```html
<td class="tabular-nums text-right">{{ item.percentual_contido|floatformat:2 }}%</td>
```

## 7 · Caveats
A área do lote usada no percentual é a **da geometria**, não a `area_terreno_m2` do cadastro. A
intersecção só pode ser medida na geometria, e dividir por um número de outra origem daria
percentuais acima de 100%. O custo é que a certidão pode trazer área de lote diferente da área
cadastrada que a gaveta do lote mostra.

"Totalmente contido" é percentual **a partir do limiar** (`LOTE_LIMIAR_TOTALMENTE_CONTIDO`, 99% por
padrão), não igual a 100%. Um traço à mão sobre a divisa nunca coincide com ela, e exigir 100%
faria quase todo "a maior" sair como "a menor". O custo é que um lote com 99,2% dentro sai como
totalmente contido.

O conjunto misto, com um lote inteiro e outros parciais, é "a maior". Basta um lote inteiro dentro
para o desenho não caber nos lotes, e os parciais seguem com o percentual declarado. O custo é que
a modalidade depende da revisão da tabela: tirar o único lote inteiro vira o conjunto para "a menor".

A busca do desenho passa a pedir os lotes no CRS métrico e a reprojetar cada um para o mapa no
servidor, com uma intersecção GEOS por lote. É o que dá área em metro quadrado sem uma segunda
consulta. O custo é trabalho proporcional ao número de lotes a cada passo da revisão, contido pela
área máxima do desenho.

## 8 · Testes (TDD)
- `test_participacao_mede_intersecao_e_percentual_do_lote` — lote 20×20 com metade dentro dá 400 m²,
  200 m² e 50%.
- `test_lote_acima_do_limiar_e_totalmente_contido` — 99,5% com limiar 99 conta como inteiro; 98,9% não.
- `test_modalidade_a_maior_com_algum_lote_inteiro` — um lote a 100% e outro a 30% dão "a maior".
- `test_modalidade_a_menor_com_desenho_entre_dois_lotes` — desenho dividido entre A (40%) e B (15%)
  dá "a menor".
- `test_busca_mede_no_crs_metrico_e_devolve_lotes_no_crs_do_mapa` — o request pede `EPSG:31983` e os
  lotes devolvidos estão em 4326.
- `test_remover_o_lote_inteiro_vira_a_menor` — `RevisarConjunto` sem o único lote inteiro devolve
  "a menor".
- `test_tabela_e_resumo_mostram_percentual_e_modalidade` — a tabela traz `50,00%` e a gaveta do desenho
  traz a modalidade.
- `test_certidao_a_maior_traz_areas_e_percentuais_por_lote` — título "a maior" e uma linha por lote com
  as três medidas.
- `test_certidao_a_menor_declara_area_contida` — título "a menor" e a abertura "está contida".
- `test_amostras_a_maior_e_a_menor` — dois PDFs para conferência *(marker `artefato`)*.
