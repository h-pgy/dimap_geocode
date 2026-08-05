---
spec: user_admin/002
versao: v1
atualizado_em: 2026-08-05
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC user_admin/002 — Impedimentos do servidor

- [x] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como administrador da plataforma, quero registrar os afastamentos de cada servidor — férias,
licenças, afastamentos — com início e fim, para que o sistema saiba quem está impedido **hoje** e,
adiante, possa negar a prática de atos administrativos a quem não está no exercício do cargo.

## Critérios de aceite

- [ ] O **tipo de impedimento** é um catálogo com nome obrigatório e **sigla opcional**
      (`"Licença para Tratar de Interesses Particulares"` / `"LTIP"`; `"Férias"` sem sigla),
      criável e reutilizável.
- [ ] O tipo expõe um **nome de exibição**: a sigla quando existe, o nome completo quando não —
      `"LTIP"` para a licença, `"Férias"` para férias.
- [ ] Duas siglas iguais são recusadas, mas **vários tipos sem sigla convivem**.
- [ ] Um **impedimento concreto** vincula um servidor a um tipo, com data de início e data de fim.
      O mesmo servidor acumula quantos impedimentos tiver ao longo do tempo (duas férias por ano é
      o caso normal).
- [ ] A **data de fim é opcional**: sem ela, o impedimento vale por prazo indeterminado a partir do
      início.
- [ ] Um impedimento cujo fim antecede o início é recusado.
- [ ] **Impedimentos do mesmo servidor podem se sobrepor** — uma licença médica que atravessa as
      férias não é erro, e nada no banco a barra.
- [ ] O perfil expõe uma booleana calculada dizendo se está **impedido hoje**: verdadeira quando
      existe ao menos um impedimento cujo período cobre a data de hoje, incluindo os extremos.
- [ ] Apagar um tipo em uso é recusado; apagar um servidor leva seus impedimentos junto.

## Contexto e decisões de arquitetura

Continua sendo **só camada de persistência**, sobre os models da SPEC `user_admin/001` — o
`Impedimento` entra como mais um módulo do pacote de models, e o `Perfil` ganha a propriedade
calculada.

**Um model único de impedimento, com o tipo em catálogo.** Férias, LTIP e afastamento diferem no
rótulo, não na estrutura: todos são um período vinculado a um servidor. Um model por espécie
multiplicaria tabelas idênticas e obrigaria a consultar todas elas para responder "está impedido
hoje?".

**A sigla é opcional, e quem manda na exibição é ela.** Ninguém diz "Licença para Tratar de
Interesses Particulares" — diz LTIP; mas ninguém diz "F" para férias. Então o tipo guarda os dois e
uma `@property` escolhe: sigla quando há, nome completo quando não. Como a sigla é opcional, sua
unicidade é uma `UniqueConstraint` condicionada ao valor não vazio — `unique=True` no campo barraria
o segundo tipo sem sigla. O vazio é `""`, não `NULL`, para não haver dois jeitos de dizer "não tem".

**Sobreposição é permitida.** Períodos cruzados acontecem de verdade (licença médica que interrompe
férias), então não há `ExclusionConstraint` nem validação de período — e, por consequência, o
projeto não precisa da extensão `btree_gist`. O que a sobreposição implica é que a resposta a
"está impedido?" é a **existência** de ao menos um período cobrindo hoje, não a contagem deles.

**Fim aberto é `NULL`, não uma data-sentinela.** Um afastamento sem retorno previsto tem fim
desconhecido; escrever `9999-12-31` para representá-lo faria toda comparação de data mentir. A
consequência é que o teste de vigência tem duas pernas: começou, e ou não terminou ou termina de
hoje em diante.

**`esta_impedido` é `@property` no `Perfil`.** Ela consulta a relação reversa e compara com a data
de hoje — mais que a formatação de campo próprio que `natureza` e `padrao` fazem, mas ainda uma
leitura das linhas do próprio registro, não regra de negócio. A regra de negócio é **o que o
impedimento impede**, e essa fica no domínio, na SPEC de autorização. O custo aceito é uma query
por perfil avaliado; com dezenas de usuários internos, isso não justifica anotação em queryset
(§3.2 também não a permitiria num manager).

**A data de hoje vem de `timezone.localdate()`**, no fuso de `TIME_ZONE`. Impedimento é ato de
calendário administrativo: usar UTC faria o servidor voltar do afastamento em horário errado nas
bordas do dia.

