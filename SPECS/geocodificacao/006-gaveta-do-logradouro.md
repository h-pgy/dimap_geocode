---
spec: geocodificacao/006
versao: v1
atualizado_em: 2026-10-02
testes_tdd: false
implementado: false
changelog:
  - v1: versão inicial
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
- [ ] Abrir a gaveta não consulta o WFS de novo: ela sai dos segmentos que a resposta já trouxe.
- [ ] O design da gaveta foi aprovado no mock e a gaveta está no styleguide.

## 3 · Domínio
O logradouro é o da [geocodificação por codlog](001-logradouro-geocod-linha.md): os
`SegmentoLogradouroFeature` de um codlog. Esta SPEC dá nome à entidade que os segmentos repetem e
apura o que só existe no conjunto deles.

**`services/domain/logradouro_geocod/models.py`**

```python
class Logradouro(BaseModel):
    """O logradouro como entidade: a identidade que todos os seus segmentos repetem."""

    codlog: str
    tipo_logradouro: str
    titulo: str | None = None
    preposicao: str | None = None
    nome_logradouro: str

    @property
    def denominacao(self) -> str:
        # O nome sem o tipo: "TTE SIQUEIRA CAMPOS". Sem título e preposição o nome fica incompleto.
        partes = [self.titulo, self.preposicao, self.nome_logradouro]
        return " ".join(p for p in partes if p)

    @property
    def nome_completo(self) -> str:
        return f"{self.tipo_logradouro} {self.denominacao}"   # "PQ TTE SIQUEIRA CAMPOS"
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

## 5 · Peças de referência a compor
- `@services/domain/lote_geocod/gaveta.py` → `MontarGavetaLote`: molde da gaveta com medida apurada no CRS métrico.
- `@services/domain/geometry` → `reprojetar`, `para_geos`: o eixo no CRS métrico, para medir.
- `@apps/logradouro_geocoder/views.py` → `geocodificar_codlog`: a resposta do logradouro, que a busca e a SPEC 005 já usam.
- `@templates/lote_geocoder/partials/_gaveta_lote.html`: o organismo de gaveta lateral a compor (`data-gaveta`, `.card-well`, `.valor-ausente`).
- Skills: `ontologia`, `mock`, `componentes-frontend`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/logradouro_geocod/gaveta.py`** — a gaveta se monta dos segmentos que a resposta
do logradouro já tem.

```python
class GavetaLogradouroInput(BaseModel):
    segmentos: list[SegmentoLogradouroFeature] = Field(min_length=1)   # todos do mesmo codlog
    crs_metrico: int


class MontarGavetaLogradouro:
    def __call__(self, entrada: GavetaLogradouroInput) -> GavetaLogradouro:
        return self.pipeline(entrada)

    def pipeline(self, entrada: GavetaLogradouroInput) -> GavetaLogradouro:
        return GavetaLogradouro(
            logradouro=self._logradouro(entrada.segmentos[0]),
            extensao_m=self._extensao_m(entrada),
            quantidade_segmentos=len(entrada.segmentos),
            numeracao=self._numeracao(entrada.segmentos),
        )

    def _logradouro(self, segmento: SegmentoLogradouroFeature) -> Logradouro:
        a = segmento.attributes
        return Logradouro(
            codlog=a.codlog,
            tipo_logradouro=a.tipo_logradouro,
            titulo=a.titulo,
            preposicao=a.preposicao,
            nome_logradouro=a.nome_logradouro,
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

**`apps/logradouro_geocoder/views.py`** — a resposta do logradouro passa a abrir a gaveta; a busca e a
SPEC 005 a recebem juntas, sem mudar nada nelas.

```python
def geocodificar_codlog(request: HttpRequest, codlog: str) -> HttpResponse:
    ...
    if not features:
        return render(...)   # o aviso de hoje, sem mudança
    montar_gaveta = MontarGavetaLogradouro()   # NOVO
    gaveta = montar_gaveta(GavetaLogradouroInput(segmentos=features, crs_metrico=MAP_INTERPOLATION_CRS))
    geojson = to_geojson_feature_collection(features, _properties)
    contexto = contexto_mapa(geojson, MAP_COR_LINHA) | {"gaveta": gaveta}
    return render(request, TEMPLATE_RESULTADO_LOGRADOURO, contexto)
```

O `_resultado_logradouro.html` troca o `mapping/_sem_gaveta_oob.html` pelo OOB do `#gaveta-entidade` com
o `logradouro_geocoder/partials/_gaveta_logradouro.html`, de raiz `data-gaveta="logradouro-{{ codlog }}"`.

## 7 · Caveats
A gaveta nasce na resposta da busca, e não na da ação da SPEC 005. É a gaveta da entidade, que vale para
quem chega a ela por qualquer caminho. O custo é a busca por logradouro mudar junto: ela deixa de
esvaziar a gaveta lateral e passa a abrir esta.

A extensão é a soma dos eixos da camada. A camada desenha um eixo por pista nas avenidas de pista
dupla, e não há atributo que diga qual eixo é o par de qual. O custo é a extensão dessas avenidas sair
quase em dobro: a Av. Paulista dá 5,4 km para cerca de 2,8 km reais.

Número zero na faixa de um segmento é tratado como lado sem numeração. É assim que a camada marca o
lado vazio. O custo é um imóvel de número 0, se existir, não contar para o menor número.

O `Logradouro` nasce ao lado do `SegmentoLogradouroAttributes`, que continua repetindo a identidade em
cada segmento. Recompor o segmento sobre a entidade mexeria na busca, na geocodificação de endereço e
nos catálogos. O custo é a identidade do logradouro existir em dois tipos.

## 8 · Testes (TDD)
- `test_gaveta_logradouro_apura_extensao_e_numeracao_do_logradouro_inteiro` — dois segmentos de 30 m e
  40 m no CRS métrico, com faixas `2–10` (par), `0–0` (ímpar) e `1–25` (ímpar), dão extensão de 70 m e
  numeração `1–25`; segmentos sem numeração dão `numeracao` `None`.
- `test_geocodificar_abre_a_gaveta_do_logradouro` — POST anônimo com um codlog devolve o payload do
  mapa e, no OOB do `#gaveta-entidade`, a gaveta de `data-gaveta="logradouro-<codlog>"`, com o codlog,
  a extensão em km e a faixa de numeração, consultando o WFS uma vez só.
- O `test_do_ponto_devolve_a_linha_do_logradouro_mais_proximo` da SPEC 005 passa a conferir essa gaveta
  no `#gaveta-entidade`, em vez de vazio.
