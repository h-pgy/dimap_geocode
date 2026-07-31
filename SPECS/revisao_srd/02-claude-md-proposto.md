# Proposta de novo CLAUDE.md

> **STATUS (2026-07-31): adotada.** Esta proposta — com o tipo de entidade no router de ações e o
> Perfil herdando de `contrib.auth` (cargo + unidade) — **já foi instalada como o `CLAUDE.md` da
> raiz**. A partir daqui, edite o `CLAUDE.md`, não este arquivo, que fica só como registro do
> raciocínio da migração (as "Notas de migração" no fim seguem úteis para entender o porquê de cada
> remoção).

> **Este arquivo é a versão completa proposta.** O CLAUDE.md atual não foi alterado.
> Tudo entre as duas linhas horizontais é o conteúdo sugerido para substituir o CLAUDE.md.
> Depois da proposta há uma seção de **notas de migração**.
>
> Revisões: 2026-07-31 — incorpora o escopo maduro (plataforma de processos da DIMAP, não
> geocodificador), o princípio Busca × Ações, o rigor de design system/Atomic Design, e remove
> conteúdo que envelhece (lista de apps, índice de skills, roadmap).

---

# CLAUDE.md — DIMAP GeoCoder

Arquivo de contexto para agentes de IA e desenvolvedores. Define **o que o sistema é, a stack, e
os padrões de arquitetura e código inegociáveis** — com a justificativa de cada decisão.

O ***como fazer*** de cada tema recorrente **não está aqui**: vive nas **skills**
(`.claude/skills/`). Antes de trabalhar num tema, verifique se há skill para ele e consulte-a. A
especificação de cada iteração vive em `SPECS/`.

---

## 1. O que é o sistema

O DIMAP GeoCoder **não é um geocodificador** — é uma **plataforma de uso interno da DIMAP que
modela processos de trabalho cujo input inicial é uma localização no território urbano** de São
Paulo. A geocodificação é a porta de entrada da plataforma, não o produto.

O fluxo tem três camadas encadeadas:

**1. Localização.** Uma **barra de pesquisa única** onde o usuário encontra de forma fluida a
entidade territorial. O sistema infere o tipo da entrada (regex de roteamento), oferece sugestões
a cada keyup e resolve a geometria, renderizada num mapa Leaflet sobre o WMS do GeoSampa.

| Entrada | Resolução | Geometria |
|---|---|---|
| Nome ou código de logradouro (`codlog`) | matcher de logradouro | **linha** |
| Endereço (rua + número) | geocodificação por interpolação sobre o logradouro | **ponto** |
| Número de contribuinte | lote no cadastro do IPTU | **polígono** |
| Endereço que bate **exatamente** com um endereço fiscal | o imóvel cadastrado no IPTU | **polígono** |

**2. Entidade territorial.** O que a busca devolve **não é uma geometria — é um objeto de domínio
tipado**: logradouro, lote, lote condominial, endereço, quadra fiscal. Cada tipo tem sua
**ontologia** própria (os atributos que fazem sentido para aquele tipo). A geometria é um atributo
do objeto, não o objeto.

**3. Gaveta.** Resolvida a entidade, abre-se a gaveta, com dois tipos de conteúdo — e a distinção
entre eles é **estruturante** (§3.5):

- **Informações** — dados públicos derivados da ontologia do objeto. **Sem login.** Sempre presentes.
- **Ações** — **Atos Administrativos** que recebem *a entidade + sua localização* como input.
  **Exigem login e autorização por perfil** (cargo × unidade da DIMAP).

Exemplos de ação: um usuário da DIMAP-1 (avaliação) localiza um imóvel e dispara **amostragem de
ofertas** (busca ofertas próximas com características similares — o processo de amostragem para
avaliação); ou emite uma **certidão de lançamento** (PDF atestando que aquele imóvel está lançado
no IPTU sob determinado contribuinte). Mesmo objeto buscado, ações diferentes conforme o perfil.

**Cada processo da DIMAP vira uma ação nova.** A plataforma é feita para crescer por adição de
ações, e boa parte do §3 existe para que essa adição **não toque no núcleo de busca**.

