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
**onde** ficam registrados:
- **Mudanças de intenção** → corpo da SPEC.
- **Correções e bugfixes** → seção `Patches` (mantém rastro sem poluir a especificação).

---

## Como usar uma SPEC (instruções para o implementador)

- Toda nova funcionalidade começa por escrever (ou receber) uma SPEC no padrão abaixo.
- A SPEC é a **fonte de verdade da iteração**: a implementação segue o que está nela.
- Snippets de código na SPEC são **direção sugerida**, não dogma — divergir exige razão
  explícita, e a divergência deve respeitar os princípios de arquitetura (§3 do CLAUDE.md)
  e o estilo (§10 do CLAUDE.md).
- **A SPEC não lista arquivos.** Ela não diz quais arquivos serão criados ou alterados —
  isso é decisão de implementação. O que a SPEC traz é uma lista de **peças já existentes**
  que devem ser **compostas**, deixando explícito o que já temos pronto.
- **Testes unitários não fazem parte da SPEC.** A seção "Notas de teste" é um guia para
  *quando os testes forem pedidos explicitamente pelo desenvolvedor*, não uma ordem para
  criá-los junto da implementação.

---

## Template do arquivo de SPEC

Ao redigir uma SPEC, use exatamente este template (substitua os campos `<…>`):

````markdown
---
spec: <epico>/<nº>
versao: v1
atualizado_em: <AAAA-MM-DD>
changelog:
  - v1: versão inicial
---

# SPEC <épico>/<nº> — <título curto>

## User story
Como <persona>, quero <objetivo>, para <valor/razão>.

## Critérios de aceite
- [ ] <condição observável de pronto>
- [ ] <condição observável de pronto>

## Contexto e decisões de arquitetura
<Em que camadas mexe (interface / domínio / persistência), quais princípios de §3 do
CLAUDE.md se aplicam, por que esta abordagem. Fluxo resumido da funcionalidade.>

## Peças de referência a compor
<Funcionalidades JÁ existentes que esta SPEC deve reutilizar por composição — não recriar.>
- `@services/integrations/wfs` → `WfsClient`: usar por composição para buscar dados do GeoSampa.
- `@services/utils` → função de normalização de texto: reutilizar no matching.

## Snippets sugeridos
```python
# direção de implementação — adaptar conforme necessário, sem violar §3 nem §10
```

## Fora de escopo
<O que esta SPEC explicitamente NÃO faz, para evitar avanço além da iteração.>

## Notas de teste
<O que precisaria de teste e casos de borda relevantes — só para referência futura,
não para implementar agora.>

## Patches
<Pequenas correções e bugfixes registrados após a SPEC estar em uso. Cada patch incrementa
a versão (changelog no front-matter) e fica registrado aqui com data e versão.>
- <AAAA-MM-DD> (v2): corrige <bug/ajuste pontual>.
````

---

## Checklist antes de entregar a SPEC

Antes de apresentar a SPEC ao usuário, verifique:

- [ ] Front-matter completo: `spec`, `versao`, `atualizado_em`, `changelog`.
- [ ] Slug do arquivo no padrão `NNN-slug-da-spec.md` dentro da subpasta do épico correto.
- [ ] User story com persona, objetivo e valor claros.
- [ ] Critérios de aceite são **condições observáveis** (não tarefas técnicas).
- [ ] Contexto explica em quais camadas a SPEC mexe e por quê essa abordagem.
- [ ] Peças de referência listam apenas o que **já existe** e deve ser reutilizado.
- [ ] Fora de escopo define explicitamente o que **não** entra nesta iteração.
- [ ] Nenhum teste unitário foi escrito ou comprometido — apenas "Notas de teste".
- [ ] A SPEC não lista arquivos a criar/alterar (isso é decisão de implementação).
- [ ] Se a SPEC tocou funcionalidades demais, ela foi quebrada em duas.