---
name: painel
description: Como acrescentar um item ao painel de ações — item livre e card de ação, o SVG que o
  slug determina, grupo e aba novos. Use SEMPRE que for expor uma tela nova no painel e SEMPRE ao
  declarar uma ação administrativa.
---

## Antes de acrescentar qualquer item: pergunte, nunca decida
Onde o item aparece, como se chama e que glifo carrega é decisão de quem conhece o processo — e ação
sem card derruba a subida (`painel.E004`). Pergunte, nesta ordem:

1. **Ação:** ela entra no painel? Se não, qual o destino dela — e o motivo, que vira a linha em
   `ACOES_SEM_CARD` (`apps/painel/checks.py`).
2. Em qual aba: uma das declaradas em `apps/painel/abas_declaradas.py`, ou uma nova?
3. Em qual grupo dela — ou fora de poço, acima ou abaixo dos grupos?
4. Em que posição dentro do grupo? A ordem exibida é a de declaração.
5. Aba nova: rótulo da tab, título e o parágrafo de descrição?
6. Grupo novo: rótulo?
7. Qual o glifo do ícone? Proponha o desenho em palavras e **espere o ok antes de gravar o
   arquivo** — nenhum item chega ao painel com ícone escolhido por conta própria.
8. **Item livre:** `nome` do card, `tooltip` (que é a descrição impressa nele) e `slug` — este
   determina a pasta do SVG. Na ação os três vêm do contrato e não se pergunta de novo.
9. O `url_name` abre um **modal** ou é uma **tela própria**? Não se deduz do nome da rota — confira
   se o template dela tem `{% extends "base.html" %}` (ver "Modal ou página própria" abaixo).

## Acrescentar item livre

Item livre é view protegida só por `login_required` — nunca entra no registro de ações
(`apps/competencias/registro.py`): não é concedível nem delegável, e ninguém confere competência
sobre ela. É por isso que ela é o único tipo que **nunca** some da cascata (`resolucao.py`,
`_visivel`) e não precisa de contrato de ação nenhum.

```python
# apps/painel/abas_declaradas.py
ItemLivre(
    slug="<app>.<nome>",           # mesmo formato <app>.<nome> das ações — é ele que acha o SVG
    nome="Rótulo do card",
    tooltip="Descrição impressa no card",
    url_name="<app>:<view>",
    # Só quando a rota pede o pk do perfil da sessão (ex.: a página do próprio perfil).
    argumento_perfil=None,
)
```

1. A view por trás de `url_name` é protegida por `@login_required` — sem competência nenhuma a
   conferir, é só isso.
2. O SVG mora em `static/src/acoes/<app>/<nome>/icones/<variante>.svg`, mesmo gabarito das ações
   (`GABARITO_CAMINHO_ICONE`, `apps/competencias/checks.py`) — só a variante declarada em
   `variante_icone` é cobrada (default `VarianteIcone.GRANDE`).
3. Acrescente o `ItemLivre` na posição decidida — dentro de um `Grupo.itens`, ou em
   `Aba.itens_acima`/`itens_abaixo` se for avulso.
4. O check `validar_painel` (`apps/painel/checks.py`) cobra do item livre exatamente o que
   `validar_registro` cobra da ação: ícone da variante declarada (`painel.E002`) e `url_name` que
   resolve sem argumento (`painel.E003`).

## Acrescentar card de ação

A ação segue os seis passos da skill `acao-administrativa` (contrato, registro, ícones, rota
protegida, view, projeção no banco) — **o passo "menu" de lá não existe mais**: quem pinça a ação
não é um `ContratoMenu`, é o `ItemAcao` que você declara aqui.

```python
# apps/painel/abas_declaradas.py
ItemAcao(acao=ACAO_X)
```

1. Escreva a ação primeiro (skill `acao-administrativa`), até o registro em
   `apps/competencias/registro.py`.
2. Um SVG por variante **declarada** em `variantes_icone` do contrato — o `ItemAcao` só herda
   `VarianteIcone.GRANDE` por padrão; se a ação declarar `PEQUENO` também, ele segue sem uso aqui
   até que outro menu o consuma.
3. Só então declare o `ItemAcao` na posição decidida. **Toda ação inscrita no registro precisa de
   um `ItemAcao` em algum lugar do painel** — a exceção vai numa linha em `ACOES_SEM_CARD`
   (`apps/painel/checks.py`), com o motivo comentado; sem isso, `painel.E004` derruba a subida.

## Modal ou página própria — o destino do card

O `url_name` do item aponta para dois tipos bem diferentes de tela — de ação ou livre, a pergunta é
a mesma — e cada um pede um ajuste diferente no card. Decida qual é **antes** de declarar o item.

### A rota abre um modal

