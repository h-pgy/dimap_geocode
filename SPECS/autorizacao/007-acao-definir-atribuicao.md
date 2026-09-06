---
spec: autorizacao/007
versao: v13
atualizado_em: 2026-08-21
testes_tdd: true
implementado: true
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
  - v12: as rotas, o DTO do ato e o contrato da remoção passam a ser declarados, o alvo inicial é a
    primeira unidade dirigida por sigla, e a colocação do menu de administrador na área
    administrativa sai de escopo
  - v13: a ordem do alvo inicial e a oferta do catálogo por unidade ganham teste próprio, separados
    dos testes que antes os carregavam de carona
---

# SPEC autorizacao/007 — Definir atribuição: a competência da unidade, e a primeira ação do registro

## 1 · User story
Quem responde pela direção de uma unidade da DIMAP define quais ações a unidade e as de baixo exercem,
na tela de atribuições, para que uma competência nova entre em vigor sem ninguém mexer no banco.

## 2 · Condições de pronto
- [ ] Quem abre a tela é **quem responde pela direção** da unidade — o titular em exercício ou o
      substituto vigente dele —, sem depender de atribuição ou concessão gravada; quem não dirige e
      não recebeu a ação por concessão recebe **403 antes de a tela montar**.
- [ ] Quem tem a ação **por concessão mas não dirige unidade alguma** abre a tela **sem alvo**: a
      árvore vem vazia e qualquer POST recebe 403.
- [ ] O alvo é escolhido **no organograma**, com cada unidade dirigida na **raiz** e as de baixo
      penduradas nela; a tela abre com a **primeira unidade dirigida, por sigla**, já como alvo.
- [ ] A árvore chega **já recortada ao alcance** — unidade fora dele não é desenhada, não há como
      navegar até ela, e é recusada se vier no request.
- [ ] Dirigir uma unidade e outra abaixo dela desenha **um ramo só**, não o ramo comum duas vezes.
- [ ] O catálogo oferecido traz **todas as ações ativas** que a unidade-alvo ainda **não** tem, as
      estruturais inclusive.
- [ ] Atribuir e remover acontecem **sem recarregar a página**, trocando só o trecho afetado.
- [ ] Remover atribuição que tem concessões **exige confirmação** e diz **quantos cargos** perdem a
      competência; **abrir a confirmação não apaga nada**, e o ato confirmado leva as concessões junto.
- [ ] Atribuir e remover são **atos registrados** (SPEC 004), distinguíveis pela operação e com o alvo
      identificando unidade e ação.
- [ ] O design foi aprovado no **mock**, `.card-atribuicao` foi portada para
      `static/src/tema-dimap.dev.css` e renderizada no styleguide antes de qualquer template da
      aplicação usá-la, e o organograma é **reusado**, não redesenhado: `_no_arvore.html` ganha as
      flags desta tela e as duas telas da SPEC `user_admin/018` continuam renderizando como hoje.

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
- [`ItemDeMenu` e `ContratoMenu`](005-contrato-de-menu-e-router.md) — o menu de administrador, que
  **pinça** esta ação; ela não se inscreve nele.

