---
spec: user_admin/010
versao: v2
atualizado_em: 2026-09-03
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: a carga passa a só criar o que falta — tipo que já existe fica intacto
---

# SPEC user_admin/010 — Seed dos tipos de impedimento

- [x] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como administrador da plataforma, quero carregar o catálogo de tipos de impedimento — férias,
licenças, afastamentos — a partir de um arquivo versionado, para que qualquer instalação do
sistema parta do mesmo catálogo, sem cadastro manual.

## Critérios de aceite

- [ ] Um arquivo `data/seed/tipos_impedimento.json` declara os tipos de impedimento (nome e sigla
      opcional).
- [ ] O comando `seed_tipos_impedimento` carrega esse arquivo, criando `TipoImpedimento`.
- [ ] A carga **só cria o que falta**, com chave natural o **nome**: é o único campo com unicidade
      incondicional do model (a sigla só é única quando preenchida — SPEC user_admin/002 —, então
      não serve de chave). Registro que já existe é **deixado intacto**; rodar duas vezes não
      duplica nem reescreve a sigla.
- [ ] Cada `TipoImpedimento` **criado** passa pelo `full_clean()` antes de ser gravado: duas siglas iguais no
      arquivo violam a `UniqueConstraint` do model e a falha aparece como erro de validação
      legível, não como `IntegrityError` cru.
- [ ] Qualquer falha — validação recusada, arquivo malformado — **aborta a carga inteira** e não
      deixa nada gravado.
- [ ] A falha aparece no console como erro do Django (`CommandError`, cor de erro do
      `self.style`) — nunca um traceback cru.
- [ ] `--dry-run` executa e valida a carga completa sem persistir nada.
- [ ] A seed **nunca apaga**: registro que existe no banco e não está no arquivo é deixado como
      está.

## Contexto e decisões de arquitetura

**Mesmo padrão da SPEC user_admin/009, com um catálogo só.** `TipoImpedimento` não referencia
outro registro do mesmo tipo, então não há o problema de ordem que motivou as duas passagens da
008 — uma passagem basta.

**Só cria o que falta.** Mesma decisão da SPEC user_admin/008 v3, pelo mesmo motivo: depois do
bootstrap o catálogo é mantido pelo sistema, e uma carga que reescreve o registro existente
desfaria essa manutenção a cada subida do container. Como corolário, editar
`data/seed/tipos_impedimento.json` não propaga mais para banco já carregado.

**Chave natural é o nome, não a sigla.** Ao contrário de `CargoBase`, a sigla de
`TipoImpedimento` é opcional e vários tipos convivem sem ela (SPEC 002): não dá para chavear por
um campo que pode ficar vazio em mais de um registro. O nome é `unique=True` no model, então é ele
quem identifica o registro — o mesmo raciocínio que levou `CargoComissao` a chavear por nome em
vez de sigla+nível.

**`full_clean()` sempre, mesmo sem `clean()` custom no model.** `TipoImpedimento` não tem lógica de
`clean()`, mas tem uma `UniqueConstraint` condicional na sigla; `full_clean()` valida constraints
de unicidade e transforma um arquivo com sigla duplicada em `ValidationError` legível em vez de
`IntegrityError` de banco — a mesma razão da 009 para `CargoComissao`.

**A carga roda dentro de um único `atomic()`**; `--dry-run` desfaz a transação no fim, igual às
seeds anteriores.

## Peças de referência a compor

- `@apps/user_admin/models` → `TipoImpedimento`: a seed grava nesse model e não reimplementa a
  `UniqueConstraint` condicional da sigla.
- `@services/utils/io` → `subpasta_de_data`, `read_json_from_folder`: resolvem `data/seed/` e a
  leitura do arquivo, como nas seeds existentes.
- `@apps/user_admin/seed_cargos.py` e
  `@apps/user_admin/management/commands/seed_cargos.py` → padrão de carregador (DTO Pydantic +
  criação do que falta por chave natural + `full_clean()` dentro de `atomic()`) e de comando fino a reaproveitar
  por composição, não por herança.

## Formato do arquivo — `data/seed/tipos_impedimento.json`

