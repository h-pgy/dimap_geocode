---
spec: autorizacao/002
versao: v1
atualizado_em: 2026-08-07
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC autorizacao/002 — Competência no banco: projeção da ação, atribuição da unidade e concessão ao cargo

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como administrador do sistema, quero atribuir ações às unidades da DIMAP e ver essas atribuições
persistidas, para que o organograma — que cresce em runtime — possa receber competências sem
alteração de código, e para que os diretores possam depois distribuí-las entre os cargos da sua
unidade.

## Critérios de aceite
- [ ] O catálogo de ações da SPEC 001 é **projetado no banco** por um comando do `manage.py`, e a
      projeção se atualiza sozinha **a cada subida do serviço web**, sem intervenção manual.
- [ ] O mesmo comando pode ser rodado à mão a qualquer momento, quantas vezes for, sem efeito
      colateral.
- [ ] Ação que **sai do registro** é desativada, nunca apagada; se voltar ao registro, é reativada
      com suas atribuições e concessões intactas.
- [ ] A projeção é **somente leitura** nas telas administrativas — a fonte de verdade continua sendo
      o código.
- [ ] O administrador do sistema atribui uma ação a uma unidade pelo **admin do Django**, e a mesma
      dupla unidade × ação não pode ser atribuída duas vezes.
- [ ] Uma concessão **só existe pendurada numa atribuição existente**: não há como liberar para um
      cargo uma ação que a unidade dele não possui, nem pelo admin nem por shell.
- [ ] Cada concessão aponta para **exatamente um** cargo — base ou em comissão, nunca os dois nem
      nenhum — e a mesma dupla atribuição × cargo não se repete.
- [ ] Retirar a atribuição de uma unidade **remove junto** as concessões que dependiam dela.

## Contexto e decisões de arquitetura

Esta SPEC é só persistência e as telas do admin clássico. Ninguém é autorizado por ela ainda — a
decisão de acesso é a SPEC 003.

**Concessão em dois níveis.** `AtribuicaoUnidade` é `(unidade, ação)`: a competência institucional,
o que aquela unidade faz. `Concessao` é `(atribuição, cargo)`: quem, dentro dela, exerce. O nível 2
referencia a **linha** do nível 1, não a dupla solta — por isso "o diretor só concede o que a
unidade dele tem" deixa de ser validação de aplicação e vira integridade referencial. Unidade com
atribuição e nenhuma concessão é estado válido: é a unidade recém-criada esperando distribuição.

**A tabela `Acao` é projeção, não fonte.** Ela existe para dar FK de verdade à atribuição e para
que as telas de concessão sejam querysets normais (listar, buscar, ordenar) em vez de casarem
queryset com registro em memória a cada linha. Por isso projeta `slug`, `nome`, `nome_curto` e
`tooltip` — o que se consulta no banco. As variantes de ícone ficam fora: nada as consulta em SQL, e
a apresentação lê o registro em memória. O admin a exibe somente-leitura; editar ali seria editar um
espelho.

**Desativação em vez de exclusão.** Apagar a linha de uma ação removida do código cascatearia
atribuições e concessões reais — perda de dado administrativo por um refactor. O sync faz upsert por
slug e marca `ativa=False` no que sumiu; a ação que volta reencontra seu histórico.

**Disparo por management command no `entrypoint.sh`, não por `post_migrate`.** O sync é uma carga,
não um efeito de schema: pendurá-lo no `post_migrate` o faria rodar dentro de todo teste que cria
banco e o deixaria invisível — sem comando para rodar à mão quando a projeção divergir. O
`docker/entrypoint.sh` já é o lugar onde o serviço web se prepara antes de servir; a linha nova
entra depois do `migrate`, e o `set -e` faz uma projeção que falhou derrubar a subida em vez de
servir um catálogo pela metade. De quebra, os system checks da SPEC 001 rodam junto com o comando —
registro quebrado não sobe.

A lógica vive no app, como as seeds de `user_admin`: mexe em persistência e orquestração, não em
domínio. O comando é fino (chamada + feedback) e recebe o registro por argumento, para o teste não
depender do global.

**Cargo: dois FK anuláveis com XOR.** O `Perfil` tem `cargo_base` obrigatório e `cargo_comissao`
opcional, e a concessão pode mirar qualquer um dos dois. Um FK genérico esconderia qual é qual; dois
campos com `CheckConstraint` garantindo exatamente um preenchido deixam explícito e barram o estado
inválido no banco, como já se faz em `CargoComissao` e `Unidade`.

**Unidade exata, sem herança.** A concessão vale para a unidade nomeada; ancestral não alcança
descendente. É decisão de produto: competência é atribuição da unidade em si, e herdar pelo
organograma daria a uma coordenadoria tudo das divisões abaixo sem ninguém ter decidido isso.

**Quem concedeu fica registrado na linha.** `Concessao` carrega o perfil concedente e a data. Não é
o log de execução de ato (SPEC 004) — é procedência: sem isso ninguém sabe quem liberou o quê.

