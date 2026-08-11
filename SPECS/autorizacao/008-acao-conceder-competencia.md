---
spec: autorizacao/008
versao: v3
atualizado_em: 2026-08-11
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: renumerada de 007 para 008 — criar a atribuição da unidade virou ação própria (SPEC 007),
    que passa a ser a primeira ação inscrita e a origem do bootstrap; aqui sobra o nível 2
  - v3: a ação vira estrutural, exercida pelo titular (SPEC titularidade/001) — o bootstrap deixa
    de depender de seed; o alcance passa da própria unidade à subárvore, como na SPEC 007
---

# SPEC autorizacao/008 — Conceder competência: distribuir entre os cargos o que a unidade tem

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como diretor de unidade da DIMAP, quero distribuir entre os cargos da minha unidade as ações que ela
possui, para que um servidor recém-chegado — ou um cargo que a unidade passou a ter — comece a
trabalhar sem depender de alguém mexer em código ou no banco.

## Critérios de aceite
- [ ] Quem abre a tela é **o titular da unidade** (SPEC `titularidade/001`), sem depender de
      concessão gravada desta ação.
- [ ] A tela lista as atribuições **da unidade-alvo**, que é a do perfil ou uma **abaixo dela** no
      organograma; unidade fora da subárvore é recusada mesmo vindo no request.
- [ ] Conceder e revogar acontecem **sem recarregar a página**, trocando só o trecho afetado.
- [ ] A escolha do cargo distingue explicitamente **cargo base** de **cargo em comissão**, e só um
      dos dois é concedido por vez.
- [ ] Não há caminho para conceder uma ação que a unidade **não possui**, nem pela interface nem
      forjando o request.
- [ ] Conceder e revogar são **atos registrados** (SPEC 004), distinguíveis pela operação e com o
      alvo identificando ação e cargo.
- [ ] A ação aparece no **menu de administrador** (SPEC 007) apenas para quem pode executá-la.
- [ ] O design foi **aprovado no mock** antes de qualquer código de aplicação.
- [ ] As peças novas estão renderizadas no styleguide e suas classes migraram para o CSS base.

## Mock de validação
`SPECS/autorizacao/008-mock-conceder-competencia.html` — a tela nos seus estados: unidade com
atribuições e cargos concedidos, atribuição sem nenhum cargo ainda, unidade sem atribuição alguma, o
item da ação no menu de administrador, e o **modal de concessão**, aberto pelo `+` de qualquer
cartão.

Servir com root na **raiz do projeto** (Live Server). Via `file://` o fetch do tema é bloqueado.

## Contexto e decisões de arquitetura

É a SPEC que fecha o épico exercitando tudo: catálogo (001), projeção e concessão (002), avaliador e
backend (003), proteção e registro (004), router (005) e as peças visuais (006). É o **nível 2** do
modelo da 002 — a 007 entrega o nível 1 e é quem põe atribuição no banco para esta tela distribuir.

**Distribuir competência é atributo de quem dirige, então esta ação também é estrutural.** Marcada
`estrutural` (SPEC 001), ela é liberada pela titularidade (SPEC 003) sem passar por atribuição nem
concessão. Se fosse concedida como as demais, o épico voltaria a ter um primeiro estado impossível:
conceder `competencias.conceder` a um cargo exigiria alguém que já a exercesse. Não há seed nem
perfil especial cravado em código — há o titular.

**O alcance é a subárvore, como na SPEC 007.** A versão anterior lia a unidade do perfil e ignorava o
request; isso deixava a unidade **sem titular** com atribuições e ninguém para distribuí-las. Como o
titular do nível acima já a alcança para atribuir, ele a alcança também para conceder — a alternativa
seria a unidade órfã ficar inerte até alguém ser nomeado. A barreira muda de forma, não de força: a
unidade-alvo é validada contra a subárvore do perfil pelo mesmo `AlcanceDeUnidades` da SPEC 007, e
unidade de outro ramo é recusada com id válido.

