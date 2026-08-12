---
spec: user_admin/014
versao: v7
atualizado_em: 2026-08-11
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: a unicidade passa a ser do titular em exercício — titular impedido não exerce e outro
        pode ser marcado ao lado dele; o índice parcial sai e a garantia migra para validação
        e domínio, preparando a SPEC de substituição
  - v3: exercício e substituição saem daqui para a SPEC 015, que vem antes desta; com a marca de
        exercício gravada no Perfil o índice parcial volta, agora condicionado às duas colunas
  - v4: a página do servidor passa a acusar a unidade sem direção — titular afastado sem substituto
        designado; o desenho já está aprovado no mock da SPEC 015
  - v5: a unicidade volta a ser do vínculo — um titular por unidade, exercendo ou não; o titular
        afastado não abre vaga para um segundo, quem cobre é o substituto da SPEC 015, que ocupa o
        papel sem receber o vínculo; entra a leitura derivada de quem dirige hoje e sai a recusa de
        retorno, que só existia por causa do segundo titular
  - v6: a unidade sem titular passa a ser estado admitido e nomeado — atributo da própria unidade,
        que a leitura da direção distingue do titular afastado sem substituto; a página da unidade
        ganha a seção de direção, com a bandeja de indicadores e o alarme em vermelho; definir,
        trocar e destituir titular viram modal, e o management command sai
  - v7: a interface sai daqui e vira a SPEC 016 — a página da unidade não existia (a 012 deixou
        editar unidade fora de escopo), e criá-la é iteração própria; esta SPEC fica com o dado, a
        regra e os atos, e o mock passa a ser o da 016
---

# SPEC user_admin/014 — Titular da unidade: um por unidade, com que cargo e quem dirige hoje

> A interface que mostra tudo isto — a página da unidade, a seção de direção e os três modais — é a
> **SPEC 016**, que vem depois desta. Aqui ficam o dado, a regra e os atos.

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como responsável pela DIMAP, quero que cada unidade tenha um titular inequívoco, com cargo
compatível com o porte dela, para que "quem dirige a unidade hoje" seja um dado do sistema — mesmo
quando o titular está afastado e quem responde é o substituto dele, e mesmo quando a unidade está
sem titular nenhum, que é o que a tela da SPEC 016 acusa — e para que a administração de
competências decorra da direção em vez de uma lista nominal em código.

## Critérios de aceite
- [ ] Uma unidade tem **no máximo um titular**, e é o **banco** que recusa o segundo. O afastamento
      do titular **não abre vaga**: quem cobre é o **substituto** (SPEC 015), nunca um segundo
      titular marcado ao lado dele.
- [ ] A unidade **pode ficar sem titular**, e isso é **atributo dela**: a unidade responde "não
      tenho titular" sem que nada no sistema impeça o estado — é o que acontece entre a exoneração
      de um titular e a nomeação do seguinte.
- [ ] **Quem dirige a unidade hoje** tem **quatro** respostas: o titular em exercício; o substituto
      dele; **sem direção** (há titular, está fora e ninguém cobre); **sem titular** (a vaga).
      Leitura derivada das marcas, decidida em `services/` e **testável sem banco**.
- [ ] Cada **tipo de unidade** declara o nível mínimo de cargo em comissão exigido do titular;
      **ausência de mínimo significa que só a alta administração serve**.
- [ ] Só titulariza quem tem cargo em comissão **de chefia** e satisfaz o mínimo do tipo da própria
      unidade — alta administração satisfaz qualquer tipo. Perfil sem cargo em comissão nunca
      titulariza; do **substituto** nada disso se exige, porque ele ocupa o papel sem receber o
      vínculo. A regra é decidida em `services/` e é **testável sem banco**.
- [ ] **Trocar o titular é uma operação só**: o titular anterior é destituído na mesma transação —
      **inclusive afastado** —, nunca restando dois marcados nem uma janela sem nenhum.
- [ ] **Destituir o titular é ato próprio**, e deixa a unidade sem titular — não se exige um
      substituído no ato para poder destituir.
