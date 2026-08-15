---
spec: autorizacao/003
versao: v9
atualizado_em: 2026-08-14
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v9: implementado — avaliador (`services/domain/autorizacao`), `apps/competencias/consulta.py`
    e `backends.py`, e os dois backends em `AUTHENTICATION_BACKENDS`; os 10 testes de §8 passam
  - v1: versão inicial
  - v2: segunda fonte de competência — ação estrutural liberada pela titularidade da unidade
    (SPEC titularidade/001), sem passar por atribuição nem concessão
  - v3: registrada a pendência de revisão da fonte da estrutural — com um titular só por unidade
    (SPEC user_admin/014 v5), quem a exerce é quem responde pela direção, incluindo o substituto do
    titular afastado; a revisão fica para iteração própria
  - v4: pendência resolvida — a fonte da estrutural passa a ser quem responde pela direção (titular
    em exercício ou substituto dele), lida pelo avaliador da SPEC user_admin/014 em vez da marca
    `e_titular` crua; o exercício vira pré-condição de qualquer competência e o substituto passa a
    exercer também as concedidas ao cargo de quem cobre (SPEC user_admin/015); a titularidade deixa
    de ser referenciada como épico próprio
  - v5: sem mudança de escopo — a SPEC foi reescrita no formato de seções numeradas da skill
    `specs`, com a justificativa toda concentrada em Caveats
  - v6: a competência exercida passa a ser um conjunto de **cadeiras** (unidade × cargo), e não uma
    unidade com dois conjuntos de cargos — o substituto pode ser de outra unidade (SPEC
    user_admin/015), e a cobertura vale na unidade do substituído
  - v7: a estrutural passa a ter duas portas — já vem liberada a quem responde pela direção e ainda
    pode ser concedida a outros cargos, pela mesma regra das demais; e a unidade × cargo de onde se
    exerce competência passa a se chamar **caneta**
  - v8: testes TDD escritos e falhando (§8) — avaliador e backend seguem por implementar
---

# SPEC autorizacao/003 — Avaliador de competência e backend de autorização

## 1 · User story
**Requisito não-funcional** — "este perfil pode executar esta ação?" passa a ter resposta pelo caminho
padrão do Django (`has_perm`, mixins, `{{ perms }}`), servida pelo que o banco guarda: as concessões e
quem responde pela direção da unidade hoje.

## 2 · Condições de pronto
- [ ] `perfil.has_perm("<app>.<nome>")` devolve `True` quando existe concessão daquela ação para um
      cargo que o perfil **exerce**, **na unidade em que o exerce**, e `False` no resto.
- [ ] Concessão da mesma ação **em outra unidade** — inclusive na unidade superior — não libera.
- [ ] Ação **estrutural** (SPEC 001) já vem liberada a quem **responde pela direção** da unidade — o
      titular em exercício ou o substituto vigente dele —, sem atribuição nem concessão gravada.
      Unidade **sem titular** e unidade **sem direção** não liberam ninguém por essa porta.
- [ ] Ação estrutural **concedida** a um cargo libera quem exerce esse cargo naquela unidade, pela
      mesma regra das demais — e quem dirige segue liberado sem concessão nenhuma.
- [ ] Perfil **fora de exercício** não exerce competência nenhuma — nem a estrutural nem a concedida ao
      cargo dele.
- [ ] Enquanto a substituição vigora, o substituto exerce também as competências concedidas ao **cargo
      do substituído, na unidade do substituído** — inclusive quando ela não é a dele —, sem receber o
      vínculo de titularidade.
- [ ] Ação **inativa** não libera ninguém, mesmo com concessão gravada.
- [ ] Superusuário passa; usuário **anônimo** ou **exonerado** não passa.
- [ ] Perguntar por **N ações** do mesmo perfil custa o mesmo que perguntar por uma: o acesso ao banco
      é **fixo** e acontece na primeira pergunta.

## 3 · Domínio
Iteração de **decisão de acesso**: nenhum model novo, nenhuma migração. A competência é exercida por
uma **caneta** — a dupla unidade × cargo de onde se assina —, e quem cobre alguém tem duas: a própria
e a do coberto, que pode ser de outra unidade.

Caneta e concessão declaram as mesmas duas coisas, unidade e cargo, e é por isso que uma se confere
contra a outra; o que as separa é o terceiro campo de cada uma — a concessão nomeia a **ação**, a caneta
diz se **dirige a unidade**. Uma caneta existe sem ação nenhuma: o servidor recém-chegado tem cargo e
unidade e não pratica ato algum. Uma concessão existe sem pessoa nenhuma: o cargo vago mantém a linha
gravada. A caneta vem da pessoa — lotação, cargo e substituição vigente; a concessão vem do ato de quem
dirige.

