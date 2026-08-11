---
spec: autorizacao/004
versao: v2
atualizado_em: 2026-08-11
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: registro passa a identificar a operação praticada; grava toda negativa e as execuções que
    alteram estado, não a leitura autorizada de tela; anônimo sai do critério de registro
---

# SPEC autorizacao/004 — Proteção de rota e registro de execução do ato

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como responsável pela DIMAP, quero que toda execução de ação seja barrada na rota para quem não tem
competência e fique registrada para quem tem, para que o ato administrativo praticado na plataforma
tenha autor conhecido — e para que esconder o botão nunca seja a única barreira.

## Critérios de aceite
- [ ] Rota de ação **nega com 403** o perfil autenticado sem competência, e manda o **anônimo para o
      login** pelo caminho padrão do Django.
- [ ] Toda execução autorizada que **altera estado** fica registrada: quem, com qual cargo e unidade
      **no momento do ato**, qual ação, **qual operação**, quando.
- [ ] Toda tentativa **negada de perfil autenticado** fica registrada, inclusive a de leitura — é o
      que permite responder se a pessoa podia.
- [ ] Duas operações opostas da mesma ação — conceder e revogar, atribuir e remover — ficam
      **distinguíveis** no registro.
- [ ] A view pode acrescentar ao registro **sobre o que** o ato incidiu; esquecer de fazê-lo não
      impede o registro de existir.
- [ ] A proteção é declarada com o **contrato da ação**, não com uma string solta.

## Contexto e decisões de arquitetura

Esta SPEC transforma a resposta da SPEC 003 em barreira efetiva e em rastro. É a contraparte do
router (SPEC 005): lá o menu esconde o que não se pode; aqui a rota recusa mesmo que alguém digite a
URL.

**403 para autenticado, login para anônimo.** Redirecionar um perfil autenticado para o login não
diz nada — ele já está logado; o que falta é competência, e isso é 403. Para HTMX o 403 é ainda mais
necessário: redirect vira a página de login trocada dentro de um fragmento. A distinção é a
combinação que o próprio Django recomenda (`login_required` + `permission_required` com
`raise_exception`).

**O decorator recebe o contrato, não a string.** O slug é escrito uma vez só, na declaração da ação;
a rota referencia o objeto. Typo vira erro de import, não negação silenciosa — que é o modo de falha
ruim de autorização por string.

**Registro garantido pelo decorator, enriquecido pela view.** O decorator grava sem depender de a
view lembrar: é o que torna o rastro estrutural em vez de dependente de disciplina. Mas só a view
sabe sobre qual entidade o ato incidiu, então ela acrescenta o alvo, e o registro existe mesmo se
ela não acrescentar. Nada disso por signal: o CLAUDE.md (§3.2) recusa efeito colateral escondido do
ponto de chamada justamente quando o efeito é ato auditável.

**Grava-se a negativa sempre, e a execução quando ela altera estado.** Uma tela de ação é aberta por
GET a cada navegação e a cada swap do HTMX; registrar tudo encheria o histórico de "atos" que são
leitura, e o ato de verdade se perderia no meio. Então: **método não-seguro autorizado** vira
registro; **qualquer método negado** vira registro, porque tentativa é o que se quer poder
investigar. Ação cujo ato é uma leitura — emitir um documento, por exemplo — força o registro
chamando o mesmo enriquecimento que a view já usa para o alvo.

**Anônimo não gera registro.** Ele é redirecionado ao login antes de haver perfil, unidade e cargo —
e são esses campos que dão sentido à linha. Registrar acesso anônimo é assunto de log de servidor,
não de histórico de ato administrativo.

**O registro diz qual operação foi praticada.** A ação é a competência ("definir atribuições"), não
o que se fez com ela: a mesma rota atribui e remove, concede e revoga. Sem esse campo, o rastro
responde "mexeu na competência" e não responde "tirou a competência de quem" — que é a pergunta que
motiva o registro existir. Texto curto vindo da view, não enumeração central: quem sabe as operações
de uma ação é ela.

**O alvo é uma coisa só; par vira identificador composto.** Atribuir incide sobre unidade **e** ação;
conceder, sobre ação **e** cargo. Em vez de multiplicar colunas de alvo por ação, o `alvo_tipo` diz o
que é o par e o `alvo_identificador` o compõe — o alvo já é texto por natureza (abaixo), e um par
cabe nele.

