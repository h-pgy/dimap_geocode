---
spec: roteamento_busca/010
versao: v8
atualizado_em: 2026-07-02
implementado: true
changelog:
  - v1: versão inicial
  - v2: canonicalização das grafias de "sem número" — submódulo próprio em services/utils/normalization (normalize_sem_numero, irmão de normalize_text), regex pós-normalize_text composta pela chave de porta e aplicada dos dois lados (input e coluna cacheada do catalog)
  - v3: EnderecoLoteParse expõe numero_bruto (input original) e numero_padronizado (computed_field = chave_numero_porta do input); chave_numero_porta passa a viver em services/utils/normalization (single-source entre o parse e a coluna do catalog); o matcher consome numero_padronizado direto
  - v4: critério explícito de que o número normalizado é só para o match — sugestão e mapa/pop-up sempre exibem cd_numero_porta original (via ContribuinteMatchOutput.numero); enderecos_fiscais_com_chave preserva a coluna original
  - v5: pop-up do lote passa a exibir o endereço da base oficial — LoteAttributes ganha codlog (cd_logradouro), nome_logradouro (nm_logradouro_completo) e numero_porta (cd_numero_porta, '' quando None) + computed_field endereco (nome + número); parse no LoteGeocoder._montar_attributes e exibição em _popup_lote.html
  - v6: consistência verificada contra o código/dados reais — (a) cd_logradouro do parquet fiscal tem 6 dígitos (codlog+DV) e os matchers devolvem 5, então o catalog prepara também a coluna codlog5 e o mask casa contra ela; (b) cd_numero_porta tem nulos no parquet, fillna('') antes da chave; (c) normalize_text preserva 'º' ('s/nº' → 'S Nº'), regex de sem-número passa a cobrir 'º'; (d) LogradouroIdentifier USA separar_numero como guarda — com o split permissivo, a guarda aplica o parser estrito sobre o token para manter LOGRADOURO intacto em 's/n'; snippets adicionados (_resolver_codlogs, pipeline do EnderecoLoteIdentifier, partial da seção, esqueleto parametrizado dos localizadores)
  - v7: correção de regressão — parse_numero_porta com fullmatch NÃO era superconjunto do estrito (parse_numero_imovel usa match de PREFIXO), e como ele vira o critério de split, "Rua X, 10." / "Rua X, 10 apto 5" / "Av X, 1.578" deixariam de gerar ENDERECO; o ramo numérico passa a usar match de prefixo (espelho do NUMERO_IMOVEL) e snippet dos identifiers estritos adicionado, explicitando que numero permanece int (interpolação intacta)
  - v8: exibir o codlog no formato `(codlog: CODLOG-dv)` após o nome do logradouro nas sugestões de "Endereço cadastrado (lote)" (parse do cd_logradouro de 6 dígitos em codlog+DV no template), para desambiguar quando a busca é por codlog (ver Patch 001)
---

# SPEC roteamento_busca/010 — Endereço que é lote (sugestões de endereço fiscal com precedência)

- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como usuário da busca simples, quero que, ao digitar um **endereço** (nome de rua + número ou
codlog + número), o sistema verifique se aquele endereço **existe no cadastro de endereços
fiscais** — e, quando existir, me mostre esses imóveis como sugestões **antes** das demais
sugestões de endereço, para que eu selecione direto o **lote** (polígono) em vez da
geocodificação por interpolação (ponto). Se o endereço digitado é um imóvel cadastrado, o que
prevalece é o lote — **sem pop-up** perguntando ponto ou polígono (decisão revogada do item 4 do
roadmap).

Quero também poder digitar números de porta **não estritamente numéricos** — `Rua Tal, 10A`,
`Rua Tal, s/n` — porque é exatamente assim que esses imóveis aparecem no cadastro fiscal. Isso
vale **só** para esse caminho: a geocodificação por interpolação continua exigindo número inteiro.

E como **"sem número" se escreve de muitas formas** (`s/n`, `S/N`, `sn`, `s.n.`, `s/nº`,
`sem número`), **não quero ter de acertar a grafia exata do cadastro**: todas essas formas devem
casar com o mesmo imóvel, independentemente de como ele foi gravado na base.

## Critérios de aceite

- [ ] Digitar **nome de logradouro + número** (ex.: `AV PAULISTA, 100`) cujo codlog+número tem
      correspondência em `enderecos_fiscais` produz uma seção **"Endereço cadastrado (lote)"**
      listando os imóveis fiscais que casam, **acima** das seções "Endereço (por codlog)" e
      "Endereço (por nome)" (e abaixo apenas de "Lote (por contribuinte)", quando houver).
- [ ] Digitar **codlog + número** (ex.: `12345 100`) também produz a seção de endereço cadastrado,
      resolvendo o codlog pelo **lookup exato já existente** (sem passar pelo match por nome).
- [ ] **Clicar** numa sugestão de endereço cadastrado dispara **exatamente o fluxo do lote já
      existente**: POST para `lote_geocoder:geocodificar` com `setor/quadra/lote/tipo_lote` →
      polígono renderizado no mapa. Nenhuma view ou domínio de geocodificação novo.
- [ ] O match do número de porta aceita formas **alfanuméricas e "sem número"**: `10A`, `10-A`,
      `s/n`, `S/N`, `sn`, `sem número` (após vírgula). `Rua X, s/n` passa a gerar candidato de
      endereço-lote (hoje não gera candidato de endereço algum). O caminho da **interpolação não
      muda**: `EnderecoParse.numero` e `EnderecoCodlogParse.numero` continuam `int`, e `10A`
      continua interpolando como `10`.
- [ ] O match do número nas sugestões é **prefixo (startswith), sem fuzzy**, sobre o número
      **normalizado nas duas pontas** com a `normalize_text` única do projeto (§7.1): digitar
      `Rua Direita, 1` sugere imóveis com porta `1`, `10A`, `12`…; digitar `10a` encontra `10-A`.
- [ ] Todas as grafias de **"sem número"** colapsam numa **única chave canônica**: **depois** da
      `normalize_text` padrão, uma **regex dedicada** reconhece as formas já normalizadas
      (`S N` de `s/n`/`s.n.`, `SN` de `sn`, `S NO`, `S Nº` de `s/nº` — o `º` é letra Unicode e
      **sobrevive** à normalização —, `SEM NUMERO` de `sem número`, …) e as reduz ao
      **mesmo token**, de modo que digitar `s/n` encontra o imóvel cadastrado como `SEM NÚMERO`
      (e vice-versa). A canonicalização roda **sobre o texto já normalizado**, **nas duas pontas**
      (coluna do catalog e consulta) e **não toca** números comuns (`10`, `10A` passam intactos).
- [ ] A coluna normalizada de `cd_numero_porta` — **já com a canonicalização de "sem número"
      embutida na função de chave** — é **preparada uma vez e cacheada** no catalog (mesmo padrão
      TTL das demais), e **aquecida** junto no `aquecer()` — nunca recalculada a cada request.
- [ ] Quando o catálogo fiscal **não tem correspondência**, a seção é **omitida por inteiro** —
      sem "Nenhum lote encontrado" poluindo a lista (o candidato é especulativo por natureza).
- [ ] As sugestões da seção são **limitadas** (default 5) para não poluir a UX, mesmo quando o
      match literal do logradouro devolve vários codlogs.