```python
class Caneta(BaseModel):
    """Uma posição de onde se exerce competência. A própria, e — enquanto a substituição vigora —
    a de quem se cobre."""

    model_config = ConfigDict(frozen=True)

    unidade_id: int
    cargo_base_id: int | None = None
    cargo_comissao_id: int | None = None
    # Resolvido na aplicação pelo AvaliadorDirecao (SPEC user_admin/014): quem cobre o titular
    # dirige a unidade dele, sem receber o vínculo.
    dirige_a_unidade: bool = False
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`AtribuicaoUnidade` e `Concessao`](002-competencia-no-banco.md) — "que ações estão concedidas a
  quais cargos, nesta unidade?".
- [`Acao.ativa` e `Acao.estrutural`](002-competencia-no-banco.md) — "esta ação ainda existe, e dirigir
  a unidade já a libera?".
- [`avaliar_direcao`, `EstadoDaDirecao` e `Direcao`](../user_admin/014-titular-da-unidade.md) — "quem
  dirige esta unidade hoje?"; a camada de aplicação pergunta e traduz a resposta em
  `dirige_a_unidade`, e o submódulo `autorizacao` não importa o `titularidade`.
- [`Perfil.em_exercicio`](../user_admin/015-exercicio-e-substituicao.md) — "este perfil está na
  cadeira?", leitura derivada do impedimento vigente e da exoneração.
- [`substituicao_que_exerce`](../user_admin/015-exercicio-e-substituicao.md) — "quem este perfil cobre
  hoje, e de que caneta?"; a substituição é do impedimento, e o substituído é
  `impedimento.perfil`.
- [`RegistroAcoes`](001-catalogo-de-acoes-em-codigo.md) — "quais slugs são estruturais?", lido do
  registro em memória e entregue ao domínio já resolvido.

A competência tem duas fontes e um resultado só: a concessão responde por qualquer ação, estrutural
inclusive; dirigir a unidade já responde pelas estruturais dela, sem nada gravado; e o exercício é
pré-condição das duas. Nada mais no sistema precisa saber que são duas.

## 4 · Fora de escopo
- Proteger rota e registrar a execução do ato — SPEC 004.
- Contrato de menu e router — SPEC 005.
- Oferecer a ação estrutural no catálogo de atribuição da unidade, para que ela possa ser concedida —
  SPEC 007.
- Alcance de quem dirige sobre as unidades **abaixo** — regra de domínio de cada ação (SPEC 007), não
  da decisão de acesso.
- Autorização dependente do objeto: a assinatura recebe `obj` porque o Django a define assim, e esta
  SPEC a ignora — sem dono ainda.
- Gravar exercício, impedimento e substituição, e decidir quem dirige a unidade — SPECs
  `user_admin/014` e `015`, **pré-requisitos desta**.
- Cadeia de substituição — o substituto que se afasta não passa a competência adiante (SPEC
  `user_admin/015`).
- Invalidação imediata do cache após alterar concessão ou registrar impedimento — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/autorizacao` (SPEC 001) → `Acao`, `VarianteIcone`; o avaliador entra no mesmo
  submódulo e é reexportado pelo `__init__.py`.
- `@apps/competencias/models` (SPEC 002) → `AtribuicaoUnidade` e `Concessao`: origem das linhas
  carregadas.
- `@apps/user_admin/models/user.py` → `Perfil`, que já herda `PermissionsMixin`: o protocolo `has_perm`
  e o atalho de superusuário; e `Perfil.em_exercicio` / `exonerado`.
- `@services/domain/titularidade/` → `avaliar_direcao`, `EstadoDaDirecao`, `Direcao`.
- `@apps/user_admin/context.py` → `_estado_da_direcao` (SPEC 016): a montagem do estado a partir do
  titular e do substituto já carregados.
- `@apps/user_admin/exercicio.py` → `substituicao_que_exerce`: a caneta coberta, com o substituído já
  em `select_related`.
- `@apps/user_admin/models/unidade.py` → `Unidade.titular`: o titular da unidade, sem consulta nova.
- `@apps/competencias/registro.py` → `REGISTRO`: de onde saem os slugs estruturais.
- `@config/settings.py` → `AUTHENTICATION_BACKENDS`: o backend novo entra ao lado do `ModelBackend`.
- Skills: `escrever-testes`, `test-django-views`.

