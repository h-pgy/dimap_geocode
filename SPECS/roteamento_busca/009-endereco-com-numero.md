---
spec: roteamento_busca/009
versao: v5
atualizado_em: 2026-06-29
implementado: false
changelog:
  - v1: versão inicial
  - v2: EnderecoCodlogParse.numero passa a ser `int` (número de imóvel é estritamente
    numérico no caminho por codlog); separar_numero_codlog só aceita dígitos puros e o
    identifier coage para int. EnderecoParse.numero (caminho por nome) permanece `str`.
  - v3: revoga a assimetria da v2. Introduz um parser TOLERANTE de número de imóvel
    (`parse_numero_imovel`), na mesma ideia dos parsers de codlog/contribuinte: extrai o
    inteiro, descarta sufixo de unidade ("1a"→1) e absorve marcadores ("nº1", "n°1", "n1",
    "n.1", "nº 1"→1). Compartilhado por separar_numero e separar_numero_codlog; AMBOS
    EnderecoParse.numero e EnderecoCodlogParse.numero são `int`.
  - v4: amplia `parse_numero_imovel` para cobrir TODAS as formas de marcador de número
    (nº, n°, n., n, no, nro, nro., núm/num, núm./num., número/numero, #), grudadas ou
    separadas, case-insensitive; regex de marcador ancorada no início do token (corrige o
    `sub` não-ancorado da v3). Sufixo de unidade (1a, 1-A) sempre descartado.
  - v5: `parse_numero_imovel` (e o reconhecimento de marcador `eh_so_marcador`) passam a
    morar no domínio de endereço `services/domain/address_match` (semeando esse módulo),
    expostos no seu `__init__.py`. Os localizadores `separar_numero`/`separar_numero_codlog`
    em `roteamento_busca` passam a COMPOR esse parser por import do nível superior.
---

# SPEC roteamento_busca/009 — Endereço com número (seções de endereço por codlog e por nome + ordenação por prioridade)

- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como usuário da busca simples, quero digitar um **logradouro e um número** — seja começando por um
**codlog** (`12345 100`), seja começando pelo **nome da rua** (`AV PAULISTA, 100`) — e ver, já a cada
tecla, **sugestões de endereço** que combinam aquele logradouro com o número que digitei, para que ao
clicar numa sugestão o sistema receba o **codlog + número** prontos para geocodificar o ponto numa
iteração futura.

Como o roteador é **ambíguo de propósito**, quando o que digitei puder ser mais de uma coisa (ex.:
`12345 100` pode ser um endereço por codlog **ou** um número de contribuinte), quero ver **todas as
seções plausíveis** ao mesmo tempo e decidir clicando — e quero que elas apareçam numa **ordem de
prioridade previsível**, da entidade mais específica para a menos específica.

## Critérios de aceite

- [ ] Digitar **codlog + número** (ex.: `12345 100`, `12345, 100`) produz uma seção **"Endereço (por
      codlog)"** cujas sugestões vêm do **lookup exato de codlog** (mesma resolução da seção de
      logradouro por codlog), cada item exibindo o logradouro e o **número digitado**.
- [ ] Digitar **nome do logradouro + número** (ex.: `AV PAULISTA, 100`, `PAULISTA 100`) produz uma
      seção **"Endereço (por nome)"** cujas sugestões vêm do **match literal/substring** sobre os nomes
      (mesma resolução da seção de logradouro por nome), cada item exibindo o logradouro e o **número
      digitado**.
- [ ] Em **ambas** as seções de endereço, clicar numa sugestão chama a **view de seleção de endereço**
      (`address_geocoder:selecionar`, já existente) postando **`codlog` + `numero`** — **nunca** o nome
      do logradouro (o codlog é o identificador preciso; o nome é só exibição). O payload casa com o
      `EnderecoSelection` (codlog + numero), já pronto.
- [ ] O separador entre logradouro e número aceita o que **fizer sentido para o usuário** (espaço,
      vírgula) — tanto no caminho por nome quanto no por codlog. **Não há** supressão de candidatos para
      desambiguar: a ambiguidade com contribuinte é **intencional**.
