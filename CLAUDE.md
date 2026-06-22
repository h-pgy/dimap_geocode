# CLAUDE.md — DIMAP GeoCoder

Arquivo de contexto para agentes de IA e desenvolvedores. Define **domínio, decisões de
arquitetura, fluxo do sistema, stack e regras inegociáveis** do projeto. Estruturas internas
(nomes de arquivos, organização fina de cada pacote) se acomodam conforme o código nasce e seguem
os princípios documentados aqui.

---

## 1. Visão Geral

**DIMAP GeoCoder** é um aplicativo web de geocodificação que opera sobre os dados oficiais de
logradouros, lotes fiscais e endereços fiscais da Prefeitura de São Paulo (PMSP). O aplicativo tem por objetivo disponibilizar ao usuário uma interface simples e intuitiva para obter dados georreferenciados de endereços, logradouros ou lotes na cidade de São Paulo. A busca pode ser realizada por endereço, nome ou código de logradouro e/ou número de contribuinte. O aplicativo identifica automaticamente qual o critério de busca e com base nele retorna em um mapa interativo:
1. Se a busca foi por nome ou código de logradouro: a linha que representa esse logradoro
2. Se a busca foi por número de contribuinte ou endereço que corresponde exatamente a um imóvel cadastrado na base do IPTU: o polígono que representa esse imóvle;
3. Se a busca foi por endereço apenas: o ponto no mapa que representa a geocodificação desse endereço.

Posteriormente, o sistema permitirá também a busca por batches (com base em planilhas pré-formatadas para cada tipo de busca), assim como exportar os resultados em formato geopackage, geojson ou shapefile.

### Usuários e projetos (persistência dos resultados)

Além da consulta avulsa, o sistema tem **autenticação de usuário** e o conceito de **Projeto**: um
espaço nomeado, pertencente a um usuário, onde resultados geocodificados são **salvos de forma
durável** para acesso posterior.

- A **busca avulsa permanece pública** — qualquer visitante pode pesquisar e ver o resultado no
  mapa **sem login**. O login só é exigido no momento de **salvar** um resultado em um projeto.
- Um usuário autenticado tem **N projetos**. Cada projeto se organiza em **camadas (layers)**.
- Uma **camada (layer)** é uma coleção nomeada de itens geocodificados **de um único tipo de
  geometria**. Cada layer tem um **nome** e uma **cor de display**, ambos definidos pelo usuário.
  **Um layer nunca mistura tipos** — é só de pontos, só de linhas ou só de polígonos.
- Um projeto **pode conter geometrias de tipos diferentes**, mas sempre **em layers separados**.
  Ex.: um projeto com um layer "Lotes da quadra A" (polígonos, cor X) e um layer "Eixos viários"
  (linhas, cor Y).
- **Pode haver vários layers do mesmo tipo** num projeto, representando coisas distintas. Ex.: dois
  layers de lotes ("Lotes fiscais" e "Lotes municipais"), cada um com seu nome e sua cor.
- **CRUD completo** sobre projetos, layers e itens: o usuário cria o projeto, cria layers (nome +
  cor + tipo), adiciona itens a um layer (geocodificando novos elementos), **reabre** o projeto
  depois, **adiciona** itens/layers e **remove** itens, layers ou o projeto inteiro.
- Como cada item salvo carrega sua geometria e cada layer é homogêneo, o projeto é a base natural
  para os **exports** (geopackage / geojson / shapefile — tipicamente uma camada de saída por layer)
  e para futuras **operações espaciais** (filtro por área, interseção, proximidade) sobre o
  conjunto salvo.

Por isso o armazenamento é **espacial desde o início**: ver §2 (PostGIS + GeoDjango).

### Fontes de dados

Toda a aplicação se apoia em três bases da PMSP. Cada uma alimenta um dos apps de domínio:

1. **Logradouros** — `codlog` (código exato) + nome oficial.
   Como o usuário pode digitar o nome de muitas formas, geramos **variações** de escrita do nome
   apontando para o mesmo `codlog` (ex.: `AV PAULISTA` / `Avenida Paulista` / `Av. Paulista` →
   mesmo codlog).
2. **Endereços fiscais** — número de contribuinte + `codlog` + endereço por escrito + metadados.
   Como o endereço por escrito reaproveita o nome do logradouro, ganha **variações análogas**: o
   mesmo endereço fiscal é registrado com cada variação do nome da sua rua.
3. **Lotes (números de contribuinte)** — id do polígono geográfico + metadados do lote (tipo:
   fiscal, municipal etc.). **Código exato, sem variação.** Os metadados alimentam a busca
   detalhada.

