---
spec: user_admin/008
versao: v2
atualizado_em: 2026-08-05
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: falha da carga vira CommandError no comando — cor de erro do Django, sem traceback cru
---

# SPEC user_admin/008 — Seed das unidades

- [x] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como administrador da plataforma, quero carregar o organograma da DIMAP a partir de um arquivo
versionado, para que qualquer instalação do sistema — máquina nova, banco recriado, ambiente de
outro desenvolvedor — parta do mesmo catálogo de tipos e unidades, sem cadastro manual.

## Critérios de aceite

- [ ] Um único arquivo `data/seed/unidades.json` declara os **tipos de unidade** e as **unidades**;
      tipo sem unidade não tem serventia e por isso não ganha arquivo próprio.
- [ ] O comando `seed_unidades` carrega esse arquivo, criando os tipos (com nível, marca de raiz e
      vedas de tipo-filho) e as unidades (com tipo, unidade superior e cor).
- [ ] A carga é **idempotente**: a chave natural do tipo é o `nome` e a da unidade é a `sigla`.
      Rodar duas vezes não duplica; registro existente tem os demais campos atualizados. A lista de
      vedas do arquivo **substitui** a do banco — veda retirada do arquivo some do registro.
- [ ] A **ordem das unidades no arquivo é irrelevante** — uma unidade pode aparecer antes da sua
      superior.
- [ ] Cada unidade passa pelo `full_clean()` antes de ser gravada: as regras de hierarquia da SPEC
      user_admin/003 valem para a seed exatamente como valem para o formulário.
- [ ] Qualquer falha — sigla de pai inexistente, tipo desconhecido, hierarquia inválida — **aborta a
      carga inteira** e não deixa nada gravado.
- [ ] A falha aparece no console como erro do Django (`CommandError`, cor de erro do `self.style`) com
      a mensagem da causa — nunca um traceback cru.
- [ ] Cada unidade declara sua `cor` explicitamente, escolhida entre os tons da paleta; omitida,
      fica com o padrão do model.
- [ ] `--dry-run` executa e valida a carga completa sem persistir nada.
- [ ] A seed **nunca apaga**: registro que existe no banco e não está no arquivo é deixado como
      está.

## Contexto e decisões de arquitetura

**Mexe em persistência e orquestração, não em domínio.** A seed carrega um catálogo administrativo
cuja única regra já está escrita — o `clean()` de `Unidade` (SPEC user_admin/003). Não há
conhecimento sobre território aqui, então o código vive no app `user_admin`, e não em `services/`:
partir a carga em duas metades só para que a leitura do JSON ficasse fora do Django custaria um
módulo a mais sem comprar teste mais barato (os testes que importam exigem banco de qualquer forma).
O comando segue **fino** (§6.4): parsing de argumento, chamada e feedback.

**Duas passagens em vez de ordenação topológica.** Primeiro cada unidade é gravada sem `pai`;
depois a superior é ligada e o `full_clean()` roda. Isso torna a ordem do arquivo irrelevante sem
nenhum algoritmo de ordenação — e dispensa detecção de ciclo, porque o próprio model já a faz: a
subordinação exige nível **estritamente** maior, e ciclo exigiria nível decrescente para sempre.

A validação fica **toda** na segunda passagem, e é de propósito: sem `pai` ligado, o `clean()`
recusaria toda unidade de tipo não-raiz. A primeira passagem só existe dentro da transação, então
estado meio-gravado não sobrevive a uma falha.

**A cor é dado, não algoritmo.** Cada unidade traz o seu slug no arquivo e a carga apenas o grava —
sem herança a partir da superior e sem derivação do nível: mecanismo aqui só criaria uma segunda
fonte de verdade para um valor que o cadastro pode mudar depois.

**Transação única, `--dry-run` por rollback.** A carga inteira roda dentro de um `atomic()`; em
dry-run a transação é desfeita no fim. É o que faz o dry-run validar de verdade — inclusive o que só
o banco sabe responder —, em vez de checar metade das regras.

