---
spec: readthedocs/001
versao: v1
atualizado_em: 2026-11-19
testes_tdd: false
implementado: false
markers_obrigatorios: [documentacao]
changelog:
  - v1: versão inicial
---

# SPEC readthedocs/001 — Documentação técnica gerada do código

## 1 · User story

**Requisito não-funcional** — documentação técnica de cada módulo (README de domínio do pacote +
referência gerada do código), recompilada a cada build e servida em `<domínio>/docs/`.

## 2 · Condições de pronto

- [ ] Todo pacote de `services/domain`, `services/integrations`, `services/utils`, `services/scripts`
      e todo app de `apps/` tem **página própria**, agrupada no menu pela camada. Um pacote novo
      aparece no build seguinte **sem configuração manual**.
- [ ] A página de um módulo abre com o `README.md` do pacote, quando existe, seguido da referência
      gerada do código: API pública, assinaturas tipadas, docstrings, campos e validators dos DTOs
      Pydantic e o código-fonte. O que **não tem docstring também aparece**.
- [ ] Pacote sem `README.md` mostra o aviso **"Sem README"** na página e é listado no log do build.
- [ ] A página inicial é o `README.md` da raiz. O `CLAUDE.md` aparece como **"Princípios e
      convenções"**, e os documentos de `DOCS/`, em **"Operação"**. O menu segue a ordem Início,
      Princípios e convenções, Domínio, Integrações, Utilitários, Scripts, Apps, Operação.
- [ ] A busca do site encontra termos dos READMEs **e** nomes do código (classes, funções, campos de
      DTO).
- [ ] O site usa a paleta, a tipografia e o vidro do Onsen de Inverno aprovados no mock. Mudar uma cor
      no `tema-dimap.dev.css` muda a cor no site no build seguinte.
- [ ] `docker compose build docs` compila o site a partir do código atual. Qualquer aviso da
      compilação **derruba o build**.
- [ ] Atrás do nginx do host, `https://<domínio>/docs/` serve o site com estilo, menu e busca
      funcionando sob o subcaminho.
- [ ] `/docs/` exige sessão autenticada: o anônimo é mandado para `/login/`.

## 3 · Domínio

Esta SPEC não introduz domínio da DIMAP: modela o **site de documentação** que o gerador monta a
partir do repositório.

```python
class Camada(StrEnum):
    """Camada de código do projeto; cada uma é uma seção do menu."""

    DOMINIO = "services/domain"
    INTEGRACOES = "services/integrations"
    UTILITARIOS = "services/utils"
    SCRIPTS = "services/scripts"
    APPS = "apps"


class ModuloDocumentado(BaseModel):
    """Um pacote Python do primeiro nível de uma camada (diretório com __init__.py)."""

    camada: Camada
    nome: str = Field(pattern=r"^[a-z][a-z0-9_]*$")  # nunca privado (_x) nem migrations
    readme: str | None = None  # None = o pacote não tem README.md

    @computed_field  # type: ignore[prop-decorator]
    @property
    def caminho_import(self) -> str:
        return f"{self.camada.value.replace('/', '.')}.{self.nome}"


class SecaoProjeto(StrEnum):
    """Seções do site escritas à mão, fora do código."""

    INICIO = "inicio"  # README.md da raiz
    PRINCIPIOS = "principios"  # CLAUDE.md
    OPERACAO = "operacao"  # DOCS/**/*.md


class DocumentoProjeto(BaseModel):
    """Um markdown escrito à mão, publicado como está."""

    secao: SecaoProjeto
    origem: PurePosixPath  # relativo à raiz do repositório
    conteudo: str


class TokenTema(BaseModel):
    """Uma variável do design system lida do tema-dimap.dev.css."""

    nome: str = Field(pattern=r"^--(color|radius|font)-[a-z0-9-]+$")
    valor: str
```

O subpacote (ex.: `services/domain/documento_oficial/models`) não é `ModuloDocumentado`: entra na
página do pacote pai, pela referência gerada.

