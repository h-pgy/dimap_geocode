---
spec: user_admin/029
versao: v1
atualizado_em: 2026-09-04
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC user_admin/029 — Cargos em comissão como ato administrativo

## 1 · User story
O administrador do sistema cria, edita, extingue e reativa cargos em comissão no catálogo da DIMAP
para que a estrutura de cargos acompanhe as alterações do quadro sem que ninguém seja nomeado num
cargo em extinção.

## 2 · Condições de pronto
- [ ] **Qualquer servidor autenticado** abre a lista de cargos em comissão na tabela-onsen, com
      filtros, o toggle **Mostrar cargos extintos** e, por linha, o lápis e a lixeira — que abrem os
      modais de editar e de extinguir **já com o cargo da linha escolhido**; os mesmos modais,
      abertos pelos cards do painel, vêm sem cargo escolhido.
- [ ] Criar, editar, extinguir e reativar são **exclusivos do administrador do sistema**: para os
      demais os cards não aparecem, e as rotas recusam mesmo com concessão gravada.
- [ ] Cargo **com ocupante no quadro** tem **nível, natureza e alta administração travados**, com o
      tooltip dizendo quantos o ocupam e que é preciso exonerá-los antes; **nome e sigla** seguem
      editáveis, inclusive em cargo extinto.
- [ ] Extinguir **data** o cargo e o tira das opções de nomeação do cadastro e da edição de servidor
      — **menos para quem já o ocupa**, que continua vendo o seu marcado e selecionado.
- [ ] Cargo extinto **continua sendo avaliado normalmente**: quem o ocupa segue exercendo as
      competências dele, titularizando unidade e podendo receber concessão nova.
- [ ] Em toda tela em que um cargo aparece, o extinto vem com **o mesmo rótulo** (`padrão · nome`)
      **em tom de warning e o tooltip "Cargo Extinto"** — nenhum texto a mais; reativar devolve o
      cargo à nomeação e retira a cor e o tooltip.
- [ ] Os quatro atos ficam **registrados** com a operação (`criar`, `editar`, `extinguir`,
      `reativar`), `alvo_tipo="cargo_comissao"` e o **nome do cargo**.
- [ ] O painel ganha a aba **Administração do Sistema**, por último, com **Tornar administrador** —
      que sai de *Atribuições* — e os quatro cards de cargo; a **lista** entra no grupo "Cargos em
      Comissão" que já existe vazio na aba *Estrutura Administrativa*.
- [ ] O design foi aprovado no mock, e as peças novas foram portadas para o tema e o styleguide
      antes de qualquer template da aplicação usá-las.

## 3 · Domínio

O cargo em comissão ganha a data que o retira da nomeação sem o apagar de nada: o cargo **entra em
extinção** e continua vivo enquanto tiver ocupante.

**`apps/cargos/models/cargos.py`** — o app é o da SPEC user_admin/028.

```python
class CargoComissao(models.Model):
    # ALTERADO nesta SPEC: ganha `extinto_em`. Os demais campos, o `clean()`, as duas
    # CheckConstraint de alta_administracao × nivel × e_chefia e as propriedades `natureza` e
    # `padrao` seguem como estão.
    sigla = models.CharField(max_length=20)
    nivel = models.PositiveSmallIntegerField(null=True, blank=True, validators=[...])
    e_chefia = models.BooleanField()
    alta_administracao = models.BooleanField(default=False)
    nome = models.CharField(max_length=200, unique=True)
    # NOVO: o dia do ato que o retirou da nomeação. Nula é cargo vigente, e é o que a reativação
    # devolve — mesma forma de `Unidade.extinta_em` e `Perfil.exonerado_em`.
    extinto_em = models.DateField(null=True, blank=True)

    @property
    def extinto(self) -> bool:
        return self.extinto_em is not None
```

`CargoComissao.objects` **continua devolvendo os extintos** — diferente de `Unidade`, que os esconde
no gerente padrão: aqui o extinto segue ofertado em quase todo lugar, e quem filtra é a nomeação
(§7).

**`services/domain/cargos/models.py`** — o domínio não conhece o model; do cargo só precisa disto.

