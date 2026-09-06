---
spec: user_admin/014
versao: v11
atualizado_em: 2026-08-12
testes_tdd: true
implementado: true
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
  - v8: snippets detalhados — os avaliadores ganham corpo, entra a ponte de model que os `clean()`
        chamam, a leitura de estado da direção sobre a substituição da SPEC 015, o mínimo de cada
        tipo no seed e a titularização dos fictícios; os DTOs passam a morar em `models.py`, como
        nos demais submódulos de domínio
  - v9: a exigência de alta administração vira coluna própria do tipo de unidade, em vez de ficar
        implícita no mínimo nulo — duas colunas pareadas por constraint, na mesma forma que
        `alta_administracao` × `nivel` em `CargoComissao`; o DTO e o avaliador leem a marca
  - v10: patch 001 — a montagem `estado_da_direcao` não entrou na implementação e passa para a
         SPEC 016
  - v11: patch 002 — a 015 deixa de ser pré-requisito desta; dentro de um épico a ordem numérica é
         a ordem de implementação, e nenhuma SPEC depende da seguinte
---

# SPEC user_admin/014 — Titular da unidade: um por unidade, com que cargo e quem dirige hoje

> A interface que mostra tudo isto — a página da unidade, a seção de direção e os três modais — é a
> **SPEC 016**, que vem depois desta. Aqui ficam o dado, a regra e os atos.

- [x] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como responsável pela DIMAP, quero que cada unidade tenha um titular inequívoco, com cargo
compatível com o porte dela, para que "quem dirige a unidade hoje" seja um dado do sistema — mesmo
quando o titular está afastado e quem responde é o substituto dele, e mesmo quando a unidade está
sem titular nenhum, que é o que a tela da SPEC 016 acusa — e para que a administração de
competências decorra da direção em vez de uma lista nominal em código.

## Critérios de aceite
- [x] Uma unidade tem **no máximo um titular**, e é o **banco** que recusa o segundo. O afastamento
      do titular **não abre vaga**: quem cobre é o **substituto** (SPEC 015), nunca um segundo
      titular marcado ao lado dele.
- [x] A unidade **pode ficar sem titular**, e isso é **atributo dela**: a unidade responde "não
      tenho titular" sem que nada no sistema impeça o estado — é o que acontece entre a exoneração
      de um titular e a nomeação do seguinte.
- [x] **Quem dirige a unidade hoje** tem **quatro** respostas: o titular em exercício; o substituto
      dele; **sem direção** (há titular, está fora e ninguém cobre); **sem titular** (a vaga).
      Leitura derivada das marcas, decidida em `services/` e **testável sem banco**.
- [x] Cada **tipo de unidade** declara o nível mínimo de cargo em comissão exigido do titular **ou**
      declara que **só a alta administração serve** — são duas colunas, e uma exclui a outra.
- [x] Só titulariza quem tem cargo em comissão **de chefia** e satisfaz o mínimo do tipo da própria
      unidade — alta administração satisfaz qualquer tipo. Perfil sem cargo em comissão nunca
      titulariza; do **substituto** nada disso se exige, porque ele ocupa o papel sem receber o
      vínculo. A regra é decidida em `services/` e é **testável sem banco**.
- [x] **Trocar o titular é uma operação só**: o titular anterior é destituído na mesma transação —
      **inclusive afastado** —, nunca restando dois marcados nem uma janela sem nenhum.
- [x] **Destituir o titular é ato próprio**, e deixa a unidade sem titular — não se exige um
      substituído no ato para poder destituir.
- [x] Rebaixar o titular, ou mudar a unidade para um tipo que ele não satisfaz, é **recusado na
      validação** — não fica titular inválido gravado.
- [x] O seed de unidades declara o mínimo de cada tipo, e os servidores fictícios nascem com
      titulares marcados — e ao menos uma unidade fictícia nasce **sem titular**, para a tela da
      SPEC 016 ser exercitável no estado que ela existe para acusar.