- [ ] O **número de imóvel** passa por um parser **tolerante** e **compartilhado** pelos dois caminhos
      (na mesma ideia dos parsers de codlog e contribuinte): ele **normaliza a forma escrita e devolve um
      `int`**. Em particular: (a) **descarta sufixo de unidade** — `Avenida Paulista, 1a` é parseado como
      logradouro `Avenida Paulista` + número `1` (idem `1-A`, `1b`); e (b) **absorve qualquer marcador de
      número usual**, grudado ou separado, com ou sem ponto, **case-insensitive**:
      `nº` · `n°` · `n.` · `n` · `no` · `nro` · `nro.` · `núm`/`num` · `núm.`/`num.` · `número`/`numero` ·
      `#` — todos com o mesmo desfecho (`nº1`, `n. 1`, `nro 1`, `núm.1`, `numero 1`, `#1` → número `1`).
      Tanto **`EnderecoParse.numero`** (por nome) quanto **`EnderecoCodlogParse.numero`** (por codlog) são
      **`int`**.
- [ ] O parser de número (`parse_numero_imovel` + `eh_so_marcador`) vive em
      **`services/domain/address_match`** (domínio de endereço), exposto no `__init__.py`, **sem import de
      Django**. O `roteamento_busca` **importa do nível superior** e compõe — não reimplementa o parsing do
      número nem alcança submódulos internos (§11).
- [ ] Entrada puramente numérica com número (ex.: `12345 100`) gera **simultaneamente** as seções
      **"Lote (por contribuinte)"** e **"Endereço (por codlog)"** — o usuário decide clicando.
- [ ] As seções da lista de sugestões aparecem **sempre** na ordem de prioridade:
      **lote (contribuinte) > endereço por codlog > endereço por nome > codlog (só) > logradouro por
      nome (só)**. A ordenação é decidida **uma vez no roteador** (ordem dos candidatos) e propaga
      naturalmente para a renderização das seções, sem reordenar no `search` nem no template.
- [ ] Digitar **só o codlog** (`12345`, sem número) continua produzindo apenas a seção de **logradouro
      por codlog** (linha); digitar **só o nome** continua produzindo apenas a de **logradouro por
      nome**. A presença do número é o que distingue endereço de logradouro.
- [ ] Respostas são **partials HTML** (§3.1); a montagem dos DTOs deixa `ValidationError` propagar ao
      middleware (infraestrutura/001), sem `try/except` nas views. CSRF herdado do `<body>` (como na
      008). Tipagem integral; `mypy` limpo.

## Contexto e decisões de arquitetura

Mexe em **domínio** (`services/domain/roteamento_busca`: novo parse, novo identifier, ordenação;
`services/domain/address_match`: **novo módulo** semeado com o parser tolerante de número de imóvel) e em
**interface/orquestração** (`apps/address_geocoder`: dois renderers de seção + partials; `apps/search`:
registro). **Não** há resolução de geometria nem plotagem — o desfecho é a lista de sugestões clicáveis
que postam para a view de seleção de endereço (que segue sendo o *stub* da 008). O parser de número fica
no **domínio de endereço** (não no roteador), porque "ler o número de um imóvel" é regra do domínio de
endereço; o roteador apenas **localiza** o token e **compõe** o parser.

A observação que simplifica tudo: **os dois fluxos novos convergem para o mesmo destino** — uma
sugestão que é, no fim, um **codlog + número** postado em `address_geocoder:selecionar`. A diferença
entre eles é **só o passo de matching**, e esse passo **já existe**:

| Seção nova            | Como resolve o logradouro | Peça de domínio reutilizada |
|-----------------------|---------------------------|-----------------------------|
| Endereço (por codlog) | lookup exato de codlog    | `match_codlog`              |
| Endereço (por nome)   | match literal/substring   | `match_logradouro_literal`  |

Os dois matchers **já devolvem o `codlog` em cada linha** (`CodlogMatchOutput.codlog`,
`LogradouroMatchOutput.codlog`). Logo a sugestão já tem o codlog na mão; o que falta é só **carregar o
número junto** e **trocar o destino do POST** (de `logradouro_matcher:selecionar` para
`address_geocoder:selecionar`). Por isso os dois renderers de endereço são, na prática, **espelhos** de
`secao_codlog` e `secao_logradouro` — mudam apenas o número que pega carona e a rota do clique.

