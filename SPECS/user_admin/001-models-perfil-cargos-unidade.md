---
spec: user_admin/001
versao: v6
atualizado_em: 2026-08-05
testes_tdd: true
implementado: true
changelog:
  - v1: versão inicial
  - v2: padrão do cargo em comissão deixa de ser texto livre e passa a ser sigla + nível
    inteiro (1 a 6), com o algarismo romano montado na leitura
  - v3: cargos da alta administração — booleana que dispensa o nível, só admitida em cargo de
    chefia
  - v4: o padrão não é único (CDA-II é diretor de divisão e assessor II); a unicidade passa
    para o nome do cargo
  - v5: TipoCargoComissao eliminado — e_chefia vai para o próprio CargoComissao, o que leva
    toda a validação para CheckConstraint e dispensa o clean() que cruzava tabela
  - v6: models organizados como pacote, um módulo por domínio (usuário, unidade, cargos),
    com o __init__ apenas reexportando
---

# SPEC user_admin/001 — Perfil, cargos e unidade: os models de identidade

- [x] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como administrador da plataforma, quero cadastrar servidores da DIMAP com seu RF, seu cargo base,
sua unidade e — quando houver — seu cargo em comissão, para que a competência administrativa de
cada um fique registrada e possa, adiante, autorizar as ações da gaveta (§3.5 do CLAUDE.md).

## Critérios de aceite

- [ ] O sistema autentica pelo **RF**: `AUTH_USER_MODEL` aponta para o model de perfil deste app e
      o identificador de login é o RF, não um `username`.
- [ ] Todo perfil tem **exatamente um** cargo base e **exatamente uma** unidade — salvar um perfil
      sem qualquer um dos dois é recusado.
- [ ] O **cargo em comissão é opcional**: um perfil sem cargo em comissão é válido.
- [ ] Todo cargo em comissão declara se é de **chefia** ou de **assessoramento**, e expõe essa
      natureza em texto legível: `"Chefia"` ou `"Assessoramento"`.
- [ ] O cargo em comissão guarda **sigla** e **nível** separados, e o **padrão legível** é a sigla
      seguida do nível em algarismo romano — `sigla="CDA"` e `nivel=4` lêem-se `"CDA-IV"`.
- [ ] O nível vai de **1 a 6**; salvar um cargo com nível fora dessa faixa é recusado.
- [ ] Um cargo marcado como **alta administração** (secretário, secretário adjunto, secretário
      executivo, chefe de gabinete) não tem nível, e seu padrão legível sai sem o algarismo.
- [ ] Um cargo **não** marcado como alta administração **exige** nível; um marcado como alta
      administração **recusa** nível. Não há como salvar as duas combinações erradas.
- [ ] Alta administração só é admitida em cargo de **chefia** — marcar a booleana num cargo de
      assessoramento é recusado.
- [ ] **Dois cargos podem compartilhar o mesmo padrão** — `CDA-II` é tanto diretor de divisão
      (chefia) quanto assessor II (assessoramento), e secretário executivo e chefe de gabinete
      dividem o padrão da alta administração. O que distingue um cargo do outro é o **nome**, e é
      ele que não se repete.
- [ ] Unidade e cargo base são **catálogos**, e nenhum registro deles pode ser apagado enquanto
      houver perfil apontando para ele — o mesmo vale para um cargo em comissão em uso.

## Contexto e decisões de arquitetura

Esta SPEC mexe **só na camada de persistência**. Não há domínio, view, template nem rota — é o
substrato de identidade sobre o qual as SPECs seguintes (seed, autorização, gaveta) vão se apoiar.

**Os models são um pacote, um módulo por domínio** — usuário, unidade e cargos —, e não um
`models.py` único. É o §7.1 aplicado à persistência: unidade, cargo e pessoa são coisas distintas,
e um arquivo que as junta cresce cruzando domínios. O `__init__.py` **só reexporta** (§7.2), para
que o resto do projeto importe do pacote sem conhecer a divisão interna.

**O model se chama `Perfil`** e herda de `AbstractBaseUser` + `PermissionsMixin`, com
`USERNAME_FIELD = "rf"`. O CLAUDE.md §3.5 já nomeia essa peça: o Perfil é o model que herda do
`django.contrib.auth` e concentra cargo e unidade. O RF é o identificador funcional do servidor na
PMSP — é por ele que a pessoa é conhecida, então manter um `username` paralelo criaria duas
identidades para a mesma pessoa.

**A natureza chefia × assessoramento é uma booleana no próprio `CargoComissao`, sem tabela de
tipos.** Uma tabela de tipos garantiria que "Diretor" nunca fosse cadastrado como assessoramento,
mas, por cruzar tabela, jogaria a regra "alta administração só em chefia" para o `clean()` — que só
vale para quem chama `full_clean()`. Com a booleana no cargo, essa regra vira `CheckConstraint` e
passa a ser garantida pelo banco em qualquer caminho de escrita. O que se abre mão é de impedir um
cadastro incoerente no seed; o seed é código revisado em PR (próxima SPEC), não digitação de
usuário. O rótulo legível (`"Chefia"` / `"Assessoramento"`) é uma `@property` sobre a booleana —
formatação de um campo persistido, não regra de negócio, e por isso cabe no model.

