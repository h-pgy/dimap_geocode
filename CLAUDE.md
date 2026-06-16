# CLAUDE.md — DIMAP GeoCoder

Arquivo de contexto para agentes de IA e desenvolvedores. Define **domínio, decisões de
arquitetura, fluxo do sistema, stack e regras inegociáveis** do projeto. Estruturas internas
(nomes de arquivos, organização fina de cada pacote) se acomodam conforme o código nasce e seguem
os princípios documentados aqui.

---

## 1. Visão Geral

**DIMAP GeoCoder** é um aplicativo web de geocodificação que opera sobre os dados oficiais de
logradouros, lotes fiscais e endereços fiscais da Prefeitura de São Paulo (PMSP). Converte
endereços em coordenadas geográficas e números de contribuinte em polígonos de lotes fiscais,
servindo como infraestrutura para localização de imóveis e logradouros.

### As três bases oficiais

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

**Regra de ouro de matching:** códigos (`codlog`, número de contribuinte) são identificadores
exatos — match direto. Texto livre (nome de rua, endereço por extenso) passa pela base de
variações.

### O fluxo central

A interação parte de uma **barra de pesquisa única**. O sistema oferece dois caminhos de entrada
— **busca simples** e **busca detalhada** — e um único destino: o mapa.

**Busca simples.** O usuário digita o que quiser na barra única: nome de rua, endereço completo,
codlog ou número de contribuinte. A aplicação usa **regex** para fazer o roteamento e inferir o
tipo da consulta **antes de qualquer outra coisa** — inclusive antes de sugerir resultados.
Identificado o tipo, a busca é direcionada ao domínio correspondente e as sugestões assíncronas
retornam já no contexto certo.

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

---

## 2. Stack Tecnológica

| Camada            | Tecnologia            | Versão de referência (jun/2026)          |
|-------------------|-----------------------|------------------------------------------|
| Backend           | Django                | 6.x                                      |
| Runtime           | Python                | 3.14                                     |
| Banco de dados    | SQLite                | fase inicial                             |
| Hipermídia        | HTMX                  | 2.x                                      |
| Mapa              | Leaflet               | 1.9.x                                    |
| Estilo            | Tailwind CSS + DaisyUI| Tailwind 4.x + DaisyUI 5.x               |
| Contratos de dados| Pydantic              | 2.x                                      |
| API REST          | Django-Ninja          | última estável                           |
| HTTP client       | requests              | última estável (sem async nesta fase)    |

> **Tailwind 4 + DaisyUI 5:** o Tailwind 4 descobre templates **exclusivamente** via diretivas
> `@source` no CSS de entrada. Toda nova pasta de templates precisa ser declarada lá. DaisyUI
> entra como `@plugin "daisyui";`.

---

## 3. Princípios de Arquitetura (inegociáveis)

A arquitetura segue a divisão em aplicativos do Django, mas a **lógica de negócio vive fora deles**,
na camada `services/`. Três regras estruturam tudo:

### 3.1 HATEOAS via HTMX
- **Todas** as rotas Django retornam *partial templates* HTML.
- O frontend **não consome JSON via JavaScript**. Padrões de SPA são **vedados**.
- **Única exceção:** a futura API REST provida pelo Django-Ninja.
- A interatividade nasce de atributos HTMX e de JS estritamente local ao Leaflet.

### 3.2 Models como camada de persistência apenas
- Django Models cuidam **exclusivamente** de validação de persistência e mapeamento relacional.
- **Nenhuma lógica de negócio** em models, managers ou signals. Roteamento, matching,
  geocodificação, reprojeção e integração externa pertencem a `services/`.

### 3.3 Isolamento rigoroso entre camadas
```
Interface (HTML / HTMX / views)  →  Domínio (services/)  →  Persistência (Django Models)
```
- A camada de interface chama o domínio; o domínio chama a persistência e integrações.
- O domínio **não importa** views, requests, nem objetos de interface do Django.
- A comunicação com o domínio se dá por **DTOs Pydantic** — nunca por `request`, `QueryDict` ou
  dicionários soltos.

---

## 4. Fluxo de Desenvolvimento (como trabalhar neste projeto)

**O app é desenvolvido em partes, nunca de uma vez.** Não saia implementando o sistema inteiro.
Cada iteração de desenvolvimento é guiada por um **arquivo de SPEC** — e nenhum código é escrito
sem uma SPEC correspondente.

