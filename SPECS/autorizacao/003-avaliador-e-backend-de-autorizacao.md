---
spec: autorizacao/003
versao: v4
atualizado_em: 2026-08-11
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
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
---

# SPEC autorizacao/003 — Avaliador de competência e backend de autorização

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como desenvolvedor da plataforma, quero perguntar ao Django se um perfil pode executar uma ação —
com a mesma chamada que qualquer projeto Django faz — e receber a resposta a partir do que o banco
guarda: as concessões e quem responde pela direção da unidade hoje. Assim rotas, menus e templates
autorizam pelo caminho padrão, em vez de cada um inventar a sua checagem.

## Critérios de aceite
- [ ] `perfil.has_perm("<app>.<nome>")` devolve `True` quando existe concessão daquela ação para um
      cargo que o perfil **exerce**, **na unidade dele**, e `False` no resto.
- [ ] Concessão da mesma ação **em outra unidade** — inclusive na unidade superior — não libera.
- [ ] Ação **estrutural** (SPEC 001) é liberada a quem **responde pela direção** da unidade (SPEC
      `user_admin/014`) — o titular em exercício, ou o substituto vigente dele —, sem atribuição nem
      concessão gravada; a quem não dirige, nem com concessão. Unidade **sem titular** e unidade
      **sem direção** não liberam ninguém.
- [ ] Perfil **fora de exercício** (SPEC `user_admin/015`) não exerce competência nenhuma — nem a
      estrutural nem a concedida ao cargo dele.
- [ ] Enquanto a substituição vigora, o substituto exerce também as competências concedidas ao
      **cargo do substituído**, na unidade dele — sem receber o vínculo de titularidade.
- [ ] Ação **inativa** não libera ninguém, mesmo com concessão gravada.
- [ ] Superusuário passa; usuário **anônimo** ou **inativo** não passa.
- [ ] Perguntar por **N ações** do mesmo perfil custa o mesmo que perguntar por uma: o acesso ao
      banco é **fixo** e acontece na primeira pergunta.
- [ ] A regra de competência é decidida em `services/` e é **testável sem banco**.

## Contexto e decisões de arquitetura

Esta SPEC entrega a decisão de acesso. Ela não protege rota nenhuma (SPEC 004) nem monta menu
(SPEC 005) — entrega a pergunta respondida.

**Reusar o protocolo do Django, trocar a fonte.** O Django separa o *protocolo* de autorização
(`has_perm`, `permission_required`, os mixins, `{{ perms }}`) da *fonte* das permissões (as tabelas
`Permission`/`Group`, servidas pelo `ModelBackend`), e `AUTHENTICATION_BACKENDS` é o ponto de
extensão oficial para trocar a segunda mantendo o primeiro. Um backend que só autoriza — nunca
autentica — passa a responder a partir das concessões da SPEC 002.

`Permission`/`Group` ficaram fora porque a concessão é uma **tripla** (ação, cargo, unidade), e
grupo → permissão só expressa duplas: a unidade viraria grupo, obrigando a resincronizar filiação
toda vez que alguém muda de lotação, com o dado já estando no `Perfil`.

**Duas fontes de competência, um resultado.** A concessão (SPEC 002) responde pelas ações comuns; a
**direção da unidade** (SPEC `user_admin/014`) responde pelas **estruturais** — as que se exercem
por dirigir a unidade, e que por isso não têm atribuição nem concessão a consultar. O avaliador une
os dois conjuntos; nada mais no sistema precisa saber que são dois.

Estrutural não se acumula por concessão: conceder uma ação estrutural a um cargo não libera ninguém,
porque a fonte dela é a direção. É o que impede a competência de ter duas portas com regras
diferentes.

**A fonte da estrutural é quem responde pela direção — e essa leitura já existe.** Ler `e_titular`
cru deixaria de fora o substituto do titular afastado, que é justamente quem dirige a unidade
enquanto o afastamento dura (SPECs `user_admin/014` e `015`), e deixaria de dentro o titular que não
está na cadeira. Quem decide isso é o `AvaliadorDirecao`, no submódulo `titularidade` — o avaliador
de competência **não o importa nem reimplementa**: recebe `dirige_a_unidade` já resolvido no DTO,
como já recebe as concessões. É o mesmo contrato do §3.3 (o domínio recebe o perfil resolvido) e o
que mantém o submódulo `autorizacao` sem cruzar domínio (§6.3). Nas duas faltas — **sem titular** e
**sem direção** — ninguém dirige, e a estrutural não sai para ninguém dentro da unidade: quem a
alcança é quem dirige o nível acima, pela subárvore de cada ação (SPECs 007 e 008).

**O exercício é pré-condição, não uma terceira fonte.** Competência é do cargo exercido; quem está
fora da cadeira não exerce, e o avaliador zera o resultado antes de olhar concessão ou direção.
Consequência aceita: o afastado perde o acesso às ações até reassumir o exercício — que é o efeito
que o afastamento existe para produzir —, e o superusuário segue passando pelo atalho do mixin.