**O padrão é derivado, não armazenado.** O que persiste é a sigla (`"CDA"`) e o nível como inteiro
(`4`); o padrão legível (`"CDA-IV"`) é uma `@property` que monta os dois. Guardar o texto pronto
tornaria o nível um dado a ser extraído por parsing toda vez que alguém precisasse compará-lo ou
ordená-lo — e abriria a chance de o texto e o número discordarem. Como a faixa é fechada em 1 a 6,
a conversão para romano é uma tabela de seis posições, não um algoritmo.

**A alta administração é uma booleana no cargo, não um nível especial.** Secretário, secretário
adjunto, secretário executivo e chefe de gabinete são cargos de chefia sem nível — reservar um
valor de nível para representá-los (um `0`, um `99`) faria a faixa 1–6 mentir e contaminaria
qualquer ordenação. Então `nivel` é anulável e a booleana é o que diz **quando** ele deve estar
vazio: marcada, o nível é proibido; desmarcada, é obrigatório.

**Toda a validação é `CheckConstraint`** (§3.2 permite validação de persistência), porque nenhuma
das duas regras cruza tabela: `alta_administracao` × `nivel` (uma marcada exige o outro vazio, e
vice-versa, com a faixa 1–6 embutida) e `alta_administracao` ⟹ `e_chefia`. O banco garante ambas em
qualquer caminho de escrita. O `clean()` apenas espelha as duas, para que o erro apareça no campo
em vez de virar `IntegrityError` — não é ele que garante nada.

**O padrão não identifica o cargo — o nome identifica.** `CDA-II` é o padrão do diretor de divisão
e também o do assessor II; secretário executivo e chefe de gabinete dividem o padrão da alta
administração. O padrão é o nível remuneratório, e é essa colisão que obriga o cargo a carregar sua
própria natureza: sem ela, dois cargos idênticos no padrão seriam indistinguíveis quanto a chefia.
Logo a unicidade recai sobre o `nome`, e **nenhuma constraint pode barrar sigla + nível repetidos**.

**Todas as FKs usam `on_delete=PROTECT`.** Apagar uma unidade ou um cargo base em uso apagaria em
cascata o vínculo administrativo de servidores — o oposto do que se quer num sistema onde esse
vínculo define competência.

**Consequência operacional:** trocar o `AUTH_USER_MODEL` depois que `contrib.auth` já foi migrado
exige recriar o banco de desenvolvimento. Não há nenhuma tabela de domínio hoje, então o custo é
`docker compose down -v` + `migrate`.

**Testes precisam do Django carregado.** A suíte hoje não tem `pytest-django`, e sem ele não é
possível sequer instanciar um model. Esta SPEC adiciona a dependência e o `DJANGO_SETTINGS_MODULE`
na configuração do pytest; os testes abaixo não pedem a fixture `db` e continuam rodando sem banco
em pé. Atenção a uma armadilha: desde o Django 4.1 o `full_clean()` também roda
`validate_constraints()`, que consulta o banco — nos testes sem banco, chamar
`full_clean(validate_constraints=False)`. É por isso que o `clean()` espelha as constraints.

## Peças de referência a compor

- `@config/settings.py` → `INSTALLED_APPS`: registrar o novo app; declarar `AUTH_USER_MODEL`.
- `@apps/core` → estrutura de app do projeto (`apps.py`, `migrations/`) como molde do novo app.
- `@tests/conftest.py` → conftest existente, onde entra a configuração do Django para os testes.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md
#
# Os models abaixo se distribuem em três módulos do pacote: Unidade em `unidade`,
# CargoBase/CargoComissao (e as constantes) em `cargos`, Perfil/PerfilManager em `user`.

ROTULO_CHEFIA = "Chefia"
ROTULO_ASSESSORAMENTO = "Assessoramento"
NIVEL_MINIMO = 1
NIVEL_MAXIMO = 6
ERRO_ALTA_ADM_SEM_CHEFIA = "Alta administração só se aplica a cargo de chefia."
ERRO_ALTA_ADM_COM_NIVEL = "Cargo da alta administração não tem nível."
ERRO_NIVEL_OBRIGATORIO = "Cargo em comissão fora da alta administração exige nível."
# Faixa fechada em 1..6: tabela em vez de algoritmo de conversão para romano.
ALGARISMOS_ROMANOS = {
    1: "I",
    2: "II",
    3: "III",
    4: "IV",
    5: "V",
    6: "VI",
}
SEPARADOR_PADRAO = "-"


class Unidade(models.Model):
    nome = models.CharField(
        max_length=120,
        unique=True,
    )
    sigla = models.CharField(
        max_length=20,
        unique=True,
    )