**O carregador levanta, o comando traduz.** `carregar_seed_unidades` deixa a falha subir como
exceção (`ValidationError` do `clean()`, `DoesNotExist` de sigla ausente) — é o próprio mecanismo do
Django, sem reinventar um DTO de erro. O comando é quem converte para `CommandError`: é o único
ponto que conhece `self.style`, e é assim que o Django já imprime erro de comando em vermelho, sem
`try/except` espalhado nem traceback cru no console de quem roda a seed.

**Não é comando de pipeline.** Não escreve artefato em `data/`, não entra em `ETAPAS` e não registra
metadados de execução: por isso não expõe `--verbose` nem `--automatico`, que existem para as cargas
das bases oficiais (skill `management-commands`).

## Peças de referência a compor

- `@apps/user_admin/models` → `TipoUnidade`, `Unidade`, `CorUnidade`: a seed grava nesses models e
  **não reimplementa** nenhuma das regras deles.
- `Unidade.clean()` (SPEC user_admin/003) → nível, veda de tipo-filho e exigência de pai: a seed
  chama `full_clean()` e deixa o model recusar.
- `@services/utils/io` → `subpasta_de_data`, `read_json_from_folder`: resolvem `data/seed/` e a
  leitura do arquivo. **Não montar `Path` para `data/`** no comando nem no carregador.
- `@apps/user_admin/paleta.py` → `HEX_POR_COR`: os oito tons disponíveis e a garantia de contraste
  contra a tinta do avatar; a seed grava o **slug**, nunca o hex.

## Formato do arquivo — `data/seed/unidades.json`

```json
{
  "tipos": [
    {
      "nome": "Equipe",
      "nivel": 1
    },
    {
      "nome": "Seção",
      "nivel": 2
    },
    {
      "nome": "Divisão",
      "nivel": 3
    },
    {
      "nome": "Departamento",
      "nivel": 4
    },
    {
      "nome": "Coordenação",
      "nivel": 5
    },
    {
      "nome": "Coordenadoria",
      "nivel": 6,
      "tipos_filhos_vedados": ["Divisão"]
    },
    {
      "nome": "Assessoria",
      "nivel": 6,
      "tipos_filhos_vedados": ["Divisão", "Departamento", "Coordenação"]
    },
    {
      "nome": "Subsecretaria",
      "nivel": 7,
      "tipos_filhos_vedados": ["Divisão"]
    },
    {
      "nome": "Secretaria Executiva",
      "nivel": 8,
      "tipos_filhos_vedados": ["Divisão", "Departamento"]
    },
    {
      "nome": "Gabinete da/do Secretária/o",
      "nivel": 9,
      "pode_ser_raiz": true,
      "tipos_filhos_vedados": ["Divisão"]
    }
  ],
  "unidades": [
    {
      "nome": "Gabinete do Secretário Municipal da Fazenda",
      "sigla": "SF-GAB",
      "tipo": "Gabinete da/do Secretária/o",
      "pai": null,
      "cor": "rocha-900"
    },
    {
      "nome": "Subsecretaria da Receita Municipal",
      "sigla": "SUREM",
      "tipo": "Subsecretaria",
      "pai": "SF-GAB",
      "cor": "madeira-700"
    },
    {
      "nome": "Departamento de Cadastros",
      "sigla": "DECAD",
      "tipo": "Departamento",
      "pai": "SUREM",
      "cor": "sakura-700"
    },
    {
      "nome": "Divisão do Mapa de Valores",
      "sigla": "DIMAP",
      "tipo": "Divisão",
      "pai": "DECAD",
      "cor": "agua-800"
    },
    {
      "nome": "DIMAP-1",
      "sigla": "DIMAP-1",
      "tipo": "Seção",
      "pai": "DIMAP",
      "cor": "agua-700"
    },
    {
      "nome": "DIMAP-2",
      "sigla": "DIMAP-2",
      "tipo": "Seção",
      "pai": "DIMAP",
      "cor": "rocha-700"
    },
    {
      "nome": "DIMAP-3",
      "sigla": "DIMAP-3",
      "tipo": "Seção",
      "pai": "DIMAP",
      "cor": "madeira-600"
    },
    {
      "nome": "DIMAP-4",
      "sigla": "DIMAP-4",
      "tipo": "Seção",
      "pai": "DIMAP",
      "cor": "sakura-600"
    }
  ]
}
```

