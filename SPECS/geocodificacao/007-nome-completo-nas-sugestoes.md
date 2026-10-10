---
spec: geocodificacao/007
versao: v3
atualizado_em: 2026-10-02
testes_tdd: true
implementado: true
changelog:
  - v1: versão inicial
  - v2: renumerada de 008 para 007 — vem antes do endereço mais próximo do ponto, que passa a ser a 008.
  - v3: a busca por nome compara também a denominação, com o título abreviado e por extenso — pelo dicionário de títulos, que a carga leva ao catálogo em parquet —, e o nome passa a ser comparado por Levenshtein.
---

# SPEC geocodificacao/007 — Nome completo do logradouro na busca e nas sugestões

## 1 · User story
Quem usa a busca digita o logradouro como o conhece — com o título abreviado, por extenso ou sem ele —
e o reconhece, na lista de sugestões que aparece a cada tecla, pelo nome completo que a gaveta mostra
depois de aberta.

## 2 · Condições de pronto
- [ ] As sugestões de logradouro e de endereço, por nome e por codlog, mostram o nome completo do
      logradouro — `AV BRIG LUIS ANTONIO`, `R DA CONSOLACAO` —, o mesmo que a gaveta aberta pela
      sugestão mostra.
- [ ] A busca encontra pelo nome completo, com o título abreviado ou por extenso: `avenida brigadeiro
      faria lima` e `av brig faria lima` trazem a `AV BRIG FARIA LIMA`, `praca nossa senhora aparecida`
      traz a `PC NSRA APARECIDA`, e `rua da consolacao` traz a `R DA CONSOLACAO`.
- [ ] A busca encontra pelos mesmos textos de hoje: `luis antonio` traz a `AV BRIG LUIS ANTONIO`.
- [ ] A busca aproximada não sugere logradouro só por começar parecido: `rua da consolasao` traz a
      `R DA CONSOLACAO`, e não a `R DA COROA`.
- [ ] A carga dos nomes de logradouros, manual ou a diária, grava título e preposição no catálogo.
- [ ] A carga dos títulos, manual ou a diária, regrava o dicionário de títulos no catálogo e avisa a
      sigla da camada que ele não traduz.

## 3 · Domínio
O logradouro é a entidade da [SPEC 006](006-gaveta-do-logradouro.md), dona da única regra do nome.
Esta SPEC a leva aos catálogos de identificação — o matcher por nome e o matcher por codlog —, que
passam a saber título e preposição. A pergunta que ela faz à entidade é "como você se chama?".

O dicionário de títulos traduz a sigla do cadastro para o extenso (`BRIG` → `Brigadeiro`). É mantido
à mão em `data/traducao_codigos_titulos_logradouro.json` (§6), e a carga o leva ao catálogo em
`data/titulos_logradouro_cache.parquet`, com o extenso normalizado. Sigla fora dele não tem extenso.

**`services/scripts/logradouros/models.py`** — `LogradouroNome` inteiro, com o que muda marcado.

```python
class LogradouroNome(BaseModel):
    codlog: str
    tipo_logradouro: str
    titulo: str | None = None       # NOVO nesta SPEC: cd_titulo_logradouro. None = sem título.
    preposicao: str | None = None   # NOVO nesta SPEC: tx_preposicao_logradouro. None = sem preposição.
    nm_logradouro: str
```

**`services/domain/logradouros_match/models.py`** — `LogradouroRow` e `LogradouroMatchOutput`
inteiros, com o que muda marcado.