Inicialmente as bases serão extraídas dos dados públicos do GeoSampa, mas posteriormente serão usados os dados internos do MDSF (em ambos os casos trata-se de geoservers consultados por meio de WFS).


### O fluxo da aplicação - UX

A interação parte de uma **barra de pesquisa única**. O sistema oferece dois caminhos de entrada
— **busca simples** e **busca detalhada** — e um único destino: o mapa.

**Busca simples.** O usuário digita o que quiser na barra única: nome de rua, endereço completo,
codlog ou número de contribuinte. A aplicação usa **regex** para fazer o roteamento e inferir o
tipo da consulta (se é logradouro, lote ou endereço). Identificado o tipo, é feito uma busca com match exato para trazer sugestões a cada keyup (por exemplo, começou a digitar o número do contribuinte 001.002 - e parou aqui - aí trago 5 contribuintes que começam com essa numeração como sugestão, o mesmo valeria para os endereços da "Rua Direita, 1..."). Caso a pessoa clique em uma das sugestões, essa sugestão é inputada como match. Caso não selecione nenhum sugestão, é feito o match com base na regra abaixo:

**Regra para matching:** códigos (`codlog`, número de contribuinte) são identificadores
exatos — match direto. Texto livre (nome de rua, endereço por extenso) passa pela base de
variações e o match é feito com fuzzy string match.

Os desfechos possíveis da inferência:

- **Endereço** → geocodificar (resultado: **ponto**);
- **Codlog** ou apenas **nome da rua** → resolver logradouro (resultado: **linha**);
- **Número de contribuinte** → encontrar imóvel (resultado: **polígono** do lote);
- O **endereço digitado corresponde exatamente** ao endereço fiscal de um imóvel no cadastro →
  *pop-up* pergunta ao usuário: geocodificar como **ponto** (geocodificação partindo do polígono
  do lote, portanto um cálculo um pouco diferente do caso "endereço solto") ou retornar o
  **polígono do lote** em si.

**Busca detalhada.** O usuário diz explicitamente o que está digitando, preenchendo campos
segmentados (tipo de logradouro / nome / número para endereço; número de contribuinte para lote).
Sem inferência por regex — o tipo já é dado.

**Saída.** Em ambos os caminhos, o resultado é renderizado em um mapa **Leaflet** (que consome o
serviço **WMS do GeoSampa**) com a geometria correspondente: **ponto** para endereço geocodificado,
**linha** para logradouro, **polígono** para lote.

**Salvar no projeto (requer login).** A partir de um resultado renderizado no mapa, o usuário
autenticado pode **salvar** aquele item em um de seus projetos (ou criar um projeto novo na hora).
Visitantes anônimos veem o resultado normalmente, mas a ação de salvar dispara o fluxo de login. Ao
reabrir um projeto, todos os seus itens são renderizados no mapa, e o usuário pode **adicionar**
novos itens (geocodificando mais elementos) ou **remover** itens existentes.

---

## 2. Stack Tecnológica

| Camada            | Tecnologia                       | Versão de referência (jun/2026)          |
|-------------------|----------------------------------|------------------------------------------|
| Backend           | Django + GeoDjango (`contrib.gis`)| 6.x                                      |
| Autenticação      | `django.contrib.auth`            | (built-in do Django)                     |
| Runtime           | Python                           | 3.14                                     |
| Banco de dados    | PostgreSQL + **PostGIS**         | desde a fase inicial                     |
| Driver do banco   | `psycopg` (psycopg **3**)        | última estável                           |
| Hipermídia        | HTMX                             | 2.x                                      |
| Mapa              | Leaflet                          | 1.9.x                                    |
| Estilo            | Tailwind CSS + DaisyUI           | Tailwind 4.x + DaisyUI 5.x               |
| Contratos de dados| Pydantic                         | 2.x                                      |
| API REST          | Django-Ninja                     | última estável                           |
| HTTP client       | requests                         | última estável (sem async nesta fase)    |
| Geoprocessamento  | GEOS / GDAL / PROJ (via GeoDjango)| conforme exigido pelo GeoDjango          |

> **PostGIS desde o início (não há fase SQLite).** O armazenamento de geometrias e as operações
> espaciais (reprojeção, interseção, export) exigem um backend espacial. A escolha é **PostGIS**,
> com `ENGINE = "django.contrib.gis.db.backends.postgis"`. O ambiente precisa das bibliotecas de
> sistema **GEOS, GDAL e PROJ** (dependências do GeoDjango) e do **PostGIS** habilitado no banco
> (`CREATE EXTENSION postgis;`).

