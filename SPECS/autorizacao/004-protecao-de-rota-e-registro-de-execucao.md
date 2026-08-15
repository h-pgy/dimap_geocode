---
spec: autorizacao/004
versao: v4
atualizado_em: 2026-08-14
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: registro passa a identificar a operação praticada; grava toda negativa e as execuções que
    alteram estado, não a leitura autorizada de tela; anônimo sai do critério de registro
  - v3: o registro passa a dizer por quem o autor respondia — com a substituição (SPEC
    user_admin/015) o ato pode ser praticado pela competência do cargo de outra pessoa, e só o
    cargo do autor descreveria o ato errado
  - v4: sem mudança de escopo — a SPEC foi reescrita no formato de seções numeradas da skill
    `specs`, com a justificativa toda concentrada em Caveats
---

# SPEC autorizacao/004 — Proteção de rota e registro de execução do ato

## 1 · User story
**Requisito não-funcional** — a competência da SPEC 003 vira barreira na rota e rastro no banco: todo
ato administrativo praticado na plataforma passa a ter autor conhecido, e toda tentativa negada passa a
ser investigável.

## 2 · Condições de pronto
- [ ] Rota de ação **nega com 403** o perfil autenticado sem competência, e manda o **anônimo para o
      login** pelo caminho padrão do Django.
- [ ] Toda execução autorizada que **altera estado** fica registrada: quem, com qual cargo e unidade
      **no momento do ato**, qual ação, **qual operação**, quando.
- [ ] Quando o autor pratica o ato **cobrindo alguém**, o registro diz **por quem ele respondia**;
      quando não, o campo fica vazio.
- [ ] Toda tentativa **negada de perfil autenticado** fica registrada, inclusive a de leitura.
- [ ] Duas operações opostas da mesma ação — conceder e revogar, atribuir e remover — ficam
      **distinguíveis** no registro.
- [ ] A view pode acrescentar ao registro **sobre o que** o ato incidiu; esquecer de fazê-lo não impede
      o registro de existir.
- [ ] A proteção é declarada com o **contrato da ação**, não com uma string solta: slug inexistente é
      erro de import, não negação silenciosa.

## 3 · Domínio
O ato praticado é a entidade nova, e ela guarda o que descreve o ato **no dia em que foi praticado** —
não o que o cadastro diz hoje.

**`apps/competencias/models/execucao.py`**
```python
class ExecucaoAcao(models.Model):
    acao = models.ForeignKey(Acao, on_delete=models.PROTECT, related_name="execucoes")
    perfil = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="execucoes",
        null=True,
    )
    # Lotação no momento do ato: perfil muda de unidade, e o histórico não pode mudar junto.
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, related_name="execucoes")
    cargo_base = models.ForeignKey(CargoBase, on_delete=models.PROTECT, related_name="execucoes")
    cargo_comissao = models.ForeignKey(
        CargoComissao,
        on_delete=models.PROTECT,
        related_name="execucoes",
        null=True,
    )
    # Ato praticado cobrindo alguém: a pessoa, nunca a linha da Substituicao, que é encerrada e
    # reaberta ao longo do tempo.
    substituindo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="execucoes_cobertas",
        null=True,
        blank=True,
    )
    autorizado = models.BooleanField()
    # A ação é a competência; a operação é o que se fez com ela — atribuir não é remover.
    operacao = models.CharField(max_length=40, blank=True)
    # Entidade territorial não é model (vem de parquet e WFS): o alvo é texto livre. Par de alvos
    # vira identificador composto, em vez de multiplicar colunas por ação.
    alvo_tipo = models.CharField(max_length=40, blank=True)
    alvo_identificador = models.CharField(max_length=120, blank=True)
    momento = models.DateTimeField(auto_now_add=True)
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`AcaoImplementada`](001-catalogo-de-acoes-em-codigo.md) — "qual ação esta rota executa?"; é o objeto
  que o decorator recebe, não o slug.
- [`Acao` projetada](002-competencia-no-banco.md) — o alvo da FK do registro.
- [`CompetenciaBackend`](003-avaliador-e-backend-de-autorizacao.md) — "este perfil pode executar esta
  ação?", já respondida; o decorator pergunta por `has_perm` e não reimplementa nada.
- [`substituicao_que_exerce`](../user_admin/015-exercicio-e-substituicao.md) — "quem o autor estava
  cobrindo no momento do ato?".

## 4 · Fora de escopo
- Tela de consulta do histórico de execuções — por ora sai pelo admin do Django; sem dono ainda.
- Retenção, expurgo e exportação do registro — sem dono ainda.
- Ação assíncrona ou enfileirada — ações são síncronas por padrão (§3.5).
- Registrar leitura de informação pública da ontologia — não é ação e não exige login.
- Gravar a unidade **em que o ato produziu efeito** quando ela não é a de lotação do autor — sem dono
  ainda (§7).

## 5 · Peças de referência a compor
- `@apps/competencias/backends.py` (SPEC 003) → `has_perm`: a decisão de acesso, já resolvida.
- `@apps/competencias/consulta.py` (SPEC 003) → `cadeiras_do_perfil`: quem o autor cobre já foi
  resolvido ali, na montagem da avaliação.
- `@apps/user_admin/exercicio.py` → `substituicao_que_exerce`: o substituído é `impedimento.perfil`.
- `@apps/competencias/schemas.py` (SPEC 001) → `AcaoImplementada`: é o que o decorator recebe.
- `@apps/competencias/models` (SPEC 002) → `Acao`: alvo da FK do registro.
- `django.contrib.auth.decorators` → `login_required`: o caminho do anônimo é o padrão.
- Skills: `escrever-testes`, `test-django-views`.

## 6 · Snippets

**`apps/competencias/protecao.py`** — a barreira e o rastro no mesmo decorator: autorizar sem registrar
deixaria o rastro dependente de disciplina de quem escreve a view.
```python
def acao_protegida(acao: AcaoImplementada) -> Callable[[ViewFunc], ViewFunc]:
    """Autoriza pelo contrato e grava a execução — autorizada ou não.

    403 para autenticado, login para anônimo: redirecionar quem já está logado não diz nada, e para
    o HTMX o redirect vira a página de login trocada dentro de um fragmento.

    Grava-se SEMPRE a negativa, e a execução quando ela altera estado: tela de ação é aberta por GET
    a cada navegação e a cada swap, e registrar tudo afogaria o ato de verdade em leitura.
    """
    ...


