---
spec: user_admin/020
versao: v2
atualizado_em: 2026-08-23
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: editar a cor entra no escopo — o disco de paleta vira partial próprio, o modal de edição o
    compõe dentro do campo-onsen e a cor passa a ser enum no DTO
  - v3: criar unidade raiz vira ação própria, exclusiva do superusuário, com regime novo no contrato
    (`exclusiva_superusuario`); tornar raiz deixa de existir na edição
---

# SPEC user_admin/020 — Os três atos que mantêm o organograma

## 1 · User story
Quem responde pela direção de uma unidade da DIMAP cria unidades abaixo da sua e corrige o cadastro
da sua e das que estão abaixo dela, na tela de cadastro e na página da unidade, para que o
organograma que define a competência administrativa seja mantido por quem responde por ele, sem
passar pelo admin do Django. E quem administra o sistema **cria a raiz** de um organograma — a
unidade que não responde a ninguém —, num ato à parte, que só ele pratica.

## 2 · Condições de pronto
- [ ] **Criar unidade** e **editar unidade** são ações **estruturais** inscritas no catálogo, com as
      rotas de abertura e de gravação protegidas: quem responde pela direção as exerce sem concessão
      gravada, e quem não dirige unidade alguma recebe **403**.
- [ ] Cada ato incide sobre a unidade que o alcance declara: **criar**, sobre a **unidade superior
      escolhida** — pai fora do alcance é recusado com 403 antes de a view rodar, e gravação sem o
      campo é **400**; **editar**, sobre a **unidade editada** — abrir ou gravar unidade fora do
      alcance é recusado com 403 e fica registrado, e o **botão de editar** só aparece a quem tem a
      competência **e** o alcance sobre ela.
- [ ] O **superusuário alcança todo o organograma**, dirigindo unidade ou não: nenhuma conferência
      de alvo o barra e todos os selects lhe oferecem todas as unidades.
- [ ] **Criar unidade raiz** é **ação própria**, com rota e registro próprios, e **exclusiva do
      superusuário**: quem não é recebe **403 registrado** e não a vê em tela alguma — **nem com a
      concessão gravada**, porque a exclusividade não se concede. A tela é a de criar unidade, com o
      campo de unidade superior **gravado**, sem afordância de gesto, e um aviso dizendo que a raiz
      não responde a ninguém.
- [ ] **Nenhuma tela torna raiz** uma unidade que tem superior — nem para o superusuário: raiz é quem
      **nasce** raiz. "Sem unidade superior" só aparece onde já é o estado da unidade: no select de
      edição de uma raiz.
- [ ] O formulário de unidade **grava nas três telas** em que já aparece: a página de cadastro, o
      modal da tela de criar servidor e o painel dentro do modal de editar servidor.
- [ ] Criada pelo modal ou pelo painel, a unidade nova aparece **já selecionada** no campo de unidade
      da lotação, **sem recarregar** a tela e sem perder o que estava preenchido nos demais campos.
- [ ] Trocar a **unidade superior** é **transferência**: a gravação volta o modal com o campo em
      **realce de alerta**, a tarja dizendo o que a transferência significa e o botão pedindo
      confirmação — nada é gravado enquanto ela não vier. Destino **fora do alcance** é permitido:
      quem transfere pode deixar de administrar a unidade.
- [ ] Confirmada, a transferência grava e o ato fica registrado como **transferir**, distinguível da
      edição comum no histórico.
- [ ] O modal de edição **grava a cor** ao lado de identificação e hierarquia: o disco abre com a cor
      gravada selecionada, e **trocar a unidade superior não repinta** a unidade — sugerir cor pelo
      pai é do cadastro, não da edição.
- [ ] **Toda** recusa — nome ou sigla já usados, tom fora da paleta, nível que não subordina, tipo
      de filha vedado pelo pai, tipo que exige unidade superior, titular que não satisfaz o tipo
      novo, tipo que deixaria **alguma filha** sem subordinação e **tentativa de tornar raiz**, por
      quem não é superusuário, uma unidade que tem superior — volta **na própria tela**, com o
      motivo em português na tarja e o **controle recusado em realce e aberto**: no modal, campo
      fechado no `.campo-onsen` esconderia a própria recusa. O que foi preenchido permanece e nada
      é gravado.
- [ ] Criar e editar são **atos registrados** (SPEC [autorizacao/004](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md)),
      com a operação e a **sigla** da unidade como alvo, gravando cargo e unidade de quem assinou no
      momento do ato.
- [ ] O design foi aprovado no **mock**, e peça nova foi portada para `static/src/tema-dimap.dev.css`
      e renderizada no styleguide antes de qualquer template da aplicação usá-la — **nenhum token
      novo**: o realce de alerta, a tarja pendente e a tarja crítica já existem. A **molécula da
      tarja de recusa** passa a morar em `templates/partials/`, e as telas de servidor e de unidade
      incluem a mesma. O **disco de paleta** sai do campo de cor do cadastro para partial próprio e
      é composto dentro do `campo-onsen` do modal, e o campo gravado da tela de raiz é `.etched` +
      `.etched-rotulo` **no lugar** do controle, com a `.tarja-vinculo` neutra do aviso. A única peça
      nova são **dois glifos**: `#glifo-unidade`, o prédio que os ícones de ação já desenham, agora
      nomeado, e `#glifo-raiz`, que o compõe com a estrela de `#glifo-titular`. Nascem em
      `_glifos_unidade.html`, e é deles que sai o ícone da ação nova.

## 3 · Domínio
Nenhum model novo, e nenhuma entidade nova: **transferência não é objeto** — é o valor de `pai`
mudando entre a leitura e a gravação, e o que ela produz de duradouro é a linha do ato registrado.

O que muda de modelagem são duas coisas no contrato de ação. O **alcance de unidade**, em duas
frentes: ele deixa de nomear um parâmetro fixo e passa a valer para qualquer parâmetro que carregue um
id de unidade — a lotação de um servidor, hoje, e a unidade superior de uma unidade, aqui —, e o
**superusuário passa a alcançar o organograma inteiro**, dirigindo unidade ou não.

E um **regime de competência novo**, ao lado de `estrutural`: a ação que **só o superusuário exerce**.
Não é alcance (alcance responde *sobre qual unidade*, e criar raiz não incide sobre nenhuma) nem
concessão (que é justamente o que ela recusa) — é uma terceira resposta à pergunta *quem exerce*, e
por isso mora no contrato, junto das outras duas.

**`services/domain/autorizacao/contratos.py`**
```python
class UnidadesSubordinadas(TipoAlcance):
    """ALTERADO nesta SPEC: o contrato é o mesmo, o alcance passa a valer para TODOS os parâmetros
    declarados — cada um carrega o id de uma unidade, e todas precisam cair no alcance. `unidade`
    continua sendo o default porque é o nome do controle na maioria das telas; criar unidade declara
    `("pai",)`, que é o nome do select de unidade superior."""

    parametros_alvo: tuple[str, ...] = ("unidade",)


class Acao(BaseModel):
    ...
    estrutural: bool = False
    # ALTERADO nesta SPEC. Booleano ao lado de `estrutural`, e não um enum de regime: trocar os dois
    # por um enum reescreveria as quatro ações já declaradas, a projeção no banco e a linha de cada
    # execução gravada — por uma ação. Os dois se excluem na prática e nada no código os cruza.
    exclusiva_superusuario: bool = False
```