**Quem cobre responde pelo cargo, então o cargo é conjunto.** Enquanto a substituição vigora, o
substituto exerce o que o cargo do afastado exerce (SPEC `user_admin/015`), sem virar titular de
nada. No DTO isso é o conjunto de cargos exercidos — o próprio mais o coberto —, e não um campo por
cargo: a regra da concessão continua sendo uma só ("bate com um cargo que ele exerce"), em vez de
ganhar um segundo caminho para o mesmo resultado. A unidade continua sendo a do perfil, que é a
mesma do substituído (SPEC `user_admin/015`).

O alcance sobre as unidades **abaixo** não é decidido aqui: `has_perm` responde pela unidade do
perfil, e a subárvore é regra de domínio de cada ação que a use (SPEC 007).

**O `ModelBackend` continua instalado.** Ele é quem serve as permissões de staff do admin do Django,
que a SPEC 002 mantém como conveniência de inspeção. Os dois backends convivem: `has_perm` é
verdadeiro se **qualquer** backend disser sim.

**Atalho de superusuário sai de graça.** `PermissionsMixin.has_perm` responde `True` para
superusuário ativo antes de consultar backend algum, e o `Perfil` já herda o mixin. Não se
reimplementa — e é ele que resolve o bootstrap enquanto não há concessão nenhuma gravada.

**A regra fica no domínio; a query, na aplicação.** A consulta traz as concessões da unidade do
perfil, a substituição vigente em que ele é substituto e as marcas de que a direção é lida — e nada
mais; quem decide se o cargo bate e se a ação está ativa é o avaliador em
`services/domain/autorizacao/`, sobre DTOs. Os slugs estruturais entram no DTO vindos do registro em
memória (SPEC 001) — o domínio não importa o catálogo do app, recebe o conjunto pronto, como já
recebe as concessões. Filtrar cargo no `.filter()` seria mais curto e
esconderia a regra num queryset — com dezenas de usuários e poucas ações por unidade, o punhado de
linhas a mais não paga esse preço, e é o que torna a regra testável sem banco (§3.3, §9).

**Cache por instância de usuário.** O menu da SPEC 005 vai perguntar por várias ações seguidas. O
backend guarda o conjunto de slugs liberados no próprio objeto de usuário na primeira pergunta —
mesma técnica do `ModelBackend`, com atributo próprio para não colidir com o cache dele. É ele que
faz o acesso ao banco ser fixo mesmo agora que a montagem custa mais de uma consulta. Custo aceito:
concessão alterada — ou impedimento registrado — só vale no request seguinte, o que é o
comportamento normal do Django.

## Peças de referência a compor
- `@services/domain/autorizacao` (SPEC 001) → contratos da ação; o avaliador entra no mesmo submódulo
  e é reexportado pelo `__init__.py`, que só reexporta (§7.2).
- `@apps/competencias/models` (SPEC 002) → `AtribuicaoUnidade` e `Concessao`: origem das linhas
  carregadas.
- `@apps/user_admin/models/user.py` → `Perfil`, que já herda `PermissionsMixin`: o protocolo
  `has_perm` e o atalho de superusuário vêm dele, não se reescrevem.
- `@services/domain/titularidade/` (SPEC `user_admin/014`) → `AvaliadorDirecao`, `EstadoDaDirecao` e
  `Direcao`: quem dirige a unidade hoje já é decidido lá; a camada de aplicação consulta e traduz em
  `dirige_a_unidade`, e o submódulo `autorizacao` não o importa.
- `@apps/user_admin/models/user.py` → `Perfil.e_titular` (SPEC `user_admin/014`) e
  `Perfil.em_exercicio` (SPEC `user_admin/015`): as marcas de que a direção e o exercício são lidos.
- `@apps/user_admin/models/substituicao.py` → `Substituicao` (SPEC `user_admin/015`): a vigente é a
  de `data_fim` nulo, e é dela que sai o cargo coberto.
- `@apps/competencias/registro.py` → `REGISTRO` (SPEC 001): de onde saem os slugs estruturais.
- `@config/settings.py` → `AUTHENTICATION_BACKENDS`: o backend novo entra **ao lado** do
  `ModelBackend`, que continua servindo o admin.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md

# services/domain/autorizacao/avaliador.py
class PerfilCompetencia(BaseModel):
    model_config = ConfigDict(frozen=True)

    unidade_id: int
    # Fora da cadeira não se exerce competência nenhuma, nem a estrutural.
    em_exercicio: bool
    # Conjuntos: enquanto a substituição vigora, o cargo do coberto entra ao lado do próprio.
    cargos_base_ids: frozenset[int]
    cargos_comissao_ids: frozenset[int] = frozenset()
    # Resolvido na aplicação pelo AvaliadorDirecao (SPEC user_admin/014); aqui não se reimplementa.
    dirige_a_unidade: bool = False


