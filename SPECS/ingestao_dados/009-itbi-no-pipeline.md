---
spec: ingestao_dados/009
versao: v3
atualizado_em: 2026-08-03
testes_tdd: true
implementado: true
depende_de: [ingestao_dados/007, ingestao_dados/008]
changelog:
  - v1: versão inicial
  - v2: o comando não nasce em `apps/core` — entra num app novo, `amostrador_ofertas`, que é o
    consumidor previsto pela SPEC 008 e nasce aqui como casca, só com o comando
  - v3: a carga ganha **escopo** (`recente` | `completo`), com `recente` como padrão — o ciclo
    noturno passa a atualizar só o ano mais recente, e a carga completa vira `--completo` na mão.
    Coleta e parse filtram; a consolidação nunca filtra. Deixa de ser verdade que esta SPEC não
    mexe em `services/`
---

# SPEC ingestao_dados/009 — A carga do ITBI entra no pipeline de atualização

- [x] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

> **Depende da 008** (a carga ITBI, já aderente ao `ScriptRunner`) e da **007** (o one-shot, a
> constante `ETAPAS` e a cadeia `--automatico` → `manual`). Ela dá ao ITBI a porta de entrada que a
> 008 deixou de propósito para depois, e acrescenta à carga o **escopo**, que é o que torna rodá-la
> todo dia sustentável.

## User story
Como operador da plataforma, quero que a carga das guias de ITBI pagas rode junto das demais no
ciclo noturno do daemon, atualizando **só o ano que ainda muda**, para que o parquet do ITBI não
dependa de alguém lembrar de rodá-la na mão — que hoje é a única forma de atualizá-la, porque ela
não tem management command — e sem rebaixar toda noite vinte anos fechados que nunca mudam.

## Critérios de aceite

- [ ] Existe um app novo, **`amostrador_ofertas`**, registrado no `INSTALLED_APPS`. Ele nasce como
      **casca**: só o management command da carga, sem rotas, sem views e sem contrato de ação.
- [ ] Existe um **management command fino** para a carga do ITBI, **dentro desse app**, no padrão do
      pipeline: expõe `--verbose` e `--automatico`, repassa `verbose` e `manual=not automatico` ao
      `run()` e **não lê `settings`** — URL do portal e política de retry continuam sendo default do
      `ItbiConfig`.
- [ ] O comando **formata o `ItbiResult`** no stdout: total de registros e caminho do parquet, e —
      quando não vazios — `anos_desatualizados`, `anos_ausentes` e as falhas por ano da coleta e do
      parse. Sucesso parcial é sucesso, e é no log do daemon que ele precisa aparecer.
- [ ] A etapa entra na constante `ETAPAS` do one-shot, **na última posição**, e passa a ser
      executada por `manage.py atualizar_dados` e pelo daemon. Nenhuma outra etapa muda de ordem.
- [ ] Rodando pelo daemon, a execução chega aos metadados com `manual: false`; rodada na mão, com
      `manual: true` — sem flag nenhuma no terminal.

### Escopo da carga

- [ ] O `ItbiConfig` ganha um **escopo** com dois valores — **`recente`** (só o ano mais recente) e
      **`completo`** (todos os anos) — e **`recente` é o padrão**. É ele que o daemon roda, porque o
      one-shot não passa flag nenhuma além de `--verbose`/`--automatico`.
- [ ] O comando expõe **`--completo`**, e só ele produz a carga de todos os anos. Refazer a base
      inteira é ato deliberado, na mão.
- [ ] No escopo `recente`, **coleta e parse filtram; a consolidação não**. Cada etapa aplica a mesma
      regra ao **próprio input** — a coleta baixa o ano mais recente que o **portal publica**, o
      parse parseia o ano mais recente que há **em disco** —, e nenhuma delas recebe a lista da
      etapa anterior. A consolidação continua sendo a projeção da pasta inteira.
- [ ] **O parquet final continua com todos os anos** depois de uma carga `recente`: os demais
      permanecem com o parquet por ano que já estava em disco. Um checkout limpo é o caso em que
      isso não vale, e o relatório o denuncia (§`anos_ausentes`, já existente).
- [ ] **O escopo aparece no resultado e nos metadados**, e `anos_desatualizados` passa a respeitá-lo:
      no escopo `recente`, ano fora do escopo **não** é reportado como desatualizado — ele não foi
      atualizado porque não devia ser, e reportá-lo faria o relatório noturno acusar vinte anos toda
      noite. No escopo `completo`, o critério é o da 008, intocado.