- [ ] `EnderecoParse` e `EnderecoCodlogParse` ganham o campo **`numero_bruto: str`** (o token do
      número como digitado), para auditabilidade — sem mudança de comportamento no caso base.
- [ ] `EnderecoLoteParse` expõe **dois atributos de número**: **`numero_bruto: str`** (a entrada
      original do usuário, como digitada) e **`numero_padronizado`** (um **`computed_field`** =
      `chave_numero_porta(numero_bruto)`, ou seja `normalize_text` + `normalize_sem_numero` +
      remoção de espaços). Ex.: `numero_bruto="s/n"` → `numero_padronizado="SN"`;
      `numero_bruto="10-A"` → `numero_padronizado="10A"`. O matcher fiscal consome
      **`numero_padronizado` direto** (não re-normaliza), casando contra a coluna cacheada do
      catalog — que usa a **mesma** `chave_numero_porta` (single-source, §7.1).
- [ ] O número **normalizado** (`numero_padronizado` / coluna `chave_numero_porta`) serve **só ao
      match**. O que é **exibido** na sugestão e o que vai para o **mapa/pop-up** é sempre o número
      **original da base** — nunca a chave normalizada. Na **sugestão**, vem de
      `cd_numero_porta` via `ContribuinteMatchOutput.numero` (output reutilizado como está); no
      **pop-up**, do `cd_numero_porta` da **feature WFS do lote** (ver critério abaixo).
      `enderecos_fiscais_com_chave` **preserva** `cd_numero_porta` (só **acrescenta** a coluna de
      chave).
- [ ] O **pop-up do lote** passa a exibir o **endereço da base oficial** (logradouro + número de
      porta), hoje ausente. `LoteAttributes` (`services/domain/lote_geocod`) ganha **`codlog`** (da
      coluna `cd_logradouro`), **`nome_logradouro`** (de `nm_logradouro_completo`), **`numero_porta`**
      (de `cd_numero_porta`, tratado para **`''` quando `None`**) e um **`computed_field`
      `endereco`** = junção `nome_logradouro` + `numero_porta`. Os três campos são **parseados** no
      `LoteGeocoder._montar_attributes` (a partir dos `props` da feature WFS) e o `_popup_lote.html`
      passa a mostrar o `endereco`. Todos os valores vêm da **base oficial** — nada de número
      normalizado aqui.
- [ ] A **precedência** é decidida no roteador (constante `PRIORIDADE_TIPOS`), não na view nem no
      template: o novo `TipoEntrada.ENDERECO_LOTE` entra logo após `CONTRIBUINTE` e antes de todos
      os outros tipos de endereço. A view de search apenas propaga a ordem, como hoje.
- [ ] Respostas são *partials* HTML (§3.1); DTOs Pydantic nas fronteiras; `ValidationError`
      propaga ao middleware (infraestrutura/001); tipagem integral e `mypy` limpo.

## Contexto e decisões de arquitetura

Mexe em **domínio** (`roteamento_busca`: novo tipo/parse/identifier e precedência;
`address_match`: leitor permissivo de número de porta; `contribuinte_match`: novo matcher por
codlog+número e coluna normalizada no catalog) e em **interface/orquestração** (renderer da nova
seção + partial; registro no `search`). **Nada muda a jusante da seleção**: o clique reaproveita
a view e o domínio de geocodificação de lote existentes.

A observação que estrutura tudo: **o output do novo matcher é o `ContribuinteMatchOutput` que já
existe** — um endereço fiscal *é* um lote, só muda a **chave de busca** (codlog + número de porta
em vez de setor/quadra/lote). Por isso:

- o matcher novo mora em `contribuinte_match` (mesmo domínio, chave diferente — duas classes,
  duas razões de mudança, §10.1);
- o mapeamento DataFrame → `ContribuinteMatchOutput` (hoje método privado do
  `ContribuinteMatcher`) é **extraído para função compartilhada** do módulo e composto pelos dois
  matchers — não duplicado;
- o partial da nova seção espelha `resultados_contribuinte.html` e posta para o **mesmo endpoint**
  `lote_geocoder:geocodificar`.

### O candidato é especulativo — e a seção pode sumir

O roteador é **parsing puro de texto**: ele não consulta base nenhuma, então não tem como saber
se o endereço digitado existe no cadastro fiscal. O `EnderecoLoteIdentifier` emite o candidato
`ENDERECO_LOTE` para **qualquer** entrada com cara de endereço (inclusive as que só ele aceita,
como `s/n` e `10A`); é o **renderer da seção** que consulta o catálogo e descobre se há match.
Consequência de UX: na maioria das buscas de endereço não haverá imóvel fiscal casando, e exibir
uma seção vazia no topo poluiria a lista. Por isso o contrato do renderer muda para
`SecaoResultado | None` e a view de search **filtra os `None`** — mudança mínima no laço existente.

### Duas formas de entrada, um tipo só

`ENDERECO_LOTE` cobre as duas formas de digitar endereço (por **nome** e por **codlog**), porque o
desfecho é o mesmo. O `EnderecoLoteParse` carrega `logradouro: LogradouroParse | None` **ou**
`codlog: CodlogParse | None` (exatamente um) + o número em **duas formas**: `numero_bruto: str` (a
entrada original do usuário) e `numero_padronizado` (um `computed_field` derivado do bruto — ver
"Normalização do número" abaixo). No renderer, a resolução para
**codlogs** reutiliza o que já existe (mesma tabela da SPEC 009):

| Forma da entrada | Como resolve os codlogs | Peça reutilizada           |
|------------------|--------------------------|----------------------------|
| nome + número    | match literal/substring  | `match_logradouro_literal` |
| codlog + número  | lookup exato de codlog   | `match_codlog`             |

Com os codlogs na mão (pode haver **mais de um** — o input do matcher aceita lista e o filtro usa
`isin`), o `EnderecoFiscalMatcher` casa o codlog (exato) + `cd_numero_porta` (prefixo normalizado)
e devolve `list[ContribuinteMatchOutput]`. **Fato verificado nos dados:** no parquet fiscal,
`cd_logradouro` tem **6 dígitos** (codlog + DV, ex. `048046`), enquanto `match_codlog` e
`match_logradouro_literal` devolvem codlog de **5 dígitos** — o `isin` direto contra
`cd_logradouro` nunca casaria. Por isso o catalog prepara (junto com a chave de porta) uma coluna
**`codlog5 = cd_logradouro.str[:5]`** e é contra **ela** que o matcher faz o `isin`.

### Número de porta: permissivo só onde deve ser

O cadastro fiscal registra portas como `10A`, `10-A`, `S/N`, `SN` — e é **só** nesse caminho que
essas formas valem. A regra mora no domínio de endereço (`address_match`), ao lado do
`parse_numero_imovel` estrito: um **`parse_numero_porta(token) -> str | None`** que aceita
marcador + dígitos com sufixo de unidade **ou** as formas de "sem número", devolvendo o token
**bruto** (a normalização acontece na composição da chave, não aqui — auditável no DTO). O ramo
numérico usa **match de prefixo, espelhando o estrito** (não fullmatch): é isso que torna o
superconjunto verdadeiro e preserva entradas que hoje geram `ENDERECO` com tokens "sujos" —
`Rua X, 10.`, `Rua X, 10 apto 5`, `Rua X, 10, casa 2` continuam gerando candidato de endereço.

