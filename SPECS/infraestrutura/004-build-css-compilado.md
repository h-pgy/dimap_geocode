---
spec: infraestrutura/004
versao: v3
atualizado_em: 2026-09-03
testes_tdd: true
implementado: true
markers_obrigatorios: [integration]
changelog:
  - v1: versão inicial
  - v2: "[bugfix] a ordem padrão de camadas do Tailwind fazia o daisyUI vencer o design system"
  - v3: o styleguide vira página da aplicação e passa a ler o CSS compilado
---

# SPEC infraestrutura/004 — CSS compilado no compose, fim do CDN

## 1 · User story

**Requisito não-funcional** — a interface passa a ser servida por CSS próprio compilado no
`docker compose`, sem compilador de Tailwind nem folha de daisyUI baixados de CDN em runtime.

## 2 · Condições de pronto

- [ ] Nenhuma página da aplicação busca Tailwind ou daisyUI na rede: com o host sem acesso a
      `cdn.jsdelivr.net`, a interface renderiza com o design system completo.
- [ ] A interface renderiza **visualmente idêntica** à servida pelo CDN — nenhum componente perde
      vidro, realce, ícone ou escala.
- [ ] O design system vence o daisyUI na cascata: componente do tema empilhado sobre classe daisyUI
      (`modal-box modal-box-glass`, `input input-glass`) mantém a pele de vidro.
- [ ] O CSS servido em desenvolvimento e o CSS assado na imagem de produção têm **o mesmo
      conteúdo**: nenhuma classe existe num e falta no outro.
- [ ] `docker compose up` só aceita requisição no `web` depois que o CSS existe: a primeira página
      servida numa subida limpa já vem estilizada.
- [ ] Editar `static/src/tema-dimap.dev.css` ou qualquer template reflete na aplicação com um
      reload, sem rodar comando.
- [ ] Build de CSS que não produz artefato derruba a subida do compose, em vez de deixar o `web`
      servir o CSS da subida anterior.
- [ ] Nenhum arquivo criado pelo build aparece no host com dono `root`, e a raiz do projeto não
      ganha `node_modules/`.
- [ ] Toda classe literal usada nos templates está presente no CSS compilado, e nenhuma classe que
      só existe em `SPECS/`, `wireframes/` ou nos mocks das skills entra nele.
- [ ] A imagem do `web` carrega o CSS minificado assado, sem `node` no runtime.
- [ ] `/design_system` responde sem login e renderiza o styleguide completo, carregando **o mesmo**
      `output.css` das demais páginas — nenhum CDN, nenhum `fetch` de CSS, nenhum
      `<style type="text/tailwindcss">`.
- [ ] Toda classe usada no styleguide existe no CSS compilado: peça exibida ali é peça que a
      aplicação tem.

## 3 · Domínio

Esta SPEC não introduz domínio. Ela consome a fonte única do design system entregue pela
[SPEC design/004](../design/004-centralizacao-tema-dev.md) — `static/src/tema-dimap.dev.css` — e
faz a ela uma única pergunta: o mesmo arquivo que o `base.html` injeta em runtime alimenta o
compilador em build. O artefato da iteração é `static/dist/output.css`.

## 4 · Fora de escopo

- Vendorar Leaflet, HTMX e as fontes do Google, que seguem em CDN — sem dono ainda.
- `collectstatic`, servidor de estáticos e cache-busting de produção — SPEC de deploy.
- Os mocks de SPEC, que seguem no `@tailwindcss/browser` porque renderizam peça que ainda não
  existe — skill `mock`.
- As citações a `examples/mock_ui.html` nas SPECs design/001, 004 e 005, que ficaram órfãs — sem
  dono ainda.
- Qualquer mudança visual em token, átomo ou molécula: a iteração exige paridade, não redesenho —
  sem dono ainda.
- As classes mortas que a auditoria de cobertura encontra (`form-control`, `btn-delegar`,
  `link-interno`, `tarja-vinculo-info`) e `bg-agua-50/70`, que referencia um degrau inexistente na
  escala `agua` — sem dono ainda.

## 5 · Peças de referência a compor