**Escala.** Uso interno: dezenas de usuários, não milhares. Isso é premissa de projeto e justifica
boa parte das decisões abaixo — quando houver dúvida entre robustez operacional e simplicidade,
**a simplicidade vence**.

---

## 2. Stack

| Camada | Tecnologia | Referência |
|---|---|---|
| Backend | Django + GeoDjango (`contrib.gis`) | 6.x |
| Runtime | Python | 3.14 |
| Banco | PostgreSQL + **PostGIS** | engine `django.contrib.gis.db.backends.postgis` |
| Driver | `psycopg` v3 (não psycopg2; o Django o resolve sozinho) | última estável |
| Consulta analítica | **DuckDB** — sobre os parquets de `data/` | última estável |
| Autenticação | `django.contrib.auth` — o **Perfil** herda dele, com models de **cargo** e **unidade** relacionados (§3.5) | — |
| Hipermídia | HTMX | 2.x |
| Mapa | Leaflet | 1.9.x |
| Estilo | Tailwind 4 + daisyUI 5 — design system "Onsen de Inverno" (§3.4) | — |
| Contratos | Pydantic | 2.x |
| HTTP client | `requests` (sem async nesta fase) | última estável |
| Geoprocessamento | GEOS / GDAL / PROJ via GeoDjango | — |
| Dependências | **uv** — nunca `pip` direto nem venv manual | — |
| Testes | **pytest** (marker `integration` para testes com dados reais) | — |
| API REST *(futura)* | Django-Ninja | — |

> **LIDAR / nuvens de pontos 3D** entrarão no escopo do projeto. As ferramentas específicas para
> lidar com pontos 3D **serão definidas posteriormente**, em SPEC própria — não improvise uma
> escolha de biblioteca antes disso.

> Ambiente: libs de sistema GEOS/GDAL/PROJ e `CREATE EXTENSION postgis;` no banco. Configuração
> sensível vem de `.env` (ver `.env.example`); banco via `docker compose`.
> Tailwind 4 descobre templates **só** via `@source` no CSS de entrada — toda nova pasta de
> templates precisa ser declarada lá.

---

## 3. Princípios de Arquitetura (inegociáveis)

### 3.1 HATEOAS via HTMX
**Todas** as rotas Django retornam *partials* HTML. O frontend **não consome JSON via
JavaScript**; padrões de SPA/React são **vedados**. Única exceção: a futura API REST do
Django-Ninja. A interatividade nasce de atributos HTMX e de JS estritamente local ao Leaflet.

*Por quê:* o estado da aplicação é o estado do servidor. Manter uma cópia dele no navegador
duplicaria a regra de negócio e a autorização em duas linguagens — inaceitável num sistema cuja
autorização define competência administrativa (§3.5). Para dezenas de usuários internos, uma SPA
adiciona uma stack inteira de build e sincronização sem resolver problema algum que exista aqui.

### 3.2 Models são camada de persistência apenas
Models cuidam **exclusivamente** de validação de persistência e mapeamento relacional — incluindo
os campos geométricos do GeoDjango, que são persistência espacial legítima. **Nenhuma lógica de
negócio** em models, managers ou signals. Lógica espacial (reprojeção, interseção, filtro por área,
export) é regra de negócio e mora em `services/`. Queries espaciais são montadas pelo domínio, não
expostas como métodos de model/manager.

*Por quê:* regra em model é regra que só roda com banco em pé e só é testável via Django. Signals,
em especial, escondem efeito colateral do ponto de chamada — o oposto do que se quer quando o
efeito é um ato administrativo auditável.

### 3.3 Isolamento rigoroso entre camadas
```
        ┌──────────────── Django ────────────────┐
Request → views (orquestração) → services/ (domínio) → models (persistência)
        └→ templates/partials HTMX (resposta) ←──────────────────────────────┘
```
- **Views/templates (orquestração):** traduzem request → DTO, chamam o domínio, escolhem o partial.
  Orquestrar é decidir *o quê* chamar e *o que* devolver — nunca implementar a regra.