class CargoBase(models.Model):
    nome = models.CharField(
        max_length=120,
        unique=True,
    )
    sigla = models.CharField(
        max_length=20,
        unique=True,
    )


class CargoComissao(models.Model):
    sigla = models.CharField(max_length=20)
    nivel = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(NIVEL_MINIMO),
            MaxValueValidator(NIVEL_MAXIMO),
        ],
    )
    e_chefia = models.BooleanField()
    alta_administracao = models.BooleanField(default=False)
    # O padrão colide entre cargos (CDA-II serve diretor de divisão e assessor II); o nome é
    # o que identifica.
    nome = models.CharField(
        max_length=200,
        unique=True,
    )

    @property
    def natureza(self) -> str:
        return ROTULO_CHEFIA if self.e_chefia else ROTULO_ASSESSORAMENTO

    @property
    def padrao(self) -> str:
        if self.nivel is None:
            return self.sigla
        return f"{self.sigla}{SEPARADOR_PADRAO}{ALGARISMOS_ROMANOS[self.nivel]}"

    def clean(self) -> None:
        # Espelha as constraints: sem isso o erro só apareceria como IntegrityError no save.
        if self.alta_administracao and not self.e_chefia:
            raise ValidationError({"alta_administracao": ERRO_ALTA_ADM_SEM_CHEFIA})
        if self.alta_administracao and self.nivel is not None:
            raise ValidationError({"nivel": ERRO_ALTA_ADM_COM_NIVEL})
        if not self.alta_administracao and self.nivel is None:
            raise ValidationError({"nivel": ERRO_NIVEL_OBRIGATORIO})

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        alta_administracao=True,
                        nivel__isnull=True,
                    )
                    | Q(
                        alta_administracao=False,
                        nivel__gte=NIVEL_MINIMO,
                        nivel__lte=NIVEL_MAXIMO,
                    )
                ),
                name="cargo_comissao_nivel_conforme_alta_administracao",
            ),
            models.CheckConstraint(
                condition=Q(alta_administracao=False) | Q(e_chefia=True),
                name="cargo_comissao_alta_administracao_e_chefia",
            ),
        ]


class Perfil(AbstractBaseUser, PermissionsMixin):
    rf = models.CharField(
        max_length=20,
        unique=True,
    )
    nome = models.CharField(max_length=200)
    cargo_base = models.ForeignKey(
        CargoBase,
        on_delete=models.PROTECT,
        related_name="perfis",
    )
    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.PROTECT,
        related_name="perfis",
    )
    cargo_comissao = models.ForeignKey(
        CargoComissao,
        on_delete=models.PROTECT,
        related_name="perfis",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = PerfilManager()

    USERNAME_FIELD = "rf"
    REQUIRED_FIELDS = ["nome"]
```

O `PerfilManager` (`create_user` / `create_superuser`) é **encanamento exigido pelo
`contrib.auth`** — sem ele o `createsuperuser` não roda. É a única coisa que vive no manager; não
abre precedente para regra de negócio ali (§3.2).

## Fora de escopo

- **Seed / pré-população do banco** — é a próxima SPEC deste épico.
- Registro no Django admin, telas de cadastro, rotas e views.
- Leitura no sentido inverso (receber `"CDA-IV"` em texto e resolver o cargo): é parsing, e mora em
  `services/domain/` quando alguma entrada de usuário precisar dele.
- Contratos de ação, router de gaveta e qualquer checagem de autorização (§3.5) — dependem destes
  models, mas não entram aqui.
- E-mail, recuperação de senha e políticas de senha.

## Testes (TDD)

- `test_perfil_autentica_por_rf` — `AUTH_USER_MODEL` aponta para o `Perfil` deste app e o
  `USERNAME_FIELD` é `rf`, não `username`.
- `test_perfil_sem_cargo_base_ou_unidade_nao_valida` — `full_clean()` de um perfil sem cargo base e
  sem unidade acusa erro em ambos os campos.
- `test_perfil_sem_cargo_comissao_valida` — o vínculo com cargo em comissão é opcional e a
  ausência dele não gera erro de validação.
- `test_padrao_do_cargo_comissao_usa_algarismo_romano` — `sigla="CDA"` com `nivel=4` lê-se
  `"CDA-IV"`; na alta administração, o padrão sai só com a sigla.
- `test_nivel_do_cargo_comissao_fora_da_faixa_nao_valida` — nível `7` (e `0`) é recusado; `1` e `6`
  passam.
- `test_nivel_e_alta_administracao_sao_mutuamente_exclusivos` — cargo comum sem nível é recusado, e
  cargo de alta administração com nível também.
- `test_alta_administracao_exige_cargo_de_chefia` — a booleana marcada num cargo de assessoramento
  é recusada.
- `test_natureza_do_cargo_e_o_rotulo_legivel` — `e_chefia=True` devolve `"Chefia"`; `False` devolve
  `"Assessoramento"`.

## Patches

_Nenhum patch registrado até o momento._