## 6 · Snippets

**`services/domain/autorizacao/models.py`** — os DTOs do avaliador, ao lado dos contratos da SPEC 001.
O perfil chega **resolvido**: o domínio não lê banco, não conhece `Perfil` e não sabe quem é titular.
```python
class PerfilCompetencia(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Fora da cadeira não se exerce competência nenhuma, nem a estrutural.
    em_exercicio: bool
    # A própria e, enquanto a substituição vigora, a de quem ele cobre — que pode ser de outra
    # unidade. Uma regra só para as duas: "bate com uma caneta que ele tem".
    canetas: tuple[Caneta, ...]


class ConcessaoVigente(BaseModel):
    model_config = ConfigDict(frozen=True)

    acao_slug: str
    acao_ativa: bool
    unidade_id: int
    cargo_base_id: int | None = None
    cargo_comissao_id: int | None = None


class AvaliacaoCompetenciaInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    perfil: PerfilCompetencia
    concessoes: tuple[ConcessaoVigente, ...]
    # Vêm do registro em código: o domínio não conhece o catálogo do app.
    slugs_estruturais: frozenset[str] = frozenset()


class AvaliacaoCompetenciaOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    slugs_liberados: frozenset[str]
```

**`services/domain/autorizacao/avaliador.py`** — a regra inteira, sem banco: o exercício zera antes de
qualquer fonte, e as duas fontes se somam num conjunto só.
```python
class AvaliadorCompetencia:
    def __call__(self, entrada: AvaliacaoCompetenciaInput) -> AvaliacaoCompetenciaOutput:
        # Pré-condição, não terceira fonte: competência é do cargo exercido.
        if not entrada.perfil.em_exercicio:
            return AvaliacaoCompetenciaOutput(slugs_liberados=frozenset())
        return AvaliacaoCompetenciaOutput(
            slugs_liberados=self._por_concessao(entrada) | self._por_direcao(entrada),
        )

    def _por_concessao(self, entrada: AvaliacaoCompetenciaInput) -> frozenset[str]:
        """O cruzamento das duas listas: as canetas do perfil (uma, ou duas quando ele cobre
        alguém) contra as concessões das unidades dessas canetas.

        A estrutural entra por aqui como qualquer outra — o que a distingue é já vir liberada a
        quem dirige, não ser exclusiva dele."""
        return frozenset(
            concessao.acao_slug
            for concessao in entrada.concessoes
            if concessao.acao_ativa
            and any(self._caneta_bate(caneta, concessao) for caneta in entrada.perfil.canetas)
        )

    def _por_direcao(self, entrada: AvaliacaoCompetenciaInput) -> frozenset[str]:
        """O atalho de quem responde pela direção: `dirige_a_unidade` é o campo que só a caneta
        tem, e ele libera as estruturais sem consultar concessão nenhuma.

        Não há filtro de ação inativa aqui: os slugs vêm do registro em código, e ação inativa é
        justamente a que saiu de lá."""
        if not any(caneta.dirige_a_unidade for caneta in entrada.perfil.canetas):
            return frozenset()
        return entrada.slugs_estruturais

    def _caneta_bate(self, caneta: Caneta, concessao: ConcessaoVigente) -> bool:
        """A conferência que dá sentido às duas listas: mesma unidade E mesmo cargo.

        O cargo é comparado DENTRO da caneta — o cargo do coberto vale na unidade dele, não na do
        substituto, e cruzar os dois liberaria competência em unidade alheia."""
        if caneta.unidade_id != concessao.unidade_id:
            return False
        # A concessão nomeia exatamente um cargo (XOR do `CheckConstraint`, SPEC 002): o ramo
        # preenchido é o que se compara, e o `None` do outro lado nunca casa por acidente.
        if concessao.cargo_base_id is not None:
            return concessao.cargo_base_id == caneta.cargo_base_id
        return concessao.cargo_comissao_id == caneta.cargo_comissao_id


def avaliar_competencia(entrada: AvaliacaoCompetenciaInput) -> AvaliacaoCompetenciaOutput:
    return AvaliadorCompetencia()(entrada)
```

