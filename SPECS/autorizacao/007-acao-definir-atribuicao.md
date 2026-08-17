---
spec: autorizacao/007
versao: v9
atualizado_em: 2026-08-17
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
  - v6: o catálogo volta a oferecer as ações estruturais — a estrutural agora pode ser concedida a
    outros cargos além de quem dirige (SPEC 003), e sem a atribuição não há o que conceder
  - v7: o alcance passa a ser declarado no contrato da ação e conferido pela proteção (SPEC 004); a
    regra da subárvore sai desta SPEC para a `user_admin/018` e a view perde a conferência à mão
  - v8: a lista de alvos oferecidos passa a sair da árvore hierárquica em `alvos_oferecidos`, com a
    subordinação visível no seletor, e `alcance_do_perfil` fica só como a barreira do decorator
  - v9: acompanha o rename de `ItemDeMenu.acao` para `acao_implementada` na SPEC 005 v4
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
      organograma, na **ordem do organograma e com a subordinação visível**; unidade fora desse alcance
      não aparece — e é recusada se vier no request.
- [ ] O catálogo oferecido traz **todas as ações ativas** que a unidade-alvo ainda **não** tem — as
      estruturais inclusive, que a unidade precisa possuir para poder concedê-las (SPEC 008).
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
Nenhum model novo e nenhuma regra nova: a SPEC 002 já entregou as duas tabelas, e esta é o **nível 1**
delas virando ato administrativo. A ação é a primeira do registro a **declarar alcance**, e é o contrato
dela que diz sobre quais unidades pode incidir.

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`Acao`, `AtribuicaoUnidade` e `Concessao`](002-competencia-no-banco.md) — "o que a unidade já exerce,
  o que o catálogo ainda oferece, e quantos cargos caem junto se a atribuição sair?".
- [`has_perm`](003-avaliador-e-backend-de-autorizacao.md) — "este perfil exerce esta ação estrutural?";
  quem lê a direção da unidade é o backend, não esta tela.
- [`SubarvoreDirigida`](004-protecao-de-rota-e-registro-de-execucao.md) — "até onde o alvo desta ação
  pode chegar?", declarado no contrato dela.
- [`acao_protegida` e `registrar_ato`](004-protecao-de-rota-e-registro-de-execucao.md) — a rota
  protegida, o alvo conferido contra o alcance e o rastro dos dois atos.
- [`alcance_do_perfil`](004-protecao-de-rota-e-registro-de-execucao.md) — "este id de unidade está no
  alcance?"; a resposta é um conjunto de ids, e quem a consome é o decorator.
- [`posicao_de` e `NoHierarquia`](../user_admin/018-arvore-hierarquica.md) — "em que ordem e a que
  profundidade o organograma alcançado se lê?"; é dali que sai o seletor de alvos, que precisa da
  forma da árvore e não do conjunto.
- [`ItemDeMenu`, `ContratoMenu` e `RoteadorMenu`](005-contrato-de-menu-e-router.md) — o menu de
  administrador, que **pinça** esta ação; ela não se inscreve nele.

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
- `@apps/competencias/consulta.py` (SPEC 004) → `alcance_do_perfil` e `unidades_dirigidas`: o conjunto
  de ids alcançados e as unidades de onde ele parte.
- `@apps/user_admin/consulta.py` → `posicao_de`, e `@apps/user_admin/context.py` →
  `contexto_organograma` (SPEC `user_admin/018`): a subárvore de uma unidade e o padrão de casar os ids
  dela com as `Unidade` num `in_bulk`.
