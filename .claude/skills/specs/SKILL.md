---
name: write-spec
description: "Escrever SPECs de desenvolvimento para o projeto DIMAP GeoCoder. Use esta skill sempre que o usuário pedir para criar, redigir, escrever ou revisar uma SPEC (especificação de funcionalidade). Isso inclui frases como 'escreve uma SPEC para X', 'cria a SPEC do épico Y', 'nova SPEC de Z', 'preciso de uma SPEC para implementar W', ou qualquer pedido de especificação de uma nova funcionalidade ou iteração do projeto. Também use quando o usuário pedir para atualizar, versionar, corrigir ou revisar uma SPEC existente."
---

# Skill: Escrever SPECs — DIMAP GeoCoder

Guia para redigir arquivos de SPEC do projeto, do front-matter ao template. Toda iteração de
desenvolvimento é guiada por uma SPEC — nenhum código é escrito sem ela.

---

## O princípio: o artefato aprova, a prosa não

> **Snippet aprova domínio. Mock aprova interface. Teste aprova comportamento.**

A SPEC é avaliada **pelo código**. Cada seção existe para responder **uma** pergunta, e cada frase da
SPEC pertence a exatamente uma seção. Ao escrever qualquer frase, pergunte-se **que pergunta ela
responde**: se responde duas, quebre; se não responde nenhuma, corte.

Duas regras transversais que caem disso:

- **Só a seção `Caveats` justifica.** Nenhuma outra seção contém "porque". Condição de pronto,
  domínio, peça de referência e fora de escopo enunciam — não argumentam.
- **A SPEC descreve a modelagem do domínio — não versiona código.** Quem versiona código é o git.
  Mudou a modelagem, edita-se o corpo, sobe a versão e registra-se **uma frase** no `changelog`; não
  existe patch nem histórico dentro do corpo.

---

## Organização da pasta `SPECS/`

As specs são organizadas **por épicos** (recortes de produto/funcionalidade), **nunca espelhando a
divisão em apps** — a divisão em apps é detalhe de implementação e pode ser cruzada por um mesmo
épico:

```
SPECS/
├── <epico-a>/
│   ├── 001-<slug-da-spec>.md
│   ├── 001-mock-<slug-da-spec>.html   ← só quando há interface entre os entregáveis
│   └── 002-<slug-da-spec>.md
└── <epico-b>/
    └── 001-<slug-da-spec>.md
```

Uma única SPEC costuma tocar **vários apps** ao mesmo tempo. Isso é esperado: o épico é a unidade de
valor; o app é onde o código acaba morando.

> **Regra prática:** se uma SPEC está crescendo a ponto de tocar funcionalidades não relacionadas,
> quebre em duas. Cada SPEC = uma iteração coesa e entregável.

### A ordem numérica é a ordem de implementação

A SPEC `NNN` só pode depender de SPECs de número **menor** — depender é precisar do que a outra
entrega (model, campo, função, componente) para poder ser implementada. Se a redação pedir
pré-requisito de número maior, as duas trocam de número ou o que falta muda de SPEC.

**Citar** SPEC posterior como consumidora do que esta entrega, ou como destino do que fica para
depois, não é dependência — é ponteiro, e é permitido.

*Por quê:* a numeração é o que diz "o que vem agora". Se ela mente, a inversão só aparece na hora de
implementar, com o pré-requisito faltando.

---

## Interface exige mock — e o mock tem skill própria

**Toda SPEC que tem front-end/interface entre os entregáveis exige um mock HTML navegável, e é o mock
que aprova o design** — mesmo quando a interface é só uma parte do que ela entrega. Componente do
design system, tela, seção, mudança de layout/coreografia ou token novo: **leia a skill `mock` e
siga-a**.

### A modelagem é aprovada ANTES do mock — nunca os dois de uma vez

1. **Modelagem.** Escreva a SPEC `.md` inteira — com o link do mock e a condição de pronto dele — e
   **pare**. Nenhuma linha de front-end aqui.
2. **Visual.** Só depois do "ok", faça o mock (a skill `mock` detalha o regime).
3. **TDD.** Aprovado o visual: testes → `testes_tdd: true` → código → porte.

*Por quê:* o mock é caro e **derivado** da modelagem — domínio que muda depois refaz a tela inteira.

