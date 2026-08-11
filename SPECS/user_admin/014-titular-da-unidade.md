---
spec: user_admin/014
versao: v1
atualizado_em: 2026-08-11
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC user_admin/014 — Titular da unidade: quem dirige, e com que cargo

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como responsável pela DIMAP, quero que cada unidade tenha um titular inequívoco, com cargo
compatível com o porte dela, para que "quem dirige a unidade" seja um dado do sistema — e não uma
inferência — e para que a administração de competências decorra da direção em vez de uma lista
nominal em código.

## Critérios de aceite
- [ ] Uma unidade tem **no máximo um** titular, e é o **banco** que recusa o segundo.
- [ ] Cada **tipo de unidade** declara o nível mínimo de cargo em comissão exigido do titular;
      **ausência de mínimo significa que só a alta administração serve**.
- [ ] Só titulariza quem tem cargo em comissão **de chefia** e satisfaz o mínimo do tipo da própria
      unidade — alta administração satisfaz qualquer tipo. Perfil sem cargo em comissão nunca
      titulariza.
- [ ] A regra de adequação é decidida em `services/` e é **testável sem banco**.
- [ ] **Trocar o titular é uma operação só**: o anterior é destituído na mesma transação, nunca
      restando dois marcados nem uma janela sem nenhum.
- [ ] Rebaixar o titular, ou mudar a unidade para um tipo que ele não satisfaz, é **recusado na
      validação** — não fica titular inválido gravado.
- [ ] O seed de unidades declara o mínimo de cada tipo, e os servidores fictícios nascem com
      titulares marcados.

## Contexto e decisões de arquitetura

Esta SPEC mexe em persistência (`user_admin`) e em domínio (`services/domain/titularidade/`). Não
decide autorização nenhuma: quem lê a titularidade e a transforma em competência é o épico
`autorizacao` (SPEC 003).

**Titularidade não é o mesmo que cargo de chefia.** `CargoComissao.e_chefia` é atributo do catálogo
de cargos: diz que o cargo é de natureza chefia, não que a pessoa dirige aquela unidade. Hoje uma
unidade pode ter zero chefias lotadas (vaga) ou várias (um diretor de divisão e um chefe de seção na
mesma lotação, o que o seed de cargos torna comum) — com isso, "quem dirige a DIMAP-1" não é
computável. A titularidade é o vínculo que falta.

**Booleana no `Perfil`, com índice único parcial por unidade.** O titular é necessariamente lotado
na unidade que dirige — e com a marca no perfil isso sai de graça, porque a unidade é a dele. Uma FK
`chefe` na `Unidade` admitiria titular lotado em outro ramo e fecharia um ciclo `Unidade`↔`Perfil`
que atrapalha seed e migração inicial — descartada. Um model de mandato com início e fim daria
histórico, mas substituição está fora do épico e a escala não paga o preço.

**O mínimo mora no tipo de unidade, e é anulável.** A escala do cargo em comissão vai até 6, o
organograma vai até o nível 9: para Subsecretaria, Secretaria Executiva e Gabinete **nenhum nível
serve** — só alta administração. Anulável resolve isso sem inventar sentinela, e a leitura fica a
mesma dos dois lados: `nivel` nulo em `CargoComissao` é "está acima da escala"; mínimo nulo em
`TipoUnidade` é "exige estar acima dela".

O mínimo **não é derivável** do nível do tipo: Departamento e Coordenação são níveis diferentes com
o mesmo mínimo (5), e Coordenadoria e Assessoria são o mesmo nível com mínimos diferentes (6 e 5,
porque Chefe de Assessoria Técnica I é CDA-5). É dado do organograma, por isso é campo.

**Nível sem chefia não basta.** Assessor VI é CDA-6 e não é chefia — com regra só de nível, ele
titularizaria uma Coordenadoria. A adequação é `e_chefia` **e** (`alta_administracao` **ou**
`nivel >= mínimo do tipo`).

**A regra cruza três tabelas, então vive no `clean()` — e a decisão, no domínio.** Perfil → cargo e
perfil → unidade → tipo: nenhuma `CheckConstraint` alcança, o mesmo caso que `Unidade.clean()` já
resolve e documenta. O predicado em si fica em `services/domain/titularidade/` sobre DTO, para ser
testável sem banco (§3.3); os `clean()` do `Perfil` e da `Unidade` o chamam — os dois, porque a
adequação quebra tanto quando o cargo muda quanto quando o tipo da unidade muda.

Consequência aceita: a **unicidade** do titular é garantia de banco; a **adequação** é garantia de
validação, e um `update()` em massa a fura. É o mesmo contrato que a hierarquia de unidades já tem.

**Trocar titular é uma operação.** Com o índice parcial, marcar o novo antes de destituir o anterior
levanta `IntegrityError`. Destituir e marcar viram um passo só, em `transaction.atomic()`.