**Mock:** [001-mock-documentacao-tecnica/](001-mock-documentacao-tecnica/) — o site compilado da
prova de conceito (ver Caveats); leia a skill `mock`.

## 4 · Fora de escopo

- Escrever os `README.md` dos pacotes e o padrão deles: readthedocs/002.
- As SPECs como seção do site ("Decisões"): sem dono ainda.
- Voltar à página pedida depois do login (`/login/` não trata `?next=`): sem dono ainda.
- O serviço `docs` no compose de produção: SPEC de deploy (`DOCS/deploy/deploy-producao.md`, §1.5),
  sem número ainda. Esta SPEC entrega a imagem e o trecho do nginx que ela consome.

## 5 · Peças de referência a compor

- `@static/src/tema-dimap.dev.css` → blocos `html[data-theme="dimap"]` e `@theme`: fonte dos tokens
  de cor, raio e fonte.
- `@templates/base.html` → link do Google Fonts (Roboto 300–900 + Roboto Mono): o site carrega a
  mesma URL.
- `@docker/Dockerfile.web` → base `python:3.14-slim-trixie` e `uv` pinado em `0.11.21`: o estágio de
  build do docs usa as mesmas versões.
- `@apps/autenticacao/urls.py` → rota `login` (`/login/`): destino do anônimo.
- `@DOCS/deploy/deploy-producao.md` → §2.3 (nginx do host): onde entra o `location /docs/`.
- Skills: `componentes-frontend`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

> Os comentários abaixo são didáticos e **não são portados** para o código (CLAUDE.md §7.2).

### 6.1 Dependências e marker

**`pyproject.toml`** (acréscimos)
```toml
[dependency-groups]
docs = [
    # Zensical é 0.x: versão exata, atualizada à mão (ver Caveats).
    "zensical==0.1.2",
    "mkdocstrings-python>=2.0.11",
    "griffe-pydantic>=1.3.2",
    # O gerador usa DTOs Pydantic e roda na imagem docs, que só instala este grupo.
    "pydantic>=2.0",
]

[tool.pytest.ini_options]
addopts = "-m 'not integration and not banco and not artefato and not documentacao'"
markers = [
    # ... os existentes ...
    "documentacao: compila o site de documentação (rode com: uv run --group docs pytest -m documentacao)",
]
```

### 6.2 O gerador de páginas

Mora em `services/scripts/documentacao/`. **Não importa Django nem `services/domain`**: só stdlib e
Pydantic. Lê o repositório e grava o `docs_dir` do Zensical (as páginas, o `SUMMARY.md` do menu e a
folha de tokens). A referência do código não é gerada aqui: a página só carrega a diretiva `:::` que
o mkdocstrings expande no build.

**`services/scripts/documentacao/models.py`** — os models do §3, mais os DTOs da operação:
```python
class Pagina(BaseModel):
    """Um arquivo do docs_dir, no caminho em que o site o publica."""

    caminho: PurePosixPath  # relativo ao docs_dir: "domain/lote_geocod.md"
    conteudo: str


class GerarDocumentacaoInput(BaseModel):
    raiz: Path  # raiz do repositório
    destino: Path  # docs_dir; apagado e recriado a cada execução


class GerarDocumentacaoOutput(BaseModel):
    paginas: list[PurePosixPath]
    modulos_sem_readme: list[ModuloDocumentado]
```

**`services/scripts/documentacao/descoberta.py`**
```python
PASTAS_IGNORADAS = frozenset({"migrations", "__pycache__"})


class DescobrirModulos:
    def __call__(self, raiz: Path) -> list[ModuloDocumentado]:
        return self.pipeline(raiz)

    def pipeline(self, raiz: Path) -> list[ModuloDocumentado]:
        # Percorre as camadas na ordem do enum: é a ordem em que aparecem no menu.
        return [
            self._modulo(camada, pasta)
            for camada in Camada
            for pasta in self._pacotes(raiz / camada.value)
        ]

    def _pacotes(self, base: Path) -> list[Path]:
        # Só o primeiro nível: subpacote é parte da página do pai, não página própria.
        return sorted(
            pasta
            for pasta in base.iterdir()
            if (pasta / "__init__.py").is_file()
            and not pasta.name.startswith("_")
            and pasta.name not in PASTAS_IGNORADAS
        )

    def _modulo(self, camada: Camada, pasta: Path) -> ModuloDocumentado:
        readme = pasta / "README.md"
        return ModuloDocumentado(
            camada=camada,
            nome=pasta.name,
            readme=readme.read_text(encoding="utf-8") if readme.is_file() else None,
        )
```