`pode_ser_raiz` omitido é `false` e `tipos_filhos_vedados` omitido é lista vazia — os mesmos
defaults do model, para que o arquivo declare só o que é exceção.

### A cor

Escolhida caso a caso entre os oito tons da paleta, sem regra derivada — nem do nível, nem da
superior. Cor amarrada ao nível diria "é uma divisão" onde a SPEC user_admin/005 quer que diga "é da
DIMAP", e ramos vizinhos ganham tons distintos justamente para se separarem à vista. Repetição entre
unidades distantes é aceita: a cor é pista, não chave.

As oito unidades usam os oito tons, sem repetição. As quatro seções da DIMAP ficam **uma em cada
família** — é onde estão os servidores, e é ali que distinguir a unidade pelo avatar tem uso; a
cadeia hierárquica acima fica com o tom mais escuro de cada família. Só a DIMAP e a DIMAP-1
compartilham família (água), o que é inevitável com quatro seções para quatro famílias, e cai bem
na filha direta.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md


class TipoUnidadeSeed(BaseModel):
    nome: str
    nivel: int
    pode_ser_raiz: bool = False
    tipos_filhos_vedados: list[str] = []


class UnidadeSeed(BaseModel):
    nome: str
    sigla: str
    tipo: str
    pai: str | None = None
    cor: CorUnidade | None = None


class ArquivoSeedUnidades(BaseModel):
    tipos: list[TipoUnidadeSeed]
    unidades: list[UnidadeSeed]
```

```python
class AplicadorUnidades:
    """Grava sem pai, depois liga a superior: a ordem do arquivo deixa de importar."""

    def __call__(self, unidades: list[UnidadeSeed]) -> ContagemSeed:
        return self.pipeline(unidades)

    def pipeline(self, unidades: list[UnidadeSeed]) -> ContagemSeed:
        contagem = self._gravar_sem_pai(unidades)
        self._ligar_superiores(unidades)
        return contagem

    def _ligar_superiores(self, unidades: list[UnidadeSeed]) -> None:
        # full_clean() aqui, com o pai já ligado — antes disso a hierarquia nem existe.
        ...
```

```python
class Command(BaseCommand):
    help = "Carrega tipos de unidade e unidades a partir de data/seed/unidades.json."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        try:
            resultado = carregar_seed_unidades(dry_run=bool(options["dry_run"]))
        # ObjectDoesNotExist cobre sigla de pai e tipo ausentes; ValidationError cobre o clean().
        except (ObjectDoesNotExist, ValidationError) as exc:
            raise CommandError(f"carga abortada: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(...))
```

## Fora de escopo

- Seed de **cargos base**, **cargos em comissão**, **tipos de impedimento** e **perfis** — cada um
  vira sua própria SPEC, reaproveitando o padrão de arquivo e comando fixado aqui.
- Interface de administração para editar o organograma; a fonte é o arquivo versionado.
- **Remoção** de tipos ou unidades ausentes do arquivo, e qualquer forma de sincronização
  bidirecional.
- Fixtures do Django (`loaddata`) — o formato próprio existe para referenciar tipo e superior por
  chave natural e passar pelo `full_clean()`, coisas que a fixture não faz.

## Testes (TDD)

Todos com o marker `banco`: a hierarquia é validada em `clean()` contra tabela e nenhuma dessas
regras se verifica sobre objeto não persistido.

- `test_carga_cria_tipos_e_unidades_do_arquivo` — tipos gravados com nível, marca de raiz e vedas;
  unidades gravadas com tipo e superior corretos. (`banco`)
- `test_carga_e_idempotente` — rodar duas vezes não duplica, e campo alterado no arquivo é
  atualizado no registro existente. (`banco`)
- `test_ordem_do_arquivo_e_irrelevante` — unidade declarada antes da sua superior é gravada com o
  vínculo correto. (`banco`)
- `test_pai_inexistente_aborta_sem_gravar_nada` — sigla de superior ausente no arquivo derruba a
  carga e o banco fica intocado. (`banco`)
- `test_hierarquia_invalida_e_recusada` — filha de tipo de nível não superior, ou de tipo vedado,
  falha a carga inteira. (`banco`)

## Patches

_Nenhum patch registrado até o momento._
