---
name: write-spec
description: "Escrever SPECs de desenvolvimento para o projeto DIMAP GeoCoder. Use esta skill sempre que o usuário pedir para criar, redigir, escrever ou revisar uma SPEC (especificação de funcionalidade). Isso inclui frases como 'escreve uma SPEC para X', 'cria a SPEC do épico Y', 'nova SPEC de Z', 'preciso de uma SPEC para implementar W', ou qualquer pedido de especificação de uma nova funcionalidade ou iteração do projeto. Também use quando o usuário pedir para atualizar, versionar ou corrigir (patch) uma SPEC existente."
---

# Skill: Escrever SPECs — DIMAP GeoCoder

Guia completo para redigir arquivos de SPEC do projeto, desde o front-matter até o template
completo. Toda iteração de desenvolvimento é guiada por uma SPEC — nenhum código é escrito
sem ela.

---

## Organização da pasta `SPECS/`

As specs são organizadas **por épicos** (recortes de produto/funcionalidade), **nunca
espelhando a divisão em apps** — a divisão em apps é detalhe de implementação e pode ser
cruzada por um mesmo épico:

```
SPECS/
├── <epico-a>/
│   ├── 001-<slug-da-spec>.md
│   └── 002-<slug-da-spec>.md
└── <epico-b>/
    └── 001-<slug-da-spec>.md
```

Uma única SPEC costuma tocar **vários apps** ao mesmo tempo (ex.: uma SPEC do épico
"busca de logradouros" mexe em `apps/search`, `apps/logradouro_matcher`,
`services/domain` e `services/scripts`). Isso é esperado: o épico é a unidade de valor;
o app é onde o código acaba morando.

> **Regra prática:** se uma SPEC está crescendo a ponto de tocar funcionalidades não
> relacionadas, quebre em duas. Cada SPEC = uma iteração coesa e entregável.

### A ordem numérica é a ordem de implementação

Dentro de um épico, a numeração **é** a ordem em que as SPECs serão implementadas: a SPEC `NNN` só
pode depender de SPECs de número **menor**. **Nenhuma SPEC N depende da N+1.**

- **Depender** é precisar do que a outra SPEC entrega (model, campo, função, componente) para poder
  ser implementada. Citar uma SPEC posterior como **consumidora** do que esta entrega, ou como
  destino de algo que fica para depois, **não** é dependência — é ponteiro, e é permitido.
- Nenhum "pré-requisito" aponta para número maior. Se a redação pedir isso, o desenho da sequência
  está errado: ou as duas trocam de número, ou o que falta muda de SPEC.
- SPEC **já implementada** que declarou dependência inválida não tem o corpo corrigido — a revogação
  entra como **patch** (append-only), como qualquer mudança pós-entrega.

*Por quê:* a numeração é o que diz "o que vem agora". Se ela não é a ordem de implementação, cada
iteração precisa reconstruir a sequência lendo todas as SPECs do épico — e a inversão só aparece na
hora de implementar, com o pré-requisito faltando no banco.

---

## Versionamento

**Um arquivo por SPEC — não se cria um novo arquivo a cada mudança.** Quando uma SPEC
evolui, ela é editada no lugar e o **código de versão** no cabeçalho é incrementado
(`v1`, `v2`, …). A versão vive no front-matter junto de um *changelog* curto.

Mudanças de escopo/intenção e pequenas correções compartilham o mesmo versionamento:
tanto uma revisão de critério quanto um bugfix incrementam a versão. A diferença é
**onde** ficam registrados — e isso depende de a SPEC **já ter sido implementada ou não**:

- **SPEC ainda NÃO implementada** (sem o check de implementação — ver abaixo): qualquer
  mudança, seja de intenção/escopo seja um ajuste pontual, é editada **no corpo da SPEC** e
  registrada **apenas no `changelog`** do front-matter. **Não existe `Patches` nesta fase** —
  enquanto não houver código, não há o que "corrigir depois do fato".
  > **Exceção (rascunho v1):** enquanto a SPEC está na **v1 e ainda não foi implementada**,
  > correções pequenas (typo, snippet incompleto, ajuste de redação) são só **edição do rascunho**
  > — **não** incrementam a versão nem geram linha no `changelog`. Só se sai da v1 quando há
  > evolução real de escopo/intenção.
- **SPEC já implementada** (check marcado): **correções, bugfixes e refactors** vão para a seção
  `Patches` (mantém rastro do que mudou *após* a entrega, sem poluir a especificação). Todo patch
  também incrementa a versão.

> **Regra de ouro do `Patches`:** só se preenche `Patches` depois que a SPEC foi implementada
> (check marcado). Antes disso, tudo é `changelog`.

> **Patch = APPEND-ONLY.** Um patch **nunca edita o corpo da SPEC** (user story, critérios de aceite,
> contexto, peças de referência, snippets). Ele faz **duas coisas e só essas**: (1) **append** de uma
> nova entrada `### Patch NNN (vX) — <título>` **no final** da seção `Patches`; (2) atualização do
> **front-matter** (bump de `versao`, nova linha no `changelog`, `atualizado_em`). O corpo permanece
> **congelado** como a especificação original — quem quiser saber o que mudou lê os patches. Não
> reescreva snippets nem listas de referência "para refletir o novo estado": isso queima tokens e
> desalinha o histórico. O snippet dentro da entrada de patch é onde o novo código aparece, se
> necessário.

### Flags de estado

Toda SPEC declara seu estado em **dois flags**, cada um em **dois lugares que andam juntos** —
front-matter e check logo após o título:

| Flag | Front-matter | Check | Vira `true`/`[x]` quando |
|---|---|---|---|
| Testes TDD escritos | `testes_tdd: false` | `- [ ] **Testes (TDD) escritos**` | os testes da seção "Testes (TDD)" foram escritos e estão falhando |
| Implementada | `implementado: false` | `- [ ] **Implementada**` | o código da SPEC foi entregue e os testes passam |

**Assim que terminar de escrever os testes da seção "Testes (TDD)", marque o check
`- [x] **Testes (TDD) escritos**` e ponha `testes_tdd: true` no front-matter** — na mesma
entrega em que os testes são commitados, não depois.

**Sempre que a SPEC for implementada, marque o check e ponha `implementado: true`** — é o que
libera o uso da seção `Patches`.

> **Gate de implementação:** `testes_tdd: true` é **pré-condição para escrever o código da SPEC**.
> Com `testes_tdd: false`, a única coisa permitida é escrever os testes. Não se implementa código de
> produção de uma SPEC cujos testes ainda não foram escritos e não estão falhando — e, portanto,
> `implementado: true` nunca aparece sem `testes_tdd: true`.

> **SPECs anteriores a este flag não têm o campo `testes_tdd` — e é assim que devem ficar.** Elas
> foram escritas antes de o projeto adotar TDD; não faça backfill. A ausência do campo significa
> "SPEC do regime antigo", não `false`.

> **Marcar os flags NÃO incrementa a versão.** Virar `testes_tdd` ou `implementado` de `false → true`
> e o check `[ ] → [x]` é um estado administrativo, não uma mudança de conteúdo. A versão e o
> `changelog` ficam intocados; nada é acrescentado ao `changelog` só por causa destas marcações.

### Markers obrigatórios

Nem todo teste roda na suíte padrão. O `addopts` do `pyproject.toml` exclui markers (`integration`
e outros que venham a existir) para que `uv run pytest` continue rápido e sem dependência de
serviço externo — banco, rede, dados reais. Um teste atrás de marker é um teste que **não roda a
menos que alguém peça**.

Quando a SPEC tem testes assim, ela declara no front-matter quais markers precisam rodar **verdes**
antes de `implementado: true`:

```yaml
markers_obrigatorios: [banco]
```