```python
class LogradouroRow(BaseModel):
    codlog: str                             # 5 dígitos, sem o DV
    dv: str
    tipo_logradouro: str
    titulo: str | None = None               # NOVO nesta SPEC: a sigla do cadastro — BRIG
    titulo_por_extenso: str | None = None   # NOVO nesta SPEC: BRIGADEIRO, do dicionário. None = sigla fora dele.
    preposicao: str | None = None           # NOVO nesta SPEC
    nm_logradouro: str                      # o nome sem título nem preposição

    # NOVO nesta SPEC: a entidade da SPEC 006, dona do nome.
    @property
    def logradouro(self) -> Logradouro:
        return Logradouro(
            codlog=f"{self.codlog}{self.dv}",
            tipo_logradouro=self.tipo_logradouro,
            titulo=self.titulo,
            preposicao=self.preposicao,
            nome_logradouro=self.nm_logradouro,
        )

    # NOVO nesta SPEC: o que a busca compara — FARIA LIMA, BRIG FARIA LIMA e BRIGADEIRO FARIA LIMA.
    # Repetidos saem: sem título, é um texto só. Memoizado: o literal percorre o catálogo a cada tecla.
    @cached_property
    def textos_de_busca(self) -> tuple[str, ...]:
        logradouro = self.logradouro
        por_extenso = logradouro.model_copy(update={"titulo": self.titulo_por_extenso or self.titulo})
        return tuple(
            dict.fromkeys((self.nm_logradouro, logradouro.denominacao, por_extenso.denominacao))
        )


class LogradouroMatchOutput(BaseModel):
    codlog: str
    dv: str
    tipo_codigo: str
    titulo: str | None = None       # NOVO nesta SPEC
    preposicao: str | None = None   # NOVO nesta SPEC
    nome_logradouro: str

    # NOVO nesta SPEC: a entidade da SPEC 006, dona do nome.
    @property
    def logradouro(self) -> Logradouro:
        return Logradouro(
            codlog=f"{self.codlog}{self.dv}",
            tipo_logradouro=self.tipo_codigo,
            titulo=self.titulo,
            preposicao=self.preposicao,
            nome_logradouro=self.nome_logradouro,
        )
```

**`services/domain/codlog_match/models.py`** — `CodlogMatchOutput` inteiro, com o que muda marcado.

```python
class CodlogMatchOutput(BaseModel):
    codlog: str
    dv: str
    tipo_logradouro: str
    titulo: str | None = None       # NOVO nesta SPEC
    preposicao: str | None = None   # NOVO nesta SPEC
    nome_logradouro: str

    # NOVO nesta SPEC: a entidade da SPEC 006, dona do nome.
    @property
    def logradouro(self) -> Logradouro:
        return Logradouro(
            codlog=f"{self.codlog}{self.dv}",
            tipo_logradouro=self.tipo_logradouro,
            titulo=self.titulo,
            preposicao=self.preposicao,
            nome_logradouro=self.nome_logradouro,
        )

    # REMOVIDO nesta SPEC: `nome_completo`, que juntava só tipo e nome.
```

**Sem mock.** Esta SPEC não tem mock: as sugestões trocam só o texto do nome, nas peças que já
existem (§7).

## 4 · Fora de escopo
- Os matchers devolverem o próprio `Logradouro`, com o codlog de 6 dígitos — sem dono ainda.
- Título por extenso na exibição — `AV BRIGADEIRO FARIA LIMA` na sugestão e na gaveta — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/logradouro` → `Logradouro.denominacao`: a regra única do nome ([SPEC 006](006-gaveta-do-logradouro.md)).
- `@services/utils/fuzzy_matcher` → `fuzzy_match(..., algorithm="levenshtein")`: a comparação aproximada.
- `@services/scripts/augment_tipos_logradouro` → `check_dados_input_consistentes`, `run`, e o comando `augment_logradouro_types`: o desenho da carga de títulos — JSON mantido à mão, parquet de cache, aviso do que o dicionário não cobre.
- `@services/utils/normalization` → `normalize_text`: o extenso na forma que a busca compara.
- `@services/utils/io` → `read_json_from_data`, `read_parquet_from_data`, `write_parquet_to_data`: a leitura do dicionário e a escrita do cache.
- `@services/domain/logradouro_geocod/geocoder.py` → `_montar_attributes`: as chaves `cd_titulo_logradouro` e `tx_preposicao_logradouro` da camada.
- `@apps/logradouro_matcher/management/commands/extrair_nomes_logradouros.py`: a carga que regrava o catálogo de nomes.
- `@tests/services/scripts/logradouros/test_extractor.py` → `_page`, `_req`: o extrator com fetcher fake.
- Skills: `management-commands`, `catalogos-lookup`, `fuzzy-matcher`, `normalize-text`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/scripts/logradouros/extractor.py`** — a carga pede título e preposição à camada e os
leva na chave de deduplicação.