**`services/domain/autorizacao/models.py`** — e o avaliador precisa saber quais são, do mesmo jeito
que já sabe quais são as estruturais.
```python
class AvaliacaoCompetenciaInput(BaseModel):
    ...
    slugs_estruturais: frozenset[str] = frozenset()
    # Slugs, e não o contrato inteiro: o avaliador decide sobre conjuntos, e é o que o mantém sem
    # saber o que é uma `Acao`.
    slugs_exclusivos: frozenset[str] = frozenset()
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`Unidade` e `TipoUnidade`](001-models-perfil-cargos-unidade.md) e a
  [hierarquia](003-hierarquia-unidades.md) — o cadastro que estes dois atos criam e alteram, e as
  regras de nível, veda e raiz que recusam o que não pode existir.
- [`acao_protegida` e `registrar_ato`](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md) —
  a rota protegida, o alvo conferido contra o alcance e o rastro do ato.
- [`alcance_do_perfil`](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md) — "quais
  unidades este perfil alcança?"; é contra este conjunto que o pai escolhido e a unidade editada são
  conferidos, e é ele que recorta o select de unidade superior da criação.
- [`has_perm`](../autorizacao/003-avaliador-e-backend-de-autorizacao.md) — "este perfil exerce esta
  ação estrutural?"; quem lê a direção da unidade é o backend, não estas telas. É por ele que a
  exclusividade do superusuário responde nos três lugares de uma vez — barreira, botão e menu —,
  porque os três perguntam a mesma coisa.
- [`cor`, `cor_sugerida`](005-cor-da-unidade.md) e `tons_da_paleta`/`hex_da_cor` — "qual tom a
  unidade tem, e como ele chega ao disco?"; a sugestão pelo pai continua sendo do cadastro, e a
  edição parte sempre da cor gravada.
- [`cargo_titulariza`](014-titular-da-unidade.md) — "o titular atual satisfaz o tipo novo?"; a recusa
  é do model, e esta SPEC só a leva ao modal.
- [`FORMULARIO_SERVIDOR` e `LeitorDeFormulario`](../formularios/001-erros-de-formulario.md) — "como
  esta recusa se diz, e qual controle ela realça?"; o catálogo do servidor é o molde, e o da unidade
  nasce ao lado dele.

**Mock:** [020-mock-unidade-como-ato-administrativo.html](020-mock-unidade-como-ato-administrativo.html) — leia a skill `mock`.

## 4 · Fora de escopo
- **Repintar as unidades abaixo** quando a cor muda: a cor do pai é sugestão no cadastro, nunca
  herança (SPEC [005](005-cor-da-unidade.md)) — sem dono ainda.
- **Excluir unidade**, e o que fazer com filhas e lotados quando ela deixa de existir — sem dono ainda.
- **Tornar raiz** uma unidade que já tem superior: raiz é quem nasce raiz, e mudar isso depois
  continua sendo caso de seed (SPEC [008](008-seed-unidades.md)) ou shell — sem dono ainda.
- **Projetar `exclusiva_superusuario` no banco**: o regime fica só no contrato em código, e a
  execução gravada não o registra — sem dono ainda (Caveats).
- Inscrever as duas ações em **menu** — sem dono ainda; o `MENU_ADMINISTRADOR` da SPEC
  `autorizacao/005` segue sem tela que o renderize.
- **Histórico de alterações da unidade, campo a campo**: o que fica é a execução registrada (SPEC
  `autorizacao/004`) — sem dono ainda.
- **Avisar a unidade de destino** de que recebeu uma subordinada — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/competencias/protecao.py` → `acao_protegida`, `conferir_alvo`, `registrar_ato`,
  `pode_executar`: a barreira, a conferência do alvo, o rastro e a resposta que a tela precisa.
- `@apps/competencias/consulta.py` → `alcance_do_perfil`: as unidades alcançadas, em conjunto de ids.
- `@apps/competencias/utils.py` → `instanciar_acao`; `@apps/competencias/registro.py` →
  `_construir_registro`: onde as três ações novas se inscrevem.
- `@services/domain/autorizacao/avaliador.py` → `AvaliadorCompetencia`; e
  `@apps/competencias/consulta.py` → `montar_avaliacao`, `_slugs_estruturais`: onde o regime novo
  entra, no mesmo lugar em que o estrutural já entra.
- `@apps/user_admin/cadastro.py` → `DesfechoCadastro`, `criar_servidor`, `editar_servidor`: o molde
  dos dois atos irmãos, do formulário cru ao desfecho.
- `@services/utils/erros_formulario` → `LeitorDeFormulario`, `TradutorDeRecusa`, `RegraDeErro`,
  `TomDeRealce`, `REGRAS_PADRAO`; e `@apps/core/erros_formulario.py` → `de_validation_error`: a
  ponte do `ValidationError` do model.
- `@apps/unidades/context.py` → `catalogo_de_unidades`, `contexto_do_modal_de_unidade`,
  `contexto_cor_sugerida`, `contexto_unidade`: os catálogos já recortáveis por `ids_permitidos`.
- `@apps/unidades/paleta.py` → `tons_da_paleta`, `hex_da_cor`; e
  `@templates/unidades/partials/_campo_cor_unidade.html`: o disco que as duas telas passam a
  compartilhar.
- `@templates/user_admin/partials/_tarja_recusa.html` e `_cadastro_concluido.html`; e
  `@templates/user_admin/perfil.html` → o poço do modal e o botão condicional: a coreografia de
  abrir por rota, recusar no lugar e fechar esvaziando.
- `@static/src/acoes/unidades/criar_unidade/icones/`: o molde da pasta que a ação nova precisa em
  `criar_unidade_raiz/` — as duas variantes declaradas são cobradas no boot (`competencias.E003`).
- `@static/src/acoes/unidades/criar_unidade/icones/grande.svg`: o **prédio** já desenhado ali é a
  forma da unidade — o glifo novo o nomeia com as mesmas coordenadas, e o modificador da raiz vai no
  canto inferior direito, onde o `+` e o lápis dos irmãos já moram.
- `@templates/unidades/partials/_glifos_unidade.html` → `#glifo-titular`: de onde sai a estrela. Hoje
  o `unidade_form.html` não inclui o sprite de glifos, e passa a incluir.
- Skills: `acao-administrativa`, `erros-de-formulario`, `componentes-frontend`, `daisyui`, `htmx`,
  `mock`, `escrever-testes`, `test-django-views`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`apps/unidades/acoes_declaradas.py`** — as três ações, no app que já administra este domínio.
