---
spec: autorizacao/007
versao: v11
atualizado_em: 2026-08-21
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
  - v10: a estrutural com alcance passa a ser exercida só por quem dirige — a concessão dela libera
    o slug e não o alvo —, o alcance declarado passa a ser `UnidadesSubordinadas` e o seletor deixa
    de repetir o ramo comum a duas unidades dirigidas
  - v11: o alvo passa a ser escolhido no organograma da SPEC `user_admin/018`, e não numa lista
    suspensa — `alvos_oferecidos` e o achatamento saem por serem a travessia de `contexto_organograma`
    reescrita; a travessia das dirigidas passa a ter uma origem só, `ramos_do_alcance`, de que
    `alcance_do_perfil` (SPEC 004) vira projeção; e o partial `_no_arvore.html` ganha as flags que
    permitem reusá-lo aqui
---

# SPEC autorizacao/007 — Definir atribuição: a competência da unidade, e a primeira ação do registro

## 1 · User story
Quem responde pela direção de uma unidade da DIMAP define quais ações a unidade e as de baixo exercem,
na tela de atribuições, para que uma competência nova entre em vigor sem ninguém mexer no banco.

## 2 · Condições de pronto
- [ ] Quem abre a tela é **quem responde pela direção** da unidade — o titular em exercício ou o
      substituto vigente dele —, sem depender de atribuição ou concessão gravada; quem não dirige
      unidade alguma não tem alvo no alcance: a árvore vem vazia e qualquer POST recebe 403.
- [ ] O alvo é escolhido **no organograma**, com cada unidade dirigida na **raiz** e as de baixo
      penduradas nela; a árvore chega **já recortada ao alcance** — unidade fora dele não é desenhada,
      não há como navegar até ela, e é recusada se vier no request.
- [ ] Dirigir uma unidade e outra abaixo dela desenha **um ramo só**, não o ramo comum duas vezes.
- [ ] O catálogo oferecido traz **todas as ações ativas** que a unidade-alvo ainda **não** tem, as
      estruturais inclusive.
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
- [ ] O organograma é **reusado**, não redesenhado: `_no_arvore.html` ganha as flags desta tela e as
      duas telas da SPEC `user_admin/018` continuam renderizando como hoje.

## 3 · Domínio
Nenhum model novo e nenhuma regra nova: a SPEC 002 já entregou as duas tabelas, e esta é o **nível 1**
delas virando ato administrativo. A ação é a primeira do registro a **declarar alcance**, e é o contrato
dela que diz sobre quais unidades pode incidir.

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`Acao`, `AtribuicaoUnidade` e `Concessao`](002-competencia-no-banco.md) — "o que a unidade já exerce,
  o que o catálogo ainda oferece, e quantos cargos caem junto se a atribuição sair?".
- [`has_perm`](003-avaliador-e-backend-de-autorizacao.md) — "este perfil exerce esta ação estrutural?";
  quem lê a direção da unidade é o backend, não esta tela.
- [`UnidadesSubordinadas`](004-protecao-de-rota-e-registro-de-execucao.md) — "até onde o alvo desta
  ação pode chegar?", declarado no contrato dela.
- [`acao_protegida` e `registrar_ato`](004-protecao-de-rota-e-registro-de-execucao.md) — a rota
  protegida, o alvo conferido contra o alcance e o rastro dos dois atos.
- [`alcance_do_perfil`](004-protecao-de-rota-e-registro-de-execucao.md) — "este id de unidade está no
  alcance?"; a resposta é um conjunto de ids, e quem a consome é o decorator.
- [`posicao_de` e `NoHierarquia`](../user_admin/018-arvore-hierarquica.md) — "que forma tem o
  organograma alcançado?"; a tela desenha a árvore, e para desenhar precisa da forma dela, não do
  conjunto de ids que basta ao decorator.
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
  de ids alcançados e as unidades de onde ele parte — é `alcance_do_perfil` que já percorre as
  dirigidas, e esta SPEC a reescreve como projeção da travessia, não faz uma segunda.
- `@apps/user_admin/consulta.py` → `posicao_de`, e `@apps/user_admin/context.py` →
  `contexto_organograma` e `_ramo` (SPEC `user_admin/018`): a subárvore de uma unidade e a travessia que
  casa os ids com as `Unidade` num `in_bulk` e marca cada nó — esta SPEC a **parametriza**, não a
  reescreve; `@services/domain/arvore_hierarquica` → `NoHierarquia`.