> **Driver `psycopg` v3, não psycopg2.** Projeto novo em Django 6 usa **psycopg 3**. O pacote PyPI
> chama-se `psycopg` (não existe `psycopg3`); instala-se com `pip install "psycopg[binary]"`. Não é
> preciso configurar o driver no `ENGINE` — o Django usa o `psycopg` instalado automaticamente.

> **Tailwind 4 + DaisyUI 5:** o Tailwind 4 descobre templates **exclusivamente** via diretivas
> `@source` no CSS de entrada. Toda nova pasta de templates precisa ser declarada lá. DaisyUI
> entra como `@plugin "daisyui";`. Inicialmente durante o desenvolvimento podemos usar o CDN para simplificar, mas quando for dar deploy precisa compilar e minificar.

---

## 3. Princípios de Arquitetura (inegociáveis)

A arquitetura segue a divisão em aplicativos do Django, mas a **lógica de negócio vive fora deles**,
na camada `services/`. Três regras estruturam tudo:

### 3.1 HATEOAS via HTMX
- **Todas** as rotas Django retornam *partial templates* HTML.
- O frontend **não consome JSON via JavaScript**. Padrões de SPA/React são **vedados**.
- **Única exceção:** a futura API REST provida pelo Django-Ninja.
- A interatividade nasce de atributos HTMX e de JS estritamente local ao Leaflet.

### 3.2 Models como camada de persistência apenas
- Django Models cuidam **exclusivamente** de validação de persistência e mapeamento relacional.
- Com o GeoDjango, isso inclui os **campos geométricos** (`PointField`, `LineStringField`,
  `PolygonField`, `GeometryField`): eles são **persistência espacial**, e por isso são legítimos no
  model. O que **não** entra no model é a **lógica espacial** (reprojeção, interseção, filtro por
  área, export): isso é regra de negócio e mora em `services/`.
- **Nenhuma lógica de negócio** em models, managers ou signals. Roteamento, matching,
  geocodificação, reprojeção, **consultas espaciais** e integração externa pertencem a `services/`.
  As *queries* espaciais são montadas pelo domínio (que constrói o `QuerySet` espacial), não
  expostas como métodos de model/manager.

### 3.3 Isolamento rigoroso entre camadas
```
        ┌──────────────── Django ────────────────┐
Request → views (orquestração) → services/ (domínio) → models (persistência)
        └→ templates/partials HTMX (resposta) ←──────────────────────────────┘
```
O **Django ocupa as duas pontas**: é ele quem recebe o request, **orquestra** o fluxo (chama o
domínio, decide o que fazer com o retorno), **serve as views** renderizando os *partials* HTMX como
resposta, **e** persiste via ORM. A camada `services/` é a única parte que **não** é Django — é onde
mora a lógica de negócio.

Os papéis, então:
- **Interface + orquestração (Django: views + templates).** Traduz request → DTO, chama o domínio,
  escolhe o *partial* e responde com HTML. **Sem lógica de negócio** — orquestrar é decidir o quê
  chamar e o que devolver, não implementar a regra.
- **Domínio (`services/`).** Toda a lógica. **Não importa** views, requests nem objetos de interface
  do Django.
- **Persistência (Django Models).** Validação de persistência e mapeamento relacional (incluindo
  campos geométricos do GeoDjango), nada além (ver §3.2).

Regras de fronteira:
- A orquestração chama o domínio; o domínio chama persistência e integrações.
- A comunicação com o domínio se dá por **DTOs Pydantic** — nunca por `request`, `QueryDict` ou
  dicionários soltos.
- **Autorização é orquestração.** Exigir login e restringir um projeto ao seu dono é decisão de
  acesso, resolvida nas views (ex.: `login_required`, checagem de propriedade). O domínio recebe o
  usuário/projeto **já resolvidos** via DTO e não conhece `request` nem sessão.

---

## 4. Fluxo de Desenvolvimento (como trabalhar neste projeto)

**O app é desenvolvido em partes, nunca de uma vez.** Não saia implementando o sistema inteiro.
Cada iteração de desenvolvimento é guiada por um **arquivo de SPEC** — e nenhum código é escrito
sem uma SPEC correspondente. Veja a SKIll @.claude/SKILLS/specs/SKILL.md sobre como escrever e como usar SPECS. AS SPECS moram em SPECS/ .

---

## 5. Estrutura Sugerida

No nível mais alto, o projeto se organiza em sete blocos:

- **`config/`** — projeto Django (settings, urls de topo, asgi/wsgi). Sem lógica de domínio.
  Habilita `django.contrib.gis` e `django.contrib.auth` em `INSTALLED_APPS` e configura o backend
  PostGIS.
- **`apps/`** — aplicativos Django (interface + persistência). Finos: views, models, urls,
  templates próprios e *management commands*.
