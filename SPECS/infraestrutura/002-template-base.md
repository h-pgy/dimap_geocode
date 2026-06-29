---
spec: infraestrutura/002
versao: v1
atualizado_em: 2026-06-26
changelog:
  - v1: versão inicial
---

# SPEC infraestrutura/002 — Template base do projeto

## User story
Como desenvolvedor, quero um único template base (`base.html`) que carregue toda a stack de
frontend (Tailwind 4 + DaisyUI 5, HTMX 2, Leaflet 1.9) e defina a casca da página (head, navbar,
área de mensagens, blocos de extensão), para que **toda página completa** do projeto seja montada
estendendo esse template, sem repetir boilerplate nem reconfigurar libs a cada app.

## Critérios de aceite
- [ ] Existe um `base.html` global em `templates/` que renderiza o documento HTML completo
      (`<!doctype>`, `<head>`, `<body>`) e é acessível a **todos os apps** (já coberto por
      `TEMPLATES.DIRS = [BASE_DIR / "templates"]` no `settings.py`).
- [ ] **Toda página completa** do projeto estende `base.html` via `{% extends "base.html" %}`.
- [ ] **Partials NÃO estendem `base.html`** — são fragmentos autossuficientes (sem `{% extends %}`),
      prefixados com `_`, trocados pelo HTMX dentro de um alvo de uma página já carregada.
- [ ] O `<head>` carrega: Tailwind 4 + DaisyUI 5 (CDN em dev, com comentário de como trocar pelo
      build de produção), HTMX 2 e o CSS/JS do **Leaflet 1.9** (CSS do Leaflet no `<head>`, JS antes
      do fechamento do `<body>`).
- [ ] O `<html>` declara `data-theme` do DaisyUI (tema único do projeto) e `lang="pt-br"`.
- [ ] **CSRF do HTMX está cabeado globalmente:** o `<body>` carrega
      `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'`, herdado por todos os elementos HTMX
      descendentes, para que qualquer `hx-post`/`hx-put`/`hx-delete` do projeto passe no
      `CsrfViewMiddleware` sem precisar repetir o token em cada formulário/botão.
- [ ] O `base.html` renderiza as **mensagens do Django** (`messages`) como componentes idiomáticos
      DaisyUI (`alert` com a variante correspondente ao nível da mensagem).
- [ ] O `base.html` tem uma **navbar DaisyUI** com a marca "DIMAP GeoCoder" (link para a home) e um
      bloco reservado para a área de sessão/usuário (login/logout), preenchível por SPECs futuras
      (`accounts`), hoje vazio ou com placeholder.
- [ ] O `base.html` expõe os blocos de extensão: `title`, `head` (CSS/meta extra por página),
      `content` (corpo) e `scripts` (JS extra por página, ex.: inicialização do mapa Leaflet).
- [ ] A `home.html` existente passa a usar o `base.html` no padrão final (navbar + blocos),
      validando o template de ponta a ponta.
- [ ] A pasta `templates/` já está declarada com `@source` em `static/src/input.css` (verificar;
      acrescentar se algum diretório de templates não estiver coberto).

## Contexto e decisões de arquitetura

**Camada:** interface (Django templates), exclusivamente. Sem domínio, sem persistência. É o item
"layout base" do app `core` (CLAUDE.md §6) e o alicerce do HATEOAS via HTMX (§3.1): como **todas**
as rotas devolvem HTML — páginas completas estendendo `base.html` e partials como fragmentos — o
template base é o ponto único onde a stack de frontend é carregada e configurada.