- [x] **Definir, trocar e destituir titular** são funções em transação, chamadas pela tela (SPEC
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

**O mínimo mora no tipo de unidade, e a exigência de alta administração é coluna própria.** A escala
do cargo em comissão vai até 6, o organograma vai até o nível 9: para Subsecretaria, Secretaria
Executiva e Gabinete **nenhum nível serve** — só alta administração. Dizer isso com mínimo nulo faria
a *ausência* do dado significar a regra mais restritiva de todas, e um tipo novo sem mínimo
preenchido a herdaria calado. Então são duas colunas pareadas por `CheckConstraint`,
`exige_alta_administracao` e o mínimo — exatamente a forma que `CargoComissao` já tem para
`alta_administracao` × `nivel`, e a leitura fica simétrica dos dois lados.

O mínimo **não é derivável** do nível do tipo: Departamento e Coordenação são níveis diferentes com
o mesmo mínimo (5), e Coordenadoria e Assessoria são o mesmo nível com mínimos diferentes (6 e 5,
porque Chefe de Assessoria Técnica I é CDA-V). É dado do organograma, por isso é campo.

**Nível sem chefia não basta.** Assessor VI é CDA-VI e não é chefia — com regra só de nível, ele
titularizaria uma Coordenadoria. A adequação é `e_chefia` **e** (`alta_administracao` **ou**
(**não** `exige_alta_administracao` **e** `nivel >= mínimo do tipo`)).

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

# services/domain/titularidade/models.py
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


class RequisitoTitularidade(BaseModel):
    model_config = ConfigDict(frozen=True)

    e_chefia: bool
    alta_administracao: bool
    nivel_cargo: int | None
    # A exigência é declarada, não inferida da falta do mínimo — ver Contexto.
    tipo_exige_alta_administracao: bool
    nivel_minimo_do_tipo: int | None
```

```python
# services/domain/titularidade/direcao.py
class AvaliadorDirecao:
    """Quem dirige a unidade hoje — e, quando ninguém dirige, qual das duas faltas é."""

    def __call__(self, estado: EstadoDaDirecao) -> Direcao:
        # A vaga responde antes de qualquer marca de exercício: não há de quem consultá-la.
        if not estado.tem_titular:
            return Direcao.SEM_TITULAR
        if estado.titular_em_exercicio:
            return Direcao.TITULAR
        if estado.substituto_do_titular_em_exercicio:
            return Direcao.SUBSTITUTO
        return Direcao.SEM_DIRECAO


def avaliar_direcao(estado: EstadoDaDirecao) -> Direcao:
    return AvaliadorDirecao()(estado)
```

```python
# services/domain/titularidade/requisito.py
class AvaliadorTitularidade:
    """Cargo compatível com o porte da unidade. Sem Django: a regra é a mesma no clean, na view
    e no teste."""

    def __call__(self, requisito: RequisitoTitularidade) -> bool:
        # Nível sem chefia não basta: Assessor VI é CDA-VI e não dirige nada.
        if not requisito.e_chefia:
            return False
        if requisito.alta_administracao:
            return True
        return self._satisfaz_o_minimo(requisito)

    def _satisfaz_o_minimo(self, requisito: RequisitoTitularidade) -> bool:
        # O tipo exige estar acima da escala, e quem chegou aqui está dentro dela.
        if requisito.tipo_exige_alta_administracao:
            return False
        # Fora dessa exigência os dois níveis existem; o None só sobra por defesa de tipo.
        if requisito.nivel_minimo_do_tipo is None or requisito.nivel_cargo is None:
            return False
        return requisito.nivel_cargo >= requisito.nivel_minimo_do_tipo


def avaliar_titularidade(requisito: RequisitoTitularidade) -> bool:
    return AvaliadorTitularidade()(requisito)
```

```python
# apps/user_admin/models/unidade.py
ERRO_ALTA_ADM_COM_MINIMO = "Tipo que exige alta administração não tem nível mínimo de titular."
ERRO_MINIMO_TITULAR_OBRIGATORIO = "Tipo fora da alta administração exige nível mínimo de titular."


class TipoUnidade(models.Model):
    # A exigência é declarada; sem ela, o tipo novo herdaria calado a regra mais restritiva.
    exige_alta_administracao = models.BooleanField(default=False)
    nivel_minimo_titular = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(NIVEL_MINIMO),
            MaxValueValidator(NIVEL_MAXIMO),
        ],
    )

    class Meta:
        constraints = [
            # Uma coluna exclui a outra — o mesmo pareamento de alta_administracao × nivel
            # em CargoComissao, e a mesma constraint espelhada no clean().
            models.CheckConstraint(
                condition=(
                    Q(
                        exige_alta_administracao=True,
                        nivel_minimo_titular__isnull=True,
                    )
                    | Q(
                        exige_alta_administracao=False,
                        nivel_minimo_titular__gte=NIVEL_MINIMO,
                        nivel_minimo_titular__lte=NIVEL_MAXIMO,
                    )
                ),
                name="tipo_unidade_minimo_conforme_alta_administracao",
            ),
        ]

    def clean(self) -> None:
        if self.exige_alta_administracao and self.nivel_minimo_titular is not None:
            raise ValidationError({"nivel_minimo_titular": ERRO_ALTA_ADM_COM_MINIMO})
        if not self.exige_alta_administracao and self.nivel_minimo_titular is None:
            raise ValidationError({"nivel_minimo_titular": ERRO_MINIMO_TITULAR_OBRIGATORIO})