- **`services/`** — camada de domínio (toda a lógica). **Não depende do Django.**
- **`data/`** — dados versionados na **raiz do projeto** (dicionários e mapeamentos que o domínio
  e os scripts consultam, a começar pelo dicionário de variações por tipo de logradouro).
- **`templates/`** — templates globais e *partials* HTMX por app.
- **`static/`** — pipeline único de Tailwind/DaisyUI (na raiz para centralizar a compilação).
  `STATICFILES_DIRS` aponta para a saída do build.
- **`SPECS/`** — especificações de desenvolvimento, organizadas por épico (ver §4).

A organização fina dentro de cada bloco é decidida no código, seguindo os princípios deste
documento.

---

## 6. Aplicativos Django (`apps/`)

Apps são **magros** (thin), mas é neles que mora a **orquestração**: roteamento, views que traduzem o
request, chamam o domínio e devolvem *partials*, models de persistência e *management commands*.
Toda **regra de negócio** é delegada a `services/` — orquestrar (decidir o quê chamar e o que
responder) não é implementar a regra.

A autenticação usa o **`django.contrib.auth`** built-in; um app fino `accounts` cuida apenas das
*views* de login/logout/registro e dos *partials* correspondentes (sem regra de negócio). O CRUD de
projetos e itens salvos vive no app `projects`.

| App                  | O que persiste                                                                | Responsabilidade                                                       |
|----------------------|-------------------------------------------------------------------------------|------------------------------------------------------------------------|
| `core`               | —                                                                             | Home, layout base, integra os componentes na UX.                       |
| `accounts`           | — (usa o `User` do `contrib.auth`)                                            | Views de login/logout/registro; *partials* de sessão. Sem regra.       |
| `search`             | — (ou histórico, se necessário)                                               | Barra única; aciona o roteamento e renderiza sugestões assíncronas.    |
| `logradouro_matcher` | Logradouro (`codlog`, nome oficial, tipo, título) e grau de certeza do match. | Views da busca de logradouro → resultado: **linha**.                   |
| `address_geocoder`   | Endereço fiscal + resultado da geocodificação (geometria **ponto**; FK logradouro). | Views da geocodificação; trata o *pop-up* de endereço fiscal exato → resultado: **ponto**. |
| `lote_matcher`       | Lote (número de contribuinte, id de polígono, tipo: fiscal / municipal / …).  | Views da busca de lote → resultado: **polígono**. Metadados alimentam a busca detalhada. |
| `projects`           | **Projeto** (dono = FK `User`, nome, timestamps), **Layer** (FK projeto, nome, cor, tipo de geometria) e **ItemDeLayer** (FK layer, geometria, metadados de origem). | Views do CRUD de projetos, layers e itens; aciona o domínio de projetos e os exports. |
| `mapping`            | — (config do WMS pode ser settings/constante)                                 | Partial do Leaflet que recebe a geometria e renderiza sobre o WMS GeoSampa. |

**Sobre os models geométricos.** Os resultados deixam de ser efêmeros: a geometria é persistida com
**campos do GeoDjango**. O `address_geocoder` guarda um `PointField` (não mais `x`/`y` soltos). Em
`projects`, a hierarquia é **Projeto → Layer → ItemDeLayer**: o **Layer** guarda `nome`, `cor` de
display e o **tipo de geometria** da camada (ponto / linha / polígono); o **ItemDeLayer** guarda a
geometria em si num **`GeometryField` genérico**, mais metadados de proveniência (o que originou o
item: endereço, codlog, contribuinte) para reexibição e export. O `GeometryField` é genérico no
nível da coluna, mas o **layer é homogêneo**: a regra "um item só entra num layer cujo tipo bate com
a sua geometria" é validada no domínio (§7.3) e **pode ser reforçada por `CheckConstraint`** no banco
(ex.: `GeometryType(geom) = layer.tipo`). O **CRS de armazenamento é fixado** (ver §7.3).

**Lembrete:** o app **orquestra** (views), guarda **o que** persiste (models) e responde com HTML;
o **como** da regra de negócio está em `services/`.

---

## 7. Camada de Serviços (`services/`)

Diretório raiz que isola toda a lógica. **Não depende do Django** (exceto utilitários
explicitamente neutros e os objetos geométricos/funções espaciais do `django.contrib.gis.geos` /
`gis.db.models.functions`, que são neutros em relação à interface). Testável de forma independente.
Dividida em quatro subcamadas:

### 7.1 `utils/`
Funções utilitárias de escopo geral, sem domínio: padrões de regex para o roteamento da busca
simples e a **função única de normalização de texto** (uppercase + remoção de
acentos). Qualquer matching textual usa essa mesma função em tempo de preparação de dados e em
tempo de consulta. Duplicar essa regra é o erro que mais quebra esse tipo de sistema.


### 7.2 `integrations/`
Comunicação com sistemas externos — prioritariamente a conexão com WFS e WMS (inicialmente GeoSampa posteriormente MDSF, mas ambos são geoservers que implementam WFS). Contratos de dados
definidos com **modelos Pydantic**. Classes executoras (clients) e modelos de contrato são
**expostos no `__init__.py`** do módulo, para que o resto do sistema importe pelo nível superior
sem alcançar caminhos internos. Erros de rede/HTTP são encapsulados em exceções próprias; o
domínio não lida com detalhes do `requests`.

### 7.3 `domain/`
A **lógica de negócio**: roteamento da busca simples, matching dos três tipos de entidade
(logradouro, endereço, lote), geocodificação, tratamento geoespacial **e a lógica de projetos**.
Todo I/O via **DTOs Pydantic**. Regras estruturantes:

- **Match exato vs. match com variação.** Códigos (`codlog`, número de contribuinte) são
  resolvidos por **lookup direto** na base. Texto livre (nome de rua, endereço por extenso)
  consulta a **base de variações** preparada pelos scripts e faz o match com fuzzy string match.
- **Sugestões assíncronas** (durante a digitação) consultam estruturas cacheadas via uma
  interface de lookup — barato e desacoplado do ORM. A implementação atual é um dict em memória;
  troca futura para Redis fica isolada nessa interface.
- O **caso especial de endereço fiscal exato** (entrada bate exatamente com o cadastro de
  imóveis) é tratado no módulo de endereço: o domínio sinaliza a ambiguidade (ponto vs.
  polígono); a UI resolve via *pop-up*.
- **Projeção (CRS):** os dados do GeoSampa costumam estar em SIRGAS 2000 / UTM 23S
  (EPSG:31983); o Leaflet renderiza em WGS84 (EPSG:4326). **As geometrias são armazenadas em um
  CRS canônico fixo** e a **reprojeção é centralizada no domínio**, usando as ferramentas do
  GeoDjango (objetos `GEOS`/`GDAL` e funções espaciais como `Transform`) — nunca reprojeção
  manual. Confirmar o CRS de origem ao integrar; definir o CRS canônico como constante única.
- **Lógica de projetos e layers.** O domínio concentra as regras de projetos, layers e itens
  salvos: criar/compor o `ItemDeLayer` a partir de um resultado de geocodificação/match e **validar
  a homogeneidade do layer** — a regra inegociável de que **a geometria do item tem de bater com o
  tipo declarado do layer** (um layer de linhas só aceita linhas, etc.). Também é do domínio, quando
  aplicável, as **operações espaciais** sobre o conjunto salvo (filtro por área, interseção,
  proximidade). O CRUD em si é orquestrado pelas views, mas a regra (o que é um item válido, a
  homogeneidade do layer, como o item se relaciona com a busca de origem) é do domínio.
  **Autorização não é responsabilidade do domínio** (ver §3.3): o domínio recebe usuário/projeto/layer
  já resolvidos.
- **Export.** A geração de **geopackage / geojson / shapefile** a partir de um projeto é lógica de
  domínio, apoiada no **GDAL** (via GeoDjango). Como cada layer é homogêneo, o mapeamento natural é
  **um layer do projeto → uma camada no arquivo de saída**. Recebe um DTO com o projeto/layers e
  devolve o artefato; a view apenas serve o arquivo resultante.

### 7.4 `scripts/`
Rotinas com **execução apartada do runtime web**: cargas das três bases oficiais (logradouros,
endereços fiscais, lotes) e preparação das estruturas de cache consumidas pelo domínio. A geração
de variações de escrita roda sobre **logradouros e endereços fiscais** — não sobre lotes, cujo
identificador é exato. Consome a normalização de `utils/` para que
as chaves geradas casem com as chaves buscadas em tempo de execução. Os dados são salvos em `data/` na raiz do projeto.

Scripts são funções/classes puras: a entrada de programa é via *management commands* (§8).
**Nunca** rodam durante o ciclo de request/response.

> Os **dados versionados** (dicionários e mapeamentos, como o de variações por tipo de logradouro:
> `AV` → `AVENIDA`, `AV.`, `AVN.`; `RUA` → `R.`; etc.) ficam em **`data/` na raiz do projeto** — não
> dentro de `services/`. São dados, não código, e crescem conforme novos formatos aparecem na base.

---

## 8. Scripts como Management Commands

