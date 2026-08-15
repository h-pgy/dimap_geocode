---
spec: autorizacao/002
versao: v6
atualizado_em: 2026-08-14
testes_tdd: true
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
  - v5: sem mudança de escopo — a SPEC foi reescrita no formato de seções numeradas da skill
    `specs`, com a justificativa toda concentrada em Caveats
  - v6: sem mudança de escopo — o XOR entre `cargo_base` e `cargo_comissao` fica explícito no
    snippet de modelagem, e a projeção do catálogo a cada deploy passa a estar escrita em código
    (`sincronizar_acoes`, comando e bloco do `entrypoint.sh`)
---

# SPEC autorizacao/002 — Competência no banco: projeção da ação, atribuição da unidade e concessão ao cargo

## 1 · User story
**Requisito não-funcional** — a competência de cada unidade e de cada cargo passa a ter onde existir,
e o catálogo de ações em código passa a ter uma projeção mantida em dia pelo próprio serviço.

## 2 · Condições de pronto
- [ ] O catálogo de ações da SPEC 001 é **projetado no banco** por um comando do `manage.py`, e a
      projeção se atualiza sozinha **a cada subida do serviço web**, sem intervenção manual.
- [ ] Rodar o comando à mão, quantas vezes for, não produz resultado diferente do da primeira vez.
- [ ] Ação que **sai do registro** é desativada, nunca apagada; de volta ao registro, é reativada com
      suas atribuições e concessões intactas.
- [ ] A projeção **não é editável** por tela nenhuma, inclusive o admin do Django.
- [ ] A projeção distingue a ação **estrutural** (SPEC 001) da comum.
- [ ] A mesma dupla unidade × ação não é atribuída duas vezes.
- [ ] Atribuir ação a unidade **não tem caminho de criação no admin do Django** — ali a atribuição só
      se inspeciona.
- [ ] Uma concessão **só existe pendurada numa atribuição existente**: não há como liberar a um cargo
      uma ação que a unidade dele não possui, nem pelo admin nem por shell.
- [ ] Cada concessão aponta para **exatamente um** cargo — base ou em comissão, nunca os dois nem
      nenhum — e a mesma dupla atribuição × cargo não se repete, **inclusive sendo um dos dois FKs
      nulo**.
- [ ] Retirar a atribuição de uma unidade **remove junto** as concessões que dela dependiam.

## 3 · Domínio
A competência tem dois níveis, e o de baixo é uma relação sobre a linha do de cima. `AtribuicaoUnidade`
é a competência institucional — o que a unidade faz; `Concessao` é quem, dentro dela, exerce. `Acao` é
projeção do registro em código, não fonte: existe para dar FK de verdade aos dois níveis.

Do catálogo da SPEC 001 esta SPEC lê [`RegistroAcoes` e `AcaoImplementada`](001-catalogo-de-acoes-em-codigo.md)
— "quais ações existem hoje, e quais delas são estruturais?".

**`apps/competencias/models/acao.py`**
```python
class Acao(models.Model):
    slug = models.CharField(max_length=120, unique=True)
    nome = models.CharField(max_length=120)
    nome_curto = models.CharField(max_length=60, blank=True)
    tooltip = models.CharField(max_length=255)
    # Ação some do código sem levar junto atribuições e concessões já concedidas.
    ativa = models.BooleanField(default=True)
    # Exercida por quem dirige a unidade: projetada para as telas a excluírem da oferta.
    estrutural = models.BooleanField(default=False)
```

**`apps/competencias/models/competencia.py`**
```python
class AtribuicaoUnidade(models.Model):
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, related_name="atribuicoes")
    acao = models.ForeignKey(Acao, on_delete=models.PROTECT, related_name="atribuicoes")


class Concessao(models.Model):
    # A ponta de cima é a LINHA da atribuição, não a dupla solta: conceder o que a unidade não tem
    # deixa de ser validação de aplicação e vira integridade referencial.
    atribuicao = models.ForeignKey(
        AtribuicaoUnidade,
        on_delete=models.CASCADE,
        related_name="concessoes",
    )
    # XOR entre os dois FKs abaixo: uma concessão nomeia cargo_base OU cargo_comissao —
    # exatamente um preenchido, nunca os dois, nunca nenhum. Ambos são anuláveis no schema
    # porque cada concessão só preenche um dos ramos; o "exatamente um" quem garante é a
    # CheckConstraint `concessao_exatamente_um_cargo` (§6), espelhada no `clean()`.
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
    # Procedência, não log de ato (SPEC 004): sem isto ninguém sabe quem liberou o quê.
    concedida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="concessoes_feitas",
        null=True,
    )
    concedida_em = models.DateTimeField(auto_now_add=True)
```

