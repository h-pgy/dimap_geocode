---
name: escrever-testes
description: "Padrões, convenções de estilo e infraestrutura da suíte de testes automatizados (pytest/TDD) do DIMAP GeoCoder. Use SEMPRE que for escrever testes unitários ou integrados em tests/, criar builders/fixtures ou configurar markers (integration, banco). Complementar à skill test-django-views."
---

# Padrões da suíte de testes — `pytest` e TDD

Convenções de estilo, infraestrutura, organização de diretórios e camadas de execução
dos testes automatizados do DIMAP GeoCoder.

---

## 1. Quando usar e relação com `test-django-views`

No DIMAP GeoCoder, o desenvolvimento é guiado por testes (**TDD**, §9 do `CLAUDE.md`):
a SPEC define **poucos e essenciais** testes observáveis antes de qualquer linha de
código de produção.

- **Esta skill (`escrever-testes`):** cobre como estruturar e escrever a **suíte de testes
  automatizados (`pytest`)** em `tests/`, cobrindo domínio (`services/`), regras de negócio,
  persistência (`apps/`) e integração.
- **Skill complementar (`test-django-views`):** cobre o **smoke test manual** de views
  Django/HTMX via `django.test.Client` (`manage.py shell -c`) após a implementação.

As duas não se sobrepõem: uma define como automatizar a verificação contínua do comportamento;
a outra valida interativamente o partial HTML e a resposta HTTP da view.

---

## 2. Regras inegociáveis de estilo e estrutura

### 2.1 Funções soltas no nível do módulo como padrão soberano
- O padrão obrigatório para testes no projeto são **funções `test_<comportamento>()` no nível do módulo**.
- Classes de teste (`class TestFoo:`) **só existem quando estritamente necessárias e com justificativa prévia aprovada** (ex.: agrupamento de testes de integração com setup compartilhado ou isolamento contextual forte). Não devem ser introduzidas por conveniência ou hábito.

### 2.2 Espelhamento módulo a módulo
- A árvore `tests/` espelha **módulo a módulo** as pastas `services/` e `apps/`:
  - `services/domain/logradouros_match/matcher.py` → `tests/services/domain/logradouros_match/test_matcher.py`
  - `apps/user_admin/seeds/cargos.py` → `tests/apps/user_admin/test_seed_cargos.py`
- **Proibido criar arquivos genéricos por feature ou SPEC** (ex.: `test_spec_003.py`, `test_catalogo_de_acoes.py` cobrindo múltiplos módulos). Arquivos agregadores obscurecem a unidade testada e degradam a rastreabilidade.

### 2.3 Priorizar builders simples; fixtures apenas quando indispensáveis
- Objetos de teste e DTOs de entrada devem ser criados por **funções builder simples e livres no próprio módulo de teste**.
- O uso de `@pytest.fixture` é restrito a casos de real necessidade de **gerenciamento de ciclo de vida, setup/teardown ou recursos complexos** (ex.: instância de matcher injetada com catálogo fake). Para dados puros, prefira builders normais.

### 2.4 Nomenclatura de builders pelo tipo construído
- O nome do builder **sempre** segue o tipo/entidade que ele produz, com prefixo `_`:
  - `_logradouro()`, `_codlog()`, `_perfil()`, `_acao_implementada()`.
- **Nunca use nomes genéricos ou vagos**, como `_make()`, `_impl()`, `_mock()`, `_build()`.

### 2.5 Seções por comentários delimitadores
- Agrupe testes relacionados usando o separador padrão de 75 caracteres com o título da seção:

```python
# ---------------------------------------------------------------------------
# Validação do contrato de entrada
# ---------------------------------------------------------------------------


def test_rejeita_codlog_vazio() -> None: ...
```

---

## 3. Camadas de execução e markers

O `addopts` no `pyproject.toml` exclui markers pesados da execução padrão para manter `uv run pytest` instantâneo (domínio puro, em memória).

| Camada | Comando | O que roda | Pré-requisito |
|---|---|---|---|
| **Unitários** | `uv run pytest` | Domínio puro, validações, fakes em memória | Nenhum (sem I/O real, sem banco) |
| **Integração** | `uv run pytest -m integration` | Leitura de dados reais (`data/*.parquet`, WFS) | Parquets presentes em `data/` |
| **Banco** | `uv run pytest -m banco` | Persistência com PostGIS / ORM Django | Banco PostGIS de pé (`docker compose`) |

### 3.1 Testes unitários rápidos (sem marker)
- Testes de lógica pura, validações Pydantic, roteadores e matchers com dados sintéticos **não recebem marker**.
- Rodam automaticamente em segundos com `uv run pytest`.

### 3.2 Marker `integration`
- Decorador: `@pytest.mark.integration`.
- Usado para testes que leem arquivos reais em `data/` ou consultam endpoints WFS reais.
- A fixture global `_isolar_diretorio_de_dados` em `tests/conftest.py` **não redireciona** `data_dir()` quando este marker está presente.
- Costuma ser agrupado em uma classe dedicada ao final do módulo: `class TestIntegracaoDadosReais:`.