**`apps/competencias/consulta.py`** — a borda que traduz banco → DTO, numa passagem só.
```python
def montar_avaliacao(perfil: Perfil) -> AvaliacaoCompetenciaInput:
    """Canetas do perfil, concessões das unidades dessas canetas e os slugs estruturais — custo
    fixo, independente de quantas ações serão perguntadas depois."""
    ...


def canetas_do_perfil(perfil: Perfil) -> tuple[Caneta, ...]:
    """A própria mais a coberta. A cobertura entra com a unidade e os cargos do SUBSTITUÍDO, que é
    quem tem a competência emprestada."""
    substituicao = substituicao_que_exerce(perfil)
    ...


def dirige(perfil: Perfil, unidade: Unidade) -> bool:
    """Confere se quem `avaliar_direcao` aponta é este perfil — titular ou substituto dele. A regra
    de direção não é reescrita aqui, e o estado é o mesmo que a página da unidade monta."""
    ...


def unidades_dirigidas(perfil: Perfil) -> frozenset[int]:
    """As unidades das canetas que dirigem — pode ser mais de uma, quando alguém cobre o titular de
    outra unidade. É daqui que a SPEC 007 parte para calcular o alcance."""
    ...
```

**`apps/competencias/backends.py`** — a implementação da DIMAP que ocupa o slot de backend do Django,
respondendo permissão e nada mais.
```python
ATRIBUTO_CACHE = "_competencia_cache"


class CompetenciaPermissionBackend:
    """Backend de autorização da DIMAP: serve `has_perm` a partir da competência (concessão da
    unidade + direção), sem autenticar ninguém.

    Não há classe-base a herdar — o Django resolve backend por duck typing, e é a assinatura destes
    três métodos que faz esta classe ser aceita em `AUTHENTICATION_BACKENDS`."""

    def authenticate(self, request: HttpRequest | None, **credenciais: object) -> None:
        # Quem autentica segue sendo o ModelBackend: devolver None aqui é como o protocolo diz
        # "não é comigo", e o Django passa ao backend seguinte.
        return None

    def get_all_permissions(self, user_obj: object, obj: object | None = None) -> set[str]:
        """Os slugs liberados, montados uma vez e guardados no próprio objeto de usuário — mesma
        técnica do ModelBackend, com atributo próprio para não colidir com o cache dele.

        É aqui que o custo fixo se cumpre: a primeira pergunta paga a consulta, e o menu que
        pergunta por dez ações seguidas não paga mais nada."""
        # Anônimo não tem caneta nenhuma. Superusuário nem chega aqui: `PermissionsMixin.has_perm`
        # responde True antes de consultar backend algum.
        if not isinstance(user_obj, Perfil):
            return set()
        # Permissão por objeto não tem dono (§4), e negar é o default seguro: devolver o conjunto
        # global responderia "pode" a uma pergunta sobre um lote específico.
        if obj is not None:
            return set()
        cacheado = getattr(user_obj, ATRIBUTO_CACHE, None)
        if cacheado is None:
            # Exoneração e afastamento não são conferidos aqui: entram no DTO como `em_exercicio`,
            # e o avaliador zera tudo antes de olhar concessão.
            entrada = montar_avaliacao(user_obj)
            avaliacao = avaliar_competencia(entrada)
            cacheado = set(avaliacao.slugs_liberados)
            setattr(user_obj, ATRIBUTO_CACHE, cacheado)
        return cacheado

    def has_perm(self, user_obj: object, perm: str, obj: object | None = None) -> bool:
        # O protocolo do Django é plano: a pergunta é pertinência no conjunto, e o `obj` só é
        # repassado para que a negativa por objeto aconteça num lugar só.
        return perm in self.get_all_permissions(user_obj, obj)
```

**`config/settings.py`** — os dois backends, cada um com um papel; a ordem não decide nada, porque
`has_perm` é verdadeiro se qualquer um deles disser sim.
```python
AUTHENTICATION_BACKENDS = [
    # Autenticação, e as permissions do admin.
    "django.contrib.auth.backends.ModelBackend",
    # Autorização por competência: só responde permissão, e é a única fonte das ações da plataforma.
    "apps.competencias.backends.CompetenciaPermissionBackend",
]
```

## 7 · Caveats
**O protocolo do Django é reusado e só a fonte muda**, com um backend novo ao lado do `ModelBackend`,
que continua servindo o admin. `Permission`/`Group` ficaram fora porque a concessão é uma tripla (ação,
cargo, unidade) e grupo → permissão só expressa duplas — a unidade viraria grupo, obrigando a
resincronizar filiação a cada mudança de lotação. Custo: `has_perm` é verdadeiro se **qualquer** backend
disser sim, então uma permission gravada à mão no admin também abre uma rota de ação.

**O conjunto de slugs liberados é cacheado na instância de usuário**, montado na primeira pergunta. Sem
isso o menu da SPEC 005, que pergunta por várias ações seguidas, multiplicaria as consultas. Custo:
concessão alterada, impedimento registrado ou substituição encerrada só valem no request seguinte.