- `@static/src/tema-dimap.dev.css` → fonte única do design system; entra no build por `@import`.
- `@package.json` → `@tailwindcss/cli` e `daisyui` já pinados nas versões em uso.
- Skills: `componentes-frontend`, `escrever-testes`.

## 6 · Snippets

**`static/src/input.css`** — a ordem das camadas e o `source(none)` são as duas linhas que
sustentam a paridade: uma com a aparência que o CDN produzia, outra entre dev e produção.
```css
/* O daisyUI emite os componentes dele dentro de `utilities`, e o design system vive em
   `components`. Na ordem padrão do Tailwind, `components` vem antes — e o daisyUI venceria o
   tema. Servido por CDN a ordem saía invertida por acidente, porque a folha do daisyUI
   registrava base/utilities primeiro e `components`, nome novo, ia para o fim da fila. */
@layer properties, theme, base, utilities, components;

/* Sem source(none) o Tailwind varre a raiz do projeto inteira por conta própria, além dos @source.
   Em dev, com o repo bind-montado, isso engole SPECS/, wireframes/, os mocks das skills e até path
   data de SVG — e o CSS de dev vira um superconjunto do de produção. */
@import "tailwindcss" source(none);
@import "./tema-dimap.dev.css";
@plugin "daisyui";

@source "../../templates";
@source "../../apps";
@source "./js";
/* Único módulo de services/ que entrega classe pronta ao template. Varrer services/ inteiro
   arrastaria domain/email/, que monta e-mail com style inline e cujos comentários e chaves de
   dicionário viram candidatos falsos. */
@source "../../services/utils/erros_formulario";
```

**`docker/Dockerfile.web`** — três estágios novos no topo. O de dev e o de produção partem do mesmo
`css-deps`, então existe um único `npm ci` e uma única versão do compilador:
```dockerfile
# syntax=docker/dockerfile:1

FROM node:24-alpine AS css-deps
# As dependências ficam FORA de /app, pelo mesmo motivo do venv em /opt/venv mais abaixo:
# o bind mount do código em desenvolvimento esconderia /app/node_modules.
ENV NODE_PATH=/opt/node/node_modules \
    PATH=/opt/node/node_modules/.bin:$PATH
WORKDIR /opt/node
# `npm ci` (não `install`) exige o lock e nunca o reescreve; a falha de instalação acontece no
# build da imagem, ruidosa, e não no meio de uma subida.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
WORKDIR /app

# Alvo do serviço `tailwind` do compose: watch sobre o bind mount.
FROM css-deps AS css-watch
# `node` é o usuário que a imagem oficial já traz em uid 1000. Rodar como ele, e não como root,
# é o que faz o output.css nascer no bind mount pertencendo ao dono do repositório — bind mount
# grava no host o uid cru do processo, sem tradução.
USER node
# --watch=always: o watch comum encerra quando o stdin fecha, que é o caso de container sem tty.
CMD ["tailwindcss", "-i", "static/src/input.css", "-o", "static/dist/output.css", "--watch=always"]

# Assa o CSS minificado para a imagem final. Roda como root e sem bind mount: o artefato nasce
# dentro da imagem, onde dono não importa.
FROM css-deps AS css-build
# Exatamente as pastas do @source, e só elas: mudança em config/ não invalida esta camada, e
# esquecer uma aqui faria produção compilar menos classes que desenvolvimento.
COPY static ./static
COPY templates ./templates
COPY apps ./apps
COPY services/utils/erros_formulario ./services/utils/erros_formulario
RUN tailwindcss -i static/src/input.css -o static/dist/output.css --minify
```

e, na imagem final, depois do `COPY . .` (o `.dockerignore` já exclui `static/dist`, então nada do
host atropela o assado):
```dockerfile
COPY --from=css-build /app/static/dist/output.css static/dist/output.css
```