### Metade já existe

O caminho **logradouro + número** **já está modelado e roteado**: o `EnderecoParse`
(= `LogradouroParse` + `numero`) e o `EnderecoIdentifier` já produzem o candidato para
`AV PAULISTA, 100`, e o `EnderecoIdentifier` **já está na tupla de identifiers do roteador**. O que
falta nesse caminho é só o **renderer** — `REGISTRO_SECOES` não tem `TipoEntrada.ENDERECO`, então hoje
esse candidato é gerado e silenciosamente descartado. Esta SPEC **liga** essa seção.

O que é genuinamente novo é o ramo do **codlog + número**:

- **`EnderecoCodlogParse`** (novo `TipoEntrada.ENDERECO_CODLOG`): `codlog` + `numero`.
- **`CodlogNumeroIdentifier`**: separa o número e **delega a validação do codlog ao `CodlogIdentifier`
  por composição** (§10.4) — não reimplementa as regras de codlog (rejeição de `.`, dígitos, máscara
  com `-`).
- um separador de número **numérico** (irmão de `separar_numero`, que é ancorado em letra): de
  `12345 100` extrai `("12345", "100")`, exigindo um separador entre os dois grupos (espaço/vírgula);
  sem separador (`12345`) **não** há número e o codlog cai no `CodlogIdentifier` normal.

### Ordenação por prioridade (no roteador)

A regra de UX "qual seção aparece primeiro" é declarada como **uma constante única** de prioridade por
`TipoEntrada` e aplicada **uma vez** ao ordenar a lista de candidatos no `EntradaRouter`. Recomenda-se
a constante (em vez de reordenar a tupla de identifiers) porque é **declarativa**, deixa a regra
explícita num lugar só e **sobrevive ao caso ambíguo** (vários candidatos) sem depender da ordem de
registro dos identifiers. Como `apps/search/views.py` itera `result.candidatos` na ordem e o template
itera `secoes` na ordem, **ordenar no roteador ordena no resto**. A semântica de `match` (só dispara
com candidato único) não muda.

Prioridade (índice menor = aparece primeiro):

```
0  CONTRIBUINTE      (lote)
1  ENDERECO_CODLOG   (endereço por codlog)
2  ENDERECO          (endereço por nome)
3  CODLOG            (logradouro por codlog)
4  LOGRADOURO        (logradouro por nome)
```

### Princípios aplicados (§3, §10, §11)

- **§3.1 HATEOAS:** renderers produzem *partial* HTML; nenhum JSON consumido por JS.
- **§3.2/§3.3 Isolamento:** o matching está no domínio; os renderers só **adaptam** o candidato em DTO e
  chamam o domínio. O novo identifier vive no domínio, sem import de Django.
- **§7.1 Normalização única:** os matchers reutilizados já operam sobre nomes/codlog normalizados — esta
  SPEC não reintroduz normalização.
- **§10.1 SRP / §10.4 Composição:** o `CodlogNumeroIdentifier` **compõe** o `CodlogIdentifier`; os
  localizadores **compõem** `parse_numero_imovel` (que mora no domínio de endereço `address_match`, não
  no roteador); cada renderer tem uma responsabilidade; o domínio de endereço não cruza lote.
- **§10.5:** Python 3.14 — sem `from __future__`.

## Peças de referência a compor

- `@services/domain/roteamento_busca` → `CodlogIdentifier` (compor no novo identifier), `EnderecoParse`
  + `EnderecoIdentifier` (já produzem logradouro+número — **reutilizar como está**, só falta renderer),
  `TipoEntrada`, `Candidato` (união discriminada — acrescentar o novo parse), `EntradaRouter`
  (acrescentar o identifier e a ordenação), e o `__init__.py` (expor o novo parse/tipo).
- `@services/domain/address_match` → **novo módulo de domínio** a criar, seede com o parser tolerante de
  número de imóvel: `parse_numero_imovel` (marcadores + sufixo de unidade → `int`) e `eh_so_marcador`,
  expostos no `__init__.py`. É o primeiro habitante do domínio de endereço.