### 3.3 Marker `banco` e `@pytest.mark.django_db`
- Todo teste que acessa banco PostGIS / ORM Django precisa receber **ambos**:
  1. `@pytest.mark.banco` (para ser excluído da suíte unitária rápida padrão)
  2. `@pytest.mark.django_db` (para que o `pytest-django` libere o acesso ao banco de testes isolado)
- **Banco de testes obrigatório e teardown:** testes de banco rodam **estritamente sobre o banco de testes efêmero gerenciado pelo Django/pytest-django** (ex.: `test_dimap_geocode`), **nunca** sobre o banco de dados de desenvolvimento ou produção real. Qualquer dado persistido deve sofrer **teardown completo** garantido pela transação/limpeza do `django_db`.
- **Alias obrigatório:** declare `banco = pytest.mark.banco` uma vez no topo do módulo após os imports para reduzir ruído visual nos decoradores:

```python
import pytest

from apps.user_admin.models import CargoBase

banco = pytest.mark.banco


@banco
@pytest.mark.django_db
def test_persistencia_cargo() -> None:
    cargo = CargoBase.objects.create(nome="Auditor", sigla="AFTM")
    assert cargo.pk is not None
```

### 3.4 Extensibilidade de markers
- A lista de markers (`integration`, `banco`) não é fechada. Novos markers podem ser introduzidos durante o desenvolvimento se houver uma nova categoria de teste com requisitos específicos de ambiente ou custo de execução.
- **Regra obrigatória:** qualquer novo marker **deve ser registrado em `pyproject.toml` e explicitamente excluído de `addopts`** (`addopts = "-m 'not integration and not banco and not novo_marker'"`), assegurando que a execução padrão continue pura e rápida.

---

## 4. Infraestrutura, `tests/conftest.py` global e isolamento de persistência

O arquivo `tests/conftest.py` na raiz é reservado **exclusivamente para fixtures de infraestrutura com `autouse=True`** aplicáveis a toda a suíte.

### 4.1 Isolamento estrito de disco e banco (sem efeitos colaterais)
Nenhum teste pode gerar efeitos colaterais persistentes no ambiente local ou no repositório:
- **Disco (I/O estritamente temporário):** É terminantemente proibido salvar arquivos na árvore permanente do projeto (`data/`, `static/`, etc.). Qualquer escrita necessária (parquets sintéticos, seeds simuladas) deve usar **`tmp_path` do pytest** para ser destruída automaticamente no teardown pós-teste.
- **Integração read-only:** Testes `@pytest.mark.integration` leem os parquets reais de `data/` **apenas como leitura (read-only)** — nunca gravam nem alteram nada no diretório de dados oficial.
- **Banco de testes isolado:** Testes de banco devem rodar no banco de testes do Django via `@pytest.mark.django_db`, com rollback/teardown garantido entre execuções.

### 4.2 Fixtures globais existentes
1. **`_isolar_diretorio_de_dados` (`autouse=True`):**
   - Redireciona chamadas a `services.utils.io.config.data_dir()` para o `tmp_path` do pytest durante testes unitários.
   - **Bypass automático:** se o teste contiver o marker `integration` (`request.node.get_closest_marker("integration")`), o diretório original `data/` é preservado para leitura.
2. **`_resetar_catalogos_singleton` (`autouse=True`):**
   - Executa `LogradouroCatalog.resetar_instancia()` e `ContribuinteCatalog.resetar_instancia()` antes e depois de cada teste para evitar contaminação do cache TTL entre execuções.

### 4.3 Proibição no `conftest.py` global
- **Nunca coloque builders, dados de domínio ou fixtures de modelos de negócio em `tests/conftest.py`**.
- Cada módulo de teste declara os seus próprios builders localmente.

### 4.4 Fakes de Catálogos (Bypass de Singleton)
- Os catálogos de domínio implementam singleton via `__new__` sobre a classe exata.
- Para criar catálogos falsos em testes com dados controlados sem tocar em disco, crie uma **subclasse** do catálogo dentro do módulo de teste:

```python
import pandas as pd
from services.domain.codlog_match.catalog import CodlogCatalog

class FakeCodlogCatalog(CodlogCatalog):
    """Subclasse escapa do singleton (o bypass do __new__ é só para a classe base)."""

    def __init__(self, dados: dict[str, list[object]]) -> None:
        self._dados = dados

    @property
    def logradouros(self) -> pd.DataFrame:
        return pd.DataFrame(self._dados)
```

---

## 5. Exemplos canônicos de implementação

### 5.1 Teste unitário de domínio com builder local