Nos localizadores de `roteamento_busca/parsing.py`, `separar_numero` e `separar_numero_codlog` já
são quase-duplicatas; em vez de criar uma terceira cópia, o esqueleto comum (vírgula / tokens /
marcador residual) passa a ser **parametrizado pelo leitor de número**. O critério de *split*
passa a ser o leitor **permissivo** (superconjunto do estrito) e os localizadores devolvem o
token bruto; cada identifier aplica **seu** parser: os estritos (`EnderecoIdentifier`,
`CodlogNumeroIdentifier`) seguem exigindo `int` (e devolvem `None` para `s/n`), o novo aceita a
string. Comportamento existente preservado: `Rua X, 10A` continua gerando `ENDERECO` com
`numero=10` (agora também `numero_bruto="10A"`), e `Rua X, s/n` — que hoje não gera endereço —
passa a gerar **só** `ENDERECO_LOTE`, com o candidato `LOGRADOURO` intacto.

**Atenção à guarda do `LogradouroIdentifier`:** ele **usa** `separar_numero` como guarda negativa
(suprime `LOGRADOURO` quando a entrada tem número). Com o split permissivo, `separar_numero`
passaria a "ver número" em `Rua X, s/n` e o candidato `LOGRADOURO` sumiria — regressão. Por isso a
guarda também aplica **seu** parser (o estrito): `LOGRADOURO` só é suprimido quando o token do
split parseia como `int` (`parse_numero_imovel`). Assim `Rua X, 10A` segue sem `LOGRADOURO`
(comportamento de hoje) e `Rua X, s/n` mantém o seu.

### Normalização do número — mesma função, chave única

A comparação digitado × base usa uma **chave de porta** — a função `chave_numero_porta` — que
**compõe dois passos encadeados**, sem implementar normalização própria:

1. **Normalização padrão do projeto** (`normalize_text`, §7.1) — uppercase, sem acento, pontuação
   virando espaço. Colapsa `10a` / `10-A` / `10 A` (após remover espaços residuais) na mesma chave
   `10A`.
2. **Canonicalização de "sem número"** (`normalize_sem_numero`) — uma **regex dedicada, aplicada só
   depois do passo 1** (portanto **sobre o texto já normalizado**, nunca sobre o texto cru), que
   reconhece as formas que "sem número" assume **depois** da normalização (`S N` de `s/n`/`s.n.`;
   `SN` de `sn`; `S NO`; `S Nº` de `s/nº` — o `º` ordinal é `\w` e não decompõe em NFD, então
   **sobrevive** à `normalize_text`; `SEM NUMERO` de `sem número`) e as reduz a **um token
   canônico único**; qualquer outra entrada (número comum) **passa intacta**. **Este passo é necessário porque o passo
   1 sozinho não basta:** só com `normalize_text` + remoção de espaços, `s/n` viraria `SN` mas `sem
   número` viraria `SEMNUMERO` — chaves **diferentes** para o mesmo conceito. A regex é **ancorada**
   nas grafias de "sem número", então números comuns (`10`, `10A`) não casam e passam intactos.

**Onde moram a canonicalização e a chave.** Ambas são **normalização de texto reutilizável**, não
regra de lote — por isso vivem em **`services/utils/normalization`**: `normalize_sem_numero` (a
canonicalização) num submódulo próprio (ex.: `sem_numero.py`), como callable **irmão** de
`normalize_text`; e `chave_numero_porta` (que só **compõe** `normalize_text` +
`normalize_sem_numero` + remoção de espaços residuais, §10.4) no mesmo pacote — **ambos
reexportados pelo `__init__.py`** (§11: `__init__.py` só reexporta; implementação nos submódulos).
`normalize_sem_numero` **assume input já normalizado** (o chamador roda `normalize_text` antes) — é
o "regex de dois lados" que só faz sentido sobre a saída da normalização padrão. **A chave viver em
`utils` é o que torna o single-source possível:** ela é consumida por **dois domínios distintos** —
o `roteamento_busca` (no `computed_field` `numero_padronizado`) e o `contribuinte_match` (na coluna
do catalog) — e nenhum importa o outro; ambos importam de `utils`.

**As duas pontas do match são `numero_padronizado` × coluna do catalog.** No lado do **input**, o
`EnderecoLoteParse` expõe `numero_padronizado` como **`computed_field` = `chave_numero_porta(
numero_bruto)`** — a padronização acontece **uma vez, no parse**, e fica no DTO (auditável ao lado
do `numero_bruto`). No lado da **base**, a coluna preparada do catalog aplica a **mesma**
`chave_numero_porta`. O **matcher não normaliza nada**: recebe `numero_padronizado` já pronto e faz
`startswith` contra a coluna. No catalog, a coluna preparada vira um segundo `ttl_cached_property`,
aquecido no `aquecer()` (padrão da infraestrutura/003); como a canonicalização entra **dentro** da
função de chave, a **coluna cacheada
já sai canonizada** — nenhuma grafia de "sem número" é reprocessada a cada request.

### Endereço no pop-up do lote (base oficial) — a SPEC alcança outro domínio

O desfecho de `ENDERECO_LOTE` é o **polígono do lote** renderizado com um pop-up. Fecha o ciclo da
funcionalidade que o pop-up **confirme o endereço** ("este lote é a AV PAULISTA, 100"), mas hoje ele
só mostra `setor.quadra.lote` + tipo — **não traz o número de porta**. Por isso esta SPEC também
mexe no domínio **`lote_geocod`** e no partial do pop-up. Isso é esperado: **uma SPEC é uma
funcionalidade, não um recorte de arquitetura** — pode atravessar quantos domínios o valor exigir
(§4 da skill de SPECs).

A fonte é a **feature WFS do lote** (a mesma já consultada pelo `LoteGeocoder`), não o parquet fiscal
nem a chave normalizada — são as colunas **oficiais** `cd_logradouro`, `nm_logradouro_completo` e
`cd_numero_porta` dos `props` da feature. O `LoteAttributes` (DTO da camada `attributes`) ganha:

- `codlog` (de `cd_logradouro`) — opcional (`str | None`), como os demais atributos de origem;
- `nome_logradouro` (de `nm_logradouro_completo`) e `numero_porta` (de `cd_numero_porta`), ambos
  **`str` com `''` quando ausentes/`None`** (o join precisa de string, e é a regra pedida para o
  número);
- `endereco`: **`computed_field`** = junção de `nome_logradouro` + `numero_porta` (o que o pop-up
  exibe).

O parse mora no `LoteGeocoder._montar_attributes` — que **já compõe** os atributos opcionais a partir
do dicionário `_OPCIONAIS` (origem → campo); os três novos entram nesse mesmo mecanismo, e o
tratamento `None → ''` fica no **DTO** (validator), fonte única da regra. O `_popup_lote.html` só
acrescenta a linha do `endereco` (omitida quando vazio). Nada disso toca a geocodificação em si nem
o CRS — é enriquecimento de atributos de exibição.

> **Nota de fonte de dados:** os três campos dependem de a camada WFS do lote (`WFS_LAYER_LOTE_CIDADAO`)
> expor essas colunas. Se não expuser, `props.get(...)` devolve `None` e os campos degradam para
> `None`/`''` (o pop-up simplesmente não mostra a linha) — sem quebrar. Confirmar na implementação
> que a camada traz `cd_logradouro`/`nm_logradouro_completo`/`cd_numero_porta`.