```python
PROPERTY_NAMES: list[str] = [
    "codlog",
    "cd_tipo_logradouro",
    "cd_titulo_logradouro",       # NOVO
    "tx_preposicao_logradouro",   # NOVO
    "nm_logradouro",
]


def _opcional(value: object) -> str | None:
    # Diferente do `_as_str`: ausência é None, não "" — é o que o `Logradouro` espera. A camada
    # manda título e preposição em branco em algumas linhas; em branco também é ausência.
    texto = "" if value is None else str(value).strip()
    return texto or None


# no laço das páginas
seen.add((
    str(codlog),
    _as_str(props.get("cd_tipo_logradouro")),
    _opcional(props.get("cd_titulo_logradouro")),
    _opcional(props.get("tx_preposicao_logradouro")),
    _as_str(props.get("nm_logradouro")),
))
```

**`services/scripts/logradouros/runner.py`** — o parquet ganha as duas colunas, com os nomes da camada.

```python
def _to_columns(rows: list[LogradouroNome]) -> dict[str, list[str | None]]:
    return {
        "codlog": [r.codlog for r in rows],
        "cd_tipo_logradouro": [r.tipo_logradouro for r in rows],
        "cd_titulo_logradouro": [r.titulo for r in rows],          # NOVO
        "tx_preposicao_logradouro": [r.preposicao for r in rows],  # NOVO
        "nm_logradouro": [r.nm_logradouro for r in rows],
    }
```

**`data/traducao_codigos_titulos_logradouro.json`** — sigla → extenso, mantido à mão; uma entrada por
linha no arquivo (aqui agrupadas para a leitura). Cobre 160 das 178 siglas da camada: as de extenso
certo e as que já são a palavra (`DOM` → `Dom`), estas para o aviso da carga apontar só sigla de fato
não traduzida.

