---
spec: design/009
versao: v3
atualizado_em: 2026-08-28
testes_tdd: true
implementado: true
changelog:
  - v1: versão inicial
  - v2: "[bugfix] a bandeja da tabela de vidro subiu para 88%→76%: sem a tinta do poço aninhado atrás, o cabeçalho grudento deixava as linhas emergirem legíveis por trás dele"
  - v3: "[bugfix] bandeja em 94%→86% e cabeçalho rente ao poço: a folga do topo e das laterais saiu das tabelas com cabeçalho, e a bandeja passou a atravessar a coluna da barra de rolagem"
---

# SPEC design/009 — Vidro sobre vidro: a placa aninhada

## 1 · User story
O servidor da DIMAP lê a página de uma unidade e o organograma dentro dela no contexto da área
administrativa para distinguir as superfícies empilhadas umas das outras em vez de ver um bloco
branco único.

## 2 · Condições de pronto
- [ ] Uma `.glass-panel` renderizada **dentro** de outro material de vidro **não pinta fundo algum**;
      a de fora segue em `65 → 45 → 30`.
- [ ] A placa aninhada continua sendo peça: mantém o desfoque, a aresta e a sombra da placa comum, e
      é por eles que ela se separa da superfície de baixo.
- [ ] A regra vale para **qualquer profundidade**: a terceira e a quarta placa empilhadas não ficam
      mais brancas que a segunda.
- [ ] Uma `.glass-panel` dentro de um `.card-well` também perde a pintura: o poço é superfície, e a
      placa sobre ele é empilhamento.
- [ ] Um `.card-well` aninhado perde o `bg-white/30` e fica com o degrau (`--sombra-poco`) e a
      aresta: profundidade é o que descreve um poço.
- [ ] O `.modal-box-glass` nunca é alcançado pela regra: a caixa do modal mantém a terceira densidade
      (`97 → 93 → 88`) em qualquer contexto em que apareça.
- [ ] O `.card-unidade` em repouso, a três níveis de profundidade no organograma, deixa de ler como
      branco chapado e mantém o contraste com o estado escavado (`.card-unidade-poco`).
- [ ] Nenhum template da aplicação muda de HTML: o mesmo partial renderizado dentro ou fora de uma
      placa se ajusta sozinho.
- [ ] O design foi aprovado no mock, e a regra foi portada para `static/src/tema-dimap.dev.css` e
      registrada no styleguide antes de qualquer template consumi-la.

## 3 · Domínio
Iteração de design system e tokens de material: nenhum model, nenhuma view e nenhum DTO. A pergunta
que esta SPEC faz aos materiais existentes:

| Material | Definição vigente | Pergunta desta SPEC |
|---|---|---|
| `.glass-panel` | `blur 18px + from-white/65 via-white/45 to-white/30 + aresta white/60 + sombra em duas camadas` | "A placa sabe que pode existir outra placa atrás dela?"; não — a translucidez é multiplicativa e o empilhamento fecha o material: duas placas dão 88% de branco no canto claro, três dão 96%, quatro dão 98%. A pintura é o que se repete; o desfoque, a aresta e a sombra descrevem a placa sozinhos. |
| `.card-well` | `bg-white/30 + var(--sombra-poco)` | "Placa sobre poço é o mesmo caso?"; sim, nos dois sentidos — o poço é mais uma superfície entre a placa de dentro e o fundo, e ele mesmo, empilhado, soma 30% de branco que o degrau já dava conta de dizer. |
| `.modal-box-glass` | `blur 28px + from-white/97 via-white/93 to-white/88 + aresta white/80` | "A caixa do modal cede a pele quando algo a contém?"; nunca — ela não flutua sobre a interface, substitui a interface, e a densidade alta é a razão de ela existir. |
| `.card-unidade-repouso` | compõe `.glass-panel` no markup | "O card do organograma quer ser exceção?"; não — ele compõe a placa porque **é** placa, e o que o cega é a profundidade em que vive, não a peça. |

A profundidade não é atributo do fragmento: o mesmo `_no_arvore.html` renderiza a três níveis em
`unidades_list.html`, a três em `unidade.html` e dentro de um poço em `_seletor_unidade_alvo.html`, e
as seções de `perfil.html` são alvo de swap fora de banda. Quem conhece a profundidade é o DOM, e é
de lá que a regra a lê.

**Mock:** [009-mock-vidro-sobre-vidro.html](009-mock-vidro-sobre-vidro.html) — leia a skill `mock`.

## 4 · Fora de escopo
- `.glass-panel-thick` aninhada: a regra alcança só `.glass-panel`, e o único caso hoje é o polegar
  da `.chave-onsen` — sem dono ainda.