### Princípios aplicados (§3, §10, §11)

- **§3.1 HATEOAS:** a seção é *partial* HTML; o clique é `hx-post`; nenhum JSON via JS.
- **§3.3 Isolamento:** identifier, parses, matcher e chave de normalização vivem no domínio, sem
  Django; o renderer só adapta candidato → DTO e escolhe o partial.
- **§10.1 SRP:** `ContribuinteMatcher` intocado; matcher novo para a chave nova; mapeamento de
  output compartilhado por composição; o módulo não cruza domínios (endereço fiscal É lote).
- **§10.4 Composição:** `EnderecoLoteIdentifier` compõe localizadores + `CodlogIdentifier`;
  renderer compõe `match_logradouro_literal` / `match_codlog` / `EnderecoFiscalMatcher`.
- **§7.1 Normalização única:** `normalize_text`, `normalize_sem_numero` e `chave_numero_porta`
  vivem juntos em `services/utils/normalization`; a chave é single-source entre o `computed_field`
  `numero_padronizado` (input) e a coluna do catalog (base) — dois domínios, uma função.
- **§10.5:** Python 3.14 — sem `from __future__`.

## Peças de referência a compor

- `@services/domain/roteamento_busca` → `TipoEntrada`, `Candidato` (união discriminada —
  acrescentar o novo parse), `LogradouroParse`/`CodlogParse` (compostos no novo parse),
  `CodlogIdentifier` (compor no branch por codlog), `EntradaRouter` + `PRIORIDADE_TIPOS`
  (acrescentar identifier e precedência), `__init__.py` (expor o novo parse/tipo). Padrão de
  `computed_field` a espelhar no `numero_padronizado` do novo parse: os `@computed_field @property`
  já existentes em `ContribuinteParse`/`CodlogParse` (`mascara`, `completo`, …). O `models.py`
  importa `chave_numero_porta` de `services.utils.normalization` (util neutro — não é dependência
  cross-domain).
- `@services/domain/roteamento_busca/parsing.py` → `separar_numero`, `separar_numero_codlog`,
  `split_tipo_nome`: esqueleto a **parametrizar pelo leitor de número** (não triplicar).
- `@services/domain/address_match` → `parse_numero_imovel`, `eh_so_marcador`, `MARCADOR_NUMERO`:
  o leitor permissivo novo mora ao lado e reaproveita o marcador; exposto no `__init__.py`.
- `@services/domain/contribuinte_match` → `ContribuinteCatalog` (+ `ttl_cached_property` de
  `@services/utils/cache` e o `aquecer()`; a coluna nova aplica `chave_numero_porta` **importada de
  `utils`**, não uma cópia local), `ContribuinteMatchOutput` (output **reutilizado como está**),
  `ContribuinteMatcher._mapear_resultados` (extrair para função compartilhada), `contribuinte_catalog`
  (instância única — o matcher novo compõe o mesmo catalog). O `EnderecoFiscalMatcher` **não
  normaliza**: recebe `numero_padronizado` pronto e faz `startswith`.
- `@services/utils/normalization` → `normalize_text`: normalização padrão do projeto (skill
  `normalize-text`), composta no passo 1 da chave. Neste mesmo pacote são **adicionados dois
  submódulos novos** (implementação no submódulo, reexport no `__init__.py`, padrão de
  `normalizer.py`): `normalize_sem_numero` (canonicalização de "sem número") e `chave_numero_porta`
  (compõe `normalize_text` + `normalize_sem_numero` + strip). Ambos são consumidos por `roteamento_busca`
  (no `computed_field` `numero_padronizado`) e por `contribuinte_match` (coluna do catalog).
- `@services/domain/logradouros_match` → `match_logradouro_literal`, `LiteralLogradouroQuery`:
  resolução nome → codlogs (branch por nome).
- `@services/domain/codlog_match` → `match_codlog`, `CodlogMatchInput`: resolução exata
  codlog → codlogs (branch por codlog).
- `@apps/lote_matcher/views.py` → `secao_contribuinte`: padrão de renderer a espelhar;
  `@apps/search/views.py` → `REGISTRO_SECOES` + laço de `rotear_busca` (filtrar `None`);
  `@apps/search/secoes.py` → `SecaoResultado`.
- `@templates/lote_matcher/partials/resultados_contribuinte.html` → padrão do partial (mesmo
  `hx-vals` e mesmo destino `lote_geocoder:geocodificar`); **sem** o ramo "Nenhum lote
  encontrado" (seção vazia é omitida a montante).
- `@services/domain/lote_geocod` → `LoteAttributes` (acrescentar `codlog` / `nome_logradouro` /
  `numero_porta` + `computed_field` `endereco`), `LoteGeocoder._montar_attributes` e o dict
  `_OPCIONAIS` (origem → campo; estender com as três colunas), `_as_str` (helper já existente).
- `@templates/lote_geocoder/partials/_popup_lote.html` → pop-up atual (setor.quadra.lote + tipo +
  condomínio): acrescentar a linha do `endereco`, omitida quando vazio.
- **SPEC 009** (endereço com número + precedência no roteador) → desenho que esta SPEC estende.
  **SPEC infraestrutura/003** (warmup eager dos catalogs) → padrão do aquecimento da nova coluna.

## Snippets sugeridos

### Leitor permissivo de número de porta (`services/domain/address_match`)

```python
# direção — adaptar sem violar §3 nem §10
SEM_NUMERO = re.compile(r"^(?:s[./]?n[º°o.]?|sem\s+n[uú]mero)$", re.IGNORECASE)
# Ramo numérico espelha NUMERO_IMOVEL: match de PREFIXO, SEM âncora/fullmatch — só acrescenta
# o sufixo de unidade ao grupo. É o prefixo que garante o SUPERCONJUNTO do estrito: todo token
# que parse_numero_imovel aceita ("10.", "10 apto 5", "10, casa 2", "1.578") este também
# aceita. Com fullmatch, esses tokens seriam rejeitados e — como este leitor é o critério de
# split dos localizadores — a entrada deixaria de gerar QUALQUER candidato de endereço
# (regressão sobre o comportamento atual).
NUMERO_PORTA = re.compile(rf"{MARCADOR_NUMERO}?\s*(\d+[\w\-]*)", re.IGNORECASE)


def parse_numero_porta(token: str) -> str | None:
    """Número de porta do cadastro fiscal: '10', '10A', '10-A', 's/n', 'sem número'.

    Devolve o número BRUTO validado — dígitos + sufixo de unidade, sem o marcador
    ('nº 10A' -> '10A'; '10 apto 5' -> '10'); grafia de "sem número" volta como digitada.
    Sem normalizar: a chave de match (chave_numero_porta) é aplicada depois, no parse.
    Superconjunto de parse_numero_imovel: tudo que o estrito aceita, este aceita.
    """
    limpo = token.strip()
    if SEM_NUMERO.fullmatch(limpo):
        return limpo
    m = NUMERO_PORTA.match(limpo)
    return m.group(1) if m else None
```

### Localizadores parametrizados (`services/domain/roteamento_busca/parsing.py`)

