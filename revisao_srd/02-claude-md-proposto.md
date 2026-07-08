# Proposta de novo CLAUDE.md

> **Este arquivo é a versão completa proposta.** O CLAUDE.md atual não foi alterado.
> Tudo abaixo da linha horizontal é o conteúdo sugerido para substituir o CLAUDE.md.

---

# CLAUDE.md — DIMAP GeoCoder

Arquivo de contexto para agentes de IA e desenvolvedores. Define **domínio, decisões de
arquitetura, fluxo do sistema, stack e regras inegociáveis**. O *como fazer* de cada tema
recorrente vive nas **skills** (`.claude/skills/` — índice no §8); o planejamento vive em
`SPECS/` (incluindo `SPECS/ROADMAP.md`).

---

## 1. Visão Geral

**DIMAP GeoCoder** é um app web de geocodificação **de uso interno** (escala de dezenas de
usuários, não milhares — dimensione decisões de infra para esse porte) sobre os dados oficiais de
logradouros, lotes fiscais e endereços fiscais da Prefeitura de São Paulo (PMSP). O usuário digita em uma **barra de
pesquisa única**; o sistema infere o tipo da consulta (regex de roteamento), oferece sugestões a
cada keyup e devolve o resultado em um mapa Leaflet sobre o WMS do GeoSampa:

| Entrada | Resolução | Geometria no mapa |
|---|---|---|
| Nome ou código de logradouro (`codlog`) | matcher de logradouro | **linha** |
| Endereço (rua + número) | geocodificação (interpolação sobre o logradouro) | **ponto** |
| Número de contribuinte | lote no cadastro do IPTU | **polígono** |
| Endereço que bate **exatamente** com um endereço fiscal | pop-up: ponto (geocodificação a partir do polígono) **ou** polígono do lote | ponto ou polígono |

**Regra de matching (estruturante):** códigos (`codlog`, contribuinte) são identificadores
exatos → lookup direto. Texto livre (nome de rua, endereço) → base de **variações de escrita**
(ex.: `AV PAULISTA` / `Avenida Paulista` → mesmo codlog) + **fuzzy match**. Ver skills
`normalize-text` e `fuzzy-matcher`.

**Fontes de dados** (três bases da PMSP, consumidas via WFS de geoserver — GeoSampa hoje, MDSF
depois): logradouros (codlog + nome oficial, com variações), endereços fiscais (contribuinte +
codlog + endereço escrito, com variações herdadas do nome da rua) e lotes (contribuinte + polígono
+ metadados; código exato, sem variação).

**Usuários e projetos (épico futuro).** A busca avulsa é e continuará **pública**. O sistema terá
autenticação (`django.contrib.auth`) e **Projetos**: espaços nomeados por usuário onde resultados
são salvos de forma durável, organizados em **layers** (nome + cor + **um único tipo de
geometria** — layer nunca mistura tipos). O login só é exigido ao **salvar**. Projetos são a base
dos exports (geopackage/geojson/shapefile, um layer → uma camada de saída) e de operações
espaciais futuras.

### Estado atual (atualizar quando mudar)

- **Implementado:** roteamento da busca única com sugestões, matching de logradouro/lote/endereço
  (incl. fuzzy fallback e caso do endereço fiscal exato), geocodificação das três geometrias,
  mapa Leaflet + WMS com o design system aplicado.
- **Ainda não existe:** `accounts`, `projects`, models de persistência de domínio (os dados de
  busca vivem em **parquet em `data/` + catálogos cacheados em memória**, com warmup eager). O
  PostGIS já está configurado (engine + extensão) e recebe os models quando o épico de projetos
  começar.
- A fonte de verdade do que está implementado é o front-matter `implementado:` das SPECs.

---

## 2. Stack Tecnológica

