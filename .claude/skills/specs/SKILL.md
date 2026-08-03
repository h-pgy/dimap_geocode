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
- [ ] Marcar os flags (`testes_tdd`/`implementado` + `[x]`) **não incrementa a versão** nem
      adiciona entrada no `changelog` — é só estado administrativo.
- [ ] Se a SPEC **ainda não foi implementada**, a seção `Patches` está vazia ("Nenhum patch
      registrado até o momento.") e toda mudança foi registrada no `changelog`, não em `Patches`.
- [ ] Se a mudança é um **patch** (SPEC já implementada), ela foi **apenas acrescentada ao final** da
      seção `Patches` + front-matter (versão/changelog) — o **corpo da SPEC não foi editado**.
- [ ] Slug do arquivo no padrão `NNN-slug-da-spec.md` dentro da subpasta do épico correto.
- [ ] User story com persona, objetivo e valor claros.
- [ ] Critérios de aceite são **condições observáveis** (não tarefas técnicas).
- [ ] Contexto explica em quais camadas a SPEC mexe e por quê essa abordagem.
- [ ] O "por quê" está **curto**: uma decisão por parágrafo, sem repetição, sem alternativa
      descartada em detalhe, e comentário de snippet em uma linha.
- [ ] Peças de referência listam apenas o que **já existe** e deve ser reutilizado.
- [ ] Fora de escopo define explicitamente o que **não** entra nesta iteração.
- [ ] Seção "Testes (TDD)" presente, com os testes derivados dos critérios de aceite — **poucos e
      essenciais** (~3 a 6), sem inflar a lista nem perseguir cobertura.
- [ ] A SPEC não lista arquivos a criar/alterar (isso é decisão de implementação).
- [ ] Se a SPEC tocou funcionalidades demais, ela foi quebrada em duas.