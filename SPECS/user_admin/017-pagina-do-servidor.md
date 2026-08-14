---
spec: user_admin/017
versao: v1
atualizado_em: 2026-08-14
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC user_admin/017 — A página do servidor: ler o cadastro, editar por modal

## 1 · User story
O responsável pela DIMAP abre a página de um servidor para ver quem é, onde está lotado, com que
cargo e em que situação de exercício, e edita o cadastro por um modal aberto dali, para que consultar
um colega e alterar o cadastro dele deixem de ser a mesma tela.

## 2 · Condições de pronto
- [ ] O servidor tem **página própria**, em rota **aberta** de leitura, alcançável pela listagem de
      servidores e pela seção de direção da unidade, com o **cabeçalho de identidade** e duas seções
      **nesta ordem** (Resumo, Exercício) e, ao fim, um botão que abre a edição.
- [ ] O **Resumo** traz RF, nome, sobrenome, unidade, cargo base e cargo em comissão **em leitura** —
      nenhum campo de formulário do cadastro fora do modal —, com a bandeja de indicadores trazendo a
      unidade de lotação, com caminho para a **página dela**, e a titularidade; o que o servidor
      **não tem** se lê ali em vez de sumir da tela.
- [ ] **Editar é modal, e o modal chega pela mesma `servidores/<pk>/editar/` de hoje**, que passa a
      devolver **só o partial**: a página de leitura não o carrega, ele abre já montado quando o botão
      o busca, e **nenhuma rota de escrita nasce aqui** — o submit não tem destino.
- [ ] No modal, os campos do cadastro — identificação, lotação e foto — aparecem preenchidos e
      **lidos**; cada um só vira campo quando alguém abre o **lápis ao lado do valor**, e **o mesmo
      botão vira ✕** para fechar — na página do servidor e na da unidade.
- [ ] O que a validação pode recusar naquele campo é dito **dentro dele**, e só **enquanto ele está
      aberto**.
- [ ] Quem não acha a unidade na lista tem um caminho **nomeado** ao pé do campo de lotação —
      **"Unidade não encontrada"** —, e é ele que abre o **cadastro de unidade como painel dentro do
      próprio modal**: o painel **cresce no lugar do botão**, **nada do que já estava preenchido se
      desfaz** — nem os campos abertos no lápis — e dá para **desistir sem subir a rolagem**.
- [ ] Os campos do cadastro de unidade **não viajam** no envio do cadastro do servidor, e nenhum
      formulário nasce dentro de outro.
- [ ] A seção de **Exercício** (SPEC 015) segue na página com seus cartões e diálogos, e **não** entra
      no modal de edição.
- [ ] **Criar servidor** segue em página de formulário, com os campos abertos, sem modal de edição e
      sem seção de exercício.
- [ ] O design foi aprovado no **mock**, e as peças novas — `.painel-onsen`, `.btn-foto`,
      `.avatar-editavel`, `.btn-etched-sm` — mais a alteração do `.campo-onsen` entram em
      `static/src/tema-dimap.dev.css` e no styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
Iteração de **interface e orquestração**: nenhum model novo, nenhuma migração, nenhum DTO de entrada
— a rota recebe só a chave do perfil na URL. O domínio consumido, e a pergunta que esta SPEC faz a
cada peça:

- [`Perfil`, `CargoBase`, `CargoComissao` e `Unidade`](001-models-perfil-cargos-unidade.md) — RF, nome,
  sobrenome, lotação e os dois cargos: o que o Resumo lê e o que o modal preenche.
- [`resolver_imagem_perfil`](006-foto-do-perfil.md) — "qual é o rosto deste servidor?", já decidido
  entre foto gravada e avatar de iniciais.
- [`Perfil.e_titular` e `cargo_titulariza`](014-titular-da-unidade.md) — "este servidor dirige a
  unidade em que está lotado?", e por que mexer no cargo ou na unidade dele pode ser recusado.
- [`contexto_exercicio`](015-exercicio-e-substituicao.md) — a seção de exercício inteira, com os
  cartões, a calha e os diálogos, montada como já é hoje.

**Mock:** [017-mock-pagina-do-servidor.html](017-mock-pagina-do-servidor.html) — leia a skill `mock`.