**`docker-compose.yml`**
```yaml
  tailwind:
    build:
      context: .
      dockerfile: docker/Dockerfile.web
      target: css-watch
    volumes:
      - .:/app

    healthcheck:
      # É este teste que o `web` espera. Sem ele a primeira página de uma subida limpa sai sem CSS.
      test: ["CMD-SHELL", "test -s static/dist/output.css"]
      interval: 2s
      timeout: 2s
      retries: 30

  web:
    depends_on:
      db:
        condition: service_healthy
      tailwind:
        # Build de CSS que não produz artefato impede o `web` de subir — em vez de deixá-lo servir
        # o output.css da subida anterior, que é a falha silenciosa que se quer eliminar.
        condition: service_healthy
```

**`templates/base.html`** — o `<link>` substitui, de uma vez, a folha do daisyUI, o script do
compilador de browser e o `<style type="text/tailwindcss">` que injetava o tema:
```html
{% load static %}
...
{# Design system compilado; a fonte segue sendo static/src/tema-dimap.dev.css. #}
<link rel="stylesheet" href="{% static 'output.css' %}" />
```

**`config/settings.py`** — `static/src` sai do `DIRS`: existia só para o `{% include %}` do tema,
que deixa de acontecer.
```python
"DIRS": [BASE_DIR / "templates"],
```

**`apps/core/views.py`** — view fina; o fundo vem do contexto que a área administrativa já usa:
```python
def design_system(request: HttpRequest) -> HttpResponse:
    return render(request, "core/design_system.html", contexto_fundo_admin())
```

**`templates/core/design_system.html`** — o styleguide portado. Como página da aplicação, o que era
contorno vira o mecanismo real: o fundo deixa de ser montado por `fetch` dos partials e passa a ser
`{% include %}`; os caminhos absolutos viram `{% static %}`; o CDN e o loader do tema saem.
```html
{% load static %}
<link rel="stylesheet" href="{% static 'output.css' %}" />
...
{% include "mapping/_mapa_admin.html" %}
```

**`.claude/skills/componentes-frontend/SKILL.md`** — a skill deixa de enumerar peças e passa a
declarar a cadeia, apontando para a rota:
> Átomo novo nasce em `static/src/tema-dimap.dev.css` → o build emite → `/design_system` mostra.
> O catálogo do que existe é a rota, não esta skill.

**`package-lock.json`** passa a ser versionado: é ele que fixa a versão do compilador e do daisyUI,
e sem ele o `npm ci` do Dockerfile aborta.

## 7 · Caveats

O `Dockerfile.web` passa a construir duas coisas: a imagem do servidor e o CSS. É o que evita um
segundo Dockerfile com o mesmo `npm ci` e a mesma invocação do compilador, livres para divergir. O
custo é que o arquivo deixa de ter um assunto só, e a nota que amarra sua base à do
`Dockerfile.daemon` passa a valer apenas do estágio final para baixo.

O serviço `tailwind` roda como o usuário `node` da imagem, e não como root, porque bind mount não
traduz uid: o número do processo é o que fica gravado no inode do host. O custo é a premissa de que
o dono do repositório é uid 1000 — o padrão de instalação em Linux, e o mesmo número do usuário
`node`. Em host onde isso não valha, o `output.css` sai pertencendo a outro dono.

O `web` passa a depender do `tailwind` para subir. A razão é tornar a falha ruidosa: a versão
anterior desta migração morria em silêncio e o Django seguia servindo o CSS velho, que foi o
sintoma observado. O custo é que build de CSS quebrado bloqueia também o trabalho que não toca a
interface.

`npm ci` roda no build da imagem, não na subida. Isso mantém a instalação fora do caminho quente e
falha cedo. O custo é que mexer em `package.json` sem `docker compose build` deixa o desenvolvedor
com a versão antiga do compilador, sem aviso.

O navegador deixa de compilar o CSS olhando o DOM: só sai no artefato a classe que o `@source`
descobre como literal em `templates/`, `apps/`, `static/src/js` ou `services/utils/erros_formulario`. O custo é que classe montada por
interpolação depende de suas variantes existirem literais em algum arquivo varrido — é o caso de
`alert-{{ message.tags }}`, cujas quatro variantes hoje aparecem literais em outros templates.

