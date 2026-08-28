---
spec: design/008
versao: v2
atualizado_em: 2026-08-27
testes_tdd: true
implementado: true
changelog:
  - v1: recalibragem concluída e portada para tema-dimap.dev.css e styleguide
  - v2: o gelo espesso genérico desce para 88%→76% (a 97% lia como papel branco) e o `.btn-glass` acompanha em white/40; a densidade de 97%→88% passa a ser do MODAL, escrita no `.modal-box-glass` — são duas perguntas diferentes, e agora são dois materiais
---

# SPEC design/008 — Recalibragem de opacidade do gelo espesso (.glass-panel-thick) e desfoque do modal

## 1 · User story
O servidor da DIMAP preenche formulários e visualiza dados dentro de modais no contexto de gestão administrativa para ler textos e campos com nitidez sem interferência visual de tabelas, toasts coloridos e alertas em segundo plano.

## 2 · Condições de pronto
- [x] O backdrop do modal (`.modal-glass`) passa de `backdrop-blur-[6px]` para `backdrop-blur-[16px]`, dissolvendo formulários densos, tabelas e toasts coloridos em uma aquarela fosca suave sem escurecer o fundo.
- [x] O material `.glass-panel-thick` e o token primitivo `.glass-bg-thick` têm gradiente denso (`from-white/88 via-white/82 to-white/76`), bloqueando o vazamento de texto e cor de trás da placa **sem deixar de ler como gelo** — quem dissolve o fundo é o desfoque de 28px, não a opacidade.
- [x] O desfoque da placa espessa (`.glass-blur-thick`) passa de 20px para `backdrop-blur-[28px]`, maximizando a suavidade da luz interna.
- [x] O componente `.select-onsen-panel` (popover do select de vidro) consome a nova graduação de gelo espesso, mantendo a consistência de material sobre interface.
- [x] O modal mantém a **terceira densidade** (`from-white/97 via-white/93 to-white/88`, blur 28px, aresta `border-white/80`, brilho de quina `1.0`), agora escrita no próprio `.modal-box-glass` em vez de herdada do `.glass-panel-thick` empilhado no markup — a regra vem depois no arquivo e vence, então nenhum modal muda de HTML.
- [x] A placa espessa preserva a aresta de luz (`border-white/70`), o brilho na quina (`inset 0 1px 0 rgba(255,255,255,0.9)`) e a sombra em duas camadas (azul-rocha profunda e ciano de vida).
- [x] O botão de vidro (`.btn-glass`) acompanha a placa: `bg-white/40`, hover `white/60` — sobre gelo espesso o white/50 anterior encostava na tinta da placa e o botão sumia como figura.
- [x] O design foi aprovado no mock, e a recalibragem foi portada para `static/src/tema-dimap.dev.css` e conferida no styleguide.

## 3 · Domínio
Iteração de design system e tokens de material: nenhum model, nenhuma view e nenhum DTO novo. A pergunta que esta SPEC faz aos materiais existentes:

| Material / Token | Definição anterior | Pergunta desta SPEC |
|---|---|---|
| `.modal-glass` | `bg-transparent! backdrop-blur-[6px]` | "O desfoque de 6px isola formulários com toasts amarelos/vermelhos atrás do modal?"; não, o ruído de alta saturação continua competindo com a leitura do diálogo. 16px dissolve o fundo em aquarela limpa. |
| `.glass-bg-thick` | `from-white/85 via-white/75 to-white/65` | "A cauda de 65% bloqueia a poluição visual de formulários densos?"; não. **v2:** 97%→88% fechava o vazamento mas matava o material — 88%→76% é o ponto em que o fundo some e o gelo permanece gelo. |
| `.glass-blur-thick` | `backdrop-blur-[20px]` | "O desfoque de 20px dispersa com conforto as arestas e textos atrás de uma placa opacificada?"; 28px suaviza a refração de luz. |
| `.glass-panel-thick` | `blur 20px + bg-thick + border-white/70 + shadow` | "A casca composta do modal reflete a densidade necessária?"; a sombra funda (`0 20px 50px`) fica, e a aresta volta a `border-white/70` com brilho de quina `0.9` — **v2**: em `white/80` e `1.0` sobre um gradiente já quase opaco, a quina deixava de ser luz e virava contorno. |
| `.btn-glass` | `bg-white/50`, hover `white/70` | **v2:** "o botão de vidro ainda se separa da placa espessa em que pousa?"; não — dois brancos altos encostados apagam a figura. `white/40` / hover `white/60`. |
| `.modal-box-glass` | `bg-transparent! max-h overflow` (a placa vinha do `.glass-panel-thick`) | **v2:** "o modal quer a mesma densidade de tudo que é espesso?"; **não** — ele não flutua sobre a interface, ele a substitui enquanto está aberto, e o diálogo precisa ganhar de um formulário inteiro. Fica em 97%→88%, escrito aqui. |
| `.select-onsen-panel` | `blur 20px + from-white/85...` | "A lista flutuante de seleção sobrevive à sobreposição de modais e tabelas sem perder leitura?"; bebe da mesma calibragem espessa. |