```python
ACAO_CRIAR_UNIDADE = instanciar_acao(
    slug="unidades.criar_unidade",
    nome="Cadastrar unidade",
    nome_curto="Nova unidade",
    tooltip="Cria uma unidade abaixo de outra que você dirige.",
    url_name="unidades:criar_unidade",
    partial="competencias/partials/_item_menu.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=True,
    # A unidade sobre a qual o ato incide é a MÃE, e o parâmetro é o nome do select da tela.
    alcance=UnidadesSubordinadas(parametros_alvo=("pai",)),
)

ACAO_EDITAR_UNIDADE = instanciar_acao(
    slug="unidades.editar_unidade",
    nome="Editar unidade",
    nome_curto="Editar unidade",
    tooltip="Altera nome, sigla, tipo e unidade superior de uma unidade.",
    url_name="unidades:editar_unidade",
    partial="competencias/partials/_item_menu.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=True,
    # Um alvo só: a unidade editada, que vem do caminho da rota. O DESTINO da transferência não é
    # conferido — transferir para fora do próprio ramo é permitido, e é isso que a confirmação
    # protege (§7).
    alcance=UnidadesSubordinadas(),
)

ACAO_CRIAR_UNIDADE_RAIZ = instanciar_acao(
    slug="unidades.criar_unidade_raiz",
    nome="Criar unidade raiz",
    nome_curto="Unidade raiz",
    tooltip="Cria a unidade de topo de um organograma, que não responde a nenhuma outra.",
    url_name="unidades:criar_unidade_raiz",
    partial="competencias/partials/_item_menu.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    # Nem estrutural nem concedida: dirigir unidade não dá esta caneta a ninguém, e conceder também
    # não. Os dois campos são independentes, e este vence — ver o avaliador abaixo.
    estrutural=False,
    exclusiva_superusuario=True,
    # Sem alcance: a raiz não pende de unidade alguma, e não há alvo a conferir. É o que dispensa a
    # saída de `is_superuser` no `conferir_alvo` de servir a esta ação.
    alcance=None,
)
```

**`apps/competencias/utils.py`** — o parâmetro novo do achatamento, na mesma ordem do contrato.
```python
def instanciar_acao(
    ...
    estrutural: bool = False,
    exclusiva_superusuario: bool = False,
    alcance: TipoAlcance | None = None,
) -> AcaoImplementada:
```

**`services/domain/autorizacao/avaliador.py`** — a exclusividade é uma subtração no fim, e não um
ramo em cada fonte.
```python
def __call__(self, entrada: AvaliacaoCompetenciaInput) -> AvaliacaoCompetenciaOutput:
    if not entrada.perfil.em_exercicio:
        return AvaliacaoCompetenciaOutput(slugs_liberados=frozenset())
    return AvaliacaoCompetenciaOutput(
        # Subtrair no fim, e não filtrar cada fonte: quem chega aqui NUNCA é superusuário — o
        # `PermissionsMixin.has_perm` responde True antes de consultar backend algum —, então
        # tirar o slug do conjunto é exatamente dizer "só ele exerce". E como as três telas
        # (barreira, botão e menu) perguntam pelo mesmo `has_perm`, uma linha responde às três.
        slugs_liberados=(self._por_concessao(entrada) | self._por_direcao(entrada))
        - entrada.slugs_exclusivos,
    )
```

**`apps/competencias/consulta.py`** — e a lista sai do registro em código, ao lado da irmã.
```python
def _slugs_exclusivos() -> frozenset[str]:
    return frozenset(
        implementada.acao.slug
        for implementada in REGISTRO.todas()
        if implementada.acao.exclusiva_superusuario
    )
```

**`apps/competencias/protecao.py`** — o dispatch do alcance percorre os parâmetros declarados.
```python
def _unidades_alvo(alcance: TipoAlcance, valores: Mapping[str, int]) -> tuple[int, ...]:
    if isinstance(alcance, UnidadesSubordinadas):
        # Cada parâmetro declarado carrega uma unidade. O `if` é o mesmo caso de leitura sem alvo
        # escolhido que `_valores_dos_alvos` já deixou passar: em POST a ausência virou 400 lá.
        return tuple(
            valores[parametro]
            for parametro in alcance.parametros_alvo
            if parametro in valores
        )
    if isinstance(alcance, LotacaoAtualEDestino):
        ...
```

**`apps/competencias/consulta.py`** — alcançar tudo é uma resposta do alcance, não uma exceção
espalhada por quem o consulta.
```python
def ramos_do_alcance(perfil: Perfil) -> tuple[NoHierarquia, ...]:
    if perfil.is_superuser:
        # O organograma inteiro, na MESMA forma que o recorte já devolve: assim `alcance_do_perfil`,
        # a árvore da tela e os selects ficam certos de uma vez, sem `is_superuser` em cada um.
        return tuple(posicao_de(raiz.pk).ego for raiz in Unidade.objects.filter(pai__isnull=True))
    arvores = {dirigida: posicao_de(dirigida).ego for dirigida in unidades_dirigidas(perfil)}
    ...
```

**`apps/competencias/protecao.py`** — e a presença do alvo, que o conjunto não responde.
```python
def conferir_alvo(request, perfil, acao, kwargs_da_rota) -> None:
    if acao.alcance is None:
        return
    # A saída existe para as ações COM alvo: sem ela, o superusuário que não dirige unidade alguma
    # tem alcance vazio e não conseguiria criar sob nenhum pai nem editar unidade alguma. Criar raiz
    # não passa por aqui — a ação dela declara `alcance=None`.
    if perfil.is_superuser:
        return
    ...
```

**`apps/unidades/schemas.py`** — os DTOs dos dois atos, ao lado do `SelecaoUnidadePai` que já mora aqui.
```python
# A paleta é do model (SPEC 005) e é de lá que ela vem: `TextChoices` é enum de string, o módulo
# de models não importa `schemas` e nenhum ciclo se fecha. `paleta.py` já o importa do mesmo lugar.
from apps.unidades.models import CorUnidade

NomeDeUnidade = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
SiglaDeUnidade = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]


class NovaUnidade(BaseModel):
    model_config = ConfigDict(frozen=True)

    nome: NomeDeUnidade
    sigla: SiglaDeUnidade
    tipo_id: int
    # `PaiOpcional` só porque a raiz existe: quem não é superusuário nunca chega aqui sem pai — o
    # decorator já devolveu 400 —, e o ato recusa quem chegar.
    pai_id: PaiOpcional = None
    # Enum, e não `str`: tom fora da paleta é recusado na fronteira, e o `choices` do `full_clean`
    # deixa de ser a única guarda. O Pydantic valida pelo valor (`agua-700`) e o `CharField` grava
    # esse mesmo valor de volta.
    cor: CorUnidade


class EdicaoUnidade(BaseModel):
    """Mesmos campos de `NovaUnidade`, com o id no lugar do pai obrigatório — a cor inclusive: o
    modal edita identificação, hierarquia e identidade visual. Sem token de confirmação — ele é do
    processo, não do cadastro, e entra como argumento do ato."""

    model_config = ConfigDict(frozen=True)

    unidade_id: int
    nome: NomeDeUnidade
    sigla: SiglaDeUnidade
    tipo_id: int
    cor: CorUnidade
    # Opcional só para a raiz que JÁ é raiz poder ser editada — o formulário dela não teria o que
    # mandar. Tornar raiz uma unidade que tem superior é recusado pelo ato, não pelo DTO.
    pai_id: PaiOpcional = None
```

