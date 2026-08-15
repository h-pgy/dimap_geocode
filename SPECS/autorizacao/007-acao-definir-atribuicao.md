---
spec: autorizacao/007
versao: v5
atualizado_em: 2026-08-14
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: a ação vira estrutural — quem a exerce é o titular da unidade (SPEC titularidade/001), e a
    seed de bootstrap deixa de existir; o menu de administrador passa a ser declarado aqui; o
    catálogo oferecido exclui as ações estruturais
  - v3: registrada a pendência de revisão de quem abre a tela — com um titular só por unidade
    (SPEC user_admin/014 v5), quem exerce a estrutural é quem responde pela direção, incluindo o
    substituto do titular afastado; a revisão fica para iteração própria
  - v4: pendência resolvida — quem abre a tela é quem responde pela direção da unidade (titular em
    exercício ou substituto dele, SPECs user_admin/014 e 015), e a unidade sem titular ou sem
    direção é alcançada por quem dirige o nível acima
  - v5: a origem do alcance passa a ser as unidades que o perfil DIRIGE, e não a de lotação — quem
    cobre o titular de outra unidade dirige aquela (SPEC user_admin/015); e a SPEC foi reescrita no
    formato de seções numeradas da skill `specs`
---

# SPEC autorizacao/007 — Definir atribuição: a competência da unidade, e a primeira ação do registro

## 1 · User story
Quem responde pela direção de uma unidade da DIMAP define quais ações a unidade e as de baixo exercem,
na tela de atribuições, para que uma competência nova entre em vigor sem ninguém mexer no banco.

## 2 · Condições de pronto
- [ ] Quem abre a tela é **quem responde pela direção** da unidade — o titular em exercício ou o
      substituto vigente dele —, sem depender de atribuição ou concessão gravada; quem não dirige recebe
      403 mesmo com concessão da ação.
- [ ] A tela oferece como alvo **as unidades que o perfil dirige e as que estão abaixo delas** no
      organograma; unidade fora desse alcance não aparece — e é recusada se vier no request.
- [ ] O catálogo oferecido traz **apenas as ações ativas e não estruturais** que a unidade-alvo ainda
      **não** tem.
- [ ] Atribuir e remover acontecem **sem recarregar a página**, trocando só o trecho afetado.
- [ ] Remover atribuição que tem concessões **exige confirmação** e diz **quantos cargos** perdem a
      competência; confirmada, as concessões vão junto.
- [ ] Atribuir e remover são **atos registrados** (SPEC 004), distinguíveis pela operação e com o alvo
      identificando unidade e ação.
- [ ] O **menu de administrador** é declarado em código e resolvido pelo router (SPEC 005): mostra esta
      ação a quem pode executá-la e some para quem não pode.
- [ ] O design foi aprovado no **mock**, e `.card-atribuicao` foi portada para
      `static/src/tema-dimap.dev.css` e renderizada no styleguide antes de qualquer template da
      aplicação usá-la.

## 3 · Domínio
Nenhum model novo: a SPEC 002 já entregou as duas tabelas, e esta é o **nível 1** delas virando ato
administrativo. O que nasce aqui é uma regra de domínio — o **alcance**: a unidade de origem e tudo
abaixo dela na árvore.

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`Acao`, `AtribuicaoUnidade` e `Concessao`](002-competencia-no-banco.md) — "o que a unidade já exerce,
  o que o catálogo ainda oferece, e quantos cargos caem junto se a atribuição sair?".
- [`has_perm`](003-avaliador-e-backend-de-autorizacao.md) — "este perfil exerce esta ação estrutural?";
  quem lê a direção da unidade é o backend, não esta tela.
- [`CadeiraExercida`](003-avaliador-e-backend-de-autorizacao.md) — "quais unidades este perfil dirige
  hoje?", que é de onde o alcance parte.
- [`acao_protegida` e `registrar_ato`](004-protecao-de-rota-e-registro-de-execucao.md) — a rota protegida
  e o rastro dos dois atos.
- [`ItemDeMenu`, `ContratoMenu` e `RoteadorMenu`](005-contrato-de-menu-e-router.md) — o menu de
  administrador, que **pinça** esta ação; ela não se inscreve nele.
- `Unidade.pai` / `Unidade.filhas` — a árvore que o alcance percorre, sem alteração.

