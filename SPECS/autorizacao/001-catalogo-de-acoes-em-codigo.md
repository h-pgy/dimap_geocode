---
spec: autorizacao/001
versao: v2
atualizado_em: 2026-08-11
testes_tdd: true
implementado: true
changelog:
  - v1: versão inicial
  - v2: declaracao.py dividido em schemas.py (contratos) e utils.py (instanciar_acao)
---

# SPEC autorizacao/001 — Catálogo de ações em código

- [x] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como desenvolvedor da plataforma, quero declarar em código, num único lugar curado, quais rotinas
do sistema são **ações administrativas** sujeitas a concessão de competência, para que essa lista
seja versionada, revisável em code review e consultável pelo resto do sistema — e para que uma
rota que apenas exige login não seja confundida com um ato administrativo.

## Critérios de aceite
- [ ] Existe um contrato de domínio que descreve **conceitualmente** uma ação — identidade, nome,
      nome curto, tooltip e as variantes de ícone que ela possui — e recusa ação sem nome, sem
      tooltip ou com slug fora do padrão.
- [ ] Existe um contrato de aplicação que **compõe** o contrato conceitual com a implementação no
      Django (rota por nome e partial do item de menu); o contrato conceitual não conhece rota nem
      template.
- [ ] O registro de ações é uma coleção **explícita e curada**, montada num único módulo sem
      descoberta automática — e é **consultável por slug** e **enumerável por inteiro**.
- [ ] O catálogo canônico tem **uma instância por processo**, acessada por uma **porta única**; a
      montagem não é acessível de fora.
- [ ] O sistema **recusa subir** (system check do Django) quando o registro tem slug duplicado,
      quando o prefixo do slug não corresponde a um app instalado, quando uma variante de ícone
      declarada não tem arquivo correspondente em disco, ou quando o `url_name` de uma ação não
      resolve.

## Contexto e decisões de arquitetura

Esta SPEC entrega só o **catálogo**: quais ações existem e como o sistema as descreve. Nada de
banco, autorização, menu ou rota protegida — isso vem nas SPECs seguintes do épico.

**Dois contratos, por composição.** Uma coisa é *o que a ação é* (conceito), outra é *como ela está
pendurada no Django* (implementação). Composição em vez de herança porque a herança produziria um
objeto só em runtime e a distinção sumiria; com composição, o conceitual existe separado — e é dele
que a SPEC 002 projeta no banco o que as telas de concessão precisam consultar. O conceitual mora em
`services/domain/`, sem Django; `url_name` e `partial` ficam na camada de aplicação porque são a
resposta de "como isso está montado na interface" (§3.3).

**Slug com prefixo de app.** O slug é `<app>.<nome>` — o mesmo formato `app_label.codename` do
Django, o que faz o `has_perm` da SPEC 003 cair na convenção em vez de fugir dela, e evita colisão
entre ações de apps diferentes por nome parecido. O prefixo não é decorativo: o check confere que
ele corresponde a um app instalado, senão um typo viraria namespace fantasma. Em disco os dois
segmentos viram dois níveis de pasta, para não deixar ponto em nome de diretório.

O slug é chave em três lugares — registro em código, tabela projetada (SPEC 002) e caminho dos
ícones. Custo aceito: renomear é mover pasta e desativar/recriar a linha no banco.

Para o domínio o prefixo é só um segmento de namespace; quem sabe que ele é um app do Django é o
check, na camada de aplicação (§3.3).

**Registro curado, sem `autodiscover`.** Descoberta automática apagaria justamente a distinção que
esta SPEC existe para tornar visível — ver o próprio perfil exige login, ver o mapa é aberto, e
nenhum dos dois é ação. Só entra no registro o que precisa de concessão. O custo é lembrar de
inscrever a ação nova; o check de `url_name` e de ícone é o que torna esquecimento barulhento.