Os mocks da skill `componentes-frontend` seguem compilando no browser, enquanto a aplicação passa a
ler CSS estático. É o que preserva o mock como ferramenta de desenho, onde se inventa componente que
ainda não existe; fazê-lo ler o artefato exigiria varrer `.claude/skills/**`, invertendo a dependência
que a SPEC design/004 fixou e recontaminando o CSS da aplicação com classe que só existe em mock. O
custo é que os dois deixam de compartilhar o mecanismo: componente aprovado no mock só é garantido na
aplicação depois de portado para o tema, onde vira classe de `@layer components` e passa a ser emitido
independentemente de varredura.

O styleguide não estende `base.html`: a casca da aplicação trava a viewport em `h-screen
overflow-hidden` e monta cromo (marca, widget de usuário) que um documento longo e rolável não quer.
O custo é um segundo `<head>` no projeto, com fontes e link do CSS repetidos — e ele precisa
acompanhar o `base.html` se a casca mudar.

A rota é aberta. Informação sobre o vocabulário visual não é ato administrativo (CLAUDE.md §3.5), e
exigir login para consultar o design system atrapalharia justamente quem o consulta. O custo é
expor a interface interna a quem alcançar a URL.

A imagem de produção passa a compilar e servir o andaime do styleguide — cerca de 22KB não
minificados de classes que só aquela rota usa. É consequência direta de `templates/` ser varrido
igual em dev e em produção, que é o que sustenta a paridade entre os dois. O custo é CSS morto
viajando para todo usuário.

Três condições de pronto — subida ordenada, ausência de artefato `root`, e falha ruidosa — não
ganham teste automatizado, porque exigiriam subir o compose de dentro do `pytest`. Ficam no smoke
manual descrito na §8. O custo é que regressão nesses três pontos só aparece na próxima subida
limpa.

## 8 · Testes (TDD)

- `test_toda_classe_literal_dos_templates_esta_no_css_compilado` — fixa que o artefato emite toda
  classe literal usada em `templates/` e `apps/**/*.html`; falha se um `@source` deixar de cobrir
  uma pasta. *(marker `integration`)*
- `test_css_compilado_ignora_pastas_fora_da_aplicacao` — fixa a paridade dev/produção: classe que
  só existe em `SPECS/`, `wireframes/` ou nos mocks das skills não aparece no artefato; falha se a
  varredura automática do Tailwind voltar a ligar. *(marker `integration`)*
- `test_css_compilado_traz_o_tema_dimap_e_os_componentes_daisyui` — fixa que `html[data-theme="dimap"]`
  e os componentes do daisyUI estão no artefato; falha se o `@plugin` sair do build, que é o modo
  como o CSS sai completo em tamanho e vazio em aparência. *(marker `integration`)*
- `test_design_system_vence_o_daisyui_na_cascata` — fixa que a camada `components` é declarada
  depois de `utilities`; falha se a ordem padrão do Tailwind voltar, quando o modal fica opaco, o
  foco perde o halo e os avisos perdem a cor sem erro nenhum. *(marker `integration`)*
- `test_rota_design_system_responde_sem_login` — fixa que `/design_system` é aberta e renderiza.
- `test_styleguide_usa_o_css_compilado_da_aplicacao` — fixa que a página traz o `<link>` do
  `output.css` e nenhum resquício de CDN ou de bloco `text/tailwindcss`.
- `test_toda_classe_do_styleguide_esta_no_css_compilado` — fixa que o styleguide não pode exibir
  peça que a aplicação não tem. *(marker `integration`)*
- `test_base_html_nao_referencia_cdn_de_tailwind_nem_daisyui` — fixa o fim do CDN na casca.
- `test_home_serve_o_link_do_css_compilado` — fixa o contrato da página: a resposta traz o `<link>`
  para `output.css` e nenhum `<style type="text/tailwindcss">`.

Smoke manual, numa subida limpa (`docker compose down && docker compose up --build`): o `web` só
responde depois do `tailwind` ficar `healthy`; `ls -l static/dist/output.css` mostra o dono do
repositório; `git status` segue limpo; e apagar `static/dist/output.css` com o compose no ar faz o
arquivo voltar sozinho.