**`services/utils/erros_formulario/regras.py`** — o tipo novo que o enum levanta, no catálogo
compartilhado e não no formulário da unidade: `enum` é classificação do Pydantic, não regra desta
tela. Nenhum formulário de hoje levanta este tipo — a linha é aditiva.
```python
REGRAS_PADRAO: Mapping[str, RegraDeErro] = {
    ...
    "enum": RegraDeErro(mensagem="{rotulo}: escolha uma opção da lista."),
}
```

**`apps/unidades/formularios.py`** — o catálogo da tela, com a única regra que o padrão não cobre.
```python
ERRO_NAO_VIRA_RAIZ = (
    "Unidade com superior não vira raiz: escolha a unidade à qual ela passa a responder."
)
AVISO_TRANSFERENCIA = (
    "Transferir {sigla}: ela e todas as unidades abaixo dela passam a responder a {destino}. "
    "Se o destino estiver fora do seu alcance, você deixa de administrá-la. Confirme para gravar."
)

FORMULARIO_UNIDADE = Formulario(
    campos=(
        CampoDeFormulario(controle="nome", rotulo="Nome"),
        CampoDeFormulario(controle="sigla", rotulo="Sigla"),
        CampoDeFormulario(controle="tipo", rotulo="Tipo"),
        CampoDeFormulario(
            controle="pai",
            rotulo="Unidade superior",
            # O tom vem da regra; a frase vem escrita do ato, com as siglas. `transferencia` fica
            # fora das REGRAS_PADRAO de propósito: nada mais no sistema o levanta.
            regras={
                "transferencia": RegraDeErro(
                    mensagem=AVISO_TRANSFERENCIA,
                    tom=TomDeRealce.ALERTA,
                )
            },
        ),
        CampoDeFormulario(controle="cor", rotulo="Cor"),
    )
)

ler_nova_unidade = LeitorDeFormulario(NovaUnidade, FORMULARIO_UNIDADE)
ler_edicao_unidade = LeitorDeFormulario(EdicaoUnidade, FORMULARIO_UNIDADE)
traduzir_recusa = TradutorDeRecusa(FORMULARIO_UNIDADE)
```

**`apps/unidades/cadastro.py`** — os dois atos, com a mesma forma de desfecho do cadastro de servidor.
```python
@dataclass(frozen=True)
class DesfechoUnidade:
    """Três desfechos em dois campos: gravou (`unidade`), recusou (`recusa`) e falta confirmar
    (`exige_confirmacao`, com o aviso na MESMA forma da recusa — mensagem e realce).

    Dataclass, e não Pydantic, pelo mesmo motivo do `DesfechoCadastro`: recado do ato para a view,
    que carrega o model gravado e não cruza fronteira de serviço — validar `Unidade` no Pydantic
    exigiria `arbitrary_types_allowed` para não validar nada."""

    unidade: Unidade | None
    recusa: RecusaDeFormulario = RecusaDeFormulario()
    exige_confirmacao: bool = False


def cadastrar_unidade(valores: Mapping[str, Any], raiz_permitida: bool = False) -> DesfechoUnidade:
    """`raiz_permitida` é a ROTA, não o perfil: quem pode criar raiz está declarado no contrato
    da ação (`exclusiva_superusuario`), e só a rota da raiz passa `True`. O ato não pergunta quem
    assina — recebe o que aquela porta permite (§3.3)."""
    leitura = ler_nova_unidade(valores)
    nova = leitura.dto
    if nova is None:
        return DesfechoUnidade(unidade=None, recusa=leitura.recusa or RecusaDeFormulario())
    if nova.pai_id is None and not raiz_permitida:
        return DesfechoUnidade(unidade=None, recusa=_recusa_de_raiz())
    unidade = Unidade(
        nome=nova.nome,
        sigla=nova.sigla,
        tipo_id=nova.tipo_id,
        pai_id=nova.pai_id,
        cor=nova.cor,
    )
    return _gravar(unidade)


def alterar_unidade(
    valores: Mapping[str, Any],
    transferencia_confirmada: bool = False,
) -> DesfechoUnidade:
    """A ordem importa: valida ANTES de pedir confirmação, para nunca pedir que se confirme uma
    transferência que a hierarquia vai recusar depois."""
    leitura = ler_edicao_unidade(valores)
    edicao = leitura.dto
    if edicao is None:
        return DesfechoUnidade(unidade=None, recusa=leitura.recusa or RecusaDeFormulario())
    unidade = get_object_or_404(Unidade, pk=edicao.unidade_id)
    destino_anterior = unidade.pai_id
    if edicao.pai_id is None and destino_anterior is not None:
        # Transferir para DEBAIXO da raiz é transferência comum; virar raiz não é edição de ninguém,
        # superusuário incluído — raiz é quem nasce raiz. O select nem oferece a opção, e é aqui que
        # a regra decide, não lá.
        return DesfechoUnidade(unidade=None, recusa=_recusa_de_raiz())
    _aplicar(unidade, edicao)
    try:
        unidade.full_clean()
    except ValidationError as recusa:
        return DesfechoUnidade(unidade=None, recusa=traduzir_recusa(de_validation_error(recusa)))
    if edicao.pai_id != destino_anterior and not transferencia_confirmada:
        return DesfechoUnidade(
            unidade=None,
            recusa=_aviso_de_transferencia(unidade),
            exige_confirmacao=True,
        )
    unidade.save()
    return DesfechoUnidade(unidade=unidade)


def _recusa_de_raiz() -> RecusaDeFormulario:
    return traduzir_recusa(
        (ErroBruto(controle="pai", tipo="raiz", mensagem=ERRO_NAO_VIRA_RAIZ),)
    )


def _aviso_de_transferencia(unidade: Unidade) -> RecusaDeFormulario:
    # A mensagem já vem escrita e vence a do catálogo; do catálogo se aproveita o TOM, que é alerta:
    # não há o que corrigir, há o que confirmar.
    destino = unidade.pai.sigla if unidade.pai else "nenhuma unidade superior (raiz)"
    return traduzir_recusa(
        (
            ErroBruto(
                controle="pai",
                tipo="transferencia",
                mensagem=AVISO_TRANSFERENCIA.format(sigla=unidade.sigla, destino=destino),
            ),
        )
    )


def _gravar(unidade: Unidade) -> DesfechoUnidade:
    try:
        unidade.full_clean()
        unidade.save()
    except ValidationError as recusa:
        # Nome e sigla repetidos, nível que não subordina, tipo vedado e titular incompatível: todas
        # são do model e chegam juntas por aqui, já nomeando os controles `nome`, `sigla`, `pai` e
        # `tipo`.
        return DesfechoUnidade(unidade=None, recusa=traduzir_recusa(de_validation_error(recusa)))
    return DesfechoUnidade(unidade=unidade)
```