O registro é **imutável e montado por uma fábrica privada**, e cada app declara a sua ação por
`declarar_acao()`, que achata a composição no ponto de escrita — o app escreve plano, o contrato
guarda aninhado. São **dois módulos** por causa do ciclo: o da declaração é importado pelos apps de
ação e não importa nenhum; o do registro importa todos e não é importado por ninguém.

**Uma instância por processo, e uma porta só.** A montagem é privada e o catálogo se expõe como uma
única instância no nível do módulo — o mesmo idioma dos catálogos de `services/domain`. Duas portas
públicas, uma fábrica e uma constante, seriam o convite para versões divergentes circulando no mesmo
processo. Frozen é o que torna a instância compartilhada segura de aliasar.

Isso vale para o **canônico**, não para o tipo: `RegistroAcoes` continua construtível à vontade, e é
assim que os testes montam registros próprios. Proibir a construção quebraria a testabilidade dos
checks, que recebem o registro por argumento justamente para não depender do global.

**Ícone: a ação declara variante, não caminho.** O contrato conceitual diz *quais* variantes
possui (`PEQUENO`, `GRANDE`); a localização é convenção resolvida fora do domínio. Duas variantes
bastam — a diferença entre elas é de tamanho óptico (um glifo de 20px carrega menos detalhe que um
de 48px), que é propriedade do desenho, não do contexto de exibição. Nomear por uso (`LISTA`,
`DESTAQUE`) amarraria a ação ao menu — descartado.

**Validação por system check.** Convenção sem verificação quebra no render, e `{% static %}` não
confere existência. O framework de checks do Django roda em `runserver`, `check` e `migrate`, o que
faz o SVG esquecido aparecer antes do navegador — e dispensa um management command próprio. As
funções de validação recebem o registro como argumento, e o check registrado só passa o registro
global: é o que as torna testáveis sem mexer em estado de módulo.

## Peças de referência a compor
- `@apps/search/views.py` → `REGISTRO_SECOES`: precedente do registro tipado e explícito em módulo;
  seguir a mesma natureza (enumeração no código, sem descoberta automática).
- `django.core.checks` → framework de system checks: usar em vez de escrever um command de
  validação.
- `django.contrib.staticfiles.finders` → `find()`: localizar o SVG honrando `STATICFILES_DIRS`, em
  vez de montar caminho absoluto na mão.
- `@services/domain/__init__.py`: o submódulo novo reexporta seus contratos pelo `__init__.py`, como
  os demais domínios — e o `__init__` só reexporta (§7.2).

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md

# services/domain/autorizacao/contratos.py
PADRAO_SLUG = r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$"


class VarianteIcone(StrEnum):
    PEQUENO = "pequeno"
    GRANDE = "grande"


class Acao(BaseModel):
    """O que a ação é. Sem rota, sem template, sem Django."""

    model_config = ConfigDict(frozen=True)

    # `<app>.<nome>`: identidade única no sistema e origem do caminho dos ícones em disco.
    slug: str = Field(pattern=PADRAO_SLUG)
    nome: str = Field(min_length=1)
    tooltip: str = Field(min_length=1)
    nome_curto: str | None = None
    variantes_icone: frozenset[VarianteIcone] = frozenset()
```

```python
# apps/competencias/declaracao.py — importado pelos apps de ação; não importa nenhum deles.
class AcaoImplementada(BaseModel):
    model_config = ConfigDict(frozen=True)

    acao: Acao
    # Rota por nome: importar a view acoplaria a ação ao app do menu e fecharia um ciclo.
    url_name: str
    partial: str


class RegistroAcoes(BaseModel):
    model_config = ConfigDict(frozen=True)

    acoes: tuple[AcaoImplementada, ...]

    def todas(self) -> tuple[AcaoImplementada, ...]: ...

    def por_slug(self, slug: str) -> AcaoImplementada | None: ...


def declarar_acao(
    slug: str,
    nome: str,
    tooltip: str,
    url_name: str,
    partial: str,
    nome_curto: str | None = None,
    variantes_icone: frozenset[VarianteIcone] = frozenset(),
) -> AcaoImplementada:
    """Achata a composição no ponto de declaração: o app da ação escreve plano, o contrato guarda
    aninhado."""
    ...