**Editar o mínimo do tipo não revalida quem já está lá.** Aceito: tipo de unidade é catálogo de
seed, praticamente imutável, e uma revalidação retroativa custaria mais do que o risco que evita.

**Titular não herda para baixo.** Dirigir a coordenadoria não é dirigir as divisões dela. O alcance
de um titular sobre a subárvore é regra do épico `autorizacao`, e alcançar não é titularizar.

**Marcar titular ainda não é ato administrativo, e o caminho é um comando.** As telas do `user_admin`
são só leitura — gravar perfil está declarado lá como ato administrativo a ser entregue com
autorização e registro. Um management command dá o caminho operacional sem antecipar essa tela, e é
o que permite ao primeiro boot ter titulares. Quando gravar perfil virar ação, a titularidade entra
junto e o comando fica como ferramenta de operação.

## Peças de referência a compor
- `@apps/user_admin/models/user.py` → `Perfil`: `unidade` e `cargo_comissao` (anulável) já são a
  lotação; a marca de titular entra aqui.
- `@apps/user_admin/models/cargos.py` → `CargoComissao` (`e_chefia`, `nivel`, `alta_administracao`)
  e o precedente de `CheckConstraint` espelhada no `clean()`.
- `@apps/user_admin/models/unidade.py` → `TipoUnidade` e `Unidade.clean()`: precedente exato da
  regra que cruza tabela e por isso não vira constraint.
- `@apps/user_admin/models/impedimentos.py` → `Perfil.esta_impedido`: existe e continua ortogonal —
  titular impedido segue titular (ver Fora de escopo).
- `@apps/user_admin/seeds/unidades.py` + `@data/seed/unidades.json`: os tipos ganham o mínimo, sem
  mudar a forma da carga; skill `seeds`.
- `@apps/user_admin/ficticios.py`: o andaime que torna a área administrativa exercitável — passa a
  marcar titulares.
- Skill `management-commands`: o comando é fino, a lógica vive no app.

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
            # Índice parcial: garante no máximo um titular por unidade sem barrar os demais lotados.
            models.UniqueConstraint(
                fields=["unidade"],
                condition=Q(e_titular=True),
                name="unidade_tem_um_titular",
            ),
        ]
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
    comando e no teste."""

    def __call__(self, requisito: RequisitoTitularidade) -> bool: ...
```

```python
# apps/user_admin/titularidade.py
def definir_titular(perfil: Perfil) -> None:
    """Destitui o anterior e marca o novo na mesma transação: o índice parcial recusa os dois
    marcados, ainda que por um instante."""
    ...
```

## Fora de escopo
- Tela para marcar titular, e titularidade como ato administrativo registrado — dependem de gravar
  perfil, que o `user_admin` ainda não faz.
- Substituição durante impedimento: titular impedido continua titular. Quem cobre o vazio é o
  titular do nível acima, pela regra de alcance do épico `autorizacao`.
- Titular interino, mais de um titular e mandato com histórico.
- Exigir que toda unidade **tenha** titular: o banco garante "no máximo um"; "pelo menos um" é
  estado operacional, e a unidade sem titular é coberta pelo superior.
- Qualquer efeito de autorização decorrente da titularidade — é o épico `autorizacao`.
- Aplicar a migração: o agente gera, quem aplica é o usuário (CLAUDE.md §4).

## Testes (TDD)
Os dois primeiros são domínio puro e rodam na suíte padrão; os demais carregam o marker `banco`,
declarado em `markers_obrigatorios`.

- `test_adequacao_exige_chefia_e_nivel_suficiente` — Diretor de Divisão titulariza Divisão; Chefe de
  Seção não titulariza Coordenadoria; Assessor VI, mesmo com nível 6, não titulariza nada. Sem banco.
- `test_tipo_sem_minimo_so_aceita_alta_administracao` — no tipo de mínimo nulo, Subsecretário
  titulariza e Coordenador II não. Sem banco.
- `test_unidade_nao_admite_dois_titulares` — marcar um segundo titular na mesma unidade é recusado
  pelo banco. *(marker `banco`)*
- `test_troca_de_titular_destitui_o_anterior` — depois da troca existe exatamente um titular, e é o
  novo. *(marker `banco`)*
- `test_titular_invalido_e_recusado_na_validacao` — rebaixar o cargo do titular, ou mover a unidade
  para um tipo que ele não satisfaz, é recusado na validação. *(marker `banco`)*
- `test_seed_e_ficticios_nascem_com_titularidade` — a carga grava o mínimo declarado em cada tipo, e
  os servidores fictícios deixam titulares marcados. *(marker `banco`)*

## Patches

_Nenhum patch registrado até o momento._