- **`services/` (domínio):** toda a lógica. **Não importa** views, requests nem objetos de
  interface do Django (objetos `GEOS`/`GDAL` e funções espaciais do `contrib.gis` são neutros e
  permitidos).
- **Models:** ver §3.2.
- A comunicação com o domínio se dá por **DTOs Pydantic** — nunca `request`, `QueryDict` ou dicts
  soltos.
- **Autorização é orquestração:** acontece na view; o domínio recebe usuário/perfil **já
  resolvidos** via DTO.

*Por quê:* o domínio é onde mora o conhecimento sobre território e processos da DIMAP — a parte
mais cara e mais durável do sistema. Amarrá-lo ao ciclo request/response o tornaria descartável
junto com qualquer troca de interface, e impediria reusá-lo em management commands e (futuramente)
na API REST.

### 3.4 Front-end: design system e Atomic Design
Toda a interface é construída **dentro** do design system do projeto ("Onsen de Inverno"), seguindo
**Atomic Design**. **Não existe componente fora do design system.** Ao criar qualquer peça de UI:

- Se ela é um **átomo** novo, **nasce como átomo no design system** — nunca como marcação solta num
  template.
- Se é uma **molécula**, é **composta pelos átomos já existentes**. Se faltar um átomo, cria-se o
  átomo novo **no design system** (aderente aos seus tokens e escalas) e a molécula o compõe.
- O mesmo vale para organismos e níveis acima: cada nível é composição do nível imediatamente
  inferior.
- Nenhum componente introduz cor, espaçamento, tipografia, sombra ou animação **fora dos tokens do
  design system**. Não se resolve falta de peça com CSS ad hoc.

*Por quê:* a gaveta muda de conteúdo a cada ação nova (§3.5), e cada processo da DIMAP traz suas
telas. Se cada ação puder inventar seu próprio HTML/CSS, a interface diverge processo a processo e
o custo de manutenção cresce com o número de ações — exatamente o que o §3.5 evita no backend.
Atomic Design é o que faz uma tela nova ser **montagem de peças existentes** em vez de invenção, e
o que mantém a coerência visual sem depender de disciplina individual.

### 3.5 Ações: app próprio, rota protegida, contrato e router
- **Cada ação é um app Django próprio, com suas rotas** — nunca dentro de um app de busca. A lógica
  vive em submódulos próprios de `services/domain/` (relação app ↔ submódulo é **N:N**).
- **As rotas de ação são sempre protegidas.** Rota aberta é exceção que só existe quando declarada
  explicitamente na SPEC.
- **Cada ação declara um contrato**, em código, que a define e diz **qual perfil de usuário pode
  executá-la**. O **Perfil** é um model próprio que **herda do `django.contrib.auth`**, com models
  relacionados de **cargo** e **unidade** da DIMAP — é a combinação deles que define a competência.
  Há um **perfil padrão** para o que basta estar autenticado. O mapeamento perfil → ação é
  **código, não configuração de runtime**.
- **Um router recebe o perfil do usuário + o tipo da entidade territorial**, lê as ações inscritas
  e devolve **apenas as liberadas** — uma ação só se oferece a quem pode executá-la **e** sobre o
  tipo de entidade em que ela opera. É ele quem monta as **gavetas** — haverá **mais de um tipo de
  gaveta**.
- **O router filtra, a rota decide.** Não renderizar o botão é UX; a autorização real acontece na
  rota, a cada execução.
- Ação é **ato administrativo**: exige autenticação e sua execução é **registrada** (quem, com qual
  perfil, sobre o quê, quando). Informação pública da ontologia do objeto **não é ação** e não
  exige login.
- **A busca nunca conhece ação alguma.** A dependência é de mão única: a ação consome o resultado da
  busca via DTO.
- **Ações são síncronas por padrão**; fila só se a SPEC de uma ação específica justificar.