Se o mock **revelar** que a modelagem estava errada, é o mock fazendo o trabalho dele: volte à SPEC,
corrija e aprove de novo antes de continuar o mock.

Na SPEC, o mock ocupa **uma linha** — um **link markdown relativo**, para nunca ficar solto na pasta —
e **uma condição de pronto**. A SPEC não descreve o mock nem argumenta estética: está na tela. Decisão
de peça nova **com custo** (acoplamento, token do qual outras telas passam a depender) é **Caveat**.

---

## Versionamento

**Um arquivo por SPEC, editado no lugar.** Toda mudança — antes ou depois de implementada — segue o
mesmo mecanismo:

1. **edita-se o corpo** onde a mudança cai (§3 Domínio, §6 Snippets, o que for);
2. **incrementa-se `versao`** (`v1`, `v2`, …) e `atualizado_em`;
3. **acrescenta-se uma linha ao `changelog`**;
4. **derrubam-se os flags**, se a mudança ainda não está no código.

> **Derrubar os flags é obrigatório.** Modelagem nova numa SPEC já entregue faz a SPEC descrever o que
> o código ainda não faz: `implementado: false` e `testes_tdd: false`, e vale o gate
> normal de novo. Deixar `implementado: true` mente para a próxima iteração, que lê esse campo para
> saber o que existe (CLAUDE.md §4).

> **Exceção (rascunho v1):** na **v1 ainda não implementada**, correção pequena (typo, snippet
> incompleto, redação) é só edição do rascunho — sem versão e sem `changelog`. Só se sai da v1 quando
> há evolução real de escopo.

**Refactor não toca a SPEC**: ela descreve a modelagem do domínio, e quem versiona código é o git.
**Bugfix** é o meio-termo — corpo intocado e flags de pé, porque o conserto já está no código, mas
ganha versão e uma linha `[bugfix]`: que aquela especificação tenha precisado de conserto é informação
sobre a modelagem.

### O `changelog` é uma frase, só o "quê"

Sem porquê, sem detalhe, sem lista de arquivos — o que foi feito se lê no corpo, que está atualizado:

```yaml
changelog:
  - v1: versão inicial
  - v2: substituição ganha período próprio
  - v3: "[bugfix] vigência ignorava data_fim nula"
  - v4: exercício deixa de ter coluna e passa a ser derivado
```

### O mock é protótipo: sem versão, sem changelog

Ele existe para **testar a interface**, então mostra sempre a **mais recente** — edita-se no lugar
quantas vezes o feedback pedir, sem registrar nada. Mexer no mock **não gera linha no `changelog` nem
bump de versão da SPEC**. Quando a tela era outra é assunto do git.

### Flags de estado

Dois flags, **só no front-matter** — não se repetem como check no corpo, onde checkbox é condição de
pronto (§2):

| Flag | Vira `true` quando |
|---|---|
| `testes_tdd` | os testes da §8 foram escritos e estão falhando |
| `implementado` | o código foi entregue e os testes passam |

Marque cada um **na mesma entrega** do que ele atesta, não depois.

> **Gate:** com `testes_tdd: false`, a única coisa permitida é escrever os testes — e `implementado:
> true` nunca aparece sem ele.

> **SPEC anterior a este flag não tem o campo `testes_tdd`** — a ausência significa "regime antigo",
> não `false`. Não faça backfill.

> **Marcar flag não incrementa a versão** — é estado administrativo.

### Markers obrigatórios

O `addopts` do `pyproject.toml` exclui markers (`integration`, `banco`) para manter `uv run pytest`
rápido — teste atrás de marker não roda a menos que alguém peça. SPEC com teste assim declara **no
front-matter** quais markers precisam rodar **verdes** antes de `implementado: true`:

```yaml
markers_obrigatorios: [banco]
```

- **Opcional**: SPEC cujos testes rodam todos na suíte padrão não tem o campo.
- **Parte do gate**: cada marker listado precisa ter rodado (`uv run pytest -m <marker>`) e passado.
- A §8 diz **quais** testes o carregam.

---

## Especificações das seções

Cada seção tem uma pergunta, uma porta de admissão e um teto. O que é rejeitado tem destino — e
"destino: nenhum" quer dizer que não se escreve em lugar algum.

**Teto estourado é pergunta, não decisão sua:** pare e pergunte ao usuário se a SPEC deve ser quebrada
em duas. Não espreme para caber nem estoure em silêncio.

