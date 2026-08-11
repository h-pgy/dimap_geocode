---
spec: autorizacao/003
versao: v2
atualizado_em: 2026-08-11
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: segunda fonte de competência — ação estrutural liberada pela titularidade da unidade
    (SPEC titularidade/001), sem passar por atribuição nem concessão
---

# SPEC autorizacao/003 — Avaliador de competência e backend de autorização

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como desenvolvedor da plataforma, quero perguntar ao Django se um perfil pode executar uma ação —
com a mesma chamada que qualquer projeto Django faz — e receber a resposta a partir das concessões
do banco, para que rotas, menus e templates autorizem pelo caminho padrão em vez de cada um
inventar a sua checagem.

## Critérios de aceite
- [ ] `perfil.has_perm("<app>.<nome>")` devolve `True` quando existe concessão daquela ação para um
      cargo do perfil **na unidade dele**, e `False` no resto.
- [ ] Concessão da mesma ação **em outra unidade** — inclusive na unidade superior — não libera.
- [ ] Ação **estrutural** (SPEC 001) é liberada a quem é **titular** da sua unidade, sem atribuição
      nem concessão gravada; a quem não é titular, nem com concessão.
- [ ] Ação **inativa** não libera ninguém, mesmo com concessão gravada.
- [ ] Superusuário passa; usuário **anônimo** ou **inativo** não passa.
- [ ] Perguntar por **N ações** do mesmo perfil custa **uma consulta só** ao banco.
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
**titularidade** (SPEC `titularidade/001`) responde pelas **estruturais** — as que se exercem por
dirigir a unidade, e que por isso não têm atribuição nem concessão a consultar. O avaliador une os
dois conjuntos; nada mais no sistema precisa saber que são dois.

Estrutural não se acumula por concessão: conceder uma ação estrutural a um cargo não libera ninguém,
porque a fonte dela é a titularidade. É o que impede a competência de ter duas portas com regras
diferentes.

O alcance sobre as unidades **abaixo** não é decidido aqui: `has_perm` responde pela unidade do
perfil, e a subárvore é regra de domínio de cada ação que a use (SPEC 007).

**O `ModelBackend` continua instalado.** Ele é quem serve as permissões de staff do admin do Django,
que a SPEC 002 mantém como conveniência de inspeção. Os dois backends convivem: `has_perm` é
verdadeiro se **qualquer** backend disser sim.

**Atalho de superusuário sai de graça.** `PermissionsMixin.has_perm` responde `True` para
superusuário ativo antes de consultar backend algum, e o `Perfil` já herda o mixin. Não se
reimplementa — e é ele que resolve o bootstrap enquanto não há concessão nenhuma gravada.

**A regra fica no domínio; a query, na aplicação.** A consulta traz as concessões da unidade do
perfil e nada mais; quem decide se o cargo bate e se a ação está ativa é o avaliador em
`services/domain/autorizacao/`, sobre DTOs. Os slugs estruturais entram no DTO vindos do registro em
memória (SPEC 001) — o domínio não importa o catálogo do app, recebe o conjunto pronto, como já
recebe as concessões. Filtrar cargo no `.filter()` seria mais curto e
esconderia a regra num queryset — com dezenas de usuários e poucas ações por unidade, o punhado de
linhas a mais não paga esse preço, e é o que torna a regra testável sem banco (§3.3, §9).

**Cache por instância de usuário.** O menu da SPEC 005 vai perguntar por várias ações seguidas. O
backend guarda o conjunto de slugs liberados no próprio objeto de usuário na primeira pergunta —
mesma técnica do `ModelBackend`, com atributo próprio para não colidir com o cache dele. Custo
aceito: concessão alterada só vale no request seguinte, o que é o comportamento normal do Django.

## Peças de referência a compor
- `@services/domain/autorizacao` (SPEC 001) → contratos da ação; o avaliador entra no mesmo submódulo
  e é reexportado pelo `__init__.py`, que só reexporta (§7.2).
- `@apps/competencias/models` (SPEC 002) → `AtribuicaoUnidade` e `Concessao`: origem das linhas
  carregadas.
- `@apps/user_admin/models/user.py` → `Perfil`, que já herda `PermissionsMixin`: o protocolo
  `has_perm` e o atalho de superusuário vêm dele, não se reescrevem.
- `@apps/user_admin/models/user.py` → `Perfil.e_titular` (SPEC `titularidade/001`): a segunda fonte
  é uma leitura de campo, sem consulta nova.
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
    cargo_base_id: int
    cargo_comissao_id: int | None = None
    e_titular: bool = False


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
- Alcance do titular sobre as unidades abaixo: é regra de domínio de cada ação (SPEC 007), não da
  decisão de acesso.
- Impedimento e substituição: perfil afastado continua autorizado até a SPEC que os trate.
- Invalidação imediata de cache após alterar concessão.

## Testes (TDD)
Os quatro primeiros são domínio puro e rodam na suíte padrão. Os dois últimos exercitam o backend
com `Perfil` real e carregam o marker `banco`, declarado em `markers_obrigatorios`.

- `test_avaliador_libera_por_cargo_base_ou_comissao` — concessão que mira o cargo base **ou** o
  cargo em comissão do perfil libera a ação; cargo que não é nenhum dos dois não libera.
- `test_avaliador_exige_unidade_exata` — concessão idêntica numa unidade diferente, inclusive na
  superior, não libera: não há herança pelo organograma.
- `test_avaliador_ignora_acao_inativa` — concessão gravada de ação inativa não entra no resultado.
- `test_avaliador_libera_estrutural_so_para_titular` — a ação estrutural sai liberada para o titular
  sem concessão nenhuma, e não sai para o não-titular nem quando há concessão dela gravada.
- `test_backend_responde_has_perm_e_consulta_uma_vez` — `has_perm` acerta o liberado e o negado, e
  perguntar por várias ações do mesmo perfil não multiplica consultas. *(marker `banco`)*
- `test_backend_nega_anonimo_e_inativo_e_nao_autentica` — anônimo e perfil inativo não recebem nada,
  e `authenticate` devolve `None`. *(marker `banco`)*

## Patches

_Nenhum patch registrado até o momento._