```

```python
# apps/user_admin/models/titularidade.py — a ponte que os dois clean() chamam; importa só o
# catálogo de cargos, e por isso não fecha ciclo com user.py nem com unidade.py.
def cargo_titulariza(
    cargo: CargoComissao | None,
    exige_alta_administracao: bool,
    nivel_minimo: int | None,
) -> bool:
    # Sem cargo em comissão não há chefia, e o avaliador recusa na primeira guarda.
    requisito = RequisitoTitularidade(
        e_chefia=bool(cargo and cargo.e_chefia),
        alta_administracao=bool(cargo and cargo.alta_administracao),
        nivel_cargo=cargo.nivel if cargo else None,
        tipo_exige_alta_administracao=exige_alta_administracao,
        nivel_minimo_do_tipo=nivel_minimo,
    )
    return avaliar_titularidade(requisito)
```

```python
# apps/user_admin/models/user.py
ERRO_TITULAR_SEM_CARGO_COMPATIVEL = (
    "O titular precisa de cargo em comissão de chefia compatível com o porte da unidade."
)


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

    def clean(self) -> None:
        # Cruza perfil → cargo e perfil → unidade → tipo: nenhuma CheckConstraint alcança.
        if not self.e_titular or not hasattr(self, "unidade"):
            return
        tipo = self.unidade.tipo
        if not cargo_titulariza(
            self.cargo_comissao,
            exige_alta_administracao=tipo.exige_alta_administracao,
            nivel_minimo=tipo.nivel_minimo_titular,
        ):
            raise ValidationError({"e_titular": ERRO_TITULAR_SEM_CARGO_COMPATIVEL})
```

```python
# apps/user_admin/models/unidade.py
ERRO_TIPO_INCOMPATIVEL_COM_TITULAR = "O titular atual não satisfaz o mínimo de cargo deste tipo."