- `@templates/user_admin/partials/_no_arvore.html` e `@static/src/js/ui/arvore_hierarquica.js`
  (SPEC `user_admin/018`): o organograma renderizado e o percorrer como estado visual do controle.
- `@services/domain/autorizacao/contratos.py` (SPEC 004) → `UnidadesSubordinadas`: o alcance declarado
  no contrato da ação.
- `@templates/user_admin/servidores_list.html` e `@templates/user_admin/unidade.html`: a área
  administrativa onde o organismo de menu é renderizado.
- SPEC 006 → `.card-acao`, `.card-acao-nome`, `.card-acao-descricao`, `.icone-acao`: o cartão explicativo
  é o item do catálogo, sem redesenho.
- `@static/src/tema-dimap.dev.css` → `.card-well`, `.glass-panel`, `.modal-glass` + `.modal-box-glass`,
  `.btn-onsen`, `.btn-glass`, `.text-overline`, `.dot-unidade`; `.organograma`, `.no-arvore` e
  `.card-unidade` (SPEC `user_admin/018`); `.scroll-etched` sobre `.table-onsen-poco`/`.table-onsen-wrap`
  + `@static/src/js/ui/scroll_etched.js` (SPEC `user_admin/013`), que é como o catálogo rola.
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
    # conferência, e a ação seguinte que precisar de alcance também não a reescreve. O nome do
    # parâmetro que carrega a unidade-alvo já é o default do alcance.
    alcance=UnidadesSubordinadas(),
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

**`apps/competencias/consulta.py`** — a travessia das dirigidas passa a ter **uma origem só**, e o
alcance da SPEC 004 vira projeção dela. Percorrer as dirigidas já era o corpo de `alcance_do_perfil`;
o que faltava era guardar a árvore em vez de jogá-la fora.
```python
def ramos_do_alcance(perfil: Perfil) -> tuple[NoHierarquia, ...]:
    """As subárvores que o perfil alcança — uma por unidade dirigida que não pende de outra dirigida.
    Cobrir o titular de uma subordinada é dirigir duas unidades do mesmo ramo: a de baixo já está
    dentro da de cima, e mantê-la seria percorrer e desenhar duas vezes a parte comum."""
    arvores = {dirigida: posicao_de(dirigida).ego for dirigida in unidades_dirigidas(perfil)}
    return tuple(
        arvore
        for dirigida, arvore in arvores.items()
        if not any(outra != dirigida and dirigida in arvores[outra].ids for outra in arvores)
    )


def alcance_do_perfil(perfil: Perfil) -> frozenset[int]:
    """"Unidades subordinadas" não é conceito, é esta projeção: os ramos alcançados reduzidos a ids.
    Descartar o ramo contido não muda o conjunto — ele já está inteiro dentro do outro."""
    return frozenset().union(*(ramo.ids for ramo in ramos_do_alcance(perfil)))
```

**`apps/user_admin/context.py`** — `contexto_organograma` passa a receber as árvores já percorridas e o
que a tela renderiza; os defaults são o que as duas telas da SPEC `user_admin/018` já fazem.
```python
def contexto_organograma(
    unidade_em_foco: Unidade | None,
    *,
    arvores: Sequence[NoHierarquia] | None = None,
    com_link: bool = True,
    com_irmas: bool = True,
    abrir_o_ego: bool = False,
) -> dict[str, Any]:
    """`arvores` recorta o organograma ao que o chamador alcança; sem elas, a hierarquia inteira.
    Recebe a árvore pronta, e não as raízes, porque quem tem o recorte já a percorreu para saber
    qual é — repetir `posicao_de` aqui seria a terceira varredura da mesma tabela na mesma
    requisição."""
    ramos = arvores if arvores is not None else [
        posicao_de(raiz.pk).ego for raiz in Unidade.objects.filter(pai__isnull=True)
    ]
    ...
    # Ordenar aqui, e não na origem: sigla é da `Unidade`, e é o `in_bulk` desta função que a tem
    # em mãos. `unidades_dirigidas` devolve conjunto — sem isto a árvore trocaria de ordem entre
    # duas aberturas da mesma tela.
    ramos = sorted(ramos, key=lambda ramo: por_id[ramo.unidade_id].sigla)
```