## 4 · Fora de escopo
- **A rota de escrita** do cadastro do servidor — épico de ações.
- Autenticação, autorização por perfil e **registro** da execução — épico `autorizacao`; é o que separa
  a leitura aberta do lápis protegido.
- **Exonerar, excluir e reativar** servidor — sem dono ainda.
- Editar, encerrar ou excluir impedimento e substituição — SPEC 015, que já os entrega nesta página.
- **Alinhar a página da unidade** a esta coreografia, buscando o modal de edição por rota em vez de
  renderizá-lo junto — sem dono ainda.
- **Gravar a unidade criada pelo painel** e devolvê-la já selecionada no campo de lotação — épico de
  ações, quando criar unidade passar a gravar.

## 5 · Peças de referência a compor
- `@templates/user_admin/unidade.html` e `@templates/user_admin/partials/_secao_resumo_unidade.html`:
  o esqueleto da página de leitura e a bandeja de indicadores.
- `@templates/user_admin/partials/_modal_editar_unidade.html`: o modal por checkbox nativo com os
  campos em `.campo-onsen`, irmão do conteúdo e nunca dentro dele.
- `@templates/user_admin/partials/_identidade_perfil.html` e `_imagem_perfil.html`: o cabeçalho e o
  rosto já resolvido em foto ou iniciais.
- `@templates/user_admin/partials/_secao_exercicio.html` e `_modais_exercicio.html`: a seção de
  exercício e seus diálogos.
- `@templates/user_admin/partials/_campos_unidade.html` e `_campo_cor_unidade.html`: as três seções do
  cadastro de unidade, com a cor sugerida já ligada por HTMX ao select de unidade superior.
- `@apps/user_admin/context.py` → `_contexto_do_modal_de_unidade`: os catálogos que esse cadastro pede.
- `@apps/user_admin/context.py` → `contexto_exercicio`, `_imagem_do_perfil`, `_catalogos_de_lotacao`:
  o que a página de edição de hoje já monta.
- `@templates/user_admin/partials/_tabela_servidores.html`: alvo e swap explícitos de um `hx-get` que
  troca só o pedaço que muda.
- `@apps/user_admin/ficticios.py`: o titular, o afastado com e sem substituto e o servidor sem cargo
  em comissão — os estados que a página precisa exibir.
- `@static/src/tema-dimap.dev.css` → `.campo-onsen`, `.stats-onsen`, `.card-well`, `.glass-panel`,
  `.select-glass`, `.dot-unidade`, `.btn-onsen` / `.btn-glass`, `.btn-etched`, `.btn-criar-inline`,
  `.upload-well`, `.avatar-glass`, `.tarja-vinculo-pendente`.
- Skills: `componentes-frontend`, `daisyui`, `htmx`, `mock`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

**`apps/user_admin/urls.py`** — duas rotas para o mesmo servidor, e é a segunda que o épico
`autorizacao` vai proteger: ler é a página, editar é o modal.
```python
path("servidores/<int:pk>/", views.pagina_perfil, name="pagina_perfil"),
path("servidores/<int:pk>/editar/", views.editar_perfil, name="editar_perfil"),
```

**`apps/user_admin/views.py`** — a mesma consulta serve às duas; o que muda é o template e o que cada
uma monta.
```python
def pagina_perfil(request: HttpRequest, pk: int) -> HttpResponse:
    return render(request, TEMPLATE_PAGINA_PERFIL, contexto_pagina_perfil(_perfil(pk)))


def editar_perfil(request: HttpRequest, pk: int) -> HttpResponse:
    # Só o partial do modal: a página de leitura não o carrega, e os catálogos dos selects só são
    # consultados quando alguém abre o lápis.
    return render(request, TEMPLATE_MODAL_PERFIL, contexto_modal_perfil(_perfil(pk)))


def _perfil(pk: int) -> Perfil:
    return get_object_or_404(
        Perfil.objects.select_related("unidade", "cargo_base", "cargo_comissao"),
        pk=pk,
    )
```