- `@services/domain/roteamento_busca/parsing.py` → `separar_numero`, `NUMERO`: **tornar `separar_numero`
  tolerante** e **espelhar** numa variante numérica `separar_numero_codlog`, ambas **compondo**
  `parse_numero_imovel`/`eh_so_marcador` (import de `services.domain.address_match`). Os dois `separar_*`
  passam a devolver o número como `int`.
- `@services/domain/codlog_match` → `match_codlog`, `CodlogMatchInput`, `CodlogMatchOutput`: resolução
  exata reutilizada por `secao_endereco_codlog` (idêntica à usada em `secao_codlog`).
- `@services/domain/logradouros_match` → `match_logradouro_literal`, `LiteralLogradouroQuery`,
  `LiteralLogradouroResult`, `LogradouroMatchOutput`: resolução literal reutilizada por `secao_endereco`
  (idêntica à usada em `secao_logradouro`).
- `@apps/logradouro_matcher/views.py` → `secao_codlog` / `secao_logradouro`: **padrão de renderer a
  espelhar** nos dois renderers de endereço.
- `@apps/address_geocoder/views.py` → `selecionar` + `@apps/address_geocoder/schemas.py`
  (`EnderecoSelection` = codlog + numero) + `@apps/address_geocoder/urls.py`
  (`address_geocoder:selecionar`): **destino do clique já pronto** — só ligar os partials a ele.
- `@apps/search/views.py` → `REGISTRO_SECOES`: **estender** com `ENDERECO` e `ENDERECO_CODLOG` (o laço
  de `rotear_busca` não muda).
- `@apps/search/secoes.py` → `SecaoResultado`: contrato de seção compartilhado, **importado** pelos
  renderers.
- `@templates/logradouro_matcher/partials/resultados_codlog.html` e
  `@templates/logradouro_matcher/partials/resultados_logradouro.html`: **padrão dos partials a
  espelhar** para endereço — acrescentando `numero` no `hx-vals` e trocando a rota para
  `address_geocoder:selecionar`.
- **SPEC 007** (seção de logradouro por nome) e **SPEC 008** (seleção clicável + view de endereço como
  stub) → desenho direto que esta SPEC continua. **SPEC infraestrutura/001** → middleware de validação.

## Snippets sugeridos

### Novo parse + tipo (`services/domain/roteamento_busca/models.py`)

```python
# direção — adaptar sem violar §3 nem §10
class TipoEntrada(StrEnum):
    CONTRIBUINTE = "contribuinte"
    CODLOG = "codlog"
    LOGRADOURO = "logradouro"
    ENDERECO = "endereco"
    ENDERECO_CODLOG = "endereco_codlog"  # novo


class EnderecoCodlogParse(BaseModel):
    tipo: Literal[TipoEntrada.ENDERECO_CODLOG] = TipoEntrada.ENDERECO_CODLOG
    codlog: CodlogParse
    numero: int  # número de imóvel é estritamente numérico no caminho por codlog

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completo(self) -> bool:
        return self.codlog.completo and self.numero > 0


# acrescentar à união discriminada:
Candidato = Annotated[
    ContribuinteParse | CodlogParse | LogradouroParse | EnderecoParse | EnderecoCodlogParse,
    Field(discriminator="tipo"),
]

# EnderecoParse JÁ EXISTE: seu campo `numero` muda de `str` para `int` (parser tolerante
# compartilhado). `completo` passa a checar `self.numero > 0`.
```

### Parser de número de imóvel (`services/domain/address_match`) — domínio de endereço