- [ ] Rebaixar o titular, ou mudar a unidade para um tipo que ele não satisfaz, é **recusado na
      validação** — não fica titular inválido gravado.
- [ ] O seed de unidades declara o mínimo de cada tipo, e os servidores fictícios nascem com
      titulares marcados — e ao menos uma unidade fictícia nasce **sem titular**, para a tela da
      SPEC 016 ser exercitável no estado que ela existe para acusar.
- [ ] **Definir, trocar e destituir titular** são funções em transação, chamadas pela tela (SPEC
      016) e pelos fictícios — não há segunda porta para a mesma escrita.

## Contexto e decisões de arquitetura

Esta SPEC mexe em persistência (`user_admin`) e em domínio (`services/domain/titularidade/`) — a
interface é a SPEC 016. Não decide autorização nenhuma: quem lê a titularidade e a transforma em
competência é o épico `autorizacao` (SPEC 003) — e o que ele passa a ter para ler é **quem responde
pela direção**, não a marca `e_titular` crua.

**Titularidade não é o mesmo que cargo de chefia.** `CargoComissao.e_chefia` é atributo do catálogo
de cargos: diz que o cargo é de natureza chefia, não que a pessoa dirige aquela unidade. Hoje uma
unidade pode ter zero chefias lotadas (vaga) ou várias (um diretor de divisão e um chefe de seção na
mesma lotação, o que o seed de cargos torna comum) — com isso, "quem dirige a DIMAP-1" não é
computável. A titularidade é o vínculo que falta.

**O titular é um só, e o afastamento não o desfaz.** Titular é o vínculo de direção da unidade;
exercício (SPEC 015) diz se ele está na cadeira **hoje**. Quando não está, quem responde é o
**substituto** designado, que ocupa o papel sem receber o vínculo — não existe segundo titular
marcado ao lado do primeiro. Admiti-lo devolveria justamente a ambiguidade que esta SPEC existe para
acabar: duas pessoas marcadas como quem dirige a mesma unidade. Cobrir é temporário e se desfaz no
retorno (SPEC 015); trocar o titular é ato definitivo e destitui o anterior.

**Booleana no `Perfil`, com índice único parcial por unidade.** O titular é necessariamente lotado na
unidade que dirige — e com a marca no perfil isso sai de graça, porque a unidade é a dele. Uma FK
`chefe` na `Unidade` admitiria titular lotado em outro ramo e fecharia um ciclo `Unidade`↔`Perfil`
que atrapalha seed e migração inicial — descartada. Um model de mandato com início e fim daria
histórico, mas a escala não paga o preço.

**A condição do índice é só `e_titular`, porque a unicidade é do vínculo.** Uma coluna da própria
linha, que o banco alcança: recusa o segundo titular haja ou não afastamento, e nada do que a
substituição faça mexe nela.

**A unidade sem titular é estado admitido, e o atributo é da unidade.** Entre a exoneração de um
titular e a nomeação do seguinte a unidade fica vaga — é rotina do organograma, não anomalia, e nada
aqui impede o estado. Mas ele não é uma ausência silenciosa: é **coisa que a unidade responde** —
`Unidade.titular` devolve o perfil ou `None`, e a vaga entra na leitura da direção com nome próprio,
para a tela poder acusá-la em vez de mostrar campo em branco. É atributo
**derivado**, não coluna: quem titulariza está nas linhas de `Perfil`, e uma marca `sem_titular` na
`Unidade` seria a mesma informação gravada duas vezes, livre para divergir a cada destituição — o
mesmo motivo pelo qual não se grava um "exercente". Precedente da forma: `Perfil.esta_impedido`.

**A direção de hoje é leitura, e tem quatro respostas.** Dirige a unidade o titular em exercício; se
ele está fora, o substituto vigente que esteja em exercício. Faltando os dois, a unidade não tem
quem responda por ela — e a causa importa para quem lê: **sem titular** é a vaga, e a saída é
nomear; **sem direção** é o titular afastado que ninguém cobre, e a saída é designar substituto na
página dele. Por isso o avaliador devolve o estado, não um booleano: um `bool` obrigaria a tela a
reconstruir a causa a partir das marcas cruas, que é justamente o que o domínio existe para evitar.
O predicado fica em `services/domain/titularidade/` sobre DTO, ao lado da adequação, e é o mesmo que
a seção da SPEC 015 consulta para acender o alarme.

