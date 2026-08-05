---
spec: user_admin/003
versao: v3
atualizado_em: 2026-08-05
testes_tdd: true
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: a raiz deixa de ser única (árvores paralelas para unidades externas) e o tipo ganha
    veto de tipos-filho, que recorta exceções à regra de nível
  - v3: o tipo ganha `pode_ser_raiz`, e unidade de tipo não-raiz passa a exigir unidade superior
---

# SPEC user_admin/003 — Hierarquia das unidades

- [x] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como administrador da plataforma, quero cadastrar cada unidade da DIMAP com seu tipo (divisão,
departamento, coordenação, coordenadoria, assessoria, secretaria) e sua unidade superior, para que o
organograma fique registrado no sistema e, adiante, a competência administrativa possa ser lida
também pela cadeia de subordinação.

## Critérios de aceite

- [ ] O **tipo de unidade** é um catálogo com nome e **nível** inteiro, criável para tipos não
      previstos hoje — nível maior significa unidade mais abrangente.
- [ ] **Dois tipos podem ter o mesmo nível** (assessoria e coordenação, por exemplo): empate
      significa que nenhum dos dois contém o outro.
- [ ] Toda unidade tem **exatamente um** tipo, e salvar unidade sem tipo é recusado.
- [ ] Uma unidade tem **no máximo um pai**, e a partir dele expõe suas **unidades filhas** diretas.
- [ ] Uma unidade só pode ser filha de uma unidade cujo tipo tem **nível estritamente maior** que o
      seu — uma divisão não subordina um departamento, nem outra divisão.
- [ ] Um tipo pode **vedar tipos de filha**: marcada a veda de divisão em coordenadoria, nenhuma
      coordenadoria aceita divisão como filha, mesmo o nível permitindo. A lista é **opcional** e
      vazia por padrão.
- [ ] Um tipo pode ser marcado como **tipo-raiz**. Só unidade de tipo-raiz fica sem pai; unidade de
      tipo não-raiz sem unidade superior é recusada. A marca vem **desligada por padrão**.
- [ ] **Unidade de tipo-raiz sem pai é admitida** e é raiz da sua própria árvore — mais de uma
      árvore convive (uma unidade de outra secretaria não fica travada).
- [ ] Nenhuma unidade é pai de si mesma.
- [ ] Apagar um tipo em uso, ou uma unidade que tem filhas, é recusado.

## Contexto e decisões de arquitetura

Continua **só camada de persistência**, sobre os models da SPEC `user_admin/001`: entra um model de
tipo de unidade e a `Unidade` ganha `tipo` e `pai`.

**A regra geral é um nível inteiro no tipo, e as exceções são vedas.** O nível sozinho é permissivo
demais (aceitaria divisão pendurada direto na coordenadoria) e um grafo completo de continências
admitidas seria pesado para o que o organograma exige. O meio-termo: o nível permite, e o tipo pode
**vedar** tipos de filha nominalmente. Declara-se só a exceção, não a matriz inteira.

**A veda é do tipo, não da unidade.** "Coordenadoria não tem divisão" vale para toda coordenadoria;
presa à unidade, a mesma veda teria que ser repetida em cada coordenadoria cadastrada, e um
esquecimento abriria um buraco silencioso na regra. É a mesma razão pela qual o nível mora no tipo.

**O tipo é um model, não um enum.** Tipos não previstos (núcleo, gerência) entram por cadastro e
seed, sem migração — e é no tipo que a regra fica presa, via `nivel`.

**Nível não é único.** Dois tipos no mesmo nível apenas não se subordinam entre si; exigir
unicidade transformaria o organograma numa fila e obrigaria a inventar posição para cada tipo novo.

**Nível, veda e exigência de pai vivem no `clean()`; do banco sai só o que é de linha única.** As
três cruzam tabela — nível, vedas e marca de raiz estão no tipo, não na unidade —, então nenhuma
`CheckConstraint` as alcança. No banco fica apenas a `CheckConstraint` de que a unidade não é pai de
si mesma.

**Raiz não é única.** Travar em uma só impediria cadastrar servidor de outra secretaria, cuja
unidade não pende do organograma da nossa. Cada unidade sem pai é raiz da sua árvore, e árvores
paralelas convivem.

**Ser raiz é propriedade do tipo.** O nível sozinho só limita para cima: uma divisão pendurada em
nada passaria. `pode_ser_raiz`, desligado por padrão, obriga a declarar no seed quem encabeça
árvore, e mantém a regra onde já estão o nível e as vedas — presa à unidade, ela teria que ser
repetida a cada cadastro. Custo aceito: a unidade externa de tipo não-raiz exige cadastrar sua
cadeia superior, e em troca o organograma externo fica registrado em vez de virar unidade órfã.

**Ciclo não precisa de verificação.** Descendo a árvore, o nível é estritamente decrescente; uma
cadeia que voltasse a si mesma exigiria um nível menor que ele próprio. A aciclicidade é corolário
da regra, não uma rotina à parte.

