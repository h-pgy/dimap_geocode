---
spec: design/008
versao: v1
atualizado_em: 2026-08-18
testes_tdd: true
implementado: true
changelog:
  - v1: recalibragem concluída e portada para tema-dimap.dev.css e styleguide
---

# SPEC design/008 — Recalibragem de opacidade do gelo espesso (.glass-panel-thick) e desfoque do modal

## 1 · User story
O servidor da DIMAP preenche formulários e visualiza dados dentro de modais no contexto de gestão administrativa para ler textos e campos com nitidez sem interferência visual de tabelas, toasts coloridos e alertas em segundo plano.

## 2 · Condições de pronto
- [x] O backdrop do modal (`.modal-glass`) passa de `backdrop-blur-[6px]` para `backdrop-blur-[16px]`, dissolvendo formulários densos, tabelas e toasts coloridos em uma aquarela fosca suave sem escurecer o fundo.
- [x] O material `.glass-panel-thick` e o token primitivo `.glass-bg-thick` têm gradiente denso (`from-white/97 via-white/93 to-white/88`), bloqueando qualquer vazamento de texto e cor de trás da placa.
- [x] O desfoque da placa espessa (`.glass-blur-thick`) passa de 20px para `backdrop-blur-[28px]`, maximizando a suavidade da luz interna.
- [x] O componente `.select-onsen-panel` (popover do select de vidro) consome a nova graduação de gelo espesso, mantendo a consistência de material sobre interface.
- [x] Modais (`.modal-box-glass` + `.glass-panel-thick`) preservam a aresta de luz (`border-white/80`), o brilho na quina (`inset 0 1px 0 rgba(255,255,255,1)`) e a sombra em duas camadas (azul-rocha profunda e ciano de vida).
- [x] O design foi aprovado no mock, e a recalibragem foi portada para `static/src/tema-dimap.dev.css` e conferida no styleguide.

## 3 · Domínio
Iteração de design system e tokens de material: nenhum model, nenhuma view e nenhum DTO novo. A pergunta que esta SPEC faz aos materiais existentes:

| Material / Token | Definição anterior | Pergunta desta SPEC |
|---|---|---|
| `.modal-glass` | `bg-transparent! backdrop-blur-[6px]` | "O desfoque de 6px isola formulários com toasts amarelos/vermelhos atrás do modal?"; não, o ruído de alta saturação continua competindo com a leitura do diálogo. 16px dissolve o fundo em aquarela limpa. |
| `.glass-bg-thick` | `from-white/85 via-white/75 to-white/65` | "A cauda de 65% bloqueia a poluição visual de formulários densos?"; não, subir para 97%→88% fecha o vazamento escuro. |
| `.glass-blur-thick` | `backdrop-blur-[20px]` | "O desfoque de 20px dispersa com conforto as arestas e textos atrás de uma placa opacificada?"; 28px suaviza a refração de luz. |
| `.glass-panel-thick` | `blur 20px + bg-thick + border-white/70 + shadow` | "A casca composta do modal reflete a densidade necessária?"; alinha aresta (`border-white/80`) e profundidade de sombra com o novo peso leitoso. |
| `.select-onsen-panel` | `blur 20px + from-white/85...` | "A lista flutuante de seleção sobrevive à sobreposição de modais e tabelas sem perder leitura?"; bebe da mesma calibragem espessa. |

**Mock:** [008-mock-opacidade-gelo-espesso.html](008-mock-opacidade-gelo-espesso.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Alteração do `.glass-panel` fino (`from-white/65 via-white/45 to-white/30`, `backdrop-blur-[10px]`), calibrado especificamente para flutuar direto sobre a água límpida do mapa.
- Adição de véu escuro (`bg-black/*` ou escurecimento de cena) no `.modal-glass`: o Onsen de Inverno veda expressamente escurecer o fundo.
- Alteração da gaveta lateral (`.glass-drawer-panel`), que possui calibragem direcional própria (`bg-gradient-to-l`).
- Alteração do comportamento funcional ou HTML dos modais de unidade e servidor.

## 5 · Peças de referência a compor
- `@static/src/tema-dimap.dev.css` → `.modal-glass`, `.glass-bg-thick`, `.glass-blur-thick`, `.glass-panel-thick`, `.select-onsen-panel`: tokens e materiais a recalibrar.
- `@templates/user_admin/partials/_modal_editar_perfil.html` → markup de referência de modal denso sobre interface.
- `@templates/user_admin/partials/_modal_editar_unidade.html` → markup de referência de modal sobre interface.
- `@.claude/skills/componentes-frontend/examples/design_system.html` → styleguide vivo (contrato visual do projeto).
- Skills: `componentes-frontend`, `mock`.

## 6 · Snippets

**`static/src/tema-dimap.dev.css`**
```css
/* Primitivos da segunda espessura: gelo denso e difusão profunda para sobrepor interface e toasts */
.glass-blur-thick { @apply backdrop-blur-[28px]; }
.glass-bg-thick   { @apply bg-gradient-to-br from-white/97 via-white/93 to-white/88; }

/* Material composto de gelo espesso: aresta white/80, brilho de quina reforçado e sombra profunda */
.glass-panel-thick {
  @apply rounded-2xl backdrop-blur-[28px] bg-gradient-to-br from-white/97 via-white/93 to-white/88
         border border-white/80
         shadow-[inset_0_1px_0_rgba(255,255,255,1),0_20px_50px_rgba(7,58,84,0.34),0_0_36px_rgba(72,202,228,0.28)];
}

/* Modal de vidro: o fundo agora embaça a 16px, dissolvendo o ruído de formulários e toasts sem escurecer */
.modal-glass { @apply bg-transparent! backdrop-blur-[16px]; }
.modal-box-glass { @apply bg-transparent! max-h-[85vh] overflow-y-auto; }

/* Popover de seleção: mantém o alinhamento com a receita do gelo espesso */
.select-onsen-panel {
  @apply fixed m-0 p-2 overflow-hidden rounded-2xl backdrop-blur-[28px] bg-transparent
         bg-gradient-to-br from-white/97 via-white/93 to-white/88 border border-white/80 text-base-content
         shadow-[inset_0_1px_0_rgba(255,255,255,1),0_20px_50px_rgba(7,58,84,0.34),0_0_36px_rgba(72,202,228,0.28)];
  inset: auto;
}
```

## 7 · Caveats
**O desfoque de 16px no backdrop e a placa em 97%→88% reduzem o reconhecimento de elementos em segundo plano.** Isso é a intenção explícita da recalibragem para priorizar a legibilidade do diálogo sobre formulários complexos. Custo: o fundo passa a ser percebido apenas como manchas suaves de luz e cor.

**A calibragem antiga é substituída sem variante.** Não há caso de uso no sistema que demande o nível anterior de transparência para vidro sobre interface. Custo: se alguma tela futura demandar um gelo semi-espesso intermediário, um novo token precisará ser criado.

**A SPEC não carrega teste automatizado.** O entregável é material e token visual no CSS do design system, sem regras de negócio de domínio em `services/`. Custo: a validação de contraste e translucidez é feita estritamente no mock e no styleguide.

## 8 · Testes (TDD)
Nenhum teste automatizado — ver Caveats.