- O campo é **opcional**: SPEC cujos testes todos rodam na suíte padrão simplesmente não o tem.
- Ele é **parte do gate de implementação**: com `markers_obrigatorios` declarado, `uv run pytest`
  sozinho não basta para marcar a SPEC como implementada — cada marker listado precisa ter rodado
  (`uv run pytest -m <marker>`) e passado.
- A seção "Testes (TDD)" diz **quais** testes carregam o marker, para que a divisão fique explícita
  na leitura.
- Declarar o campo **não incrementa a versão** se for junto da redação da SPEC; passar a exigir um
  marker novo depois é mudança de conteúdo e segue a regra normal de versionamento.

*Por quê:* o §9 do CLAUDE.md faz o teste ser o que guia a implementação. Teste escondido atrás de
marker que ninguém roda não guia nada — o campo é o que transforma "existe um comando para rodar"
em "a SPEC não fica pronta sem rodar".

---

## Como usar uma SPEC (instruções para o implementador)

- Toda nova funcionalidade começa por escrever (ou receber) uma SPEC no padrão abaixo.
- A SPEC é a **fonte de verdade da iteração**: a implementação segue o que está nela.
- Snippets de código na SPEC são **direção sugerida**, não dogma — divergir exige razão
  explícita, e a divergência deve respeitar os "Princípios de Arquitetura" e o "Estilo e
  Convenções de Código" do CLAUDE.md.
- **A SPEC não lista arquivos.** Ela não diz quais arquivos serão criados ou alterados —
  isso é decisão de implementação. O que a SPEC traz é uma lista de **peças já existentes**
  que devem ser **compostas**, deixando explícito o que já temos pronto.
- **A SPEC propõe os testes — o desenvolvimento é TDD.** A seção "Testes (TDD)" lista os testes
  que vão guiar a implementação: eles são **aprovados junto com a SPEC** e **escritos antes** do
  código. É isso que faz a validação humana acontecer antes da implementação, e não depois.
- **Ordem obrigatória: testes → flag → código.** Escreva os testes da SPEC, veja-os falhar, marque
  `testes_tdd: true` + `- [x] **Testes (TDD) escritos**`, e só então implemente. **É proibido
  escrever código de produção de uma SPEC com `testes_tdd: false`** — se o flag está em `false`, o
  trabalho da vez é escrever os testes.
- **Poucos testes, bem escolhidos — não exagere.** A lista fixa o **comportamento observável** dos
  critérios de aceite, mais os casos de borda que realmente quebram. Nada de getter, DTO trivial ou
  variação que só repete outro caso; **cobertura não é meta**. Regra prática: uma SPEC com 3
  critérios de aceite pede algo como **3 a 6 testes**, não 20. Lista inflada engessa refactor e
  queima ciclo de revisão — o oposto do que o TDD deveria comprar.

---

## SPEC de design vem com mock — sem ele não há aprovação

**Toda SPEC cujo entregável é interface** (componente novo do design system, tela nova, mudança de
coreografia ou de layout) **é apresentada junto com um mock HTML navegável**. Prosa não é aprovável
em design: descrever "poço rebaixado com aresta tracejada que acende no foco" não permite julgar
nada — ver na tela permite.

- **Onde mora:** ao lado da SPEC, mesmo prefixo — `SPECS/<epico>/NNN-mock-<slug>.html`.
- **O que ele mostra:** cada peça nova **nos seus estados** (vazio × preenchido, fechado × aberto,
  criar × editar), na condição real de uso — sobre o mapa vivo, não sobre fundo chapado.
- **Como carrega o tema:** o mock **não** duplica o design system. Ele faz `fetch` de
  `static/src/tema-dimap.dev.css` (fonte única, SPEC design/004) e injeta num `<style
  type="text/tailwindcss">`, como os exemplos da skill `componentes-frontend`. Exige servidor com
  root na raiz do projeto (Live Server) — via `file://` o fetch é bloqueado.