**Travessia profunda não entra.** `filhas` (relação reversa) responde "quem está logo abaixo"; subir
a cadeia de ancestrais ou varrer a subárvore é insumo de autorização hierárquica e mora em
`services/domain/` na SPEC que precisar disso.

**Consequência operacional:** `tipo` é obrigatório, então a migração pressupõe a tabela de unidades
ainda sem carga — o seed do épico é que vai nascer com a hierarquia montada. Como toda unidade
passa a exigir tipo, os testes que hoje criam unidade avulsa acompanham.

## Peças de referência a compor

- `@SPECS/user_admin/001` → `Unidade` e o pacote de models do app: o tipo entra no módulo `unidade`
  e o `__init__` passa a reexportá-lo.
- `@SPECS/user_admin/002` → o marker `banco` e o padrão de teste de constraint contra o Postgres
  real.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md
#
# TipoUnidade e os campos novos de Unidade ficam no módulo `unidade` do pacote de models.

ERRO_NIVEL_NAO_SUBORDINA = "A unidade pai precisa ser de um tipo de nível superior."
ERRO_TIPO_FILHO_VEDADO = "A unidade pai não admite filhas deste tipo."
ERRO_TIPO_EXIGE_PAI = "Unidades deste tipo precisam ter uma unidade superior."


class TipoUnidade(models.Model):
    nome = models.CharField(
        max_length=60,
        unique=True,
    )
    # Nível maior = mais abrangente; empate significa que nenhum dos dois contém o outro.
    nivel = models.PositiveSmallIntegerField()
    # Desligado por padrão: encabeçar árvore é exceção declarada no seed, não default silencioso.
    pode_ser_raiz = models.BooleanField(default=False)
    # Exceção ao nível: coordenadoria segue superior à divisão, mas pode recusá-la como filha.
    tipos_filhos_vedados = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="vedado_como_filho_em",
        blank=True,
    )


class Unidade(models.Model):
    nome = models.CharField(
        max_length=120,
        unique=True,
    )
    sigla = models.CharField(
        max_length=20,
        unique=True,
    )
    tipo = models.ForeignKey(
        TipoUnidade,
        on_delete=models.PROTECT,
        related_name="unidades",
    )
    pai = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="filhas",
        null=True,
        blank=True,
    )

    def clean(self) -> None:
        # Sem tipo não há regra a aplicar; quem acusa a ausência é o clean_fields.
        if not hasattr(self, "tipo"):
            return
        if self.pai is None:
            if not self.tipo.pode_ser_raiz:
                raise ValidationError({"pai": ERRO_TIPO_EXIGE_PAI})
            return
        # Nível e vedas vivem no tipo: as regras cruzam tabela e nenhuma CheckConstraint as alcança.
        tipo_pai = self.pai.tipo
        if self.tipo.nivel >= tipo_pai.nivel:
            raise ValidationError({"pai": ERRO_NIVEL_NAO_SUBORDINA})
        if tipo_pai.tipos_filhos_vedados.filter(pk=self.tipo.pk).exists():
            raise ValidationError({"pai": ERRO_TIPO_FILHO_VEDADO})

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(pai=F("id")),
                name="unidade_nao_e_pai_de_si_mesma",
            ),
        ]
```

## Fora de escopo

- Veda no sentido inverso (um tipo declarar em quais tipos **pode** entrar) e veda por unidade
  específica — nesta iteração a exceção só se declara como tipo-filho vedado no tipo-pai.
- Travessia de ancestrais e de subárvore, e qualquer autorização que leia a cadeia de subordinação.
- Seed dos tipos e do organograma da DIMAP — vai junto com o seed do épico.
- Telas, rotas e Django admin para montar a hierarquia.
- Histórico de reorganização administrativa (unidade que muda de pai por decreto).

## Testes (TDD)

Todos levam o marker `banco`: a veda é um M2M e a constraint é do Postgres — nenhum dos dois se
verifica sobre objeto não persistido.

- `test_unidade_filha_exige_nivel_menor_que_o_do_pai` — nível menor valida; nível igual e nível
  maior que o do pai são recusados.
- `test_tipo_pai_recusa_filha_de_tipo_vedado` — com divisão vedada em coordenadoria, a divisão é
  recusada sob a coordenadoria mesmo com nível inferior, e segue aceita sob o departamento.
- `test_tipo_nao_raiz_exige_pai` — unidade de tipo não marcado como raiz é recusada sem pai, e
  aceita sob um pai válido.
- `test_unidades_sem_pai_convivem` — duas unidades de tipo-raiz são salvas sem pai, cada uma com sua
  árvore.
- `test_unidade_nao_pode_ser_pai_de_si_mesma` — apontar o próprio registro como pai é recusado pelo
  banco.
- `test_filhas_lista_as_unidades_subordinadas` — a relação reversa devolve as filhas diretas da
  unidade, e só elas.

## Patches

_Nenhum patch registrado até o momento._