**O alvo é texto, não relação.** Lote, logradouro e endereço não são models — vêm dos parquets e do
WFS. `GenericForeignKey` não alcança isso; dois campos livres (tipo e identificador) alcançam, e são
opcionais porque ação de menu administrativo não incide sobre entidade territorial nenhuma.

**Cargo e unidade ficam na linha do registro.** Perfil muda de lotação; se o registro só apontasse
para o perfil, a consulta de amanhã descreveria o ato de ontem com a lotação de hoje. Risco residual
aceito: renomear a sigla de uma unidade reescreve como o histórico se lê — não se guarda cópia do
texto para evitar isso.

## Peças de referência a compor
- `@apps/competencias/backends.py` (SPEC 003): o decorator pergunta por `has_perm`, não reimplementa
  a decisão.
- `@apps/competencias/schemas.py` (SPEC 001) → `AcaoImplementada`: é o que o decorator recebe.
- `@apps/competencias/models` (SPEC 002) → `Acao`: alvo da FK do registro.
- `django.contrib.auth.decorators` → `login_required`: o caminho do anônimo é o padrão, não se
  reescreve.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md

# apps/competencias/models/execucao.py
class ExecucaoAcao(models.Model):
    acao = models.ForeignKey(
        Acao,
        on_delete=models.PROTECT,
        related_name="execucoes",
    )
    perfil = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="execucoes",
        null=True,
    )
    # Lotação no momento do ato: perfil muda de unidade e o histórico não pode mudar junto.
    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.PROTECT,
        related_name="execucoes",
    )
    cargo_base = models.ForeignKey(
        CargoBase,
        on_delete=models.PROTECT,
        related_name="execucoes",
    )
    cargo_comissao = models.ForeignKey(
        CargoComissao,
        on_delete=models.PROTECT,
        related_name="execucoes",
        null=True,
    )
    autorizado = models.BooleanField()
    # A ação é a competência; a operação é o que se fez com ela — atribuir não é remover.
    operacao = models.CharField(
        max_length=40,
        blank=True,
    )
    # Entidade territorial não é model: o alvo é texto livre, e ação de menu não tem alvo.
    alvo_tipo = models.CharField(
        max_length=40,
        blank=True,
    )
    alvo_identificador = models.CharField(
        max_length=120,
        blank=True,
    )
    momento = models.DateTimeField(auto_now_add=True)
```

```python
# apps/competencias/protecao.py
def acao_protegida(
    acao: AcaoImplementada,
) -> Callable[[ViewFunc], ViewFunc]:
    """Autoriza pelo contrato e grava a execução — autorizada ou não."""
    ...


def registrar_ato(
    request: HttpRequest,
    operacao: str,
    alvo_tipo: str = "",
    alvo_identificador: str = "",
) -> None:
    """Enriquece o registro que o decorator vai gravar — e força a gravação quando o ato é uma
    leitura, que o decorator sozinho não registraria."""
    ...
```

## Fora de escopo
- Tela de consulta do histórico de execuções: por ora sai pelo admin do Django.
- Retenção, expurgo e exportação do registro.
- Ação assíncrona ou enfileirada — ações são síncronas por padrão (§3.5).
- Registrar leitura de informação pública da ontologia: não é ação e não exige login.
- Aplicar a migração: o agente gera, quem aplica é o usuário (CLAUDE.md §4).

## Testes (TDD)
Todos exercitam view real com `Perfil` gravado e carregam o marker `banco`.

- `test_rota_nega_autenticado_sem_competencia_com_403` — perfil logado sem concessão recebe 403, não
  redirect.
- `test_rota_manda_anonimo_para_o_login` — anônimo é redirecionado, não recebe 403.
- `test_execucao_autorizada_fica_registrada_com_a_lotacao_do_momento` — o POST autorizado guarda
  unidade e cargos vigentes no ato, e mudar a lotação do perfil depois não altera a linha gravada.
- `test_tentativa_negada_fica_registrada` — o 403 também deixa rastro, marcado como não autorizado.
- `test_leitura_autorizada_nao_vira_registro` — o GET autorizado da tela não gera linha; o mesmo GET
  negado gera.
- `test_operacoes_opostas_ficam_distinguiveis` — duas operações da mesma ação geram registros que se
  distinguem pela operação gravada.
- `test_alvo_e_opcional_no_registro` — view que informa o alvo o grava; view que não informa gera
  registro mesmo assim.

## Patches

_Nenhum patch registrado até o momento._