### 4.1 Organização da pasta `SPECS/`
As specs são organizadas **por épicos** (recortes de produto/funcionalidade), **nunca espelhando a
divisão em apps** — a divisão em apps é detalhe de implementação e pode ser cruzada por um mesmo
épico. A pasta tem subpastas por épico:

```
SPECS/
├── <epico-a>/
│   ├── 001-<slug-da-spec>.md
│   └── 002-<slug-da-spec>.md
└── <epico-b>/
    └── 001-<slug-da-spec>.md
```

Uma única spec costuma tocar **vários apps** (ex.: uma spec do épico "busca de logradouros" mexe em
`apps/search`, `apps/logradouro_matcher`, `services/domain` e `services/scripts` ao mesmo tempo).
Isso é esperado: o épico é a unidade de valor; o app é onde o código acaba morando.

### 4.2 Como usar uma SPEC
- Toda nova funcionalidade começa por escrever (ou receber) uma SPEC no padrão de §4.3.
- A SPEC é a fonte de verdade da iteração: a implementação segue o que está nela.
- Snippets de código na SPEC são **direção sugerida**, não dogma — mas divergir deles exige razão
  explícita, e a divergência deve respeitar os princípios de arquitetura (§3).
- Referências a arquivos existentes na SPEC devem ser seguidas: editar o arquivo apontado, não
  recriar um paralelo.

### 4.3 Padrão do arquivo de SPEC
Cada SPEC é um `.md` com a estrutura abaixo:

````markdown
# SPEC <épico>/<nº> — <título curto>

## User story
Como <persona>, quero <objetivo>, para <valor/razão>.

## Critérios de aceite
- [ ] <condição observável de pronto>
- [ ] <condição observável de pronto>

## Contexto e decisões de arquitetura
<Em que camadas mexe (interface / domínio / persistência), quais princípios de §3 se aplicam,
por que esta abordagem. Fluxo resumido da funcionalidade.>

## Arquivos do projeto
**Existentes (editar):**
- `caminho/para/arquivo.py` — <o que muda>

**Novos (criar):**
- `caminho/para/novo_arquivo.py` — <responsabilidade>

## Snippets sugeridos
```python
# direção de implementação — adaptar conforme necessário, sem violar §3
```

## Fora de escopo
<O que esta SPEC explicitamente NÃO faz, para evitar avanço além da iteração.>

## Notas de teste
<O que precisa de teste; casos de borda relevantes.>
````

Regra prática: se uma SPEC está crescendo a ponto de tocar funcionalidades não relacionadas,
quebre em duas. Cada SPEC = uma iteração coesa e entregável.

---

## 5. Estrutura Sugerida

No nível mais alto, o projeto se organiza em sete blocos:

- **`config/`** — projeto Django (settings, urls de topo, asgi/wsgi). Sem lógica de domínio.
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

Apps são **finos**: roteamento, views que devolvem partials, models de persistência e *management
commands*. Toda decisão de negócio é delegada a `services/`. São **6 apps** (5 de domínio + a UX).

| App                  | O que persiste                                                              | Responsabilidade                                                       |
|----------------------|-----------------------------------------------------------------------------|------------------------------------------------------------------------|
| `core`               | —                                                                           | Home, layout base, integra os componentes na UX.                       |
| `search`             | — (ou histórico, se necessário)                                             | Barra única; aciona o roteamento e renderiza sugestões assíncronas.    |
| `logradouro_matcher` | Logradouro (`codlog`, nome oficial, tipo, título) e grau de certeza do match.| Views da busca de logradouro → resultado: **linha**.                  |
| `address_geocoder`   | Endereço fiscal + resultado da geocodificação (ponto `x`, `y`; FK logradouro).| Views da geocodificação; trata o *pop-up* de endereço fiscal exato → resultado: **ponto**. |
| `lote_matcher`       | Lote (número de contribuinte, id de polígono, tipo: fiscal / municipal / …).| Views da busca de lote → resultado: **polígono**. Metadados alimentam a busca detalhada. |
| `mapping`            | — (config do WMS pode ser settings/constante)                               | Partial do Leaflet que recebe a geometria e renderiza sobre o WMS GeoSampa. |

**Lembrete:** o app guarda **o que** persiste e **as views**; o **como** está em `services/`.

---

## 7. Camada de Serviços (`services/`)

Diretório raiz que isola toda a lógica. **Não depende do Django** (exceto utilitários
explicitamente neutros). Testável de forma independente. Dividida em quatro subcamadas:

### 7.1 `utils/`
Funções utilitárias de escopo geral, sem domínio: padrões de regex para o roteamento da busca
simples e — crítico — a **função única de normalização de texto** (uppercase + remoção de
acentos). Qualquer matching textual usa essa mesma função em tempo de preparação de dados e em
tempo de consulta. Duplicar essa regra é o erro que mais quebra esse tipo de sistema.

> Os **dados versionados** (dicionários e mapeamentos, como o de variações por tipo de logradouro:
> `AV` → `AVENIDA`, `AV.`, `AVN.`; `RUA` → `R.`; etc.) ficam em **`data/` na raiz do projeto** — não
> dentro de `services/`. São dados, não código, e crescem conforme novos formatos aparecem na base.

### 7.2 `integrations/`
Comunicação com sistemas externos — prioritariamente o **WFS do GeoSampa**. Contratos de dados
definidos com **modelos Pydantic**. Classes executoras (clients) e modelos de contrato são
**expostos no `__init__.py`** do módulo, para que o resto do sistema importe pelo nível superior
sem alcançar caminhos internos. Erros de rede/HTTP são encapsulados em exceções próprias; o
domínio não lida com detalhes do `requests`.

### 7.3 `domain/`
A **lógica de negócio**: roteamento da busca simples, matching dos três tipos de entidade
(logradouro, endereço, lote), geocodificação e tratamento geoespacial. Todo I/O via **DTOs
Pydantic**. Regras estruturantes:

- **Match exato vs. match com variação.** Códigos (`codlog`, número de contribuinte) são
  resolvidos por **lookup direto** na base. Texto livre (nome de rua, endereço por extenso)
  consulta a **base de variações** preparada pelos scripts.
- **Sugestões assíncronas** (durante a digitação) consultam estruturas cacheadas via uma
  interface de lookup — barato e desacoplado do ORM. A implementação atual é um dict em memória;
  troca futura para Redis fica isolada nessa interface.
- O **caso especial de endereço fiscal exato** (entrada bate exatamente com o cadastro de
  imóveis) é tratado no módulo de endereço: o domínio sinaliza a ambiguidade (ponto vs.
  polígono); a UI resolve via *pop-up*.
- **Projeção:** dados do GeoSampa costumam estar em SIRGAS 2000 / UTM 23S (EPSG:31983); o
  Leaflet renderiza em WGS84 (EPSG:4326). A reprojeção é centralizada — confirmar o CRS de
  origem ao integrar.

### 7.4 `scripts/`
Rotinas com **execução apartada do runtime web**: cargas das três bases oficiais (logradouros,
endereços fiscais, lotes) e preparação das estruturas de cache consumidas pelo domínio. A geração
de variações de escrita roda sobre **logradouros e endereços fiscais** — não sobre lotes, cujo
identificador é exato. Consome `data/` (dicionários, na raiz) e a normalização de `utils/` para que
as chaves geradas casem com as chaves buscadas em tempo de execução.

Scripts são funções/classes puras: a entrada de programa é via *management commands* (§8).
**Nunca** rodam durante o ciclo de request/response.

---

## 8. Scripts como Management Commands

Os scripts se integram ao Django como **comandos customizados do `manage.py`**, em
`management/commands/` do app de domínio mais próximo do dado. O comando é **fino**: só faz
parsing de argumentos, chama o script em `services/scripts/` e dá feedback no `stdout`.
**Sem lógica.** Padrão:

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
hx-get → apps/mapping → partial do Leaflet recebe a geometria
                        (ponto / linha / polígono) e renderiza sobre o WMS GeoSampa