## Contexto e decisões de arquitetura

Mexe na **orquestração** — um app novo, um comando fino dentro dele e uma linha na constante
`ETAPAS` — e, em `services/`, acrescenta à carga do ITBI o **escopo**, que é o que torna rodá-la
todo dia sustentável. A 008 entregou a carga inteira e deixou fora de escopo o comando e a entrada
no pipeline, apostando que nasceriam com o app consumidor (amostras para avaliação). É o que
acontece aqui — o app é criado, e o parquet do ITBI deixa de ser o único de `data/` que ninguém
atualiza.

**O app é `amostrador_ofertas`, e ele nasce como casca.** É a ação da DIMAP-1 que vai consumir este
dado (§3.5: uma ação, um app), e por isso o comando é dela e não de `apps/core` — a carga do ITBI
não é infraestrutura transversal, é o insumo de um processo específico. Nesta iteração o app tem
**só o comando**: sem rota, sem contrato, sem inscrição no router. Criar a casca agora é o que evita
o comando nascer no lugar errado e ter que migrar depois; criar a ação junto seria escrever ação sem
SPEC de ação.

**Última posição, e é o único critério de ordenação que importa aqui.** O pipeline aborta na
primeira falha (007), e o ITBI é a etapa mais frágil que ele tem: um portal de CMS que responde 503,
~20 downloads e ~20 planilhas manuais para parsear. Nenhuma outra etapa consome o parquet do ITBI,
então pô-lo no fim faz a falha dele custar só ele — no meio, um 503 do portal impediria a variação
dos logradouros de rodar.

**Sem `settings` e sem variável de ambiente nova.** A 008 previu que a URL e os timeouts virariam
`settings` junto com o app consumidor; o app chegou, mas não o motivo — nada ali varia por ambiente
hoje, e a regra da 006 para constante do próprio script é default no `Config`. O comando não existe
para devolver ao script uma constante que já é dele. A promoção entra quando houver um ambiente que
precise de valor diferente.

**O escopo existe porque o ciclo é diário.** Rodar a carga completa toda noite seria rebaixar e
reparsear ~20 planilhas inteiras — vinte anos fechados, que não mudam mais, mais o corrente, que é o
único que muda. O escopo `recente` reduz o ciclo noturno a um download e um parse; a carga completa
continua existindo para o dia em que o portal republicar um ano antigo ou o parser mudar, e aí é
comando na mão.

**`recente` é o padrão porque o daemon não tem como pedir outra coisa.** O one-shot executa as
etapas por nome, com `--verbose` e `--automatico` fixos; não há canal para uma flag por etapa, e
inventar um faria o pipeline conhecer as opções de cada script. Então quem decide o ciclo noturno é
o default do `Config` — e o default certo é o barato, com o caro atrás de uma flag explícita.

**Cada etapa aplica o escopo ao próprio input, e é isso que preserva a independência da 008.** A
coleta pergunta ao portal qual é o ano mais recente; o parse pergunta ao disco. Nenhuma das duas
recebe a lista da outra — a interface entre as etapas continua sendo a pasta, e o teste da 008 que
protege isso continua valendo. Na prática as duas respostas coincidem; quando não coincidirem
(download do ano corrente falhou), o parse reprocessa o ano mais recente que existe, que é o
comportamento correto e não precisa de regra nova.

**A consolidação nunca filtra.** Ela é a projeção da pasta de parseados, e filtrá-la faria o parquet
encolher para um ano — exatamente o que a 008 desenhou as duas pastas para impedir. É por isso que
uma carga `recente` continua entregando o parquet inteiro.

**O escopo muda o significado de `anos_desatualizados`, e por isso viaja no resultado.** O critério
da 008 — "está no parquet e não atualizou agora" — acusaria vinte anos toda noite sob o escopo
`recente`, e um relatório que sempre acusa tudo não é lido. Sob `recente`, o campo passa a olhar só
os anos que a carga se propôs a atualizar; sob `completo`, é o critério da 008, intocado. Registrar
o escopo nos metadados é o que permite, meses depois, distinguir "só um ano atualizou" de "só um ano
foi pedido".

**Custo aceito: os testes multi-ano da 008 passam a declarar `escopo=completo`.** É o comportamento
deles desde sempre — o que muda é que agora ele tem nome e não é mais o default. O comportamento que
cada um fixa continua idêntico.