```json
{
  "ABADE": "Abade", "AGRIC": "Agricultor", "AGRIM": "Agrimensor", "ALF": "Alferes",
  "ALM": "Almirante", "APOST": "Apóstolo", "ARCIP": "Arcipreste", "ARCJO": "Arcanjo",
  "ARQ": "Arquiteto", "ARQA": "Arquiteta", "ASP": "Aspirante", "AVI": "Aviador",
  "AVIA": "Aviadora",
  "BAND": "Bandeirante", "BEATO": "Beato", "BEL": "Bacharel", "BEMAV": "Bem-Aventurado",
  "BEPDE": "Beato Padre", "BISP": "Bispo", "BR": "Barão", "BRA": "Baronesa", "BRIG": "Brigadeiro",
  "CABO": "Cabo", "CABPM": "Cabo PM", "CAD": "Cadete", "CAP": "Capitão", "CAPPM": "Capitão PM",
  "CARD": "Cardeal", "CAVLH": "Cavalheiro", "CD": "Conde", "CDSSA": "Condessa", "CEL": "Coronel",
  "CELPM": "Coronel PM", "CIN": "Cineasta", "COMED": "Comediante", "COMEN": "Comendador",
  "COMIS": "Comissário", "COMP": "Compositor", "COMTE": "Comandante", "CON": "Cônego",
  "CONS": "Conselheiro", "CONSU": "Cônsul",
  "DEL": "Delegado", "DENT": "Dentista", "DEP": "Deputado", "DEPA": "Deputada",
  "DEPDR": "Deputado Doutor", "DESEM": "Desembargador", "DIACO": "Diácono", "DOM": "Dom",
  "DONA": "Dona", "DR": "Doutor", "DRA": "Doutora", "DUQ": "Duque", "DUQSA": "Duquesa",
  "EDIT": "Editor", "EDUC": "Educador", "EDUCA": "Educadora", "EMB": "Embaixador",
  "EMBA": "Embaixadora", "ENG": "Engenheiro", "ENGA": "Engenheira", "ESCOT": "Escoteiro",
  "ESCR": "Escritor", "EXP": "Expedicionário",
  "FREI": "Frei",
  "GAL": "General", "GCM": "Guarda Civil Metropolitano", "GOV": "Governador", "GRUM": "Grumete",
  "IMAC": "Imaculada", "IMP": "Imperatriz", "INSP": "Inspetor", "IRMA": "Irmã", "IRMAO": "Irmão",
  "IRMAS": "Irmãs",
  "JORN": "Jornalista",
  "LIB": "Libertador", "LIDCO": "Líder Comunitário", "LIVR": "Livreiro", "LORD": "Lord",
  "MADRE": "Madre", "MAEST": "Maestro", "MAJ": "Major", "MAL": "Marechal",
  "MALAR": "Marechal do Ar", "MAQ": "Maquinista", "MARQ": "Marquês", "MARQA": "Marquesa",
  "MERE": "Mère", "MEST": "Mestre", "MIN": "Ministro", "MISSA": "Missionária",
  "MJAVI": "Major-Aviador", "MJBRI": "Major-Brigadeiro", "MME": "Madame", "MONGE": "Monge",
  "MONS": "Monsenhor", "MTRAS": "Mestras", "MUS": "Músico",
  "NSRA": "Nossa Senhora",
  "OUVID": "Ouvidor",
  "PAI": "Pai", "PAPA": "Papa", "PAST": "Pastor", "PDE": "Padre", "PDES": "Padres",
  "POETA": "Poeta", "POTSA": "Poetisa", "PREF": "Prefeito", "PRES": "Presidente",
  "PRINC": "Príncipe", "PRODR": "Professor Doutor", "PROF": "Professor", "PROFA": "Professora",
  "PROM": "Promotor", "PROTA": "Profeta", "PRSA": "Princesa", "PSARG": "Primeiro-Sargento",
  "PSGPM": "Primeiro-Sargento PM", "PSTRA": "Pastora", "PTTE": "Primeiro-Tenente",
  "RAB": "Rabino", "RADTA": "Radialista", "RAINH": "Rainha", "REG": "Regente", "REI": "Rei",
  "REV": "Reverendo",
  "S": "São", "SARG": "Sargento", "SARGM": "Sargento-Mor", "SBTTE": "Subtenente",
  "SDPM": "Soldado PM", "SEN": "Senador", "SEU": "Seu", "SGPM": "Sargento PM", "SIR": "Sir",
  "SOCIO": "Sociólogo", "SOLD": "Soldado", "SOROR": "Soror", "SR": "Senhor", "SRA": "Senhora",
  "SSARG": "Segundo-Sargento", "SSGPM": "Segundo-Sargento PM", "STA": "Santa", "STO": "Santo",
  "TEO": "Teólogo", "TIA": "Tia", "TSARG": "Terceiro-Sargento", "TSGPM": "Terceiro-Sargento PM",
  "TTAVI": "Tenente-Aviador", "TTBRI": "Tenente-Brigadeiro", "TTCEL": "Tenente-Coronel",
  "TTCPM": "Tenente-Coronel PM", "TTE": "Tenente",
  "VER": "Vereador", "VIG": "Vigário", "VISC": "Visconde", "VISCA": "Viscondessa",
  "VOL": "Voluntário"
}
```

**`services/scripts/traducao_titulos_logradouro/`** — a carga do dicionário, no desenho do
`augment_tipos_logradouro`: `constants.py`, `models.py`, o pipeline e o `runner.py` com o contrato
`ScriptRunner`. Não gera variação de digitação: o fuzzy já a cobre no nome inteiro.

