---
spec: autorizacao/006
versao: v1
atualizado_em: 2026-08-07
testes_tdd: false
implementado: false
changelog:
  - v1: versão inicial
---

# SPEC autorizacao/006 — Ícones das ações e renderização do menu

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como usuário da plataforma, quero ver as ações disponíveis para mim como itens legíveis e coerentes
com o resto da interface, para reconhecer o que posso fazer sem precisar ler tudo — e como
desenvolvedor, quero que uma ação nova traga só o desenho do seu glifo, sem inventar tela.

## Critérios de aceite
- [ ] O ícone de uma ação é localizado **por convenção** a partir do slug e da variante, sem caminho
      escrito em lugar nenhum além do resolvedor.
- [ ] O SVG é **inserido inline** e herda a cor do texto — o ícone acompanha hover, foco e a tinta do
      contexto.
- [ ] Ação sem o arquivo declarado **não quebra a tela**: cai num glifo genérico do design system.
- [ ] Ler o mesmo ícone várias vezes na mesma página **não relê o disco**.
- [ ] O menu renderiza a saída do router (SPEC 005) compondo **átomo → molécula → organismo**, sem
      nenhuma marcação solta e sem token novo fora do design system.
- [ ] A mesma ação é renderizável em **duas formas** — linha compacta e cartão explicativo —, e quem
      escolhe é o menu, não a ação.
- [ ] Menu sem item liberado exibe **estado vazio**, não um painel quebrado.
- [ ] O design foi **aprovado no mock** antes de qualquer código de aplicação.
- [ ] As peças novas estão renderizadas no styleguide e suas classes migraram para o CSS base.

## Mock de validação
`SPECS/autorizacao/006-mock-icones-e-menu.html` — mostra o átomo de ícone nas duas variantes e nas
duas peles (aceso e gravado), as **duas formas** do item (linha compacta e cartão explicativo) nos
seus estados (repouso, hover, tooltip, ícone ausente) e o organismo do menu montado sobre o mapa
vivo: na forma de lista, na forma de cartões e sem nenhum item.

Servir com root na **raiz do projeto** (Live Server). Via `file://` o fetch do tema é bloqueado.

## Contexto e decisões de arquitetura

Esta SPEC dá corpo visual ao que a SPEC 005 resolve em memória. É a primeira de interface do épico,
por isso vem com mock (skill `specs`).

**Escopo maior do que "ícones".** Entregar só o átomo de ícone não seria iteração exercitável — não
dá para aprovar um glifo fora do lugar onde ele vive. A SPEC vai até o organismo: ícone, item e
menu. A tela que *consome* o menu é a SPEC 007.

**Inline, não `<img>`.** Com `<img src>` o SVG não herda `currentColor`: o ícone deixaria de
acompanhar o hover que acende o gelo e a tinta do contexto, e viraria um PNG glorificado dentro de
um design system inteiramente tokenizado. Inline custa ler o arquivo no render — pago com cache em
memória, no mesmo idioma dos catálogos de `services/domain`.

**A ação é dona do desenho; o design system é dono da renderização.** O átomo aplica tamanho e
amarra o traço do SVG a `currentColor`; a pele continua vindo dos átomos que já existem
(`.icon-glow` para o registro aceso, `.icon-etched` dentro de botão de vidro). Assim uma ação nova
não consegue introduzir cor, sombra ou tamanho fora dos tokens nem se quiser — que é o ponto do §3.4.

**O átomo de ícone não declara `color`.** Quem normaliza é o `stroke` do SVG, não o elemento: uma
declaração de cor no átomo venceria por ordem de cascata a pele empilhada — `.icon-glow` é
`text-agua-600` — e o brilho sumiria sem erro nenhum. A cor vem sempre de fora, seja da pele, seja
do contexto.

**O caminho do ícone já é convenção declarada — o resolvedor não a redeclara.** O gabarito vive em
`apps/competencias/checks.py` desde a SPEC 001, e é o que o system check usa para cobrar o arquivo.
Duas cópias divergiriam em silêncio: o check aprovaria um caminho e o resolvedor leria outro.

**Nome de ação é título, e título é madeira.** O conceito do design system reserva a madeira quente
aos títulos — é o único calor orgânico da cena, contra a rocha fria do corpo. Cartão e item nomeiam
a ação, então o nome vai em `madeira-700`; `rocha-950` fica para corpo e subtítulo, como manda a
tabela tipográfica.

**Acender é gesto, não repouso.** O §5 do design system define que o hover **acende** o gelo; um
menu cujos ícones já nascem acesos não deixa nada para o hover fazer e vira uma parede de ciano sem
hierarquia. No hover e no foco o glifo recebe a água e o brilho; em repouso, a linha compacta o
deixa herdar a tinta do item e o cartão o deixa **gravado no gelo** — a mesma tinta do
`.icon-etched`, sem o brilho dele, e com o filtro da **medida grande**, porque os deslocamentos da
gravação são px absolutos e no glifo de 48px o sulco da medida pequena vira um fio. O `.icon-glow`
estático continua valendo para o ícone solitário; o que muda é que lista não é lugar de ícone
permanentemente aceso.