class Unidade(models.Model):
    # A vaga é a ausência do vínculo, e quem responde por ela é a unidade. Derivado, não coluna:
    # gravar duplicaria as linhas de Perfil. Precedente: Perfil.esta_impedido.
    @property
    def titular(self) -> "Perfil | None":
        return self.perfis.filter(e_titular=True).first()

    def clean(self) -> None:
        self._checar_titular()
        ...  # as regras de hierarquia da SPEC 003 seguem como estão, depois desta

    def _checar_titular(self) -> None:
        # O outro lado da mesma adequação: mudar o tipo quebra o que o cargo do titular satisfazia.
        if self.pk is None or not hasattr(self, "tipo"):
            return
        titular = self.titular
        if titular is None:
            return
        if not cargo_titulariza(
            titular.cargo_comissao,
            exige_alta_administracao=self.tipo.exige_alta_administracao,
            nivel_minimo=self.tipo.nivel_minimo_titular,
        ):
            raise ValidationError({"tipo": ERRO_TIPO_INCOMPATIVEL_COM_TITULAR})
```

```python
# apps/user_admin/titularidade.py — os atos e a montagem dos DTOs na borda; mexe em persistência
# e orquestração, e por isso vive no app (mesmo lugar de ficticios.py e das seeds).
def definir_titular(perfil: Perfil) -> None:
    """Destitui o titular anterior — afastado ou não — e marca o novo na mesma transação: o índice
    recusa os dois marcados, ainda que por um instante."""
    with transaction.atomic():
        _destituir(perfil.unidade, exceto=perfil)
        perfil.e_titular = True
        # Depois da destituição: validate_constraints enxerga a transação e acusaria o anterior.
        perfil.full_clean()
        perfil.save(update_fields=["e_titular"])


def destituir_titular(unidade: Unidade) -> None:
    """Abre a vaga: a unidade fica sem titular, e é a tela que cobra a nomeação."""
    with transaction.atomic():
        _destituir(unidade)


def _destituir(unidade: Unidade, exceto: Perfil | None = None) -> None:
    # update() em massa fura a validação, mas desmarcar nunca produz titular inválido.
    titulares = Perfil.objects.filter(unidade=unidade, e_titular=True)
    if exceto is not None and exceto.pk is not None:
        titulares = titulares.exclude(pk=exceto.pk)
    titulares.update(e_titular=False)


def estado_da_direcao(unidade: Unidade) -> EstadoDaDirecao:
    """Junta as marcas da SPEC 015 no DTO que o domínio lê; é o que a SPEC 016 consome."""
    titular = unidade.titular
    if titular is None:
        return EstadoDaDirecao(
            tem_titular=False,
            titular_em_exercicio=False,
            substituto_do_titular_em_exercicio=False,
        )
    substituicao = titular.substituicoes_recebidas.filter(data_fim__isnull=True).first()
    return EstadoDaDirecao(
        tem_titular=True,
        titular_em_exercicio=titular.em_exercicio,
        # O substituto fora de exercício não cobre ninguém: a unidade fica sem direção.
        substituto_do_titular_em_exercicio=bool(
            substituicao and substituicao.substituto.em_exercicio
        ),
    )
```

```jsonc
// data/seed/unidades.json — cada tipo declara um dos dois; o resto da entrada não muda.
{ "nome": "Equipe",        "nivel_minimo_titular": 2 }
{ "nome": "Seção",         "nivel_minimo_titular": 3 }
{ "nome": "Divisão",       "nivel_minimo_titular": 4 }
{ "nome": "Departamento",  "nivel_minimo_titular": 5 }
{ "nome": "Coordenação",   "nivel_minimo_titular": 5 }
{ "nome": "Coordenadoria", "nivel_minimo_titular": 6 }
// Chefe de Assessoria Técnica I é CDA-V: mesmo nível da Coordenadoria, mínimo menor.
{ "nome": "Assessoria",    "nivel_minimo_titular": 5 }
// Acima da escala do cargo em comissão: nenhum nível serve.
{ "nome": "Subsecretaria",               "exige_alta_administracao": true }
{ "nome": "Secretaria Executiva",        "exige_alta_administracao": true }
{ "nome": "Gabinete da/do Secretária/o", "exige_alta_administracao": true }
```

```python
# apps/user_admin/seeds/unidades.py
class TipoUnidadeSeed(BaseModel):
    # Omitir os dois não é atalho para nada: a constraint recusa o par vazio na carga.
    exige_alta_administracao: bool = False
    nivel_minimo_titular: int | None = None