**Conceder o que a unidade não tem é impossível por estrutura.** A concessão pendura na linha de
atribuição (SPEC 002); a interface só oferece as atribuições da unidade-alvo, e um request forjado
com outra atribuição esbarra no fato de ela não pertencer a uma unidade alcançada. Dois cercos, e o
de baixo não depende do de cima.

**Conceder acontece num modal, não num campo embutido no cartão.** A escolha é maior do que um
dropdown: a concessão mira **um** cargo, base **ou** em comissão (o XOR da SPEC 002), e são dois
catálogos distintos. Fundi-los num único campo esconderia a regra — e `select_onsen.js` não trata
`optgroup`, então nem a saída barata existe. No modal a natureza do cargo é escolhida antes do
catálogo, e a regra fica visível na tela em vez de só no `CheckConstraint`. O modal vive **fora** do
cartão e de qualquer formulário: formulário aninhado é HTML inválido, e é o padrão que o projeto já
usa para gatilho-em-campo (SPEC user_admin/012).

**A escolha da natureza pede uma molécula nova: o toggle de vidro.** O `join` com `btn` do daisyUI
foi descartado — quinas quadradas no meio e a paleta dele, que não é a da cena. Mas duas peças
soltas lado a lado também não servem: leem como dois chips, não como um controle de duas posições. O
que dá a leitura são três coisas juntas — **trilha única, metades de largura igual sem folga, e uma
placa que desliza** de uma para a outra. E os materiais são os dois do design system em oposição: a
trilha é **poço** (`.card-well`), porque escolha é campo e campo aqui é sempre coisa rebaixada; o
polegar é **placa de gelo** (`.glass-panel`) correndo sobre ele — a mesma figura da tabela de vidro,
agora em movimento. Nenhuma receita de vidro é reescrita: os dois materiais são compostos no HTML.

A tinta do rótulo alterna entre `.etched-deeper` em repouso e `.etched-inked` quando selecionado —
ambos já existentes, sem cinza de desabilitado. Estado lido em CSS por `:has(input:checked)`, com o
rádio nativo continuando a ser o campo: nenhum estado de UI em JavaScript.

O toggle nasce **genérico** (`.toggle-onsen`), não como peça desta tela: escolha entre duas posições
excludentes vai reaparecer, e o §3.4 existe para que a segunda seja montagem e não invenção.

**Revogar também é ato.** Tirar competência muda o que alguém pode fazer tanto quanto dar; as duas
operações passam pelo mesmo decorator e deixam rastro, com o alvo dizendo qual ação e qual cargo.

**Escopo do diretor é a unidade, não o cargo.** Ele distribui para qualquer cargo do catálogo, desde
que dentro de uma unidade que alcança — inclusive cargos que ele mesmo não ocupa e ações que ele
mesmo não exerce. Foi decisão explícita: a competência é da unidade, e distribuí-la é a atribuição de
quem a dirige.

**Duas peças novas: o toggle e o chip.** Além do `.toggle-onsen`, a concessão já feita aparece como
`.chip-concessao` com afordância de remoção — o cartão da atribuição precisa mostrar *quais* cargos
exercem, e badge simples não carrega ação. As duas vão ao CSS base e ao styleguide no porte.

**A regra de hover do ícone do item é a da SPEC 006.** O mock desta SPEC a escreve mais estreita, sem
o cartão; no porte vale a versão da 006, que cobre as duas formas — a classe é compartilhada e a
última a ser portada não pode estreitar a primeira.

## Peças de referência a compor
- `@apps/competencias/models` (SPEC 002) → `AtribuicaoUnidade`, `Concessao`: a tela não cria
  atribuição, só concessão.
- SPEC 007 → a ação `competencias.definir_atribuicao`, o `MENU_ADMINISTRADOR` e o
  `AlcanceDeUnidades`: é ela que põe atribuição no banco, declara o menu que esta ação também compõe
  e entrega a regra de subárvore reusada aqui. `.card-atribuicao` é a **mesma classe** das duas
  telas — quem implementar primeiro a leva ao CSS base e ao styleguide; aqui ela ganha os chips.