*Por quê:* a plataforma cresce por adição de processos. Contrato + router fazem "adicionar um
processo" ser **inscrever um app**, sem tocar no núcleo de busca — que, do contrário, apodreceria
linearmente com o número de processos. Manter o mapeamento perfil → ação em código deixa a
competência administrativa versionada e revisável em code review, e não editável numa tabela sem
rastro; e o registro da execução é o que permite saber *quem* praticou o ato e *se podia*.

---

## 4. Fluxo de Desenvolvimento

**O app é desenvolvido em partes, nunca de uma vez.** Cada iteração é guiada por uma **SPEC** em
`SPECS/` — nenhum código é escrito sem SPEC correspondente.

**Regra inegociável:** escrever a SPEC **antes** de implementar e **aguardar a aprovação explícita
do usuário**. Nunca começar a codar com a SPEC não apresentada ou não aprovada.

- Patches de SPEC são **append-only** — nunca editam o corpo da SPEC.
- **A fonte de verdade sobre o que já existe é o front-matter `implementado:` das SPECs.** Consulte
  antes de assumir que algo está ou não implementado.

---

## 5. Estrutura do Projeto

| Diretório | Conteúdo |
|---|---|
| `config/` | projeto Django (settings, urls de topo, asgi/wsgi). Sem lógica de domínio. |
| `apps/` | apps Django — a camada de interface. **Magros.** |
| `services/` | camada de domínio. **Não depende do Django.** (§6) |
| `data/` | dados versionados e artefatos do pipeline (parquets, dicionários de variações). |
| `templates/` | templates globais e partials por app. |
| `static/` | pipeline Tailwind/daisyUI (`src/input.css` → `dist/output.css`). |
| `SPECS/` | especificações por épico. |
| `tests/` | pytest, espelhando `services/`. |

**Dados ≠ código:** dicionários e mapeamentos versionados ficam em `data/`, nunca dentro de
`services/`.

### `apps/` × `services/`

- **`services/` é o núcleo do sistema:** onde ocorre a **modelagem do domínio** e onde se definem
  as **portas e adaptadores**. Em `integrations/` estão os adaptadores para o mundo externo; em
  `domain/`, o **conhecimento de domínio da DIMAP vertido em código**.
- **`apps/` é onde esse conhecimento é consultado** para implementar **casos de uso** específicos —
  incluindo a checagem de autorização de quem os executa, quando couber.
- A relação entre app e submódulo de `services/` é **N:N**, não espelhamento.

Dois padrões de organização em vigor:

- **matcher × geocoder.** O *matcher* identifica **qual** entidade o usuário quer; o *geocoder*
  resolve **a geometria** da entidade escolhida. São responsabilidades distintas — e a
  identificação é reusável por ações que não precisam de geometria.
- **um app por ação.** Cada processo da DIMAP tem o seu (§3.5).

---

## 6. Camada de Serviços (`services/`)

### 6.1 `utils/`
Escopo geral, sem domínio: **normalização única de texto** (**qualquer** matching textual usa a
mesma função na preparação dos dados e na consulta — duplicar essa regra é o erro que mais quebra
este tipo de sistema), **fuzzy matching** (nunca chamar rapidfuzz direto), cache e IO.

### 6.2 `integrations/`
**Toda fonte de dado externa entra por aqui** — geoservers WFS/WMS (GeoSampa hoje, MDSF depois),
mas também *scrapers*, conexões diretas a bancos de terceiros e APIs. Cada fonte é um módulo
próprio, com contratos Pydantic; clients e modelos **expostos no `__init__.py`**; erros de rede e
de protocolo encapsulados em exceções próprias — o domínio nunca vê `requests`, driver de banco nem
HTML de scraping.

*Por quê:* o domínio raciocina sobre território e processos, não sobre transporte. Isolar a fonte
aqui é o que permite trocar GeoSampa por MDSF, ou um scraper por uma API oficial, sem tocar em
regra de negócio.

### 6.3 `domain/`
O conhecimento de domínio da DIMAP vertido em código, em **submódulos por domínio**: roteamento da
busca, matching de cada entidade, geocodificação, geometria — e um submódulo por ação (§3.5). Todo
I/O via DTOs Pydantic. Um submódulo **nunca cruza domínios distintos**.