class ConcessaoVigente(BaseModel):
    model_config = ConfigDict(frozen=True)

    acao_slug: str
    acao_ativa: bool
    unidade_id: int
    cargo_base_id: int | None = None
    cargo_comissao_id: int | None = None


class AvaliacaoCompetencia(BaseModel):
    model_config = ConfigDict(frozen=True)

    perfil: PerfilCompetencia
    concessoes: tuple[ConcessaoVigente, ...]
    # Vêm do registro em código: o domínio não conhece o catálogo do app.
    slugs_estruturais: frozenset[str] = frozenset()


class CompetenciaResultado(BaseModel):
    model_config = ConfigDict(frozen=True)

    slugs_liberados: frozenset[str]


class AvaliadorCompetencia:
    def __call__(self, entrada: AvaliacaoCompetencia) -> CompetenciaResultado: ...
```

```python
# apps/competencias/consulta.py
def montar_avaliacao(perfil: Perfil) -> AvaliacaoCompetencia:
    """Carrega concessões da unidade, substituição vigente e as marcas da direção — custo fixo,
    independente de quantas ações serão perguntadas depois."""
    ...


def perfil_dirige_a_unidade(
    perfil: Perfil,
    estado: EstadoDaDirecao,
) -> bool:
    """Confere se quem o AvaliadorDirecao (SPEC user_admin/014) aponta é este perfil — titular ou
    substituto dele. A regra de direção não é reescrita aqui."""
    ...
```

```python
# apps/competencias/backends.py
ATRIBUTO_CACHE = "_competencia_cache"


class CompetenciaBackend:
    """Backend só de autorização: `authenticate` devolve None e quem autentica segue sendo o
    ModelBackend."""

    def authenticate(
        self,
        request: HttpRequest | None,
        **credenciais: object,
    ) -> None:
        return None

    def get_all_permissions(
        self,
        user_obj: object,
        obj: object | None = None,
    ) -> set[str]: ...

    def has_perm(
        self,
        user_obj: object,
        perm: str,
        obj: object | None = None,
    ) -> bool: ...
```

## Fora de escopo
- Proteger rota e registrar a execução do ato (SPEC 004).
- Contrato de menu e router (SPEC 005).
- Autorização dependente do objeto: a assinatura recebe `obj` porque o Django a define assim, mas
  esta SPEC a ignora — competência aqui é do perfil, não do lote.
- Alcance de quem dirige sobre as unidades abaixo: é regra de domínio de cada ação (SPEC 007), não
  da decisão de acesso.
- Gravar exercício, impedimento e substituição, e decidir quem dirige a unidade: SPECs
  `user_admin/014` e `015`, **pré-requisitos desta**. Aqui só se lê o que elas gravam.
- Cadeia de substituição — o substituto que se afasta não passa a competência adiante (SPEC
  `user_admin/015`).
- Invalidação imediata de cache após alterar concessão ou registrar impedimento.

## Testes (TDD)
Os cinco primeiros são domínio puro e rodam na suíte padrão. Os três últimos exercitam o backend
com `Perfil` real e carregam o marker `banco`, declarado em `markers_obrigatorios`.

- `test_avaliador_libera_por_cargo_base_ou_comissao` — concessão que mira o cargo base **ou** o
  cargo em comissão do perfil libera a ação; cargo que não é nenhum dos dois não libera.
- `test_avaliador_exige_unidade_exata` — concessão idêntica numa unidade diferente, inclusive na
  superior, não libera: não há herança pelo organograma.
- `test_avaliador_ignora_acao_inativa` — concessão gravada de ação inativa não entra no resultado.
- `test_avaliador_libera_estrutural_so_para_quem_dirige` — a ação estrutural sai liberada para quem
  dirige a unidade, sem concessão nenhuma, e não sai para quem não dirige nem quando há concessão
  dela gravada.
- `test_avaliador_nega_tudo_fora_de_exercicio` — perfil fora de exercício não recebe nem a
  concedida ao cargo dele nem a estrutural, ainda que dirija a unidade no papel.
- `test_backend_responde_has_perm_sem_multiplicar_consultas` — `has_perm` acerta o liberado e o
  negado, e perguntar por várias ações do mesmo perfil não acrescenta consulta. *(marker `banco`)*
- `test_backend_le_a_direcao_e_a_substituicao_do_banco` — o titular em exercício e o substituto do
  titular afastado recebem a estrutural; o titular afastado sem substituto não recebe, e o
  substituto ganha também a concessão do **cargo do substituído**. *(marker `banco`)*
- `test_backend_nega_anonimo_e_inativo_e_nao_autentica` — anônimo e perfil inativo não recebem nada,
  e `authenticate` devolve `None`. *(marker `banco`)*

## Patches

_Nenhum patch registrado até o momento._
