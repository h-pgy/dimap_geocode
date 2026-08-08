---
spec: autorizacao/007
versao: v1
atualizado_em: 2026-08-07
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC autorizacao/007 — Conceder competência: a primeira ação, ponta a ponta

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como diretor de unidade da DIMAP, quero distribuir entre os cargos da minha unidade as ações que ela
possui, para que um servidor recém-chegado — ou um cargo que a unidade passou a ter — comece a
trabalhar sem depender de alguém mexer em código ou no banco.

## Critérios de aceite
- [ ] A tela lista **apenas as atribuições da unidade do próprio perfil**, e para cada uma os cargos
      que já a exercem.
- [ ] A unidade sobre a qual se concede vem **do perfil autenticado**; valor de unidade enviado no
      request é ignorado.
- [ ] Conceder e revogar acontecem **sem recarregar a página**, trocando só o trecho afetado.
- [ ] A escolha do cargo distingue explicitamente **cargo base** de **cargo em comissão**, e só um
      dos dois é concedido por vez.
- [ ] Não há caminho para conceder uma ação que a unidade **não possui**, nem pela interface nem
      forjando o request.
- [ ] Conceder e revogar são **atos registrados** (SPEC 004), com o alvo identificando ação e cargo.
- [ ] A ação aparece no **menu de administrador** apenas para quem a possui.
- [ ] O design foi **aprovado no mock** antes de qualquer código de aplicação.
- [ ] As peças novas estão renderizadas no styleguide e suas classes migraram para o CSS base.

## Mock de validação
`SPECS/autorizacao/007-mock-conceder-competencia.html` — a tela nos seus estados: unidade com
atribuições e cargos concedidos, atribuição sem nenhum cargo ainda, unidade sem atribuição alguma, o
item da ação no menu de administrador, e o **modal de concessão**, aberto pelo `+` de qualquer
cartão.

Servir com root na **raiz do projeto** (Live Server). Via `file://` o fetch do tema é bloqueado.

## Contexto e decisões de arquitetura

É a SPEC que fecha o épico exercitando tudo: catálogo (001), projeção e concessão (002), avaliador e
backend (003), proteção e registro (004), router (005) e as peças visuais (006). Também é a
**primeira ação inscrita no registro** — até aqui ele estava vazio.

**A ação de conceder é ela própria uma ação concedida.** Não há perfil especial cravado em código: o
diretor concede porque alguém concedeu a ele `competencias.conceder` na unidade dele. O bootstrap
sai pelo superusuário, que atribui e concede pelo admin do Django (SPEC 002) — o atalho do
`PermissionsMixin` cobre o primeiro passo.

**A unidade vem do perfil, nunca do request.** É a superfície de ataque óbvia da tela: um campo de
unidade no formulário permitiria conceder na unidade alheia com um POST forjado. A view lê
`perfil.unidade` e ignora qualquer coisa que chegue com esse nome. Vale como critério de aceite
porque é comportamento observável, não detalhe de implementação.

**Conceder o que a unidade não tem é impossível por estrutura.** A concessão pendura na linha de
atribuição (SPEC 002); a interface só oferece as atribuições da unidade, e um request forjado com
outra atribuição esbarra no fato de ela não pertencer à unidade do perfil. Dois cercos, e o de baixo
não depende do de cima.

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
que dentro da unidade dele — inclusive cargos que ele mesmo não ocupa e ações que ele mesmo não
exerce. Foi decisão explícita: a competência é da unidade, e distribuí-la é a atribuição de quem a
dirige.

## Peças de referência a compor
- `@apps/competencias/models` (SPEC 002) → `AtribuicaoUnidade`, `Concessao`: a tela não cria
  atribuição, só concessão.
- `@apps/competencias/protecao.py` (SPEC 004) → `acao_protegida` e `registrar_alvo`.
- `@apps/competencias/menus.py` (SPEC 005) → `ItemDeMenu` e `ContratoMenu`: o menu de administrador
  pinça esta ação; ela não se inscreve nele.
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
ACAO_CONCEDER = declarar_acao(
    slug="competencias.conceder",
    nome="Conceder competência",
    nome_curto="Competências",
    tooltip="Distribui as atribuições da unidade entre os cargos.",
    url_name="competencias:conceder",
    partial="competencias/partials/_item_menu_conceder.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
)
```

```python
# apps/competencias/views.py
@acao_protegida(ACAO_CONCEDER)
def conceder(request: HttpRequest) -> HttpResponse:
    # A unidade sai do perfil: aceitar do request abriria concessão em unidade alheia.
    comando = ComandoConcessao(
        unidade_id=request.user.unidade_id,
        atribuicao_id=request.POST["atribuicao"],
        cargo_base_id=request.POST.get("cargo_base"),
        cargo_comissao_id=request.POST.get("cargo_comissao"),
    )
    ...
```

## Fora de escopo
- Criar atribuição de unidade: continua sendo do administrador do sistema, pelo admin do Django.
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

- `test_tela_lista_apenas_atribuicoes_da_propria_unidade` — atribuição de outra unidade não aparece,
  nem a de uma unidade superior.
- `test_concessao_ignora_unidade_enviada_no_request` — POST com unidade alheia concede na unidade do
  perfil ou é recusado, nunca na unidade forjada.
- `test_concessao_recusa_atribuicao_de_outra_unidade` — atribuição existente mas de outra unidade é
  recusada mesmo com id válido.
- `test_conceder_e_revogar_ficam_registrados_com_alvo` — as duas operações geram execução registrada
  identificando ação e cargo.
- `test_menu_administrador_mostra_a_acao_so_para_quem_a_possui` — o item aparece para o perfil com a
  concessão e some para o que não a tem.

## Patches

_Nenhum patch registrado até o momento._