**`templates/user_admin/partials/_no_arvore.html`** — as flags entram como três condições, e nada
mais muda: quem não as passa continua recebendo o organograma da 018.
```html
{# Aberto no ego: esta tela abre mostrando as subordinadas, porque escolher entre elas é o que se  #}
{# faz aqui; a página da unidade abre fechada, no caminho.                                         #}
{% if no.em_foco and abrir_o_ego %}no-arvore-aberto{% endif %}
{# As três flags vêm do contexto, nunca de um default no template: variável ausente é falsa, e as  #}
{# telas da 018, que não as passam, perderiam o elo e a seta em silêncio.                          #}
{% if com_link %}<a class="card-unidade-pagina" ...>{% endif %}
{% if com_irmas %}<button class="no-arvore-irmas" ...>{% endif %}
```

**`apps/competencias/context.py`** — a composição, que é toda a escolha do alvo.
```python
contexto_organograma(
    unidade_alvo,
    arvores=ramos_do_alcance(perfil),
    # Nesta tela o card escolhe o alvo: levar à página da unidade seria sair no meio do ato, e
    # chamar as irmãs não tem o que revelar — a linha do nível já vem aberta.
    com_link=False,
    com_irmas=False,
    abrir_o_ego=True,
)
```

**`apps/competencias/catalogo.py`** — o que o modal oferece.
```python
def acoes_oferecidas(unidade: Unidade) -> QuerySet[Acao]:
    """Ativas e ainda não atribuídas. A estrutural entra como qualquer outra: excluí-la exigiria uma
    lista de slugs privilegiados, que é a configuração em runtime que o §3.5 recusa."""
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
outra pela view, para desenhá-la — e cada uma é agora uma chamada só a `ramos_do_alcance`. Cachear a
segunda exigiria carregar estado entre decorator e view, e o organograma da DIMAP é pequeno. Custo:
`posicao_de` recarrega todos os pares uma vez por unidade dirigida, e dirigir duas é o caso normal de
quem cobre o titular de outra.

**A barreira e a tela leem a mesma travessia em duas formas**: o decorator projeta os ramos num conjunto
de ids, e a tela os desenha como árvore. Uma forma só serviria mal aos dois — o conjunto não desenha
nada, e a árvore não responde pertinência em tempo constante. Custo: nenhum de divergência, porque a
origem passou a ser uma; o que sobra é a projeção do decorator jogar fora a estrutura que a tela usa,
e as duas serem calculadas em momentos diferentes da mesma requisição.

**Quem dirige a raiz alcança o organograma inteiro.** O Secretário é titular da unidade-raiz, e a
subárvore da raiz é tudo — o alcance máximo cai da mesma regra, sem exceção escrita para a alta
administração. Custo: um único perfil concentra a competência de atribuir em qualquer unidade, e o que
o contém é o registro do ato, não uma segunda barreira.

**Autoatribuição é aceita.** Quem dirige a unidade responde pelo que ela faz, inclusive por passar a
exercer uma ação nova. Custo: nada impede que quem dirige amplie a própria competência, e o controle
disso é o registro (SPEC 004), não uma aprovação de terceiro.

**Conceder uma ação estrutural com alcance libera o slug e não o alvo.** A concessão entra pela porta
da SPEC 003 e faz o `has_perm` passar, mas o alcance sai só das unidades dirigidas (SPEC 004): quem
recebe a concessão sem dirigir nada abre a tela com a árvore vazia e não consuma ato nenhum. Custo: o
catálogo oferece uma atribuição cuja concessão, para estas duas ações, não produz efeito — e o que
avisa disso é esta linha, não a interface.

**Esta SPEC mexe em artefato de outras duas, e em nenhuma delas muda o que foi entregue.** Da
`user_admin/018` ela parametriza `contexto_organograma` e põe três flags em `_no_arvore.html`, todas com
o default no comportamento atual; da SPEC 004 ela reescreve `alcance_do_perfil` como projeção de
`ramos_do_alcance`, com a mesma assinatura e o mesmo resultado — refactor, não modelagem nova, e por
isso as duas seguem implementadas. Custo: o snippet de `alcance_do_perfil` no §6 da SPEC 004 passa a
mostrar um corpo que o código não tem mais, e `_no_arvore.html` deixa de ter uma tela só — um ajuste
feito por qualquer das três alcança as outras duas, o mesmo risco que `.card-atribuicao` corre com a
SPEC 008.

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
  gravada, e o substituto dele entra enquanto ele está afastado; quem não dirige unidade alguma recebe
  403. *(marker `banco`)*
- `test_organograma_oferece_so_a_subarvore_dirigida` — a árvore nasce na unidade dirigida, com as de
  baixo penduradas nela; unidade de outro ramo e unidade acima não aparecem, e dirigir uma unidade e
  outra abaixo dela desenha um ramo só. *(marker `banco`)*
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