```python
import re

# Marcador de número usual (case-insensitive): nº, n°, n., n, no, nro, nro., núm/num,
# núm./num., número/numero, #. Definido UMA vez e reutilizado.
MARCADOR_NUMERO = r"(?:n(?:[º°o]|ro|[uú]m(?:ero)?)?\.?|#)"
SO_MARCADOR = re.compile(rf"^{MARCADOR_NUMERO}$", re.IGNORECASE)  # token que é SÓ marcador (ex.: "nº", "nro")

# Parser TOLERANTE de número de imóvel — espelha a ideia dos parsers de codlog/contribuinte:
# normaliza a forma escrita e extrai o INTEIRO. Marcador opcional (grudado ou separado) +
# dígitos; sufixo de unidade ("1a", "1-A") cai fora. Ancorado no início. None se não há dígito.
NUMERO_IMOVEL = re.compile(rf"{MARCADOR_NUMERO}?\s*(\d+)", re.IGNORECASE)


def parse_numero_imovel(token: str) -> int | None:
    m = NUMERO_IMOVEL.match(token.strip())  # match = ancorado no início; não exige fim (sufixo ignorado)
    return int(m.group(1)) if m else None


def eh_so_marcador(token: str) -> bool:  # usado pelo localizador p/ limpar marcador residual do logradouro
    return SO_MARCADOR.fullmatch(token.strip()) is not None
```

> O `__init__.py` de `services/domain/address_match` **expõe** `parse_numero_imovel` e `eh_so_marcador`
> (§11 — importar pelo nível superior, sem alcançar submódulos). Este é o **primeiro habitante** do
> domínio de endereço; a geocodificação (interpolação número→ponto, item 2 do roadmap) virá aqui.

### Localizadores de número (`services/domain/roteamento_busca/parsing.py`) — compõem o parser

```python
from services.domain.address_match import eh_so_marcador, parse_numero_imovel

# separar_numero (texto que começa por LETRA — JÁ EXISTE, fica TOLERANTE) e
# separar_numero_codlog (começa por DÍGITO — NOVO) localizam o token candidato a número e
# delegam a leitura a parse_numero_imovel; ambas devolvem o número já como int.
#   "Avenida Paulista, 1a"  -> ("Avenida Paulista", 1)
#   "Avenida Paulista nº 1" -> ("Avenida Paulista", 1)   # marcador separado: removido via eh_so_marcador
#   "12345 100" / "12345, 100" -> ("12345", 100)
#   "12345" -> None (sem separador, sem número -> é codlog puro)
def separar_numero(texto: str) -> tuple[str, int] | None: ...
def separar_numero_codlog(texto: str) -> tuple[str, int] | None: ...
```

> No caso **sem vírgula** com marcador **separado** (`Avenida Paulista nº 1`, `... nro 1`), o localizador
> toma `1` como número e ainda **descarta o token-marcador residual** do texto do logradouro quando ele é
> **só marcador** (`eh_so_marcador(token)`), senão o matcher buscaria "Avenida Paulista nº". Com vírgula,
> o marcador já vem junto do número no resto e é absorvido por `parse_numero_imovel`.

### Identifier compondo o de codlog (`services/domain/roteamento_busca/codlog.py` ou módulo próximo)

```python
class CodlogNumeroIdentifier:
    def __init__(self, codlog_identifier: CodlogIdentifier | None = None) -> None:
        self._codlog = codlog_identifier or CodlogIdentifier()

    def __call__(self, texto: str, finished_typing: bool) -> EnderecoCodlogParse | None:
        partes = separar_numero_codlog(texto)
        if partes is None:
            return None
        codlog_txt, numero = partes
        codlog = self._codlog(codlog_txt, finished_typing)  # composição: regras de codlog
        if codlog is None:
            return None
        return EnderecoCodlogParse(codlog=codlog, numero=numero)  # numero já vem int de separar_numero_codlog
```

### Roteador: novo identifier + ordenação (`services/domain/roteamento_busca/router.py`)

```python
# prioridade da UX, declarada num lugar só
PRIORIDADE_TIPOS: tuple[TipoEntrada, ...] = (
    TipoEntrada.CONTRIBUINTE,
    TipoEntrada.ENDERECO_CODLOG,
    TipoEntrada.ENDERECO,
    TipoEntrada.CODLOG,
    TipoEntrada.LOGRADOURO,
)


class EntradaRouter:
    def __init__(self, identifiers: tuple[Identifier, ...] | None = None) -> None:
        self._identifiers = identifiers or (
            ContribuinteIdentifier(),
            CodlogNumeroIdentifier(),  # novo (antes do CodlogIdentifier não importa: ordena no fim)
            CodlogIdentifier(),
            LogradouroIdentifier(),
            EnderecoIdentifier(),
        )

    def __call__(self, query: RoteamentoQuery) -> RoteamentoResult:
        bruto = query.texto.strip()
        candidatos = [
            c for ident in self._identifiers
            if (c := ident(bruto, query.finished_typing)) is not None
        ]
        candidatos.sort(key=lambda c: PRIORIDADE_TIPOS.index(c.tipo))
        return RoteamentoResult(texto=query.texto, candidatos=candidatos)
```