### 6.4 `scripts/`
Rotinas **apartadas do runtime web**: cargas das bases oficiais, geração de variações de escrita
(sobre logradouros e endereços fiscais — nunca sobre lotes, cujo código é exato) e preparação dos
caches, salvando em `data/`. Ordem do pipeline: **cargas → variações → refresh do cache**.

Scripts são funções/classes puras; a entrada é um **management command fino** — só parsing de
argumentos, chamada ao script e feedback no stdout, sem lógica. **Nunca rodam durante
request/response.**

---

## 7. Estilo e Convenções de Código

### 7.1 Princípios
- **Responsabilidade única** (prioritário): cada classe/função tem **uma** razão para mudar. E um
  **módulo não cruza domínios** distintos — lote ≠ logradouro ≠ quadra ≠ ação.
- **Classes callables, integradas por composição.** `__call__` é a porta de entrada e é **fino**:
  com mais de uma etapa, delega a um método `pipeline` que orquestra métodos-passo
  (`_montar_request`, `_feature_para_segmento`, …). Empilhar passos dentro do `__call__` é
  proibido. **Herança é exceção rara**, só para definir interface (ABC) e quando a SPEC pedir.
- **DTOs nas duas pontas:** classes recebem DTO de input e retornam DTO de output.
- **Nomenclatura:** `PascalCase` classes, `snake_case` funções, `UPPER_CASE` constantes. Estrutura
  em inglês, **termos de domínio em português** (`roteamento_busca`, `nome_camada`) — não
  "traduzir" nomes de domínio.
- **Constantes** no topo do módulo, após os imports. Valores de configuração são lidos via settings
  e **reextraídos para constantes locais** — o módulo referencia a constante, não o objeto de
  settings.
- Python 3.14: **não usar `from __future__ import ...`**.

### 7.2 Convenções
- **Tipagem integral** em todo Python; `mypy` e `ruff` limpos.
- **Pydantic nas fronteiras:** DTOs de domínio e contratos de integração.
- **Validação de entrada nas views:** construir o DTO e deixar o `PydanticValidationMiddleware`
  interceptar o `ValidationError` — **nunca `try/except` na view**.
- **Geometria pelo GeoDjango**: os CRS vêm da orquestração (settings → DTO), nunca hardcoded no
  domínio, e toda reprojeção é centralizada no domínio — nada de cálculo ou parsing manual de
  WKT/coordenadas.
- **Imports pelo `__init__.py` exposto** de `services.integrations` / `services.domain`;
  **`__init__.py` só reexporta — nunca implementa.**
- **JavaScript restrito:** só JS puro, em dois casos — callbacks de eventos HTMX e utilitários do
  Leaflet. Sem regra de negócio, sem estado, sem montar UI a partir de JSON. Validação e
  persistência sempre no servidor.
- **Templates:** partials prefixados com `_`; páginas estendem `base.html`.
- **HTMX:** `hx-trigger` com `delay`/`changed` na busca; alvos e swaps explícitos.
- **UI:** nenhum componente fora do design system e do Atomic Design (§3.4).

---

## 8. Comandos

```bash
uv sync                                   # dependências (sempre via uv)
docker compose up -d                      # PostgreSQL + PostGIS; config em .env
uv run python manage.py migrate

uv run python manage.py <command>         # pipeline de dados — ver apps/*/management/commands/

npx @tailwindcss/cli -i static/src/input.css -o static/dist/output.css --watch
uv run python manage.py runserver

uv run mypy .
uv run ruff check .
uv run pytest                             # unitários
uv run pytest -m integration              # com dados reais
```

---

## 9. Política de Testes — TDD

**O desenvolvimento é guiado por testes.** O ciclo de cada iteração:

1. A **SPEC define os testes** — poucos e essenciais — e é aprovada pelo usuário **com eles**.
2. Os **testes são escritos primeiro** e falham.
3. Implementa-se até passarem.
4. Valida-se o conjunto (smoke test da view quando houver interface, `mypy`, `ruff`).