```python
class IdentidadeCargo(BaseModel):
    model_config = ConfigDict(frozen=True)

    cargo_id: int
    nome: str
    padrao: str


class PreviaDaEdicao(BaseModel):
    model_config = ConfigDict(frozen=True)

    cargo: IdentidadeCargo
    # Servidores no quadro que ocupam o cargo — exonerado não ocupa mais e não trava nada.
    ocupantes: int


class TravasDaEdicao(BaseModel):
    """O que a edição não pode tocar, e o texto que explica por quê."""

    model_config = ConfigDict(frozen=True)

    natureza_travada: bool
    motivo: str = ""


class PreviaDaExtincaoCargo(BaseModel):
    model_config = ConfigDict(frozen=True)

    cargo: IdentidadeCargo
    # Extinguir cargo ocupado é o cenário normal: a contagem é o que o modal informa, não uma
    # condição de passagem.
    ocupantes: int
    ja_extinto: bool = False


class PreviaDaReativacaoCargo(BaseModel):
    model_config = ConfigDict(frozen=True)

    cargo: IdentidadeCargo
    ja_vigente: bool = False


class Veredito(BaseModel):
    model_config = ConfigDict(frozen=True)

    pode: bool
    motivo: str = ""
```

Consumido de SPECs anteriores, sem recópia:

- [`Acao` e `AcaoImplementada`](../autorizacao/001-catalogo-de-acoes-em-codigo.md) e a
  [proteção de rota com registro](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md) —
  esta SPEC pergunta a eles como quatro atos sem alcance e exclusivos do superusuário se inscrevem e
  se registram.
- [`ContratoPainel`, `Aba`, `Grupo`, `ItemAcao`, `ItemLivre`](../painel/001-painel-de-acoes-por-abas.md)
  — esta SPEC pergunta onde os cinco itens novos entram e o que a aba nova declara.
- [`RequisitoTitularidade`](014-titular-da-unidade.md) — esta SPEC pergunta o que acontece com a
  titularidade quando o cargo que a sustenta entra em extinção: **nada**, o cargo segue avaliado.

**Mock:** [029-mock-cargos-em-comissao.html](029-mock-cargos-em-comissao.html) — leia a skill `mock`.