**Quem mostra as quatro respostas é a SPEC 016.** O alarme da SPEC 015 mora na página do servidor e
depende de haver um servidor afastado a quem ancorá-lo — na vaga não há ninguém. A página da unidade
é o único lugar onde as quatro respostas cabem juntas, e criá-la é iteração própria: a SPEC 012
deixou editar unidade fora de escopo, e hoje só existe a tela de cadastro. Esta SPEC entrega a
leitura; a 016, a tela que a consome.

**O retorno do titular não esbarra em ninguém.** Com um titular só, reassumir o exercício (SPEC 015)
é sempre aceito pela titularidade: encerra a substituição vigente e devolve a direção a quem nunca
deixou de ser titular. Não há segundo titular no lugar para recusá-lo.

**O mínimo mora no tipo de unidade, e é anulável.** A escala do cargo em comissão vai até 6, o
organograma vai até o nível 9: para Subsecretaria, Secretaria Executiva e Gabinete **nenhum nível
serve** — só alta administração. Anulável resolve isso sem inventar sentinela, e a leitura fica a
mesma dos dois lados: `nivel` nulo em `CargoComissao` é "está acima da escala"; mínimo nulo em
`TipoUnidade` é "exige estar acima dela".

O mínimo **não é derivável** do nível do tipo: Departamento e Coordenação são níveis diferentes com
o mesmo mínimo (5), e Coordenadoria e Assessoria são o mesmo nível com mínimos diferentes (6 e 5,
porque Chefe de Assessoria Técnica I é CDA-V). É dado do organograma, por isso é campo.

**Nível sem chefia não basta.** Assessor VI é CDA-VI e não é chefia — com regra só de nível, ele
titularizaria uma Coordenadoria. A adequação é `e_chefia` **e** (`alta_administracao` **ou**
`nivel >= mínimo do tipo`).

**A adequação cruza três tabelas, então vive no `clean()` — e a decisão, no domínio.** Perfil → cargo
e perfil → unidade → tipo: nenhuma `CheckConstraint` alcança, o mesmo caso que `Unidade.clean()` já
resolve e documenta. O predicado em si fica em `services/domain/titularidade/` sobre DTO, para ser
testável sem banco (§3.3); os `clean()` do `Perfil` e da `Unidade` o chamam — os dois, porque a
adequação quebra tanto quando o cargo muda quanto quando o tipo da unidade muda.

Consequência aceita: a **unicidade** do titular é garantia de banco; a **adequação** é garantia de
validação, e um `update()` em massa a fura. É o mesmo contrato que a hierarquia de unidades já tem.

**A adequação é requisito do vínculo, não de quem cobre.** Substituir é responder pelo cargo de
alguém enquanto ele está fora, não titularizar: o substituto costuma ser subordinado sem cargo de
chefia, e exigir dele o mínimo do tipo esvaziaria a designação nas unidades pequenas (SPEC 015).
Consequência aceita: durante o afastamento, a unidade pode ser dirigida por quem não poderia ser
titular dela.

**Trocar titular é uma operação; destituir é outra.** Com o índice parcial, marcar o novo antes de
destituir o anterior levanta `IntegrityError`: destituir e marcar viram um passo só, em
`transaction.atomic()`. O anterior é destituído **mesmo afastado** — a troca é o caminho para o
afastamento que virou definitivo, e o temporário já tem o dele. A substituição do destituído não é
encerrada: ela cobre o cargo dele, e a direção passa a seguir o novo titular pela leitura derivada.
Destituir sem substituir é ato próprio e é o que abre a vaga — exigir um sucessor no mesmo gesto
faria o sistema recusar exatamente a situação que ele precisa saber representar.

**Editar o mínimo do tipo não revalida quem já está lá.** Aceito: tipo de unidade é catálogo de
seed, praticamente imutável, e uma revalidação retroativa custaria mais do que o risco que evita.