**`apps/unidades/models/unidade.py`** — a hierarquia passa a ser conferida também para baixo.
```python
ERRO_TIPO_DESSUBORDINA_FILHA = "O tipo novo deixaria {siglas} sem subordinação."


def clean(self) -> None:
    self._checar_titular()
    self._checar_hierarquia()
    self._checar_filhas()


def _checar_filhas(self) -> None:
    """Criar não alcança esta regra — unidade nova não tem filhas. Editar, sim: baixar o nível do
    tipo deixaria as filhas de nível igual ou maior penduradas em quem já não as subordina, e o
    `_checar_hierarquia` só olha para cima."""
    if self.pk is None or not hasattr(self, "tipo"):
        return
    dessubordinadas = self.filhas.filter(tipo__nivel__gte=self.tipo.nivel)
    if dessubordinadas.exists():
        siglas = ", ".join(dessubordinadas.values_list("sigla", flat=True))
        raise ValidationError({"tipo": ERRO_TIPO_DESSUBORDINA_FILHA.format(siglas=siglas)})
```

**`apps/unidades/urls.py`** — leitura, escrita e o nome do parâmetro que o alcance declara.
```python
urlpatterns = [
    path("nova/", views.criar_unidade, name="criar_unidade"),
    # A escrita é rota apartada da que mostra o formulário: é essa separação que faz "abrir a tela
    # não cadastra nada" ser estrutural, e não uma flag no formulário.
    path("nova/gravar/", views.gravar_unidade, name="gravar_unidade"),
    # O ato é UM (`cadastrar_unidade`); o que muda é o desfecho que cada tela precisa ver. A página
    # troca o formulário inteiro pelo painel de conclusão; as telas de servidor trocam só o bloco de
    # campos por uma tarja curta e ainda atualizam, fora de banda, o select de lotação que vive fora
    # do modal. Conteúdo e alvo diferentes não cabem numa resposta só — e a alternativa a duas URLs
    # seria uma view escolhendo template pelo `HX-Target`, que põe o contrato da resposta num
    # cabeçalho e tira do teste a pergunta "que rota foi chamada".
    path(
        "nova/gravar-e-selecionar/",
        views.gravar_unidade_e_selecionar,
        name="gravar_unidade_e_selecionar",
    ),
    # A raiz tem porta própria porque é ato próprio: mesma tela, outro contrato de competência. O
    # `url_name` do contrato aponta para a de abertura, que é a que o check resolve.
    path("raiz/", views.criar_unidade_raiz, name="criar_unidade_raiz"),
    path("raiz/gravar/", views.gravar_unidade_raiz, name="gravar_unidade_raiz"),
    path("cor-sugerida/", views.cor_sugerida_unidade, name="cor_sugerida_unidade"),
    path("arvore/", views.arvore_de_unidades, name="arvore_de_unidades"),
    path("<int:pk>/", views.pagina_unidade, name="pagina_unidade"),
    # `unidade`, e não `pk`: é o parâmetro que o alcance da ação nomeia.
    path("<int:unidade>/editar/", views.editar_unidade, name="editar_unidade"),
    path("<int:unidade>/gravar/", views.gravar_edicao_unidade, name="gravar_edicao_unidade"),
]
```

**`apps/unidades/views.py`** — as views chegam com competência e alvo já conferidos.
```python
@acao_protegida(ACAO_CRIAR_UNIDADE)
def criar_unidade(request: HttpRequest) -> HttpResponse:
    # Oferecer o que o decorator vai recusar no POST é convidar ao 403: a lista de unidades
    # superiores sai do mesmo alcance que a barreira confere.
    autor = _autor(request)
    # Sem `permite_raiz`: esta tela nunca oferece "sem unidade superior", nem ao superusuário —
    # quem cria raiz é a outra rota.
    return render(request, TEMPLATE_UNIDADE, contexto_criar_unidade(alcance_do_perfil(autor)))


@acao_protegida(ACAO_CRIAR_UNIDADE_RAIZ)
def criar_unidade_raiz(request: HttpRequest) -> HttpResponse:
    """A mesma tela, com o campo de unidade superior gravado. Sem recorte de alcance: só o
    superusuário chega aqui, e ele alcança tudo."""
    return render(request, TEMPLATE_UNIDADE, contexto_criar_unidade(raiz=True))


@acao_protegida(ACAO_CRIAR_UNIDADE_RAIZ)
@require_POST
def gravar_unidade_raiz(request: HttpRequest) -> HttpResponse:
    # `pai_id` imposto, não lido: o campo vem `disabled` e não posta nada, mas quem define o que
    # esta porta faz é a rota — POST forjado com `pai` não vira criação comum numa ação sem alcance.
    valores = dict(_valores_da_unidade(request)) | {"pai_id": None}
    desfecho = cadastrar_unidade(valores, raiz_permitida=True)
    if desfecho.unidade is None:
        return render(request, TEMPLATE_UNIDADE_FORM, contexto_criacao_recusada(...), status=422)
    # Operação própria: no histórico, criar uma raiz não se confunde com criar uma subordinada.
    registrar_ato(
        request,
        operacao="criar_raiz",
        alvo_tipo="unidade",
        alvo_identificador=desfecho.unidade.sigla,
    )
    return render(request, TEMPLATE_UNIDADE_CRIADA, {"unidade": desfecho.unidade})


@acao_protegida(ACAO_CRIAR_UNIDADE)
@require_POST
def gravar_unidade(request: HttpRequest) -> HttpResponse:
    desfecho = cadastrar_unidade(
        _valores_da_unidade(request),
        raiz_permitida=_autor(request).is_superuser,
    )
    if desfecho.unidade is None:
        return render(request, TEMPLATE_UNIDADE_FORM, contexto_criacao_recusada(...), status=422)
    registrar_ato(request, operacao="criar", alvo_tipo="unidade", alvo_identificador=desfecho.unidade.sigla)
    return render(request, TEMPLATE_UNIDADE_CRIADA, {"unidade": desfecho.unidade})


@acao_protegida(ACAO_CRIAR_UNIDADE)
@require_POST
def gravar_unidade_e_selecionar(request: HttpRequest) -> HttpResponse:
    """Mesmo ato, outra resposta — e o nome diz qual: grava e devolve a unidade já escolhida. O alvo
    é o bloco de campos do painel, e o campo de lotação volta por swap fora de banda."""
    desfecho = cadastrar_unidade(_valores_da_unidade(request))
    if desfecho.unidade is None:
        return render(request, TEMPLATE_CAMPOS_UNIDADE, contexto_criacao_recusada(...), status=422)
    registrar_ato(request, operacao="criar", alvo_tipo="unidade", alvo_identificador=desfecho.unidade.sigla)
    return render(
        request,
        TEMPLATE_UNIDADE_SELECIONADA,
        {"unidade": desfecho.unidade, "selecionado": desfecho.unidade.pk}
        | catalogo_de_unidades(alcance_do_perfil(_autor(request))),
    )


@acao_protegida(ACAO_EDITAR_UNIDADE)
@require_POST
def gravar_edicao_unidade(request: HttpRequest, unidade: int) -> HttpResponse:
    valores = {
        # Do caminho da rota, nunca do corpo: é o mesmo id que o decorator conferiu.
        "unidade_id": unidade,
        "nome": request.POST.get("nome", ""),
        "sigla": request.POST.get("sigla", ""),
        "tipo_id": request.POST.get("tipo", ""),
        "pai_id": request.POST.get("pai", ""),
    }
    # Presença é a confirmação: o hidden só existe no modal que já mostrou o aviso.
    desfecho = alterar_unidade(
        valores,
        transferencia_confirmada="confirmar_transferencia" in request.POST,
    )
    if desfecho.unidade is None:
        # `_unidade(unidade)` relido do banco: `alterar_unidade` já alterou a instância dele em
        # memória, e reaproveitá-la mostraria no lado lido o valor que ainda não vale.
        return render(
            request,
            TEMPLATE_MODAL_UNIDADE,
            contexto_edicao_recusada(_unidade(unidade), valores, desfecho),
            # Falta confirmar não é recusa: 200 com o modal em estado de confirmação, 422 quando a
            # validação recusou de verdade.
            status=200 if desfecho.exige_confirmacao else 422,
        )
    registrar_ato(
        request,
        # O token só existe no modal que já mostrou o aviso, e transferência alguma grava sem
        # ele: é ele que distingue, no histórico, uma correção de nome de uma transferência.
        operacao="transferir" if "confirmar_transferencia" in request.POST else "editar",
        alvo_tipo="unidade",
        alvo_identificador=desfecho.unidade.sigla,
    )
    return render(request, TEMPLATE_EDICAO_CONCLUIDA, contexto_unidade(desfecho.unidade))
```