```python
# O esqueleto comum (vírgula / tokens / marcador residual) localiza o TOKEN candidato e usa
# parse_numero_porta (permissivo, superconjunto) como critério de split, devolvendo o token bruto.
#   separar_numero("Rua X, 10A")  -> ("Rua X", "10A")
#   separar_numero("Rua X, s/n")  -> ("Rua X", "s/n")     # novo: hoje devolve None
#   separar_numero_codlog("12345 100") -> ("12345", "100")  # regras de âncora/ponto intactas
# Cada identifier aplica SEU parser sobre o token: estritos exigem int, o de lote aceita str.
import re
from collections.abc import Callable

from services.domain.address_match import eh_so_marcador, parse_numero_porta

COMECA_COM_LETRA = re.compile(r"[^\W\d_]", re.UNICODE)

LeitorNumero = Callable[[str], str | None]


def _separar_token_numero(texto: str, leitor: LeitorNumero) -> tuple[str, str] | None:
    """Esqueleto comum aos dois localizadores — hoje duplicado, passa a existir uma vez.

    `leitor` é o critério de split (o que conta como "token de número"); o retorno é
    sempre o token BRUTO — quem parseia é o identifier consumidor.
    """
    head, sep, resto = texto.partition(",")

    if sep and resto.strip():
        token = resto.strip()
        if leitor(token) is not None:
            return head.strip(), token

    # Sem vírgula (ou vírgula sem número parseável depois): verifica último(s) token(s)
    tokens = (head if sep else texto).split()
    if len(tokens) < 2:
        return None

    token = tokens[-1]
    if leitor(token) is None:
        return None

    penultimo = tokens[-2]
    prefixo = " ".join(tokens[:-2] if eh_so_marcador(penultimo) else tokens[:-1])
    if not prefixo:
        return None
    return prefixo, token


def separar_numero(texto: str) -> tuple[str, str] | None:
    """(logradouro, token bruto) ou None. Split pelo leitor permissivo (superconjunto)."""
    limpo = texto.strip()
    if not COMECA_COM_LETRA.match(limpo):
        return None
    return _separar_token_numero(limpo, parse_numero_porta)


def separar_numero_codlog(texto: str) -> tuple[str, str] | None:
    """(codlog_txt, token bruto) ou None. Âncora em dígito e rejeição de ponto intactas.

    Obs.: a rejeição de ponto (formato de contribuinte) vale para a ENTRADA inteira,
    então "12345, s.n." fica fora deste caminho — "12345, s/n" e "12345, sn" funcionam.
    """
    limpo = texto.strip()
    if not limpo or not limpo[0].isdigit():
        return None
    if "." in limpo:
        return None
    return _separar_token_numero(limpo, parse_numero_porta)


# LogradouroIdentifier — a guarda negativa fica ESTRITA (o split é permissivo, mas LOGRADOURO
# só é suprimido quando o token parseia como número de imóvel; preserva LOGRADOURO em "s/n"):
#   partes = separar_numero(limpo)
#   if partes is not None and parse_numero_imovel(partes[1]) is not None:
#       return None
```

### Identifiers estritos — contrato `int` preservado (`services/domain/roteamento_busca`)

Os localizadores agora devolvem o token **bruto** (`str`), então `EnderecoIdentifier` e
`CodlogNumeroIdentifier` passam a re-parsear o token com o parser **estrito** — e é isso que
**garante que nada muda a jusante**: `EnderecoParse.numero` e `EnderecoCodlogParse.numero`
continuam `int`, os partials continuam postando `numero` para o `address_geocoder`, e a
**interpolação** (que exige número inteiro) permanece intacta.

```python
class EnderecoIdentifier:
    def __call__(self, texto: str, finished_typing: bool) -> EnderecoParse | None:
        partes = separar_numero(texto)
        if partes is None:
            return None
        logradouro_txt, token = partes
        numero = parse_numero_imovel(token)  # estrito: int ou None — MESMO parser de hoje
        if numero is None:
            return None  # "s/n" não vira ENDERECO — só ENDERECO_LOTE
        tipo, nome = split_tipo_nome(logradouro_txt)
        return EnderecoParse(
            logradouro=LogradouroParse(
                tipo_logradouro=tipo, nome=nome, entrada_finalizada=finished_typing
            ),
            numero=numero,
            numero_bruto=token,
        )


# CodlogNumeroIdentifier: mesmo padrão — parse_numero_imovel(token) para o `numero: int`,
# token bruto em `numero_bruto`, None quando o token não parseia como int.
```

### Novo parse + tipo + precedência (`services/domain/roteamento_busca`)

```python
class TipoEntrada(StrEnum):
    ...
    ENDERECO_LOTE = "endereco_lote"  # novo


# models.py importa de utils (neutro, não é cross-domain):
#   from services.utils.normalization import chave_numero_porta


class EnderecoLoteParse(BaseModel):
    tipo: Literal[TipoEntrada.ENDERECO_LOTE] = TipoEntrada.ENDERECO_LOTE
    logradouro: LogradouroParse | None = None
    codlog: CodlogParse | None = None
    numero_bruto: str  # a entrada original do usuário, como digitada ("s/n", "10-A", "100")

    @model_validator(mode="after")
    def _exatamente_uma_forma(self) -> "EnderecoLoteParse":
        if (self.logradouro is None) == (self.codlog is None):
            raise ValueError("Informe logradouro OU codlog (exatamente um).")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def numero_padronizado(self) -> str:
        """numero_bruto após normalize_text + match de "sem número" (a chave de porta).

        Derivado do bruto (não é um segundo campo de entrada). O matcher fiscal consome
        ISTO direto; a coluna do catalog usa a MESMA chave_numero_porta (single-source, §7.1).
        Ex.: "s/n" -> "SN"; "10-A" -> "10A"; "100" -> "100".
        """
        return chave_numero_porta(self.numero_bruto)


# EnderecoParse e EnderecoCodlogParse ganham `numero_bruto: str` (auditabilidade);
# `numero: int` permanece como está nos dois. Eles NÃO ganham `numero_padronizado`
# (vão para interpolação com número inteiro; "sem número" não se aplica).

PRIORIDADE_TIPOS: tuple[TipoEntrada, ...] = (
    TipoEntrada.CONTRIBUINTE,
    TipoEntrada.ENDERECO_LOTE,   # novo: precede os demais endereços
    TipoEntrada.ENDERECO_CODLOG,
    TipoEntrada.ENDERECO,
    TipoEntrada.CODLOG,
    TipoEntrada.LOGRADOURO,
)
```

### Identifier (`services/domain/roteamento_busca`)

