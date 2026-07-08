---
spec: design/005
versao: v1
atualizado_em: 2026-07-08
implementado: true
changelog:
  - v1: versão inicial
---

# SPEC design/005 — Centralização do tema dev em fonte única (`static/src`)

- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como desenvolvedor do DIMAP GeoCoder, quero que os tokens e componentes do design system
existam em **um único arquivo dentro do domínio do projeto**, consumido pelo `base.html`
(dev/CDN), pelos mocks da skill `componentes-frontend` e pelo futuro build de prod, para que
mudar o design system seja editar **um** arquivo — eliminando as quatro cópias de hoje
(`input.css`, espelho inline do `base.html` e cabeçalho de cada um dos dois mocks) que precisam
ser sincronizadas à mão.

## Critérios de aceite
- [ ] Existe `static/src/tema-dimap.dev.css` contendo o design system completo em CSS
      compatível com o CDN (`@tailwindcss/browser`): variáveis do tema daisyUI sob
      `html[data-theme="dimap"]`, bloco `@theme` (escalas agua/rocha/madeira/sakura, fontes)
      e as classes de componente (`.glass-*`, `.btn-onsen`, etc.). **Sem** `@plugin`/`@source`
      (esses são esqueleto de build e ficam no `input.css`).
- [ ] O `base.html` não contém mais nenhum token/classe duplicado: o bloco
      `<style type="text/tailwindcss">` passa a ser preenchido por `{% include %}` do arquivo
      único (resolvido no servidor, sem JS), e a UI renderiza **visualmente idêntica**.
- [ ] Os dois mocks da skill (`examples/design_system.html`, `examples/mock_ui.html`) não
      contêm mais cópia do tema: um loader curto de JS puro busca o arquivo único via HTTP e o
      injeta como `<style type="text/tailwindcss">`. O cabeçalho de cada mock documenta que
      eles agora exigem um servidor estático com root na raiz do projeto (ex.: Live Server) —
      não abrem mais via duplo clique (`file://` bloqueia o fetch).
- [ ] O `input.css` importa o mesmo arquivo (`@import "./tema-dimap.dev.css";`) e não duplica
      nenhum token/componente — fica apenas com o esqueleto de build.
- [ ] Mudar um token no arquivo único reflete na aplicação (reload) e nos mocks (reload) sem
      nenhuma edição adicional.

## Contexto e decisões de arquitetura
Mexe apenas em **interface (template base), configuração de templates e assets de dev** —
nenhuma camada de domínio ou persistência. Decisões:

- **A dependência aponta da skill para o projeto, nunca o contrário.** O arquivo único vive em
  `static/src` (onde o design system já mora, junto do `input.css`); a aplicação **não** lê nada
  de `.claude/`. Os mocks (que são da skill) é que buscam o arquivo do projeto.
- **Include server-side no `base.html`** em vez de loader JS: o Django resolve o arquivo em
  render, sem request extra e sem JS de infraestrutura no template. Custo aceito: adicionar
  `static/src` aos `DIRS` do template engine em `config/settings.py` (uso pouco convencional,
  documentado por comentário no settings). O arquivo é CSS puro — sem `{{` nem `{%`, portanto
  inerte para o template engine.
- **Por que injeção via `<style>` e não `<link>`:** verificado no código do
  `@tailwindcss/browser` que ele processa **exclusivamente** blocos
  `style[type="text/tailwindcss"]` inline (não há suporte a `<link>`), reagindo a mutações do
  DOM — por isso o include (aplicação) e o fetch+inject (mocks).
- **O CDN permanece em dev** (decisão pós-SPEC 004: build compilado só quando o desenvolvimento
  estabilizar / na iteração de deploy). Esta SPEC reduz o custo daquela decisão: o espelho
  deixa de ser espelho e vira a fonte.
- **`input.css` importa a mesma fonte**: no dia do build de prod, o mesmo arquivo alimenta o
  binário standalone — o tema via variáveis planas sob `[data-theme]` é exatamente o mecanismo
  que o daisyUI 5 usa por baixo do `@plugin "daisyui/theme"`, e o `base.html` já fixa
  `data-theme="dimap"` no `<html>`.

## Peças de referência a compor
- `templates/base.html` → o bloco `<style type="text/tailwindcss">` atual é o **conteúdo de
  partida** do arquivo único (é a versão mais atual do espelho, validada visualmente).
- `static/src/input.css` → conferir que tokens/componentes de lá e do espelho inline estão
  consolidados sem perda (a comparação declaração a declaração já foi feita em 2026-07-08 e
  deu paridade total — repetir o diff como verificação).
- `.claude/skills/componentes-frontend/examples/*.html` → cabeçalhos com as cópias a remover.
- `config/settings.py` → bloco `TEMPLATES` existente; entra só o diretório extra em `DIRS`.
- SKILL.md da `componentes-frontend` → §8 referencia o setup; atualizar a descrição do fluxo.

## Snippets sugeridos
```python
# config/settings.py — DIRS do template engine
"DIRS": [
    BASE_DIR / "templates",
    # static/src entra SÓ para o {% include %} do tema dev (SPEC design/005):
    # o base.html inclui tema-dimap.dev.css server-side dentro do <style type="text/tailwindcss">.
    BASE_DIR / "static" / "src",
],
```

```html
<!-- base.html — o bloco inteiro de tema/componentes vira isto -->
<style type="text/tailwindcss">{% include "tema-dimap.dev.css" %}</style>
```

```html
<!-- mocks (examples/*.html) — loader no lugar da cópia do tema; exige Live Server na raiz -->
<script>
  fetch("/static/src/tema-dimap.dev.css")
    .then((r) => r.text())
    .then((css) => {
      const s = document.createElement("style");
      s.type = "text/tailwindcss";
      s.textContent = css;
      document.head.appendChild(s);
    });
</script>
```

```css
/* input.css — esqueleto de build; tokens/componentes vêm da fonte única */
@import "tailwindcss";
@plugin "daisyui";
@source "../../templates";
@source "../../apps";
@import "./tema-dimap.dev.css";
```

## Fora de escopo
- **Build de prod** (`--minify`, Dockerfile multi-stage, fim do CDN): continua adiado para a
  iteração de deploy; a SPEC 004 permanece como está.
- **Qualquer mudança visual** em tokens/componentes — esta SPEC só move, não altera.
- Vendorar Leaflet, HTMX, fontes (continuam em CDN).

## Notas de teste
- Regressão visual da home: renderização idêntica antes/depois do include (sem requests novos
  além dos já existentes).
- Mock aberto via Live Server renderiza idêntico ao estado anterior; aberto via `file://`,
  falha de forma explícita (documentada no cabeçalho).
- Grep de paridade: nenhuma declaração (`--var: valor`) do espelho antigo ausente no arquivo
  único; nenhuma duplicação remanescente em `base.html`/mocks/`input.css`.
- Editar um token (ex.: cor de `--color-agua-400`) e verificar reflexo na home e no mock com
  um reload cada.

## Patches

_Nenhum patch registrado até o momento._
