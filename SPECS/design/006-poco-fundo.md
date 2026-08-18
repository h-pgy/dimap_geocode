---
spec: design/006
versao: v1
atualizado_em: 2026-08-17
testes_tdd: true
implementado: true
changelog:
  - v1: versão inicial
---

# SPEC design/006 — Profundidade do vidro sobre placa

## 1 · User story
O servidor da DIMAP distingue as seções, os campos e os controles dentro de um painel administrativo
para localizar o que procura, e o que pode acionar, sem reler a tela inteira.

## 2 · Condições de pronto
- [ ] Um poço assentado sobre placa de gelo **se lê como degrau**: a superfície do poço se separa da
      placa que o carrega.
- [ ] Um campo de vidro **tem poço em repouso**, não só ao receber foco.
- [ ] Um botão de vidro assentado sobre placa **se lê como levantado**.
- [ ] As peças **não mudam de material**: a recalibragem altera sombra e aresta, nunca blur, raio ou
      gradiente.
- [ ] Todas as peças do tier raso passam a ter **a mesma profundidade** — nenhuma fica para trás.
- [ ] A profundidade do poço existe **num só lugar por escala**: alterá-la é editar um valor, não seis.
- [ ] Peça de **24px** não recebe a profundidade de poço de seção: o sulco desenha degrau, não lava a
      altura inteira de escuro.
- [ ] O design foi aprovado no **mock**, e a recalibragem foi portada para
      `static/src/tema-dimap.dev.css` e conferida no styleguide.

## 3 · Domínio
Iteração de design: nenhum model, nenhuma migração, nenhum DTO. O tema tem hoje quatro tiers de
profundidade, e a pergunta que esta SPEC faz a eles:

| tier | peças | valor |
|---|---|---|
| raso | `.card-well`, `.upload-well`, `.toggle-onsen`, `.calha-cobertura`, campos do `.campo-onsen` e do `.painel-onsen` | `inset 0 2px 6px /0.15` |
| fundo | `.scroll-etched`, `.th-onsen` filtrado | `/0.28` |
| escavado | `.card-unidade-poco`, `.card-unidade-ego` | `/0.32` |
| marca | `.paint-well`, `.dot-unidade`, `.paint-well-atual` | `/0.45`–`/0.5` |

- Tier raso — "quantos usuários esta calibragem tem sobre o mapa?"; nenhum: as seis peças aparecem
  só em `user_admin/`, sempre dentro de uma `.glass-panel`.
- Tiers fundo e escavado — "qual profundidade já se lê sobre placa hoje?"; é deles que sai a escala
  do tier recalibrado.
- `.input-glass`, `.select-glass`, `.file-input-glass` — "o campo tem poço em repouso?"; não tem
  sombra alguma antes do foco, e sobre a placa fica mais claro que o próprio fundo.
- `.btn-glass` — "qual é o relevo calibrado para botão sobre o mapa?"; sombra larga e clara, que
  separa do mapa e vira véu sobre a placa.