**`services/scripts/documentacao/paginas.py`**
```python
AVISO_SEM_README = (
    '!!! warning "Sem README"\n'
    "    Este pacote ainda não tem `README.md`: abaixo, só o que o código diz.\n"
)

# Uma tupla só, lida pelo menu e pelos testes: mudar a ordem do site é mudar esta linha.
MENU: tuple[tuple[str, Camada | SecaoProjeto], ...] = (
    ("Início", SecaoProjeto.INICIO),
    ("Princípios e convenções", SecaoProjeto.PRINCIPIOS),
    ("Domínio", Camada.DOMINIO),
    ("Integrações", Camada.INTEGRACOES),
    ("Utilitários", Camada.UTILITARIOS),
    ("Scripts", Camada.SCRIPTS),
    ("Apps", Camada.APPS),
    ("Operação", SecaoProjeto.OPERACAO),
)


def pasta_da_camada(camada: Camada) -> PurePosixPath:
    # "services/domain" → "domain": é o trecho que aparece na URL (/docs/domain/lote_geocod/).
    return PurePosixPath(PurePosixPath(camada.value).name)


class MontarPaginaModulo:
    def __call__(self, modulo: ModuloDocumentado) -> Pagina:
        return Pagina(
            caminho=pasta_da_camada(modulo.camada) / f"{modulo.nome}.md",
            conteudo=self.pipeline(modulo),
        )

    def pipeline(self, modulo: ModuloDocumentado) -> str:
        return "\n\n".join(
            (
                f"# {modulo.nome}",
                self._corpo(modulo),
                self._referencia(modulo),
            )
        )

    def _corpo(self, modulo: ModuloDocumentado) -> str:
        if modulo.readme is None:
            return AVISO_SEM_README
        # O título da página é o nome do pacote: o H1 do README sairia duplicado.
        return re.sub(r"\A# .*\n", "", modulo.readme)

    def _referencia(self, modulo: ModuloDocumentado) -> str:
        # Os pacotes de services declaram __all__, e a referência mostra exatamente essas portas.
        # Os apps não declaram: a referência deles desce aos submódulos.
        diretiva = f"::: {modulo.caminho_import}"
        if modulo.camada is Camada.APPS:
            diretiva += "\n    options:\n      show_submodules: true"
        return f"## Referência\n\n{diretiva}"


class MontarPaginaDocumento:
    def __call__(self, documento: DocumentoProjeto) -> Pagina:
        return Pagina(caminho=self._caminho(documento), conteudo=documento.conteudo)

    def _caminho(self, documento: DocumentoProjeto) -> PurePosixPath:
        match documento.secao:
            case SecaoProjeto.INICIO:
                return PurePosixPath("index.md")
            case SecaoProjeto.PRINCIPIOS:
                return PurePosixPath("principios.md")
            case SecaoProjeto.OPERACAO:
                return PurePosixPath("operacao") / documento.origem.name


class MontarMenu:
    """O SUMMARY.md que o plugin literate-nav lê como menu do site."""

    def __call__(
        self,
        modulos: list[ModuloDocumentado],
        documentos: list[DocumentoProjeto],
    ) -> Pagina:
        return Pagina(
            caminho=PurePosixPath("SUMMARY.md"),
            conteudo=self.pipeline(modulos, documentos),
        )

    def pipeline(
        self,
        modulos: list[ModuloDocumentado],
        documentos: list[DocumentoProjeto],
    ) -> str:
        linhas: list[str] = []
        for titulo, secao in MENU:
            linhas.extend(self._secao(titulo, secao, modulos, documentos))
        return "\n".join(linhas) + "\n"

    # _secao: página única para INICIO e PRINCIPIOS; para camada e OPERACAO, o index.md da seção
    # seguido de um item indentado por página, na ordem alfabética.
```