**Comentário de código não conta em teto nenhum** — desde que seja o do §7.2 do CLAUDE.md: o *porquê*
**necessário** de uma implementação não óbvia.

### 1 · User story — *para quem, e por quê?*

Formato fixo, uma frase:

> `<ator X>` executa `<ação Y>` no contexto de `<Z>` para obter `<benefício W>`.

- O ator é um **papel real** — servidor da DIMAP, avaliador da DIMAP-1, administrador do cadastro.
  **Nunca "desenvolvedor do sistema"**.
- **Se o único ator possível é o desenvolvedor, não é user story.** A SPEC declara, em vez dela, uma
  linha: **"Refatoração"** ou **"Requisito não-funcional"**, com o que ela melhora, e segue direto
  para o Domínio. Essa é a válvula: não invente persona para preencher a seção.

**Teto:** 1 frase.

### 2 · Condições de pronto — *como sei que acabou?*

Estado **observável de fora**, por quem não leu o código — nunca tarefa. **Teste de descarte:** dá
para escrever a situação em que falha? Se não dá, não é condição. Cada uma tem ao menos um teste no §8.

```markdown
- [ ] Uma unidade tem **no máximo um titular**: marcar um segundo é recusado.
- [ ] Servidor com impedimento vigente **não aparece** na lista de candidatos a substituto.
- [ ] Encerrar um impedimento antes do prazo **devolve o servidor ao exercício no mesmo ato**, e as
      substituições em curso terminam no mesmo dia.
- [ ] Digitar `avenida palista, 347` exibe a seção de **endereço cadastrado** com o grau de certeza
      do logradouro corrigido.
```

Fora do formato: *"o `Perfil` ganha o método `em_exercicio()`"* (tarefa, e nomeia classe) · *"o campo
aberto é poço, porque é o que se lê como 'escreve-se aqui'"* (detalhe visual e "porque") · *"a listagem
é performática"* (não dá para escrever a situação em que falha) · *"`mypy` e `ruff` limpos"* (obrigação
permanente do projeto).

**Rejeitado vai para:** justificativa → **Caveats** · detalhe visual → **mock** · nome de módulo →
**Snippets**.
**Teto:** 10.

### 3 · Domínio — *como o domínio está sendo modelado?*

O coração da SPEC. A **ontologia aparece como código Pydantic** — models e DTOs escritos, não
descritos.

**Como modelar está na skill `ontologia`** — herança × composição, relação como entidade, derivado ×
guardado, enum × subtipo. **Leia-a antes de escrever esta seção.** Aqui ficam só as regras de como a
seção é redigida:

- **DTO que carrega objeto de domínio envelopa o model dele** — nunca recopia os campos da entidade
  soltos. Ao lado do objeto entra só o que é do **processo**: CRS, camada, paginação, perfil resolvido.
  Campo de entidade solto dentro de DTO é a ontologia duplicada, livre para divergir dela.

  ```python
  class LoteGeocodInput(BaseModel):
      lote: Lote                   # a entidade inteira, não setor/quadra/lote soltos
      output_crs: int              # e só então o que é do processo
  ```
- **Domínio consumido de SPECs anteriores entra por link interno**, com uma frase dizendo **que
  pergunta esta SPEC faz a ele** — não se recopia DTO de outra SPEC.
- **Domínio alterado de SPEC anterior é a exceção: traz-se o modelo inteiro**, não o delta, com
  comentário marcando o que mudou. A partir daí, o modelo vigente é o desta SPEC.

  ```python
  class Perfil(BaseModel):
      nome: str
      unidade: Unidade
      e_titular: bool = False   # ALTERADO nesta SPEC: campo novo
  ```
- **Prosa só quando o tipo não consegue dizer.** Enuncia o domínio; não justifica a escolha (isso é
  Caveat) nem descreve comportamento (isso é condição de pronto).
- SPEC que não introduz domínio novo — interface, orquestração, infra — tem esta seção **curta**: os
  links do que ela consome e a frase da pergunta que faz. Seção curta é resposta legítima; não invente
  ontologia para preencher.

**Teto:** sem teto de código; **uma frase por modelo** — e preferencialmente ela é um comentário no
próprio código, não prosa fora dele.