Os scripts se integram ao Django como **comandos customizados do `manage.py`**, em
`management/commands/` do app de domínio mais próximo do dado. O comando é **fino**: só faz
parsing de argumentos, chama o script em `services/scripts/` e dá feedback no `stdout`. A lógica/regra de negócio não fica no comando, fica no script. Padrão:

```python
from django.core.management.base import BaseCommand
from services.scripts import load_logradouros


class Command(BaseCommand):
    help = "Carrega os logradouros oficiais da PMSP a partir do GeoSampa."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--source", type=str, default="geosampa")

    def handle(self, *args: object, **options: object) -> None:
        total = load_logradouros.run(source=options["source"])
        self.stdout.write(self.style.SUCCESS(f"{total} logradouros carregados."))
```

A preparação inicial segue uma ordem natural: cargas das bases oficiais primeiro, depois a
geração das variações (que depende das duas primeiras), por fim o *refresh* do cache de lookup.

---

## 9. Fluxo de Dados (ponta a ponta)

```
Usuário digita na barra (apps/search)
   │  (HTMX hx-trigger="keyup changed delay:300ms")
   ▼
services.domain — regex de roteamento identifica o tipo da entrada
   │
   ├─ ENDEREÇO    → address_geocoder → domínio de endereço
   │                                  ├─ endereço fiscal EXATO no cadastro?
   │                                  │     └─ partial com pop-up: ponto ou polígono?
   │                                  └─ caso comum: geocodificação → PONTO
   │
   ├─ LOGRADOURO  → logradouro_matcher → domínio de logradouro
   │                                   └─ resolve codlog → LINHA
   │
   └─ LOTE        → lote_matcher → domínio de lote
                                   └─ resolve nº contribuinte → POLÍGONO

A view do app correspondente:
   • monta DTOs Pydantic
   • chama services.domain (consultando lookup cacheado quando aplicável)
   • renderiza partial HTML (sugestões durante digitação; resultado ao final)

Resultado final ─────────────────────────────────────────────────────────────
   ▼
hx-post → apps/mapping → partial do Leaflet recebe a geometria
                        (ponto / linha / polígono) e renderiza sobre o WMS GeoSampa
   │
   └─ [usuário autenticado] ação "salvar no projeto"
          ▼
      apps/projects (view) → exige login (orquestração/autorização)
          • usuário escolhe projeto + layer de destino (ou cria layer: nome + cor;
            tipo do layer = tipo da geometria do resultado)
          • monta DTO do item a partir do resultado
          • chama services.domain (lógica de projetos: valida homogeneidade do
            layer e compõe o ItemDeLayer)
          • persiste via ORM (GeometryField, no CRS canônico)
          • responde partial: layer/projeto atualizado

Reabrir projeto (apps/projects) ──────────────────────────────────────────────
   • lista os layers do projeto (do dono logado) e seus itens
   • renderiza as geometrias no mapa (apps/mapping) com a cor de cada layer,
     reprojetando para 4326 na saída
   • permite criar/remover layers, adicionar itens (volta ao fluxo de busca) e
     remover itens (CRUD em projeto / layer / item)
   • permite exportar (services.domain → GDAL → geopackage / geojson / shapefile;
     um layer por camada de saída)
```

A **busca avulsa é pública** (sem login) até a etapa de renderização no mapa. **Salvar** é o ponto
em que o login é exigido. A **busca detalhada** pula a etapa de roteamento — o tipo é dado pelo
formulário — e entra direto no módulo de domínio correspondente.

---

## 10. Estilo de Código

Princípios que regem **como** o código é escrito, complementando os princípios de arquitetura (§3).

### 10.1 Responsabilidade única
Cada classe ou função tem **uma só razão para mudar** (*Single Responsibility Principle*).
Se uma peça acumula responsabilidades, ela é dividida. Esse princípio é prioritário no projeto. ALém disso, os módulos representam diferentes **domínios** do projeto. Um mesmo módulo não pode atacar dois domínios simultaneamente (por exemplo lotes E logradouros - são coisas diferentes). O domínio de **projetos** também é separado dos domínios de busca/matching.

### 10.2 Nomenclatura
- **Classes:** `PascalCase` (ex.: `WfsClient`, `LogradouroMatcher`).
- **Funções e métodos:** `snake_case` (ex.: `resolve_codlog`, `build_lookup`).
- **Constantes:** `UPPER_CASE` (ex.: `DEFAULT_SRID`, `GEOSAMPA_WFS_URL`).

### 10.3 Constantes
- **Locais ao módulo:** definidas em `UPPER_CASE` nas linhas iniciais do arquivo, **logo após os
  imports**.
