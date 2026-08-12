---
spec: user_admin/015
versao: v2
atualizado_em: 2026-08-11
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: a substituição passa a dizer o papel — enquanto vigora, o substituto responde pelo cargo do
        afastado e, se o afastado é o titular, dirige a unidade (SPEC 014), sem receber o vínculo de
        titularidade; a unicidade da titularidade deixa de depender da marca de exercício
---

# SPEC user_admin/015 — Exercício e substituição: quem está na cadeira e quem cobre

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como responsável pela DIMAP, quero registrar o impedimento de um servidor e designar quem o
substitui, para que "quem está exercendo o cargo hoje" e "quem responde por ele enquanto está fora"
sejam dados do sistema — e para que a competência acompanhe quem efetivamente está lá, inclusive a
direção da unidade quando quem se afasta é o titular.

## Critérios de aceite
- [ ] Todo perfil tem exercício **gravado** e nasce **em exercício** — vale para qualquer servidor,
      com ou sem cargo em comissão.
- [ ] Criar impedimento pela página do servidor **tira a pessoa de exercício na mesma transação**:
      não existe impedimento gravado com a pessoa ainda na cadeira.
- [ ] Voltar ao exercício é **ato explícito** na mesma página, e ele **encerra a substituição
      vigente** na mesma transação.
- [ ] Só se designa substituto para quem está **fora de exercício e tem cargo em comissão** — o
      caminho não se oferece ao resto, e a rota recusa igual.
- [ ] O substituto é escolhido entre os servidores **da mesma unidade** que estão **em exercício**, e
      nunca é o próprio substituído.
- [ ] Enquanto vigora, o substituto **responde pelo cargo** do afastado — e, se o afastado é o
      **titular** da unidade, é o substituto quem **dirige a unidade** (SPEC 014). A designação
      **não** o torna titular: o vínculo é único e continua com o afastado.
- [ ] Um substituído tem **no máximo uma substituição vigente**, e é o **banco** que recusa a
      segunda. Um mesmo servidor **pode** substituir mais de uma pessoa.
- [ ] A página do servidor mostra o impedimento vigente, **quem o substitui** e **quem ele está
      substituindo** — e marca como **pendência** o caso de estar fora de exercício sem impedimento
      ativo.
- [ ] A regra de quem pode substituir quem é decidida em `services/` e é **testável sem banco**.
- [ ] O design foi aprovado no **mock** antes de qualquer código de aplicação.

## Contexto e decisões de arquitetura

Esta SPEC mexe em persistência (`user_admin`: a marca de exercício no `Perfil` e o model de
substituição), em domínio (`services/domain/exercicio/`) e em interface (uma seção nova e dois modais
na página do servidor). Ela não decide autorização: quem lê o exercício e o transforma em competência
é o épico `autorizacao`.

**Exercício é estado gravado, não derivado do impedimento.** `Perfil.esta_impedido` (SPEC 002)
responde "há impedimento ativo hoje" e segue derivado. A marca de exercício responde outra coisa — se
a pessoa está na cadeira —, vale para **qualquer** servidor e pode cair por motivo que não seja
impedimento. Derivar uma da outra amarraria o exercício a uma única causa e o tornaria dependente da
data de hoje; gravado, ele é coluna que o banco filtra — e é de um filtro, não de um cálculo linha a
linha, que saem a lista de quem pode substituir e a leitura de quem dirige a unidade hoje (SPEC
014).

**O impedimento tira do exercício; o retorno é ato.** Criar impedimento é escrita, e por isso pode
arrastar a saída do exercício na mesma transação. O fim do impedimento não é escrita nenhuma — é uma
data passando —, então nada devolve a pessoa sozinha: reassumir é ato explícito, com caminho próprio,
e é ele que encerra a substituição. Consequência aceita e **exibida**: entre o fim do impedimento e o
retorno, a pessoa fica fora de exercício sem impedimento ativo, e a seção marca isso como pendência
em vez de esconder.

**Substituição é tabela, não campo.** Um campo `substituto` no `Perfil` não diria desde quando, e
encerrar seria apagar. A tabela guarda substituído, substituto e período; `data_fim` nulo é a
vigente, e é sobre ela que o índice parcial garante uma só por substituído — condição de coluna da
própria linha, que o banco alcança. O histórico sai de graça.

**Sem cargo em comissão não há o que substituir.** Substituir é cobrir a competência de um cargo em
comissão; de quem não tem, não há competência a cobrir.

**Quem substitui ocupa o papel, não recebe o vínculo.** Enquanto vigora, o substituto responde pelo
que o cargo do afastado responde — e, quando o afastado é o titular, isso é dirigir a unidade (SPEC
014). Nada é marcado no substituto: a titularidade é vínculo único por unidade e continua com quem
se afastou, que é o que faz o retorno devolver a direção sem negociar com ninguém. Daí também que do
**substituto** não se exija cargo em comissão nem o mínimo do tipo da unidade: quem cobre costuma
ser subordinado, e exigir cargo esvaziaria a designação justamente nas unidades pequenas.

