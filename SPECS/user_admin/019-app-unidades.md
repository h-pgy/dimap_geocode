---
spec: user_admin/019
versao: v1
atualizado_em: 2026-08-22
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC user_admin/019 — Unidade sai de `user_admin` e vira app próprio

## 1 · User story
**Refatoração** — `user_admin` carregava dois domínios; o da unidade passa a ter app próprio, e o
cadastro de servidor deixa de crescer junto com o organograma.

## 2 · Condições de pronto
- [ ] `apps/unidades` responde pela unidade: model, hierarquia, cor, organograma, seed, titularidade
      e as telas dela. `user_admin` não tem model, rota nem template de unidade.
- [ ] As URLs de unidade continuam nos mesmos caminhos (`/gestao/unidades/…`), sob o namespace
      `unidades:`.
- [ ] Os models de `apps/unidades` não importam `apps/user_admin` em runtime.
- [ ] A mudança de app **renomeia** as tabelas e move os `ContentType`: nenhuma linha é recriada.
- [ ] A suíte passa sem nenhum teste novo.

## 3 · Domínio
Nenhuma ontologia nova. [`Unidade`, `TipoUnidade` e `CorUnidade`](001-models-perfil-cargos-unidade.md)
e a [hierarquia](003-hierarquia-unidades.md) mudam de app, não de forma.

A escala do cargo em comissão (`NIVEL_MINIMO`, `NIVEL_MAXIMO`) passa a viver em
`services/domain/titularidade`: `CargoComissao` e `TipoUnidade` a declaram como validador, e agora
estão em apps diferentes.

## 4 · Fora de escopo
- Atualizar o corpo das SPECs anteriores que citam caminhos movidos (user_admin 008 e 012–018,
  autorizacao 003/004/007, criacao_usuarios/006) — **sem dono ainda**.

## 5 · Peças de referência a compor
- `@services/domain/titularidade` → `avaliar_titularidade`: a regra que a ponte dos models chama.
- `@services/domain/arvore_hierarquica` → `ArvoreHierarquica`: a posição no organograma.

## 6 · Snippets

A dependência entre os apps é de mão única **nos models**: `user_admin` conhece `unidades` pela FK de
lotação, e o caminho de volta existe só para o verificador de tipos.

**`apps/unidades/models/titularidade.py`**
```python
# Em runtime a função só lê e_chefia, alta_administracao e nivel — o tipo é a única coisa que
# precisaria importar user_admin, e sob TYPE_CHECKING ele não é importado.
if TYPE_CHECKING:
    from apps.user_admin.models import CargoComissao


def cargo_titulariza(cargo: "CargoComissao | None", ...) -> bool: ...
```

A tabela é a mesma; o que muda é quem a declara. O estado das migrações se ajusta sem DDL, e só
depois a tabela é renomeada.

**`apps/unidades/migrations/0001_initial.py`**
```python
# database_operations vazio: as tabelas já existem, criadas por user_admin. O db_table fixado aponta
# para o nome antigo — inclusive o do M2M, que o Django deriva dele.
migrations.SeparateDatabaseAndState(
    database_operations=[],
    state_operations=[
        migrations.CreateModel(name="TipoUnidade", ..., options={"db_table": "user_admin_tipounidade"}),
        migrations.CreateModel(name="Unidade", ..., options={"db_table": "user_admin_unidade"}),
    ],
)
```

**`apps/unidades/migrations/0002_renomear_tabelas_e_content_types.py`**
```python
# table=None devolve o nome padrão do app novo. O Postgres leva as FKs junto: a constraint segue a
# tabela, não o nome dela. O RunPython move django_content_type.app_label, sem o que o migrate
# seguinte criaria content types novos e as Permission ficariam no app_label velho.
migrations.AlterModelTable(name="tipounidade", table=None)
migrations.AlterModelTable(name="unidade", table=None)
migrations.RunPython(_mover_content_types(APP_ANTIGO, APP_NOVO), _mover_content_types(APP_NOVO, APP_ANTIGO))
```

## 7 · Caveats

Os dois apps se conhecem na camada de orquestração: `apps/unidades/context.py`, `direcao.py` e
`titularidade.py` importam `user_admin`. A página da unidade mostra o titular e o substituto, e a do
servidor mostra o alarme da unidade que ele dirige — nenhuma das duas se escreve sem a outra. O custo
é que mudança na apresentação do `Perfil` alcança a página da unidade sem passar por ela.

`imagem_do_perfil` e `selo_do_exercicio` saíram de `context.py` para `apps/user_admin/apresentacao.py`.
Sem isso, `unidades.context` e `user_admin.context` se importariam mutuamente. O custo é um módulo a
mais na borda do `user_admin`.

Doze SPECs anteriores citam caminhos que este refactor moveu e continuam com `implementado: true`.
Editá-las exigiria bump de versão em cada uma por uma mudança de pasta, e o que elas especificam segue
de pé. O custo é que o corpo delas aponta para arquivos que mudaram de lugar — quem os procurar
encontra por esta SPEC.

Esta SPEC nasce com os dois flags em `true`: ela registra um refactor já executado, e o que a valida é
a suíte que já existia.

## 8 · Testes (TDD)
Nenhum teste novo — é refactor, e o comportamento é o mesmo. Os testes da unidade mudam de caminho
(`tests/apps/user_admin/` → `tests/apps/unidades/`) e de import, sem alteração de conteúdo:

- `tests/apps/unidades/models/test_unidade.py` — hierarquia, tipo e cor *(marker `banco`)*
- `tests/apps/unidades/models/test_titularidade.py` — a adequação cruzando `Perfil` e `Unidade` *(marker `banco`)*
- `tests/apps/unidades/test_titularidade.py` — os atos de definir e destituir titular *(marker `banco`)*
- `tests/apps/unidades/test_seed_unidades.py` — a carga do organograma *(marker `banco`)*
- `tests/apps/unidades/views/` — página da unidade, organograma e formulário *(marker `banco`)*