**`apps/unidades/context.py`** — a paleta passa a nascer de uma cor, e sugerir vira um dos casos.
```python
def contexto_da_paleta(cor: str) -> dict[str, Any]:
    """Recebe o valor CRU do POST para repopular a tela recusada — por isso `str`, e não o enum:
    slug forjado cai no default em vez de estourar o template, e quem o recusa é o DTO."""
    tinta = cor if cor in CorUnidade.values else CorUnidade.AGUA_700
    return {
        "tons": tons_da_paleta(tinta),
        "cor_hex": hex_da_cor(tinta),
    }


def contexto_cor_sugerida(pai_pk: int | None) -> dict[str, Any]:
    # Continua sendo a resposta do hx-get do select de pai — e só do CADASTRO: na edição a cor é
    # escolha gravada, e resugerir repintaria a unidade sem que ninguém pedisse.
    pai = Unidade.objects.filter(pk=pai_pk).first() if pai_pk else None
    return contexto_da_paleta(Unidade(pai=pai).cor_sugerida)
```

**`templates/unidades/partials/_disco_de_paleta.html`** — o disco extraído do campo de cor do
cadastro, para que o modal o componha sem arrastar rótulo e dica da outra tela.
```html
{# `form_id` só é escrito quando quem inclui declara: no cadastro os campos vivem FORA do <form>    #}
{# (SPEC 017) e precisam apontá-lo; no modal de edição eles estão dentro dele, e o atributo apontando #}
{# para id inexistente desassociaria o rádio de qualquer formulário.                                  #}
{# `.palette-field` DESCE do campo para cá: é o ancestral do `:has(input:checked)` que acende o poço  #}
{# atual, e os dois `.paint-well-atual` (gatilho e centro do disco) estão dentro deste invólucro.     #}
<div class="palette-field dropdown dropdown-right dropdown-end w-fit">
  ...
  <label class="paint-well" style="--a: {{ tom.angulo }}deg; --tinta: {{ tom.hex }}" title="{{ tom.rotulo }}">
    <input type="radio" name="cor" value="{{ tom.slug }}"{% if form_id %} form="{{ form_id }}"{% endif %} class="sr-only"{% if tom.selecionado %} checked{% endif %}>
  </label>
  ...
</div>
```

**`templates/unidades/partials/_campo_cor_unidade.html`** — o campo do cadastro passa a ser rótulo,
disco e dica; o alvo do hx-get segue sendo ele.
```html
{# Sem `.palette-field`: ela desceu para o disco, junto dos dois poços que ela acende. #}
<div id="campo-cor-unidade" class="form-field">
  <span class="text-overline">Cor da unidade</span>
  {% include "unidades/partials/_disco_de_paleta.html" with form_id="form-nova-unidade" %}
  <span class="form-field-hint">Pinta o anel do avatar de quem é lotado aqui. Repetir tom entre unidades é permitido.</span>
</div>
```

**`templates/unidades/partials/_campos_unidade.html`** — o campo de unidade superior nos dois
regimes, e o fim do `permite_raiz`.
```html
{# Raiz: gravação NO LUGAR do controle, e não um controle desabilitado. Além de `disabled` ainda    #}
{# ter cara de select, `.select-glass` declara `text-base-content` e vence `.etched-rotulo` por vir #}
{# depois no tema — a gravação não pegaria. Sem `<select name="pai">` no DOM, também não há o que   #}
{# postar. Nenhum átomo novo: os dois já existem.                                                  #}
<div class="form-field">
  <span class="text-overline">Unidade superior</span>
  {% if raiz %}
    <p class="etched etched-rotulo text-[15px] py-2.5">— sem unidade superior (raiz) —</p>
    <div class="tarja-vinculo flex items-start gap-2 mt-2">
      <svg class="w-5 h-5 shrink-0 text-info" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24"><use href="#glifo-raiz"/></svg>
      <p class="text-[13px] text-base-content/80">
        Unidade <strong>raiz</strong>: não responde a nenhuma outra, e é dela que o organograma
        começa. Só quem administra o sistema pode criar uma.
      </p>
    </div>
  {% else %}
    {# Sem `{% if permite_raiz %}`: a opção "sem unidade superior" deixa de existir nesta tela. #}
    <select name="pai" form="form-nova-unidade" class="select select-glass {{ realce.pai }}" data-select-onsen ...>
    ...
  {% endif %}
</div>
```

**`templates/unidades/partials/_campo_unidade_lotacao.html`** — o select de lotação, extraído das duas
telas de servidor que já o desenham igual, agora com o invólucro que o swap fora de banda alcança.
```html
{# O invólucro existe porque a casca de vidro (SPEC 011) SUBSTITUI o select no DOM: trocar só o     #}
{# <select> deixaria a casca velha na tela. Ele carrega o `flex-1 min-w-0` que a regra de filho     #}
{# direto de `.form-field-inline-action` dava ao select. Remontada a casca? Sim: `select_onsen.js`  #}
{# já reage a `htmx:afterSwap`, que o swap principal dispara.                                       #}
<div id="campo-unidade-lotacao" class="flex-1 min-w-0"{% if oob %} hx-swap-oob="outerHTML"{% endif %}>
  <select name="unidade" class="select select-glass {{ realce.unidade }}" data-select-onsen>
    {% for unidade in unidades %}
      <option value="{{ unidade.pk }}"{% if unidade.pk == selecionado %} selected{% endif %}>{{ unidade.sigla }} · {{ unidade.nome }}</option>
    {% endfor %}
  </select>
</div>
```