| Camada | Tecnologia | Referência |
|---|---|---|
| Backend | Django + GeoDjango (`contrib.gis`) | 6.x |
| Autenticação | `django.contrib.auth` (built-in) | — |
| Runtime | Python | 3.14 |
| Banco | PostgreSQL + **PostGIS** | engine `django.contrib.gis.db.backends.postgis` |
| Driver | `psycopg` (v3 — não psycopg2; o Django o usa automaticamente) | última estável |
| Hipermídia | HTMX | 2.x |
| Mapa | Leaflet | 1.9.x |
| Estilo | Tailwind CSS 4 + DaisyUI 5 (design system "Onsen de Inverno" — skill `componentes-frontend`) | — |
| Contratos | Pydantic | 2.x |
| API REST (futura) | Django-Ninja | última estável |
| HTTP client | requests (sem async nesta fase) | última estável |
| Geoprocessamento | GEOS / GDAL / PROJ via GeoDjango | — |
| Dependências | **uv** (nunca pip direto / venv manual) | — |
| Testes | **pytest** (marker `integration` para testes com dados reais) | — |

> O ambiente exige as libs de sistema GEOS/GDAL/PROJ e `CREATE EXTENSION postgis;` no banco.
> Tailwind 4 só descobre templates via `@source` no CSS de entrada — toda nova pasta de templates
> precisa ser declarada lá (detalhes e armadilhas de build: skill `componentes-frontend` §8).

---

## 3. Princípios de Arquitetura (inegociáveis)

A lógica de negócio vive fora dos apps Django, na camada `services/`. Três regras estruturam tudo:

### 3.1 HATEOAS via HTMX
- **Todas** as rotas Django retornam *partial templates* HTML.
- O frontend **não consome JSON via JavaScript**. Padrões de SPA/React são **vedados**.
- **Única exceção:** a futura API REST do Django-Ninja.
- A interatividade nasce de atributos HTMX e de JS estritamente local ao Leaflet.

### 3.2 Models como camada de persistência apenas
- Models cuidam **exclusivamente** de validação de persistência e mapeamento relacional —
  incluindo os **campos geométricos** do GeoDjango (`PointField`, `PolygonField`…), que são
  persistência espacial legítima.
- **Nenhuma lógica de negócio** em models, managers ou signals. Lógica espacial (reprojeção,
  interseção, filtro por área, export) é regra de negócio e mora em `services/`. Queries
  espaciais são montadas pelo domínio, não expostas como métodos de model/manager.

### 3.3 Isolamento rigoroso entre camadas
```
        ┌──────────────── Django ────────────────┐
Request → views (orquestração) → services/ (domínio) → models (persistência)
        └→ templates/partials HTMX (resposta) ←──────────────────────────────┘
```
- **Interface + orquestração (views/templates):** traduz request → DTO, chama o domínio, escolhe
  o partial. Orquestrar é decidir o quê chamar e o que devolver — nunca implementar a regra.
- **Domínio (`services/`):** toda a lógica. Não importa views, requests nem objetos de interface
  do Django (os objetos `GEOS`/`GDAL` e funções espaciais do `contrib.gis` são neutros e
  permitidos).
- **Persistência (models):** ver §3.2.
- A comunicação com o domínio se dá por **DTOs Pydantic** — nunca `request`, `QueryDict` ou
  dicionários soltos.
- **Autorização é orquestração:** `login_required` e checagem de dono são das views; o domínio
  recebe usuário/projeto já resolvidos via DTO.

---

## 4. Fluxo de Desenvolvimento

**O app é desenvolvido em partes, nunca de uma vez.** Cada iteração é guiada por um arquivo de
**SPEC** em `SPECS/` — nenhum código é escrito sem SPEC correspondente.

**Regra de workflow inegociável:** escrever a SPEC **antes** de implementar e **aguardar a
aprovação explícita do usuário**. Nunca começar a codar com a SPEC não apresentada/aprovada.