### Renderers de endereço (`apps/address_geocoder/views.py`) — espelham os de logradouro

```python
from apps.search.secoes import SecaoResultado
from services.domain.codlog_match import CodlogMatchInput, match_codlog
from services.domain.logradouros_match import LiteralLogradouroQuery, match_logradouro_literal
from services.domain.roteamento_busca import EnderecoCodlogParse, EnderecoParse

TITULO_ENDERECO_CODLOG = "Endereço (por codlog)"
TITULO_ENDERECO_NOME = "Endereço (por nome)"


def secao_endereco_codlog(candidato: EnderecoCodlogParse) -> SecaoResultado:
    dto = CodlogMatchInput(
        input_codlog=candidato.codlog.codlog,
        digito_verificador=candidato.codlog.digito_verificador or None,
    )
    html = render_to_string(
        "address_geocoder/partials/resultados_endereco_codlog.html",
        {"resultados": match_codlog(dto), "numero": candidato.numero},
    )
    return SecaoResultado(titulo=TITULO_ENDERECO_CODLOG, html=html)


def secao_endereco(candidato: EnderecoParse) -> SecaoResultado:
    dto = LiteralLogradouroQuery(
        nome=candidato.logradouro.nome,
        tipo=candidato.logradouro.tipo_logradouro or None,
    )
    html = render_to_string(
        "address_geocoder/partials/resultados_endereco_nome.html",
        {"resultado": match_logradouro_literal(dto), "numero": candidato.numero},
    )
    return SecaoResultado(titulo=TITULO_ENDERECO_NOME, html=html)
```

### Registro estendido (`apps/search/views.py`)

```python
REGISTRO_SECOES: dict[TipoEntrada, SectionRenderer] = {
    TipoEntrada.CONTRIBUINTE: secao_contribuinte,
    TipoEntrada.ENDERECO_CODLOG: secao_endereco_codlog,
    TipoEntrada.ENDERECO: secao_endereco,
    TipoEntrada.CODLOG: secao_codlog,
    TipoEntrada.LOGRADOURO: secao_logradouro,
}
```

### Partial de endereço por codlog (`templates/address_geocoder/partials/resultados_endereco_codlog.html`)

```htmldjango
{# fragmento HTMX, sem extends — recebe: resultados (list[CodlogMatchOutput]), numero (str) #}
{% if resultados %}
  <ul class="divide-y divide-base-300">
    {% for r in resultados %}
      <li class="py-3 flex items-baseline gap-4 cursor-pointer hover:bg-base-200"
          hx-post="{% url 'address_geocoder:selecionar' %}"
          hx-vals='{"codlog": "{{ r.codlog }}", "numero": "{{ numero }}"}'
          hx-target="#resultado-busca"
          hx-swap="innerHTML">
        <span class="font-mono text-sm text-base-content/60 w-16 shrink-0">{{ r.codlog }}-{{ r.dv }}</span>
        <span class="font-medium">{{ r.nome_completo }}, {{ numero }}</span>
      </li>
    {% endfor %}
  </ul>
{% else %}
  <p class="text-base-content/60 text-sm py-4">Nenhum logradouro encontrado.</p>
{% endif %}
```

> O partial de endereço por nome (`resultados_endereco_nome.html`) espelha
> `resultados_logradouro.html` (recebe `resultado` + `numero`, mantém o aviso de
> `ignorou_filtro_tipo`), só trocando a rota para `address_geocoder:selecionar` e acrescentando
> `numero` no `hx-vals` e na exibição.

## Fora de escopo