```

```python
# apps/competencias/registro.py — o único módulo que importa os apps de ação.
def _construir_registro() -> RegistroAcoes:
    """Ponto único de montagem: inscrever ação é acrescentar uma linha aqui.
    Privado — quem consome o catálogo entra por `obter_registro()`."""
    # Nasce vazio: a primeira ação chega junto da SPEC que a implementa.
    return RegistroAcoes(acoes=())


# Porta única do catálogo: uma instância por processo, no idioma dos catálogos de services/domain.
REGISTRO = _construir_registro()
```

```python
# apps/competencias/checks.py
# Os dois segmentos do slug viram dois níveis de pasta: ponto em nome de diretório é ruim de viver.
GABARITO_CAMINHO_ICONE = "acoes/{app}/{nome}/icones/{variante}.svg"


def validar_registro(registro: RegistroAcoes) -> list[Error]:
    """Recebe o registro por argumento — o check registrado só injeta o global."""
    ...
```

## Fora de escopo
- **Nenhuma ação real é registrada nesta SPEC.** O registro nasce vazio; a primeira ação inscrita é
  a de conceder competência, que chega junto da sua tela.
- Projeção da ação no banco e sincronização (SPEC 002).
- Atribuição da unidade, concessão ao cargo e o admin clássico (SPEC 002).
- Avaliador de competência, backend de autorização e `has_perm` (SPEC 003).
- Proteção de rota e registro de execução do ato (SPEC 004).
- Contrato de menu e router (SPEC 005).
- Resolvedor de ícone, cache e átomo do design system (SPEC 006) — aqui só se verifica que o
  arquivo existe, não se renderiza nada.
- Impedimento, substituição, concessão por natureza de cargo e concessão nominal.

## Testes (TDD)
Todos rodam na suíte padrão — sem banco, sem marker. Como o registro global nasce vazio, os testes
montam **registros próprios a partir de ações fictícias** vindas de fixtures, e é a fixture que
varia por caso (slug repetido, ícone ausente, rota inexistente).

- `test_acao_recusa_contrato_incompleto` — ação sem nome, sem tooltip ou com slug fora do padrão
  `<app>.<nome>` é rejeitada na construção do contrato.
- `test_registro_consulta_por_slug_e_enumera` — o registro devolve a ação pelo slug, `None` para
  slug inexistente, e enumera todas as inscritas.
- `test_check_acusa_slug_duplicado` — duas ações com o mesmo slug produzem erro de check.
- `test_check_acusa_prefixo_de_app_inexistente` — slug cujo prefixo não é um app instalado produz
  erro de check.
- `test_check_acusa_variante_de_icone_sem_arquivo` — variante declarada sem SVG correspondente
  produz erro de check; variante não declarada não é cobrada.
- `test_check_acusa_url_name_que_nao_resolve` — `url_name` inexistente produz erro de check.

## Patches

### Patch 001 (v2) — `declaracao.py` dividido em `schemas.py` + `utils.py`

Rename mecânico, sem mudança de comportamento. `apps/competencias/declaracao.py` misturava os
contratos Pydantic (`AcaoImplementada`, `RegistroAcoes`) com a função que os monta — separados por
responsabilidade:

- `apps/competencias/schemas.py` — só os contratos: `AcaoImplementada`, `RegistroAcoes`.
- `apps/competencias/utils.py` — `instanciar_acao()` (era `declarar_acao()`), que importa de
  `.schemas`.

`registro.py` e `checks.py` passam a importar `RegistroAcoes` de `.schemas`. Nos testes,
`test_declaracao.py` foi dividido do mesmo jeito — `test_schemas.py` (consulta/enumeração do
registro) e `test_utils.py` (composição aninhada) — e `test_checks.py` importa de `.schemas`/
`.utils`.