Unidade com atribuição e nenhuma concessão é estado válido: é a unidade recém-criada esperando
distribuição.

## 4 · Fora de escopo
- Decidir se um perfil pode executar uma ação — SPEC 003.
- Criar atribuição por tela, com autorização e registro — SPEC 007.
- Distribuir a atribuição entre os cargos por tela — SPEC 008.
- Registro de execução do ato administrativo — SPEC 004.
- Quem é titular de cada unidade e quem responde por ela hoje — SPECs `user_admin/014` e `015`.
- Concessão por natureza de cargo ("qualquer chefia") e concessão nominal a um servidor — sem dono
  ainda.
- Herança de competência pelo organograma — decidida contra nesta SPEC (§7), sem dono.

## 5 · Peças de referência a compor
- `@apps/competencias/registro.py` → `REGISTRO`, e `@apps/competencias/schemas.py` → `RegistroAcoes`:
  fonte única do sync.
- `@apps/user_admin/models` → `Unidade`, `CargoBase`, `CargoComissao`: alvos das FKs.
- `@apps/user_admin/seeds/` + `@apps/user_admin/management/commands/seed_cargos.py`: carga idempotente
  por chave natural com comando fino por cima.
- `@docker/entrypoint.sh`: preparação do serviço web antes de servir, sob `set -e`.
- `@apps/user_admin/models/cargos.py` → `CargoComissao.Meta.constraints`: `CheckConstraint` espelhada
  no `clean()`.
- `@apps/user_admin/models/impedimentos.py` → `TipoImpedimento.Meta.constraints`: `UniqueConstraint`
  com `condition`.
- `django.contrib.admin`: inspeção somente-leitura sobre as três tabelas.
- Skills: `management-commands`, `escrever-testes`.

## 6 · Snippets

**`apps/competencias/models/competencia.py`** — as invariantes da concessão, no banco.
```python
class Concessao(models.Model):
    ...

    class Meta:
        constraints = [
            # XOR explícito: FK genérico esconderia qual cargo é qual, e dois campos com check
            # barram o estado inválido antes de ele existir.
            models.CheckConstraint(
                check=(
                    Q(cargo_base__isnull=False, cargo_comissao__isnull=True)
                    | Q(cargo_base__isnull=True, cargo_comissao__isnull=False)
                ),
                name="concessao_exatamente_um_cargo",
            ),
            # Uma constraint por ramo do XOR: com uma constraint única sobre os três campos, o FK
            # nulo do outro ramo deixaria a duplicata passar (nulos não colidem no Postgres).
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

**`apps/competencias/models/competencia.py`** — a unicidade do nível 1.
```python
class AtribuicaoUnidade(models.Model):
    ...

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["unidade", "acao"],
                name="atribuicao_unica_por_unidade_e_acao",
            ),
        ]
```

**`apps/competencias/sync.py`** — a projeção: upsert por slug, desativação do que sumiu do código.
`Acao` aqui é o **model** (§3); o contrato do registro entra como `implementada.acao`.
```python
class ContagemSync(BaseModel):
    """Feedback do comando — e o que o teste de idempotência lê para saber que a 2ª rodada não
    mexeu em nada."""

    criadas: int
    atualizadas: int
    desativadas: int
    reativadas: int


def sincronizar_acoes(registro: RegistroAcoes) -> ContagemSync:
    """Recebe o registro por argumento para o teste não depender do global."""
    slugs_no_codigo = {implementada.acao.slug for implementada in registro.todas()}
    # Lido ANTES do upsert: depois dele toda linha do código já está ativa e a reativação seria
    # indistinguível de uma linha que nunca saiu.
    reativados = set(
        Acao.objects.filter(ativa=False, slug__in=slugs_no_codigo).values_list("slug", flat=True)
    )
    criadas = 0
    with transaction.atomic():
        for implementada in registro.todas():
            contrato = implementada.acao
            _, criada = Acao.objects.update_or_create(
                slug=contrato.slug,
                defaults={
                    "nome": contrato.nome,
                    # O contrato admite None; a coluna é `blank=True`, não anulável.
                    "nome_curto": contrato.nome_curto or "",
                    "tooltip": contrato.tooltip,
                    "estrutural": contrato.estrutural,
                    # Voltar ao registro reativa a linha — e ela reencontra as atribuições e
                    # concessões que continuaram penduradas nela enquanto esteve inativa.
                    "ativa": True,
                },
            )
            criadas += int(criada)
        # Apagar a linha da ação removida do código cascatearia atribuições e concessões reais: o
        # que sai do registro é desativado. Filtrar por `ativa=True` é o que faz a 2ª rodada contar
        # zero em vez de reescrever as mesmas linhas.
        desativadas = (
            Acao.objects.filter(ativa=True).exclude(slug__in=slugs_no_codigo).update(ativa=False)
        )
    return ContagemSync(
        criadas=criadas,
        atualizadas=len(slugs_no_codigo) - criadas,
        desativadas=desativadas,
        reativadas=len(reativados),
    )