### 4 · Fora de escopo — *onde eu paro?*

**O que pertence ao domínio do §3 e foi deliberadamente recortado desta iteração.** É a fila das
próximas SPECs do épico, não uma lista de tudo que a SPEC não faz.

- **Teste de descarte:** isso está no §3? Se não está, **não entra aqui** — dizer que a SPEC não faz
  coisa que nunca foi do domínio dela é ruído.
- Cada item nomeia o **dono**: outra SPEC, outro épico, ou "sem dono ainda".

**Teto:** uma linha por item.

### 5 · Peças de referência a compor — *o que eu não devo reescrever?*

O que **já existe hoje** e o implementador plausivelmente reimplementaria sem esta linha.

- Formato: `@caminho` → nome: o que resolve. **Uma linha. Sem justificar.**
- **Só o que se reutiliza.** Arquivo que a SPEC vai apenas *alterar* não entra aqui — o destino do
  código novo é declarado no §6, junto do snippet.
- Não repete regra do CLAUDE.md ("view fina, DTO na fronteira") — isso não é peça.
- Skills a consultar entram numa linha só, no fim.

**Teto:** ~8 itens.

### 6 · Snippets — *como a regra de negócio fica em código?*

**É por aqui que a SPEC é avaliada.** Escreva os snippets de verdade, mostrando principalmente **como
as regras de negócio foram implementadas** — a expressão da invariante, o predicado, a transação, o
pipeline da classe callable.

- **Cada snippet declara onde vai morar** — caminho do módulo/arquivo previsto, acima do bloco. Onde o
  código mora é decisão de arquitetura (CLAUDE.md §3), e é ela que o usuário avalia aqui: domínio em
  `services/`, view fina, model só persistindo. Previsão, não promessa — divergir na implementação é
  permitido pelas mesmas regras do resto do snippet.

  **`services/domain/exercicio/vigencia.py`**
  ```python
  def esta_vigente(periodo: Periodo, hoje: date) -> bool: ...
  ```
- **O DTO da operação (`...Input` / `...Output`) se escreve aqui** — é parte do contrato que se revisa.
  Ele **envelopa** a entidade como campo tipado; o que não se recopia é o **model do §3**, que entra
  por **link interno** do markdown (`[Lote](#3--domínio)`).
- **Comentário didático existe só na SPEC.** Aqui você comenta para o revisor ler rápido: o que o
  bloco faz, por que aquela ordem, o que a linha protege.
- **⚠️ NA HORA DE PORTAR, O COMENTÁRIO DESCRITIVO NÃO VAI JUNTO.** No código de produção vale o §7.2
  do CLAUDE.md sem exceção: comentário explica o **porquê**, nunca o **quê**, em uma linha. O código
  tem que ser autoexplicativo. Comentário que parafraseia a linha é ruído que envelhece e passa a
  mentir — ele serviu à leitura da SPEC e morre ali.
- Não escreva boilerplate, imports óbvios nem a implementação completa. Snippet é **direção sugerida**;
  divergir exige razão e respeito ao §3 e ao §7 do CLAUDE.md.

### 7 · Caveats — *o que estou aceitando pagar?*

**A única seção que justifica.** Entra aqui, e só aqui:

- decisão que **contraria ou tensiona o CLAUDE.md** (e por que não é violação, ou por que se aceitou
  que seja);
- **custo consciente** assumido: performance futura, acoplamento novo, invariante que escapa,
  duplicação tolerada, revalidação que não acontece.

**Pode vir vazia — e vazia é o estado saudável.** Mas vazia tem que ser conclusão, não preguiça. É
caveat, obrigatoriamente, se qualquer destes for verdade:

- [ ] uma **invariante ficou fora do banco** (vive em `clean()`, em `services/` ou só no teste) — diga
      o que escapa dela;
- [ ] algo roda em **O(n) sobre catálogo que vai crescer**, ou refaz consulta que dava para reaproveitar;
- [ ] um módulo **passou a conhecer outro** que antes não conhecia;
- [ ] o mesmo dado passou a existir em **dois lugares** que podem divergir;
- [ ] alguma coisa **não é revalidada** quando sua causa muda;
- [ ] você escreveu "por ora", "aceito", "não cobre" ou "fica para depois" em qualquer lugar da SPEC.