```python
class EnderecoLoteIdentifier:
    """Emite ENDERECO_LOTE para entrada com cara de endereço, nas duas formas (nome/codlog)."""

    def __init__(self, codlog_identifier: CodlogIdentifier | None = None) -> None:
        self._codlog = codlog_identifier or CodlogIdentifier()

    def __call__(self, texto: str, finished_typing: bool) -> EnderecoLoteParse | None:
        return self._pipeline(texto, finished_typing)

    def _pipeline(self, texto: str, finished_typing: bool) -> EnderecoLoteParse | None:
        # exatamente uma das formas produz parse (o model_validator garante a exclusividade)
        return self._por_codlog(texto, finished_typing) or self._por_nome(texto, finished_typing)

    def _por_nome(self, texto: str, finished_typing: bool) -> EnderecoLoteParse | None:
        partes = separar_numero(texto)
        if partes is None:
            return None
        logradouro_txt, token = partes
        numero_bruto = parse_numero_porta(token)
        if numero_bruto is None:
            return None
        tipo, nome = split_tipo_nome(logradouro_txt)
        return EnderecoLoteParse(
            logradouro=LogradouroParse(
                tipo_logradouro=tipo, nome=nome, entrada_finalizada=finished_typing
            ),
            numero_bruto=numero_bruto,
        )

    def _por_codlog(self, texto: str, finished_typing: bool) -> EnderecoLoteParse | None:
        partes = separar_numero_codlog(texto)
        if partes is None:
            return None
        codlog_txt, token = partes
        numero_bruto = parse_numero_porta(token)
        if numero_bruto is None:
            return None
        codlog = self._codlog(codlog_txt, finished_typing)
        if codlog is None:
            return None
        return EnderecoLoteParse(codlog=codlog, numero_bruto=numero_bruto)
```

### Normalização de "sem número" + chave de porta (`services/utils/normalization`)

Dois submódulos **novos** no pacote de normalização, irmãos de `normalizer.py`, ambos
reexportados pelo `__init__.py` (§11) ao lado de `normalize_text`. Ficam em `utils` (não no domínio
do lote) porque são consumidos por **dois domínios** — `roteamento_busca` (parse) e
`contribuinte_match` (catalog) — e nenhum importa o outro.

```python
# services/utils/normalization/sem_numero.py
import re

# Token canônico único para qualquer grafia de "sem número".
CANONICO_SEM_NUMERO = "SN"

# Regex aplicada SOBRE O TEXTO JÁ NORMALIZADO (saída de normalize_text), nunca sobre o cru:
# reconhece as formas que "sem número" assume depois da normalização (comportamento REAL
# conferido da normalize_text) —
#   S N (s/n, s.n., s/n°)  |  SN (sn)  |  S NO (s/no)  |  S Nº (s/nº)  |  SEM NUMERO (sem número).
# O 'º' ordinal é letra Unicode (\w) e NÃO decompõe em NFD — sobrevive à normalize_text —,
# por isso a regex precisa aceitá-lo. Já o '°' (degree sign) é símbolo e vira espaço.
# Ancorada (fullmatch): números comuns (10, 10A) não casam e passam intactos.
SEM_NUMERO_NORMALIZADO = re.compile(r"^S\s*N(?:[ºO]|UMERO)?$|^SEM\s*NUMERO$")


class SemNumeroNormalizer:
    """Canoniza as grafias de 'sem número' num token único.

    ASSUME input JÁ normalizado por normalize_text (§7.1) — é o passo 2 da chave, o
    'regex de dois lados' que só faz sentido sobre a saída da normalização padrão.
    Entrada que não casa 'sem número' (número comum) volta INTACTA.
    """

    def __call__(self, texto_normalizado: str) -> str:
        if SEM_NUMERO_NORMALIZADO.fullmatch(texto_normalizado):
            return CANONICO_SEM_NUMERO
        return texto_normalizado
```

```python
# services/utils/normalization/numero_porta.py
# Compõe as duas normalizações. Para não criar import circular com o __init__ (que instancia
# normalize_text/normalize_sem_numero), monte instâncias locais a partir das CLASSES dos submódulos:
from .normalizer import TextNormalizer
from .sem_numero import SemNumeroNormalizer

normalize_text = TextNormalizer()
normalize_sem_numero = SemNumeroNormalizer()


def chave_numero_porta(valor: str) -> str:
    """Chave única de match do número de porta — COMPÕE, sem normalização própria.

    1) normalize_text (§7.1): normalização padrão do projeto;
    2) normalize_sem_numero: canoniza as grafias de "sem número" (números comuns passam intactos);
    3) remove espaços residuais (ex.: '10 A' -> '10A'; o token canônico já é sem espaço).

    Fonte ÚNICA da chave: usada no computed_field numero_padronizado (input) E na
    coluna do catalog (base) — nunca duplicar. Ex.: 's/n' -> 'SN'; '10-A' -> '10A'.
    """
    return normalize_sem_numero(normalize_text(valor)).replace(" ", "")


# services/utils/normalization/__init__.py — reexporta tudo ao lado de normalize_text:
#   from .normalizer import TextNormalizer
#   from .sem_numero import SemNumeroNormalizer
#   from .numero_porta import chave_numero_porta
#   normalize_text = TextNormalizer()
#   normalize_sem_numero = SemNumeroNormalizer()
#   __all__ = ["normalize_text", "normalize_sem_numero", "chave_numero_porta"]
```

### Matcher fiscal (`services/domain/contribuinte_match`)

```python
class EnderecoFiscalMatchInput(BaseModel):
    codlogs: list[str] = Field(min_length=1)
    numero_padronizado: str = Field(min_length=1)  # já normalizado no parse (candidato.numero_padronizado)
    limite: int = Field(default=5, gt=0)


class EnderecoFiscalMatcher:
    def __init__(self, catalog: ContribuinteCatalog | None = None) -> None:
        self._catalog = catalog or ContribuinteCatalog()

    def __call__(self, payload: EnderecoFiscalMatchInput) -> list[ContribuinteMatchOutput]:
        return self._pipeline(payload)

    def _pipeline(self, payload: EnderecoFiscalMatchInput) -> list[ContribuinteMatchOutput]:
        df = self._catalog.enderecos_fiscais_com_chave
        mask = self._build_mask(df, payload)
        return mapear_resultados(df[mask].head(payload.limite))  # função compartilhada extraída

    def _build_mask(self, df: pd.DataFrame, payload: EnderecoFiscalMatchInput) -> pd.Series:
        # numero_padronizado JÁ é a chave (feita no parse) — o matcher não normaliza nada.
        # isin contra codlog5 (coluna preparada no catalog): cd_logradouro tem 6 dígitos
        # (codlog+DV) no parquet e os matchers de logradouro devolvem codlog de 5.
        return df["codlog5"].isin(payload.codlogs) & df["chave_numero_porta"].str.startswith(
            payload.numero_padronizado
        )
```

> `mapear_resultados` é o atual `ContribuinteMatcher._mapear_resultados` promovido a função do
> módulo, composta pelos dois matchers. O `__init__.py` expõe `match_endereco_fiscal` (instância
> com o **mesmo** `_catalog` compartilhado), `EnderecoFiscalMatchInput` e o que mais o renderer
> precisar. **Formato conferido nos dados:** `cd_logradouro` no parquet tem **6 dígitos**
> (codlog + DV zero-padded, ex. `048046`); `CodlogMatchOutput.codlog` e
> `LogradouroMatchOutput.codlog` têm **5** (o DV vem em campo próprio) — daí a coluna `codlog5`.

### Catalog: coluna preparada e cacheada (`services/domain/contribuinte_match/catalog.py`)