*Por quê:* o erro mais caro do desenvolvimento assistido por IA não é código malfeito — é código
plausível que resolve o problema errado. A SPEC diz o que fazer em prosa; o teste torna isso
**executável e verificável antes** de existir implementação. E como os testes são aprovados junto
com a SPEC, a validação humana acontece **antes** do código, não depois.

Regras que tornam isso sustentável:

- **Poucos testes, bem escolhidos.** O teste existe para fixar **comportamento observável**: um por
  critério de aceite, mais os casos de borda que realmente quebram. Não se testa getter, DTO
  trivial nem variação que só repete outro caso, e **não se persegue cobertura**. Excesso de teste
  engessa refactor e queima ciclo de revisão — o oposto do que o TDD deveria comprar.
- **Testa-se comportamento, não implementação.** Teste que quebra quando o código é refatorado sem
  mudança de comportamento é passivo, não ativo.
- **O alvo natural é `services/`** — domínio puro, sem Django, barato de testar (é para isso que
  serve o isolamento do §3.3). Views entram quando o que se quer fixar é o contrato HTTP/partial.
- `pytest`; `tests/` espelha `services/`.

---

## 10. Checklist antes de codar

- [ ] Há **SPEC aprovada pelo usuário**, que **reaproveita** o que existe por composição? (§4)
- [ ] Os **testes da SPEC foram escritos antes** do código, e são **poucos e essenciais**? (§9)
- [ ] As respostas são **partials HTML**; nenhum JSON consumido por JS? (§3.1)
- [ ] Lógica em `services/`; views só orquestram; models só persistem; commands só disparam? (§3)
- [ ] Comunicação com o domínio por **DTOs Pydantic** nas duas pontas? (§3.3)
- [ ] Se mexe em UI: o componente está **no design system**, composto pelo nível inferior do Atomic
      Design, sem token novo fora dele? (§3.4)
- [ ] Se é ação: app próprio, **rota protegida**, contrato declarando o perfil, execução
      **registrada** — e a busca segue intocada? (§3.5)
- [ ] **Responsabilidade única**, e nenhum módulo cruzando domínios? (§7.1)
- [ ] Matching textual usando a normalização única e o fuzzy matcher do projeto? (§6.1)
- [ ] Geometria via GeoDjango, CRS vindo da orquestração, reprojeção centralizada? (§7.2)
- [ ] **A skill do tema foi consultada?**
- [ ] Tipagem integral, `mypy` e `ruff` limpos? (§7.2)

---

## Notas de migração (não fazem parte do CLAUDE.md)

**1. Conteúdo que sai do CLAUDE.md:**

| Sai | Destino |
|---|---|
| §9 antigo — diagrama ASCII "Fluxo de Dados ponta a ponta" | descartado: duplicava o §1 e já divergia do código |
| §14 antigo — "Roadmap por Fase" (e o bug das duas seções `## 14`) | **descartado** — já estava desatualizado e foi superado pelo escopo de plataforma; o que existe é rastreado pelo front-matter `implementado:` das SPECs |
| §6 antigo — tabela app a app | **descartada**: muda com frequência e divergia do real. `INSTALLED_APPS` é a fonte de verdade; o §5 documenta os *padrões* de organização (matcher/geocoder, um app por ação), que são o que de fato precisa ser sabido |
| §8 antigo — exemplo completo de management command | skill `management-commands` (rascunho em `skills_sugeridas/`) |
| Notas de setup de psycopg 3 / PostGIS | descartadas: setup one-shot, já realizado |
| Apêndice "Regra de workflow do usuário (memorizada)" | fundido no §4 |
| Índice de skills | **descartado** — ver item 2 |
| §1 "Fontes de dados" e "Entradas futuras" | **descartados.** As fontes passam a ser descritas onde de fato importam — `services/integrations` (§6.2), agora explícito de que **toda** fonte externa entra ali: WFS/WMS, scrapers, bancos de terceiros e APIs. Desenho no mapa e projetos/layers saem do CLAUDE.md — são escopo de SPEC |
| §6.3 — regra de match exato × fuzzy, catálogos em memória e projeção/CRS | **descartados por nível de abstração:** são decisões já implementadas e específicas de uma parte do sistema, não princípios que valham o custo de contexto em toda sessão. Catálogos já estão cobertos pela skill `catalogos-lookup` (que carrega inclusive a regra "nunca ler parquet direto") e o match exato × fuzzy pelas skills `fuzzy-matcher`/`normalize-text` + a futura `fluxo-busca`. **Projeção/CRS não tem skill** — ver item 7. O §6.3 fica com o que é abstrato: o que é o domínio, submódulos por domínio, DTOs nas fronteiras |