**A regra decide em Python, sobre as linhas carregadas, em vez de filtrar cargo no queryset.** É o que
mantém a competência testável sem banco (§3.3, §9) em vez de escondida num `.filter()`. Custo: O(n)
sobre as concessões das unidades das canetas a cada primeira pergunta — dezenas de linhas, no
organograma que a DIMAP tem hoje.

**A direção e os slugs estruturais chegam ao domínio já resolvidos, pela aplicação.** É o que impede o
submódulo `autorizacao` de importar o `titularidade` e de conhecer o catálogo do app (§6.3). Custo: quem
monta a avaliação precisa lembrar de resolver os dois — esquecer não quebra nada visivelmente, só faz a
estrutural sumir para quem dirige.

**A montagem do `EstadoDaDirecao` é a mesma peça da página da unidade** (SPEC `user_admin/016`), e esta
SPEC a consome em vez de reescrever a leitura. Custo: uma peça de `context.py` passa a ter dois
consumidores em apps diferentes, e mudar a assinatura dela quebra longe de onde ela mora.

**A ação estrutural tem duas portas: já vem liberada a quem dirige a unidade e ainda pode ser concedida
a outros cargos.** Quem responde pela direção precisa dela sem depender de ninguém, e trancá-la nele
impediria a delegação que o dia a dia da unidade exige. Custo: a mesma competência passa a ser conferida
por duas regras, e revogar a concessão não tira o acesso de quem dirige — sem a tela dizer de onde ele
vem, a revogação parece não ter funcionado.

**Delegar a estrutural passa pelos dois níveis da SPEC 002**, a atribuição da unidade e depois a
concessão ao cargo, enquanto a porta da direção não exige linha nenhuma. É o que mantém uma regra só
para toda concessão, em vez de um caminho curto exclusivo da estrutural. Custo: a unidade precisa
receber a atribuição de uma ação que seu dirigente já exerce sem ela.

**O afastado perde o acesso a tudo enquanto está fora de exercício.** É o efeito que o afastamento existe
para produzir: competência é do cargo exercido. Custo: ato pendente iniciado antes do afastamento fica
sem quem o termine até a volta ou a designação do substituto, e o único contorno é o superusuário.

## 8 · Testes (TDD)
Os seis primeiros são domínio puro e rodam na suíte padrão. Os três últimos exercitam o backend com
`Perfil` real e carregam o marker `banco`.

- `test_avaliador_libera_por_cargo_base_ou_comissao` — concessão que mira o cargo base **ou** o cargo em
  comissão da caneta libera a ação; cargo que não é nenhum dos dois não libera.
- `test_avaliador_exige_unidade_exata` — concessão idêntica numa unidade diferente, inclusive na
  superior, não libera: não há herança pelo organograma.
- `test_avaliador_nao_cruza_canetas` — o cargo de uma caneta não libera concessão da unidade da outra:
  quem cobre alguém de outra unidade exerce lá o cargo do coberto, e aqui o dele.
- `test_avaliador_ignora_acao_inativa` — concessão gravada de ação inativa não entra no resultado.
- `test_avaliador_libera_estrutural_para_quem_dirige` — a estrutural sai liberada para a caneta que
  dirige a unidade, sem atribuição nem concessão gravada, e não sai para quem não dirige e não tem
  concessão dela.
- `test_avaliador_libera_estrutural_concedida_a_outro_cargo` — concessão de ação estrutural ao cargo da
  caneta libera quem não dirige, pela mesma regra de unidade exata das ações comuns.
- `test_avaliador_nega_tudo_fora_de_exercicio` — perfil fora de exercício não recebe nem a concedida ao
  cargo dele nem a estrutural, ainda que dirija a unidade no papel.
- `test_backend_responde_has_perm_sem_multiplicar_consultas` — `has_perm` acerta o liberado e o negado, e
  perguntar por várias ações do mesmo perfil não acrescenta consulta. *(marker `banco`)*
- `test_backend_monta_as_canetas_do_banco` — o titular em exercício e o substituto do titular afastado
  recebem a estrutural da unidade dirigida; o titular afastado sem substituto não recebe; e o substituto
  de outra unidade ganha a concessão do **cargo do substituído, na unidade do substituído**.
  *(marker `banco`)*
- `test_backend_nega_anonimo_e_exonerado_e_nao_autentica` — anônimo e perfil exonerado não recebem nada,
  e `authenticate` devolve `None`. *(marker `banco`)*
