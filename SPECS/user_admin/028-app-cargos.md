---
spec: user_admin/028
versao: v1
atualizado_em: 2026-09-04
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC user_admin/028 — App `cargos`: o catálogo ganha dono

## 1 · User story
**Refatoração** — o catálogo de cargos passa a ter app próprio, que é o dono de domínio de onde
pendem os atos de cargo da SPEC user_admin/029.

## 2 · Condições de pronto
- [ ] `CargoBase` e `CargoComissao` respondem por **`apps.cargos`**, e nenhum módulo do projeto
      importa cargo de `apps.user_admin`.
- [ ] As tabelas passam a se chamar `cargos_cargobase` e `cargos_cargocomissao`, com **as linhas
      gravadas e as FKs de `Perfil`, `Concessao` e `Execucao` intactas** — nada é recriado.
- [ ] `seed_cargos` roda pelo app novo, sobre o mesmo `data/seed/cargos.json`, e continua só criando
      o que falta.
- [ ] A suíte existente passa inteira, inclusive `-m banco`, com alteração **só de import** — e do
      caminho dos arquivos de teste de cargo, movidos para `tests/apps/cargos/` com o conteúdo
      intacto.
- [ ] `manage.py check` e `makemigrations --check` ficam limpos depois do porte: nenhuma migração
      pendente e nenhum system check derrubado.

## 3 · Domínio

Nenhum campo, constraint, validação ou regra muda. Os dois models mudam de app — e, com ele, de
tabela.

**`apps/cargos/models/cargos.py`**

```python
# ALTERADO nesta SPEC: `CargoBase` e `CargoComissao` (SPEC user_admin/001) mudam de app. Campos,
# `clean()`, as duas CheckConstraint de alta_administracao × nivel × e_chefia e as propriedades
# `natureza` e `padrao` vêm inteiros, como estão. O `db_table` não é declarado: o nome padrão do
# app novo (`cargos_cargocomissao`) é o que a migração renomeia.
class CargoBase(models.Model): ...
class CargoComissao(models.Model): ...
```

A dependência é de mão única: `apps.user_admin` importa `apps.cargos` (é `Perfil` que aponta para o
cargo), nunca o contrário.

- [`CargoBase` e `CargoComissao`](001-models-perfil-cargos-unidade.md) — esta SPEC pergunta a eles
  só onde moram.
- [Seed dos cargos](009-seed-cargos.md) — esta SPEC pergunta de que app o comando parte; o arquivo,
  a chave natural e o "só cria o que falta" seguem como estão.

## 4 · Fora de escopo
- `extinto_em`, os quatro atos, a listagem e a marca de cargo extinto — SPEC user_admin/029.
- Mover `Impedimento`, `Substituicao` ou qualquer outro model de `user_admin` — sem dono ainda.
- Registrar os cargos no Django admin — sem dono ainda; hoje nenhum dos dois está lá.

## 5 · Peças de referência a compor
- `@apps/user_admin/seeds/cargos.py` e `@apps/user_admin/management/commands/seed_cargos.py` →
  carregador e comando: **movidos**, não reescritos.
- `@apps/user_admin/models/cargos.py` → os dois models: movidos com `clean()`, constraints e
  propriedades intactos.
- `@tests/apps/user_admin/models/test_cargos.py` e `@tests/apps/user_admin/test_seed_cargos.py` →
  movidos para `tests/apps/cargos/`, com o conteúdo intacto.
- Skills: `seeds`, `escrever-testes`, `management-commands`.

## 6 · Snippets

**`apps/cargos/migrations/0001_initial.py` e `apps/user_admin/migrations/00NN_*.py`** — três passos,
nesta ordem. É a única parte do porte que toca banco com estado.

```python
# 1) user_admin: a tabela é renomeada DE VERDADE, com o model ainda morando em user_admin. É a
# única operação de banco de todo o porte — daqui para a frente, só estado.
operations = [
    migrations.AlterModelTable(name="cargobase", table="cargos_cargobase"),
    migrations.AlterModelTable(name="cargocomissao", table="cargos_cargocomissao"),
]

# 2) cargos/0001_initial: o model nasce no app novo SÓ no estado — a tabela dele já existe, com o
# nome que o passo 1 deu. `CreateModel` de verdade tentaria criar tabela por cima.
operations = [
    migrations.SeparateDatabaseAndState(
        state_operations=[
            migrations.CreateModel(name="CargoBase", fields=[...]),
            migrations.CreateModel(name="CargoComissao", fields=[...], options={...}),
        ],
        database_operations=[],
    ),
]

# 3) user_admin: os models somem do estado do app velho e as FKs passam a apontar para `cargos.*`.
# Também só estado: a coluna `cargo_base_id` continua a mesma, e nada no banco muda.
operations = [
    migrations.SeparateDatabaseAndState(
        state_operations=[
            migrations.AlterField(model_name="perfil", name="cargo_base", field=...),
            migrations.AlterField(model_name="perfil", name="cargo_comissao", field=...),
            migrations.DeleteModel(name="CargoBase"),
            migrations.DeleteModel(name="CargoComissao"),
        ],
        database_operations=[],
    ),
]
# `apps.competencias` (Concessao, Execucao) recebe a mesma migração de estado, com as suas FKs.
```

**`config/settings.py`**

```python
INSTALLED_APPS = [
    ...
    # Antes de `user_admin`: é `Perfil` que aponta para o cargo, e a leitura da lista deve seguir a
    # direção da dependência.
    "apps.cargos",
    "apps.user_admin",
    ...
]
```

**O mapa do porte** — o que muda em cada ponto que hoje conhece os dois models.

```python
# apps/competencias/{context,models/competencia,models/execucao}.py
# apps/unidades/{direcao,models/titularidade,models/unidade}.py
# apps/user_admin/{context,ficticios,models/user,superusuario}.py
- from apps.user_admin.models import CargoBase, CargoComissao
+ from apps.cargos.models import CargoBase, CargoComissao

# apps/user_admin/models/__init__.py deixa de reexportar os dois — `__init__.py` só reexporta o que
# é do app (CLAUDE.md §7.2), e cargo não é mais.
```

## 7 · Caveats

**Refactor com SPEC, contra o CLAUDE.md §4.** A regra é que refactor não toca a SPEC, porque quem
versiona código é o git. Aqui a mudança de app é pré-requisito estrutural da SPEC user_admin/029 —
que precisa de um app para pendurar quatro ações — e carrega migração que altera banco com estado,
que você revisa antes de aplicar. O custo é uma SPEC que descreve movimentação de arquivo.

**Renomear tabela em base com estado só sai certo na ordem.** Os três passos precisam ser aplicados
em sequência, e desfazer no meio deixa o estado do Django divergente do banco. Aceito por estarmos em
desenvolvimento; num banco de produção o mesmo porte pediria janela e backup.

**Não há teste novo a escrever antes do código.** A política de TDD (CLAUDE.md §9) pressupõe
comportamento novo a fixar, e um porte de app não tem nenhum: o critério é a suíte existente passar
sem alteração além do import. O custo é que o flag `testes_tdd` sobe junto com a entrega, e não
antes dela.

## 8 · Testes (TDD)

**Nenhum teste novo.** O que fixa este porte é a suíte que já existe: se ela passa sem alteração
além dos imports, o comportamento não mudou — que é exatamente o que a refatoração promete.

- `uv run pytest` verde.
- `uv run pytest -m banco` verde — é o que exercita as FKs de `Perfil`, `Concessao` e `Execucao`
  contra as tabelas renomeadas. *(marker `banco`)*
- `uv run python manage.py check` e `makemigrations --check` limpos.