**Mock:** [006-mock-poco-fundo.html](006-mock-poco-fundo.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Os tiers fundo, escavado e marca: já se leem sobre placa.
- Poço dentro de poço: a `.tarja-vinculo` (SPEC user_admin/015) já é a placa assentada em poço.
- `.btn-onsen` e `.btn-criar-inline`: têm gradiente próprio e não dependem de sombra para separar —
  sem dono ainda.
- Uma variante rasa para poço sobre o mapa, quando houver a primeira tela que precise dela — sem
  dono ainda.

## 5 · Peças de referência a compor
- `@static/src/tema-dimap.dev.css` → `--radius-placa`: o idioma de valor compartilhado do tema,
  definido uma vez e consumido por `var()`.
- `@static/src/tema-dimap.dev.css` → `.card-unidade-poco`: a profundidade que já se lê sobre placa,
  com o fio de luz na aresta de baixo.
- `@.claude/skills/componentes-frontend/examples/design_system.html`: o styleguide, contrato visual
  do projeto.
- Skills: `componentes-frontend`, `mock`.

## 6 · Snippets

**`static/src/tema-dimap.dev.css`** — a profundidade vira valor nomeado, ao lado do `--radius-placa`.
```css
/* Um valor por escala: a divergência entre os poços do sistema era livre enquanto o número estava
   copiado em cada peça. O segundo inset é o lábio de luz — sem ele a sombra afunda a peça sem
   desenhar a quina, e o degrau não fecha. */
--sombra-poco: inset 0 2px 7px rgba(7, 58, 84, 0.38), inset 0 -1px 0 rgba(255, 255, 255, 0.8);
/* Mesma língua, outra escala: num pill de 24px o blur de 7px lava a altura inteira em vez de
   desenhar um degrau. Trilho do toggle e calha da cobertura bebem daqui. */
--sombra-poco-fina: inset 0 1px 3px rgba(7, 58, 84, 0.3), inset 0 -1px 0 rgba(255, 255, 255, 0.7);
```

**`static/src/tema-dimap.dev.css`** — os consumidores. `box-shadow` direto, como o `.tarja-vinculo`
faz com o raio: `@apply shadow-[…]` embrulharia o valor na maquinaria de cor do Tailwind.
```css
.card-well {
  @apply rounded-2xl bg-white/30 border border-white/45;
  box-shadow: var(--sombra-poco);
}

/* O campo ganha poço em REPOUSO. No foco o anel de água entra por cima do poço, não no lugar dele:
   sem o inset repetido aqui, focar o campo o desafundaria. Vale igual para .select-glass e
   .file-input-glass, que são a mesma receita. */
.input-glass {
  @apply w-full rounded-xl bg-white/30 border-rocha-900/15 text-base-content
         placeholder:text-rocha-700/60 backdrop-blur-[10px] transition-all duration-300
         focus:bg-white/45 focus:border-agua-500 focus:outline-none;
  box-shadow: var(--sombra-poco);
}
.input-glass:focus {
  box-shadow: var(--sombra-poco), 0 0 0 3px rgba(0, 150, 199, 0.2), 0 0 20px rgba(72, 202, 228, 0.35);
}

/* O oposto do poço: aqui a peça LEVANTA. A sombra fecha e escurece porque sombra larga e clara só
   separa contra o mapa; sobre a placa ela vira véu. Fica na mesma tinta do --sombra-poco, mas não
   bebe dele: a geometria é outra (externa, não inset), e só a opacidade coincide. */
.btn-glass {
  @apply rounded-full backdrop-blur-[10px] bg-white/50 border border-white/60 text-base-content
         transition-all duration-300 hover:bg-white/70;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8), 0 2px 8px rgba(7, 58, 84, 0.38);
}
```

**`static/src/tema-dimap.dev.css`** — duas regras descendentes saem. Elas existiam para dar poço aos
campos dentro do `.campo-onsen` e do `.painel-onsen`, que o `.input-glass` não tinha; agora ele tem,
e o `border-white/45!` delas desfaria a aresta escura nova.
```css
/* REMOVIDAS */
.campo-onsen-campo  :where(input, select, .select-onsen-trigger) { … }
.painel-onsen-corpo :where(input, select, .select-onsen-trigger) { … }
```

**`static/src/tema-dimap.dev.css`** — os átomos de gravação sobre placa declaram a própria tinta, em
vez de esperar `.etched-deeper` empilhado no markup. Ambos vêm depois do `.etched` e têm a mesma
especificidade, então vencem.
```css
/* Glifo dentro de botão de vidro e seta de ordenação moram sempre sobre placa: a tinta de repouso
   do .etched não se lê ali, e um glifo novo tem que nascer legível. */
.icon-etched { @apply text-[15px] leading-none; color: rgba(13, 27, 42, 0.3); }
.sort-etched { color: rgba(13, 27, 42, 0.3); }
.sort-etched:hover { color: rgba(13, 27, 42, 0.45); }
```

**`static/src/tema-dimap.dev.css`** — a tabela: o sulco da barra passa a ser mais fundo que o poço
que o contém, a sombra do cabeçalho perde a aresta e as linhas ganham separação.
```css
/* Sulco cavado no fundo de uma bacia não pode ler mais claro que a bacia (--sombra-poco é 0.38). */
.scroll-etched { box-shadow: inset 0 2px 5px rgba(7, 58, 84, 0.45), inset 0 -1px 0 rgba(255, 255, 255, 0.7); }

/* Sem backdrop-filter: ele NÃO é atenuado por mask-image (Chromium aplica na caixa inteira e corta
   a seco), e o degrau entre o borrado e o nítido lia como aresta dura. Sem o blur, a máscara
   vertical também sai — ela multiplicaria um gradiente que já cai sozinho até zero. */
.table-onsen thead th::after { /* só o gradiente, h-14 */ }

/* Um fio de tinta ACIMA da aresta branca: sozinha, a luz sobre gelo claro não separa. */
.table-onsen tbody td { box-shadow: inset 0 -2px 0 -1px rgba(7, 58, 84, 0.09); }
```

## 7 · Caveats
**A calibragem antiga desaparece em vez de virar variante.** As seis peças do tier raso não têm
nenhum uso sobre o mapa hoje, e guardar um `-raso` sem usuário seria inventar peça para o styleguide
manter. Custo: a primeira tela que puser um desses poços sobre o mapa vai precisar recriar a
variante, e quem a escrever não terá o valor antigo à mão — ele estará só no git.

**O `.btn-glass` e o `.input-glass:focus` repetem sombra que já existe.** `box-shadow` é uma
propriedade só: quem sobrescreve uma camada leva junto as outras. Custo: o brilho de quina do botão
e o poço do campo em foco passam a existir em dois lugares cada, livres para divergir do original.

**A ordem no arquivo decide a tinta dos átomos de gravação.** `.icon-etched` e `.sort-etched` vencem
o `.etched` por virem depois, com a mesma especificidade, e não por serem mais específicos. Custo:
mover qualquer um deles para cima do `.etched` devolve a tinta rasa sem erro nenhum, nem no build
nem no console — a mesma fragilidade dos poços.

**A SPEC não carrega teste automatizado.** O entregável é material do design system, sem
comportamento observável em `services/`, e um teste que afirme o conteúdo do CSS quebra a cada
ajuste de valor sem proteger nada. Custo: a regressão destas peças só aparece para quem olhar a tela.

## 8 · Testes (TDD)
Nenhum teste automatizado — ver Caveats.