**`services/scripts/documentacao/tokens.py`**
```python
# Os dois blocos em que o tema declara variáveis: os papéis do daisyUI e o @theme do Tailwind.
BLOCOS_DO_TEMA = (r'html\[data-theme="dimap"\]', r"@theme")
DECLARACAO = re.compile(r"^\s*(--(?:color|radius|font)-[a-z0-9-]+)\s*:\s*([^;]+);", re.MULTILINE)


class ExtrairTokensTema:
    def __call__(self, css: str) -> list[TokenTema]:
        return self.pipeline(css)

    def pipeline(self, css: str) -> list[TokenTema]:
        return [
            TokenTema(nome=nome, valor=valor.strip())
            for bloco in self._blocos(css)
            for nome, valor in DECLARACAO.findall(bloco)
        ]

    def _blocos(self, css: str) -> list[str]:
        # Os dois blocos não têm chave aninhada: o primeiro "}" depois da abertura fecha o bloco.
        # Fora deles (@layer components) há variáveis locais de peça, que não são token.
        return [
            achado.group(1)
            for seletor in BLOCOS_DO_TEMA
            for achado in re.finditer(seletor + r"\s*\{([^}]*)\}", css)
        ]


def folha_de_tokens(tokens: list[TokenTema]) -> Pagina:
    corpo = "".join(f"  {token.nome}: {token.valor};\n" for token in tokens)
    return Pagina(caminho=PurePosixPath("estilo/tokens.css"), conteudo=f":root {{\n{corpo}}}\n")
```

**`services/scripts/documentacao/gerador.py`**
```python
TEMA = PurePosixPath("static/src/tema-dimap.dev.css")
PELE = PurePosixPath("documentacao/estilo/onsen.css")


class GerarDocumentacao:
    def __call__(self, entrada: GerarDocumentacaoInput) -> GerarDocumentacaoOutput:
        return self.pipeline(entrada)

    def pipeline(self, entrada: GerarDocumentacaoInput) -> GerarDocumentacaoOutput:
        modulos = descobrir_modulos(entrada.raiz)
        documentos = self._ler_documentos(entrada.raiz)
        paginas = [
            *(montar_pagina_modulo(modulo) for modulo in modulos),
            *(montar_pagina_documento(documento) for documento in documentos),
            *self._indices_de_secao(),
            montar_menu(modulos, documentos),
            folha_de_tokens(extrair_tokens_tema(self._ler(entrada.raiz, TEMA))),
            Pagina(caminho=PurePosixPath("estilo/onsen.css"), conteudo=self._ler(entrada.raiz, PELE)),
        ]
        self._gravar(entrada.destino, paginas)
        return GerarDocumentacaoOutput(
            paginas=[pagina.caminho for pagina in paginas],
            modulos_sem_readme=[modulo for modulo in modulos if modulo.readme is None],
        )

    def _ler_documentos(self, raiz: Path) -> list[DocumentoProjeto]:
        # README.md → INICIO; CLAUDE.md → PRINCIPIOS; DOCS/**/*.md → OPERACAO.
        ...

    def _indices_de_secao(self) -> list[Pagina]:
        # Um index.md por seção com subpáginas, só com o título: é a página da seção no menu.
        ...

    def _gravar(self, destino: Path, paginas: list[Pagina]) -> None:
        # Recria do zero: pacote apagado do código não deixa página órfã de um build anterior.
        shutil.rmtree(destino, ignore_errors=True)
        for pagina in paginas:
            arquivo = destino / pagina.caminho
            arquivo.parent.mkdir(parents=True, exist_ok=True)
            arquivo.write_text(pagina.conteudo, encoding="utf-8")


gerar_documentacao = GerarDocumentacao()
```