- **Resolução de geometria** (ponto por interpolação do número sobre a linha do logradouro) e qualquer
  chamada de geocodificação — a `selecionar` de endereço segue o *stub* da 008 (valida o DTO e dá
  `print`).
- **Plotagem no mapa** (`apps/mapping` / Leaflet / WMS).
- **Caso especial do endereço fiscal exato** (pop-up ponto vs. polígono) — fase posterior.
- **Match fuzzy** para o nome: as sugestões usam o match **literal/substring** (como na 007); o fuzzy é
  o caminho do match final, fora desta iteração.
- **Busca detalhada** (campos segmentados) e qualquer rota direta dos apps de endereço/logradouro.
- **Guard de desambiguação** que suprima o candidato de contribuinte — a ambiguidade é intencional.
- **Estilização final** das seções e refinamento visual (DaisyUI detalhado).

## Notas de teste

<Só para referência futura — não implementar agora.>

- POST `termo_pesquisa="12345 100"`, `tipo_evento="keyup"` → aparecem as seções **"Lote (por
  contribuinte)"** e **"Endereço (por codlog)"**, nessa ordem (prioridade); a seção de endereço lista
  codlogs que começam com `12345`, cada item exibindo `, 100` e postando `{codlog, numero:"100"}` para
  `address_geocoder:selecionar`.
- POST `termo_pesquisa="AV PAULISTA, 100"` → seção **"Endereço (por nome)"** com itens contendo
  `PAULISTA`, exibindo o número e postando `codlog + numero`. Tipo `AV` reconhecido não dispara o aviso
  de `ignorou_filtro_tipo`.
- Separadores equivalentes: `12345 100` e `12345, 100` produzem o mesmo parse; idem `PAULISTA 100` e
  `PAULISTA, 100`.
- `12345` (sem número) → **só** "Logradouro (por codlog)" (e o candidato de contribuinte que já existia
  hoje); **sem** seção de endereço. `PAULISTA` (sem número) → **só** "Logradouro (por nome)".
- Ordem das seções: uma entrada que gere CONTRIBUINTE + ENDERECO_CODLOG sai sempre com o lote primeiro;
  uma que gere ENDERECO + ... respeita a `PRIORIDADE_TIPOS`.
- `parse_numero_imovel`: `"1"`→1; `"1a"`/`"1-A"`/`"1b"`→1 (sufixo de unidade descartado);
  `"nº1"`/`"n°1"`/`"n1"`/`"n.1"`/`"nº 1"`/`"no 1"`/`"nro1"`/`"nro. 1"`/`"núm1"`/`"num.1"`/`"número 1"`/
  `"numero1"`/`"#1"`/`"# 1"`→1 (todas as formas, case-insensitive); `"abc"`→None; `"norte"`→None
  (marcador não engole token sem dígito).
- Caminho por nome: `"Avenida Paulista, 1a"`→ logradouro `"Avenida Paulista"` + número `1`;
  `"Avenida Paulista, nº1"`, `"Avenida Paulista, n1"`, `"Avenida Paulista, n.1"` → número `1`;
  `"Avenida Paulista nº 1"` (sem vírgula, marcador separado) → logradouro `"Avenida Paulista"` (sem o
  `nº` residual) + número `1`.
- `separar_numero_codlog`: `12345 100`→`("12345",100)`; `12345`→`None`; `001.002.0003 45`→`None` (tem
  ponto, não é codlog) — garantindo que o contribuinte com espaço **não** vire endereço por codlog.
- Números são `int` nos dois parses: `12345 100` → `EnderecoCodlogParse.numero == 100` (não `"100"`);
  `Av Paulista, 1` → `EnderecoParse.numero == 1`. O template renderiza e o POST envia o número
  serializado, coerente com `EnderecoSelection.numero`.
- Clique numa sugestão de endereço (por codlog e por nome) chama a view de endereço e imprime
  `codlog + numero`; DTO inválido cai no middleware (422, não 500); CSRF herdado (sem 403).
- Regressão 005/006/007/008: seções de codlog, contribuinte e logradouro por nome seguem funcionando; a
  view de seleção de logradouro/lote intactas.

## Patches

_Nenhum patch registrado até o momento._