**`apps/user_admin/context.py`** — o `contexto_editar_perfil` de hoje se parte em dois, pela mesma
linha que separa as rotas. `contexto_criar_perfil` segue como está: criar não tem o que ler.
```python
def contexto_pagina_perfil(perfil: Perfil) -> dict[str, Any]:
    """O que a página lê. Sem catálogo nenhum: os selects são do modal, que vem por rota."""
    return (
        contexto_fundo_admin()
        | contexto_exercicio(perfil)
        | {
            "perfil": perfil,
            "imagem": _imagem_do_perfil(perfil),
            "cor_unidade_hex": hex_da_cor(perfil.cor_unidade),
            # Titularidade é atributo do perfil, e a unidade dirigida é sempre a de lotação:
            # perguntar de novo ao banco por Unidade.titular seria refazer o que já está em mãos.
            "unidade_dirigida": perfil.unidade if perfil.e_titular else None,
        }
    )


def contexto_modal_perfil(perfil: Perfil) -> dict[str, Any]:
    """O que o modal preenche: o perfil, os catálogos dos três selects e os do painel de unidade,
    que vem fechado dentro dele."""
    return (
        _catalogos_de_lotacao()
        | _contexto_do_modal_de_unidade()
        | {
            "perfil": perfil,
            "imagem": _imagem_do_perfil(perfil),
        }
    )
```

**`templates/user_admin/perfil.html`** — a página nova, irmã de `unidade.html`.
```html
{# O sprite é por página, e os ids se repetem entre sprites: incluir os dois juntos duplicaria #}
{# glifo-alerta e glifo-substituto. O da página do servidor carrega o exercício mais o lápis.   #}
{% include "user_admin/partials/_glifos_servidor.html" %}

<div class="admin-shell">
  <div class="max-w-3xl mx-auto px-4 py-24">
    <div class="glass-panel p-6 sm:p-8 flex flex-col gap-6">
      {% include "user_admin/partials/_identidade_perfil.html" %}
      {% include "user_admin/partials/_secao_resumo_perfil.html" %}
      {% include "user_admin/partials/_secao_exercicio.html" %}

      <button hx-get="{% url 'user_admin:editar_perfil' perfil.pk %}"
              hx-target="#poco-modal"
              hx-swap="innerHTML settle:150ms">Editar servidor</button>
    </div>
  </div>
</div>

{# Poço do modal, irmão do conteúdo e nunca dentro dele: formulário aninhado é HTML inválido, e    #}
{# aqui fora ele escapa do contexto de empilhamento da .admin-shell. Nasce vazio — a rota o monta. #}
<div id="poco-modal" class="poco-modal"></div>
{% include "user_admin/partials/_modais_exercicio.html" %}
```

**`static/src/tema-dimap.dev.css`** — as peças novas e a alteração das que já estavam lá. A placa
chega esmaecida porque o fragmento vem com o toggle já marcado: sem a fase de settle ela apareceria
pronta. O painel usa a grade — `0fr → 1fr` é o único jeito de animar altura sem fixar um valor em
pixels que o conteúdo desmente.
```css
.poco-modal .modal-box { @apply transition-[opacity,scale,translate] duration-150 ease-out; }
/* O important é contra o daisyUI, que entinta o estado aberto com seletor mais específico. */
.poco-modal.htmx-settling .modal-box { @apply opacity-0! -translate-y-1!; }

.painel-onsen { @apply grid transition-all duration-300 ease-in-out; grid-template-rows: 0fr; }
.painel-onsen-toggle { @apply sr-only; }
/* A folga vive DENTRO do recorte: sem ela o overflow corta a sombra da placa e a quina sai reta. */
.painel-onsen-corpo { @apply overflow-hidden -mx-4 px-4 pt-6 pb-6 opacity-0 transition-opacity duration-300; }
.painel-onsen:has(> .painel-onsen-toggle:checked) { grid-template-rows: 1fr; }
.painel-onsen:has(> .painel-onsen-toggle:checked) > .painel-onsen-corpo { @apply opacity-100; }
/* O painel toma o lugar do gatilho, e o :has() sobe ao pai porque os dois moram em ramos diferentes. */
*:has(> .painel-onsen > .painel-onsen-toggle:checked) .painel-onsen-gatilho { @apply hidden; }
/* Campo do painel é campo rebaixado: sobre placa erguida o .input-glass não diz que se escreve nele. */
.painel-onsen-corpo :where(input, select, .select-onsen-trigger) {
  @apply bg-white/30! border-white/45! shadow-[inset_0_2px_6px_rgba(7,58,84,0.15)];
}

.btn-foto { /* irmão do .btn-criar-inline: círculo de gelo com a tinta ciana */ }
.avatar-editavel { @apply relative w-fit; }
.avatar-editavel > .btn-foto { @apply absolute bottom-0 right-0 translate-x-1 translate-y-1 mt-0!; }
/* Variante do átomo da SPEC 013: ao lado de um botão que grava, o corpo cheio disputa a atenção. */
.btn-etched-sm { @apply text-[12px] font-semibold tracking-[0.1em] px-1 py-0.5; }

/* ALTERAÇÃO na peça da SPEC 016 — vale também para o modal da página da unidade. */
.campo-onsen-lapis-fecha { @apply hidden; }
.campo-onsen:has(> .campo-onsen-toggle:checked) .campo-onsen-lapis:where(:hover, :focus-visible) .campo-onsen-lapis-abre { @apply hidden; }
.campo-onsen:has(> .campo-onsen-toggle:checked) .campo-onsen-lapis:where(:hover, :focus-visible) .campo-onsen-lapis-fecha { @apply inline; }
```