A pele do ícone dentro de item e cartão é, por isso, uma classe própria — `.icone-acao-acende` —, e
não `.icon-glow` empilhado: quem acende é o hover do item, não o glifo.

No cartão a gravação não contraria a regra de que ela nunca carrega informação: quem nomeia a ação é
o título, e o glifo é identificação secundária que ganha legibilidade plena no hover.

**Duas formas do mesmo item, escolhidas pelo menu.** A linha compacta serve o menu estreito; o
cartão traz para a superfície o texto que na linha só existe como tooltip — é o que torna a ação
autoexplicativa onde há espaço. As duas leem o mesmo contrato, e quem escolhe é o `ItemDeMenu`, como
já escolhe a variante de ícone (SPEC 005). Deixar a ação escolher sua forma furaria o "o menu pinça
a ação".

**O cartão usa `hover-3d` do daisyUI, e isso impõe três restrições.** O componente exige nove filhos
diretos — conteúdo mais oito zonas de detecção — e conteúdo não-interativo; por isso o elemento
clicável é o `<a>` de fora, nunca um botão dentro. O material do cartão é `.card-well`, não vidro:
`backdrop-filter` dentro de elemento com transform 3D reamostra o fundo errado e o blur descola da
peça durante o tilt. E **nenhuma classe do projeto pode declarar `display` no elemento `.hover-3d`**:
ele é `inline-grid` e posiciona as zonas por `grid-area` numa grade 3×3 — trocar o display derruba a
detecção por quadrante e sobra só o `scale`, que parece um cartão pulando para a frente sem
inclinar.

**Fallback em vez de buraco.** Arquivo ausente já é erro de system check no boot (SPEC 001); em
runtime, um glifo genérico degrada melhor do que um vazio no meio do menu.

**Nenhum token novo.** As peças compõem escalas, materiais de vidro e tipografia existentes. Se o
mock pedir cor ou sombra nova, é sinal de que a peça está errada, não de que falta token.

## Peças de referência a compor
- `@apps/competencias/menus.py` (SPEC 005) → `MenuResolvido` e `ItemRenderizavel`: o organismo
  renderiza essa saída, sem recalcular autorização — a linha usa o nome curto, o cartão o nome e o
  tooltip.
- `@apps/competencias/checks.py` (SPEC 001) → `GABARITO_CAMINHO_ICONE`: a convenção de caminho já
  existe e é reusada, não reescrita.
- Skill `componentes-frontend` → `.glass-panel`, `.card-well`, `.icon-glow`, `.icon-etched`,
  `.text-overline`, `.btn-glass`: as peles do item e do painel saem daqui.
- `@services/domain/warmup.py`: idioma de cache em memória aquecido no processo web.
- `@templates/partials/_filtros_gravacao.html`: os `defs` do filtro de gravação já vêm no
  `base.html` — `.icon-etched` depende deles.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md

# apps/competencias/icones.py — o gabarito vem de checks.py (SPEC 001); aqui não se redeclara.
class ResolvedorIcones:
    """Slug + variante → markup do SVG, cacheado por processo."""

    def __call__(
        self,
        slug: str,
        variante: VarianteIcone,
    ) -> str: ...
```

```html
<!-- átomo: normaliza a caixa; quem acende é o hover do item, não o glifo em repouso -->
<span class="icone-acao icone-acao-pequeno icone-acao-acende">{{ svg|safe }}</span>
```

## Fora de escopo
- A tela que consome o menu e a primeira ação registrada (SPEC 007).
- Gaveta da entidade territorial.
- Desenhar os glifos das ações: esta SPEC entrega o mecanismo e um glifo genérico de fallback.
- Ícone colorido ou com mais de duas variantes.
- Invalidação do cache de SVG sem reiniciar o processo.

## Porte obrigatório após a aprovação do mock
As classes novas migram **tal e qual** para `static/src/tema-dimap.dev.css` (fonte única, SPEC
design/004), e cada peça nova é renderizada em
`.claude/skills/componentes-frontend/examples/design_system.html`, na seção da sua camada. A SPEC não
está implementada enquanto os dois portes não tiverem sido feitos.

## Testes (TDD)
Rodam na suíte padrão. O resolvedor é o que tem comportamento a fixar; a aprovação do desenho é o
mock, não teste automatizado.

- `test_resolvedor_localiza_icone_por_convencao` — slug e variante produzem o caminho esperado e
  devolvem o markup do arquivo.
- `test_resolvedor_cai_no_glifo_generico_sem_arquivo` — variante sem arquivo devolve o fallback em
  vez de erro.
- `test_resolvedor_le_o_disco_uma_vez_por_icone` — a segunda leitura do mesmo ícone não toca o
  sistema de arquivos.
- `test_menu_vazio_renderiza_estado_vazio` — partial do menu com `MenuResolvido` vazio devolve o
  estado vazio, não painel quebrado.

## Patches

_Nenhum patch registrado até o momento._