```python
import pytest
from pydantic import ValidationError

from services.domain.roteamento_busca import CodlogParse, EnderecoLoteParse, LogradouroParse


def _logradouro(tipo: str = "avenida", nome: str = "paulista") -> LogradouroParse:
    return LogradouroParse(tipo_logradouro=tipo, nome=nome)


def _codlog(codlog: str = "12345", dv: str = "0") -> CodlogParse:
    return CodlogParse(codlog=codlog, digito_verificador=dv)


# ---------------------------------------------------------------------------
# Exclusividade e validação do modelo
# ---------------------------------------------------------------------------


def test_aceita_somente_logradouro() -> None:
    parse = EnderecoLoteParse(logradouro=_logradouro(), numero_bruto="100")
    assert parse.logradouro is not None
    assert parse.codlog is None


def test_rejeita_ambos_preenchidos() -> None:
    with pytest.raises(ValidationError):
        EnderecoLoteParse(logradouro=_logradouro(), codlog=_codlog(), numero_bruto="100")
```

### 5.2 Teste com persistência (`banco`) e builder com overrides

```python
import pytest
from apps.user_admin.models import Perfil

banco = pytest.mark.banco


def _perfil(**overrides: object) -> Perfil:
    defaults = {"nome": "Fulano da Silva", "rf": "123.456-7"}
    return Perfil(**(defaults | overrides))


# ---------------------------------------------------------------------------
# Propriedades de domínio do modelo (sem banco)
# ---------------------------------------------------------------------------


def test_rf_formatado() -> None:
    assert _perfil().rf_formatado == "123.456-7"


# ---------------------------------------------------------------------------
# Persistência e consultas no banco
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_salvar_e_consultar_perfil() -> None:
    perfil = _perfil(rf="999.888-7")
    perfil.save()
    assert Perfil.objects.filter(rf="999.888-7").exists()
```

### 5.3 Seção de integração com dados reais (ao final do módulo)

```python
# ---------------------------------------------------------------------------
# Integração com dados reais
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIntegracaoDadosReais:
    """Roda apenas com: uv run pytest -m integration"""

    def test_matcher_encontra_logradouro_real(self) -> None:
        from services.domain.codlog_match import match_codlog, CodlogMatchInput

        resultado = match_codlog(CodlogMatchInput(input_codlog="00001"))
        assert len(resultado) > 0
        assert resultado[0].codlog == "00001"
```

---

## 6. Peças de referência no repositório

Consulte estes arquivos como modelo canônico ao escrever novos testes:

- `tests/services/utils/test_cache.py` → Funções soltas no módulo, separadores `# ---`, sem classes.
- `tests/services/domain/roteamento_busca/test_models.py` → Builders `_logradouro()` e `_codlog()`.
- `tests/services/domain/roteamento_busca/test_router.py` → Helper de ação `rotear()` e `achar()` expressivos.
- `tests/apps/user_admin/test_seed_cargos.py` → Uso correto de `banco = pytest.mark.banco`, `@pytest.mark.django_db` e builders inline.
- `tests/services/domain/codlog_match/test_matcher.py` → Testes unitários com fake in-memory + classe `TestIntegracaoDadosReais` isolada.
- `tests/conftest.py` → Exemplo de fixtures de infraestrutura `autouse=True`.

---

## 7. O que NÃO fazer (Anti-patterns)

- ❌ **Não agrupar testes em classes por padrão** (`class TestUsuario:`). Use funções soltas separadas por `# ---`.
- ❌ **Não criar arquivos genéricos como `test_actions.py` ou `test_spec_005.py`**. Cada arquivo em `tests/` espelha um arquivo correspondente em `services/` ou `apps/`.
- ❌ **Não nomear builders com termos genéricos** (`_make()`, `_impl()`, `_setup()`). Use sempre o nome da entidade (`_acao()`, `_perfil()`).
- ❌ **Não poluir `tests/conftest.py` com builders ou regras de domínio**. Fixtures globais são apenas para isolamento de I/O e reset de singletons.
- ❌ **Não esquecer `@pytest.mark.django_db` em testes com `@banco`**. Sem o `django_db`, o pytest bloqueará chamadas ao ORM.
- ❌ **Não rodar testes contra o banco de desenvolvimento/real nem deixar registros sem teardown**. Use sempre `@pytest.mark.django_db` para operar no banco de testes efêmero.
- ❌ **Não salvar arquivos fora de `tmp_path`**. É estritamente vedado gravar dados na árvore permanente do projeto (`data/`, `static/`); parquets em `data/` são acessados por `@integration` apenas em modo read-only.
- ❌ **Não realizar chamadas de rede ou leituras de disco reais em testes unitários**. Se precisa de arquivo real, marque com `@pytest.mark.integration`.
- ❌ **Não usar `from __future__ import ...`** (Python 3.14 nativo).
- ❌ **Não testar getters triviais, DTOs sem lógica ou buscar 100% de cobertura artificial**. Foque nos critérios de aceite observáveis e casos de borda reais.