- **Vindas de configuração:** lidas via **Pydantic Settings** e, no início do módulo (após os
  imports), **reextraídas para constantes** `UPPER_CASE` locais — o resto do módulo referencia a
  constante, não o objeto de settings.

### 10.4 Classes: callables, composição e contratos
- Sempre que couber, classes são **callables**: implementam `__call__` como ponto de entrada da sua
  responsabilidade.
- A integração entre classes é por **composição**. **Herança é exceção rara**, reservada a quando
  se quer definir uma **interface** (ex.: `ABC`) — e nesse caso a SPEC dirá explicitamente.
- Classes recebem **DTOs de input** e retornam **DTOs de output**, deixando o contrato de dados
  explícito em ambas as pontas (Pydantic — ver §3.3 e §11).

### 10.5 Estamos usando python 3.14 - nao use futures
Já estamso na versao mais atual do python, não é para usar from __future__ !

---

## 11. Convenções de Código

- **Tipagem integral:** *type annotations* em **todo o código Python** (não se aplica a templates
  HTML/HTMX). `mypy` deve passar limpo.
- **Pydantic nas fronteiras:** contratos de integração e DTOs de domínio são modelos Pydantic.
- **Normalização única:** uppercase + remoção de acentos vivem em um único lugar em
  `services/utils/`, usados em qualquer matching textual (preparação e consulta).
- **CRS canônico único:** o SRID de armazenamento é definido como **constante única** e toda
  reprojeção passa pelo ponto centralizado do domínio (GeoDjango), nunca espalhada/manual.
- **Geometria pelo GeoDjango:** persistência espacial usa os campos do `django.contrib.gis`;
  manipulação de geometria usa objetos `GEOS`/`GDAL`. Nada de parsing manual de WKT/coordenadas
  fora desse caminho.
- **Autorização nas views:** login e propriedade de projeto são resolvidos na orquestração
  (`login_required` e checagem de dono), nunca no domínio.
- **Dados ≠ código:** dicionários e mapeamentos versionados ficam em **`data/` na raiz do
  projeto**, não dentro de `services/`.
- **Imports do domínio:** importar de `services.integrations` e `services.domain` pelos
  `__init__.py` expostos; não alcançar submódulos internos.
- **Management commands sem lógica:** só parsing + chamada ao script + feedback.
- **JavaScript no frontend (restrito):** só **JS puro** (sem TypeScript/frameworks), em **dois
  casos**: (1) funções de *callback* que escutam eventos do **HTMX** (`htmx.on(...)`); e (2) funções
  utilitárias para se comunicar com o objeto `map` do **Leaflet**. Não implementa regra de negócio,
  não mantém estado nem consome JSON para montar UI — no máximo serializa dados (ex.: geometria do
  mapa) e envia ao backend via POST do HTMX. Validação e persistência ficam sempre no servidor.
- **Templates:** *partials* prefixados com `_`; páginas estendem `base.html`.
- **HTMX:** `hx-trigger` com `delay`/`changed` na busca simples; alvos e *swaps* explícitos.
- **Estilização:** Tailwind + DaisyUI; toda nova pasta de templates registrada com `@source` no
  CSS de entrada.

---

## 12. Comandos de Desenvolvimento

**Gerenciador de dependências: `uv`.** Todo o ciclo de vida do projeto (instalar, adicionar e
remover pacotes, rodar comandos dentro do ambiente) passa pelo `uv`. Não use `pip` diretamente nem
crie venvs manualmente — o `uv` cuida disso.

```bash
# Ambiente Python — instalar dependências do projeto
uv sync
# Bibliotecas de sistema exigidas pelo GeoDjango: GEOS, GDAL, PROJ
# Banco: PostgreSQL com PostGIS habilitado -> CREATE EXTENSION postgis;

# Banco (PostGIS desde a fase inicial)
uv run python manage.py migrate

# Pipeline de dados (apartado do runtime web): cargas → variações → cache
uv run python manage.py <cada management command>

# Build do CSS (Tailwind 4 + DaisyUI 5) — terminal separado, em watch
npx @tailwindcss/cli -i static/src/input.css -o static/dist/output.css --watch

# Servidor de desenvolvimento
uv run python manage.py runserver

# Qualidade
uv run mypy .
uv run ruff check .
uv run python manage.py test
```

---

## 13. Política de Testes

**Testes unitários são desenvolvidos sob demanda explícita, nunca como parte automática da implementação de uma SPEC.**

O fluxo correto é:
1. Escrever (ou receber) a SPEC.
2. Implementar o código da SPEC.
3. Validar a implementação (smoke test manual, mypy, etc.).
4. **Só então**, quando o desenvolvedor pedir explicitamente, escrever os testes unitários.