**2. Por que não há índice de skills.** As `description` das skills já entram no contexto do agente
em toda sessão; listá-las de novo no CLAUDE.md é duplicação de token sem ganho de descoberta. O
CLAUDE.md declara a **regra** ("nunca chamar rapidfuzz direto", "nunca ler parquet direto",
"nenhum componente fora do design system") e o cabeçalho instrui a procurar a skill do tema — a
skill certa é encontrada pela própria descrição. Se no futuro houver uma skill *sobre criar skills*
que exija registro central, esse índice volta com dono definido.

**3. Skills que citam o CLAUDE.md por número precisam ser ajustadas.** Quatro skills (`specs`,
`leaflet-map`, `test-django-views`, `wfs-fetcher`) referenciam seções por número, e a renumeração
quebra essas citações. O levantamento linha a linha, com a redação sugerida, está em
**`01-diagnostico.md` §8.2**. Regra geral: trocar a citação numérica pelo **nome da seção**
("princípios de arquitetura", "política de testes"), que sobrevive a renumerações futuras.

**4. Decisões que o novo documento registra pela primeira vez** — confirmadas com o usuário em
2026-07-31, e que precisam de SPEC própria antes de virarem código: a arquitetura de ações (§3.5) —
app próprio com rotas protegidas, contrato declarando o perfil autorizado, router que lê as ações
inscritas e monta as gavetas (haverá mais de um tipo), execução registrada, e a busca intocada —,
o rigor de design system/Atomic Design como princípio de arquitetura (§3.4), DuckDB na stack e
LIDAR/pontos 3D como escopo futuro com ferramental a definir.

**5. Pendência aberta pela remoção do §6.3: falta uma skill de geoprocessamento/CRS.** O que saiu
do CLAUDE.md — SIRGAS 2000/UTM 23S (EPSG:31983) do GeoSampa, WGS84 (EPSG:4326) do Leaflet, as
settings `MAP_INTERPOLATION_CRS`/`MAP_OUTPUT_CRS`, o uso de `Transform` e objetos GEOS/GDAL, e a
definição do CRS canônico quando a persistência de geometria entrar — **não tem hoje onde morar**.
A skill `leaflet-map` cobre só a renderização. Enquanto essa skill não existir, o CLAUDE.md mantém
a **regra** em §7.2 ("CRS vêm da orquestração, reprojeção centralizada no domínio, nada manual"),
mas os detalhes ficam sem registro — é a única perda real desta rodada de enxugamento.

**6. Mudança de política: TDD (§9).** A política anterior — "testes só sob demanda explícita, nunca
junto da SPEC" — está **revogada**. A skill `specs` já foi atualizada: "Notas de teste" virou
"**Testes (TDD)**", com instrução de listar **poucos testes essenciais** (~3 a 6 numa SPEC típica)
e o item de checklist correspondente. A skill `test-django-views` ainda precisa de ajuste de
enquadramento — o smoke test deixa de ser *a* validação e vira passo complementar à suíte definida
na SPEC (ver `01-diagnostico.md` §8.3).

**7. Correções pontuais aplicadas:** endereço que bate exatamente com endereço fiscal resolve para
**polígono** (o documento anterior descrevia um pop-up ponto-ou-polígono); caminho da skill de
SPECs corrigido; `manage.py test` → `pytest`; typos "imóvle"/"logradoro"/"estamso"; o CRS descrito
como settings via orquestração (o "CRS canônico de armazenamento" só existirá com a persistência de
geometria).