## 4 · Fora de escopo
- `extinto_em` em `CargoBase` e os atos que o mantêm — SPEC própria do épico `user_admin`.
- Revalidação das titularidades vigentes quando o cargo muda de nível ou natureza — sem dono ainda.
- Histórico de alterações do cargo além do registro de execução — sem dono ainda.
- Página própria do cargo, com os servidores que já o ocuparam — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/cargos` → o app do catálogo, entregue pela SPEC user_admin/028: os models, a seed e o
  comando já moram lá.
- `@apps/unidades/extincao.py` → `extinguir_unidade`/`reativar_unidade`: forma do ato reversível com
  prévia, veredito e desfecho.
- `@services/domain/extincao_unidade` → `Veredito` e as prévias: mesma forma, outro domínio.
- `@templates/unidades/partials/_tabela_unidades.html`, `_corpo_unidades.html`,
  `_barra_acoes_unidades.html` → tabela-onsen com coluna do lápis, coluna da lixeira, toggle de
  extintas e barra de ações.
- `@templates/user_admin/partials/_modal_editar_perfil.html` → `campo-onsen-lapis`: o campo em
  leitura que o lápis abre para edição.
- `@static/src/js/ui/select_onsen.js` → o aprimorador que desenha os itens a partir dos `<option>` e
  já copia o realce que o servidor marcou.
- `@apps/competencias/utils.py` → `instanciar_acao`: nunca construir `Acao`/`AcaoImplementada` na mão.
- `@apps/competencias/protecao.py` → `acao_protegida`, `registrar_ato`.
- `@apps/user_admin/context.py` → `_catalogos_de_lotacao`: ponto único que monta os selects de cargo
  do cadastro e da edição de servidor.
- Skills: `acao-administrativa`, `painel`, `componentes-frontend`, `mock`, `ontologia`,
  `escrever-testes`.

## 6 · Snippets

**`apps/cargos/acoes_declaradas.py`**

```python
# Quatro ações para um catálogo só: é a `operacao` do registro que precisa distinguir os atos, e
# quatro contratos é o que dá a cada um card, ícone e rastro próprios (custo em §7).
ACAO_CRIAR_CARGO = instanciar_acao(
    slug="cargos.criar_cargo_comissao",
    nome="Cadastrar cargo em comissão",
    nome_curto="Novo cargo",
    tooltip="Cria um cargo em comissão no catálogo da DIMAP.",
    url_name="cargos:modal_criar_cargo",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    # Mesmo regime de "criar unidade raiz" e "tornar administrador": dirigir unidade não dá esta
    # caneta, e conceder também não.
    estrutural=False,
    exclusiva_superusuario=True,
    # O catálogo é global: não incide sobre unidade alguma, e não há alvo a conferir.
    alcance=None,
)
# ACAO_EDITAR_CARGO, ACAO_EXTINGUIR_CARGO e ACAO_REATIVAR_CARGO seguem o mesmo molde, com
# `url_name` nas rotas diretas (`modal_editar_cargo`, `modal_extinguir_cargo`,
# `modal_reativar_cargo`) — as de gravação recebem o cargo no caminho e não revertem sem argumento
# (`competencias.E004`).
```

**`services/domain/cargos/avaliador.py`** — as três regras do ato, sem Django.

```python
class AvaliadorEdicao:
    """O que a edição pode tocar. Natureza é nível + chefia + alta administração: mudá-la sob um
    ocupante mudaria, sem ato nenhum, a competência que ele exerce e a unidade que ele titulariza."""

    def __call__(self, previa: PreviaDaEdicao) -> TravasDaEdicao:
        if previa.ocupantes == 0:
            return TravasDaEdicao(natureza_travada=False)
        return TravasDaEdicao(
            natureza_travada=True,
            motivo=(
                f"{previa.ocupantes} servidor(es) ocupam este cargo. Exonere-os antes de alterar "
                "nível, natureza ou alta administração."
            ),
        )


class AvaliadorExtincaoCargo:
    def __call__(self, previa: PreviaDaExtincaoCargo) -> Veredito:
        # Ocupante não impede: o cargo entra em extinção e vai esvaziando conforme as exonerações.
        if previa.ja_extinto:
            return Veredito(pode=False, motivo="Este cargo já está extinto.")
        return Veredito(pode=True)


class AvaliadorReativacaoCargo:
    def __call__(self, previa: PreviaDaReativacaoCargo) -> Veredito:
        if previa.ja_vigente:
            return Veredito(pode=False, motivo="Este cargo não está extinto.")
        return Veredito(pode=True)
```

**`apps/cargos/consulta.py`** — a regra de quem pode ser nomeado, num lugar só.

```python
def cargos_nomeaveis(cargo_atual_id: int | None = None) -> QuerySet[CargoComissao]:
    """Os cargos que uma nomeação pode escolher: os vigentes, mais o que o servidor JÁ ocupa.

    Sem a segunda metade, abrir a edição de quem ocupa cargo extinto para trocar o e-mail gravaria
    o cargo vazio — a tela apagaria a nomeação sem ninguém pedir.
    """
    nomeaveis = Q(extinto_em__isnull=True)
    if cargo_atual_id is not None:
        nomeaveis |= Q(pk=cargo_atual_id)
    return CargoComissao.objects.filter(nomeaveis).order_by("nome")


def ocupantes_no_quadro(cargo: CargoComissao) -> int:
    # Exonerado não ocupa mais: quem trava a edição é quem está no quadro hoje.
    return cargo.perfis.filter(is_active=True, exonerado_em__isnull=True).count()