**Mock:** [007-mock-definir-atribuicao.html](007-mock-definir-atribuicao.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Distribuir a atribuição entre os cargos — SPEC 008.
- Onde o menu de administrador aparece na área administrativa: esta SPEC o declara, nenhuma tela o
  renderiza — sem dono ainda.
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
  `_construir_registro`.
- `@apps/competencias/protecao.py` (SPEC 004) → `acao_protegida` e `registrar_ato`.
- `@apps/competencias/menus.py` (SPEC 005) → `ItemDeMenu` e `ContratoMenu`.
- `@apps/competencias/consulta.py` (SPEC 004) → `unidades_dirigidas`.
- `@apps/user_admin/consulta.py` (SPEC `user_admin/018`) → `posicao_de`, e
  `@services/domain/arvore_hierarquica` → `NoHierarquia`.
- `@templates/user_admin/partials/_no_arvore.html` e `@static/src/js/ui/arvore_hierarquica.js`
  (SPEC `user_admin/018`) → o organograma renderizado e o percorrer como estado visual do controle.
- `@templates/competencias/partials/_item_menu.html` e `_icone_acao.html` (SPEC 006) → a linha do menu
  e o átomo do glifo.
- `@services/domain/autorizacao/contratos.py` (SPEC 004) → `UnidadesSubordinadas`.
- `@static/src/tema-dimap.dev.css` → `.card-well`, `.glass-panel`, `.glass-bg`/`.glass-edge`/
  `.glass-shadow`, `.modal-glass` + `.modal-box-glass`, `.btn-onsen`, `.btn-glass`, `.text-overline`,
  `.dot-unidade`; `.card-acao` e `.icone-acao` (SPEC 006); `.organograma`, `.no-arvore` e
  `.card-unidade` (SPEC `user_admin/018`); `.scroll-etched` sobre `.table-onsen-poco`/`.table-onsen-wrap`
  + `@static/src/js/ui/scroll_etched.js` (SPEC `user_admin/013`).
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
    # O item genérico da SPEC 006, não um partial desta ação: a linha do menu é a mesma para todas.
    partial="competencias/partials/_item_menu.html",
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

**`apps/competencias/menus_declarados.py`** — o menu pinça a ação; a ação não se inscreve. Nenhuma tela
o renderiza nesta iteração (§4).
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

**`apps/competencias/urls.py`** — seis rotas, todas protegidas pelo mesmo contrato. O `app_name` fecha
o `url_name` declarado na ação, e o system check da SPEC 001 faz `reverse` dele no boot.
```python
app_name = "competencias"

urlpatterns = [
    # A tela. Sem argumento na URL: o alvo viaja como parâmetro, que é o que o alcance confere.
    path("atribuicoes/", views.definir_atribuicao, name="definir_atribuicao"),
    # Trocar de unidade na árvore troca só o painel — a árvore não é reenviada.
    path("atribuicoes/painel/", views.painel_atribuicoes, name="painel_atribuicoes"),
    path("atribuicoes/catalogo/", views.catalogo, name="catalogo_atribuicao"),
    path("atribuicoes/atribuir/", views.atribuir, name="atribuir"),
    # A confirmação é rota de LEITURA e a remoção é rota de escrita: é essa separação, e não uma
    # flag no formulário, que faz "sem confirmação nada é apagado" ser estrutural.
    path("atribuicoes/remover/confirmar/", views.confirmar_remocao, name="confirmar_remocao"),
    path("atribuicoes/remover/", views.remover, name="remover"),
]
```

**`apps/competencias/comandos.py`** — o DTO do ato, idêntico para atribuir e remover: as duas operações
incidem sobre o mesmo par.
```python
class ComandoAtribuicao(BaseModel):
    """Construído na view, que deixa o `PydanticValidationMiddleware` interceptar o `ValidationError`
    — id não-numérico e slug fora do padrão morrem aqui, antes de virar consulta."""

    model_config = ConfigDict(frozen=True)

    unidade_alvo_id: int
    acao_slug: str = Field(pattern=PADRAO_SLUG)
```

**`apps/competencias/atribuicao.py`** — os dois atos, e a leitura que a confirmação precisa.
```python
def atribuir(comando: ComandoAtribuicao) -> AtribuicaoUnidade:
    """`get_or_create`, não `create`: o duplo clique no cartão do catálogo não pode virar
    `IntegrityError` na tela — a unicidade quem garante é a constraint da SPEC 002."""
    atribuicao, _ = AtribuicaoUnidade.objects.get_or_create(
        unidade_id=comando.unidade_alvo_id,
        acao=Acao.objects.get(slug=comando.acao_slug),
    )
    return atribuicao


def remover(comando: ComandoAtribuicao) -> None:
    """Uma exclusão só: as concessões caem pelo CASCADE da FK (SPEC 002). Varrer e apagar aqui
    duplicaria em Python a regra que já é do schema."""
    AtribuicaoUnidade.objects.filter(
        unidade_id=comando.unidade_alvo_id,
        acao__slug=comando.acao_slug,
    ).delete()


def cargos_que_perdem(comando: ComandoAtribuicao) -> list[str]:
    """Os nomes que a confirmação mostra. Lidos no momento em que o modal é montado (Caveats)."""
    ...
```

**`apps/competencias/views.py`** — a view chega com competência e alvo já conferidos; nenhuma delas
repete a conferência.
```python
@acao_protegida(ACAO_DEFINIR_ATRIBUICAO)
def definir_atribuicao(request: HttpRequest) -> HttpResponse:
    # Nenhuma conferência de alcance escrita aqui: o POST forjado com unidade de outro ramo já foi
    # recusado pelo decorator, que leu o alcance do contrato da ação.
    return render(request, "competencias/definir_atribuicao.html", contexto_da_tela(request.user))


@acao_protegida(ACAO_DEFINIR_ATRIBUICAO)
@require_POST
def atribuir(request: HttpRequest) -> HttpResponse:
    comando = ComandoAtribuicao(
        unidade_alvo_id=request.POST["unidade"],
        acao_slug=request.POST["acao"],
    )
    atribuicao = atribuir_acao(comando)
    # A view NUNCA grava a execução: deixa o recado e quem persiste é o decorator, depois do return.
    registrar_ato(
        request,
        operacao="atribuir",
        alvo_tipo="unidade_acao",
        alvo_identificador=f"{atribuicao.unidade.sigla}:{atribuicao.acao.slug}",
    )
    return render(request, "competencias/partials/_poco_atribuicoes.html", ...)


@acao_protegida(ACAO_DEFINIR_ATRIBUICAO)
def confirmar_remocao(request: HttpRequest) -> HttpResponse:
    """GET: monta o modal com a contagem real. Não apaga — e é por não existir aqui nenhuma escrita
    que a confirmação é obrigatória, sem flag nenhuma no formulário."""
    ...
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
    return frozenset[int]().union(*(ramo.ids for ramo in ramos_do_alcance(perfil)))
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
    qual é."""
    ramos = list(arvores) if arvores is not None else [
        posicao_de(raiz.pk).ego for raiz in Unidade.objects.filter(pai__isnull=True)
    ]
    por_id = Unidade.objects.in_bulk(
        frozenset(unidade_id for ramo in ramos for unidade_id in ramo.ids)
    )
    caminho = frozenset(posicao_de(unidade_em_foco.pk).acima) if unidade_em_foco else frozenset()
    # Ordenar aqui, e não na origem: sigla é da `Unidade`, e é o `in_bulk` desta função que a tem
    # em mãos. `unidades_dirigidas` devolve conjunto — sem isto a árvore trocaria de ordem entre
    # duas aberturas da mesma tela.
    ramos = sorted(ramos, key=lambda ramo: por_id[ramo.unidade_id].sigla)
    return {
        "ramos": [_ramo(ramo, por_id, caminho, unidade_em_foco) for ramo in ramos],
        "unidade_em_foco": unidade_em_foco,
        # As três SEMPRE no contexto, mesmo no default: variável ausente é falsa no template, e as
        # telas da 018 perderiam o elo e a seta em silêncio.
        "com_link": com_link,
        "com_irmas": com_irmas,
        "abrir_o_ego": abrir_o_ego,
    }
```

**`templates/user_admin/partials/_no_arvore.html`** — as flags entram como três condições, e nada
mais muda: quem não as passa continua recebendo o organograma da 018.
```html
{# Aberto no ego: esta tela abre mostrando as subordinadas, porque escolher entre elas é o que se  #}
{# faz aqui; a página da unidade abre fechada, no caminho.                                         #}
{% if no.em_foco and abrir_o_ego %}no-arvore-aberto{% endif %}
{% if com_link %}<a class="card-unidade-pagina" ...>{% endif %}
{% if com_irmas %}<button class="no-arvore-irmas" ...>{% endif %}
```

**`apps/competencias/context.py`** — a composição, que é toda a escolha do alvo.
```python
def contexto_da_tela(perfil: Perfil, unidade_alvo: Unidade | None = None) -> dict[str, Any]:
    ramos = ramos_do_alcance(perfil)
    # O alvo inicial sai dos PRÓPRIOS ramos do perfil: por construção está dentro do alcance, e é
    # isso que o dispensa da conferência do decorator, que num GET sem parâmetro não roda.
    alvo = unidade_alvo or _primeira_dirigida(ramos)
    return contexto_organograma(
        alvo,
        arvores=ramos,
        # Nesta tela o card escolhe o alvo: levar à página da unidade seria sair no meio do ato, e
        # chamar as irmãs não tem o que revelar — a linha do nível já vem aberta.
        com_link=False,
        com_irmas=False,
        abrir_o_ego=True,
    ) | {"unidade_alvo": alvo, "atribuicoes": _atribuicoes_de(alvo)}


def _primeira_dirigida(ramos: Sequence[NoHierarquia]) -> Unidade | None:
    """Por sigla, e não pela ordem do conjunto: `unidades_dirigidas` não tem ordem, e a tela abriria
    numa unidade diferente a cada requisição. `None` é o perfil que tem a ação por concessão e não
    dirige nada — árvore vazia, e nada a atribuir."""
    return (
        Unidade.objects.filter(pk__in=[ramo.unidade_id for ramo in ramos]).order_by("sigla").first()
    )
```

**`apps/competencias/catalogo.py`** — o que o modal oferece.
```python
def acoes_oferecidas(unidade: Unidade) -> QuerySet[Acao]:
    """Ativas e ainda não atribuídas. A estrutural entra como qualquer outra: excluí-la exigiria uma
    lista de slugs privilegiados, que é a configuração em runtime que o §3.5 recusa."""
    return Acao.objects.exclude(atribuicoes__unidade=unidade).filter(ativa=True)
```

**`templates/competencias/partials/_card_acao_catalogo.html`** — o cartão do catálogo compõe as mesmas
classes do `.card-acao` da SPEC 006, mudando só o gatilho: ali o cartão **navega** para a ação, aqui
ele **atribui** a ação à unidade.
```html
{# O clicável continua sendo o elemento de fora: o .hover-3d exige conteúdo não-interativo nos 9  #}
{# filhos diretos, e é por isso que o gatilho não pode ser um botão dentro do cartão.             #}
<button class="hover-3d card-acao-alvo"
        hx-post="{% url 'competencias:atribuir' %}"
        hx-vals='{"unidade": "{{ unidade_alvo.pk }}", "acao": "{{ acao.slug }}"}'
        hx-target="#poco-atribuicoes">
  <div class="glass-bg glass-edge glass-shadow card-acao"> ... </div>
  ...
</button>
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

**A barreira e a tela leem a mesma travessia em duas formas, e nenhuma das duas é cacheada**: o
decorator projeta os ramos num conjunto de ids, a tela os desenha como árvore, e uma forma só serviria
mal aos dois — o conjunto não desenha nada, e a árvore não responde pertinência em tempo constante.
Carregar estado entre decorator e view para reaproveitar exigiria um atributo no request, e o
organograma da DIMAP é pequeno. Custo: `posicao_de` relê a tabela inteira uma vez por unidade dirigida
em cada uma das duas chamadas a `ramos_do_alcance`, mais uma vez para o caminho do ego — cinco leituras
por abertura de tela para quem dirige duas unidades, que é o caso normal de quem cobre outro titular.

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

**O `MENU_ADMINISTRADOR` é declarado e nenhuma tela o renderiza.** Declará-lo junto da ação mantém a
competência administrativa versionada em code review, que é a razão do §3.5; onde ele aparece é decisão
de interface que o mock desta SPEC não responde (§4). Custo: o contrato fica sem consumidor até a SPEC
que o colocar em tela, e a única porta da tela é a URL direta.

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
  gravada, e o substituto dele entra enquanto ele está afastado; quem não dirige e não tem concessão
  recebe 403. *(marker `banco`)*
- `test_concessao_sem_direcao_abre_a_tela_sem_alvo` — quem tem a ação por concessão mas não dirige
  unidade alguma abre a tela com a árvore vazia, e o POST com qualquer unidade recebe 403.
  *(marker `banco`)*
- `test_organograma_oferece_so_a_subarvore_dirigida` — a árvore nasce na unidade dirigida, com as de
  baixo penduradas nela; unidade de outro ramo e unidade acima não aparecem, não há elo nem chamado
  das irmãs, e dirigir uma unidade e outra abaixo dela desenha um ramo só. *(marker `banco`)*
- `test_tela_abre_na_primeira_dirigida_por_sigla` — com duas dirigidas sem parentesco, o ego inicial
  é a de menor sigla, e não a que o conjunto devolver primeiro. *(marker `banco`)*
- `test_organograma_da_018_segue_com_elo_e_botao_de_irmas` — a página da unidade, que não passa flag
  alguma, continua renderizando o elo para a página e o chamado das irmãs. *(marker `banco`)*
- `test_catalogo_oferece_so_o_que_falta` — a ação já atribuída e a inativa ficam fora da oferta; a
  estrutural que a unidade ainda não tem é oferecida. *(marker `banco`)*
- `test_atribuicao_de_outra_unidade_nao_tira_a_acao_da_oferta` — a oferta é por unidade: o que a
  vizinha exerce continua disponível aqui. *(marker `banco`)*
- `test_atribuir_recusa_unidade_fora_do_alcance` — POST com unidade existente mas de outro ramo é
  recusado mesmo com id válido, sem a view conferir nada: é a declaração do contrato chegando à rota.
  *(marker `banco`)*
- `test_remover_so_apaga_no_post_confirmado` — abrir a confirmação traz a contagem de cargos e não
  apaga nada; o POST apaga a atribuição e as concessões dependentes juntas. *(marker `banco`)*
- `test_atribuir_e_remover_ficam_registrados_com_alvo` — as duas operações geram execução registrada
  distinguível pela operação, identificando unidade e ação. *(marker `banco`)*