```python
from services.utils.normalization import chave_numero_porta  # a MESMA do numero_padronizado


@ttl_cached_property(ttl_seconds=DATA_TTL_SECONDS)
def enderecos_fiscais_com_chave(self) -> pd.DataFrame:
    df = self.enderecos_fiscais.copy()
    # cd_numero_porta tem NULOS no parquet (~23 mil) — fillna("") antes da chave, senão
    # normalize_text recebe None e quebra. Linha sem porta ganha chave "" (não casa
    # startswith de nenhuma consulta, já que numero_padronizado tem min_length=1).
    # chave_numero_porta já embute normalize_text + canonicalização de "sem número",
    # então a coluna cacheada sai canonizada (SEM NÚMERO -> token canônico) — nada é
    # reprocessado por request.
    df["chave_numero_porta"] = df["cd_numero_porta"].fillna("").map(chave_numero_porta)
    # cd_logradouro tem 6 dígitos (codlog+DV); os matchers devolvem 5 — coluna de match:
    df["codlog5"] = df["cd_logradouro"].str[:5]
    return df

# aquecer(): além de enderecos_fiscais, tocar enderecos_fiscais_com_chave.
```

### Renderer com omissão + registro (`apps/lote_matcher` + `apps/search`)

```python
TITULO_ENDERECO_LOTE = "Endereço cadastrado (lote)"


def _resolver_codlogs(candidato: EnderecoLoteParse) -> list[str]:
    """Resolve a entrada para codlogs (5 dígitos) — mesma tabela da SPEC 009."""
    if candidato.codlog is not None:
        resultados = match_codlog(
            CodlogMatchInput(
                input_codlog=candidato.codlog.codlog,
                digito_verificador=candidato.codlog.digito_verificador or None,
            )
        )
        return [r.codlog for r in resultados]
    assert candidato.logradouro is not None  # exclusividade garantida pelo model_validator
    resultado = match_logradouro_literal(
        LiteralLogradouroQuery(
            nome=candidato.logradouro.nome,
            tipo=candidato.logradouro.tipo_logradouro or None,
        )
    )
    return [m.codlog for m in resultado.logradouros]


def secao_endereco_lote(candidato: EnderecoLoteParse) -> SecaoResultado | None:
    codlogs = _resolver_codlogs(candidato)  # nome → match_logradouro_literal; codlog → match_codlog
    if not codlogs:
        return None
    resultados = match_endereco_fiscal(
        EnderecoFiscalMatchInput(codlogs=codlogs, numero_padronizado=candidato.numero_padronizado)
    )
    if not resultados:
        return None  # seção OMITIDA: candidato especulativo sem match não polui a UX
    html = render_to_string(
        "lote_matcher/partials/resultados_endereco_lote.html", {"resultados": resultados}
    )
    return SecaoResultado(titulo=TITULO_ENDERECO_LOTE, html=html)


# apps/search/views.py — o contrato passa a admitir None e o laço filtra:
SectionRenderer = Callable[..., SecaoResultado | None]
secoes = [
    secao
    for candidato in result.candidatos
    if (render_secao := REGISTRO_SECOES.get(candidato.tipo)) is not None
    and (secao := render_secao(candidato)) is not None
]
```

O partial espelha `resultados_contribuinte.html` (mesmo `hx-vals` com
`setor/quadra/lote/tipo_lote`, mesmo destino `lote_geocoder:geocodificar`), exibindo
`logradouro, numero` em destaque e o SQL como apoio — e **sem** ramo de lista vazia:

```django
{# templates/lote_matcher/partials/resultados_endereco_lote.html — fragmento HTMX, sem extends #}
{# Recebe: resultados (list[ContribuinteMatchOutput]) — nunca vazia: seção omitida a montante  #}
<ul class="divide-y divide-base-300">
  {% for r in resultados %}
    <li class="py-3 flex items-baseline gap-4 cursor-pointer hover:bg-base-200"
        hx-post="{% url 'lote_geocoder:geocodificar' %}"
        hx-vals='{"setor": "{{ r.setor }}", "quadra": "{{ r.quadra }}", "lote": "{{ r.lote }}", "tipo_lote": "{{ r.tipo_lote }}"}'
        hx-target="#resultado-busca"
        hx-swap="innerHTML"
    >
      <span class="font-medium">
        {{ r.logradouro }}, {{ r.numero }}{% if r.complemento %} — {{ r.complemento }}{% endif %}
      </span>
      <span class="font-mono text-sm text-base-content/60 shrink-0">
        {{ r.setor }}.{{ r.quadra }}.{{ r.lote }}{% if r.digito %}-{{ r.digito }}{% endif %}
      </span>
      <span class="badge badge-sm badge-ghost shrink-0">{{ r.tipo_lote }}</span>
    </li>
  {% endfor %}
</ul>
```

### Endereço no pop-up do lote (`services/domain/lote_geocod` + template)

```python
# services/domain/lote_geocod/models.py — LoteAttributes ganha três campos + endereco (computed).
class LoteAttributes(BaseModel):
    """Atributos do lote (camada `attributes` da feature)."""
    id_poligono: str
    setor: str
    quadra: str
    lote: str
    tipo_lote: str
    codlog: str | None = None          # cd_logradouro (opcional, como os demais de origem)
    nome_logradouro: str = ""          # nm_logradouro_completo (str; '' quando ausente/None)
    numero_porta: str = ""             # cd_numero_porta ORIGINAL (str; '' quando ausente/None)
    tipo_quadra: str | None = None
    condominio: str | None = None

    @field_validator("nome_logradouro", "numero_porta", mode="before")
    @classmethod
    def _none_para_vazio(cls, v: object) -> str:
        return "" if v is None else str(v)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def endereco(self) -> str:
        """Endereço por extenso da base oficial: nome do logradouro + número de porta."""
        partes = [p for p in (self.nome_logradouro, self.numero_porta) if p]
        return ", ".join(partes)
```

```python
# services/domain/lote_geocod/geocoder.py — só estender o dict de opcionais; o _montar_attributes
# (que já faz o spread `_as_str(props.get(origem))`) NÃO muda. O None->'' fica no DTO.
_OPCIONAIS: dict[str, str] = {
    "cd_tipo_quadra": "tipo_quadra",
    "cd_condominio": "condominio",
    "cd_logradouro": "codlog",
    "nm_logradouro_completo": "nome_logradouro",
    "cd_numero_porta": "numero_porta",
}
```

```django
{# templates/lote_geocoder/partials/_popup_lote.html — acrescentar a linha do endereço #}
<b>{{ a.setor }}.{{ a.quadra }}.{{ a.lote }}</b><br>
{% if a.endereco %}{{ a.endereco }}<br>{% endif %}
tipo {{ a.tipo_lote }}{% if a.condominio %} · cond. {{ a.condominio }}{% endif %}
```

## Fora de escopo

- **Pop-up "ponto ou polígono"** para endereço fiscal exato: decisão **revogada** — prevalece o
  lote, sem perguntar. Não é adiamento: o pop-up sai do roadmap.
- **Geocodificação de ponto a partir do polígono do lote** — não existe mais como desfecho deste
  fluxo.
- **Fuzzy** no número de porta ou no nome do logradouro desta seção: sugestões usam match
  literal/prefixo, como nas SPECs 007/009.
- **Formas multi-token de "sem número" sem vírgula** (`Rua X sem número`): só a forma pós-vírgula
  e os tokens únicos (`s/n`, `sn`, `s.n.`) são reconhecidos nesta iteração.
- **Busca detalhada** (campos segmentados) e alterações no fluxo de interpolação
  (`address_geocoder`) além do campo `numero_bruto` nos parses.
- **Estilização final** da seção (badge/ícone de "imóvel cadastrado" pode ser refinado depois).
- **Exibir o `codlog` no pop-up:** ele é **carregado** no `LoteAttributes` (dado disponível para uso
  futuro), mas o pop-up mostra só o `endereco` — layout do pop-up não é objeto desta iteração.