```

**`apps/cargos/cadastro.py`** — a trava conferida no servidor, não na tela.

```python
def editar_cargo(cargo: CargoComissao, valores: Mapping[str, Any]) -> DesfechoCargo:
    leitura = ler_cargo_comissao(valores)
    if leitura.dto is None:
        return DesfechoCargo(cargo=None, recusa=leitura.recusa or RecusaDeFormulario())
    travas = avaliar_edicao(
        PreviaDaEdicao(cargo=_identidade(cargo), ocupantes=ocupantes_no_quadro(cargo))
    )
    # `disabled` não chega ao servidor, e requisição forjada não vê tela nenhuma: a trava vale aqui,
    # comparando o que veio com o que está gravado.
    if travas.natureza_travada and _natureza_mudou(cargo, leitura.dto):
        return DesfechoCargo(cargo=None, recusa=recusa_de_natureza(travas.motivo))
    cargo.nome = leitura.dto.nome
    cargo.sigla = leitura.dto.sigla
    if not travas.natureza_travada:
        cargo.nivel = leitura.dto.nivel
        cargo.e_chefia = leitura.dto.e_chefia
        cargo.alta_administracao = leitura.dto.alta_administracao
    try:
        with transaction.atomic():
            # A consistência alta_administracao × nivel × e_chefia é do model e não se reescreve aqui.
            cargo.full_clean()
            cargo.save()
    except ValidationError as recusa:
        return DesfechoCargo(cargo=None, recusa=traduzir_recusa(de_validation_error(recusa)))
    return DesfechoCargo(cargo=cargo)
```

**`apps/cargos/extincao.py`**

```python
def extinguir_cargo(cargo: CargoComissao, hoje: date) -> DesfechoCargo:
    veredito = avaliar_extincao_cargo(previa_da_extincao(cargo))
    if not veredito.pode:
        return DesfechoCargo(cargo=None, recusa=recusa_do_veredito(veredito.motivo))
    # Uma coluna e nada mais: extinguir NÃO mexe em perfil, titularidade, concessão nem delegação —
    # o cargo continua sendo avaliado, e é isso que o distingue da extinção de unidade.
    cargo.extinto_em = hoje
    cargo.save(update_fields=["extinto_em"])
    return DesfechoCargo(cargo=cargo)
```

**`apps/cargos/views.py`** — o molde das quatro gravações.

```python
@acao_protegida(ACAO_EXTINGUIR_CARGO)
@require_POST
def gravar_extincao(request: HttpRequest, cargo: int) -> HttpResponse:
    alvo = get_object_or_404(CargoComissao, pk=cargo)
    desfecho = extincao.extinguir_cargo(alvo, timezone.localdate())
    if desfecho.cargo is None:
        return render(request, TEMPLATE_MODAL, contexto_recusa(alvo, desfecho.recusa))
    # O nome DEPOIS do ato: numa edição que renomeia, é o nome novo que fica no rastro (§7).
    registrar_ato(
        request,
        operacao="extinguir",
        alvo_tipo="cargo_comissao",
        alvo_identificador=desfecho.cargo.nome,
    )
    return render(request, TEMPLATE_CONCLUIDO, contexto_concluido(desfecho.cargo))
```

**`apps/user_admin/context.py`** — o único ponto que oferta cargo para nomeação.

```python
def _catalogos_de_lotacao(
    ids_permitidos: Collection[int] | None = None,
    cargo_comissao_atual: int | None = None,
) -> dict[str, Any]:
    return catalogo_de_unidades(ids_permitidos) | {
        "cargos_base": CargoBase.objects.order_by("nome"),
        # Cadastro passa `None` (ninguém ocupa nada ainda); edição passa o cargo gravado.
        "cargos_comissao": cargos_nomeaveis(cargo_comissao_atual),
    }