**`services/scripts/documentacao/__main__.py`** — porta de entrada fina (ver Caveats):
```python
def main() -> None:
    parser = argparse.ArgumentParser(description="Gera as páginas do site de documentação técnica.")
    parser.add_argument("raiz", type=Path)
    parser.add_argument("destino", type=Path)
    argumentos = parser.parse_args()
    saida = gerar_documentacao(
        GerarDocumentacaoInput(raiz=argumentos.raiz, destino=argumentos.destino),
    )
    print(f"{len(saida.paginas)} páginas geradas")
    for modulo in saida.modulos_sem_readme:
        print(f"sem README: {modulo.caminho_import}")


main()
```

### 6.3 O site

**`documentacao/mkdocs.yml`** — o Zensical lê `mkdocs.yml` nativamente. O mesmo arquivo compila no
MkDocs + Material, que é a saída de emergência (ver Caveats).
```yaml
site_name: DIMAP GeoCoder — Documentação técnica
docs_dir: paginas  # gerado por services.scripts.documentacao; fora do git
site_dir: site  # fora do git
# Sem site_url: com links relativos, o mesmo build serve na raiz (dev, :8001) e em /docs/ (produção).
theme:
  name: material
  language: pt-BR
  font: false  # as fontes vêm do mesmo link do base.html, no extra_css
  palette:
    scheme: default
    primary: custom
    accent: custom
  features:
    - navigation.sections
    - navigation.indexes
    - navigation.top
    - search.highlight
    - content.code.copy
extra_css:
  - https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&family=Roboto+Mono:wght@400;500;700&display=swap
  - estilo/tokens.css  # gerado do tema-dimap.dev.css
  - estilo/onsen.css  # a pele: variáveis do tema do Zensical → tokens
markdown_extensions:
  - admonition
  - pymdownx.superfences
  - pymdownx.highlight
  - toc:
      permalink: true
plugins:
  - search
  - literate-nav:
      nav_file: SUMMARY.md
  - mkdocstrings:
      handlers:
        python:
          paths: [..]  # a raiz do repositório; o griffe lê o código sem importá-lo
          options:
            show_root_heading: false
            show_source: true
            show_if_no_docstring: true  # sem isto, o que não tem docstring some da página
            show_signature_annotations: true
            separate_signature: true
            members_order: source
            filters: ["!^_", "!^migrations$"]
            extensions:
              - griffe_pydantic:
                  schema: false
```

**`documentacao/estilo/onsen.css`** — a pele. Só referencia tokens (`var(--color-…)`), sem hex; o
ponto de partida é a folha aprovada no mock. Trecho:
```css
/* O tema grava as variáveis no body; `:root > *` vence a paleta padrão sem important. */
:root > * {
  --md-primary-fg-color: var(--color-agua-700);
  --md-accent-fg-color: var(--color-agua-600);
  --md-default-bg-color: var(--color-base-100);
  --md-default-fg-color: var(--color-rocha-950);
  --md-default-fg-color--light: color-mix(in srgb, var(--color-rocha-950) 70%, transparent);
  --md-typeset-a-color: var(--color-agua-700);
  --md-code-fg-color: var(--color-rocha-900);
  --md-code-hl-keyword-color: var(--color-agua-800);
  --md-code-hl-string-color: var(--color-accent);
  --md-code-hl-number-color: var(--color-sakura-600);
  --md-text-font: var(--font-sans);
  --md-code-font: var(--font-mono);
  /* ... demais papéis e cores de realce de sintaxe ... */
}

/* Cabeçalho = .glass-panel; área de leitura = .glass-panel-thick (receita copiada, ver Caveats). */
.md-header {
  background: linear-gradient(to bottom right, rgb(255 255 255 / 0.65), rgb(255 255 255 / 0.45), rgb(255 255 255 / 0.3));
  backdrop-filter: blur(18px);
  border-bottom: 1px solid rgb(255 255 255 / 0.6);
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.8), 0 8px 32px rgb(7 58 84 / 0.25), 0 0 24px rgb(72 202 228 / 0.25);
}

/* Hierarquia do §4 do design system: títulos em madeira, menu em .text-overline. */
.md-typeset h1 {
  color: var(--color-madeira-700);
  font-weight: 900;
  letter-spacing: -0.025em;
}
```