```python
# constants.py
TRADUCAO_TITULOS_MANUAL = "traducao_codigos_titulos_logradouro.json"
PARQUET_NOMES_LOGRADOURO_BASE_ORIGINAL = "nomes_logradouros.parquet"
OUTPUT_PARQUET_NAME = "titulos_logradouro_cache.parquet"


# models.py
class TraducaoTitulosConfig(BaseModel):
    input_json_name: str = TRADUCAO_TITULOS_MANUAL
    input_parquet_name: str = PARQUET_NOMES_LOGRADOURO_BASE_ORIGINAL
    output_parquet_name: str = OUTPUT_PARQUET_NAME


class TraducaoTitulosStats(BaseModel):
    n_titulos: int
    siglas_sem_extenso: list[str] = []   # o que a camada usa e o dicionário não traduz


# traducao_titulos_logradouro.py
COL_SIGLA = "cd_titulo_logradouro"
COL_EXTENSO = "nome_titulo"


def siglas_sem_extenso(dicionario: dict[str, str], input_parquet_name: str) -> list[str]:
    # o mesmo papel do `check_dados_input_consistentes` dos tipos
    parquet = read_parquet_from_data(input_parquet_name)
    siglas_da_camada = {str(sigla) for sigla in parquet[COL_SIGLA] if sigla}
    return sorted(siglas_da_camada - set(dicionario))


def pipeline(config: TraducaoTitulosConfig) -> TraducaoTitulosStats:
    dicionario = cast(dict[str, str], read_json_from_data(config.input_json_name))
    sem_extenso = siglas_sem_extenso(dicionario, config.input_parquet_name)
    siglas = list(dicionario)
    # normalizado aqui, uma vez: o literal compara contra a consulta normalizada, e `Cônego`
    # precisa chegar ao catálogo como `CONEGO`
    extensos = [normalize_text(extenso) for extenso in dicionario.values()]
    write_parquet_to_data({COL_SIGLA: siglas, COL_EXTENSO: extensos}, config.output_parquet_name)
    return TraducaoTitulosStats(n_titulos=len(siglas), siglas_sem_extenso=sem_extenso)


# runner.py — `verbose` entra pelo contrato; não há o que detalhar além do aviso
def run(
    config: TraducaoTitulosConfig,
    *,
    verbose: bool = False,
    manual: bool = True,
) -> TraducaoTitulosStats:
    with registrar_execucao(config.output_parquet_name, manual=manual) as registro:
        stats = pipeline(config)
        registro.sucesso(registros=stats.n_titulos)
    return stats


_contrato: ScriptRunner[TraducaoTitulosConfig, TraducaoTitulosStats] = run
```

**`apps/logradouro_matcher/management/commands/traduzir_titulos_logradouro.py`** — comando fino, como
o `augment_logradouro_types`: parsing, `run` e o aviso de cada sigla sem extenso.

```python
def handle(self, *args: object, **options: object) -> None:
    config = TraducaoTitulosConfig()
    stats = run(
        config,
        verbose=bool(options["verbose"]),
        manual=not options["automatico"],
    )
    for sigla in stats.siglas_sem_extenso:
        self.stdout.write(
            self.style.WARNING(
                f"AVISO: título '{sigla}' presente em nomes_logradouros.parquet "
                f"mas ausente no dicionário de títulos."
            )
        )
    self.stdout.write(self.style.SUCCESS(f"Concluído. Títulos no parquet: {stats.n_titulos}"))
```

**`apps/core/management/commands/atualizar_dados.py`** — a etapa nova entra na fase de variações,
depois da carga de nomes que ela confere.

```python
ETAPAS: tuple[str, ...] = (
    "extrair_segmentos_logradouros",
    "extrair_nomes_logradouros",
    "extrair_enderecos_fiscais",
    "augment_logradouro_types",
    "traduzir_titulos_logradouro",   # NOVO
    "extrair_guias_itbi",
)
```

Na entrega, `extrair_nomes_logradouros` e depois `traduzir_titulos_logradouro` rodam uma vez, os dois
parquets regravados entram no diff e o processo web é reiniciado para os catálogos lerem os parquets
novos.

**`services/domain/logradouros_match/catalog.py`** — a linha lê as colunas novas e o extenso do
título, e o catálogo passa a responder por texto de busca em vez de por nome.