**Titular não herda para baixo.** Dirigir a coordenadoria não é dirigir as divisões dela. O alcance
de um titular sobre a subárvore é regra do épico `autorizacao`, e alcançar não é titularizar.

**O ato é função, e há um caminho só.** `definir_titular` e `destituir_titular` são chamadas pela
tela (SPEC 016) e pelo `ficticios.py`, que já é o andaime da área administrativa. Um management
command paralelo seria uma segunda porta para a mesma escrita, com a regra a manter nos dois lugares
— descartado. A rota que as chama nasce aberta pela mesma exceção ao §3.5 declarada na SPEC 015,
com autenticação, autorização e registro entrando com o épico `autorizacao`.

## Peças de referência a compor
- `@apps/user_admin/models/user.py` → `Perfil`: `unidade` e `cargo_comissao` (anulável) já são a
  lotação; a marca de titular entra aqui.
- `@apps/user_admin/models/cargos.py` → `CargoComissao` (`e_chefia`, `nivel`, `alta_administracao`)
  e o precedente de `CheckConstraint` espelhada no `clean()`.
- `@apps/user_admin/models/unidade.py` → `TipoUnidade` e `Unidade.clean()`: precedente exato da
  regra que cruza tabela e por isso não vira constraint.
- `Perfil.em_exercicio` e a `Substituicao` (SPEC 015, **pré-requisito desta**): as duas marcas de
  que a leitura da direção é feita, e o ato de retorno que devolve a cadeira ao titular.
- `@apps/user_admin/seeds/unidades.py` + `@data/seed/unidades.json`: os tipos ganham o mínimo, sem
  mudar a forma da carga; skill `seeds`.
- `@apps/user_admin/ficticios.py`: o andaime que torna a área administrativa exercitável — passa a
  marcar titulares, e a deixar uma unidade vaga.
- Skill `escrever-testes` (marker `banco`).

## Mock de validação
Não há: esta SPEC não entrega interface. O desenho da seção de direção, da bandeja de indicadores e
dos três modais está no mock da **SPEC 016** (`SPECS/user_admin/016-mock-pagina-da-unidade.html`), e
é lá que ele é aprovado.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md

# apps/user_admin/models/unidade.py
class TipoUnidade(models.Model):
    # Nulo = nenhum nível serve: só alta administração titulariza este tipo.
    nivel_minimo_titular = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(NIVEL_MINIMO),
            MaxValueValidator(NIVEL_MAXIMO),
        ],
    )
```

```python
# apps/user_admin/models/user.py
class Perfil(AbstractBaseUser, PermissionsMixin):
    e_titular = models.BooleanField(default=False)

    class Meta:
        constraints = [
            # A unicidade é do vínculo: um titular por unidade, exercendo ou não. Quem cobre o
            # afastado é substituto (SPEC 015), não um segundo marcado.
            models.UniqueConstraint(
                fields=["unidade"],
                condition=Q(e_titular=True),
                name="unidade_tem_um_titular",
            ),
        ]
```

```python
# services/domain/titularidade/direcao.py
class Direcao(StrEnum):
    TITULAR = "titular"
    SUBSTITUTO = "substituto"
    # Há titular, está fora e ninguém cobre: designar substituto resolve.
    SEM_DIRECAO = "sem_direcao"
    # Ninguém titulariza a unidade: só nomear resolve.
    SEM_TITULAR = "sem_titular"


class EstadoDaDirecao(BaseModel):
    model_config = ConfigDict(frozen=True)

    tem_titular: bool
    titular_em_exercicio: bool
    # Sem substituto designado, `False`: quem não existe não cobre ninguém.
    substituto_do_titular_em_exercicio: bool


class AvaliadorDirecao:
    """Quem dirige a unidade hoje — e, quando ninguém dirige, qual das duas faltas é."""

    def __call__(self, estado: EstadoDaDirecao) -> Direcao: ...
```

```python
# apps/user_admin/models/unidade.py
class Unidade(models.Model):
    # A vaga é a ausência do vínculo, e quem responde por ela é a unidade. Derivado, não coluna:
    # gravar duplicaria as linhas de Perfil. Precedente: Perfil.esta_impedido.
    @property
    def titular(self) -> "Perfil | None": ...
