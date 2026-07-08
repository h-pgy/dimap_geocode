---
spec: design/005
versao: v1
atualizado_em: 2026-07-08
implementado: true
changelog:
  - v1: versão inicial
---

# SPEC design/005 — Navbar compacta em tela estreita (busca entre os chips)

- [x] **Implementada**

## User story
Como usuário no celular ou tablet, quero que a barra de busca recolhida não fique coberta pelos
chips de marca e de usuário, para continuar enxergando e usando a busca depois que um resultado
é renderizado.

## Critérios de aceite
- [ ] Em tela < 1024px (lg), com resultado no DOM, a barra de busca vira um pill de 3rem alinhado
      em `top-6` entre o chip da marca (monograma "D", `w-12 h-12`) e o widget de usuário
      (avatar `w-9 h-9`), sem sobreposição — a "navbar de gelo" validada no mock.
- [ ] Em tela < 1024px, no estado compacto, a linha de dicas (Ctrl+K + badges) some; sugestões e
      resultado seguem renderizando abaixo da fileira, na largura normal.
- [ ] Em tela ≥ 1024px nada muda: chip da marca com texto completo, widget de usuário com texto,
      barra compacta com padding e dicas como hoje.
- [ ] A transição hero → compacto segue animada (mesma coreografia de 500ms da `.search-hero`),
      sem JavaScript de layout — CSS reagindo a `#resultado-busca` não vazio.

## Contexto e decisões de arquitetura
Só camada de interface (templates + tokens CSS). O design já foi todo resolvido e validado no
design system: os tokens `.search-panel` e `.search-hints` e a media query `@media (width < 64rem)`
já existem em `static/src/tema-dimap.dev.css` (fonte única, SPEC design/004), e o padrão está
registrado no styleguide e no mock da skill `componentes-frontend`. Esta SPEC é apenas o **porte
do markup**: os templates da aplicação passam a usar as classes que os tokens esperam.

Decisões que vêm do design validado:
- O corte é **lg (64rem)**, não sm: o painel compacto tem `max-w-2xl` (42rem) e colide com os
  chips até em tablets.
- Abaixo de lg, o chip da marca é **sempre** monograma e o widget de usuário é **sempre** só
  avatar (independente do estado da busca) — evita chip largo em tela estreita e dispensa
  seletores de estado fora da `.search-hero`.
- Largura e padding do painel de busca moram no token `.search-panel`, **não** como utilities no
  markup — utility no HTML venceria a regra de componente (layer utilities acima de layer
  components) e o estado compacto nunca aplicaria.

## Peças de referência a compor
- `@static/src/tema-dimap.dev.css` → tokens `.search-panel`, `.search-hints` e a media query da
  navbar compacta: **já existem**, o template só adota as classes.
- `@.claude/skills/componentes-frontend/examples/mock_ui.html` → markup de referência validado
  pelo usuário: chip da marca com monograma (`w-12 h-12 lg:w-auto…`), avatar responsivo
  (`w-9 h-9 lg:w-11 lg:h-11`), posições `left-4/right-4 lg:left-6/lg:right-6`.
- `templates/base.html` → chip da marca e `#widget-area-usuario` existentes (recebem as
  variantes responsivas).
- `templates/core/home.html` → painel de busca existente (recebe `search-panel`/`search-hints`
  no lugar das utilities de largura/padding).

## Snippets sugeridos
```html
<!-- home.html: painel de busca — largura/padding saem do markup, entram via token -->
<div class="pointer-events-auto glass-panel search-panel flex flex-col gap-2">
  …
  <div class="search-hints flex justify-between px-2 pt-1 items-center">…</div>
</div>

<!-- base.html: chip da marca — monograma abaixo de lg -->
<a href="{% url 'core:home' %}"
   class="fixed top-6 left-4 lg:left-6 z-20 glass-panel rounded-full! flex items-center
          justify-center w-12 h-12 lg:w-auto lg:h-auto lg:px-5 lg:py-2.5 transition-glass
          hover:bg-white/60">
  <span class="hidden lg:inline text-lg font-black tracking-tight text-madeira-700">DIMAP GeoCoder</span>
  <span class="lg:hidden text-xl font-black tracking-tight text-madeira-700">D</span>
</a>

<!-- base.html: widget de usuário — avatar w-9 e texto oculto abaixo de lg -->
<div id="widget-area-usuario"
     class="fixed top-6 right-4 lg:right-6 z-20 glass-panel rounded-full! p-1.5 flex items-center
            lg:gap-3 cursor-pointer transition-glass hover:bg-white/60">
  <div class="w-9 h-9 lg:w-11 lg:h-11 rounded-full bg-rocha-800 …">…</div>
  <div class="hidden lg:block pr-4">…</div>
</div>
```

## Fora de escopo
- Qualquer mudança nos tokens do design system (já entregues junto com o mock validado).
- Comportamento das sugestões/resultado além da largura atual (seguem `w-11/12 max-w-2xl`).
- Autenticação/conteúdo real do widget de usuário (segue estático, SPEC futura de accounts).
- Registro do padrão no SKILL.md da skill `componentes-frontend` (feito fora do ciclo de SPEC).

## Notas de teste
- Visual, por viewport: < 640px, 640–1023px e ≥ 1024px, nos estados hero (sem resultado) e
  compacto (com resultado) — conferir alinhamento da fileira em `top-6` e ausência de sobreposição.
- Caso de borda: resultado presente e viewport redimensionada cruzando o corte de 64rem — a barra
  deve alternar pill ↔ painel sem quebra de layout.

## Patches

_Nenhum patch registrado até o momento._