**Nunca** escreva testes junto com a implementação da SPEC sem ser solicitado. Isso se aplica mesmo quando a SPEC traz "Notas de teste" — essa seção é um guia para *quando os testes forem pedidos*, não uma ordem para criá-los imediatamente.

> **Razão:** no desenvolvimento assistido por IA, gerar testes antes da validação humana desperdiça tokens e ciclos de revisão. O desenvolvedor precisa primeiro confirmar que a implementação está correta; os testes vêm depois, para fixar esse comportamento.

---

## 14. Regras Críticas — checklist antes de codar

Princípios inegociáveis. Cada item remete à seção onde o detalhe vive — consulte-a em vez de
tratar este checklist como a especificação completa.

- [ ] **Há uma SPEC** guiando a iteração, e ela **reaproveita** o que já existe por composição em vez
      de reimplementar? (§4)
- [ ] **HATEOAS via HTMX:** as respostas são *partials* HTML e o frontend **não** consome JSON via JS?
      (única exceção: a API REST futura) (§3.1)
- [ ] **Lógica de negócio em `services/`** — e cada camada no seu papel: views orquestram (incluindo
      autorização), models só persistem, commands só disparam? (§3)
- [ ] A comunicação com o domínio se dá por **DTOs Pydantic**, nas duas pontas? (§3.3, §10.4)
- [ ] **Responsabilidade única**, e um módulo **não cruza domínios** distintos? (§10.1)
- [ ] **Composição** como regra de integração; herança só para definir interface, quando a SPEC pedir?
      (§10.4)
- [ ] Todo o **tratamento geoespacial** está centralizado e segue os contratos do projeto — geometria
      via GeoDjango, CRS canônico único, reprojeção e consultas espaciais no domínio? (§3.2, §7.3)
- [ ] Qualquer **matching textual** usa a **mesma** normalização em preparação e em consulta? (§7.1)
- [ ] **Dado versionado fica em `data/`** (na raiz), separado do código? (§11)
- [ ] **Tipagem integral** e `mypy` limpo? (§11)
- [ ] As **convenções de código** (nomenclatura, constantes, contratos expostos no `__init__.py`,
      templates/`@source`) foram seguidas? (§10, §11)

---

## 14. Roadmap por Fase

A fase 1 é construída na ordem abaixo — cada item se apoia no anterior:

| Ordem | Entrega                                                                                      |
|-------|----------------------------------------------------------------------------------------------|
| 1     | **Busca de logradouros** com *fuzzy string search* (e o roteamento por regex que a aciona).  |
| 2     | **Geocodificação de endereços** (interpolação do número sobre o logradouro → ponto).         |
| 3     | **Busca de lotes** por número de contribuinte → polígono.                                     |
| 4     | **Caso extremo do endereço fiscal exato:** quando a entrada bate exatamente com um endereço fiscal, oferecer (via *pop-up*) busca de lote **ou** geocodificação especial — que parte do **polígono do lote**, não da interpolação do número no logradouro. |
| 5     | **Autenticação de usuário** (`django.contrib.auth`): registro, login, logout.                |
| 6     | **Projetos + layers + persistência dos resultados:** criar projeto e layers (nome + cor + tipo de geometria), **salvar** itens geocodificados no layer adequado, **reabrir** o projeto e fazer CRUD em projeto / layer / item. Cada layer é homogêneo. Busca avulsa segue pública; salvar exige login. |

Transversais à fase 1: os apps em pé (incluindo `accounts` e `projects`), banco **PostGIS** com
geometrias armazenadas no CRS canônico, pipeline de cargas + preparação de cache via *management
commands*, e o mapa Leaflet + WMS GeoSampa renderizando ponto / linha / polígono.

| Depois | Entrega                                                                                     |
|--------|---------------------------------------------------------------------------------------------|
| Fase 2 | **Export** dos itens de um projeto em geopackage / geojson / shapefile (via GDAL).           |
| Fase 2 | **Busca por batches** (planilhas pré-formatadas por tipo), gravando resultados em projeto.   |
| Fase 2 | **Operações espaciais** sobre os itens salvos (filtro por área, interseção, proximidade).    |
| Fase 2 | **Digitalização manual no mapa** (modo projeto): o usuário desenha pontos/linhas/polígonos no Leaflet e salva no layer adequado. JS utilitário extrai a geometria e dispara HTMX; o backend valida e persiste via GeoDjango (ver regra de JS em §11). Detalhes na SPEC. |
| Fase 2 | API REST com Django-Ninja.                                                                   |
| —      | Cache de lookup migra de dict em memória para Redis, isolado atrás da interface.            |