**Mock:** [008-mock-opacidade-gelo-espesso.html](008-mock-opacidade-gelo-espesso.html) — leia a skill `mock`. Ele é o **laboratório comparativo** desta SPEC: as classes sufixadas (`-antigo`, `-medio`, `-denso`) são os níveis que estiveram em disputa e continuam ali como registro. Os overrides que duplicavam o tema foram removidos no v2 — o mock consome a fonte única, e por isso mostra sempre a calibragem vigente.

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
/* Primitivos da segunda espessura: quem dissolve o fundo é o blur de 28px, não a opacidade */
.glass-blur-thick { @apply backdrop-blur-[28px]; }
.glass-bg-thick   { @apply bg-gradient-to-br from-white/88 via-white/82 to-white/76; }

/* Material composto de gelo espesso: aresta white/70, brilho de quina 0.9 e sombra profunda */
.glass-panel-thick {
  @apply rounded-2xl backdrop-blur-[28px] bg-gradient-to-br from-white/88 via-white/82 to-white/76
         border border-white/70
         shadow-[inset_0_1px_0_rgba(255,255,255,0.9),0_20px_50px_rgba(7,58,84,0.34),0_0_36px_rgba(72,202,228,0.28)];
}

/* Modal: a terceira densidade, a única em que a opacidade alta é o acerto. Vem depois do
   .glass-panel-thick no arquivo, então vence o que o markup empilha — sem tocar em modal algum. */
.modal-box-glass {
  @apply bg-transparent! max-h-[85vh] overflow-y-auto backdrop-blur-[28px]
         bg-gradient-to-br from-white/97 via-white/93 to-white/88 border-white/80
         shadow-[inset_0_1px_0_rgba(255,255,255,1),0_20px_50px_rgba(7,58,84,0.34),0_0_36px_rgba(72,202,228,0.28)];
}

/* Botão de vidro: um degrau abaixo, para continuar figura sobre a placa espessa */
.btn-glass {
  @apply rounded-full backdrop-blur-[10px] bg-white/40 border border-white/60 text-base-content
         shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_2px_8px_rgba(7,58,84,0.38)]
         transition-all duration-300 hover:bg-white/60 hover:shadow-[0_4px_20px_rgba(72,202,228,0.4)];
}

/* Modal de vidro: o fundo agora embaça a 16px, dissolvendo o ruído de formulários e toasts sem escurecer */
.modal-glass { @apply bg-transparent! backdrop-blur-[16px]; }

/* Popover de seleção: mantém o alinhamento com a receita do gelo espesso */
.select-onsen-panel {
  @apply fixed m-0 p-2 overflow-hidden rounded-2xl backdrop-blur-[28px] bg-transparent
         bg-gradient-to-br from-white/88 via-white/82 to-white/76 border border-white/70 text-base-content
         shadow-[inset_0_1px_0_rgba(255,255,255,0.9),0_20px_50px_rgba(7,58,84,0.34),0_0_36px_rgba(72,202,228,0.28)];
  inset: auto;
}
```

## 7 · Caveats
**O desfoque de 16px no backdrop e a placa em 88%→76% reduzem o reconhecimento de elementos em segundo plano.** Isso é a intenção explícita da recalibragem para priorizar a legibilidade do diálogo sobre formulários complexos. Custo: o fundo passa a ser percebido apenas como manchas suaves de luz e cor.

**O v1 aplicou a densidade do modal ao material inteiro, e as outras peças pagaram.** A 97%→88% a placa cumpre a condição de pronto e deixa de ser gelo: sem nada visível atrás, o gradiente vira papel branco, a aresta translúcida perde função e o brilho de quina lê como contorno. No **modal** isso é o acerto — ele substitui a interface enquanto está aberto. Em tudo que apenas **flutua sobre** ela, é regressão de material. O v2 separa os dois. Custo: passam a existir três densidades de gelo em vez de duas, e quem criar peça nova tem de escolher entre elas.

**Peças que herdam a placa espessa continuam em 88%→76% e não foram promovidas à densidade do modal:** o aviso do ato grave (`.botao-aura-aviso`), o clone da linha pinçada (`.table-flutuante-clone`), o trilho da `.chave-onsen` e o popover do `.select-onsen-panel`. O aviso é o caso limítrofe — é um diálogo como o modal, com a mesma justificativa para ser denso. Custo: se ele ficar leve demais na tela, a promoção é uma linha, mas é decisão visual e não foi tomada aqui.

**A calibragem antiga é substituída sem variante.** Não há caso de uso no sistema que demande outro nível de transparência para vidro sobre interface. Custo: se alguma tela futura demandar um gelo semi-espesso intermediário, um novo token precisará ser criado.

**A SPEC não carrega teste automatizado.** O entregável é material e token visual no CSS do design system, sem regras de negócio de domínio em `services/`. Custo: a validação de contraste e translucidez é feita estritamente no mock e no styleguide.

## 8 · Testes (TDD)
Nenhum teste automatizado — ver Caveats.
