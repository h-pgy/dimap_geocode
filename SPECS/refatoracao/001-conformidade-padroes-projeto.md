---
spec: refatoracao/001
versao: v1
atualizado_em: 2026-08-25
testes_tdd: false
implementado: false
changelog:
  - v1: versão inicial
---

# SPEC refatoracao/001 — Conformidade com Padrões de Código do Projeto

## 1 · User story
**Refatoração** — adequação do repositório aos padrões inegociáveis do [CLAUDE.md](../../CLAUDE.md), eliminando erros de linter (`ruff`), inconsistências de tipagem (`mypy`), nomenclatura de partials e desvios de encapsulamento.

## 2 · Condições de pronto
- [ ] A execução de `uv run ruff check .` e `uv run mypy .` conclui com zero erros e avisos.
- [ ] Partials de busca e de validação em `templates/` possuem o prefixo obrigatório `_` e respondem corretamente nos pontos de chamada.
- [ ] Partials do app de mapa estão organizados sob `templates/mapping/partials/`.
- [ ] Classes nos templates HTML não utilizam o modificador `!` do Tailwind (gerador de `!important`).
- [ ] O modelo [`GeoJsonProperties`](#3--domínio) é reexportado por `services.domain.geometry` e consumido pelas views sem importação de submódulos internos.
- [ ] Parâmetros de `settings` em views e comandos de gerenciamento são reextraídos para constantes no topo do módulo.
- [ ] A suíte de testes isola todos os singletons de catálogo em memória, incluindo o catálogo de codlogs.

## 3 · Domínio
A refatoração não introduz novas entidades de negócio, atuando sobre a conformidade de contratos e interfaces existentes.

Consome:
- [`GeoJsonProperties`](../geocodificacao/001-geocodificador-logradouro.md) — contrato de propriedades GeoJSON serializadas para o frontend.
- [`CodlogCatalog`](../infraestrutura/003-catalogo-memoria.md) — singleton de lookup em memória de logradouros por código.

```python
class GeoJsonProperties(BaseModel):
    """Contrato de propriedades injetadas na Feature GeoJSON serializada."""
    tipo: str
    rotulo: str
    cor: str | None = None
```

## 4 · Fora de escopo
- Models do Django seguem as convenções do framework na camada de persistência (`is_active`, `is_staff`, `is_superuser`, etc.) — o que é válido e esperado para o mapeamento relacional.
- Renomeação do campo de persistência `e_titular` para `eh_titular` no model `Perfil` — mantido fora deste escopo por exigir migração de banco dedicada no épico `user_admin`.
- Renomeação de colunas em parquets legados — mantido fora deste escopo para evitar reexecução de pipeline WFS no ciclo de refatoração.

## 5 · Peças de referência a compor
- `@services/domain/geometry` → `GeoJsonProperties`: contrato GeoJSON de saída.
- `@services/domain/codlog_match` → `CodlogCatalog`: catálogo em memória com `resetar_instancia()`.
- `@apps/core/middleware` → `PydanticValidationMiddleware`: interceptador global de `ValidationError`.
- Skills: `specs`, `catalogos-lookup`, `componentes-frontend`.

## 6 · Snippets

**`services/domain/geometry/__init__.py`**
```python
# Reexportação obrigatória (§7.2 do CLAUDE.md): views consomem o pacote, não models.py direto.
from .models import GeoFeature, GeoJsonProperties, LineGeometry, PointGeometry, PolygonGeometry
from .serializers import to_geojson_feature_collection

__all__ = [
    "GeoFeature",
    "GeoJsonProperties",
    "LineGeometry",
    "PointGeometry",
    "PolygonGeometry",
    "to_geojson_feature_collection",
]
```

**`tests/conftest.py`**
```python
# Reset de TODOS os catálogos singletons antes e após cada teste, evitando vazamento de estado.
from services.domain.codlog_match import CodlogCatalog
from services.domain.contribuinte_match import ContribuinteCatalog
from services.domain.logradouros_match import LogradouroCatalog


@pytest.fixture(autouse=True)
def _resetar_catalogos_singleton() -> Generator[None, None, None]:
    CodlogCatalog.resetar_instancia()
    LogradouroCatalog.resetar_instancia()
    ContribuinteCatalog.resetar_instancia()
    yield
    CodlogCatalog.resetar_instancia()
    LogradouroCatalog.resetar_instancia()
    ContribuinteCatalog.resetar_instancia()
```

**`apps/user_admin/cadastro.py`**
```python
# Constantes de settings reextraídas no topo do módulo (§7.1 do CLAUDE.md).
EMAIL_ENVIO_HABILITADO: bool = settings.EMAIL_ENVIO_HABILITADO
ENFORCE_PREFEITURA_EMAIL: bool = settings.ENFORCE_PREFEITURA_EMAIL
```

## 7 · Caveats
A camada de persistência (Django models) mantém as convenções nativas do framework (`is_active`, `is_staff`), que são legítimas para mapeamento relacional. No domínio puro (`services/domain/`), a regra é estritamente em português com `eh_`. A coluna de banco `e_titular` e parquets existentes são mantidos inalterados para isolar este ciclo de refatoração sem exigir migrações manuais do banco ou reprocessamentos de pipeline WFS.

## 8 · Testes (TDD)
- `test_geometry_reexporta_geojson_properties` — confirma que `GeoJsonProperties` está acessível em `services.domain.geometry`.
- `test_reset_catalogos_singleton_limpa_codlog_catalog` — verifica que o fixture `autouse` limpa o singleton `CodlogCatalog`.
- `test_partials_possuem_prefixo_underscore` — varre os diretórios `templates/*/partials/` e falha se algum template não iniciar com `_`.