- **Tokens ainda não existentes** vão no mock em `script[type="text/css"]` inerte, **concatenados ao
  tema pelo loader dentro do MESMO bloco `text/tailwindcss`**. Bloco separado é processado sem o
  `@theme` do tema, as escalas `agua/rocha/madeira/sakura` viram "unknown utility class" no `@apply`
  e a folha inteira cai.
- **A SPEC referencia o mock** numa seção "Mock de validação" e num critério de aceite: o design foi
  aprovado no mock antes de qualquer código de aplicação.

### O mock implementa Atomic Design — não é rascunho de tela

**Mock não é wireframe nem "tela desenhada em HTML".** Ele é o design system em exercício, e por isso
**obedece ao Atomic Design da skill `componentes-frontend` (§2 dela) desde o primeiro rascunho** —
não "depois, na hora de implementar":

- **Organizado nas quatro camadas, nessa ordem, em seções visíveis na página:** tokens → átomos →
  moléculas → organismos. A página mostra cada camada separadamente **antes** de mostrar a tela
  montada, porque o que se aprova é a peça reutilizável, não o arranjo dela numa tela.
- **Cada nível é composição do nível imediatamente inferior.** Organismo que contém marcação solta
  em vez de moléculas já existentes está errado, mesmo que a tela pareça certa.
- **Nada de CSS ad hoc.** Toda pele nova é classe no `@layer components` com `@apply` **só de
  utilities**, aderente às escalas e materiais existentes. Cor, sombra, blur, espaçamento ou
  tipografia fora dos tokens reprova o mock, por mais bonita que esteja a tela.
- **Peça que já existe é reutilizada, não redesenhada.** Antes de criar, confira o styleguide.

### Aprovado o mock, o porte é obrigatório — em dois lugares

Aprovação do mock **não** é licença para copiar o HTML dele para dentro dos templates. O que foi
aprovado vira patrimônio do design system, e isso são **dois destinos obrigatórios**, ambos na mesma
entrega da implementação:

1. **CSS base do design system — `static/src/tema-dimap.dev.css`.** Os blocos de token do mock
   migram para lá **tal e qual**, na seção da camada a que pertencem. É a fonte única (SPEC
   design/004): enquanto o token viver só no mock, ele não existe para a aplicação.
2. **Styleguide — `.claude/skills/componentes-frontend/examples/design_system.html`.** Cada peça
   nova é renderizada lá, na seção da sua camada (2 · Átomos, 3 · Moléculas, 4 · Organismos). É o
   **contrato visual do projeto**: componente que não está no styleguide não é encontrável e será
   reinventado — que é exatamente o que o Atomic Design existe para impedir.

Só depois disso os templates da aplicação usam as classes. **A SPEC de design não está implementada
enquanto os dois portes não tiverem sido feitos** — o critério de aceite do styleguide cobre isso, e
o do CSS base é pressuposto de qualquer template que use as classes novas.

O mock **permanece** no `SPECS/` como o artefato aprovado da iteração: não é descartado nem editado
para "refletir o novo estado". Quem quiser saber o que foi aprovado ali abre o mock; quem quiser usar
a peça vai ao styleguide.

*Por quê:* o mesmo motivo do TDD (§9 do CLAUDE.md), aplicado ao que teste automatizado não alcança.
O teste torna a regra verificável antes do código; o mock torna o **design** verificável antes do
código. E o porte obrigatório é o que impede o efeito colateral clássico: cada SPEC de interface
inventando seu próprio HTML, com a coerência visual dependendo de disciplina individual em vez de
peça compartilhada (§3.4 do CLAUDE.md).

---

## Concisão: escreva o "por quê" curto

**Não seja verboso.** Vale para o "Contexto e decisões de arquitetura", para os comentários dos
snippets e para qualquer justificativa na SPEC. A SPEC é lida antes de cada implementação e relida a
cada revisão — texto inflado não a torna mais rigorosa, só faz a decisão que importa se perder no
meio da prosa.

