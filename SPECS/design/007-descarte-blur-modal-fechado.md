---
spec: design/007
versao: v1
atualizado_em: 2026-08-18
testes_tdd: true
implementado: true
markers_obrigatorios: []
changelog:
  - v1: versão inicial
---

# SPEC design/007 — Neutralização de desfoque fantasma em modais fechados

## 1 · User story
O servidor da DIMAP fecha qualquer modal da interface no contexto de gestão ou consulta para retomar a visualização da tela limpa sem retenção de manchas ou artefatos residuais de desfoque.

## 2 · Condições de pronto
- [x] Ao fechar qualquer modal baseado em `.modal-glass` ou `.modal-toggle`, nenhum elemento descendente com `backdrop-filter` retém camada ativa de renderização na GPU.
- [x] Modais com toggle nativo desmarcado (`.modal-toggle:not(:checked) + .modal`) têm `backdrop-filter: none !important;` aplicado a si e a todos os seus descendentes pelo CSS do tema.
- [x] Modais fechados sem toggle (`.modal:not(.modal-open):not([open]):not(:has(.modal-toggle:checked))`) têm `backdrop-filter: none !important;` aplicado a si e a todos os seus descendentes.
- [x] Ao fechar o modal de edição do servidor carregado via HTMX no poço `#poco-modal`, a tela não exibe retângulos ou resíduos de desfoque sobre a placa administrativa ou sobre o mapa.
- [x] O comportamento visual, a transparência e as transições do modal em estado aberto permanecem inalterados.

## 3 · Domínio
Iteração de design system e folha de estilos: nenhum model, nenhuma migração, nenhum DTO de domínio. A pergunta que esta SPEC faz às peças existentes:

- `.modal-glass` ([`SPEC user_admin/012`](SPECS/user_admin/012-design-formulario-unidade.md)): "o modal fechado ainda retém filtros de desfoque de fundo?"; sim, o daisyUI 5 oculta `.modal` com `visibility: hidden` e `opacity: 0`, mantendo nós com `backdrop-filter` no layout e gerando retenção de textura na GPU (Chromium/Windows).
- `.modal-box-glass` e `.glass-panel-thick`: "a placa interna do modal desativa seu desfoque quando o modal é fechado?"; não, a placa retém `backdrop-blur-[20px]`.
- `.select-onsen-panel` e `.btn-glass`: "os controles internos do modal desativam seus desfoques ao fechar o diálogo?"; não, popovers e botões mantêm seus respectivos filtros de vidro ativos enquanto o markup persistir no DOM.

## 4 · Fora de escopo
- Substituição da biblioteca daisyUI ou refatoração dos diálogos para a tag nativa `<dialog>`.
- Alteração das receitas de vidro (`.glass-panel`, `.glass-panel-thick`, `.btn-glass`) quando o modal está em estado aberto.
- Gerenciamento de ciclo de vida de remoção física de nós do DOM via JavaScript além das regras CSS declarativas de apresentação.

## 5 · Peças de referência a compor
- `@static/src/tema-dimap.dev.css` → `.modal-glass`, `.modal-box-glass`: classes de modal de vidro e poço no design system.
- `@templates/user_admin/perfil.html` → `#poco-modal`: poço de injeção dinâmica de modal via HTMX.
- Skills: `componentes-frontend`, `daisyui`.

## 6 · Snippets

**`static/src/tema-dimap.dev.css`**
```css
/* Neutralização de artefato de GPU (Chromium/Windows): quando o modal está fechado
   (toggle desmarcado ou ausência de .modal-open/[open]), força o descarte do backdrop-filter
   em toda a subárvore para impedir retenção da textura de blur na memória de vídeo. */
.modal-toggle:not(:checked) + .modal,
.modal-toggle:not(:checked) + .modal *,
.modal:not(.modal-open):not([open]):not(:has(.modal-toggle:checked)),
.modal:not(.modal-open):not([open]):not(:has(.modal-toggle:checked)) * {
  backdrop-filter: none !important;
}
```

## 7 · Caveats
**A SPEC não carrega teste automatizado.** O entregável é uma regra declarativa de CSS do design system (`tema-dimap.dev.css`) voltada a neutralizar comportamento de renderização de GPU do navegador (Chromium/Windows), sem regra de negócio em `services/`, models ou contratos de DTO. Um teste que apenas verifique texto no arquivo CSS traria acoplamento frágil sem testar a composição real da GPU. Custo: a validação é visual no navegador.

## 8 · Testes (TDD)
Nenhum teste automatizado — ver Caveats.