**Nível 1 no admin do Django, nível 2 depois.** Atribuir ação a unidade é ato do administrador do
sistema, e o `django.contrib.admin` já resolve a tela e registra o histórico no `LogEntry`. A tela
do diretor concedendo a cargos vem em SPEC própria; até lá, `Concessao` também aparece no admin,
como bootstrap.

## Peças de referência a compor
- `@apps/competencias/acoes.py` → `RegistroAcoes` (SPEC 001): fonte única do sync; a projeção lê
  dele, nunca o contrário.
- `@apps/user_admin/models` → `Unidade`, `CargoBase`, `CargoComissao`: alvos das FKs, sem alteração
  nesta SPEC.
- `@apps/user_admin/seeds/` + `@apps/user_admin/management/commands/seed_cargos.py`: padrão de carga
  idempotente por chave natural com comando fino por cima — o sync segue a mesma natureza, com o
  registro em código no lugar do JSON de `data/seed/`.
- `@docker/entrypoint.sh`: já prepara o serviço web antes de servir; o comando novo entra depois do
  `migrate`, sob o mesmo `set -e`.
- `@apps/user_admin/models/cargos.py` → `CargoComissao.Meta.constraints`: precedente de
  `CheckConstraint` espelhada no `clean()`; a XOR de cargo segue o mesmo padrão.
- `django.contrib.admin`: telas do nível 1, em vez de UI própria.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md

# apps/competencias/models/acao.py
class Acao(models.Model):
    """Projeção do registro em código (SPEC 001). Não é editável: a fonte é o código."""

    slug = models.CharField(
        max_length=120,
        unique=True,
    )
    nome = models.CharField(max_length=120)
    nome_curto = models.CharField(
        max_length=60,
        blank=True,
    )
    tooltip = models.CharField(max_length=255)
    # Ação some do código sem levar junto atribuições e concessões já concedidas.
    ativa = models.BooleanField(default=True)
```

```python
# apps/competencias/models/competencia.py
class AtribuicaoUnidade(models.Model):
    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.PROTECT,
        related_name="atribuicoes",
    )
    acao = models.ForeignKey(
        Acao,
        on_delete=models.PROTECT,
        related_name="atribuicoes",
    )


class Concessao(models.Model):
    # CASCADE: unidade que perdeu a competência não deixa cargo exercendo-a.
    atribuicao = models.ForeignKey(
        AtribuicaoUnidade,
        on_delete=models.CASCADE,
        related_name="concessoes",
    )
    cargo_base = models.ForeignKey(
        CargoBase,
        on_delete=models.PROTECT,
        related_name="concessoes",
        null=True,
        blank=True,
    )
    cargo_comissao = models.ForeignKey(
        CargoComissao,
        on_delete=models.PROTECT,
        related_name="concessoes",
        null=True,
        blank=True,
    )
    concedida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="concessoes_feitas",
        null=True,
    )
    concedida_em = models.DateTimeField(auto_now_add=True)
```

```python
# apps/competencias/sync.py
def sincronizar_acoes(registro: RegistroAcoes) -> ContagemSync:
    """Upsert por slug + desativação das ausentes. Recebe o registro por argumento para o teste
    não depender do global."""
    ...
```

```sh
# docker/entrypoint.sh — depois do migrate, sob o mesmo set -e
if [ -f manage.py ]; then
    echo "==> Sincronizando catálogo de ações..."
    python manage.py sincronizar_acoes
fi
```

## Fora de escopo
- Decidir se um perfil pode executar uma ação — avaliador e backend são a SPEC 003.
- Tela própria do diretor concedendo a cargos: até ela existir, `Concessao` sai pelo admin.
- Registro de execução do ato administrativo (SPEC 004).
- Concessão por natureza de cargo ("qualquer chefia") e concessão nominal a um servidor.
- Impedimento e substituição.
- Herança de competência pelo organograma.
- Aplicar a migração: o agente gera, quem aplica é o usuário (CLAUDE.md §4).

## Testes (TDD)
Todos exigem banco e carregam o marker `banco` — declarado em `markers_obrigatorios`.

- `test_sync_projeta_registro_e_e_idempotente` — rodar duas vezes não duplica linha, e nome alterado
  no código chega na projeção.
- `test_sync_desativa_ausente_e_reativa_no_retorno` — ação fora do registro vira `ativa=False` sem
  perder atribuições e concessões; de volta ao registro, volta `ativa=True` com elas intactas.
- `test_concessao_exige_exatamente_um_cargo` — nenhum cargo ou os dois preenchidos é recusado pelo
  banco.
- `test_remover_atribuicao_remove_concessoes` — apagar a atribuição da unidade leva junto as
  concessões que dela dependiam.
- `test_atribuicao_e_concessao_nao_se_duplicam` — a mesma dupla unidade × ação, e a mesma dupla
  atribuição × cargo, são recusadas na segunda gravação.

## Patches

_Nenhum patch registrado até o momento._