- Como escrever, versionar e patchear SPECs: skill `write-spec` (`.claude/skills/specs/`).
- Patches de SPEC são **append-only** — nunca editam o corpo da SPEC.
- Para saber o que já existe, consulte o front-matter `implementado:` das SPECs.
- O roadmap por fases vive em `SPECS/ROADMAP.md`.

---

## 5. Estrutura do Projeto

- **`config/`** — projeto Django (settings, urls de topo, asgi/wsgi). Sem lógica de domínio.
  Configuração sensível vem de `.env` (ver `.env.example`).
- **`apps/`** — aplicativos Django, **magros**: views, urls, templates próprios, management
  commands (e models, quando a persistência de domínio nascer).
- **`services/`** — camada de domínio. **Não depende do Django.** (§6)
- **`data/`** — dados versionados e artefatos do pipeline (parquets das bases, dicionários de
  variações). Dados ≠ código: mapeamentos versionados ficam aqui, nunca em `services/`.
- **`templates/`** — templates globais e partials por app.
- **`static/`** — pipeline único Tailwind/DaisyUI (`src/input.css` → `dist/output.css`).
- **`SPECS/`** — especificações por épico + roadmap.
- **`tests/`** — testes pytest espelhando `services/`.

### Apps Django (estado atual)

| App | Responsabilidade |
|---|---|
| `core` | Home, layout base, middlewares transversais (incl. `PydanticValidationMiddleware` — skill `pydantic-validation-errors`). |
| `search` | Barra única: view roteadora + seções de sugestão por tipo de entrada. |
| `logradouro_matcher` | Busca/sugestão de logradouro (nome ou codlog). |
| `lote_matcher` | Busca/sugestão de lote por número de contribuinte. |
| `address_geocoder` | Fluxo de endereço (seleção, caso do endereço fiscal exato). |
| `logradouro_geocoder` | Resolve a geometria **linha** do logradouro escolhido. |
| `lote_geocoder` | Resolve a geometria **polígono** do lote escolhido. |
| `mapping` | Partial do Leaflet: recebe a geometria e renderiza sobre o WMS (skill `leaflet-map`). |
| `accounts` *(futuro)* | Views de login/logout/registro sobre o `contrib.auth`. Sem regra de negócio. |
| `projects` *(futuro)* | CRUD de Projeto → Layer → ItemDeLayer; exports. Layer guarda nome, cor e tipo de geometria; ItemDeLayer guarda a geometria (`GeometryField`) + metadados de proveniência. A homogeneidade do layer é validada no domínio (§6.3), reforçável por `CheckConstraint`. |

**Padrão matcher/geocoder:** o *matcher* identifica **qual** entidade o usuário quer (sugestões,
desambiguação); o *geocoder* resolve **a geometria** da entidade escolhida. São apps distintos
porque são responsabilidades distintas (§7.1).

---

## 6. Camada de Serviços (`services/`)

### 6.1 `utils/`
Escopo geral, sem domínio: normalização única de texto (skill `normalize-text` — **qualquer**
matching textual usa a mesma função na preparação dos dados e na consulta), fuzzy matching
(skill `fuzzy-matcher` — nunca chamar rapidfuzz direto), cache/catálogos de lookup, IO.

### 6.2 `integrations/`
Comunicação com sistemas externos — geoservers WFS/WMS (GeoSampa hoje, MDSF depois). Contratos
Pydantic; clients e modelos **expostos no `__init__.py`** (importar sempre pelo nível superior);
erros de rede encapsulados em exceções próprias — o domínio não vê `requests`. Uso: skills
`wfs-fetcher` (e futura `wms-fetcher`).

### 6.3 `domain/`
A lógica de negócio: roteamento da busca, matching das três entidades, geocodificação,
tratamento geoespacial e (futuramente) a lógica de projetos. Todo I/O via DTOs Pydantic.
Regras estruturantes:

- **Match exato vs. variação** — ver §1 (regra de matching).
- **Sugestões assíncronas** consultam estruturas cacheadas via **interface de lookup** —
  desacoplada do ORM. Os **catálogos in-memory** (parquets de `data/` + warmup eager) são o
  **desenho definitivo, não um provisório**: app de uso interno (escala pequena), dados read-only
  e reconstruíveis a partir dos parquets, e os caminhos de fuzzy/varredura exigem o corpus dentro
  do processo. **Redis foi avaliado e descartado (2026-07-07)** — não elimina nenhum modo de
  falha atual e adiciona uma dependência externa. Se um dia houver pressão de memória
  (multi-worker/multi-máquina), a primeira alternativa para lookups exatos/prefixo é o
  **PostgreSQL já na stack**. Todo consumo passa pela interface do catálogo — nunca ler
  `data/*.parquet` direto em view ou domínio (skill futura `catalogos-lookup`).
- **Projeção (CRS):** GeoSampa opera em SIRGAS 2000/UTM 23S (EPSG:31983); o Leaflet renderiza em
  WGS84 (EPSG:4326). O **CRS canônico de armazenamento é constante única** e toda reprojeção é
  **centralizada no domínio** via GeoDjango (`Transform`, objetos GEOS/GDAL) — nunca manual.
- **Homogeneidade de layer (futuro):** a geometria de um item tem de bater com o tipo declarado
  do layer — validada no domínio; autorização nunca é responsabilidade do domínio (§3.3).
- **Export (futuro):** GDAL via GeoDjango; um layer do projeto → uma camada no arquivo de saída.

### 6.4 `scripts/`
Rotinas **apartadas do runtime web**: cargas das bases oficiais, geração de variações (sobre
logradouros e endereços fiscais — nunca sobre lotes, cujo código é exato) e preparação dos caches
de lookup, salvando em `data/`. Ordem natural do pipeline: **cargas → variações → refresh do
cache**. Scripts são funções/classes puras; a entrada é via management command: **comando fino —
só parsing de argumentos, chamada ao script e feedback no stdout**. Nunca rodam durante
request/response.

---

## 7. Estilo e Convenções de Código

### 7.1 Princípios
- **Responsabilidade única** (prioritário): cada classe/função tem uma razão para mudar; um
  módulo não cruza domínios distintos (lotes ≠ logradouros ≠ projetos).
- **Classes callables por composição:** `__call__` é a porta de entrada e é **fino** — com mais
  de uma etapa, delega a um método `pipeline` que orquestra métodos-passo (`_montar_request`,
  …). Herança é exceção rara, só para interface (ABC) e quando a SPEC pedir. Classes recebem
  DTOs de input e retornam DTOs de output.
- **Nomenclatura:** `PascalCase` classes, `snake_case` funções, `UPPER_CASE` constantes.
  Termos de domínio em **português** (`roteamento_busca`, `nome_camada`) — não "traduzir".
- **Constantes:** no topo do módulo, logo após os imports. Valores de configuração são lidos via
  Pydantic Settings e **reextraídos para constantes locais** — o módulo referencia a constante.
- Python 3.14: **não usar `from __future__ import ...`**.

### 7.2 Convenções
- **Tipagem integral** em todo Python; `mypy` limpo.
- **Pydantic nas fronteiras:** DTOs de domínio e contratos de integração.
- **Validação de entrada nas views:** construir o DTO e deixar o `PydanticValidationMiddleware`
  interceptar `ValidationError` (nunca `try/except` na view) — skill `pydantic-validation-errors`.
- **Geometria pelo GeoDjango**; CRS canônico único; reprojeção centralizada (§6.3). Nada de
  parsing manual de WKT/coordenadas.
- **Imports pelo `__init__.py` exposto** de `services.integrations`/`services.domain`;
  **`__init__.py` só reexporta — nunca implementa.**
