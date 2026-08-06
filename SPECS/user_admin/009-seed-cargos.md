---
spec: user_admin/009
versao: v1
atualizado_em: 2026-08-05
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC user_admin/009 — Seed dos cargos (base e em comissão)

- [x] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como administrador da plataforma, quero carregar o catálogo de cargos da DIMAP — base e em
comissão — a partir de um arquivo versionado, para que qualquer instalação do sistema parta do
mesmo catálogo, sem cadastro manual.

## Critérios de aceite

- [ ] Um único arquivo `data/seed/cargos.json` declara os **cargos base** e os **cargos em
      comissão** — mesmo padrão de arquivo único da SPEC user_admin/008, aqui sem serventia em
      dividir porque nenhum dos dois catálogos referencia o outro.
- [ ] O comando `seed_cargos` carrega esse arquivo, criando/atualizando `CargoBase` (nome, sigla)
      e `CargoComissao` (nome, sigla, nível, chefia, alta administração).
- [ ] A carga é **idempotente**: a chave natural de `CargoBase` é a `sigla`; a de `CargoComissao`
      é o `nome` — sigla+nível colide entre cargos distintos (ex.: CDA-II serve tanto diretor de
      divisão quanto assessor), então só o nome identifica de forma única. Rodar duas vezes não
      duplica; registro existente tem os demais campos atualizados.
- [ ] Cada `CargoComissao` passa pelo `full_clean()` antes de ser gravado: a regra de
      `alta_administracao` × `nivel` × `e_chefia` do model vale para a seed como vale para
      qualquer outro ponto de escrita.
- [ ] Qualquer falha — validação de `CargoComissao` recusada pelo `clean()`, arquivo malformado —
      **aborta a carga inteira** e não deixa nada gravado, nem em `CargoBase` nem em
      `CargoComissao`.
- [ ] A falha aparece no console como erro do Django (`CommandError`, cor de erro do
      `self.style`) — nunca um traceback cru.
- [ ] `--dry-run` executa e valida a carga completa sem persistir nada.
- [ ] A seed **nunca apaga**: registro que existe no banco e não está no arquivo é deixado como
      está.

## Contexto e decisões de arquitetura

**Mesmo padrão da SPEC user_admin/008, com uma única passagem por catálogo.** Diferente de
`Unidade`, nem `CargoBase` nem `CargoComissao` referenciam outro registro do mesmo tipo — não há
hierarquia entre cargos —, então não existe o problema de "ordem do arquivo importa" que motivou
as duas passagens da 008. Cada catálogo é gravado numa passagem só.

**`CargoBase` sem `full_clean()`, `CargoComissao` com.** `CargoBase` não declara `clean()`: um
`update_or_create` direto já é suficiente. `CargoComissao` declara (a consistência entre
`alta_administracao`, `nivel` e `e_chefia`) e tem `CheckConstraint` espelhando a mesma regra — sem
`full_clean()`, um arquivo inconsistente falharia como `IntegrityError` cru em vez de um erro de
validação legível.

**Um arquivo, dois catálogos, uma transação.** Os dois catálogos não se referenciam entre si, mas
compartilham o mesmo comando e a mesma seed de "cargos da DIMAP" — separar em dois arquivos
obrigaria dois comandos para o mesmo conceito sem ganho de coesão. A carga inteira roda dentro de
um único `atomic()`; `--dry-run` desfaz a transação no fim, igual à 008.

## Peças de referência a compor

- `@apps/user_admin/models` → `CargoBase`, `CargoComissao`: a seed grava nesses models e não
  reimplementa `clean()` nem as `CheckConstraint`.
- `@services/utils/io` → `subpasta_de_data`, `read_json_from_folder`: resolvem `data/seed/` e a
  leitura do arquivo, como em `@apps/user_admin/seed_unidades.py`.
- `@apps/user_admin/seed_unidades.py` e
  `@apps/user_admin/management/commands/seed_unidades.py` → padrão de carregador (DTO Pydantic +
  `update_or_create`/`full_clean()` dentro de `atomic()`) e de comando fino a reaproveitar por
  composição, não por herança.

## Formato do arquivo — `data/seed/cargos.json`