```

```python
# services/domain/titularidade/requisito.py
class RequisitoTitularidade(BaseModel):
    model_config = ConfigDict(frozen=True)

    e_chefia: bool
    alta_administracao: bool
    nivel_cargo: int | None
    nivel_minimo_do_tipo: int | None


class AvaliadorTitularidade:
    """Cargo compatível com o porte da unidade. Sem Django: a regra é a mesma no clean, no
    view e no teste."""

    def __call__(self, requisito: RequisitoTitularidade) -> bool: ...
```

```python
# apps/user_admin/titularidade.py
def definir_titular(perfil: Perfil) -> None:
    """Destitui o titular anterior — afastado ou não — e marca o novo na mesma transação: o índice
    recusa os dois marcados, ainda que por um instante."""
    ...


def destituir_titular(unidade: Unidade) -> None:
    """Abre a vaga: a unidade fica sem titular, e é a tela que cobra a nomeação."""
    ...
```

## Fora de escopo
- **A página da unidade, a seção de direção e os três modais** — SPEC 016, que vem depois desta.
  Aqui a titularidade só é exercitável pelos fictícios e pelos testes.
- Titularidade como ato administrativo **registrado**, e a proteção da rota: entram com o épico
  `autorizacao`, nos mesmos termos da exceção declarada na SPEC 015.
- Exercício, impedimento e substituição: são da SPEC 015, **pré-requisito desta**.
- Titular interino e mandato com histórico — inclusive **desde quando** a unidade está vaga, que
  exigiria guardar a data da destituição.
- Encerrar a substituição do titular destituído: ela cobre o cargo dele, não a direção (ver
  Contexto).
- Exigir que toda unidade **tenha** titular, ou quem a dirija: a vaga é estado operacional, e a
  unidade sem direção é coberta pelo superior — a tela acusa, mas nada impede o estado.
- Escolher automaticamente quem responde pela unidade vaga (o titular do pai, o mais graduado da
  casa): quem alcança a subárvore é regra do épico `autorizacao`.
- Qualquer efeito de autorização decorrente da titularidade ou do exercício — é o épico
  `autorizacao`.
- Aplicar a migração: o agente gera, quem aplica é o usuário (CLAUDE.md §4).

## Testes (TDD)
Os três primeiros são domínio puro e rodam na suíte padrão; os demais carregam o marker `banco`,
declarado em `markers_obrigatorios`.

- `test_adequacao_exige_chefia_e_nivel_suficiente` — Diretor de Divisão titulariza Divisão; Chefe de
  Seção não titulariza Coordenadoria; Assessor VI, mesmo com nível 6, não titulariza nada. Sem banco.
- `test_tipo_sem_minimo_so_aceita_alta_administracao` — no tipo de mínimo nulo, Subsecretário
  titulariza e Coordenador II não. Sem banco.
- `test_direcao_distingue_titular_substituto_e_as_duas_faltas` — dirige o titular em exercício;
  dirige o substituto quando ele está fora; sem os dois é `SEM_DIRECAO`; sem titular é `SEM_TITULAR`,
  e nenhuma marca de exercício muda isso. Sem banco.
- `test_unidade_nao_admite_dois_titulares` — marcar um segundo titular é recusado pelo banco,
  inclusive com o primeiro fora de exercício. *(marker `banco`)*
- `test_troca_destitui_o_anterior_e_destituir_abre_a_vaga` — depois da troca existe exatamente um
  titular, é o novo, e o anterior é destituído mesmo afastado; destituir sozinho deixa a unidade sem
  titular. *(marker `banco`)*
- `test_titular_invalido_e_recusado_na_validacao` — rebaixar o cargo do titular, ou mover a unidade
  para um tipo que ele não satisfaz, é recusado na validação. *(marker `banco`)*
- `test_seed_e_ficticios_nascem_com_titularidade` — a carga grava o mínimo declarado em cada tipo, os
  servidores fictícios deixam titulares marcados e ao menos uma unidade fica vaga. *(marker `banco`)*

## Patches

_Nenhum patch registrado até o momento._