- **JavaScript restrito:** só JS puro, em dois casos — callbacks de eventos HTMX e utilitários do
  Leaflet. Sem regra de negócio, sem estado, sem montar UI a partir de JSON (skill `leaflet-map`).
- **Templates:** partials prefixados com `_`; páginas estendem `base.html`.
- **HTMX:** `hx-trigger` com `delay`/`changed` na busca; alvos e swaps explícitos (skill `htmx`).
- **Estilização:** design system "Onsen de Inverno" — skill `componentes-frontend` (obrigatória
  para qualquer trabalho de UI); referência de componentes na skill `daisyui`.
- **Management commands sem lógica** (§6.4).
- **Dados ≠ código:** dicionários/mapeamentos versionados em `data/`.

---

## 8. Skills do projeto (`.claude/skills/`)

Consulte a skill **antes** de trabalhar no tema — elas carregam o *como* que este arquivo não
repete:

| Tema | Skill |
|---|---|
| Escrever/versionar/patchear SPECs | `write-spec` (`specs/`) |
| Normalizar texto para matching | `normalize-text` (**sempre**, nunca criar outra função) |
| Similaridade/ranking de strings | `fuzzy-matcher` (**sempre**, nunca rapidfuzz direto) |
| Erros de validação Pydantic em views | `pydantic-validation-errors` |
| Consumir WFS (ingestão GeoSampa/MDSF) | `wfs-fetcher` |
| Instanciar mapa/renderizar geometria | `leaflet-map` |
| Qualquer UI/template/estilo | `componentes-frontend` + `daisyui` |
| Sintaxe/comportamento HTMX | `htmx` |
| Smoke test de views após implementar | `test-django-views` |

---

## 9. Comandos de Desenvolvimento

```bash
# Dependências (sempre via uv)
uv sync

# Banco e ambiente: PostgreSQL+PostGIS via docker-compose; config em .env (ver .env.example)
docker compose up -d
uv run python manage.py migrate

# Pipeline de dados (apartado do runtime): cargas → variações → cache
uv run python manage.py <management command>   # ver apps/*/management/commands/

# CSS (Tailwind 4 + DaisyUI 5) — terminal separado, em watch
npx @tailwindcss/cli -i static/src/input.css -o static/dist/output.css --watch

# Servidor de desenvolvimento
uv run python manage.py runserver

# Qualidade
uv run mypy .
uv run ruff check .
uv run pytest                    # unitários
uv run pytest -m integration     # testes com dados reais
```

---

## 10. Política de Testes

**Testes unitários só sob demanda explícita do desenvolvedor — nunca como parte automática da
implementação de uma SPEC** (mesmo quando a SPEC traz "Notas de teste": aquilo é guia para quando
os testes forem pedidos). O fluxo é: SPEC aprovada → implementação → **validação** (smoke test
manual via skill `test-django-views`, mypy, ruff) → testes, se e quando pedidos.

---

## 11. Regras Críticas — checklist antes de codar

- [ ] Há **SPEC aprovada pelo usuário** guiando a iteração, que **reaproveita** o que existe por
      composição? (§4)
- [ ] Respostas são **partials HTML** (HATEOAS/HTMX); nenhum JSON consumido por JS? (§3.1)
- [ ] Lógica de negócio em `services/`; views só orquestram (incl. autorização); models só
      persistem; commands só disparam? (§3)
- [ ] Comunicação com o domínio por **DTOs Pydantic** nas duas pontas? (§3.3)
- [ ] **Responsabilidade única** e nenhum módulo cruzando domínios? (§7.1)
- [ ] Tratamento geoespacial centralizado: GeoDjango, CRS canônico único, reprojeção no domínio?
      (§6.3)
- [ ] Matching textual usando a normalização única e o fuzzy matcher do projeto? (skills)
- [ ] A skill do tema foi consultada? (§8)
- [ ] Tipagem integral, mypy e ruff limpos? (§7.2)