**Páginas estendem; partials não (decisão central da SPEC).** O `base.html` é a casca completa do
documento. Um partial é um fragmento que o HTMX injeta (`hx-swap`) dentro de um `hx-target` de uma
página **já carregada**; se um partial estendesse o base, a resposta traria um `<html>` inteiro —
com `<head>`, libs e navbar duplicados — dentro de um `<div>`, quebrando o DOM e recarregando as
bibliotecas. Por isso a regra do CLAUDE.md §11 (*"partials prefixados com `_`; páginas estendem
`base.html`"*) é inegociável: **partial = fragmento, sem `extends`**.

**CSRF do HTMX no `<body>`.** Diferente de um `<form>` Django comum (que injeta
`{% csrf_token %}`), requisições HTMX não-GET precisam carregar o token no header `X-CSRFToken`. O
atributo `hx-headers` é **herdado** (ver skill `htmx` → `hx-headers`), então declará-lo uma vez no
`<body>` cobre todos os elementos HTMX da página. Isso é configuração transversal de interface —
mora no template base, não nas views.

**Tema DaisyUI único.** O projeto fixa **um** tema via `data-theme` no `<html>` (hoje `light`). A
troca/expansão de temas é decisão de produto futura, fora desta SPEC. DaisyUI entra como
`@plugin "daisyui";` — já presente tanto no CDN (`<style type="text/tailwindcss">`) quanto no
`static/src/input.css` do build.

**Leaflet no base.** O mapa (`apps/mapping`) é destino central da UX e aparece na página principal;
carregar o CSS/JS do Leaflet no `base.html` evita reconfiguração por app. A **inicialização** de um
mapa específico (JS local ao Leaflet, permitido por §11) fica no bloco `scripts` de cada página que
tem mapa, não no base.

**Dev vs. produção (CSS).** Em desenvolvimento, Tailwind+DaisyUI vêm do CDN (`@tailwindcss/browser`)
para simplificar. O `base.html` deve manter o comentário de que, no deploy, troca-se o CDN pelo
`<link>` para `static/dist/output.css` compilado (`npx @tailwindcss/cli -i static/src/input.css -o
static/dist/output.css`), conforme CLAUDE.md §2/§12. O Tailwind 4 descobre os templates apenas via
`@source` no `input.css` — `templates/` e `apps/` já estão declarados lá; qualquer pasta nova de
templates precisa ser acrescentada.

**Acessibilidade a todos os apps (verificação pedida).** Confirmado no `settings.py`:
`TEMPLATES.DIRS = [BASE_DIR / "templates"]` (linha 98) com `APP_DIRS: True` (linha 99) e
`STATICFILES_DIRS = [BASE_DIR / "static" / "dist"]` (linha 149), `STATIC_URL = "static/"` (linha
148). Ou seja, `templates/base.html` é resolvível por qualquer app via `{% extends "base.html" %}`
e os estáticos compilados são servidos de `static/dist/`. Nenhuma mudança de `settings.py` é
necessária para o template base ficar acessível — esta SPEC apenas usa o que já está configurado.

## Peças de referência a compor
- `@templates/base.html` → casca já existente (Tailwind/DaisyUI/HTMX via CDN, blocos `title`,
  `head`, `content`, `scripts`): **evoluir no lugar**, não recriar. Acrescentar Leaflet, CSRF do
  HTMX, navbar, área de mensagens.
- `@templates/core/home.html` → página de exemplo que já estende `base.html`: ajustar para o padrão
  final (navbar herdada do base), servindo de validação ponta a ponta.
- `@static/src/input.css` → entrada do build com `@plugin "daisyui";` e `@source` para `templates/`
  e `apps/`: já cobre as pastas atuais; reutilizar.
- `@config/settings.py` → `TEMPLATES.DIRS`, `APP_DIRS`, `STATIC_URL`, `STATICFILES_DIRS` já
  configurados: o template base apenas se apoia neles.
- skill `daisyui` → usar componentes idiomáticos (`navbar`, `alert`, classes `bg-base-*`,
  `text-base-content`) ao montar navbar e mensagens.
- skill `htmx` (`hx-headers`) → padrão de CSRF herdado no `<body>`.

## Snippets sugeridos
```html
{# templates/base.html — direção; adaptar sem violar §3/§10/§11 #}
{% load static %}
<!doctype html>
<html lang="pt-br" data-theme="light">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{% block title %}DIMAP GeoCoder{% endblock %}</title>

    {# Leaflet (mapa) — CSS no head #}
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9/dist/leaflet.css" />

    {# Dev: Tailwind 4 + DaisyUI via CDN. No deploy, compilar static/src/input.css
       -> static/dist/output.css e trocar por:
       <link rel="stylesheet" href="{% static 'output.css' %}" /> (CLAUDE.md §2/§12). #}
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <style type="text/tailwindcss">@plugin "daisyui";</style>
    <script src="https://unpkg.com/htmx.org@2"></script>

    {% block head %}{% endblock %}
  </head>

  {# CSRF herdado por todos os elementos HTMX descendentes (skill htmx → hx-headers) #}
  <body class="min-h-screen bg-base-100 text-base-content"
        hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>

    <nav class="navbar bg-base-200 border-b border-base-300">
      <div class="flex-1">
        <a href="{% url 'core:home' %}" class="btn btn-ghost text-xl">DIMAP GeoCoder</a>
      </div>
      <div class="flex-none">
        {% block navbar_session %}{# accounts: login/logout (SPEC futura) #}{% endblock %}
      </div>
    </nav>

    {% if messages %}
      <div class="container mx-auto px-6 pt-4 space-y-2">
        {% for message in messages %}
          <div class="alert alert-{{ message.tags|default:'info' }}">
            <span>{{ message }}</span>
          </div>
        {% endfor %}
      </div>
    {% endif %}

    {% block content %}{% endblock %}

    {# Leaflet JS antes do fim do body; páginas com mapa inicializam no bloco scripts #}
    <script src="https://unpkg.com/leaflet@1.9/dist/leaflet.js"></script>
    {% block scripts %}{% endblock %}
  </body>
</html>
```

```html
{# Padrão de uma PÁGINA completa #}
{% extends "base.html" %}
{% block title %}… {% endblock %}
{% block content %}<main class="container mx-auto px-6 py-8">…</main>{% endblock %}

{# Padrão de um PARTIAL (NUNCA estende base) — fragmento autossuficiente #}
{# templates/<app>/partials/_sugestoes.html #}
<ul class="menu bg-base-100 rounded-box">…</ul>
```

## Fora de escopo
- **Navbar de sessão (login/logout)** funcional: o bloco `navbar_session` é só reservado; o
  conteúdo vem com a SPEC de `accounts` (roadmap §14, item 5).
- **Compilação/minificação de produção** do CSS e troca definitiva do CDN pelo `<link>` do build:
  esta SPEC mantém o CDN em dev e documenta a troca, mas não executa o pipeline de deploy.
- **Inicialização de mapas Leaflet** concretos e o partial do mapa: são da SPEC de `apps/mapping`.
- **Toasts/posicionamento avançado de mensagens** e múltiplos temas DaisyUI: tema único fixo agora.
- **Padrão "rota serve página completa no GET e partial no `HX-Request`"** (dupla renderização via
  header `HX-Request`): não é usado na Fase 1 — partials são fragmentos puros. Fica registrado como
  possibilidade futura, não implementado aqui.
- Qualquer alteração em `settings.py` (já está tudo configurado para o base ser acessível).

## Notas de teste
*(Somente referência — não implementar agora; CLAUDE.md §13.)*
- Renderizar a `home` e verificar que `base.html` produz documento HTML válido, com Tailwind/DaisyUI,
  HTMX e Leaflet carregados.
- Verificar que o `<body>` emite `hx-headers` com um `X-CSRFToken` não vazio.
- Disparar um `hx-post` simples de uma página filha e confirmar que **não** há `403 CSRF` (o token
  herdado funciona).
- Confirmar que um partial renderizado isoladamente **não** contém `<html>`/`<head>` (é fragmento).
- Verificar que mensagens do Django (`messages.success/error/...`) aparecem como `alert` DaisyUI com
  a variante correta.

## Patches
<!-- Correções pontuais entram aqui, cada uma incrementando a versão no front-matter. -->
