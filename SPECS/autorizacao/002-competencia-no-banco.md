---
spec: autorizacao/002
versao: v4
atualizado_em: 2026-08-11
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: admin do Django deixa de ser o caminho do nível 1 — atribuir ação a unidade vira ação
    própria (`competencias.definir_atribuicao`, SPEC 007), semeada para os cargos de chefia; aqui
    o admin fica só como conveniência de inspeção
  - v3: o bootstrap deixa de ser seed e passa a decorrer da titularidade (SPEC titularidade/001);
    a projeção leva `estrutural`; unicidade da concessão passa a duas constraints parciais (FK
    anulável não colide); referências de módulo corrigidas para `registro.py`/`schemas.py`
  - v4: a titularidade foi entregue como SPEC user_admin/014, não como épico próprio, e quem exerce
    a estrutural é quem responde pela direção — titular em exercício ou substituto dele (SPEC
    user_admin/015); referências corrigidas, sem mudança nas tabelas
---

# SPEC autorizacao/002 — Competência no banco: projeção da ação, atribuição da unidade e concessão ao cargo

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como responsável pela DIMAP, quero que as ações atribuídas às unidades fiquem persistidas, para que
o organograma — que cresce em runtime — possa receber competências sem alteração de código, e para
que os diretores possam depois distribuí-las entre os cargos da sua unidade.

## Critérios de aceite
- [ ] O catálogo de ações da SPEC 001 é **projetado no banco** por um comando do `manage.py`, e a
      projeção se atualiza sozinha **a cada subida do serviço web**, sem intervenção manual.
- [ ] O mesmo comando pode ser rodado à mão a qualquer momento, quantas vezes for, sem efeito
      colateral.
- [ ] Ação que **sai do registro** é desativada, nunca apagada; se voltar ao registro, é reativada
      com suas atribuições e concessões intactas.
- [ ] A projeção é **somente leitura** nas telas administrativas — a fonte de verdade continua sendo
      o código.
- [ ] A projeção distingue a ação **estrutural** (SPEC 001) da comum, para que as telas possam
      deixar de oferecer o que ninguém atribui nem concede.
- [ ] A mesma dupla unidade × ação não pode ser atribuída duas vezes.
- [ ] `AtribuicaoUnidade` aparece no admin do Django **apenas como conveniência de inspeção** — o
      caminho de criação é a ação `competencias.definir_atribuicao` (SPEC 007).
- [ ] Uma concessão **só existe pendurada numa atribuição existente**: não há como liberar para um
      cargo uma ação que a unidade dele não possui, nem pelo admin nem por shell.
- [ ] Cada concessão aponta para **exatamente um** cargo — base ou em comissão, nunca os dois nem
      nenhum — e a mesma dupla atribuição × cargo não se repete, **inclusive sendo um dos dois FKs
      nulo**.
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
queryset com registro em memória a cada linha. Por isso projeta `slug`, `nome`, `nome_curto`,
`tooltip` e `estrutural` — o que se consulta no banco. As variantes de ícone ficam fora: nada as
consulta em SQL, e a apresentação lê o registro em memória. O admin a exibe somente-leitura; editar
ali seria editar um espelho.

**A ação estrutural é projetada, mas nunca atribuída.** Ela existe na tabela porque o registro de
execução (SPEC 004) precisa de FK para ela como para qualquer outra. Mas competência estrutural
decorre de dirigir a unidade (SPEC 001, SPEC `user_admin/014`) e não passa por estas duas tabelas —
por isso a coluna, que é o que permite às telas da SPEC 007 não oferecerem o que não produz efeito.

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

O sync entra **sob a mesma condição do `migrate`** (`DJANGO_AUTO_MIGRATE`), e não solto ao lado
dela: quem desliga a migração automática em produção o faz para que a subida não toque o schema, e
um sync rodando contra um banco que ainda não migrou derrubaria o serviço pelo `set -e` — o oposto
do que o desligamento pede.

A lógica vive no app, como as seeds de `user_admin`: mexe em persistência e orquestração, não em
domínio. O comando é fino (chamada + feedback) e recebe o registro por argumento, para o teste não
depender do global.

**Cargo: dois FK anuláveis com XOR.** O `Perfil` tem `cargo_base` obrigatório e `cargo_comissao`
opcional, e a concessão pode mirar qualquer um dos dois. Um FK genérico esconderia qual é qual; dois
campos com `CheckConstraint` garantindo exatamente um preenchido deixam explícito e barram o estado
inválido no banco, como já se faz em `CargoComissao` e `Unidade`.

**A unicidade da concessão são duas constraints parciais, não uma.** Um único
`UniqueConstraint(atribuicao, cargo_base, cargo_comissao)` **não** impediria a duplicata: no
Postgres nulos são distintos entre si, e um dos dois FKs é sempre nulo por causa do XOR — a segunda
gravação idêntica passaria. Uma constraint por ramo, cada uma condicionada ao FK que importa, é o
que faz o banco recusar de fato.

**Unidade exata, sem herança.** A concessão vale para a unidade nomeada; ancestral não alcança
descendente. É decisão de produto: competência é atribuição da unidade em si, e herdar pelo
organograma daria a uma coordenadoria tudo das divisões abaixo sem ninguém ter decidido isso.

**Quem concedeu fica registrado na linha.** `Concessao` carrega o perfil concedente e a data. Não é
o log de execução de ato (SPEC 004) — é procedência: sem isso ninguém sabe quem liberou o quê.