### 6.4 Imagem, compose e rota

**`docker/Dockerfile.docs`**
```dockerfile
# syntax=docker/dockerfile:1
# Sem GDAL, sem Django, sem banco: o gerador e o griffe leem o código sem importá-lo.
FROM python:3.14-slim-trixie AS build
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /uvx /bin/
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --only-group docs
# Só o que vira página: mexer em data/ ou templates/ não invalida o cache deste estágio.
COPY services ./services
COPY apps ./apps
COPY DOCS ./DOCS
COPY documentacao ./documentacao
COPY README.md CLAUDE.md ./
COPY static/src/tema-dimap.dev.css ./static/src/tema-dimap.dev.css
# --strict: aviso de compilação (link quebrado, referência que não resolve) derruba o build.
RUN python -m services.scripts.documentacao . documentacao/paginas \
 && zensical build --strict -f documentacao/mkdocs.yml

FROM nginx:1.29-alpine
COPY --from=build /app/documentacao/site /usr/share/nginx/html
```

**`docker-compose.yml`** (acréscimo)
```yaml
  # Documentação técnica. Só existe sob o profile `docs`:
  #   docker compose --profile docs up --build docs   → http://localhost:8001
  docs:
    build:
      context: .
      dockerfile: docker/Dockerfile.docs
    profiles: ["docs"]
    ports:
      - "${DOCS_PORT:-8001}:80"
```

**`apps/autenticacao/views.py`** (acréscimo)
```python
@require_GET
def autorizar_documentacao_view(request: HttpRequest) -> HttpResponse:
    # O auth_request do nginx só lê o status: 204 libera /docs/, 401 manda para o login.
    if request.user.is_authenticated:
        return HttpResponse(status=HTTPStatus.NO_CONTENT)
    return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
```

**`apps/autenticacao/urls.py`** (acréscimo)
```python
    path(
        "documentacao/autorizar/",
        views.autorizar_documentacao_view,
        name="autorizar_documentacao",
    ),
```

**`DOCS/deploy/deploy-producao.md`**, §2.3 (acréscimo ao `server` do nginx do host)
```nginx
location = /docs {
    return 301 /docs/;
}

location /docs/ {
    auth_request /_autorizar_docs;
    error_page 401 = @login_docs;
    # A barra final do proxy_pass tira o prefixo: o container serve o site na raiz.
    proxy_pass http://127.0.0.1:8001/;
}

location = /_autorizar_docs {
    internal;
    proxy_pass http://127.0.0.1:8000/documentacao/autorizar/;
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location @login_docs {
    return 302 /login/;
}
```

**`.gitignore`** e **`.dockerignore`** (acréscimo nos dois)
```gitignore
# Gerados: no .dockerignore, impedem que um build local atropele o da imagem.
documentacao/paginas/
documentacao/site/
```

**`CLAUDE.md`**: §5 ganha a linha da pasta `documentacao/` (configuração e pele do site de
documentação; as páginas são geradas). §8 ganha os comandos:
```bash
docker compose --profile docs up --build docs                                # site em http://localhost:8001
uv run --group docs python -m services.scripts.documentacao . documentacao/paginas
uv run --group docs zensical serve -f documentacao/mkdocs.yml -a 127.0.0.1:8001
uv run --group docs pytest -m documentacao
```

## 7 · Caveats

O gerador vive em `services/scripts/documentacao`, mas entra por `python -m` e grava em
`documentacao/paginas`, e não por management command gravando em `data/` (CLAUDE.md §6.4). O build da
imagem docs roda sem Django, GDAL e banco, e a saída é artefato descartável do build, não dado
versionado. O custo é um segundo tipo de porta de entrada para scripts, e o pacote fica proibido de
importar Django ou `services/domain`.

O site não é montado com peças do design system (CLAUDE.md §3.4): a marcação é do tema do Zensical,
e o Onsen de Inverno entra como tokens mais uma pele que só os referencia. Recriar o tema de
documentação em Atomic Design seria construir um gerador de site do zero. O custo é que a receita do
vidro (gradiente, blur, sombra em duas camadas) fica copiada no `onsen.css` e não acompanha o
`tema-dimap.dev.css` — só cores, raios e fontes acompanham sozinhos.

