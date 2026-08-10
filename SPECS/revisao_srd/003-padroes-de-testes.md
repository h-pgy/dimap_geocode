---
spec: revisao_srd/003
versao: v6
atualizado_em: 2026-08-10
testes_tdd: false
implementado: false
changelog:
  - v1: versão inicial
  - v2: incorpora markers, conftest.py global e convenções de execução
  - v3: permite fixtures quando necessário, priorizando builders simples
  - v4: esclarece extensibilidade de markers e exclusão obrigatória da suíte padrão
  - v5: esclarece propósito da seção 'Testes (TDD)' no processo desta SPEC
  - v6: corrige caminho de destino da skill para .claude/skills/ (fonte original)
---

# SPEC revisao_srd/003 — Padrões da suíte de testes

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## Entregável

**Uma skill** a ser criada em `.claude/skills/` (nome sugerido:
`escrever-testes`, caminho `.claude/skills/escrever-testes/SKILL.md` — pois
`.agents` é symlink do `.claude`) que codifica as convenções de estilo, markers
e infraestrutura da suíte de testes do projeto.

**Relação com a skill `test-django-views`:** aquela skill cobre o **smoke test
manual** de views Django/HTMX — validação funcional via `django.test.Client`
após a implementação. Esta skill é **complementar**: cobre a escrita dos
**testes automatizados** (`pytest`) que a SPEC define antes do código (TDD).
As duas não se sobrepõem — uma diz como escrever os testes, a outra diz como
validar views na mão depois.

## User story

Como desenvolvedor do projeto, quero que o estilo, a infraestrutura e as
convenções de execução dos testes sejam uniformes e explícitos, para que
qualquer agente ou colaborador escreva novos testes coerentes com os existentes
— sem precisar de revisão corretiva a cada iteração.

## Critérios de aceite

### Estilo dos arquivos de teste

- [ ] O padrão de testes são funções `test_` no nível do módulo. Classes de
      teste (`class TestFoo`) só existem quando necessário e com justificativa
      prévia aprovada — não são o padrão e não devem ser introduzidas por
      omissão.
- [ ] A árvore de `tests/` espelha `services/` e `apps/` módulo a módulo — um
      `test_foo.py` por `foo.py`, sem arquivos genéricos por feature ou SPEC.
- [ ] Objetos auxiliares priorizam funções builder simples e livres no módulo.
      O uso de `@pytest.fixture` é permitido apenas quando necessário (ex.:
      gerenciamento de ciclo de vida, setup/teardown ou recursos complexos).
- [ ] O nome de cada builder segue o tipo que ele constrói: `_logradouro()`,
      `_codlog()`, `_acao_implementada()` — nunca nomes genéricos como `_impl`.
- [ ] Grupos de testes relacionados são separados por comentários `# ---`.

### Markers

- [ ] Testes unitários rápidos (domínio puro, sem I/O real) **não recebem
      marker** — rodam por padrão com `uv run pytest`.
- [ ] Testes de integração que leem dados reais de `data/` (parquets, WFS)
      recebem `@pytest.mark.integration`. São excluídos do `pytest` padrão via
      `addopts` e rodam com `uv run pytest -m integration`.
- [ ] Testes que exigem banco PostGIS de pé recebem `@pytest.mark.banco` **e**
      `@pytest.mark.django_db` (sem `django_db` o ORM não funciona). São
      excluídos do `pytest` padrão e rodam com `uv run pytest -m banco`.
- [ ] O alias `banco = pytest.mark.banco` é declarado **uma vez** no topo do
      módulo para evitar repetição do path completo em cada teste.
- [ ] A lista de markers não é exaustiva: novos markers podem ser criados se
      identificados como mais adequados durante o desenvolvimento, desde que
      sejam bem justificados e explicitamente excluídos da execução padrão (via
      `addopts`), garantindo que os testes unitários continuem rápidos e
      autocontidos.

### Conftest global

- [ ] `tests/conftest.py` contém apenas fixtures `autouse=True` de
      infraestrutura — nunca builders de domínio. Novas fixtures globais exigem
      justificativa aprovada.
- [ ] A fixture `_isolar_diretorio_de_dados` redireciona `data_dir()` para
      `tmp_path`, **exceto** em testes marcados com `@integration` (que leem os
      parquets reais por definição).
- [ ] A fixture `_resetar_catalogos_singleton` limpa os singletons de catálogos
      (Logradouro, Contribuinte) antes e depois de cada teste para evitar
      vazamento de TTL cache entre testes.

## Contexto e decisões de arquitetura

**Funções soltas por padrão; classes apenas quando justificadas.** A suíte
existente usa funções `test_` no nível do módulo. Classes de teste podem existir
em casos onde o agrupamento traz clareza real que o comentário `# ---` não
alcança, mas exigem justificativa prévia aprovada — não são introduzidas por
omissão nem por conveniência de agrupamento.

**Espelhamento módulo a módulo.** `tests/` reflete `services/` e `apps/`
diretório a diretório: um `test_foo.py` por `foo.py`. Um arquivo genérico por
feature (ex.: `test_catalogo_de_acoes.py` cobrindo vários módulos de uma SPEC)
oculta qual módulo o teste exercita e torna o rastreamento de falhas mais lento.

**Builders nomeados pelo tipo.** O padrão observado em `_logradouro()` e
`_codlog()` é: nome do tipo construído em snake_case com prefixo `_`. Nomes
genéricos (`_impl`, `_make`) não dizem o que é criado e não ajudam na leitura
do teste.