**Mesma unidade, e em exercício.** A competência é cargo × unidade (§3.5): quem cobre precisa estar
na unidade cuja direção ou cujos processos vai exercer. E precisa estar em exercício — designar quem
está fora seria criar o vazio na origem.

**A designação cruza linhas, então vive no `clean()` — e a decisão, no domínio.** Substituído → cargo
em comissão e exercício; substituto → unidade e exercício: é comparação entre duas linhas de
`Perfil`, que nenhuma `CheckConstraint` alcança (só a identidade entre as duas pontas alcança, e essa
vira constraint). O predicado fica em `services/domain/exercicio/` sobre DTO, para ser testável sem
banco (§3.3).

**Esta é a primeira tela do `user_admin` que grava, e a rota nasce aberta por exceção declarada.**
§3.5 exige rota de ação protegida; autenticação ainda não existe no projeto, e a listagem de
servidores (SPEC 013) já abriu essa exceção nos mesmos termos. Registrar a execução do ato depende do
registro da SPEC `autorizacao/004`. As duas coisas entram com o épico `autorizacao` — até lá a
exceção fica declarada aqui, num lugar só, e não espalhada em código.

**A titularidade vem depois e se apoia nisto, mas não depende dele para ser única.** A SPEC 014
garante um titular por unidade num índice que só olha para a marca de titular; o que ela consome
daqui é a leitura de quem dirige hoje — o titular em exercício, ou o substituto dele — e o alarme de
unidade sem direção. Esta SPEC grava exercício e substituição, e não sabe o que é titular.

## Peças de referência a compor
- `@apps/user_admin/models/impedimentos.py` → `Impedimento` e `TipoImpedimento`: o impedimento já
  existe e não muda de forma; o que falta é criá-lo pela tela e ligá-lo ao exercício.
- `@apps/user_admin/models/user.py` → `Perfil.esta_impedido`: segue derivado, ao lado da marca
  gravada — a divergência entre os dois é a pendência de retorno.
- `@templates/user_admin/perfil_form.html` e os partials `_secao_identificacao.html` /
  `_secao_lotacao.html`: a seção nova é mais uma seção do mesmo organismo, não uma tela.
- `@templates/user_admin/partials/_modal_nova_unidade.html`: modal por checkbox nativo, irmão do
  formulário e nunca dentro dele (SPEC 012) — é o padrão que os dois modais novos repetem.
- `@apps/user_admin/schemas.py`: DTO construído na view, com o `PydanticValidationMiddleware`
  respondendo pelo erro; nada de `try/except` na view.
- `@apps/user_admin/views.py` + `@apps/user_admin/context.py`: view fina e função de contexto — o
  padrão do app.
- `@apps/user_admin/ficticios.py`: o andaime da área administrativa passa a deixar impedimento e
  substituição exercitáveis.
- Skills `componentes-frontend` (Atomic Design e o styleguide), `escrever-testes` (marker `banco`) e
  `test-django-views`.

## Mock de validação
`SPECS/user_admin/015-mock-exercicio-e-substituicao.html`, sobre o canvas administrativo vivo. A
seção de exercício nos **sete** estados que precisa cobrir — em exercício; afastado sem substituto;
**titular afastado sem substituto** (o alarme de unidade sem direção, que só ganha código com a SPEC
014); afastado com substituto; retorno pendente; afastado sem cargo em comissão (onde o caminho de
designar **não tem peça**, em vez de botão desabilitado); e o outro lado, a página de quem substitui.
Mais os **três** modais: registrar impedimento, designar substituto e retornar ao exercício — o
último existe porque o ato tem um efeito que não está na tela, encerrar a substituição vigente.

**A escala semântica fica fixada aqui**, e vale para as duas SPECs: verde é estar na cadeira; âmbar é
a pessoa fora dela, tanto afastada quanto com retorno pendente; **vermelho é só a unidade sem
direção** — a única condição da tela que trava competência administrativa. O selo do exercício
descreve a pessoa e nunca fica vermelho; quem escala é a tarja, porque quem está errado é o estado da
unidade, não o afastamento.

Duas moléculas nascem aqui: `.linha-pessoa` (pessoa identificada em uma linha, que se repete no
substituto designado e em quem se substitui) e `.tarja-vinculo` (a placa clara que emoldura um
vínculo vigente dentro do poço da seção, com as variantes `-pendente` e `-critica`). **Escolher o
substituto não inventa peça**: é o campo de seleção de vidro da SPEC 011 (`data-select-onsen`), o
mesmo da lotação — lista fechada de uma pessoa é exatamente o que ele resolve, com filtro por texto,
teclado e o `<select>` seguindo como o campo.

O único token novo é de raio: **`--radius-placa` (0.625rem)**, entre `--radius-field` e
`--radius-box`. A placa assentada dentro de um poço não é campo nem caixa — quer ficar retangular,
mas quina viva não pertence a um material em que toda aresta é luz. Vira token, e não medida solta
na molécula, porque a titularidade (SPEC 014) assenta placas no mesmo poço e elas precisam da mesma
quina. Aprovado o mock, as moléculas migram para `static/src/tema-dimap.dev.css` na camada de
moléculas, o raio entra em `html[data-theme="dimap"]` junto dos outros, e as peças são renderizadas
no styleguide da skill `componentes-frontend`, antes de qualquer template da aplicação usá-las.