```

A **busca detalhada** pula a etapa de roteamento — o tipo é dado pelo formulário — e entra
direto no módulo de domínio correspondente.

---

## 10. Convenções de Código

- **Tipagem integral:** *type annotations* em **todo o código Python** (não se aplica a templates
  HTML/HTMX). `mypy` deve passar limpo.
- **Pydantic nas fronteiras:** contratos de integração e DTOs de domínio são modelos Pydantic.
- **Normalização única:** uppercase + remoção de acentos vivem em um único lugar em
  `services/utils/`, usados em qualquer matching textual (preparação e consulta).
- **Dados ≠ código:** dicionários e mapeamentos versionados ficam em **`data/` na raiz do
  projeto**, não dentro de `services/`.
- **Imports do domínio:** importar de `services.integrations` e `services.domain` pelos
  `__init__.py` expostos; não alcançar submódulos internos.
- **Management commands sem lógica:** só parsing + chamada ao script + feedback.
- **JavaScript no frontend (restrito):** a única ocasião em que se escreve JS é **JS puro** —
  nada de TypeScript, React ou qualquer framework. Esse JS existe apenas como *callbacks* que
  **ouvem exclusivamente eventos do HTMX** (via `htmx.on(...)`); não busca dados, não consome JSON,
  não mantém estado de aplicação. (O Leaflet renderizando o mapa é o único outro JS tolerado.)
- **Templates:** *partials* prefixados com `_`; páginas estendem `base.html`.
- **HTMX:** `hx-trigger` com `delay`/`changed` na busca simples; alvos e *swaps* explícitos.
- **Estilização:** Tailwind + DaisyUI; toda nova pasta de templates registrada com `@source` no
  CSS de entrada.

---

## 11. Comandos de Desenvolvimento

```bash
# Ambiente Python
python -m venv .venv && source .venv/bin/activate
pip install -e .                      # ou: uv sync

# Banco (SQLite — fase inicial)
python manage.py migrate

# Pipeline de dados (apartado do runtime web): cargas → variações → cache
python manage.py <cada management command, na ordem definida em §8>

# Build do CSS (Tailwind 4 + DaisyUI 5) — terminal separado, em watch
npx @tailwindcss/cli -i static/src/input.css -o static/dist/output.css --watch

# Servidor de desenvolvimento
python manage.py runserver

# Qualidade
mypy .
ruff check .
python manage.py test
```

---

## 12. Regras Críticas — checklist antes de codar

- [ ] Existe uma **SPEC** (em `SPECS/<épico>/`) guiando esta iteração? Nenhum código nasce sem ela.
- [ ] A rota retorna **partial HTML**? (exceto a API REST futura) Se devolve JSON, está errado.
- [ ] Há **JS consumindo JSON** no frontend? Vedado (exceto Leaflet renderizando o mapa).
- [ ] A lógica de negócio está em **`services/`**, não em view/model/template/command?
- [ ] Entradas e saídas do domínio são **DTOs Pydantic**?
- [ ] Na busca simples, o **roteamento por regex** roda **antes** de qualquer consulta de domínio?
- [ ] Códigos (`codlog`, nº de contribuinte) são resolvidos por **match exato**? Apenas texto livre
      passa pela base de **variações**?
- [ ] Qualquer matching textual usa a **mesma** normalização (`utils.text`) em tempo de preparação
      e em tempo de consulta?
- [ ] Dicionários e mapeamentos estão em **`data/` na raiz** (dado versionado), não embutidos na
      lógica nem dentro de `services/`?
- [ ] Sugestões assíncronas consultam o **cache via interface de lookup**, não o ORM a cada tecla?
- [ ] Contratos de integração são **Pydantic** e estão **expostos no `__init__.py`**?
- [ ] **Type annotations** em tudo? `mypy` limpo?
- [ ] Models contêm **apenas** persistência? Commands **sem** lógica?
- [ ] A geometria de saída (ponto / linha / polígono) bate com o tipo da consulta?
- [ ] Nova pasta de templates registrada com `@source` no CSS de entrada?

---

## 13. Roadmap por Fase

A fase 1 é construída na ordem abaixo — cada item se apoia no anterior:

| Ordem | Entrega                                                                                      |
|-------|----------------------------------------------------------------------------------------------|
| 1     | **Busca de logradouros** com *fuzzy string search* (e o roteamento por regex que a aciona).  |
| 2     | **Geocodificação de endereços** (interpolação do número sobre o logradouro → ponto).         |
| 3     | **Busca de lotes** por número de contribuinte → polígono.                                     |
| 4     | **Caso extremo do endereço fiscal exato:** quando a entrada bate exatamente com um endereço fiscal, oferecer (via *pop-up*) busca de lote **ou** geocodificação especial — que parte do **polígono do lote**, não da interpolação do número no logradouro. |

Transversais à fase 1: os 6 apps em pé, pipeline de cargas + preparação de cache via *management
commands* (SQLite), e o mapa Leaflet + WMS GeoSampa renderizando ponto / linha / polígono.

| Depois | Entrega                                                                                     |
|--------|---------------------------------------------------------------------------------------------|
| Fase 2 | API REST com Django-Ninja.                                                                   |
| —      | Cache de lookup migra de dict em memória para Redis, isolado atrás da interface.            |