**`templates/user_admin/partials/_modal_editar_perfil.html`** — o partial que a rota devolve. O
`checked` vem no fragmento: chegar já é abrir, e fechar é o `<label>` desmarcando — sem JS de estado.
```html
<input type="checkbox" id="modal-editar-perfil" class="modal-toggle" checked />
<div class="modal modal-glass" role="dialog">
  <div class="modal-box glass-panel-thick modal-box-glass">
    <form class="flex flex-col gap-6">
      ... identificação em .campo-onsen ...
      <div class="card-well p-5 flex flex-col gap-4">
        <p class="text-overline">Lotação</p>
        ... o campo da unidade em .campo-onsen ...
        {# O caminho é nomeado: quem não achou a unidade lê o que fazer. Aberto o painel, este    #}
        {# <label> some, e o cadastro cresce no lugar exato onde a pergunta foi feita.            #}
        <label for="painel-nova-unidade" class="painel-onsen-gatilho ...">Unidade não encontrada</label>

        <div class="painel-onsen">
          <input type="checkbox" id="painel-nova-unidade" class="painel-onsen-toggle" />
          <div class="painel-onsen-corpo">
            <div class="glass-panel rounded-2xl p-5 flex flex-col gap-4">
              ... título, ✕ e {% include "user_admin/partials/_campos_unidade.html" %} ...
              {# O ✕ do topo sai de vista num painel longo: o mesmo gesto se repete aqui embaixo, #}
              {# em registro gravado, ao lado do que grava.                                       #}
              <label for="painel-nova-unidade" class="btn-etched btn-etched-sm etched">✕ cancelar</label>
              <button type="submit" form="form-nova-unidade" class="btn btn-onsen btn-sm">Criar unidade</button>
            </div>
          </div>
        </div>
        ... cargo base e cargo em comissão em .campo-onsen ...
      </div>
      ... foto em .avatar-editavel ...
      <div class="modal-action">... Cancelar · Salvar alterações ...</div>
    </form>

    {# O formulário do cadastro de unidade nasce VAZIO e irmão do de cima. Os campos dele moram lá  #}
    {# dentro, ao pé da lotação, e se ligam aqui pelo atributo `form` — é o que deixa o painel      #}
    {# crescer onde a pergunta nasceu sem produzir formulário aninhado, que é HTML inválido.        #}
    <form id="form-nova-unidade" class="hidden"></form>
  </div>
</div>
```

**`templates/user_admin/partials/_campos_unidade.html`** — cada campo do cadastro de unidade declara
a que formulário pertence.
```html
<input type="text" name="nome" form="form-nova-unidade" class="input input-glass" />
```