> Consumo do raio: em Tailwind 4 é `border-radius: var(--radius-placa)` ou `rounded-(--radius-placa)`.
> O `rounded-[--x]` da v3 emite `border-radius: --x`, inválido, e cai em **raio zero** — os mocks de
> `autorizacao/006`, `007` e `008` estão de quina viva por isso e são corrigidos no mesmo porte.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md

# apps/user_admin/models/user.py
class Perfil(AbstractBaseUser, PermissionsMixin):
    # Gravado, não derivado: o fim do impedimento é uma data passando, e data que passa não escreve.
    em_exercicio = models.BooleanField(default=True)
```

```python
# apps/user_admin/models/substituicao.py
class Substituicao(models.Model):
    substituido = models.ForeignKey(
        "user_admin.Perfil",
        on_delete=models.PROTECT,
        related_name="substituicoes_recebidas",
    )
    substituto = models.ForeignKey(
        "user_admin.Perfil",
        on_delete=models.PROTECT,
        related_name="substituicoes_exercidas",
    )
    data_inicio = models.DateField()
    # Nulo = vigente; é sobre ele que o índice parcial garante uma substituição por substituído.
    data_fim = models.DateField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(substituto=F("substituido")),
                name="substituicao_nao_e_de_si_mesmo",
            ),
            models.UniqueConstraint(
                fields=["substituido"],
                condition=Q(data_fim__isnull=True),
                name="substituido_tem_uma_substituicao_vigente",
            ),
        ]
```

```python
# services/domain/exercicio/designacao.py
class ParteDaSubstituicao(BaseModel):
    model_config = ConfigDict(frozen=True)

    perfil_id: int
    unidade_id: int
    em_exercicio: bool
    tem_cargo_comissao: bool


class Designacao(BaseModel):
    model_config = ConfigDict(frozen=True)

    substituido: ParteDaSubstituicao
    substituto: ParteDaSubstituicao


class AvaliadorDesignacao:
    """Quem pode cobrir quem. Sem Django: a regra é a mesma no clean, na view e no teste."""

    def __call__(self, designacao: Designacao) -> bool: ...
```

```python
# apps/user_admin/exercicio.py
def registrar_impedimento(perfil: Perfil, impedimento: Impedimento) -> None:
    """Grava o impedimento e tira do exercício na mesma transação: não existe impedimento gravado
    com a pessoa ainda na cadeira."""
    ...


def retornar_ao_exercicio(perfil: Perfil) -> None:
    """Devolve à cadeira e encerra a substituição vigente na mesma transação."""
    ...
```

## Fora de escopo
- Titularidade e o efeito do exercício sobre ela — SPEC 014, que vem depois desta.
- Cadeia de substituição: substituto do substituto, e redesignação automática quando o substituto se
  impede. O substituto fora de exercício não cobre ninguém — a leitura da direção (SPEC 014) enxerga
  isso e acende o alarme —, mas nada entra no lugar dele sozinho.
- Editar, encerrar ou excluir impedimento pela tela — esta iteração só **cria**.
- Reagir à passagem do tempo: nada devolve ninguém ao exercício sozinho, e não há rotina que
  reconcilie a marca com os impedimentos vencidos (ver Contexto).
- Autenticação, autorização por perfil e registro da execução do ato — épico `autorizacao`.
- Qualquer efeito de autorização decorrente do exercício ou da substituição — épico `autorizacao`.
- Aplicar a migração: o agente gera, quem aplica é o usuário (CLAUDE.md §4).

## Testes (TDD)
Os dois primeiros são domínio puro e rodam na suíte padrão; os demais carregam o marker `banco`,
declarado em `markers_obrigatorios`.

- `test_substituto_precisa_da_mesma_unidade_e_do_exercicio` — recusa substituto de outra unidade,
  recusa quem está fora de exercício e recusa o próprio substituído; aceita o par válido. Sem banco.
- `test_so_substitui_quem_esta_fora_com_cargo_em_comissao` — substituído em exercício é recusado, e
  substituído sem cargo em comissão também. Sem banco.
- `test_criar_impedimento_tira_do_exercicio` — depois da criação pela página, o perfil está fora de
  exercício, e o impedimento nunca fica gravado sem isso. *(marker `banco`)*
- `test_retorno_ao_exercicio_encerra_a_substituicao` — o perfil volta a exercer e a substituição
  vigente ganha término no mesmo passo. *(marker `banco`)*
- `test_substituido_nao_admite_duas_substituicoes_vigentes` — a segunda designação sem encerrar a
  primeira é recusada pelo banco. *(marker `banco`)*
- `test_secao_mostra_substituto_e_pendencia_de_retorno` — a seção traz o nome de quem substitui, e
  acusa a pendência quando não há impedimento ativo e a pessoa segue fora. *(marker `banco`)*

## Patches

_Nenhum patch registrado até o momento._
