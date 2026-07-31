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

### Flag de implementação

Toda SPEC declara se já foi implementada, em **dois lugares que andam juntos**:

1. No front-matter: `implementado: false` (vira `true` quando o código da SPEC é entregue).
2. Logo após o título, um **check** `- [ ] **Implementada**` (vira `- [x] **Implementada**`).

**Sempre que a SPEC for implementada, marque o check e ponha `implementado: true`** — é o que
libera o uso da seção `Patches`.

> **Marcar como implementada NÃO incrementa a versão.** Virar o flag `implementado: false → true`
> e o check `[ ] → [x]` é um estado administrativo, não uma mudança de conteúdo. A versão e o
> `changelog` ficam intocados; nada é acrescentado ao `changelog` só por causa desta marcação.

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
- **Poucos testes, bem escolhidos — não exagere.** A lista fixa o **comportamento observável** dos
  critérios de aceite, mais os casos de borda que realmente quebram. Nada de getter, DTO trivial ou
  variação que só repete outro caso; **cobertura não é meta**. Regra prática: uma SPEC com 3
  critérios de aceite pede algo como **3 a 6 testes**, não 20. Lista inflada engessa refactor e
  queima ciclo de revisão — o oposto do que o TDD deveria comprar.

---

## Template do arquivo de SPEC

Ao redigir uma SPEC, use exatamente este template (substitua os campos `<…>`):

````markdown
---
spec: <epico>/<nº>
versao: v1
atualizado_em: <AAAA-MM-DD>
implementado: false
changelog:
  - v1: versão inicial
---

# SPEC <épico>/<nº> — <título curto>

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
view só quando o que se fixa é o contrato HTTP/partial.>

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

- [ ] Front-matter completo: `spec`, `versao`, `atualizado_em`, `implementado`, `changelog`.
- [ ] Check `- [ ] **Implementada**` presente logo após o título, coerente com `implementado:`
      no front-matter (ambos só viram `true`/`[x]` quando o código é entregue).
- [ ] Marcar a SPEC como implementada (`implementado: true` + `[x]`) **não incrementa a versão**
      nem adiciona entrada no `changelog` — é só um estado administrativo.
- [ ] Se a SPEC **ainda não foi implementada**, a seção `Patches` está vazia ("Nenhum patch
      registrado até o momento.") e toda mudança foi registrada no `changelog`, não em `Patches`.
- [ ] Se a mudança é um **patch** (SPEC já implementada), ela foi **apenas acrescentada ao final** da
      seção `Patches` + front-matter (versão/changelog) — o **corpo da SPEC não foi editado**.
- [ ] Slug do arquivo no padrão `NNN-slug-da-spec.md` dentro da subpasta do épico correto.
- [ ] User story com persona, objetivo e valor claros.
- [ ] Critérios de aceite são **condições observáveis** (não tarefas técnicas).
- [ ] Contexto explica em quais camadas a SPEC mexe e por quê essa abordagem.
- [ ] Peças de referência listam apenas o que **já existe** e deve ser reutilizado.
- [ ] Fora de escopo define explicitamente o que **não** entra nesta iteração.
- [ ] Seção "Testes (TDD)" presente, com os testes derivados dos critérios de aceite — **poucos e
      essenciais** (~3 a 6), sem inflar a lista nem perseguir cobertura.
- [ ] A SPEC não lista arquivos a criar/alterar (isso é decisão de implementação).
- [ ] Se a SPEC tocou funcionalidades demais, ela foi quebrada em duas.