**`templates/user_admin/partials/_campo_cor_unidade.html`** — o `dropdown` desce um nível, do campo
inteiro para o gatilho.
```html
{# "Para a direita" é 100% da largura da ÂNCORA: no campo inteiro, o disco saltava para fora do  #}
{# painel. Ancorado embaixo, ele cresce para cima, onde o recorte do painel não o corta.         #}
<div class="palette-field form-field">
  <span class="text-overline">Cor da unidade</span>
  <div class="dropdown dropdown-right dropdown-end w-fit">
    <div tabindex="0" role="button" class="btn btn-ghost btn-glass w-fit gap-3 px-3 h-12">...</div>
    <div tabindex="0" class="dropdown-content z-30 ml-2">... o .palette-disc ...</div>
  </div>
  <span class="form-field-hint">...</span>
</div>
```

O campo abaixo é o exemplar dos demais: valor lido, campo escondido, lápis que troca os dois, e o
aviso da validação dentro do campo aberto.
```html
<div class="campo-onsen">
  <input type="checkbox" id="editar-campo-comissao" class="campo-onsen-toggle" />
  <span class="text-overline etched-rotulo">Cargo em comissão</span>
  <div class="campo-onsen-linha">
    <p class="campo-onsen-valor">
      {% if perfil.cargo_comissao %}{{ perfil.cargo_comissao.padrao }} · {{ perfil.cargo_comissao.nome }}{% else %}— sem cargo em comissão —{% endif %}
    </p>
    <div class="campo-onsen-campo">
      <select name="cargo_comissao" class="select select-glass" data-select-onsen>...</select>
      {# Só quem é titular carrega a recusa: é o clean() que cruza cargo → unidade → tipo. #}
      {% if perfil.e_titular %}
        <div class="tarja-vinculo tarja-vinculo-pendente ...">
          Trocar por um cargo que não titulariza a {{ perfil.unidade.sigla }} é
          <strong>recusado na validação</strong>: a unidade não fica com titular inválido gravado.
        </div>
      {% endif %}
    </div>
    {# Os dois glifos viajam juntos: aberto o campo, o hover troca o lápis pelo ✕, e o mesmo botão #}
    {# que abriu passa a dizer como se fecha.                                                      #}
    <label for="editar-campo-comissao" class="campo-onsen-lapis ...">
      <span class="etched icon-etched campo-onsen-lapis-abre">✎</span>
      <span class="etched icon-etched campo-onsen-lapis-fecha">✕</span>
    </label>
  </div>
</div>
```

**`templates/user_admin/perfil_form.html`** — sobra só o que cria: os `{% if perfil %}` saem, e com
eles a identidade, o exercício e os diálogos que só a página tem.

## 7 · Caveats
**As duas rotas nascem abertas**, pela mesma exceção ao §3.5 declarada nas SPECs 013 e 016. Enquanto
não há autenticação, exigir login tornaria a tela inexercitável, e nada aqui grava. Custo: a do modal
já é o lugar certo da checagem e ainda não a faz — quando o épico `autorizacao` chegar, é ela que
passa a exigir perfil, e até lá "ver" e "editar" só estão separados por endereço.

**Os campos do cadastro do servidor passam a existir em duas formas**: abertos em
`_secao_identificacao.html` / `_secao_lotacao.html`, que criar usa, e em `.campo-onsen` no modal.
Compartilhar um partial só exigiria um condicional de modo dentro de cada campo, que é o que o modal
da unidade já evitou. Custo: acrescentar campo ao cadastro obriga a tocar os dois lugares, que
divergem se alguém tocar um só.

**O cadastro aparece duas vezes na tela** — no Resumo como texto, no modal como campo. Quem só quer
saber onde o servidor está lotado não deveria precisar abrir o modal de edição. Custo: dois lugares
renderizando o mesmo dado, que divergem se um deles mudar de fonte.

**O modal chega por rota e abre sozinho**, porque o fragmento traz o `modal-toggle` já marcado, e a
entrada dele é a fase de `settle` do HTMX. É o que evita JavaScript para abrir a placa depois do
swap e mantém o fechar no `<label>` nativo. Custo duplo: o partial carrega estado de interface no
HTML — quem o buscar direto no endereço vê um modal sem página atrás — e a duração vive em dois
lugares, o `settle:` do atributo e a `transition` do `.poco-modal`, que ninguém consegue ler um do
outro.