**Mock:** [007-mock-definir-atribuicao.html](007-mock-definir-atribuicao.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Distribuir a atribuição entre os cargos — SPEC 008.
- Herança de competência pelo organograma: alcançar a unidade filha para **editar** não é fazê-la
  **exercer** (SPEC 002).
- Criar, mover ou renomear unidade, marcar titular e designar substituto — SPECs `user_admin/012`, `014`
  e `015`.
- Concessão nominal a um servidor e concessão por natureza de cargo — sem dono ainda.
- Tela de consulta do histórico de execuções — SPEC 004.
- Demais ações da plataforma: esta SPEC inscreve uma só.

## 5 · Peças de referência a compor
- `@apps/competencias/models` (SPEC 002) → `Acao`, `AtribuicaoUnidade`, `Concessao`.
- `@apps/competencias/utils.py` (SPEC 001) → `instanciar_acao`, e `@apps/competencias/registro.py` →
  `_construir_registro`: esta ação é a primeira inscrita.
- `@apps/competencias/protecao.py` (SPEC 004) → `acao_protegida` e `registrar_ato`.
- `@apps/competencias/menus.py` (SPEC 005) → `ItemDeMenu`, `ContratoMenu`, `RoteadorMenu`.
- `@apps/competencias/consulta.py` (SPEC 003) → `cadeiras_do_perfil`: as unidades dirigidas já saem
  resolvidas dali.
- `@apps/user_admin/models/unidade.py` → `Unidade.pai` / `filhas`: a árvore.
- `@templates/user_admin/servidores_list.html` e `@templates/user_admin/unidade.html`: a área
  administrativa onde o organismo de menu é renderizado.
- SPEC 006 → `.card-acao`, `.card-acao-nome`, `.card-acao-descricao`, `.icone-acao`: o cartão explicativo
  é o item do catálogo, sem redesenho.
- `@static/src/tema-dimap.dev.css` → `.card-well`, `.glass-panel`, `.modal-glass` + `.modal-box-glass`,
  `.select-onsen`, `.btn-onsen`, `.btn-glass`, `.text-overline`, `.dot-unidade`.
- Skills: `componentes-frontend`, `daisyui`, `htmx`, `mock`, `pydantic-validation-errors`,
  `escrever-testes`, `test-django-views`.

## 6 · Snippets

**`apps/competencias/acoes_declaradas.py`** — a primeira ação inscrita no registro.
```python
ACAO_DEFINIR_ATRIBUICAO = instanciar_acao(
    slug="competencias.definir_atribuicao",
    nome="Definir atribuições da unidade",
    nome_curto="Atribuições",
    tooltip="Define quais ações a unidade exerce.",
    url_name="competencias:definir_atribuicao",
    partial="competencias/partials/_item_menu_definir_atribuicao.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    # Quem a exerce é quem dirige a unidade: não passa por atribuição nem concessão, e é isso que
    # dispensa qualquer seed de bootstrap.
    estrutural=True,
)
```

**`apps/competencias/menus_declarados.py`** — o menu pinça a ação; a ação não se inscreve.
```python
MENU_ADMINISTRADOR = ContratoMenu(
    slug="competencias.administrador",
    nome="Administração",
    itens=(
        ItemDeMenu(
            acao=ACAO_DEFINIR_ATRIBUICAO,
            variante_icone=VarianteIcone.PEQUENO,
            forma=FormaItem.LINHA,
        ),
    ),
)
```

**`services/domain/autorizacao/alcance.py`** — mesmo submódulo do avaliador (SPEC 003), não um novo.
```python
class ParUnidade(BaseModel):
    model_config = ConfigDict(frozen=True)

    unidade_id: int
    pai_id: int | None


class ComandoAlcance(BaseModel):
    model_config = ConfigDict(frozen=True)

    # As unidades DIRIGIDAS, não a de lotação: quem cobre o titular de outra unidade dirige aquela
    # (SPEC user_admin/015), e pode dirigir duas ao mesmo tempo.
    origens: frozenset[int]
    pares: tuple[ParUnidade, ...]


class AlcanceDeUnidades:
    """As origens e tudo abaixo delas. Recebe os pares por DTO: a regra é testável sem banco, e a
    árvore da DIMAP cabe numa consulta só."""

    def __call__(self, comando: ComandoAlcance) -> frozenset[int]: ...
```

**`apps/competencias/views.py`** — duas barreiras distintas: o decorator barra quem não dirige, o
domínio recusa unidade-alvo fora do alcance.
```python
@acao_protegida(ACAO_DEFINIR_ATRIBUICAO)
def definir_atribuicao(request: HttpRequest) -> HttpResponse:
    # Sem esta validação um POST forjado atribuiria competência em ramo alheio: `has_perm` responde
    # pela competência, não pelo alvo.
    comando = ComandoAtribuicao(
        origens=unidades_dirigidas(request.user),
        unidade_alvo_id=request.POST["unidade"],
        acao_slug=request.POST["acao"],
    )
    ...
    registrar_ato(
        request,
        operacao="atribuir",
        alvo_tipo="unidade_acao",
        alvo_identificador=f"{unidade.sigla}:{acao.slug}",
    )
```

**`apps/competencias/catalogo.py`** — o que o modal oferece.
```python
def acoes_oferecidas(unidade: Unidade) -> QuerySet[Acao]:
    """Ativas, não estruturais e ainda não atribuídas. O filtro é pela COLUNA `estrutural`, não por
    lista de slugs, para a próxima ação estrutural não precisar lembrar de se excluir."""
    return Acao.objects.filter(ativa=True, estrutural=False).exclude(
        atribuicoes__unidade=unidade,
    )
```

## 7 · Caveats
**As duas ações administrativas moram no app `competencias`, e isso é exceção declarada ao §3.5.** A
regra existe para que um processo novo da DIMAP não engorde o núcleo, e estas duas não são processos:
são a administração da própria competência, operam sobre os models desta SPEC e não existem sem eles.
Custo: o app deixa de ser só infraestrutura de autorização e passa a ter view, template e tela.

**A autorização acontece em dois lugares para o mesmo ato**: o decorator confere a competência, o
domínio confere o alvo. `has_perm` responde pela unidade em que o perfil exerce e nada mais — alcançar
as unidades abaixo é regra desta ação, não da decisão de acesso. Custo: quem lê a view precisa saber que
passar pelo decorator não basta, e uma ação futura que esqueça a segunda barreira fica aberta a POST
forjado com id de outro ramo.

**O alcance é calculado em Python, sobre todos os pares `(unidade, pai)` carregados numa consulta.**
Manter a regra fora do ORM é o que a torna testável sem banco (§3.3), e o organograma da DIMAP é menor
que o custo de uma recursão em SQL. Custo: a tela carrega o organograma inteiro a cada abertura, e isso
deixa de ser barato se a árvore crescer para além da DIMAP.

**Quem dirige a raiz alcança o organograma inteiro.** O Secretário é titular da unidade-raiz, e a
subárvore da raiz é tudo — o alcance máximo cai da mesma regra, sem exceção escrita para a alta
administração. Custo: um único perfil concentra a competência de atribuir em qualquer unidade, e o que
o contém é o registro do ato, não uma segunda barreira.

**Autoatribuição é aceita.** Quem dirige a unidade responde pelo que ela faz, inclusive por passar a
exercer uma ação nova. Custo: nada impede que quem dirige amplie a própria competência, e o controle
disso é o registro (SPEC 004), não uma aprovação de terceiro.

**A remoção cascateia nas concessões, e a confirmação é o único lugar onde isso aparece antes.** A
contagem é lida no momento em que o modal é montado. Custo: entre a pergunta e o "sim" outra pessoa pode
conceder mais um cargo, e o número que o diretor viu não é o que caiu.

**`.card-atribuicao` é a mesma classe da SPEC 008**, aqui no estado sem chips. Duas telas mostram a mesma
coisa — uma atribuição da unidade — e desenhá-la duas vezes seria inventar peça já existente. Custo: a
classe tem duas SPECs donas; quem implementar primeiro a leva ao tema e ao styleguide, e a outra confere
em vez de reescrever — se a segunda estreitar a regra, a primeira quebra longe daqui.

## 8 · Testes (TDD)
Carregam o marker `banco`, menos o do alcance, que é domínio puro e roda na suíte padrão.

- `test_alcance_cobre_a_subarvore_e_para_no_ramo` — a partir das origens, devolve elas e todas as
  descendentes; nunca a superior, a irmã ou outro ramo. Duas origens devolvem a união das duas
  subárvores.
- `test_tela_abre_para_quem_dirige_e_nega_o_resto` — o titular em exercício entra sem concessão nenhuma
  gravada, e o substituto dele entra enquanto ele está afastado; quem não dirige recebe 403 mesmo com
  concessão da ação. *(marker `banco`)*
- `test_catalogo_oferece_so_o_que_falta_e_nao_oferece_estrutural` — a ação já atribuída, a inativa e a
  estrutural ficam fora da oferta. *(marker `banco`)*
- `test_atribuir_recusa_unidade_fora_do_alcance` — POST com unidade existente mas de outro ramo é
  recusado mesmo com id válido. *(marker `banco`)*
- `test_remover_com_concessoes_exige_confirmacao` — sem confirmação nada é apagado; confirmada, a
  atribuição e as concessões dependentes somem juntas. *(marker `banco`)*
- `test_atribuir_e_remover_ficam_registrados_com_alvo` — as duas operações geram execução registrada
  distinguível pela operação, identificando unidade e ação. *(marker `banco`)*
- `test_menu_administrador_mostra_a_acao_so_para_quem_pode` — o item aparece para quem dirige a unidade e
  some para quem não dirige. *(marker `banco`)*