O mock desta SPEC é o site compilado da prova de conceito, e não um HTML que faz `fetch` do tema como
manda a skill `mock`. A marcação é gerada pelo Zensical e só existe depois da compilação. O custo é
que aprovar o visual exige compilar o site, com um comando.

O Zensical está na série 0.x (Beta), com versão exata no grupo `docs`. É o sucessor ativo do Material
for MkDocs, que está em manutenção, e o MkDocs 2.0 quebra os plugins. O custo é atualização manual e
configuração que pode mudar entre versões 0.x, com o MkDocs + Material lendo o mesmo `mkdocs.yml`
como saída de emergência.

A documentação reflete o código do último build da imagem e não acompanha o código entre um build e
outro. É o que faz o site de produção bater com o código implantado. O custo é que, em dev, o site só
se atualiza com `docker compose build docs` ou com o gerador rodado à mão.

`show_source` publica o código-fonte inteiro no site, protegido pela sessão. Quem mantém o sistema lê
o código na mesma página da referência. O custo é que qualquer servidor autenticado, de qualquer
perfil, lê o código do sistema.

A rota `documentacao/autorizar/` devolve só status (204/401), e não um partial HTML (CLAUDE.md §3.1).
Ela é consumida pelo `auth_request` do nginx, não pelo navegador nem por JS. O custo é ser a única
rota da aplicação sem corpo HTML.

A interface da busca (rótulos e mensagens) aparece em inglês. O Zensical ainda não traduz a busca
nova, e a indexação é multilíngue. O custo é uma tela de busca em inglês dentro de um site em
português.

## 8 · Testes (TDD)

Gerador — `tests/services/scripts/documentacao/`, suíte padrão, sobre um repositório falso em
`tmp_path`:

- `test_pacote_vira_pagina_no_menu_da_sua_camada` — `services/domain/exemplo/` com `__init__.py`
  gera `domain/exemplo.md` com `::: services.domain.exemplo` e aparece no `SUMMARY.md` sob Domínio.
  Diretório sem `__init__.py`, `_privado` e `migrations` não geram página.
- `test_pagina_abre_com_readme_do_pacote` — o texto do `README.md` do pacote está na página, antes de
  `## Referência`, e o H1 do README não se repete.
- `test_pacote_sem_readme_ganha_aviso_e_entra_na_lista` — a página traz o aviso "Sem README", e o
  módulo está em `modulos_sem_readme`.
- `test_documentos_do_projeto_viram_paginas_na_ordem_do_menu` — `README.md` → `index.md`,
  `CLAUDE.md` → `principios.md`, `DOCS/deploy/x.md` → `operacao/x.md`. As seções do `SUMMARY.md`
  seguem a ordem do `MENU`.
- `test_tokens_de_cor_saem_do_tema` — um tema com `--color-agua-600: #123456;` no `@theme` gera
  `estilo/tokens.css` com esse valor. Variável declarada dentro de `@layer components` não entra.

Site compilado — *(marker `documentacao`)*:

- `test_site_do_repositorio_compila_em_modo_estrito` — o gerador + `zensical build --strict` sobre o
  repositório real terminam sem erro.
- `test_referencia_mostra_campos_de_dto_sem_docstring` — num repositório falso, um `BaseModel` sem
  docstring com o campo `area_m2` aparece na página do pacote com o nome do campo.
- `test_busca_indexa_readme_e_codigo` — o `search.json` do site compilado contém uma frase do
  README do pacote falso e o nome da classe dele.
- `test_site_serve_sob_subcaminho` — nenhum `href`/`src` do HTML compilado começa com `/` (fora
  `//`): o site funciona em qualquer prefixo.

View — `tests/apps/autenticacao/`, suíte padrão:

- `test_documentacao_exige_sessao` — `autorizar_documentacao_view` devolve 401 para o anônimo e 204
  para o usuário autenticado (`RequestFactory`, sem banco).