- Revisão do invólucro `.glass-panel` que embrulha as páginas administrativas inteiras
  (`perfil.html`, `unidade.html`, `unidades_list.html`) — sem dono ainda.
- `.glass-drawer-panel` e `.glass-panel-deep` aninhados: sem ocorrência no sistema — sem dono ainda.
- `.upload-well`: é poço com tinta própria (`bg-white/30` declarado nele), então aninhado ele
  continua pintando enquanto o `.card-well` ao lado não — sem dono ainda.

## 5 · Peças de referência a compor
- `@static/src/tema-dimap.dev.css` → `.glass-panel`, `.glass-bg`, `.glass-edge`, `.glass-shadow`: a
  placa e os primitivos de que a variante aninhada é feita.
- `@templates/unidades/partials/_no_arvore.html` → o organograma recursivo: o fragmento que renderiza
  em três profundidades diferentes.
- `@templates/user_admin/perfil.html` → placa de página com seções incluídas dentro.
- `@templates/competencias/partials/_seletor_unidade_alvo.html` → poço com placa e organograma dentro.
- `@.claude/skills/componentes-frontend/examples/design_system.html` → styleguide vivo.
- Skills: `componentes-frontend`, `mock`.

## 6 · Snippets

**`static/src/tema-dimap.dev.css`**
```css
@layer components {
  /* A placa aninhada: o material é pintado UMA vez por pilha. Empilhada, a placa continua sendo
     placa pelo que não se repete — o desfoque (que compõe com o da de baixo), a aresta de luz e a
     sombra.

     Os dois :where() zeram a especificidade do que envolvem, então a regra fica em (0,1,0) — igual
     à do .glass-panel base — e vence só por vir depois no arquivo; uma utility no markup continua
     ganhando das duas quando alguém precisar de escape local.

     O combinador de descendência resolve a profundidade inteira num seletor só: nível 3 e nível 4
     caem aqui do mesmo jeito que o nível 2, e não existe .glass-panel .glass-panel .glass-panel.

     .card-well entra no prefixo: rebaixado ou não, ele é mais uma superfície no caminho até o fundo.
     .modal-box-glass sai pelo :not() — a caixa do modal mantém a pele onde quer que esteja. E a
     regra não alcança .glass-panel-thick: o polegar da .chave-onsen segue intocado. */
  :where(.glass-panel, .glass-panel-thick, .glass-drawer-panel, .modal-box-glass, .card-well)
  .glass-panel:where(:not(.modal-box-glass)) {
    @apply bg-none;
  }
  /* O poço aninhado perde a tinta e fica com o degrau: profundidade é o que descreve um poço. */
  :where(.glass-panel, .glass-panel-thick, .glass-drawer-panel, .modal-box-glass, .card-well)
  .card-well {
    @apply bg-transparent;
  }
}
```

Nem o desfoque, nem a aresta, nem a sombra são redeclarados: as regras apagam **só** a pintura, e
todo o resto continua vindo das peças base.

## 7 · Caveats

**A regra age à distância: quem lê o markup vê `.glass-panel` e não sabe qual das duas peles vai
sair.** A profundidade é a única informação que o fragmento não tem como carregar — ele é incluído em
três lugares diferentes e é alvo de swap HTMX —, então lê-la do DOM é o que mantém partial resolvendo
domínio e não apresentação. Custo: as duas peles precisam estar renderizadas lado a lado no
styleguide, porque a classe no markup deixou de descrever sozinha o que aparece na tela.

**A mesma peça passa a ter duas aparências conforme onde é renderizada.** É a intenção da regra, mas
inverte a leitura de quem valida um componente isolado: a placa conferida sozinha no styleguide não é
a que a página mostra. Custo: revisão de peça nova passa a exigir os dois contextos.

**Cada nível empilhado continua com o seu próprio `backdrop-filter`.** Manter o desfoque é o que dá
sentido físico ao vidro sobre vidro, e cada camada compõe com a de baixo. Custo: o organograma
instancia um `backdrop-filter` por card de unidade, e é a tela onde uma árvore larga pode pesar na
GPU.

**Peças já implementadas mudam de aparência sem serem tocadas.** Quinze placas e cinquenta e dois
poços aninhados passam a receber a variante por consequência da regra, não por decisão própria — o
`.card-unidade` em repouso, as células da bandeja de indicadores, o poço das tabelas, o trilho da
`.chave-onsen` e a face afundada do `.botao-aura`. Custo: a validação de todas elas passou a depender
do mock desta SPEC, e nenhuma tem teste que acuse regressão.

**Nenhum teste automatizado.** O entregável é material e token visual no CSS do design system, sem
regra de negócio em `services/`. Custo: a validação de contraste e translucidez acontece
estritamente no mock e no styleguide.

## 8 · Testes (TDD)
Nenhum teste automatizado — ver Caveats.