```

**`templates/cargos/partials/_rotulo_cargo.html`** — a marca, num lugar só.

```django
{# O rótulo de sempre. Extinto NÃO ganha texto nenhum: é o MESMO `padrão · nome`, em tom de #}
{# warning, e o aviso vive no tooltip. #}
<span class="rotulo-cargo{% if cargo.extinto %} rotulo-cargo-extinto{% endif %}"
      {% if cargo.extinto %}title="Cargo Extinto"{% endif %}>{{ cargo.padrao }} · {{ cargo.nome }}</span>
```

Dentro de um `<select>` o rótulo é o mesmo, e o marcador desce por atributo — é o `select_onsen.js`
que o leva ao item que ele desenha:

```django
<option value="{{ cargo.pk }}"{% if cargo.extinto %} data-extinto="true" title="Cargo Extinto"{% endif %}>{{ cargo.padrao }} · {{ cargo.nome }}</option>
```

```javascript
// montarOpcoes: uma linha ao lado do textContent, mesma natureza do realce que o trigger já herda.
if (opcao.dataset.extinto) item.dataset.extinto = "true";
```

**`apps/painel/abas_declaradas.py`**

```python
ABA_ADMINISTRACAO = Aba(
    slug="painel.administracao_sistema",
    rotulo="Administração do Sistema",
    titulo="Administração do Sistema",
    descricao=(
        "Os atos que não decorrem de dirigir unidade alguma: quem tem plenos poderes sobre o "
        "sistema e o catálogo de cargos em comissão sobre o qual toda nomeação se apoia."
    ),
    grupos=(
        # Sai de ABA_ATRIBUICOES, onde o grupo se chamava "Administração do Sistema" — o nome agora
        # é o da aba, e o grupo passa a nomear o que reúne.
        Grupo(
            rotulo="Administradores",
            itens=(ItemAcao(acao=ACAO_TORNAR_ADMINISTRADOR, partial=PARTIAL_CARTAO_MODAL),),
        ),
        Grupo(
            rotulo="Cargos em Comissão",
            itens=(
                ItemAcao(acao=ACAO_CRIAR_CARGO, partial=PARTIAL_CARTAO_MODAL),
                ItemAcao(acao=ACAO_EDITAR_CARGO, partial=PARTIAL_CARTAO_MODAL),
                ItemAcao(acao=ACAO_EXTINGUIR_CARGO, partial=PARTIAL_CARTAO_MODAL),
                ItemAcao(acao=ACAO_REATIVAR_CARGO, partial=PARTIAL_CARTAO_MODAL),
            ),
        ),
    ),
)

# O grupo que nasceu vazio na aba da estrutura recebe a listagem — que é leitura aberta e, por
# isso, não cabe numa aba que só o administrador enxerga.
Grupo(
    rotulo="Cargos em Comissão",
    itens=(
        ItemLivre(
            slug="painel.lista_cargos",
            nome="Cargos em comissão",
            tooltip="O catálogo de cargos da DIMAP, com nível, natureza e quem os ocupa.",
            url_name="cargos:listar_cargos",
        ),
    ),
)

PAINEL = ContratoPainel(
    abas=(ABA_MINHA_CONTA, ABA_RECURSOS_HUMANOS, ABA_ESTRUTURA, ABA_ATRIBUICOES, ABA_ADMINISTRACAO),
)
```

## 7 · Caveats

**A trava de natureza vive em `services/` e na view, não no banco.** Nível, chefia e alta
administração de cargo ocupado só são recusados pelo caminho do ato; um `UPDATE` direto na tabela
muda a natureza sob o ocupante sem que nada reclame. O custo é uma invariante que depende do
caminho — as `CheckConstraint` do model seguem garantindo só a consistência interna do cargo.

**Extinguir cargo não revalida nada.** O cargo entra em extinção e continua titularizando unidade,
exercendo a competência de quem o ocupa e podendo receber concessão nova — é o que faz a extinção
ser barata e o que a distingue da extinção de unidade. O custo é o organograma poder ficar dirigido
por titular cujo cargo já está em extinção, visível só pela marca.

**`CargoComissao.objects` continua trazendo os extintos**, ao contrário de `Unidade`, cujo gerente
padrão os esconde. O extinto segue ofertado em quase toda tela, e o único ponto que filtra é
`cargos_nomeaveis`. O custo é que um ponto novo de nomeação que esqueça o filtro não quebra nada
visível — nomeia em cargo extinto em silêncio.

**`select_onsen.js` ganha mais uma coisa a carregar.** A marca do cargo é cor, não texto, e dentro de
um select ela só chega ao item desenhado se o utilitário copiar o marcador do `<option>` — que é o
mesmo caminho pelo qual ele já leva o `campo-realce-` do `<select>` ao gatilho. O custo é que, com o
JS desligado, o `<option>` nativo fica sem a cor e sobra só o `title`.

**O rastro da edição guarda o nome depois do ato.** Renomear um cargo grava o nome novo no
`alvo_identificador`, e o nome anterior não fica em lugar nenhum do registro. Ler o histórico de um
cargo renomeado exige juntar as linhas pelo que sobrou em comum.

**Renomear pela tela briga com a seed.** `seed_cargos` usa o `nome` como chave natural e só cria o
que falta, então um cargo renomeado pela tela é **recriado** com o nome antigo na próxima carga.
Aceito enquanto a seed for bootstrap; conciliar as duas fontes é problema de outra SPEC.

**Quatro ações para um catálogo só.** Como as quatro são exclusivas do superusuário, a separação não
compra granularidade de concessão nenhuma — ela existe só para o rastro distinguir os atos. O custo
são quatro pastas de ícone, quatro cards e quatro linhas no registro para o que poderia ser uma ação
com quatro operações.

**`ACAO_TORNAR_ADMINISTRADOR` muda de aba.** Nenhum dado muda e a competência é a mesma, mas quem já
sabia onde o card estava precisa reaprender.

## 8 · Testes (TDD)

**Comportamento**

- `test_extinguir_data_o_cargo_e_o_tira_da_nomeacao` — depois do ato, `extinto_em` está preenchido e
  `cargos_nomeaveis()` não devolve o cargo. *(marker `banco`)*
- `test_cargo_extinto_segue_ofertado_a_quem_ja_o_ocupa` — `cargos_nomeaveis(cargo_atual_id=...)`
  devolve o extinto do próprio servidor, e só ele. *(marker `banco`)*
- `test_reativar_devolve_o_cargo_a_nomeacao` — `extinto_em` volta a ser nulo e o cargo reaparece na
  oferta. *(marker `banco`)*
- `test_cargo_extinto_continua_exercendo_competencia` — perfil com cargo extinto e concessão gravada
  segue com `has_perm` verdadeiro. *(marker `banco`)*
- `test_edicao_recusa_natureza_de_cargo_ocupado` — POST que muda `nivel`/`e_chefia`/
  `alta_administracao` de cargo com ocupante é recusado e nada é gravado. *(marker `banco`)*
- `test_edicao_altera_nome_e_sigla_de_cargo_ocupado_e_extinto` — a mesma tela grava nome e sigla,
  ocupado ou extinto. *(marker `banco`)*
- `test_edicao_livre_quando_ninguem_ocupa` — sem ocupante, nível e natureza mudam. *(marker `banco`)*
- `test_veredito_recusa_ato_repetido` — extinguir o já extinto e reativar o vigente são recusados
  com motivo; domínio puro, sem banco.
- `test_listagem_esconde_extintos_sem_o_toggle` — a tabela só traz extintos com o toggle ligado.
  *(marker `banco`)*
- `test_listagem_aberta_a_qualquer_autenticado` — servidor sem caneta alguma recebe 200 na lista, e
  ela não traz os gestos de ato. *(marker `banco`)*

**Segurança da ação** (skill `acao-administrativa`; fora do teto)

- `test_anonimo_vai_ao_login_sem_registrar` — as quatro rotas redirecionam e não deixam linha.
  *(marker `banco`)*
- `test_autenticado_sem_competencia_recebe_403_e_fica_registrado` — a negativa aparece no histórico.
  *(marker `banco`)*
- `test_concessao_gravada_nao_abre_acao_exclusiva_de_superusuario` — nem concessão nem direção de
  unidade liberam os quatro atos. *(marker `banco`)*
- `test_ato_grava_quem_cargo_unidade_operacao_e_alvo` — a linha registra a lotação do momento e o
  nome do cargo alvo. *(marker `banco`)*
- `test_extinguir_e_reativar_ficam_distinguiveis_no_registro` — as operações opostas não se
  confundem no rastro. *(marker `banco`)*
- `test_gravacao_so_por_post` — as rotas de gravação recusam GET, e abrir o modal não pratica ato.
  *(marker `banco`)*