```python
TITULOS_CACHE_FILE = "titulos_logradouro_cache.parquet"   # NOVO


# NOVO: o mesmo desenho do `_variacoes` — o parquet de cache da carga, sob o TTL do catálogo.
@ttl_cached_property(ttl_seconds=DATA_TTL_SECONDS)
def _titulos_por_extenso(self) -> dict[str, str]:
    cols = read_parquet_from_data(TITULOS_CACHE_FILE)
    siglas = cast(list[str], cols["cd_titulo_logradouro"])
    extensos = cast(list[str], cols["nome_titulo"])
    return dict(zip(siglas, extensos))


@ttl_cached_property(ttl_seconds=DATA_TTL_SECONDS)
def _rows(self) -> list[LogradouroRow]:
    cols = read_parquet_from_data(NOMES_LOGRADOUROS_FILE)
    codlogs = cast(list[str], cols["codlog"])
    tipos = cast(list[str], cols["cd_tipo_logradouro"])
    titulos = cast(list[str | None], cols["cd_titulo_logradouro"])            # NOVO
    preposicoes = cast(list[str | None], cols["tx_preposicao_logradouro"])    # NOVO
    nomes = cast(list[str], cols["nm_logradouro"])
    por_extenso = self._titulos_por_extenso                                   # NOVO
    return [
        LogradouroRow(
            codlog=c[:5],
            dv=c[5],
            tipo_logradouro=t,
            titulo=ti,
            titulo_por_extenso=por_extenso.get(ti) if ti else None,
            preposicao=p,
            nm_logradouro=n,
        )
        for c, t, ti, p, n in zip(codlogs, tipos, titulos, preposicoes, nomes)
    ]


# NOVO: cada linha entra no índice por cada um dos seus textos. Aquecido no `aquecer`, o que
# memoiza o `textos_de_busca` de todas as linhas antes da primeira busca.
@ttl_cached_property(ttl_seconds=DATA_TTL_SECONDS)
def _por_texto(self) -> dict[str, list[LogradouroRow]]:
    indice: dict[str, list[LogradouroRow]] = {}
    for row in self._rows:
        for texto in row.textos_de_busca:
            indice.setdefault(texto, []).append(row)
    return indice


# NOVO: os choices do fuzzy, sem repetição — homônimos dividem o texto e não ocupam duas posições
# do ranking.
def textos_de_busca(self, codigo: str | None) -> list[str]:
    universo = self.linhas_do_tipo(codigo) if codigo else self._rows
    return list(dict.fromkeys(texto for row in universo for texto in row.textos_de_busca))


# SUBSTITUI `linhas_por_nome`: o texto casado pode ser o nome, a denominação ou ela por extenso.
def linhas_por_texto(self, texto: str, codigo: str | None) -> list[LogradouroRow]:
    linhas = self._por_texto.get(texto, [])
    return [row for row in linhas if codigo is None or row.tipo_logradouro == codigo]
```

**`services/domain/logradouros_match/models.py`** — a conversão da linha na saída passa a existir num
lugar só; o resolver, o matcher literal e o fuzzy a chamam, em vez de montar a saída cada um.

```python
class LogradouroMatchOutput(BaseModel):
    ...

    # NOVO: a única montagem da saída a partir da linha do catálogo.
    @classmethod
    def da_linha(cls, row: LogradouroRow) -> Self:
        return cls(
            codlog=row.codlog,
            dv=row.dv,
            tipo_codigo=row.tipo_logradouro,
            titulo=row.titulo,
            preposicao=row.preposicao,
            nome_logradouro=row.nm_logradouro,
        )
```

**`services/domain/logradouros_match/literal_matcher.py`** — prefixo e trecho valem contra qualquer um
dos textos. A ordem continua a do catálogo.

```python
def _match_nome(self, nome: str, codigo: str | None) -> list[LogradouroRow]:
    universo = (
        self._catalog.linhas_do_tipo(codigo) if codigo else self._catalog.todas_as_linhas()
    )
    # `faria lima` casa o prefixo do nome; `brig faria lima`, o da denominação;
    # `brigadeiro faria lima`, o da denominação por extenso.
    prefixo = [
        row for row in universo
        if any(texto.startswith(nome) for texto in row.textos_de_busca)
    ]
    if prefixo:
        return prefixo
    return [row for row in universo if any(nome in texto for texto in row.textos_de_busca)]


# no _build
logradouros = [LogradouroMatchOutput.da_linha(row) for row in rows[:limite]]
```

**`services/domain/logradouros_match/matcher.py`** — o nome é comparado por Levenshtein, como o tipo
já é, contra os textos de busca.

```python
# Uma linha ocupa até três textos no ranking: pedir o triplo garante `limite` linhas distintas.
TEXTOS_POR_LINHA = 3


def _match_nome(
    self,
    nome_token: str,
    codigo: str | None,
    limite: int,
) -> tuple[FuzzyMatchResult, bool]:
    choices = self._catalog.textos_de_busca(codigo) if codigo else []
    if not choices:
        return self._match_nome_global(nome_token, limite), codigo is not None
    resultado = fuzzy_match(
        nome_token,
        choices,
        limit=limite * TEXTOS_POR_LINHA,
        algorithm="levenshtein",   # ALTERADO: era jaro_winkler
    )
    if resultado.best_match is None or resultado.best_match.similarity_score < self._threshold:
        return self._match_nome_global(nome_token, limite), codigo is not None
    return resultado, False


def _match_nome_global(self, nome_token: str, limite: int) -> FuzzyMatchResult:
    return fuzzy_match(
        nome_token,
        self._catalog.textos_de_busca(None),
        limit=limite * TEXTOS_POR_LINHA,
        algorithm="levenshtein",   # ALTERADO: era jaro_winkler
    )


# no _build_result
rows = self._catalog.linhas_por_texto(melhor.original_string, filtro) if melhor else []
logradouros = [LogradouroMatchOutput.da_linha(row) for row in rows]
```

