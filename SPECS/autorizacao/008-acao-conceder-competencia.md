---
spec: autorizacao/008
versao: v9
atualizado_em: 2026-08-17
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: renumerada de 007 para 008 — criar a atribuição da unidade virou ação própria (SPEC 007),
    que passa a ser a primeira ação inscrita e a origem do bootstrap; aqui sobra o nível 2
  - v3: a ação vira estrutural, exercida pelo titular (SPEC titularidade/001) — o bootstrap deixa
    de depender de seed; o alcance passa da própria unidade à subárvore, como na SPEC 007
  - v4: registrada a pendência de revisão de quem abre a tela — com um titular só por unidade
    (SPEC user_admin/014 v5), quem exerce a estrutural é quem responde pela direção, incluindo o
    substituto do titular afastado; a revisão fica para iteração própria
  - v5: pendência resolvida — quem abre a tela é quem responde pela direção da unidade (titular em
    exercício ou substituto dele, SPECs user_admin/014 e 015), e a unidade sem titular ou sem
    direção é alcançada por quem dirige o nível acima
  - v6: o seletor de duas posições passa a se chamar `.seletor-onsen` — `.toggle-onsen` já é o
    interruptor da SPEC user_admin/015, no tema desde então —, a origem do alcance passa a ser as
    unidades dirigidas, e a SPEC foi reescrita no formato de seções numeradas da skill `specs`
  - v7: o alcance passa a ser declarado no contrato da ação e conferido pela proteção (SPEC 004); a
    view perde a conferência escrita à mão e a atribuição-alvo continua conferida contra a unidade
  - v8: o seletor de unidades passa a vir de `alvos_oferecidos` (SPEC 007), e o poço de atribuições
    fica explicitamente restrito à unidade-alvo escolhida
  - v9: o alcance declarado passa a ser `UnidadesSubordinadas`, e conceder a estrutural deixa de
    ampliar o alcance de quem a recebe
---

# SPEC autorizacao/008 — Conceder competência: distribuir entre os cargos o que a unidade tem

## 1 · User story
Quem responde pela direção de uma unidade da DIMAP distribui entre os cargos as ações que a unidade
possui, na tela de competências, para que um servidor recém-chegado — ou um cargo que a unidade passou a
ter — comece a trabalhar sem depender de alteração em código ou no banco.

## 2 · Condições de pronto
- [ ] Quem abre a tela é **quem responde pela direção** da unidade — o titular em exercício ou o
      substituto vigente dele —, sem depender de concessão gravada desta ação.
- [ ] A tela lista as atribuições **da unidade-alvo escolhida**, e só dela — as das outras unidades
      alcançadas não entram no mesmo poço.
- [ ] O seletor oferece as unidades que o perfil **dirige** e as que estão **abaixo delas** no
      organograma, cada uma **antes das que pendem dela e com a subordinação visível**; unidade fora
      desse alcance é recusada mesmo vindo no request.
- [ ] Conceder e revogar acontecem **sem recarregar a página**, trocando só o trecho afetado.
- [ ] A escolha do cargo distingue explicitamente **cargo base** de **cargo em comissão**, e só um dos
      dois é concedido por vez.
- [ ] Não há caminho para conceder uma ação que a unidade **não possui**, nem pela interface nem forjando
      o request.
- [ ] Conceder e revogar são **atos registrados** (SPEC 004), distinguíveis pela operação e com o alvo
      identificando ação e cargo.
- [ ] A ação aparece no **menu de administrador** (SPEC 007) apenas para quem pode executá-la.
- [ ] O design foi aprovado no **mock**, e as peças novas — `.seletor-onsen` e `.chip-concessao` — mais
      `.card-atribuicao`, compartilhada com a SPEC 007, foram portadas para
      `static/src/tema-dimap.dev.css` e renderizadas no styleguide antes de qualquer template da
      aplicação usá-las.