**Priorizar builders simples; fixtures apenas quando necessário.** Builders
livres chamados diretamente em cada teste mantêm o teste autocontido e eliminam
a indireção desnecessária para geração de dados. Fixtures (`@pytest.fixture`) são
permitidas apenas quando estritamente necessárias (ex.: controle de ciclo de
vida, setup/teardown ou recursos complexos).

**Camadas de execução e novos markers.** O `addopts` do `pyproject.toml` exclui
por padrão testes com markers para garantir que `uv run pytest` seja sempre
rápido (domínio puro, sem I/O nem banco). A lista de markers (`integration`,
`banco`) não é exaustiva: novos markers podem ser criados se identificados como
mais adequados durante o desenvolvimento, desde que sejam bem justificados e
obrigatoriamente excluídos da execução padrão para manter os testes unitários
rápidos e autocontidos. Camadas existentes:

| Comando | O que roda | Pré-requisito |
|---|---|---|
| `uv run pytest` | Testes unitários rápidos | Nenhum |
| `uv run pytest -m integration` | Integração com dados reais | Parquets em `data/` |
| `uv run pytest -m banco` | Testes com PostGIS | Banco rodando |

**Alias de marker.** Nos módulos de `apps/` que usam banco, o padrão é declarar
`banco = pytest.mark.banco` uma vez no topo e usar `@banco` nos decoradores.
Isso reduz ruído visual e mantém o import de `pytest` como único ponto de
entrada para markers.

**Conftest mínimo.** O `tests/conftest.py` global é restrito a fixtures de
infraestrutura (`autouse=True`) que todo teste precisa — isolamento de I/O e
reset de singletons. Builders de domínio ficam no módulo de teste que os usa.

## Peças de referência a compor

- `tests/services/utils/test_cache.py` → exemplo canônico de funções soltas e
  seções por comentário.
- `tests/services/domain/roteamento_busca/test_models.py` → exemplo de builders
  `_logradouro()` / `_codlog()`.
- `tests/services/domain/roteamento_busca/test_router.py` → exemplo de helper
  de ação (`rotear()`) nomeado pelo que faz.
- `tests/apps/user_admin/test_seed_cargos.py` → exemplo sem fixtures, com
  builder inline, alias `banco = pytest.mark.banco` e `@pytest.mark.django_db`.
- `tests/services/domain/codlog_match/test_matcher.py` → exemplo de testes
  unitários (funções soltas) + seção de integração (`class
  TestIntegracaoDadosReais` com `@pytest.mark.integration`).
- `tests/conftest.py` → fixtures globais `autouse=True` de infraestrutura.

## Snippets sugeridos

### Builder + teste unitário

```python
# direção de implementação — adaptar conforme necessário

# Builder nomeado pelo tipo construído, com defaults razoáveis.
def _acao_implementada(
    slug: str = "search.exportar_csv",
    url_name: str = "search:exportar_csv",
    partial: str = "_exportar_csv.html",
) -> AcaoImplementada:
    return declarar_acao(slug=slug, ..., url_name=url_name, partial=partial)


# ---------------------------------------------------------------------------
# Seção de testes (comentário obrigatório entre grupos)
# ---------------------------------------------------------------------------


def test_por_slug_devolve_none_para_slug_inexistente() -> None:
    registro = RegistroAcoes(acoes=(_acao_implementada(),))
    assert registro.por_slug("nao.existe") is None
```

### Teste com marker `banco`

```python
import pytest

from apps.user_admin.models import Perfil

banco = pytest.mark.banco


def _perfil(**overrides: object) -> Perfil:
    defaults = {"nome": "Fulano", "rf": "000.000-0"}
    return Perfil(**(defaults | overrides))


# ---------------------------------------------------------------------------
# Validações de modelo (sem banco)
# ---------------------------------------------------------------------------


def test_rf_formatado() -> None:
    assert _perfil().rf_formatado == "000.000-0"


# ---------------------------------------------------------------------------
# Persistência (com banco)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_salvar_e_recuperar() -> None:
    _perfil().save()
    assert Perfil.objects.count() == 1
```

### Seção de integração (no final do arquivo)

```python
@pytest.mark.integration
class TestIntegracaoDadosReais:
    """Roda apenas com: uv run pytest -m integration"""

    def test_matcher_encontra_logradouro_real(self) -> None:
        # Usa catálogos reais carregados de data/ (fixture global
        # _isolar_diretorio_de_dados é bypassada pelo marker).
        ...
```

## Fora de escopo

- Migração retroativa de arquivos de teste já existentes que não seguem o
  padrão (ex.: uso de classes em `test_numero.py`) — a norma vale para testes
  novos; backfill só se o arquivo for reescrito por outro motivo.

## Testes (TDD)

*(Esta é a seção padrão do template de SPECs do projeto, onde normalmente se
listam os testes unitários/integrados a serem escritos antes da implementação do
código).*

**Não aplicável para o entregável desta SPEC:** o resultado desta SPEC é uma
skill de convenções e documentação (`.claude/skills/escrever-testes/SKILL.md`),
e não código executável de software. Portanto, não há testes `pytest` prévios a
serem escritos para esta SPEC em si. Ela é dada como implementada quando a skill
estiver redigida e disponibilizada no repositório.

## Patches

_Nenhum patch registrado até o momento._