**`templates/unidades/partials/_campos_unidade.html`** — os campos compartilhados pelas três telas
passam a repopular o que foi digitado, a realçar o controle recusado e a ser um alvo de swap.
```html
{# `contents` para que o invólucro não vire um item do flex do formulário e as três seções em poço #}
{# percam o espaçamento entre si. É este bloco que as telas em painel trocam.                      #}
<div id="campos-nova-unidade" class="contents">
  {% include "partials/_tarja_recusa.html" with titulo="Unidade não cadastrada" %}
  ...
  <input type="text" name="nome" form="form-nova-unidade" class="input input-glass {{ realce.nome }}" value="{{ valores.nome }}" />
</div>
```

**`templates/unidades/partials/_unidade_criada_e_selecionada.html`** — a resposta do painel: o bloco de
campos vira a confirmação, e o campo lá fora se atualiza sozinho.
```html
<div id="campos-nova-unidade" class="contents">
  <div class="tarja-vinculo flex items-start gap-2">
    <p class="text-[13px] text-base-content/80">
      <strong>{{ unidade.sigla }}</strong> criada e já selecionada na lotação.
    </p>
  </div>
</div>
{% include "unidades/partials/_campo_unidade_lotacao.html" with oob=True %}
```

**`templates/unidades/partials/_modal_editar_unidade.html`** — o modal ganha destino, e o botão muda
de nome quando o que falta é confirmar.
```html
<form hx-post="{% url 'unidades:gravar_edicao_unidade' unidade.pk %}"
      hx-target="#poco-modal"
      hx-swap="innerHTML">
  {% include "partials/_tarja_recusa.html" with titulo="Alterações não gravadas" %}
  ...
  {# TODO campo-onsen chega ABERTO quando o controle foi recusado ou avisado — os quatro, não só  #}
  {# este: o input fica escondido atrás do toggle, e realçar um campo que ninguém vê não corrige   #}
  {# nem confirma nada. Vale para as recusas do model que nomeiam `tipo` (titular incompatível,    #}
  {# filha dessubordinada) tanto quanto para as que nomeiam `pai`.                                 #}
  <input type="checkbox" id="editar-campo-pai" class="campo-onsen-toggle"{% if realce.pai %} checked{% endif %} />
  ...
  <select name="pai" class="select select-glass {{ realce.pai }}" data-select-onsen>
    {# Só para a unidade que JÁ é raiz, que sem a opção não teria como continuar sendo o que é.   #}
    {# Ninguém TORNA raiz por aqui: a opção não existe para quem tem superior.                     #}
    {% if not unidade.pai_id %}<option value="" selected>— sem unidade superior (raiz) —</option>{% endif %}
  ...
  {# A cor é campo do modal como os outros: o valor LIDO é o poço com a tinta gravada, e o campo é #}
  {# o mesmo disco do cadastro. Escondido o rádio segue submetendo — `.campo-onsen-campo` é         #}
  {# `display:none`, e o que tira um controle do envio é `disabled`, não a visibilidade.            #}
  <div class="campo-onsen">
    <input type="checkbox" id="editar-campo-cor" class="campo-onsen-toggle"{% if realce.cor %} checked{% endif %} />
    <span class="text-overline etched-rotulo">Cor</span>
    <div class="campo-onsen-linha">
      {# `inline-block`: dentro do `.campo-onsen-valor`, que é bloco comum, o span fica inline e   #}
      {# `w-8 h-8` não pegam — nos outros usos o poço blockifica por ser filho de `.btn` ou absoluto. #}
      <p class="campo-onsen-valor"><span class="paint-well-atual inline-block align-middle w-8 h-8" style="--tinta: {{ cor_hex }}"></span></p>
      <div class="campo-onsen-campo">{% include "unidades/partials/_disco_de_paleta.html" %}</div>
      ...
    </div>
  </div>
  ...
  {% if exige_confirmacao %}<input type="hidden" name="confirmar_transferencia" value="1" />{% endif %}
  <button type="submit" class="btn btn-onsen btn-sm">
    {% if exige_confirmacao %}Confirmar transferência{% else %}Salvar alterações{% endif %}
  </button>
</form>
```

## 7 · Caveats
**O destino da transferência não é conferido contra o alcance, e a confirmação é o que existe no
lugar.** Exigir o destino dentro do alcance impediria o caso que dá sentido ao ato — entregar a
própria unidade a outro ramo —, e transferir só encolhe o alcance de quem assina: para ganhar alguma
coisa seria preciso editar uma unidade de fora, que a barreira já recusa. Custo: quem dirige pode
tirar a unidade do próprio alcance e não conseguir trazê-la de volta, e o que contém isso é a
confirmação na tela mais a linha do ato registrado.

**O superusuário atravessa toda conferência de alvo, de todas as ações.** Alcançar tudo é o que
`is_superuser` já significa no `has_perm` do Django, e mantê-lo preso ao alcance deixava o
administrador sem poder criar a primeira unidade de um ramo. Custo: a barreira de alcance de criar e
editar servidor também deixa de valer para ele, e o que contém isso passa a ser só a linha do ato
registrado.

**A raiz é ato à parte, e não um caso especial do ato de criar.** Fosse a mesma ação, "quem pode
criar" passaria a depender do valor de um campo do formulário — a competência viraria dado de
requisição, e a tela teria de esconder uma opção que a barreira não confere. Separando, cada porta
tem um contrato só: uma exige direção e alcance, a outra exige ser superusuário e não incide sobre
unidade alguma. Custo: duas rotas e duas linhas no registro para telas quase idênticas, e a página de
cadastro deixa de oferecer a opção "sem unidade superior" que a SPEC
[criacao_usuarios/006](../criacao_usuarios/006-enforcement-do-cadastro-de-servidor.md) mantinha.

**A exclusividade do superusuário é uma subtração no avaliador, não uma conferência na barreira.**
Ela poderia ser um `if perfil.is_superuser` no `acao_protegida`, mas aí o botão e o menu continuariam
oferecendo a ação a quem tomaria 403 ao clicar — e seriam três lugares repetindo a mesma regra. No
avaliador ela responde de uma vez, porque os três perguntam pelo mesmo `has_perm`, e o superusuário
nem chega lá (o `PermissionsMixin` responde True antes de consultar backend). Custo: quem lê
`acao_protegida` não vê a regra passar por ali, e entender por que a ação é exclusiva exige abrir o
avaliador; e uma concessão gravada para ela fica na tabela sem efeito nenhum, silenciosamente.

**`exclusiva_superusuario` não é projetada no banco.** A projeção (SPEC `autorizacao/002`) e a linha
da execução copiam `estrutural`, e copiar o regime novo custaria migração numa tabela de estado real
por um campo que só o código lê — o catálogo de atribuição já não filtra pelo regime hoje. Custo: o
admin do Django não mostra que a ação é exclusiva, e o histórico não registra sob que regime o ato
foi praticado.