```json
{
  "tipos": [
    { "nome": "Férias", "sigla": null },
    { "nome": "Licença para Tratar de Interesses Particulares", "sigla": "LIP" },
    { "nome": "Licença para Tratamento de Saúde", "sigla": "LTS" },
    { "nome": "Licença por Motivo de Doença em Pessoa da Família", "sigla": null },
    { "nome": "Licença Maternidade", "sigla": null },
    { "nome": "Licença Paternidade", "sigla": null },
    { "nome": "Afastamento para Cursos e Congressos", "sigla": null },
    { "nome": "Licença Médica de Curta Duração", "sigla": null },
    { "nome": "Licença Gala", "sigla": null },
    { "nome": "Licença Nojo", "sigla": null }
  ]
}
```

`sigla` nula/omitida vira `""`, o default do model.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md


class TipoImpedimentoSeed(BaseModel):
    nome: str
    sigla: str | None = None


class ArquivoSeedTiposImpedimento(BaseModel):
    tipos: list[TipoImpedimentoSeed]


class ContagemSeedTiposImpedimento(BaseModel):
    tipos: int


def _gravar_tipos(tipos: list[TipoImpedimentoSeed]) -> int:
    criados = 0
    for tipo in tipos:
        if TipoImpedimento.objects.filter(nome=tipo.nome).exists():
            continue
        # Monta em memória e só então full_clean(): create() gravaria antes de a
        # UniqueConstraint condicional da sigla ser checada.
        obj = TipoImpedimento(
            nome=tipo.nome,
            sigla=tipo.sigla or "",
        )
        obj.full_clean()
        obj.save()
        criados += 1
    return criados


def carregar_seed_tipos_impedimento(*, dry_run: bool = False) -> ContagemSeedTiposImpedimento:
    pasta = subpasta_de_data(NOME_SUBPASTA_SEED)
    dados = read_json_from_folder(pasta, NOME_ARQUIVO_SEED)
    arquivo = ArquivoSeedTiposImpedimento.model_validate(dados)
    with transaction.atomic():
        criados = _gravar_tipos(arquivo.tipos)
        if dry_run:
            transaction.set_rollback(True)
    return ContagemSeedTiposImpedimento(tipos=criados)
```

```python
class Command(BaseCommand):
    help = "Carrega tipos de impedimento a partir de data/seed/tipos_impedimento.json."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="valida a carga completa sem persistir nada.",
        )

    def handle(self, *args: object, **options: object) -> None:
        dry_run = bool(options["dry_run"])
        try:
            resultado = carregar_seed_tipos_impedimento(dry_run=dry_run)
        except ValidationError as exc:
            raise CommandError(f"carga abortada: {exc}") from exc
        prefixo = "dry-run ok" if dry_run else "carga concluída"
        self.stdout.write(
            self.style.SUCCESS(f"{prefixo}: {resultado.tipos} tipos de impedimento criados.")
        )
```

## Fora de escopo

- Seed de **perfis** e de **impedimentos concretos** — o impedimento concreto liga um servidor
  real a um período e não é dado de catálogo (ver "fora de escopo" da SPEC 002).
- Interface de administração para editar o catálogo; a fonte é o arquivo versionado.
- **Remoção** de tipos ausentes do arquivo.
- Fixtures do Django (`loaddata`) — mesmo motivo das seeds anteriores.

## Testes (TDD)

Todos com o marker `banco`: idempotência e `full_clean()` só se verificam contra tabela.

- `test_carga_cria_tipos_impedimento_do_arquivo` — todos os tipos gravados com nome e sigla
  corretos, inclusive vários tipos sem sigla convivendo. (`banco`)
- `test_carga_nao_toca_registro_existente` — rodar duas vezes não duplica, e sigla alterada no
  arquivo **não** reescreve o registro que já estava no banco. (`banco`)
- `test_sigla_duplicada_no_arquivo_aborta_sem_gravar_nada` — dois tipos com a mesma sigla no
  arquivo derrubam a carga inteira, nada persistido. (`banco`)
- `test_dry_run_nao_persiste` — `--dry-run` valida sem deixar registro no catálogo. (`banco`)

## Patches

_Nenhum patch registrado até o momento._