```

**`apps/competencias/management/commands/sincronizar_acoes.py`** — comando fino: chamada e feedback
no stdout, sem lógica e sem argumento (o registro é o do processo).
```python
class Command(BaseCommand):
    help = "Projeta o catálogo de ações em código na tabela `Acao`."

    def handle(self, *args: object, **options: object) -> None:
        contagem = sincronizar_acoes(REGISTRO)
        self.stdout.write(self.style.SUCCESS(f"Catálogo sincronizado: {contagem}"))
```

**`docker/entrypoint.sh`** — o que faz a projeção acompanhar o deploy: toda subida do serviço web
roda o comando, dentro do MESMO bloco do `migrate`, que já existe no arquivo.
```sh
# Sync contra banco não migrado derrubaria a subida pelo set -e: quem desliga a migração automática
# desliga a projeção junto.
if [ -f manage.py ] && [ "${DJANGO_AUTO_MIGRATE:-1}" = "1" ]; then
    echo "==> Aplicando migrações..."
    python manage.py migrate --noinput
    echo "==> Sincronizando catálogo de ações..."
    python manage.py sincronizar_acoes
fi

exec "$@"
```

**`apps/competencias/admin.py`** — as três tabelas entram somente-leitura; nenhum `add`/`change` para
`Acao`, e a atribuição fica sem caminho de criação.

## 7 · Caveats
**O catálogo de ações passa a existir em dois lugares** — o registro em código (SPEC 001) e a tabela
projetada. É o que dá FK de verdade à atribuição e faz as telas de concessão serem querysets normais,
em vez de casarem queryset com registro em memória linha a linha. Custo: entre uma subida e outra os
dois divergem, e quem lê a tabela pode ver ação que o código já não tem — daí a coluna `ativa` e o
admin somente-leitura.

**Ação removida do código é desativada, não apagada.** Apagar cascatearia atribuições e concessões
reais, transformando um refactor em perda de dado administrativo. Custo: a tabela acumula linhas
mortas, e renomear um slug é mover pasta de ícones e desativar/recriar a linha, perdendo o vínculo com
o histórico anterior.

**O sync é disparado pelo `entrypoint.sh`, não por `post_migrate`.** Pendurado no sinal, ele rodaria
dentro de todo teste que cria banco e ficaria sem comando para rodar à mão quando a projeção
divergisse. Custo: quem sobe o serviço fora do Docker não tem a projeção atualizada sozinha e precisa
lembrar do comando.

**A XOR do cargo é escrita duas vezes** — `CheckConstraint` no banco e `clean()` no model, como já se
faz em `CargoComissao`. Sem o `clean()`, o formulário do admin devolveria `IntegrityError` cru em vez
de erro de campo. Custo: a mesma regra em dois lugares, que divergem se alguém tocar num só.

**A concessão vale para a unidade nomeada, sem herança pelo organograma.** Herdar daria a uma
coordenadoria tudo das divisões abaixo sem ninguém ter decidido isso. Custo: quem quiser a mesma ação
em toda uma subárvore atribui unidade a unidade, e não existe hoje caminho para fazer isso de uma vez.

## 8 · Testes (TDD)
Todos exigem banco e carregam o marker `banco`.

- `test_sync_projeta_registro_e_e_idempotente` — rodar duas vezes não duplica linha, e nome alterado no
  código chega na projeção, `estrutural` inclusive. *(marker `banco`)*
- `test_sync_desativa_ausente_e_reativa_no_retorno` — ação fora do registro vira `ativa=False` sem
  perder atribuições e concessões; de volta ao registro, volta `ativa=True` com elas intactas.
  *(marker `banco`)*
- `test_concessao_exige_exatamente_um_cargo` — nenhum cargo ou os dois preenchidos é recusado pelo
  banco. *(marker `banco`)*
- `test_remover_atribuicao_remove_concessoes` — apagar a atribuição da unidade leva junto as concessões
  que dela dependiam. *(marker `banco`)*
- `test_atribuicao_e_concessao_nao_se_duplicam` — a mesma dupla unidade × ação é recusada na segunda
  gravação; e a mesma dupla atribuição × cargo também, **nos dois ramos do XOR** — é o caso que a
  constraint única sobre os três campos deixaria passar pelo FK nulo. *(marker `banco`)*