- `@apps/competencias/protecao.py` (SPEC 004) → `acao_protegida` e `registrar_ato`.
- `@apps/competencias/menus.py` (SPEC 005) → `ItemDeMenu` e `ContratoMenu`: o menu de administrador
  pinça esta ação; ela não se inscreve nele.
- `@apps/user_admin/models/user.py` → `Perfil.e_titular` (SPEC `titularidade/001`): a fonte da
  competência desta ação.
- Skill `componentes-frontend` → `.card-well`, `.select-onsen` (SPEC user_admin/011), `.btn-onsen`,
  `.btn-glass`, `.text-overline`, `.icon-etched`, badges semânticos.
- `.modal-glass` + `.modal-box-glass`: o modal já existe no design system e abre por checkbox
  nativo — não se escreve JS para isso.
- `.etched` + `.etched-rotulo` (SPEC user_admin/013): o repouso do seletor de natureza é a gravação
  que já existe; a tinta sobe porque o sulco ali **nomeia** a opção.
- SPEC 006 → `.icone-acao`: a ação aparece na tela com o próprio glifo.
- `@apps/user_admin/models` → `CargoBase`, `CargoComissao`: catálogo oferecido no campo.
- Skill `pydantic-validation-errors`: a view monta o DTO e deixa o middleware tratar — sem
  `try/except`.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md

# apps/competencias/acoes_declaradas.py
ACAO_CONCEDER = instanciar_acao(
    slug="competencias.conceder",
    nome="Conceder competência",
    nome_curto="Competências",
    tooltip="Distribui as atribuições da unidade entre os cargos.",
    url_name="competencias:conceder",
    partial="competencias/partials/_item_menu_conceder.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    # Distribuir é atributo de quem dirige: liberada pela titularidade, não por concessão.
    estrutural=True,
)
```

```python
# apps/competencias/views.py
@acao_protegida(ACAO_CONCEDER)
def conceder(request: HttpRequest) -> HttpResponse:
    # A unidade-alvo é validada contra a subárvore do perfil: sem isso um POST forjado concede em
    # ramo alheio.
    comando = ComandoConcessao(
        unidade_origem_id=request.user.unidade_id,
        unidade_alvo_id=request.POST["unidade"],
        atribuicao_id=request.POST["atribuicao"],
        cargo_base_id=request.POST.get("cargo_base"),
        cargo_comissao_id=request.POST.get("cargo_comissao"),
    )
    ...
```

## Fora de escopo
- Criar atribuição de unidade: é a ação `competencias.definir_atribuicao` (SPEC 007).
- Concessão nominal a um servidor e concessão por natureza de cargo.
- Impedimento e substituição.
- Tela de consulta do histórico de execuções.
- Demais ações da plataforma: esta SPEC inscreve uma só.
- Aplicar a migração: o agente gera, quem aplica é o usuário (CLAUDE.md §4).

## Porte obrigatório após a aprovação do mock
As classes novas migram **tal e qual** para `static/src/tema-dimap.dev.css` (fonte única, SPEC
design/004), e cada peça nova é renderizada em
`.claude/skills/componentes-frontend/examples/design_system.html`, na seção da sua camada. A SPEC não
está implementada enquanto os dois portes não tiverem sido feitos.

## Testes (TDD)
Todos exercitam a view com dados gravados e carregam o marker `banco`.

- `test_tela_abre_para_titular_e_lista_a_subarvore` — o titular entra sem concessão gravada e vê as
  atribuições da própria unidade e das de baixo; a da unidade superior não aparece.
- `test_concessao_recusa_unidade_fora_do_alcance` — POST com unidade de outro ramo é recusado mesmo
  com id válido.
- `test_concessao_recusa_atribuicao_de_outra_unidade` — atribuição existente mas de unidade não
  alcançada é recusada mesmo com id válido.
- `test_conceder_e_revogar_ficam_registrados_com_alvo` — as duas operações geram execução registrada
  distinguível pela operação, identificando ação e cargo.
- `test_menu_administrador_mostra_a_acao_so_para_quem_pode` — o item aparece para o titular e some
  para quem não é.

## Patches

_Nenhum patch registrado até o momento._