**`services/domain/logradouros_match/resolver.py`** — a mesma linha pode chegar por mais de um texto;
fica a primeira, que é a de maior score. `_to_output` sai.

```python
def _itens_do_fuzzy(
    self,
    resultado: LogradouroMatchResult,
    limite: int,
) -> list[ResolucaoLogradouroItem]:
    filtro = None if resultado.ignorou_filtro_tipo else self._codigo_do_tipo(resultado)
    aceitos = [m for m in resultado.match_nome.matches if m.similarity_score >= self._threshold]
    itens: list[ResolucaoLogradouroItem] = []
    vistas: set[int] = set()
    for match in aceitos:
        for row in self._catalog.linhas_por_texto(match.original_string, filtro):
            # as linhas são as instâncias do catálogo: identidade basta para deduplicar
            if id(row) in vistas:
                continue
            vistas.add(id(row))
            itens.append(
                ResolucaoLogradouroItem(
                    logradouro=LogradouroMatchOutput.da_linha(row),
                    score=match.similarity_score,
                )
            )
    return itens[:limite]
```

**`services/domain/codlog_match/matcher.py`** — o matcher por codlog lê as mesmas colunas.

```python
CodlogMatchOutput(
    codlog=str(linha["codlog"])[:5],
    dv=str(linha["codlog"])[5],
    tipo_logradouro=str(linha["cd_tipo_logradouro"]),
    titulo=linha["cd_titulo_logradouro"],           # NOVO: sem str(), que transformaria None em "None"
    preposicao=linha["tx_preposicao_logradouro"],   # NOVO
    nome_logradouro=str(linha["nm_logradouro"]),
)
```

**Templates de sugestão** — as quatro listas leem o nome da entidade. O `if` que protegia o tipo vazio
sai: a entidade já trata.

```html
{# logradouro_matcher/partials/resultados_codlog.html #}
<span class="font-medium">{{ r.logradouro.nome_completo }}</span>

{# address_geocoder/partials/resultados_endereco_codlog.html #}
<span class="font-medium">{{ r.logradouro.nome_completo }}, {{ numero }}</span>
```

Nas listas por nome, o item já se chama `logradouro`; um apelido dentro do loop evita o
`item.logradouro.logradouro`, como o `{% with %}` da gaveta do lote.

```html
{# logradouro_matcher/partials/resultados_logradouro.html #}
{% for item in resultado.itens %}
  {% with logradouro=item.logradouro.logradouro %}
    <li class="suggestion-item items-baseline gap-4" ...>
      ...
      <span class="font-medium">{{ logradouro.nome_completo }}</span>
      ...
    </li>
  {% endwith %}
{% endfor %}

{# address_geocoder/partials/resultados_endereco_nome.html — o mesmo apelido #}
<span class="font-medium">{{ logradouro.nome_completo }}, {{ numero }}</span>
```

## 7 · Caveats
Esta SPEC não tem mock. A interface não ganha peça nem muda de layout: as quatro listas de sugestão
trocam só o texto do nome, nas peças que já existem. O custo é a conferência do nome mais longo na
linha da sugestão ficar com o usuário, na tela, depois da entrega.

A linha do catálogo e as saídas dos matchers mantêm a identidade em campos soltos, com o codlog de 5
dígitos e o DV à parte, e entregam o `Logradouro` por um atributo derivado. Devolver o próprio
`Logradouro` mudaria o formato do codlog que a busca, o endereço do lote e os templates de sugestão
consomem. O custo é a identidade do logradouro existir em mais três tipos, cada um com o seu ponto de
montagem.

A extração deduplica por codlog, tipo, título, preposição e nome. A camada é a fonte, e escolher uma
das grafias de um codlog seria decidir por ela. O custo é a sugestão repetida para o codlog cujos
segmentos divergem, como acontece com 4 codlogs na camada atual.