## 3 · Domínio
Nenhum model novo: é o **nível 2** da SPEC 002 virando ato administrativo, e a 007 é quem põe atribuição
no banco para esta tela distribuir. A concessão mira **um** cargo — base ou em comissão —, e é a linha
da atribuição que ela pendura, não a dupla unidade × ação.

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`AtribuicaoUnidade` e `Concessao`](002-competencia-no-banco.md) — "o que esta unidade exerce, e quais
  cargos já a exercem?"; a tela cria e revoga concessão, e não toca a atribuição.
- [`has_perm`](003-avaliador-e-backend-de-autorizacao.md) — "este perfil exerce esta ação estrutural?".
- [`UnidadesSubordinadas`](004-protecao-de-rota-e-registro-de-execucao.md) — "até onde o alvo desta
  ação pode chegar?", declarado no contrato dela, como na SPEC 007.
- [`alvos_oferecidos`](007-acao-definir-atribuicao.md) — "que unidades o seletor oferece, em que ordem
  e a que profundidade?"; a subárvore alcançada já sai achatada dali, como na tela da SPEC 007.
- [`acao_protegida` e `registrar_ato`](004-protecao-de-rota-e-registro-de-execucao.md) — a rota
  protegida, o alvo conferido contra o alcance e o rastro dos dois atos.
- [`MENU_ADMINISTRADOR`](007-acao-definir-atribuicao.md) — o menu que **pinça** também esta ação.
- `CargoBase` e `CargoComissao` — os dois catálogos oferecidos no campo.