- **Uma decisão, um parágrafo curto.** Diga a decisão, a razão dela e o custo aceito. Ponto.
- **Não repita a mesma justificativa** em seções diferentes, nem parafraseie o critério de aceite
  que a decisão atende — remeta a ele.
- **Não escreva a alternativa descartada em detalhe.** Uma oração basta ("volume nomeado esconderia
  os artefatos do `git status` — descartado"). Comparativo longo entre opções é discussão de
  proposta, não de especificação.
- **Comentário de snippet é uma linha.** Ele diz *por que* aquela linha existe, não o que ela faz —
  a mesma regra do §7 do CLAUDE.md. Snippet que precisa de três linhas de comentário está
  escondendo uma decisão que devia estar no "Contexto".
- **Não use ênfase para compensar tamanho.** Negrito em tudo é o mesmo que negrito em nada.

**A prosa descreve o estado atual, nunca como se chegou nele.** Cada decisão é enunciada por si, como
se a SPEC estivesse na primeira versão: nada de "a SPEC X deixou isso de fora", "o mock mostrou
que…", "antes era Y e passou a ser Z", nem contraposição ao que uma versão anterior dizia. O
histórico de como a especificação evoluiu vive no `changelog` do front-matter e, depois da entrega,
nos `Patches` — é lá que se procura, e repeti-lo no corpo faz cada releitura pagar por uma discussão
já encerrada. Ponteiro para outra SPEC continua valendo, desde que diga o que ela **entrega hoje**,
não o que ela deixou de entregar ontem.

---

## Template do arquivo de SPEC

Ao redigir uma SPEC, use exatamente este template (substitua os campos `<…>`):

````markdown
---
spec: <epico>/<nº>
versao: v1
atualizado_em: <AAAA-MM-DD>
testes_tdd: false
implementado: false
markers_obrigatorios: []  # opcional — markers que precisam rodar verdes antes de implementado: true
changelog:
  - v1: versão inicial
---

# SPEC <épico>/<nº> — <título curto>

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como <persona>, quero <objetivo>, para <valor/razão>.

## Critérios de aceite
- [ ] <condição observável de pronto>
- [ ] <condição observável de pronto>

## Contexto e decisões de arquitetura
<Em que camadas mexe (interface / domínio / persistência), quais dos "Princípios de
Arquitetura" do CLAUDE.md se aplicam, por que esta abordagem. Fluxo resumido da funcionalidade.>

## Peças de referência a compor
<Funcionalidades JÁ existentes que esta SPEC deve reutilizar por composição — não recriar.>
- `@services/integrations/wfs` → `WfsClient`: usar por composição para buscar dados do GeoSampa.
- `@services/utils` → função de normalização de texto: reutilizar no matching.

## Snippets sugeridos
```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md
```

## Fora de escopo
<O que esta SPEC explicitamente NÃO faz, para evitar avanço além da iteração.>

## Testes (TDD)
<Os testes que guiam a implementação — escritos ANTES do código. Um por critério de aceite
observável, mais os casos de borda que realmente quebram. POUCOS E ESSENCIAIS: ~3 a 6 numa
SPEC típica. Não listar getter, DTO trivial nem variação que só repete outro caso.
Uma linha por teste: nome + o comportamento que ele fixa. Alvo natural é `services/`;
view só quando o que se fixa é o contrato HTTP/partial.
Se algum teste carrega marker (banco, integration, …), diga quais — e liste o marker em
`markers_obrigatorios` no front-matter.
Ao escrevê-los, marque `testes_tdd: true` + o check no topo — é o que libera a implementação.>

- `test_<comportamento>` — <o comportamento observável que este teste fixa>
- `test_<caso_de_borda>` — <a borda que ele protege>

## Patches
<SÓ existe depois que a SPEC foi implementada (check `Implementada` marcado). Correções, bugfixes e
refactors registrados após a entrega. **APPEND-ONLY:** cada patch é uma nova entrada acrescentada ao
FINAL desta seção — o corpo da SPEC NUNCA é editado por um patch. Cada patch incrementa a versão
(changelog no front-matter) e fica registrado aqui com versão e título. Enquanto a SPEC NÃO foi
implementada, deixe esta seção como abaixo e registre tudo no `changelog`.>

_Nenhum patch registrado até o momento._
````

---

## Checklist antes de entregar a SPEC

Antes de apresentar a SPEC ao usuário, verifique:

- [ ] Front-matter completo: `spec`, `versao`, `atualizado_em`, `testes_tdd`, `implementado`,
      `changelog`.
- [ ] Checks `- [ ] **Testes (TDD) escritos**` e `- [ ] **Implementada**` presentes logo após o
      título, cada um coerente com seu flag no front-matter.
- [ ] `implementado: true` só existe se `testes_tdd: true` — código de produção não começa antes
      dos testes.
- [ ] Se algum teste da SPEC roda atrás de marker, o marker está em `markers_obrigatorios` e a
      seção "Testes (TDD)" diz quais testes o carregam — e ele rodou verde antes de
      `implementado: true`.
- [ ] Marcar os flags (`testes_tdd`/`implementado` + `[x]`) **não incrementa a versão** nem
      adiciona entrada no `changelog` — é só estado administrativo.
- [ ] Se a SPEC **ainda não foi implementada**, a seção `Patches` está vazia ("Nenhum patch
      registrado até o momento.") e toda mudança foi registrada no `changelog`, não em `Patches`.
- [ ] Se a mudança é um **patch** (SPEC já implementada), ela foi **apenas acrescentada ao final** da
      seção `Patches` + front-matter (versão/changelog) — o **corpo da SPEC não foi editado**.
- [ ] Slug do arquivo no padrão `NNN-slug-da-spec.md` dentro da subpasta do épico correto.
- [ ] A SPEC só depende de SPECs de número **menor** do mesmo épico — nenhum "pré-requisito" aponta
      para a seguinte.
- [ ] User story com persona, objetivo e valor claros.
- [ ] Critérios de aceite são **condições observáveis** (não tarefas técnicas).
- [ ] Contexto explica em quais camadas a SPEC mexe e por quê essa abordagem.
- [ ] O "por quê" está **curto**: uma decisão por parágrafo, sem repetição, sem alternativa
      descartada em detalhe, e comentário de snippet em uma linha.
- [ ] A prosa descreve o **estado atual**, sem histórico de decisão — o "como se chegou aqui" está
      no `changelog` (ou nos `Patches`), não no corpo.
- [ ] Peças de referência listam apenas o que **já existe** e deve ser reutilizado.
- [ ] Fora de escopo define explicitamente o que **não** entra nesta iteração.
- [ ] Seção "Testes (TDD)" presente, com os testes derivados dos critérios de aceite — **poucos e
      essenciais** (~3 a 6), sem inflar a lista nem perseguir cobertura.
- [ ] Se o entregável é **interface**, o **mock HTML** acompanha a SPEC (`NNN-mock-<slug>.html`),
      carrega o tema por fetch da fonte única, mostra cada peça nos seus estados, e está citado numa
      seção "Mock de validação" e num critério de aceite.
- [ ] O mock está **organizado em Atomic Design** (tokens → átomos → moléculas → organismos, em
      seções visíveis), cada nível composto pelo inferior, sem CSS ad hoc.
- [ ] A SPEC declara o **porte obrigatório** pós-aprovação nos dois destinos: tokens para
      `static/src/tema-dimap.dev.css` e peças renderizadas em
      `.claude/skills/componentes-frontend/examples/design_system.html`.
- [ ] A SPEC não lista arquivos a criar/alterar (isso é decisão de implementação).
- [ ] Se a SPEC tocou funcionalidades demais, ela foi quebrada em duas.