**Um mesmo ato com duas rotas de escrita.** A página e os painéis das telas de servidor precisam de
desfechos diferentes — painel de conclusão que substitui o formulário, contra tarja curta mais o
select de lotação atualizado fora de banda —, e a alternativa seria uma view só escolhendo template
pelo `HX-Target` de quem postou. Custo: o contrato da ação aponta para uma das rotas, e uma rota de
escrita nova do mesmo ato pode nascer sem `@acao_protegida` sem que nada acuse além da revisão.

**O aviso de transferência viaja na forma de uma recusa.** `RecusaDeFormulario` já carrega mensagem,
tom e realce por controle, e um tipo próprio para "falta confirmar" seria a mesma estrutura com outro
nome. Custo: o campo do desfecho se chama `recusa` e carrega, às vezes, algo que não recusou nada —
quem lê precisa do `exige_confirmacao` ao lado para saber qual dos dois é.

**A confirmação é um segundo POST, e o primeiro é jogado fora.** Sem estado de sessão, o modal
devolvido carrega os valores digitados e o token, e o ato roda inteiro de novo — validação incluída.
Custo: duas passagens pelo `full_clean` por transferência, e a janela entre as duas em que outra
pessoa pode ter mudado a hierarquia (a segunda validação é que fecha essa janela).

**`Unidade.clean` passa a consultar as filhas.** Baixar o nível do tipo deixaria as filhas penduradas
em quem já não as subordina, e a regra de nível só olhava para cima. Custo: uma consulta a mais em
toda validação de unidade — inclusive na criação, onde não há filha alguma para conferir —, e a
invariante segue fora do banco, alcançável por `update()` e por carga direta.

**A edição não sugere cor, e o disco vira partial próprio.** Pendurar no select de pai do modal o
mesmo `hx-get` do cadastro repintaria a unidade a cada transferência, apagando em silêncio uma
escolha gravada — sugerir é decisão de quem cadastra, não de quem corrige. Extrair o disco é o que
permite compô-lo dentro do `campo-onsen` sem arrastar o rótulo e a dica da tela de cadastro. Custo:
o `form=` dos rádios deixa de ser fixo no partial e desce como parâmetro de quem inclui — um
`include` que esqueça de declará-lo no cadastro manda o formulário sem a cor, e nada acusa além da
revisão.

**O select de lotação vira partial compartilhado das duas telas de servidor.** As duas o desenham
igual, e o swap fora de banda precisa de um invólucro estável em ambas. Custo: `apps/unidades`
passa a ser dono de um pedaço da tela de servidor, e o invólucro carrega classe de layout que antes
vinha do token de campo.

**As duas ações moram em `apps/unidades`, e não em app próprio.** Elas administram o domínio do app
em que já vivem — mesma exceção declarada ao §3.5 que `competencias` e `user_admin` usam. Custo: o
app de unidade passa a ter rota protegida e ato registrado ao lado das telas de leitura abertas, e
distinguir os dois regimes depende de ler o decorator.

## 8 · Testes (TDD)
Comportamento *(todos com marker `banco`)*:
- `test_gravar_cria_a_unidade_abaixo_da_escolhida` — POST válido grava com o pai escolhido e devolve o
  painel de conclusão.
- `test_recusa_do_model_volta_no_formulario_realcada` — pai cujo nível não subordina volta o
  formulário com a frase em português e `.campo-realce-erro` no controle `pai`, sem gravar.
- `test_criacao_no_painel_devolve_o_campo_de_lotacao_com_a_unidade_nova` — a rota da lotação responde
  com o campo fora de banda e a unidade nova já selecionada.
- `test_tornar_raiz_e_recusado_para_todos` — nenhuma tela traz a opção "sem unidade superior" para
  quem tem superior, e o POST que a força é recusado no controle `pai` — inclusive vindo do
  superusuário —, sem gravar.
- `test_troca_de_pai_pede_confirmacao_sem_gravar` — a gravação volta o modal com `.campo-realce-alerta`
  no controle `pai` e o cadastro intacto no banco.
- `test_transferencia_confirmada_grava_e_registra_como_transferir` — com o token, o pai muda e a
  execução fica com `operacao="transferir"`.
- `test_edicao_sem_troca_de_pai_grava_sem_confirmacao` — nome, sigla e cor alterados gravam de
  primeira, com `operacao="editar"`, e a cor nova volta selecionada no disco.
- `test_tom_fora_da_paleta_e_recusado_no_controle_cor` — slug forjado morre no DTO, com a frase em
  português e o realce no controle `cor`, sem gravar.
- `test_recusa_vence_a_confirmacao` — transferência para um pai que não subordina volta como erro, e
  não como aviso a confirmar.
- `test_tipo_que_dessubordina_filha_e_recusado` — baixar o nível do tipo com filha de nível igual ou
  maior é recusado no controle `tipo`, sem gravar.
- `test_botao_de_editar_so_aparece_para_quem_alcanca_a_unidade` — a página da unidade traz o botão
  para quem dirige e não o traz para quem não alcança.

Segurança da ação (fora do teto — skill `acao-administrativa`; todos com marker `banco`):
- `test_anonimo_vai_para_o_login_sem_deixar_linha` — nas duas rotas de escrita.
- `test_autenticado_sem_competencia_recebe_403_registrado` — nas duas ações.
- `test_concessao_em_outra_unidade_nao_libera` — competência não se herda pelo organograma.
- `test_estrutural_libera_quem_dirige_sem_concessao` — e recusa quem não dirige.
- `test_perfil_fora_de_exercicio_nao_exerce` — impedido recebe 403; exonerado chega como anônimo e
  recebe 302, sem linha.
- `test_criar_com_pai_fora_do_alcance_e_403_registrado` — id válido, ramo alheio.
- `test_criar_sem_o_parametro_pai_e_400` — POST forjado não escapa da conferência.
- `test_superusuario_alcanca_todo_o_organograma` — sem dirigir unidade alguma, ele cria sob qualquer
  pai e edita qualquer unidade, e os atos ficam registrados como os de qualquer outro.
- `test_criar_raiz_so_o_superusuario_exerce` — ele grava a unidade sem superior, com
  `operacao="criar_raiz"`; quem não é recebe 403 registrado **mesmo com a concessão gravada** para o
  slug, e a ação não entra no `slugs_liberados` dele.
- `test_gravar_raiz_ignora_o_pai_forjado` — POST com `pai` preenchido na rota da raiz grava sem
  superior assim mesmo: quem define o ato é a porta, não o corpo.
- `test_editar_unidade_fora_do_alcance_e_403_registrado` — abrir o modal e gravar, os dois.
- `test_acao_inativa_nao_libera_ninguem` — fora do registro, nem com concessão gravada.
- `test_execucao_registrada_com_o_cargo_e_a_unidade_do_momento` — mudar a lotação depois não reescreve
  a linha.
- `test_leitura_autorizada_nao_vira_registro` — abrir a tela de cadastro não é ato.
- `test_gravacao_so_por_post` — GET nas rotas de escrita não altera nada.