**Estes testes precisam de banco, e ficam atrás de um marker `banco`.** Diferente da SPEC 001, o
comportamento a fixar é uma consulta: sem linha persistida não há relação reversa a consultar.
Teste que exige serviço externo não é unitário, então o marker entra na exclusão que o
`integration` já usa (`addopts`) e `uv run pytest` segue rápido e sem docker. O que impede o marker
de virar teste morto é o `markers_obrigatorios: [banco]` no front-matter: esta SPEC não é marcada
como implementada sem `uv run pytest -m banco` verde.

## Peças de referência a compor

- `@SPECS/user_admin/001` → `Perfil` e o pacote de models do app: o `Impedimento` entra como módulo
  novo e o `__init__` passa a reexportá-lo também.
- `@config/settings.py` → `TIME_ZONE`: é o fuso que define qual é "hoje".
- `@pyproject.toml` → `[tool.pytest.ini_options]`: o marker `integration` e sua exclusão em
  `addopts` são o molde para o marker `banco`.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md
#
# TipoImpedimento e Impedimento num módulo próprio do pacote de models; a property abaixo
# entra no Perfil, que já vive em `user`.


class TipoImpedimento(models.Model):
    nome = models.CharField(
        max_length=120,
        unique=True,
    )
    sigla = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    @property
    def nome_exibicao(self) -> str:
        return self.sigla or self.nome

    class Meta:
        constraints = [
            # unique=True no campo barraria o segundo tipo sem sigla; a condição isenta o vazio.
            models.UniqueConstraint(
                fields=["sigla"],
                condition=~Q(sigla=""),
                name="tipo_impedimento_sigla_unica",
            ),
        ]


class Impedimento(models.Model):
    perfil = models.ForeignKey(
        "user_admin.Perfil",
        on_delete=models.CASCADE,
        related_name="impedimentos",
    )
    tipo = models.ForeignKey(
        TipoImpedimento,
        on_delete=models.PROTECT,
        related_name="impedimentos",
    )
    data_inicio = models.DateField()
    # Nulo = prazo indeterminado; data-sentinela faria toda comparação de data mentir.
    data_fim = models.DateField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(data_fim__isnull=True) | Q(data_fim__gte=F("data_inicio")),
                name="impedimento_fim_nao_antecede_inicio",
            ),
        ]


# ---- em `user`, no Perfil ----

    @property
    def esta_impedido(self) -> bool:
        hoje = timezone.localdate()
        return self.impedimentos.filter(
            Q(data_fim__isnull=True) | Q(data_fim__gte=hoje),
            data_inicio__lte=hoje,
        ).exists()
```

## Fora de escopo

- **O que o impedimento impede.** Negar ações a quem está impedido é autorização (§3.5) e entra na
  SPEC do router de gaveta.
- Seed dos tipos de impedimento — vai junto com o seed geral do épico.
- Telas, rotas e Django admin para cadastrar impedimento.
- Histórico de alteração do impedimento (quem cadastrou, quem corrigiu) e qualquer trilha de
  auditoria.
- Cálculo de saldo de férias, período aquisitivo e qualquer regra de RH.

## Testes (TDD)

Os cinco primeiros tocam o banco e levam o marker `banco` — rodam com `uv run pytest -m banco`,
com o docker de pé. Os dois últimos são de propriedade pura e seguem na suíte padrão.

- `test_perfil_com_impedimento_vigente_esta_impedido` — período que cobre hoje, incluindo o dia de
  início e o dia de fim, devolve verdadeiro.
- `test_perfil_com_impedimento_de_fim_aberto_esta_impedido` — início no passado e `data_fim` nula
  mantêm o perfil impedido.
- `test_perfil_com_impedimento_fora_de_vigencia_nao_esta_impedido` — período já encerrado e período
  ainda por começar devolvem falso.
- `test_impedimento_com_fim_anterior_ao_inicio_nao_valida` — a constraint recusa o registro.
- `test_impedimentos_sobrepostos_coexistem` — dois períodos cruzados do mesmo perfil são salvos sem
  erro, e o perfil aparece impedido uma vez.
- `test_nome_exibicao_prefere_a_sigla` — com sigla devolve `"LTIP"`; sem sigla devolve `"Férias"`.
- `test_tipos_sem_sigla_convivem` — dois tipos sem sigla são salvos, mas duas siglas iguais são
  recusadas.

## Patches

_Nenhum patch registrado até o momento._
