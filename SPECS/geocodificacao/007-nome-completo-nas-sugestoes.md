---
spec: geocodificacao/007
versao: v2
atualizado_em: 2026-10-02
testes_tdd: false
implementado: false
changelog:
  - v1: versão inicial
  - v2: renumerada de 008 para 007 — vem antes do endereço mais próximo do ponto, que passa a ser a 008.
---

# SPEC geocodificacao/007 — Nome completo do logradouro nas sugestões

## 1 · User story
Quem usa a busca escolhe um logradouro ou um endereço no contexto da lista de sugestões que aparece a
cada tecla para reconhecê-lo pelo nome completo, o mesmo que a gaveta mostra depois de aberta.

## 2 · Condições de pronto
- [ ] As sugestões de logradouro e de endereço, por nome e por codlog, mostram o nome completo do
      logradouro — `AV BRIG LUIS ANTONIO`, `R DA CONSOLACAO` —, o mesmo que a gaveta aberta pela
      sugestão mostra.
- [ ] A busca encontra pelos mesmos textos de hoje: `luis antonio` traz a `AV BRIG LUIS ANTONIO`.
- [ ] A carga dos nomes de logradouros, manual ou a diária, grava título e preposição no catálogo.

## 3 · Domínio
O logradouro é a entidade da [SPEC 006](006-gaveta-do-logradouro.md), dona da única regra do nome.
Esta SPEC a leva aos catálogos de identificação — o matcher por nome e o matcher por codlog —, que
passam a saber título e preposição. A pergunta que ela faz à entidade é "como você se chama?".

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
    codlog: str                     # 5 dígitos, sem o DV
    dv: str
    tipo_logradouro: str
    titulo: str | None = None       # NOVO nesta SPEC
    preposicao: str | None = None   # NOVO nesta SPEC
    nm_logradouro: str              # o texto que a busca compara: sem título nem preposição


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
- Busca pelo título ou pela preposição: o `BRIG` digitado casar com o título — sem dono ainda.
- Os matchers devolverem o próprio `Logradouro`, com o codlog de 6 dígitos — sem dono ainda.
- Título por extenso (`BRIG` → "Brigadeiro") — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/logradouro` → `Logradouro`: a regra única do nome ([SPEC 006](006-gaveta-do-logradouro.md)).
- `@services/domain/logradouro_geocod/geocoder.py` → `_montar_attributes`: as chaves `cd_titulo_logradouro` e `tx_preposicao_logradouro` da camada.
- `@apps/logradouro_matcher/management/commands/extrair_nomes_logradouros.py`: a carga que regrava o catálogo de nomes.
- `@tests/services/scripts/logradouros/test_extractor.py` → `_page`, `_req`: o extrator com fetcher fake.
- Skills: `management-commands`, `catalogos-lookup`, `escrever-testes`, `test-django-views`.

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
    # Diferente do `_as_str`: ausência é None, não "" — é o que o `Logradouro` espera.
    return None if value is None else str(value)


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

Na entrega, `extrair_nomes_logradouros` roda uma vez, o `data/nomes_logradouros.parquet` regravado
entra no diff e o processo web é reiniciado para os catálogos lerem o parquet novo.

**`services/domain/logradouros_match/catalog.py`** — a linha do catálogo lê as colunas novas.

```python
@ttl_cached_property(ttl_seconds=DATA_TTL_SECONDS)
def _rows(self) -> list[LogradouroRow]:
    cols = read_parquet_from_data(NOMES_LOGRADOUROS_FILE)
    codlogs = cast(list[str], cols["codlog"])
    tipos = cast(list[str], cols["cd_tipo_logradouro"])
    titulos = cast(list[str | None], cols["cd_titulo_logradouro"])            # NOVO
    preposicoes = cast(list[str | None], cols["tx_preposicao_logradouro"])    # NOVO
    nomes = cast(list[str], cols["nm_logradouro"])
    return [
        LogradouroRow(
            codlog=c[:5],
            dv=c[5],
            tipo_logradouro=t,
            titulo=ti,
            preposicao=p,
            nm_logradouro=n,
        )
        for c, t, ti, p, n in zip(codlogs, tipos, titulos, preposicoes, nomes)
    ]
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


# resolver.py (`_to_output` sai), literal_matcher.py e matcher.py
logradouros = [LogradouroMatchOutput.da_linha(row) for row in rows]
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

As saídas dos matchers mantêm a identidade em campos soltos, com o codlog de 5 dígitos e o DV à
parte, e entregam o `Logradouro` por um atributo derivado. Devolver o próprio `Logradouro` mudaria o
formato do codlog que a busca, o endereço do lote e os templates de sugestão consomem. O custo é a
identidade do logradouro existir em mais dois tipos, cada um com o seu ponto de montagem.

A extração deduplica por codlog, tipo, título, preposição e nome. A camada é a fonte, e escolher uma
das grafias de um codlog seria decidir por ela. O custo é a sugestão repetida para o codlog cujos
segmentos divergem, como já acontece hoje com grafias diferentes do nome (3 codlogs no catálogo
atual).

A carga dos nomes roda na entrega, e o parquet regravado vai no mesmo diff do código. O catálogo lê as
colunas novas sem alternativa para o parquet antigo, e o parquet de `data/` é versionado com o código.
O custo é o diff da entrega trazer o catálogo de nomes inteiro regravado.

Título e preposição entram no nome exibido, não no texto que a busca compara. Levá-los à comparação
mexe no literal, no fuzzy e nas variações, e é outra iteração (§4). O custo é o título digitado na
busca não ajudar a achar o logradouro.

## 8 · Testes (TDD)
- `test_extracao_de_nomes_traz_titulo_e_preposicao` — feature com `cd_titulo_logradouro` `BRIG` e sem
  preposição vira linha com título `BRIG` e preposição `None`.
- `test_resolver_acha_pelo_nome_e_entrega_o_nome_completo` — sobre um catálogo com a linha `AV` /
  título `BRIG` / `LUIS ANTONIO`, a busca literal e a aproximada pelo nome acham a linha, e a saída diz
  `AV BRIG LUIS ANTONIO`.
- `test_sugestoes_mostram_o_nome_completo_do_logradouro` — as quatro seções de sugestão (logradouro e
  endereço, por nome e por codlog), sobre catálogos com essa linha, renderizam `AV BRIG LUIS ANTONIO`.
- O logradouro sem tipo do catálogo é coberto pelo `test_nome_completo_do_logradouro_junta_titulo_e_preposicao`
  da SPEC 006.