**Só o modal do cadastro vem por rota**: os diálogos do exercício e o modal de edição da unidade
seguem renderizados junto com suas páginas. A rota é o que dá lugar à autorização de editar o
cadastro, e converter os demais agora dobraria esta iteração. Custo: duas coreografias de modal
convivem no mesmo épico até a SPEC que alinhar as outras.

**Os campos do cadastro de unidade moram dentro do formulário do servidor e pertencem a outro**, um
`<form>` vazio no fim da placa, pelo atributo `form`. É o que deixa o painel crescer ao pé do campo
que motivou a pergunta sem produzir formulário aninhado, que o navegador descartaria. Custo: a
separação entre os dois cadastros deixa de ser visível na árvore do HTML e passa a depender de um
atributo em cada campo — esquecê-lo num campo novo o faz viajar no envio errado, em silêncio.

**A mesma placa passa a ter dois botões de gravar** — "Criar unidade" no painel e "Salvar alterações"
no rodapé. É o preço de não abrir modal dentro de modal, e o que mantém intacto o que já estava
preenchido quando o painel abre. Custo: nada impede fechar o painel com a unidade não criada e salvar
o servidor achando que criou.

**Esta SPEC altera peças de outras**: o `.campo-onsen` da SPEC 016 ganha o ✕ no lápis, e o
`_campo_cor_unidade.html` da SPEC 012 passa a ancorar o disco no gatilho, abrindo para a direita.
O lápis sem saída de fecho e o disco recortado pelo painel são defeitos das peças, não desta tela.
Custo: a entrega mexe na página da unidade e no formulário de unidade, que esta SPEC não descreve —
e uma regressão ali aparece longe daqui.

**O painel de unidade nasce dentro do modal, mesmo fechado**, e com ele os catálogos de tipos, de
unidades superiores e a paleta. Buscá-lo por rota na hora de abrir devolveria o problema que o
painel resolve — conteúdo remontado do servidor, com o que estava preenchido em risco. Custo: quem
abre o lápis só para trocar o RF paga as consultas do cadastro de unidade.

## 8 · Testes (TDD)
Todos fixam contrato HTTP/partial e tocam o banco: carregam o marker `banco`. A montagem da seção de
exercício já é testada na SPEC 015 e não se repete aqui.

- `test_pagina_do_servidor_traz_o_resumo_em_leitura` — GET devolve 200 com RF, nome, unidade, cargo
  base e cargo em comissão no resumo, o caminho para a página da unidade, e nenhum campo de cadastro
  fora do modal. *(marker `banco`)*
- `test_resumo_diz_o_que_o_servidor_nao_tem` — servidor sem cargo em comissão e sem titularidade lê as
  duas ausências no resumo; o titular lê a unidade que dirige. *(marker `banco`)*
- `test_rota_do_modal_devolve_so_o_partial_preenchido` — GET na rota de edição devolve o modal, e só
  ele, com os valores do perfil e a opção corrente selecionada nos três selects, o toggle já marcado
  e o formulário sem destino de submit. *(marker `banco`)*
- `test_pagina_do_servidor_nao_carrega_o_modal` — a página traz o poço vazio e o botão que busca a
  rota de edição, sem nenhum campo do cadastro no HTML. *(marker `banco`)*
- `test_modal_traz_o_painel_de_unidade_fechado_e_com_formulario_proprio` — o partial traz o cadastro
  de unidade com os tipos e as unidades superiores do catálogo e o toggle desmarcado; todo campo dele
  declara o formulário da unidade, e nenhum `<form>` nasce dentro de outro. *(marker `banco`)*
- `test_pagina_do_servidor_mantem_a_secao_de_exercicio` — a página do afastado traz os cartões do
  exercício e os diálogos deles, fora do modal de edição. *(marker `banco`)*
- `test_criar_servidor_segue_em_formulario_aberto` — a página de novo servidor traz os campos abertos
  e não traz o modal de edição, o cabeçalho de identidade nem a seção de exercício. *(marker `banco`)*
- `test_caminhos_levam_a_pagina_do_servidor` — a listagem de servidores e a seção de direção da
  unidade apontam para a rota da página, não para a de edição. *(marker `banco`)*