Um modal é um fragmento sem `{% extends "base.html" %}` — pensado para chegar por HTMX dentro de
uma página que já está de pé, nunca para ser navegado direto. Um card comum (`<a href>`) levaria o
clique ao fragmento cru, sem CSS nem HTMX — foi o que aconteceu com "Tornar administrador" antes
desta seção existir, porque a rota dele sempre foi assim: pensada como "a rota direta da ação" de
um menu que nunca chegou a ser renderizado.

1. Declare o item com `partial=PARTIAL_CARTAO_MODAL` (a constante de
   `apps/painel/abas_declaradas.py`, que aponta para `painel/partials/_card_item_modal.html`) — o
   mesmo cartão visual, mas com `hx-get`/`hx-target="#poco-modal"` em vez de `<a href>`.
2. `templates/painel/painel.html` já declara `#poco-modal` e carrega `select_onsen.js` — nenhuma
   das duas coisas precisa ser repetida por item novo.
3. Se o modal tiver `<select data-select-onsen>`, ele já sai aprimorado: o módulo reage a
   `htmx:afterSwap`, e o painel o carrega para a página inteira, não por modal.

### A rota é uma tela própria

Estende `base.html` e existe como destino de navegação legítimo, com título e URL próprios. O card
comum (`<a href>`) já funciona sem ajuste algum — o que falta é a **volta**: acrescente
`{% include "partials/_botao_voltar_painel.html" %}` no topo do conteúdo da tela, como primeiro
filho do wrapper (mesmo padrão de `templates/unidades/unidades_list.html`). Sem ele, quem entra pela
tela fica sem caminho de volta ao painel.

- **A lógica de origem mora só no partial** — nenhuma view calcula nem passa nada no contexto. Ele
  só aparece quando o `Referer` da requisição é de fato o painel (`apps/core/navegacao.py` →
  `veio_do_painel`, exposto como filtro de template por `apps/core/templatetags/navegacao.py`) —
  chegar pela tela por qualquer outro caminho não tem para onde "voltar", e o `{% include %}` não
  desenha nada. Página que serve mais de um fluxo (ex.: `autenticacao/definir_senha.html`, que
  também atende o primeiro acesso obrigatório) não precisa de condição própria: o painel nunca
  linca para esse outro fluxo, então o `Referer` nunca bate lá.
- Botão dinâmico como o de `unidades/unidade_form.html` ("Voltar para a lista de unidades" quando a
  origem é a própria lista, "Voltar para a área do usuário" quando o clique veio direto do painel) é
  exceção, não regra — só vale a pena numa tela que também é destino de outra navegação já
  estabelecida antes do painel existir. **O verbo continua "Voltar" nos dois ramos** — muda o
  destino, não o gesto: em qualquer um dos dois, é para onde a visita esteve que o clique leva.
  Usa o mesmo filtro (`{% load navegacao %}{% if request|veio_do_painel %}`) direto no template, não
  o partial pronto — o destino do "senão" muda por página.

## Grupo e aba novos

```python
# apps/painel/abas_declaradas.py
Grupo(rotulo="Nome do assunto", itens=(...))

Aba(
    slug="painel.<nome>",
    rotulo="Texto da tab",
    titulo="Título do corpo",
    descricao="O parágrafo abaixo do título — o mesmo texto para todo servidor, sem enumerar o "
    "que ele não pode.",
    grupos=(...),
    # basica=True só na aba que TODO servidor autenticado precisa ver mesmo sem caneta alguma —
    # hoje só ABA_MINHA_CONTA. Ela é o que impede o painel de abrir vazio (painel.E001).
)
```

- **Grupo vazio não renderiza.** Declarar um grupo sem item nenhum é válido (ex.: "Cargos em
  Comissão", que nasce assim de propósito) — ele só não aparece até ganhar o primeiro `ItemAcao`
  ou `ItemLivre`.
- **`basica` é flag de UMA aba só.** Mais de uma aba básica não quebra nada tecnicamente, mas
  confunde qual delas abre por padrão (`painel/partials/_abas.html` marca `checked` em toda aba com
  `basica=True`) — não declare uma segunda sem necessidade real.
- Aba nova entra em `PAINEL.abas`, na posição em que deve aparecer — ordem de declaração é ordem de
  exibição, nos três níveis (aba, grupo, item).

## Desenho próprio

Todo item nasce com o `partial_padrao` do continente que o contém (o grupo, ou a aba quando o item
é avulso) — hoje sempre `PARTIAL_CARTAO` (`painel/partials/_card_item.html`, que compõe o cartão de
`competencias/partials/_card_acao.html`). Declare `partial` no próprio item quando ele precisar de
forma diferente da do grupo: "Sair" usa `_botao_sair.html` por não ser um `<a href>`, e sim um
`<form method="post">`; todo item cujo `url_name` abre um modal usa `PARTIAL_CARTAO_MODAL` pelo
motivo da seção anterior.

Componente novo — nunca CSS ad hoc num partial: nasce no design system (skill
`componentes-frontend`), aprovado no mock (skill `mock`) antes de qualquer template da aplicação
usá-lo.