## Peças de referência a compor

- `@services/scripts/itbi` → `run`, `ItbiConfig`, `ItbiResult`: a carga inteira, pronta e aderente
  ao `ScriptRunner`. O comando a **chama**, não a reimplementa, e `ItbiResult` já traz
  `anos_desatualizados` e `anos_ausentes` calculados. O `Config` ganha o escopo; o `Result`, o
  escopo que rodou.
- `@services/scripts/itbi/coletor.py` e `@…/parser.py` → as etapas 1 e 2: as duas ganham o filtro
  do escopo sobre o input **que cada uma já lê hoje** (a lista do scraper, a pasta de originais).
  Nenhuma passa a conhecer a outra.
- `@services/scripts/itbi/disco.py` → onde já mora a leitura "quais anos esta pasta tem": é a
  prateleira do filtro de escopo, que é a mesma regra para as duas etapas e por isso existe uma vez.
- `@apps/core/management/commands/atualizar_dados.py` → a constante `ETAPAS` e a injeção do
  executor: é o único ponto que muda no one-shot.
- `@apps/address_geocoder/management/commands/extrair_enderecos_fiscais.py` → o molde do comando
  fino com as duas flags do pipeline.
- `@apps/lote_matcher` → o molde do app mínimo (o que um app do projeto tem quando não tem model).
- `@config/settings.py` → o `INSTALLED_APPS`, onde o app novo se registra: sem isso o Django não
  descobre o comando.
- `@.claude/skills/management-commands/SKILL.md` → a anatomia do comando e a regra do
  `--automatico`; a skill já manda "script novo do pipeline entra em `ETAPAS`", então ela **não
  muda** com esta SPEC.

## Snippets sugeridos

```python
# apps/amostrador_ofertas/management/commands/extrair_guias_itbi.py — fino: sem settings,
# porque URL e retry são constantes do próprio script (default do ItbiConfig).
class Command(BaseCommand):
    help = "Baixa as planilhas de guias de ITBI pagas do portal da Fazenda e consolida em data/."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--verbose", action="store_true")
        parser.add_argument(
            "--automatico",
            action="store_true",
            help="uso interno do daemon: marca a execução como automática nos metadados.",
        )
        parser.add_argument(
            "--completo",
            action="store_true",
            help="rebaixa e reparseia TODOS os anos publicados; sem a flag, só o mais recente.",
        )

    def handle(self, *args: object, **options: object) -> None:
        escopo = EscopoCarga.COMPLETO if options["completo"] else EscopoCarga.RECENTE
        result = run(
            ItbiConfig(escopo=escopo),
            verbose=bool(options["verbose"]),
            manual=not options["automatico"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído. {result.consolidacao.total_records} registros "
                f"em {result.output_path}"
            )
        )
        # Sucesso parcial é sucesso: sem isto, o log do daemon não denuncia ano que envelheceu
        # nem ano que o portal publica e a base não tem.
        if result.anos_desatualizados:
            self.stdout.write(self.style.WARNING(f"desatualizados: {result.anos_desatualizados}"))
        if result.anos_ausentes:
            self.stdout.write(self.style.WARNING(f"ausentes: {result.anos_ausentes}"))
```

```python
# apps/core/management/commands/atualizar_dados.py — uma linha a mais, no fim
ETAPAS: tuple[str, ...] = (
    "extrair_segmentos_logradouros",
    "extrair_nomes_logradouros",
    "extrair_enderecos_fiscais",
    "augment_logradouro_types",
    # Última: o pipeline aborta na primeira falha, e nenhuma etapa consome o parquet do ITBI.
    "extrair_guias_itbi",
)
```

```python
# services/scripts/itbi/models.py — o escopo é do Config, e viaja até o Result porque muda
# o significado do relatório.
class EscopoCarga(StrEnum):
    RECENTE = "recente"
    COMPLETO = "completo"


class ItbiConfig(BaseModel):
    portal: ItbiPortalConfig = Field(default_factory=ItbiPortalConfig)
    # O default é o que o daemon roda: o one-shot não tem como passar flag por etapa.
    escopo: EscopoCarga = EscopoCarga.RECENTE


class ItbiResult(BaseModel):
    escopo: EscopoCarga

    @property
    def anos_desatualizados(self) -> list[int]:
        """No parquet com dado de uma carga anterior: não baixou OU não parseou agora."""
        atualizados = set(self.coleta.anos_baixados) & set(self.parse.anos_parseados)
        candidatos = set(self.consolidacao.anos_no_parquet)
        if self.escopo is EscopoCarga.RECENTE:
            # Fora do escopo, não atualizar é a intenção — acusar isso toda noite cala o relatório.
            candidatos &= set(self.coleta.anos_alvo)
        return sorted(candidatos - atualizados)
```