```json
{
  "cargo_base": [
    { "nome": "Auditor Fiscal Tributário Municipal", "sigla": "AFTM" },
    { "nome": "Assistente Administrativo de Gestão", "sigla": "AAG" },
    {
      "nome": "Analista de Planejamento e Desenvolvimento Organizacional - Contadoria",
      "sigla": "APDO-Contador"
    },
    {
      "nome": "Analista de Políticas Públicas e Gestão Governamental",
      "sigla": "APPGG"
    },
    { "nome": "Arquiteto Urbanista", "sigla": "QEAG" }
  ],
  "cargo_comissao": [
    { "nome": "Secretária/o Municipal", "sigla": "SEC", "nivel": null, "e_chefia": true, "alta_administracao": true },
    { "nome": "Chefia de Gabinete", "sigla": "CHG", "nivel": null, "e_chefia": true, "alta_administracao": true },
    { "nome": "Subsecretária/o", "sigla": "SUBSEC", "nivel": null, "e_chefia": true, "alta_administracao": true },
    { "nome": "Secretária/o Adjunta/o", "sigla": "SAD", "nivel": null, "e_chefia": true, "alta_administracao": true },
    { "nome": "Secretário Executivo", "sigla": "SAD-Exec", "nivel": null, "e_chefia": true, "alta_administracao": true },
    { "nome": "Diretor de Departamento", "sigla": "CDA", "nivel": 5, "e_chefia": true, "alta_administracao": false },
    { "nome": "Coordenador II", "sigla": "CDA", "nivel": 6, "e_chefia": true, "alta_administracao": false },
    { "nome": "Coordenador I", "sigla": "CDA", "nivel": 5, "e_chefia": true, "alta_administracao": false },
    { "nome": "Chefe de Assessoria Técnica II", "sigla": "CDA", "nivel": 6, "e_chefia": true, "alta_administracao": false },
    { "nome": "Chefe de Assessoria Técnica I", "sigla": "CDA", "nivel": 5, "e_chefia": true, "alta_administracao": false },
    { "nome": "Diretor de Divisão", "sigla": "CDA", "nivel": 4, "e_chefia": true, "alta_administracao": false },
    { "nome": "Chefe de Seção", "sigla": "CDA", "nivel": 3, "e_chefia": true, "alta_administracao": false },
    { "nome": "Líder de Equipe", "sigla": "CDA", "nivel": 2, "e_chefia": true, "alta_administracao": false },
    { "nome": "Assessor I", "sigla": "CDA", "nivel": 1, "e_chefia": false, "alta_administracao": false },
    { "nome": "Assessor II", "sigla": "CDA", "nivel": 2, "e_chefia": false, "alta_administracao": false },
    { "nome": "Assessor III", "sigla": "CDA", "nivel": 3, "e_chefia": false, "alta_administracao": false },
    { "nome": "Assessor IV", "sigla": "CDA", "nivel": 4, "e_chefia": false, "alta_administracao": false },
    { "nome": "Assessor V", "sigla": "CDA", "nivel": 5, "e_chefia": false, "alta_administracao": false },
    { "nome": "Assessor VI", "sigla": "CDA", "nivel": 6, "e_chefia": false, "alta_administracao": false }
  ]
}
```

`nivel` omitido/`null` é o padrão do model (cargo da alta administração). `alta_administracao`
omitido é `false`, o default do model.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md


class CargoBaseSeed(BaseModel):
    nome: str
    sigla: str


class CargoComissaoSeed(BaseModel):
    nome: str
    sigla: str
    nivel: int | None = None
    e_chefia: bool
    alta_administracao: bool = False


class ArquivoSeedCargos(BaseModel):
    cargo_base: list[CargoBaseSeed]
    cargo_comissao: list[CargoComissaoSeed]


class ContagemSeedCargos(BaseModel):
    cargo_base: int
    cargo_comissao: int


def _gravar_cargo_base(cargos: list[CargoBaseSeed]) -> None:
    for cargo in cargos:
        CargoBase.objects.update_or_create(
            sigla=cargo.sigla,
            defaults={"nome": cargo.nome},
        )


def _gravar_cargo_comissao(cargos: list[CargoComissaoSeed]) -> None:
    for cargo in cargos:
        # get_or_create + full_clean(): sem isso a regra alta_administracao × nivel × e_chefia
        # só apareceria como IntegrityError cru no save.
        obj, _ = CargoComissao.objects.get_or_create(nome=cargo.nome)
        obj.sigla = cargo.sigla
        obj.nivel = cargo.nivel
        obj.e_chefia = cargo.e_chefia
        obj.alta_administracao = cargo.alta_administracao
        obj.full_clean()
        obj.save()


def carregar_seed_cargos(*, dry_run: bool = False) -> ContagemSeedCargos:
    pasta = subpasta_de_data(NOME_SUBPASTA_SEED)
    dados = read_json_from_folder(pasta, NOME_ARQUIVO_SEED)
    arquivo = ArquivoSeedCargos.model_validate(dados)
    with transaction.atomic():
        _gravar_cargo_base(arquivo.cargo_base)
        _gravar_cargo_comissao(arquivo.cargo_comissao)
        if dry_run:
            transaction.set_rollback(True)
    return ContagemSeedCargos(
        cargo_base=len(arquivo.cargo_base),
        cargo_comissao=len(arquivo.cargo_comissao),
    )
```

```python
class Command(BaseCommand):
    help = "Carrega cargos base e em comissão a partir de data/seed/cargos.json."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        dry_run = bool(options["dry_run"])
        try:
            resultado = carregar_seed_cargos(dry_run=dry_run)
        except ValidationError as exc:
            raise CommandError(f"carga abortada: {exc}") from exc
        prefixo = "dry-run ok" if dry_run else "carga concluída"
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefixo}: {resultado.cargo_base} cargos base e "
                f"{resultado.cargo_comissao} cargos em comissão."
            )
        )
```

## Fora de escopo

- Seed de **tipos de impedimento** e **perfis** — cada um segue como sua própria SPEC,
  reaproveitando o mesmo padrão.
- Interface de administração para editar o catálogo; a fonte é o arquivo versionado.
- **Remoção** de cargos ausentes do arquivo.
- Fixtures do Django (`loaddata`) — mesmo motivo da SPEC user_admin/008.

## Testes (TDD)

Todos com o marker `banco`: idempotência e `full_clean()` de `CargoComissao` só se verificam
contra tabela.

- `test_carga_cria_cargo_base_e_cargo_comissao_do_arquivo` — os dois catálogos gravados com os
  campos corretos, inclusive um cargo da alta administração (`nivel=None`). (`banco`)
- `test_carga_e_idempotente` — rodar duas vezes não duplica em nenhum dos dois catálogos, e campo
  alterado no arquivo é atualizado no registro existente. (`banco`)
- `test_cargo_comissao_invalido_aborta_sem_gravar_nada` — `alta_administracao=true` com `nivel`
  preenchido (ou sem `e_chefia`) derruba a carga inteira, incluindo o que já seria válido em
  `cargo_base`. (`banco`)
- `test_dry_run_nao_persiste` — `--dry-run` valida sem deixar registro em nenhum dos dois
  catálogos. (`banco`)

## Patches

_Nenhum patch registrado até o momento._