- `@services/domain/autorizacao/contratos.py` (SPEC 004) → `SubarvoreDirigida`: o alcance declarado no
  contrato da ação.
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
    # Onde ela pode incidir, e não só quem a exerce: o dirigente age sobre a própria unidade e sobre
    # as de baixo. Declarado aqui, a proteção (SPEC 004) o cumpre sozinha — a view não repete a
    # conferência, e a ação seguinte que precisar de alcance também não a reescreve.
    alcance=SubarvoreDirigida(parametro="unidade"),
)
```

**`apps/competencias/menus_declarados.py`** — o menu pinça a ação; a ação não se inscreve.
```python
MENU_ADMINISTRADOR = ContratoMenu(
    slug="competencias.administrador",
    nome="Administração",
    itens=(
        ItemDeMenu(
            acao_implementada=ACAO_DEFINIR_ATRIBUICAO,
            variante_icone=VarianteIcone.PEQUENO,
            forma=FormaItem.LINHA,
        ),
    ),
)
```

**`apps/competencias/views.py`** — a view chega com competência e alvo já conferidos; o alcance só
reaparece aqui para montar a lista de alvos oferecidos, que é UX, não barreira.
```python
@acao_protegida(ACAO_DEFINIR_ATRIBUICAO)
def definir_atribuicao(request: HttpRequest) -> HttpResponse:
    # Nenhuma conferência de alcance escrita aqui: o POST forjado com unidade de outro ramo já foi
    # recusado pelo decorator, que leu o alcance do contrato da ação.
    comando = ComandoAtribuicao(
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

**`apps/competencias/consulta.py`** — a mesma árvore que o decorator confere, aqui na forma que a tela
desenha. Ao lado de `alcance_do_perfil` (SPEC 004), que a lê como conjunto.
```python
def alvos_oferecidos(perfil: Perfil) -> list[dict[str, Any]]:
    """As unidades alcançadas na ordem do organograma, com a profundidade que o seletor indenta. O
    conjunto de ids de `alcance_do_perfil` não serve aqui: ele não tem ordem nem nível, e o seletor
    precisa dos dois."""
    arvores = [posicao_de(dirigida).ego for dirigida in unidades_dirigidas(perfil)]
    # Segunda consulta para casar id com Unidade, como no organograma da SPEC user_admin/018: sem
    # ela o domínio precisaria conhecer `Unidade` para já devolver sigla e cor.
    por_id = Unidade.objects.in_bulk(
        frozenset(unidade_id for arvore in arvores for unidade_id in arvore.ids)
    )
    return [alvo for arvore in arvores for alvo in _achatar(arvore, por_id, profundidade=0)]


def _achatar(
    no: NoHierarquia,
    por_id: Mapping[int, Unidade],
    profundidade: int,
) -> Iterator[dict[str, Any]]:
    """Pré-ordem: a unidade antes do que pende dela, que é a ordem em que o organograma se lê."""
    yield {"unidade": por_id[no.unidade_id], "profundidade": profundidade}
    for filha in sorted(no.filhas, key=lambda filha: por_id[filha.unidade_id].sigla):
        yield from _achatar(filha, por_id, profundidade + 1)
```

**`apps/competencias/catalogo.py`** — o que o modal oferece.
```python
def acoes_oferecidas(unidade: Unidade) -> QuerySet[Acao]:
    """Ativas e ainda não atribuídas. A estrutural entra: quem dirige já a exerce sem atribuição
    nenhuma (SPEC 003), mas delegá-la a outro cargo exige que a unidade a possua primeiro."""
    return Acao.objects.exclude(atribuicoes__unidade=unidade).filter(ativa=True)
```

## 7 · Caveats
**As duas ações administrativas moram no app `competencias`, e isso é exceção declarada ao §3.5.** A
regra existe para que um processo novo da DIMAP não engorde o núcleo, e estas duas não são processos:
são a administração da própria competência, operam sobre os models desta SPEC e não existem sem eles.
Custo: o app deixa de ser só infraestrutura de autorização e passa a ter view, template e tela.

**A autorização continua acontecendo em duas conferências, agora as duas dentro do decorator**: a
competência responde pela unidade em que o perfil exerce, o alcance responde por sobre qual unidade ele
pode incidir. Declarar o alcance no contrato (SPEC 004) é o que impede que cada ação nova reescreva a
segunda — e esqueça. Custo: quem lê a view não vê nenhuma das duas, e a barreira que a protege está no
`acoes_declaradas.py`, longe daqui.

**A árvore é percorrida duas vezes por abertura de tela**: uma pelo decorator, para conferir o alvo, e
outra pela view, para montar a lista de unidades oferecidas. Cachear a segunda exigiria carregar estado
entre decorator e view, e o organograma da DIMAP é pequeno. Custo: cada uma das duas recarrega todos os
pares uma vez por unidade dirigida — até quatro varreduras do organograma por requisição, já que
dirigir duas unidades é o caso normal de quem cobre o titular de outra.

**A mesma árvore é lida em duas formas, por duas funções**: `alcance_do_perfil` a reduz a um conjunto
de ids, e `alvos_oferecidos` a achata na ordem do organograma. Uma só forma serviria mal aos dois — o
conjunto não desenha o seletor, e a lista ordenada não responde pertinência em tempo constante. Custo:
o que a barreira aceita e o que a tela oferece são calculados separadamente, e passam a divergir se
uma das duas mudar de origem.

**Quem dirige a raiz alcança o organograma inteiro.** O Secretário é titular da unidade-raiz, e a
subárvore da raiz é tudo — o alcance máximo cai da mesma regra, sem exceção escrita para a alta
administração. Custo: um único perfil concentra a competência de atribuir em qualquer unidade, e o que
o contém é o registro do ato, não uma segunda barreira.

**Autoatribuição é aceita.** Quem dirige a unidade responde pelo que ela faz, inclusive por passar a
exercer uma ação nova. Custo: nada impede que quem dirige amplie a própria competência, e o controle
disso é o registro (SPEC 004), não uma aprovação de terceiro.

**O catálogo oferece as duas ações administrativas desta SPEC e da 008, como qualquer outra.** Elas são
estruturais e agora a estrutural é concedível (SPEC 003); excluí-las exigiria uma lista de slugs
privilegiados, que é a configuração em runtime que o §3.5 recusa. Custo: quem dirige pode atribuir e
depois conceder a um cargo o poder de atribuir e conceder — a delegação não tem profundidade limitada, e
o que a contém é o registro do ato.

**A remoção cascateia nas concessões, e a confirmação é o único lugar onde isso aparece antes.** A
contagem é lida no momento em que o modal é montado. Custo: entre a pergunta e o "sim" outra pessoa pode
conceder mais um cargo, e o número que o diretor viu não é o que caiu.

**`.card-atribuicao` é a mesma classe da SPEC 008**, aqui no estado sem chips. Duas telas mostram a mesma
coisa — uma atribuição da unidade — e desenhá-la duas vezes seria inventar peça já existente. Custo: a
classe tem duas SPECs donas; quem implementar primeiro a leva ao tema e ao styleguide, e a outra confere
em vez de reescrever — se a segunda estreitar a regra, a primeira quebra longe daqui.

## 8 · Testes (TDD)
Todos carregam o marker `banco`.

- `test_tela_abre_para_quem_dirige_e_nega_o_resto` — o titular em exercício entra sem concessão nenhuma
  gravada, e o substituto dele entra enquanto ele está afastado; quem não dirige recebe 403 mesmo com
  concessão da ação. *(marker `banco`)*
- `test_seletor_oferece_a_subarvore_na_ordem_do_organograma` — o seletor traz a unidade dirigida antes
  das de baixo, cada uma com a profundidade dela; unidade de outro ramo e unidade acima não aparecem.
  *(marker `banco`)*
- `test_catalogo_oferece_so_o_que_falta` — a ação já atribuída e a inativa ficam fora da oferta; a
  estrutural que a unidade ainda não tem é oferecida. *(marker `banco`)*
- `test_atribuir_recusa_unidade_fora_do_alcance` — POST com unidade existente mas de outro ramo é
  recusado mesmo com id válido, sem a view conferir nada: é a declaração do contrato chegando à rota.
  *(marker `banco`)*
- `test_remover_com_concessoes_exige_confirmacao` — sem confirmação nada é apagado; confirmada, a
  atribuição e as concessões dependentes somem juntas. *(marker `banco`)*
- `test_atribuir_e_remover_ficam_registrados_com_alvo` — as duas operações geram execução registrada
  distinguível pela operação, identificando unidade e ação. *(marker `banco`)*
- `test_menu_administrador_mostra_a_acao_so_para_quem_pode` — o item aparece para quem dirige a unidade e
  some para quem não dirige. *(marker `banco`)*