**Mock:** [008-mock-conceder-competencia.html](008-mock-conceder-competencia.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Criar atribuição de unidade — SPEC 007.
- Concessão nominal a um servidor e concessão por natureza de cargo ("qualquer chefia") — sem dono ainda.
- Registrar impedimento e designar substituto — SPEC `user_admin/015`; aqui a substituição só é lida,
  pela SPEC 003.
- Tela de consulta do histórico de execuções — SPEC 004.
- Demais ações da plataforma: esta SPEC inscreve uma só.

## 5 · Peças de referência a compor
- `@apps/competencias/models` (SPEC 002) → `AtribuicaoUnidade`, `Concessao`.
- `@apps/competencias/utils.py` (SPEC 001) → `instanciar_acao`.
- `@apps/competencias/protecao.py` (SPEC 004) → `acao_protegida` e `registrar_ato`.
- `@apps/competencias/menus.py` (SPEC 005) → `ItemDeMenu` e `ContratoMenu`; e
  `@apps/competencias/menus_declarados.py` (SPEC 007) → `MENU_ADMINISTRADOR`.
- `@services/domain/autorizacao/contratos.py` (SPEC 004) → `UnidadesSubordinadas`: o alcance declarado
  no contrato da ação.
- `@apps/competencias/consulta.py` (SPEC 007) → `alvos_oferecidos`: a subárvore alcançada, já casada com
  as `Unidade` e achatada em pré-ordem.
- `@apps/user_admin/models` → `CargoBase`, `CargoComissao`: catálogo oferecido no campo.
- SPEC 006 → `.icone-acao`, e SPEC 007 → `.card-atribuicao`: a peça é a mesma, aqui com a faixa de chips.
- `@static/src/tema-dimap.dev.css` → `.card-well`, `.glass-panel`, `.glass-panel-thick`, `.modal-glass` +
  `.modal-box-glass`, `.select-onsen`, `.btn-onsen`, `.btn-glass`, `.text-overline`, `.dot-unidade`,
  `.etched` + `.etched-deeper` + `.etched-inked`.
- Skills: `componentes-frontend`, `daisyui`, `htmx`, `mock`, `pydantic-validation-errors`,
  `escrever-testes`, `test-django-views`.

## 6 · Snippets

**`apps/competencias/acoes_declaradas.py`** — a segunda ação inscrita.
```python
ACAO_CONCEDER = instanciar_acao(
    slug="competencias.conceder",
    nome="Conceder competência",
    nome_curto="Competências",
    tooltip="Distribui as atribuições da unidade entre os cargos.",
    url_name="competencias:conceder",
    partial="competencias/partials/_item_menu_conceder.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    # Distribuir é atributo de quem dirige: liberada pela direção da unidade, não por concessão —
    # senão conceder `competencias.conceder` exigiria alguém que já a exercesse.
    estrutural=True,
    # Mesmo alcance da SPEC 007, pela mesma declaração: quem dirige distribui na própria unidade e
    # nas de baixo. A conferência é da proteção (SPEC 004), não desta view.
    alcance=UnidadesSubordinadas(),
)
```

**`apps/competencias/views.py`** — o cerco que sobra para a view, porque o decorator não tem como fazê-lo.
```python
@acao_protegida(ACAO_CONCEDER)
def conceder(request: HttpRequest) -> HttpResponse:
    # A unidade-alvo já foi conferida contra o alcance pelo decorator. A atribuição, não: ela é
    # entidade desta ação, e um id de atribuição de outro ramo passaria pela primeira conferência
    # sem esbarrar em nada.
    comando = ComandoConcessao(
        unidade_alvo_id=request.POST["unidade"],
        atribuicao_id=request.POST["atribuicao"],
        cargo_base_id=request.POST.get("cargo_base"),
        cargo_comissao_id=request.POST.get("cargo_comissao"),
    )
    ...
    registrar_ato(
        request,
        operacao="conceder",
        alvo_tipo="acao_cargo",
        alvo_identificador=f"{acao.slug}:{cargo.padrao}",
    )
```

**`templates/competencias/partials/_modal_conceder.html`** — a natureza do cargo antes do catálogo: são
dois catálogos distintos, e o XOR da SPEC 002 fica visível na tela em vez de só no `CheckConstraint`.
```html
{# Rádio nativo é o campo; o estado é lido em CSS por :has(input:checked). Nenhum estado em JS. #}
<div class="card-well seletor-onsen">
  <span class="seletor-onsen-polegar glass-panel" aria-hidden="true"></span>
  <label class="seletor-onsen-opcao">
    <input type="radio" name="natureza" class="sr-only" checked />
    <span class="seletor-onsen-rotulo etched etched-deeper">Cargo base</span>
  </label>
  <label class="seletor-onsen-opcao">
    <input type="radio" name="natureza" class="sr-only" />
    <span class="seletor-onsen-rotulo etched etched-deeper">Cargo em comissão</span>
  </label>
</div>
```

**`static/src/tema-dimap.dev.css`** — o seletor de duas posições, genérico.
```css
/* Trilha única, metades de largura igual e uma placa que desliza: é isso que faz ler como UM
   controle, e não como dois chips. Os materiais vêm compostos no HTML — poço na trilha, gelo no
   polegar —, sem receita de vidro reescrita aqui. */
.seletor-onsen { @apply relative inline-grid grid-cols-2 p-1; }
/* Metade da trilha menos a folga: assim translateX(100%) pousa exatamente na outra metade. */
.seletor-onsen-polegar { @apply absolute z-0 top-1 bottom-1 left-1 transition-transform duration-500 ease-in-out; }
/* O rádio é sr-only: o anel de foco aparece na TRILHA. `:has(input:focus-visible)`, nunca
   `:focus-within`, que acenderia também no clique de mouse. */
.seletor-onsen:has(input:focus-visible) { @apply ring-2 ring-agua-400/70; }
```

## 7 · Caveats
**O seletor de duas posições nasce como peça genérica do design system**, `.seletor-onsen`, embora só uma
tela o use hoje. Escolha entre duas posições excludentes vai reaparecer, e o §3.4 existe para que a
segunda seja montagem e não invenção. Custo: uma peça no styleguide com um consumidor só, e um nome a um
caractere de distância do `.toggle-onsen` da SPEC `user_admin/015`, que é o interruptor liga/desliga —
confundir os dois é fácil e o styleguide é o único lugar que os separa.

**A natureza do cargo é escolhida antes do catálogo, em vez de um campo único com os dois.** Fundi-los
esconderia o XOR da SPEC 002, e o `select_onsen.js` não trata `optgroup` — nem a saída barata existe.
Custo: são dois campos onde a interface poderia ter um, e o formulário carrega os dois catálogos mesmo
quando só um será usado.

**O alcance é o mesmo da SPEC 007, declarado do mesmo jeito no contrato desta ação.** A unidade sem
titular — e a sem direção — ficaria com atribuições e ninguém para distribuí-las se a tela lesse só a
unidade do perfil, e quem dirige o nível acima já a alcança para atribuir. Custo: as duas ações repetem
a mesma linha de declaração, e mudar o alcance de uma não muda o da outra — a repetição é visível, mas
nada obriga as duas a andarem juntas.

**A atribuição-alvo continua conferida dentro da view.** O decorator confere unidade, que é o alvo que
toda ação com alcance compartilha; a atribuição é entidade desta ação, e ensiná-la ao decorator faria a
proteção conhecer os models de cada ação que ela protege. Custo: esta view tem uma barreira própria que
o contrato não declara, e é a que um refactor descuidado apaga sem o `has_perm` reclamar.

**Conceder a estrutural que a unidade possui não dá alcance a quem a recebe.** A concessão libera o
slug pela porta da SPEC 003, e o alcance continua saindo só das unidades dirigidas (SPEC 004) — o
cargo contemplado abre a tela sem unidade nenhuma para escolher. Custo: o poço oferece a distribuição
de uma competência que, para as duas ações administrativas, só quem responde pela direção exerce de
fato.

**Quem dirige distribui para qualquer cargo dentro do alcance**, inclusive cargos que não ocupa e ações
que não exerce. A competência é da unidade, e distribuí-la é atribuição de quem responde por ela. Custo:
não há segunda aprovação, e o que contém o ato é o registro (SPEC 004).

**A concessão feita pelo substituto não caduca quando o titular volta.** Ela é da unidade, não de quem a
concedeu, e expirá-la faria a competência oscilar com o afastamento de terceiros. Custo: uma decisão
tomada durante a cobertura sobrevive ao fim dela, e desfazê-la é ato explícito de quem voltar.

**`.card-atribuicao` é a mesma classe da SPEC 007**, aqui com a faixa de chips. Custo: a classe tem duas
SPECs donas; quem implementar primeiro a leva ao tema e ao styleguide, e a outra confere em vez de
reescrever.

**A regra de hover do ícone do item é a da SPEC 006**, que cobre as duas formas. O mock desta SPEC a
escreve mais estreita, sem o cartão. Custo: no porte vale a versão da 006 — a última a ser portada não
pode estreitar a primeira, e nada além da revisão impede isso.

## 8 · Testes (TDD)
Todos exercitam a view com dados gravados e carregam o marker `banco`.

- `test_tela_abre_para_quem_dirige` — o titular em exercício entra sem concessão gravada, e o substituto
  dele entra enquanto ele está afastado; quem não dirige recebe 403. *(marker `banco`)*
- `test_poco_traz_so_as_atribuicoes_da_unidade_escolhida` — o poço lista as atribuições da unidade-alvo
  e nenhuma das outras alcançadas; o seletor, esse sim, oferece a subárvore dirigida inteira, e a
  unidade superior não aparece nele. *(marker `banco`)*
- `test_concessao_recusa_unidade_fora_do_alcance` — POST com unidade de outro ramo é recusado mesmo com
  id válido. *(marker `banco`)*
- `test_concessao_recusa_atribuicao_de_outra_unidade` — atribuição existente mas de unidade não alcançada
  é recusada mesmo com id válido. *(marker `banco`)*
- `test_concessao_mira_exatamente_um_cargo` — POST com os dois cargos, ou com nenhum, é recusado antes de
  chegar ao banco. *(marker `banco`)*
- `test_conceder_e_revogar_ficam_registrados_com_alvo` — as duas operações geram execução registrada
  distinguível pela operação, identificando ação e cargo. *(marker `banco`)*
- `test_menu_administrador_mostra_a_acao_so_para_quem_pode` — o item aparece para quem dirige a unidade e
  some para quem não dirige. *(marker `banco`)*