```

```python
# apps/user_admin/ficticios.py
# Uma unidade elegível fica de fora: a vaga é o estado que a tela da SPEC 016 existe para acusar.
UNIDADES_SEM_TITULAR = 1


class CriadorServidoresFicticios:
    def _titularizar(
        self,
        perfis: list[Perfil],
        cargos_comissao: list[CargoComissao],
    ) -> int:
        titulaveis = self._um_por_unidade(perfis)[:-UNIDADES_SEM_TITULAR]
        for perfil in titulaveis:
            # O cargo vem do porte da unidade, não do rodízio: senão o clean recusaria a marca.
            perfil.cargo_comissao = self._cargo_que_titulariza(perfil.unidade, cargos_comissao)
            perfil.save(update_fields=["cargo_comissao"])
            definir_titular(perfil)
        return len(titulaveis)
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
- `test_tipo_que_exige_alta_administracao_recusa_qualquer_nivel` — no tipo com a marca ligada,
  Subsecretário titulariza e Coordenador II não, mesmo no topo da escala. Sem banco.
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
- `test_seed_e_ficticios_nascem_com_titularidade` — a carga grava, em cada tipo, o mínimo ou a
  exigência de alta administração que o arquivo declara; os
  servidores fictícios deixam titulares marcados e ao menos uma unidade fica vaga. *(marker `banco`)*

## Patches

### Patch 001 (v10) — a montagem do `EstadoDaDirecao` não entrou, e passa para a SPEC 016

Esta SPEC foi implementada **antes** da 015, que ela declara como pré-requisito. Consequência: o
snippet `estado_da_direcao(unidade)` — que monta o DTO lendo `Perfil.em_exercicio` e a
`Substituicao` — **não foi implementado**, porque nenhum dos dois existe no model. Tudo o mais
entrou, e o critério de aceite das quatro respostas está satisfeito pelo `avaliar_direcao`, que é
puro, testado e não depende daqueles campos.

A montagem **não volta para cá quando a 015 entrar**: ela fica na **SPEC 016**, a primeira que a
consome, onde titular e substituto já estão carregados para a tela e a composição não custa uma
consulta a mais. A 015 entrega a leitura da substituição vigente que a 016 compõe com
`Unidade.titular`.

O que existe hoje em `apps/user_admin/titularidade.py` são os dois atos — `definir_titular` e
`destituir_titular`.

### Patch 002 (v11) — a 015 deixa de ser pré-requisito: nenhuma SPEC depende da seguinte

Dentro de um épico, a ordem numérica **é** a ordem de implementação, e a SPEC N não depende da N+1
(skill `specs`). Esta SPEC violava a regra ao declarar a 015 como pré-requisito — e a implementação
mostrou que a dependência não existia: o único ponto que precisava de `em_exercicio` e da
`Substituicao` era a montagem do `EstadoDaDirecao`, que saiu daqui no patch 001. O dado, a regra, os
avaliadores e os atos ficaram de pé sem nada da 015.

Ficam sem efeito, no corpo, duas declarações:

- a marca "**pré-requisito desta**" nas duas menções à SPEC 015 (Peças de referência e Fora de
  escopo) — a 015 é a SPEC **seguinte**, e o que ela entrega é consumido pela **016**, não por esta;
- a exceção de rota aberta ao §3.5, que o Contexto atribui à SPEC 015 — ela foi declarada primeiro
  na **SPEC 013**, nos mesmos termos, e é de lá que esta SPEC a herda.

O que a 015 e a 016 devem a esta SPEC segue como está: a leitura de quem dirige hoje é a mesma peça
nas duas.