## Notas de teste

<Só para referência futura — não implementar agora.>

- `parse_numero_porta`: `"100"`→`"100"`; `"10A"`→`"10A"`; `"10-A"`→`"10-A"`; `"nº 10A"`→`"10A"`;
  `"s/n"`/`"S/N"`/`"sn"`/`"s.n."`/`"sem número"`→ token bruto; `"abc"`→None; `""`→None.
  **Prefixo (não fullmatch)**: `"10."`→`"10"`; `"10 apto 5"`→`"10"`; `"10, casa 2"`→`"10"`;
  `"1.578"`→`"1"` (mesmo comportamento do estrito hoje). Superconjunto: todo token aceito por
  `parse_numero_imovel` é aceito aqui — vale testar por propriedade sobre os casos do estrito.
- `normalize_sem_numero` (utilitário, recebe texto **já normalizado**): `"S N"`, `"SN"`, `"S NO"`,
  `"SEM NUMERO"` → `CANONICO_SEM_NUMERO`; `"10A"`, `"100"`, `"AV PAULISTA"` → **inalterados**
  (identidade); é idempotente (aplicar duas vezes não muda). Reexportado no `__init__.py` ao lado
  de `normalize_text`.
- `chave_numero_porta` (compõe `normalize_text` + `normalize_sem_numero` + strip): `"10a"`,
  `"10-A"`, `"10 A"` → mesma chave `"10A"`; **todas** as grafias de sem número — `"s/n"`, `"S/N"`,
  `"sn"`, `"s.n."`, `"s/nº"`, `"sem número"`, `"sem numero"` → o **mesmo token canônico**; um número
  comum (`"100"`, `"10A"`) **não** é tocado. Comportamento real da `normalize_text` **já conferido**
  (a regex casa sobre estas saídas): `"s/n"`/`"s.n."`/`"s/n°"` → `"S N"`; `"sn"` → `"SN"`;
  `"s/no"` → `"S NO"`; `"s/nº"` → `"S Nº"` (o `º` ordinal sobrevive); `"sem número"` → `"SEM NUMERO"`.
- `EnderecoLoteParse.numero_padronizado` (computed_field = `chave_numero_porta(numero_bruto)`):
  `numero_bruto="s/n"` → `"SN"`; `"10-A"` → `"10A"`; `"100"` → `"100"`. É **derivado** (muda junto
  com `numero_bruto`, não é um segundo campo de entrada). `EnderecoParse`/`EnderecoCodlogParse`
  **não** têm o campo.
- Chave dos dois lados: um imóvel gravado como `"SEM NÚMERO"` na base (coluna cacheada) é
  encontrado ao digitar `"s/n"`, e vice-versa — o `numero_padronizado` (input) e a coluna do
  catalog (base) saem da **mesma** `chave_numero_porta` (single-source).
- Cache: a coluna `chave_numero_porta` do catalog já sai **canonizada** e o `aquecer()` a toca;
  requests subsequentes não recomputam a canonicalização de "sem número".
- Localizadores: `("Rua X, 10A")`→`("Rua X","10A")`; `("Rua X, s/n")`→`("Rua X","s/n")`;
  `("12345 100")`→`("12345","100")`; contribuinte com ponto segue rejeitado no caminho codlog.
- Regressão dos parses estritos: `Rua X, 10A` → `ENDERECO` com `numero=10`/`numero_bruto="10A"`;
  `Rua X, 10.` e `Rua X, 10 apto 5` → **seguem** gerando `ENDERECO` com `numero=10` (tokens
  "sujos" que o split permissivo com fullmatch teria quebrado);
  `Rua X, s/n` → **sem** `ENDERECO`, **com** `ENDERECO_LOTE` e `LOGRADOURO` intacto (a guarda do
  `LogradouroIdentifier` aplica o parser estrito sobre o token: `10A` suprime `LOGRADOURO` como
  hoje, `s/n` não).
- Roteador: entrada de endereço gera `ENDERECO_LOTE` sempre à frente de
  `ENDERECO_CODLOG`/`ENDERECO` e atrás de `CONTRIBUINTE`.
- Matcher: recebe `numero_padronizado` (já é a chave — **não** re-normaliza) + codlog certo, e por
  prefixo acha `10`, `10A`, `100`; `numero_padronizado="SN"` acha o imóvel `SEM NÚMERO`; codlog
  fora da lista não vaza; `limite` respeitado; lista de codlogs com vários itens (`isin`); o `isin`
  casa codlog de **5 dígitos** contra a coluna `codlog5` (não contra `cd_logradouro`, que tem 6);
  linha com `cd_numero_porta` nulo ganha chave `""` e nunca casa.
- View: endereço com match fiscal exibe a seção no topo dos endereços; endereço sem match fiscal
  **não** exibe a seção (nem título vazio); clique posta `setor/quadra/lote/tipo_lote` para
  `lote_geocoder:geocodificar` e o polígono renderiza (regressão do fluxo de lote).
- `aquecer()` toca a nova coluna (log de aquecimento) e requests subsequentes não recalculam.
- `LoteAttributes`: `numero_porta`/`nome_logradouro` viram `''` quando `props` traz `None`/ausente;
  `codlog` fica `None` quando ausente; `endereco` = `"AV PAULISTA, 100"` quando ambos presentes,
  `"AV PAULISTA"` quando só o nome, `""` quando nenhum. Valores vêm **crus da base oficial** (nada
  de normalização). `LoteGeocoder._montar_attributes` popula os três a partir dos `props` da feature.
- Pop-up: com a feature trazendo logradouro+número, o `_popup_lote.html` mostra a linha do
  `endereco`; sem esses dados, a linha é **omitida** (pop-up igual ao de hoje). Regressão: o pop-up
  segue mostrando `setor.quadra.lote` + tipo + condomínio.
- Regressão 009: seções e seleção de endereço por codlog/nome intactas.

## Patches

### Patch 001 (v8) — codlog nas sugestões de endereço cadastrado (lote)

Ao buscar por **codlog + número** (ex.: `048046 100`), a seção "Endereço cadastrado (lote)"
mostrava só `logradouro, numero`, sem o codlog — o usuário não tinha como confirmar que a
sugestão correspondia ao codlog digitado. O partial passa a exibir, **após o nome do logradouro**,
o codlog no formato `(codlog: CODLOG-dv)`, com o mesmo estilo `font-mono text-base-content/60`
usado nas demais listas de sugestão.

O valor vem do `ContribuinteMatchOutput.codlog` (já disponível no output — `cd_logradouro`, 6
dígitos codlog+DV do parquet fiscal); o template **parseia** os 6 dígitos em codlog (5) + DV (1)
via `slice`, exibindo `04804-6`. **Nenhuma mudança de domínio, DTO ou matcher** — só o template
`templates/lote_matcher/partials/resultados_endereco_lote.html`.

```django
<span class="font-medium">
  {{ r.logradouro }}
  <span class="font-mono text-sm text-base-content/60">(codlog: {{ r.codlog|slice:":5" }}-{{ r.codlog|slice:"5:" }})</span>,
  {{ r.numero }}{% if r.complemento %} — {{ r.complemento }}{% endif %}
</span>
```