As cargas dos nomes e dos títulos rodam na entrega, e os parquets regravados vão no mesmo diff do
código. O catálogo lê as colunas novas e o cache de títulos sem alternativa para o parquet antigo, e o
parquet de `data/` é versionado com o código. O custo é o diff da entrega trazer o catálogo de nomes
inteiro regravado.

O catálogo de logradouros passa a depender do cache de títulos para montar suas linhas. É o mesmo
desenho do cache de tipos, que ele já lê. O custo é o cache de títulos ausente derrubar a carga do
catálogo inteiro, e não só o extenso.

A busca compara cada logradouro por até três textos: o nome sozinho, a denominação com a sigla e a
denominação por extenso. O primeiro mantém achável quem digita como hoje, e os outros acham quem digita
o nome oficial, abreviado ou não. O custo é o fuzzy percorrer cerca de 62 mil textos por tecla em vez
de 51 mil, e a mesma linha poder ocupar três posições do ranking, o que obriga o matcher a pedir o
triplo de textos e o resolver a deduplicar.

O nome passa a ser comparado por Levenshtein — o `fuzz.ratio` do `fuzzy_matcher`, em que trocar uma
letra custa o dobro de inserir —, e o corte de 80 se mantém. O Jaro-Winkler premia o começo comum e
aceita acima do corte o que só começa igual: `DA COROA` com 88 para `da consolasao`, `BRIG FARIA LIMA`
com 88 para `brigadeiro luiz antonio`. O custo é o Levenshtein ser mais severo com dois erros num nome
curto: `rebolsas` dá 75 contra a `REBOUCAS` e deixa de ser sugerida.

O dicionário de títulos é mantido à mão e cobre só as siglas de extenso certo. A camada não traz o
extenso, e um extenso chutado faria a busca casar com o título errado. O custo é a sigla incerta, ou
nova na camada, ficar sem extenso até alguém traduzi-la — o logradouro segue achado pela sigla e pelo
nome — e a carga diária repetir o aviso das 18 siglas incertas de hoje até lá.

## 8 · Testes (TDD)
- `test_extracao_de_nomes_traz_titulo_e_preposicao` — feature com `cd_titulo_logradouro` `BRIG` e
  preposição em branco vira linha com título `BRIG` e preposição `None`.
- `test_traducao_de_titulos_normaliza_e_avisa_sigla_sem_extenso` — sobre dicionário e parquet de nomes
  sintéticos, o cache traz `CON` → `CONEGO`, e a sigla da camada ausente do dicionário sai em
  `siglas_sem_extenso`.
- `test_catalogo_acha_a_linha_pelo_titulo_por_extenso` — sobre os parquets sintéticos de nomes e de
  títulos, a linha `AV` / `BRIG` / `LUIS ANTONIO` é achada por `LUIS ANTONIO`, `BRIG LUIS ANTONIO` e
  `BRIGADEIRO LUIS ANTONIO`; a de sigla fora do dicionário, só pelo nome e pela sigla.
- `test_resolver_acha_pelo_nome_curto_e_pelo_completo` — sobre essa linha, `luis antonio`,
  `brig luis antonio`, `brigadeiro luis antonio` e `brigadero luiz antonio` a acham, e a saída diz
  `AV BRIG LUIS ANTONIO`.
- `test_busca_aproximada_nao_sugere_pelo_comeco_parecido` — sobre um catálogo com `R DA CONSOLACAO` e
  `R DA COROA`, `rua da consolasao` traz só a `R DA CONSOLACAO`.
- `test_busca_aproximada_lista_cada_logradouro_uma_vez` — `brigadero luiz antonio`, que casa com a
  denominação e com ela por extenso, traz a `AV BRIG LUIS ANTONIO` uma vez; dois homônimos `R AURORA`
  aparecem uma vez cada.
- `test_sugestoes_mostram_o_nome_completo_do_logradouro` — as quatro seções de sugestão (logradouro e
  endereço, por nome e por codlog), sobre catálogos com essa linha, renderizam `AV BRIG LUIS ANTONIO`.
- O logradouro sem tipo do catálogo é coberto pelo `test_nome_completo_do_logradouro_junta_titulo_e_preposicao`
  da SPEC 006.