**Os dois níveis saem do admin.** Atribuir ação a unidade **não** é ato de administrador de sistema
pelo `django.contrib.admin`: é ato administrativo como qualquer outro, e vira a ação
`competencias.definir_atribuicao` (SPEC 007), com tela própria, autorização na rota e execução
registrada (SPEC 004). O nível 2 sai da SPEC 008. O admin sobre estas duas tabelas permanece como
conveniência de inspeção, não como caminho de criação.

**O primeiro estado do banco não é problema destas tabelas.** As duas ações que as administram são
**estruturais** (SPEC 001): quem as exerce é quem responde pela direção da unidade — o titular em
exercício ou o substituto dele (SPECs `user_admin/014` e `015`) —, sem atribuição nem concessão
gravada. Por isso as duas tabelas podem nascer vazias sem travar nada — não há ovo-e-galinha a
quebrar, e nenhuma seed é necessária para isso.

## Peças de referência a compor
- `@apps/competencias/registro.py` → `REGISTRO` e `@apps/competencias/schemas.py` → `RegistroAcoes`
  (SPEC 001): fonte única do sync; a projeção lê dele, nunca o contrário.
- `@apps/user_admin/models` → `Unidade`, `CargoBase`, `CargoComissao`: alvos das FKs, sem alteração
  nesta SPEC.
- `@apps/user_admin/seeds/` + `@apps/user_admin/management/commands/seed_cargos.py`: padrão de carga
  idempotente por chave natural com comando fino por cima — o sync segue a mesma natureza, com o
  registro em código no lugar do JSON de `data/seed/`.
- `@docker/entrypoint.sh`: já prepara o serviço web antes de servir; o comando novo entra depois do
  `migrate`, sob o mesmo `set -e`.
- `@apps/user_admin/models/cargos.py` → `CargoComissao.Meta.constraints`: precedente de
  `CheckConstraint` espelhada no `clean()`; a XOR de cargo segue o mesmo padrão.
- `@apps/user_admin/models/impedimentos.py` → `TipoImpedimento.Meta.constraints`: precedente de
  `UniqueConstraint` com `condition` — as duas constraints parciais da concessão têm a mesma forma.
- `django.contrib.admin`: conveniência de inspeção sobre as duas tabelas; não é caminho de criação.

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
    # Exercida por quem dirige a unidade: projetada para as telas a excluírem da oferta.
    estrutural = models.BooleanField(default=False)
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

    class Meta:
        constraints = [
            # Uma por ramo do XOR: com constraint única, o FK nulo do outro ramo deixaria a
            # duplicata passar (nulos não colidem no Postgres).
            models.UniqueConstraint(
                fields=["atribuicao", "cargo_base"],
                condition=Q(cargo_base__isnull=False),
                name="concessao_unica_por_cargo_base",
            ),
            models.UniqueConstraint(
                fields=["atribuicao", "cargo_comissao"],
                condition=Q(cargo_comissao__isnull=False),
                name="concessao_unica_por_cargo_comissao",
            ),
        ]
```

```python
# apps/competencias/sync.py
def sincronizar_acoes(registro: RegistroAcoes) -> ContagemSync:
    """Upsert por slug + desativação das ausentes. Recebe o registro por argumento para o teste
    não depender do global."""
    ...
```

```sh
# docker/entrypoint.sh — dentro do MESMO bloco do migrate: sync sem schema migrado derruba a subida.
if [ -f manage.py ] && [ "${DJANGO_AUTO_MIGRATE:-1}" = "1" ]; then
    python manage.py migrate --noinput
    echo "==> Sincronizando catálogo de ações..."
    python manage.py sincronizar_acoes
fi
```

## Fora de escopo
- Decidir se um perfil pode executar uma ação — avaliador e backend são a SPEC 003.
- Tela do diretor concedendo a cargos: SPEC 008.
- A ação `competencias.definir_atribuicao` — contrato, tela e autorização: SPEC 007. Aqui só se
  persiste o que ela vai gravar.
- Quem é titular de cada unidade e quem responde por ela hoje: SPECs `user_admin/014` e `015`.
- Registro de execução do ato administrativo (SPEC 004).
- Concessão por natureza de cargo ("qualquer chefia") e concessão nominal a um servidor.
- Impedimento e substituição.
- Herança de competência pelo organograma.
- Aplicar a migração: o agente gera, quem aplica é o usuário (CLAUDE.md §4).

## Testes (TDD)
Todos exigem banco e carregam o marker `banco` — declarado em `markers_obrigatorios`.

- `test_sync_projeta_registro_e_e_idempotente` — rodar duas vezes não duplica linha, e nome alterado
  no código chega na projeção, `estrutural` inclusive.
- `test_sync_desativa_ausente_e_reativa_no_retorno` — ação fora do registro vira `ativa=False` sem
  perder atribuições e concessões; de volta ao registro, volta `ativa=True` com elas intactas.
- `test_concessao_exige_exatamente_um_cargo` — nenhum cargo ou os dois preenchidos é recusado pelo
  banco.
- `test_remover_atribuicao_remove_concessoes` — apagar a atribuição da unidade leva junto as
  concessões que dela dependiam.
- `test_atribuicao_e_concessao_nao_se_duplicam` — a mesma dupla unidade × ação é recusada na segunda
  gravação; e a mesma dupla atribuição × cargo também, **nos dois ramos do XOR** — é o caso que a
  constraint única deixaria passar pelo FK nulo.

## Patches

_Nenhum patch registrado até o momento._