**Forma:** um caveat = um parágrafo = **três frases** — a decisão (uma oração), a razão (uma frase), o
custo (uma frase). Não escreva a alternativa descartada em detalhe: uma oração basta ("volume nomeado
esconderia os artefatos do `git status` — descartado"). Comparativo longo entre opções é discussão de
proposta, não de especificação.

**Teto:** sem teto — mas só o estritamente necessário. Passando de 10, o problema não é a seção: a
iteração está assumindo custo demais de uma vez.

### 8 · Testes (TDD) — *o que demonstra que o domínio foi implementado?*

Os testes que guiam a implementação, **escritos antes do código** e **aprovados junto com a SPEC** — é
isso que faz a validação humana acontecer antes da implementação, e não depois.

- Uma linha por teste: **nome + o comportamento observável que ele fixa**.
- Cada condição de pronto do §2 tem ao menos um teste; teste sem condição é **borda que realmente
  quebra**.
- **Teste que só pode falhar se alguém apagar código de propósito não entra.** Nada de getter, DTO
  trivial ou variação que só repete outro caso. **Cobertura não é meta.**
- Alvo natural é `services/` — domínio puro, sem Django. View só quando o que se fixa é o contrato
  HTTP/partial.
- Se algum teste carrega marker, diga quais — e liste o marker em `markers_obrigatorios`.

**Teto:** 10.

---

## Estilo da prosa

O que sobrou de prosa na SPEC — o parágrafo do Domínio e os Caveats — segue três regras:

- **Não seja verboso.** A SPEC é lida antes de cada implementação e relida a cada revisão; texto
  inflado não a torna mais rigorosa, só faz a decisão que importa se perder no meio.
- **Não use ênfase para compensar tamanho.** Negrito em tudo é o mesmo que negrito em nada.
- **A prosa descreve o estado atual, nunca como se chegou nele.** Cada frase é enunciada por si, como
  se a SPEC estivesse na primeira versão: nada de "a SPEC X deixou isso de fora", "o mock mostrou
  que…", "antes era Y e passou a ser Z". O histórico vive no `changelog`, em uma frase por versão.
  Ponteiro para outra SPEC continua valendo, desde que diga o que ela **entrega hoje**.

---

## Template do arquivo de SPEC

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

## 1 · User story
<ator> executa <ação> no contexto de <contexto> para obter <benefício>.

<!-- Se o único ator possível é o desenvolvedor, apague a frase acima e escreva UMA linha:
     **Refatoração** — <o que melhora>.   ou   **Requisito não-funcional** — <o que garante>. -->

## 2 · Condições de pronto
- [ ] <estado observável de pronto>
- [ ] <estado observável de pronto>

## 3 · Domínio
<A ontologia modelada, em Pydantic. Domínio consumido de SPECs anteriores entra por link, com a
pergunta que esta SPEC faz a ele. Prosa só se o tipo não disser — no máximo um parágrafo.>

```python
class <Entidade>(BaseModel):
    ...
```

## 4 · Fora de escopo
<O que É do §3 e foi deliberadamente recortado desta iteração — com o dono de cada item.>

## 5 · Peças de referência a compor
- `@services/integrations/wfs` → `WfsClient`: busca de dados do GeoSampa.
- `@services/utils` → normalização de texto: preparação do matching.
- Skills: `<skill>`, `<skill>`.

## 6 · Snippets
<As REGRAS DE NEGÓCIO em código, com comentário didático — que NÃO é portado.
DTOs do §3 por link interno, não recopiados. Cada bloco vem com o módulo previsto.>

**`services/domain/<dominio>/<modulo>.py`**
```python
# comentário didático: só existe aqui. No código de produção vale o §7.2 do CLAUDE.md.
```

## 7 · Caveats
<Só o que contraria/tensiona o CLAUDE.md ou é custo consciente assumido. Pode vir vazia.>

_Nada a declarar._

## 8 · Testes (TDD)
- `test_<comportamento>` — <o comportamento observável que este teste fixa>
- `test_<caso_de_borda>` — <a borda que ele protege> *(marker `<marker>`)*
````

**SPEC com interface entre os entregáveis** acrescenta, no fim do §3, **uma linha** com **link
relativo** —
o mock mora na mesma pasta, então o caminho é só o nome do arquivo:

```markdown
**Mock:** [NNN-mock-<slug>.html](NNN-mock-<slug>.html) — leia a skill `mock`.
```

e uma condição de pronto dizendo que o design foi aprovado no mock e as peças foram portadas para o
tema e o styleguide antes de qualquer template da aplicação usá-las.

---

## Como usar uma SPEC (instruções para o implementador)

- A SPEC é a **fonte de verdade da iteração**.
- **Ordem obrigatória: testes → flag → código.** Escreva os testes do §8, veja-os falhar, marque
  `testes_tdd: true`, e só então implemente. **É proibido escrever código de produção de uma SPEC com
  `testes_tdd: false`.**
- **Snippets são direção sugerida, não dogma** — divergir exige razão explícita, e a divergência deve
  respeitar os "Princípios de Arquitetura" e o "Estilo e Convenções de Código" do CLAUDE.md.
- **Ao portar um snippet, apague o comentário didático.** Sobra só o comentário do §7.2: uma linha,
  explicando o *porquê*, nunca o *quê*.
- **Cada snippet vem com o módulo/arquivo previsto.** Não é inventário de arquivos a tocar — é a
  decisão de camada, que é o que se revisa.
- Se há interface entre os entregáveis, **leia a skill `mock`** e faça o porte para o tema e o
  styleguide na
  mesma entrega.

---

## Checklist antes de entregar a SPEC

**Front-matter e estado**
- [ ] `spec`, `versao`, `atualizado_em`, `testes_tdd`, `implementado`, `changelog` completos.
- [ ] Os flags vivem **só no front-matter** — nenhum check repetindo-os após o título.
- [ ] `implementado: true` só existe se `testes_tdd: true`.
- [ ] Marker de teste declarado em `markers_obrigatorios` e rodado verde antes de `implementado: true`.
- [ ] Marcar flags **não** incrementou a versão nem gerou linha no `changelog`.
- [ ] Mudança registrada do jeito único: **corpo editado** + versão + **uma frase** no `changelog` —
      nenhuma seção de patches, nenhum histórico dentro do corpo.
- [ ] Mudança de modelagem numa SPEC já entregue **derrubou os flags** (`implementado` e `testes_tdd`
      de volta a `false`) — só bugfix mantém a SPEC implementada.
- [ ] Arquivo em `NNN-slug.md`, na subpasta do épico, dependendo só de SPECs de número **menor**.

**Seções**
- [ ] **§1** no formato ator/ação/contexto/benefício, sem "desenvolvedor do sistema" — ou declarada
      como Refatoração / Requisito não-funcional.
- [ ] **§2** são condições observáveis, sem "porque", sem nome de arquivo, sem detalhe visual — até 10.
- [ ] **§3** traz a ontologia **em Pydantic**, com a skill `ontologia` seguida; o que vem de SPEC
      anterior está por **link** (ou inteiro, se **alterado**, com o comentário); prosa ≤ 1 frase por
      modelo.
- [ ] **§4** lista só o que **pertence ao §3** e foi recortado, cada item com dono.
- [ ] **§5** lista só o que **já existe** e seria reimplementado — uma linha cada, sem justificar, sem
      arquivo que só vai ser alterado.
- [ ] **§6** mostra as **regras de negócio** em código, com comentário didático, sem recopiar DTOs — e
      a SPEC avisa que o comentário descritivo **não é portado**.
- [ ] **§7** contém **só** desvio do CLAUDE.md e custo consciente; nenhuma outra seção justifica nada;
      os gatilhos de caveat foram conferidos um a um.
- [ ] **§8** tem até 10 testes, ao menos um por condição de pronto mais bordas reais, nenhum trivial.

**Interface**
- [ ] Entregável tem interface → a skill `mock` foi lida e seguida; a SPEC traz o **link markdown
      relativo** para o mock (nenhum mock solto na pasta) e a condição de pronto da aprovação + porte.
- [ ] **A SPEC está sendo entregue sozinha, sem o mock** — a modelagem é aprovada primeiro; o mock só
      começa depois do "ok".
- [ ] Nenhuma argumentação estética na SPEC — está na tela.

**Geral**
- [ ] A prosa descreve o **estado atual**, sem histórico de decisão.
- [ ] Todo snippet do §6 declara o **módulo/arquivo previsto** acima do bloco.
- [ ] Se tocou funcionalidades demais, foi quebrada em duas.