def registrar_ato(
    request: HttpRequest,
    operacao: str,
    alvo_tipo: str = "",
    alvo_identificador: str = "",
) -> None:
    """Enriquece o registro que o decorator vai gravar — e força a gravação quando o ato é uma
    leitura (emitir um documento, por exemplo), que o decorator sozinho não registraria.

    Só a view sabe sobre o que o ato incidiu; o registro existe mesmo se ela não disser."""
    ...
```

**`apps/competencias/registro_execucao.py`** — a linha gravada, com a lotação do momento e quem o autor
cobria.
```python
def gravar_execucao(
    perfil: Perfil,
    acao: AcaoImplementada,
    autorizado: bool,
    operacao: str = "",
    ...
) -> ExecucaoAcao:
    # A competência que abriu a rota pode ser a de outra pessoa: sem isto a linha descreveria o ato
    # pelo cargo errado, e um subordinado sem chefia figuraria distribuindo competência.
    substituicao = substituicao_que_exerce(perfil)
    ...
```

**`apps/competencias/views.py`** — como a view usa as duas peças.
```python
@acao_protegida(ACAO_DEFINIR_ATRIBUICAO)
def definir_atribuicao(request: HttpRequest) -> HttpResponse:
    ...
    registrar_ato(
        request,
        operacao="atribuir",
        alvo_tipo="unidade_acao",
        alvo_identificador=f"{unidade.sigla}:{acao.slug}",
    )
```

## 7 · Caveats
**O registro é gravado pelo decorator, e não por signal.** Signal esconderia do ponto de chamada o
efeito que mais precisa ser visível — e o CLAUDE.md §3.2 o recusa justamente quando o efeito é ato
auditável. Custo: o decorator passa a fazer duas coisas, autorizar e gravar, e quem ler a view precisa
saber que a segunda acontece sem aparecer ali.

**Grava-se toda negativa e só a execução que altera estado.** Uma tela de ação é aberta por GET a cada
navegação e a cada swap do HTMX, e registrar tudo encheria o histórico de "atos" que são leitura. Custo:
ação cujo ato **é** uma leitura — emitir um documento — só fica registrada se a view chamar
`registrar_ato`, e esquecer disso não quebra nada visivelmente.

**Acesso anônimo não gera registro.** Ele é redirecionado ao login antes de haver perfil, unidade e
cargo, que são os campos que dão sentido à linha. Custo: varredura de URL por quem não está logado não
aparece no histórico de atos — só no log do servidor.

**O alvo é texto livre, em dois campos opcionais.** Lote, logradouro e endereço não são models — vêm dos
parquets e do WFS —, e `GenericForeignKey` não os alcança. Custo: nada garante que o identificador
gravado ainda exista nem que esteja bem formado, e consultar o histórico por alvo é busca em texto.

**Cargo e unidade são copiados para a linha, mas a sigla não.** Sem a cópia, a consulta de amanhã
descreveria o ato de ontem com a lotação de hoje. Custo aceito: renomear a sigla de uma unidade reescreve
como todo o histórico dela se lê.

**A unidade gravada é a de lotação do autor, não aquela em que o ato produziu efeito.** Quem cobre alguém
de outra unidade (SPEC `user_admin/015`) pratica o ato pela cadeira do coberto, e fazer o decorator
descobrir qual cadeira autorizou exigiria o avaliador devolver a origem de cada slug liberado. Custo: nesse
caso a unidade da linha descreve onde o autor está lotado, e chegar à unidade do ato exige passar por
`substituindo`.

## 8 · Testes (TDD)
Todos exercitam view real com `Perfil` gravado e carregam o marker `banco`.

- `test_rota_nega_autenticado_sem_competencia_com_403` — perfil logado sem concessão recebe 403, não
  redirect. *(marker `banco`)*
- `test_rota_manda_anonimo_para_o_login` — anônimo é redirecionado, não recebe 403, e não deixa linha.
  *(marker `banco`)*
- `test_execucao_autorizada_fica_registrada_com_a_lotacao_do_momento` — o POST autorizado guarda unidade
  e cargos vigentes no ato, e mudar a lotação do perfil depois não altera a linha gravada.
  *(marker `banco`)*
- `test_ato_praticado_em_substituicao_diz_por_quem_responde` — o substituto que age pela competência do
  afastado deixa gravado quem ele cobria; quem age por competência própria deixa o campo vazio.
  *(marker `banco`)*
- `test_tentativa_negada_fica_registrada` — o 403 também deixa rastro, marcado como não autorizado.
  *(marker `banco`)*
- `test_leitura_autorizada_nao_vira_registro` — o GET autorizado da tela não gera linha; o mesmo GET
  negado gera. *(marker `banco`)*
- `test_operacoes_opostas_ficam_distinguiveis` — duas operações da mesma ação geram registros que se
  distinguem pela operação gravada. *(marker `banco`)*
- `test_alvo_e_opcional_no_registro` — view que informa o alvo o grava; view que não informa gera registro
  mesmo assim. *(marker `banco`)*