```python
# services/scripts/itbi/disco.py — a mesma regra para as duas etapas, escrita uma vez:
# "o escopo recente é o ano mais alto que ESTA etapa enxerga".
def anos_do_escopo(anos: Iterable[int], escopo: EscopoCarga) -> set[int]:
    vistos = set(anos)
    if escopo is EscopoCarga.COMPLETO or not vistos:
        return vistos
    return {max(vistos)}
```

## Fora de escopo

- **Promover URL e timeouts do ITBI a `settings`** — continuam default do `Config`, pela regra da
  006. Entra com o app consumidor.
- **Baixar só o que mudou** (`If-Modified-Since`, hash): segue fora de escopo como na 008 — o escopo
  `recente` resolve o custo do ciclo diário por outro caminho, mais simples e sem cache a invalidar.
- **Escopo por ano arbitrário** (`--ano 2019`, intervalos): são dois valores porque são os dois
  regimes reais — o ciclo noturno e a refação da base. Ano específico entra quando houver caso.
- **Detectar sozinho que um ano antigo mudou no portal**: se o publicador reeditar 2019, só a carga
  completa o pega. É o que a flag existe para fazer.
- **Frequência própria por etapa** (rodar o ITBI semanalmente e o resto todo dia): o daemon tem um
  horário e um pipeline, e a 007 já deixou "múltiplos horários" fora de escopo.
- **A ação de amostragem de ofertas em si** — rota protegida, contrato declarando o perfil,
  inscrição no router, registro da execução, telas. O app nasce aqui como casca do pipeline de
  dados; a ação vem em SPEC própria, e é lá que o §3.5 é cumprido.
- **Consumir o dado** — catálogo em memória, matching de SQL, geocodificação dos endereços do ITBI.
- **Alertar sobre `anos_ausentes`/`falhas_por_ano`** (e-mail, webhook): o dado aparece no stdout e
  nos metadados; agir sobre ele é outra iteração, como a 007 já registrou.

## Testes (TDD)

- `test_itbi_e_a_ultima_etapa_do_pipeline` — `ETAPAS` contém a etapa do ITBI e ela é a **última**:
  fixa a decisão de isolamento de falha, que uma reordenação distraída desfaria em silêncio.
- `test_toda_etapa_do_pipeline_tem_comando_em_app_instalado` — por descoberta sobre `ETAPAS`: cada
  nome corresponde a um comando existente **num app do `INSTALLED_APPS`**. Nome errado ou app novo
  fora do `INSTALLED_APPS` só apareceriam como `CommandError` no ciclo noturno; o teste cresce
  sozinho com a próxima etapa.
- `test_carga_padrao_e_o_escopo_recente` — o default do `ItbiConfig` é `recente`. É uma linha, e é
  ela que decide o que o daemon faz toda noite: o one-shot não passa flag por etapa.
- `test_escopo_recente_atualiza_so_o_ano_mais_recente_e_preserva_os_demais` — portal publicando dois
  anos, os dois em disco: só o mais recente é baixado e só o parquet dele é reescrito, e o parquet
  final continua com os dois anos. Um teste para as três etapas, porque é a combinação delas que
  importa.
- `test_escopo_recente_nao_reporta_os_anos_fora_do_escopo_como_desatualizados` — sob `recente`, o ano
  antigo intocado **não** sai em `anos_desatualizados`; sob `completo`, o critério da 008 continua
  valendo. É a borda que impede o relatório noturno de acusar vinte anos toda noite.

Os testes multi-ano da 008 (`test_ano_despublicado_ou_nao_baixado_continua_no_parquet`,
`test_run_sobrescreve_sem_acumular`, `test_ano_publicado_e_nao_baixado_sai_em_anos_ausentes`) passam
a declarar `escopo=completo`. **O comportamento que cada um fixa não muda** — o que era default
virou explícito.

## Patches

_Nenhum patch registrado até o momento._
