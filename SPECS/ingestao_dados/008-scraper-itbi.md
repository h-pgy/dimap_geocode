---
spec: ingestao_dados/008
versao: v10
atualizado_em: 2026-08-03
testes_tdd: true
implementado: true
depende_de: ingestao_dados/006
changelog:
  - v1: versão inicial
  - v2: coluna `mes` (da aba); pasta dos originais passa a ser `data/itbi_originais/`, sobrescrita
    a cada carga e mantendo sempre a última versão de cada ano; metadado é um só, o do parquet, e
    passa a carregar os anos que falharam e o porquê; conversão de tipos com `errors="raise"` (nulo
    de conversão silenciosa é indistinguível de célula vazia); management command, settings e
    `ETAPAS` saem do escopo — esta iteração é só `services/`; DTOs da integração num módulo próprio;
    cliente HTTP com retry (`ItbiRetryPolicy`) explicitado, incluindo retry por status 5xx
  - v3: download que falha **reaproveita** o xlsx da carga anterior, quando ele existe na pasta de
    originais; o ano reaproveitado é reportado em lista própria, separada dos que falharam
  - v4: o cliente HTTP com retry sai da integração e vira utilitário reaproveitável em
    `services/utils/` (a política de retry continua sendo da ITBI, e o WFS não é migrado); a etapa
    de coleta (rede → arquivos) e a de consolidação (arquivos → parquet) viram duas classes, e o
    `run()` passa a compô-las
  - v5: a interface entre as duas etapas passa a ser **a pasta**, não a lista de anos da coleta — a
    consolidação varre `data/itbi_originais/` e não sabe o que o portal publicou, de modo que ano
    despublicado ou não baixado continua no parquet; o "reaproveitamento" some do código e vira
    consequência do desenho; o resultado reporta por etapa (baixados / no parquet, com as falhas de
    cada uma) e deriva os **anos desatualizados**
  - v6: divergência de esquema deixa de ser silenciosa — a consolidação reporta por ano as colunas
    **desconhecidas** (cabeçalho original) e as **ausentes** (nome de saída), e as duas vão para os
    metadados
  - v7: três etapas em vez de duas — entra `data/itbi_parseados/<ano>.parquet` entre o xlsx e o
    parquet consolidado. O parquet de um ano só é escrito quando aquele ano parseia inteiro, então
    xlsx novo quebrado não custa o ano: a consolidação passa a ler o último resultado **válido** de
    cada ano, não o último arquivo baixado. O resultado passa a ter um bloco por etapa e
    `anos_desatualizados` cobre "não baixou **ou** não parseou"
  - v8: o `HttpFetcher` passa a usar uma `Session` injetável (headers do consumidor, conexão
    reaproveitada) e a repassar `**kwargs` ao `get`; o snippet ganha o laço de tentativa completo
  - v9: `user_agent` e `headers` na construção do `HttpFetcher`, sem exigir que o consumidor monte
    a `Session`; a integração ITBI declara o seu User-Agent
  - v10: explicitada a montagem das peças — a integração expõe um `build_fetcher` (como o do WFS) e
    o `run()` injeta **o mesmo** fetcher no scraper e no downloader
---

# SPEC ingestao_dados/008 — Scraper das guias de ITBI pagas (portal da Fazenda → Parquet)

- [x] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como analista da DIMAP, quero as **guias de ITBI pagas** — todas as planilhas anuais publicadas na
página de acesso à informação da Fazenda — consolidadas num **único parquet** de `data/`, com ano,
mês e colunas de nome estável, para que as ações de avaliação passem a ter uma base de transações
imobiliárias do município sem ninguém baixar Excel na mão todo mês.

## Critérios de aceite

### Descoberta das planilhas (integração)

- [ ] Uma **integração nova** (§6.2) lê a página pública do portal e devolve, para cada ano
      publicado, o **ano** e a **URL absoluta** da planilha `.xlsx`. O domínio nunca vê `requests`,
      HTML nem `BeautifulSoup`.
- [ ] A varredura acontece **dentro** da `<section class="psp-agencies-content">` — não na página
      inteira. O ano de cada item vem do `<strong>` do próprio `<li>`, **não** do nome do arquivo
      (o arquivo de 2025 se chama `...(28012026)...`).
- [ ] **Só os links de Excel/xlsx entram**; os `.ods` do mesmo `<li>` são ignorados.
- [ ] **URL relativa e absoluta são tratadas pela mesma regra**: toda `href` é resolvida contra a
      URL da página, sem `if` sobre o formato do link. Hoje o ano mais recente é relativo e os
      antigos são absolutos, e isso pode inverter a qualquer publicação.
- [ ] Quando a estrutura esperada não existe (seção ausente, nenhum link de xlsx), a integração
      levanta **exceção própria** dizendo que o portal mudou — nunca `AttributeError`/`IndexError`
      vazando de dentro do parser.

### Cliente HTTP com retry — reaproveitável, em `services/utils/`

- [ ] O acesso à rede é de **um cliente só**, e ele mora em **`services/utils/`**, não dentro da
      integração: é infraestrutura de IO sem domínio (§6.1), do mesmo escopo de `io/` e
      `normalization/`. **Qualquer integração futura que precise de HTTP com retry usa este** — não
      escreve o laço de novo.
- [ ] O cliente recebe uma **política de retry por composição** (timeout, número de tentativas,
      espera entre elas, status que merecem nova tentativa) — a política é DTO, e cada consumidor
      declara a sua.
- [ ] O cliente usa uma **`Session`**, e o consumidor pode definir **`user_agent` e `headers` na
      construção** — sem precisar montar a `Session` na mão, que também é aceita por composição.
      Assim a identificação vale para todas as chamadas e a conexão é reaproveitada nos ~20
      downloads da carga.
- [ ] O cliente **repassa ao `get` os argumentos que a chamada pedir** (`stream`, `params`,
      `headers`): não precisa crescer um parâmetro novo a cada necessidade, e o `timeout` da
      política é o default que a chamada pode sobrepor.
- [ ] O retry cobre **falha de rede e status de servidor** (5xx/429): o portal responde 503 com
      frequência, e uma política que só repete em timeout deixaria a carga inteira à mercê de uma
      indisponibilidade de segundos.
- [ ] Esgotadas as tentativas, o erro sai como **exceção própria** (nunca `requests.HTTPError` cru),
      com a URL e o número de tentativas na mensagem. **A integração traduz** esse erro na sua
      própria exceção — `requests` não escapa de `services/utils/`, e o erro do utilitário não
      escapa da integração.
- [ ] Nem o scraper nem o downloader falam com `requests` por conta própria: os dois recebem o
      cliente por composição.

### Três etapas encadeadas por pasta

- [ ] A carga tem **três etapas, e cada uma é uma classe** (§7.1), encadeadas por **pastas**, não
      por objetos passados de uma para a outra:
      1. **coleta** — portal → `data/itbi_originais/<ano>.xlsx`;
      2. **parse** — cada xlsx de `itbi_originais/` → `data/itbi_parseados/<ano>.parquet`;
      3. **consolidação** — todos os parquets de `itbi_parseados/` → o parquet único de `data/`.
- [ ] **Cada etapa lê a pasta anterior e ignora o que a etapa anterior fez ou deixou de fazer.** O
      parse não sabe o que a coleta baixou; a consolidação não sabe o que o parse escreveu — cada
      uma varre o diretório e trabalha com o que houver lá.
- [ ] **Nenhuma etapa apaga arquivo.** Ano que sumiu do portal, que não baixou ou que não parseou
      continua no parquet final com o último dado bom que tiver em disco. Tirar um ano da base é
      apagar os arquivos dele.
- [ ] **Cada escrita é atômica e por ano** (helper da SPEC 006): interrompida no meio (`kill -9`,
      disco cheio), **não substitui** o arquivo anterior por um truncado nem deixa `.tmp` para trás.
- [ ] As duas pastas **não são versionadas** — são insumo reconstruível, não dado (§5). O dado é o
      parquet consolidado. E a resolução dos caminhos sai do **ponto único que resolve `data/`** em
      `services/utils/io`: nenhum `Path` para `data/` montado no script (é o que mantém o
      redirecionamento dos testes valendo).
- [ ] **O ano viaja no nome do arquivo** de ponta a ponta (`<ano>.xlsx` → `<ano>.parquet`) — é o que
      permite às etapas 2 e 3 não conhecerem o portal. Arquivo que não obedece ao padrão do nome é
      ignorado.

### Parse: uma planilha por vez, um parquet por ano

- [ ] **O parquet de um ano só é escrito quando aquele ano parseia inteiro.** Falhando (arquivo
      ilegível, valor que não converte), **nada é escrito para aquele ano** e o parquet da carga
      anterior permanece — é ele que a consolidação vai usar.
- [ ] **A falha de um ano não interrompe o parse dos demais**, e volta no resultado com o erro que a
      causou.
- [ ] De cada planilha entram **apenas as abas no padrão `MÊS-ANO`** (`JAN-2026`, `ABR_2026`,
      `DEZ-2015`…), aceitando as variações de separador que o portal usa. Aba fora do padrão
      (resumo, notas, planilha vazia) é ignorada em silêncio.
- [ ] As colunas são renomeadas por um **dicionário único, constante do módulo** — a única fonte de
      verdade sobre o nome de saída de cada coluna. O casamento entre o cabeçalho da planilha e a
      chave do dicionário usa a **normalização única do projeto** (§6.1) nos dois lados, não
      igualdade literal.
- [ ] Coluna da planilha que **não está** no dicionário é descartada; coluna do dicionário
      **ausente** na aba entra nula — um ano com esquema diferente não derruba a carga.
- [ ] **Descartar e preencher com nulo não acontece em silêncio**: o parse reporta, **por ano**, as
      duas divergências de esquema, e elas vão para os metadados junto com o resto:
      - **colunas desconhecidas** — estavam na planilha e não no dicionário, com o **cabeçalho
        exato** como veio (é o texto que se cola no `MAPA_COLUNAS` para adotá-la);
      - **colunas ausentes** — estavam no dicionário e não na planilha, pelo **nome de saída** (é a
        coluna que sai nula no parquet para aquele ano).

      Sem isso, o portal acrescentar uma coluna nova seria invisível, e uma coluna que sumiu de um
      ano ficaria indistinguível de uma coluna que existe e está vazia.
- [ ] As colunas numéricas e a de data são **convertidas explicitamente, com erro estrito**: valor
      que não converte **levanta** e derruba o parse daquele ano. Conversão silenciosa para nulo é
      proibida — nulo de parser e célula vazia ficariam indistinguíveis no parquet.
- [ ] O parquet do ano tem, além das colunas mapeadas: **`ano`** (do nome do arquivo, que veio do
      `<strong>` do portal), **`mes`** (`1`–`12`, do nome da aba) e **`is_financiamento`** (`False`
      quando o tipo de financiamento é nulo ou vazio, `True` caso contrário).

### Consolidação

- [ ] A consolidação **concatena os parquets de `itbi_parseados/`** num **único parquet** em `data/`
      — é ele o artefato que será consumido; xlsx e parquets por ano são insumo.
- [ ] Ela **não interpreta nada**: os parquets por ano já vêm com o esquema final, escritos por esta
      mesma carga ou por uma anterior. Não há renomeação, tipagem nem tratamento de falha por ano
      aqui.
- [ ] **Se `itbi_parseados/` estiver vazia, o `run()` levanta** — parquet vazio nunca sobrescreve o
      bom.

### Contrato e observabilidade

- [ ] O script segue o **contrato `ScriptRunner`** (`run(config, *, verbose=False, manual=True)`,
      declaração conferida pelo `mypy` e pela varredura de `services/scripts/`).
- [ ] **Um registro de metadados só, o do parquet.** Nenhum xlsx tem entrada própria no JSON de
      metadados — o artefato desta carga é o parquet consolidado.
- [ ] **A falha de um ano não aborta a carga**, em nenhuma etapa: link podre e 503 não impedem os
      outros anos de baixar; arquivo ilegível e valor que não converte não impedem os outros de
      parsear. O ano falho **continua no parquet** com o último dado bom que tiver.
- [ ] **O DTO de resultado responde, sozinho, "o que aconteceu nesta carga"** — e é ele que vai
      para o JSON de metadados, porque é lá que se olha dias depois, sem log de terminal, e é dele
      que sai o log do daemon. **Cada etapa reporta o que sabe**, em bloco próprio:
      - **coleta:** os anos que **baixou** e, por ano, o erro dos que **não conseguiu baixar**;
      - **parse:** os anos que **parseou**, por ano o erro dos que **falharam**, e por ano as
        **divergências de esquema** (coluna desconhecida, coluna ausente);
      - **consolidação:** os anos que **entraram no parquet** e o total de registros.
- [ ] Desses blocos sai a resposta que interessa ao operador — **quais anos do parquet estão
      desatualizados**, isto é, estão lá com dado de uma carga anterior porque não baixaram ou não
      parsearam agora. Ela aparece no resultado **pronta**, para ninguém ter que cruzar listas na
      mão.
- [ ] `--verbose` **apura e devolve mais** (regra da SPEC 006): com ele, o resultado traz a
      contagem de **linhas por ano**.

## Contexto e decisões de arquitetura

Mexe só na camada de dados, e **só em `services/`**: uma integração nova, um script de carga novo e
uma extensão pequena em dois utilitários (`io` e `metadados`). Não toca `apps/`, views, templates
nem banco.

**A fonte é um scraper, e por isso entra em `services/integrations/` (§6.2).** É a mesma porta do
WFS: DTOs Pydantic na saída, exceções próprias, tudo reexportado no `__init__.py`. O que justifica o
isolamento aqui é mais forte que no WFS — a página é gerada por um CMS sem `id` nem HTML semântico,
então **a estrutura vai mudar**; quando mudar, o conserto é um arquivo da integração e o script não
fica sabendo. Pelo mesmo motivo a integração **levanta erro próprio** quando não encontra a seção:
mudança de layout tem que aparecer como "o portal mudou", não como `NoneType has no attribute`.

**O cliente HTTP com retry é utilitário, não peça da integração.** Repetir requisição com
backoff, traduzir erro de rede e desistir depois de N tentativas não tem nada de ITBI nem de WFS: é
IO genérico, o mesmo escopo que já justifica `services/utils/io/` e `services/utils/normalization/`
(§6.1). Deixá-lo dentro de `integrations/itbi/` seria a segunda cópia do laço no projeto, e a
terceira nasceria com a próxima fonte — o mesmo erro que a normalização única existe para evitar.
Então: **o mecanismo vive em `services/utils/`; a política é do consumidor**, injetada por
composição.

**A política de retry da ITBI é própria — e é onde mora a diferença para o WFS.** O `WfsRetryPolicy`
repete em `Timeout` e `ConnectionError`; o portal da Fazenda responde **503** — foi o que ele
devolveu nas tentativas de leitura durante a redação desta SPEC. Repetir só em exceção de rede não
cobriria o modo de falha real desta fonte, então a integração ITBI declara também os **status que
merecem nova tentativa**, com timeout maior (são arquivos, não JSON de página). Os valores são da
ITBI; o laço que os obedece é de todo mundo.

**Quem monta as peças é o `run()`, e o fetcher é um só.** A integração oferece um `build_fetcher`
com os defaults dela (política e User-Agent), no mesmo papel do `build_fetcher` do WFS; o `run()` o
chama uma vez e injeta **o mesmo cliente** no scraper e no downloader. Um fetcher por classe daria
duas `Session`, e o argumento de reaproveitar conexão e headers deixaria de valer.

**Cada camada traduz o erro da de baixo.** O utilitário levanta a exceção *dele* (`requests` não
escapa de `services/utils/`); a integração a traduz na exceção *dela* (o erro do utilitário não
escapa de `integrations/itbi/`); o script decide o que fazer com ela. Sem isso, o pacote de baixo
vaza para cima e trocar o cliente HTTP viraria refactor de três camadas.

**Coletar, parsear e consolidar são três classes (§7.1).** Elas mudam por razões diferentes — a
coleta quando o portal muda (layout, link podre, 503); o parse quando a planilha muda (aba nova,
coluna renomeada, valor que não converte); a consolidação, praticamente nunca. Juntá-las produziria
a classe que faz rede e pandas ao mesmo tempo, impossível de testar sem dublê de rede para exercitar
o parser. Separadas, o parse recebe **um diretório de xlsx** e a consolidação **um diretório de
parquets**: nenhuma das duas sabe que existe rede, e o teste de ambas é um punhado de arquivos
sintéticos num `tmp_path`. O `run()` compõe as três.

**Descobrir e baixar também são separados**, e ficam na integração: o layout da página e o destino
em disco mudam por motivos distintos, e o teste do parser roda sobre uma string de HTML.

**`urljoin` sempre, para todo link.** Absoluto passa intacto, relativo resolve contra a página. Um
`if href.startswith("http")` seria uma regra a mais para manter e quebraria no dia em que o portal
publicar um link protocol-relative.

**O ano vem do `<strong>`; o mês, da aba.** O nome do arquivo mente (o de 2025 traz a data de
publicação, `28012026`), e o rótulo do portal é o que o publicador declara ser aquele arquivo. O
padrão da aba também captura um ano — ele serve para **reconhecer** a aba, não para preencher a
coluna; `ano` é sempre o do portal, e essa é a regra para quem for implementar.

**A pasta é a interface entre as etapas — e é o que torna o parquet estável.** Cada etapa varre o
diretório que a anterior alimenta e trabalha com o que houver lá; nenhuma recebe lista de anos da
anterior. A consequência é a que se quer: **o portal despublicar 2006–2009 não apaga 2006–2009 do
parquet**, porque os arquivos continuam em disco. Se uma etapa consumisse o resultado da outra, o
histórico do parquet passaria a depender do que o CMS da Prefeitura resolve manter no ar — uma base
de vinte anos encolhendo por decisão de terceiro, sem ninguém perceber.

**São duas pastas porque o xlsx bom é destruído antes de a gente saber se ele presta.** Com uma
pasta só, o download promove o arquivo novo por cima do antigo e a validação viria depois: se a
planilha nova estiver corrompida ou com um valor que não converte, o ano é perdido — o dado bom da
carga anterior já não existe mais. Guardar o resultado **parseado** de cada ano num parquet próprio
resolve pela ordem das operações: o xlsx novo é escrito e o parquet do ano **só é substituído
quando o parse daquele ano termina inteiro**. O que a consolidação lê é sempre o último resultado
**válido** de cada ano, não o último arquivo baixado.

**Cada pasta responde a uma pergunta diferente, e as duas ficam.** `itbi_originais/` é o que o
portal entregou — é lá que se abre o Excel para descobrir por que o parser quebrou; `itbi_parseados/`
é o último dado bom de cada ano. Nenhuma é versionada (`.gitignore`): são insumo reconstruível, e o
dado versionado é o parquet consolidado (§5, mesma linha da 006 — `data/` é estado, não histórico).

Com isso, **falha deixou de ser caso especial em qualquer etapa**: o ano simplesmente não é
atualizado naquele estágio e a etapa seguinte encontra o artefato anterior onde ele sempre esteve.
Não há lógica de fallback em lugar nenhum — nenhum `if existe: usa o velho`.

**Nenhuma etapa apaga arquivo, e o parquet é a projeção da pasta de parseados.** Tirar um ano da
base é apagar os arquivos dele, não deixar de publicá-lo no portal.

**O nome do arquivo é o contrato entre as etapas.** A coleta grava o ano do `<strong>` no nome do
xlsx e o parse o repassa ao nome do parquet (`<ano>.xlsx` → `<ano>.parquet`). É o que permite as
etapas seguintes não conhecerem o portal e ainda assim saberem a que ano cada arquivo pertence — e é
a razão de o nome ser derivado do ano desde o começo, não do nome que o portal deu ao arquivo (que
tem espaço, `%28` e muda a cada publicação).

**Divergência de esquema é aviso, não erro — mas precisa ser vista.** Descartar coluna desconhecida
e preencher com nulo a que faltou é o que impede um ano fora do padrão de derrubar a carga; o preço
é que a base pode estar perdendo uma coluna nova do portal, ou publicando nulo onde há dado, sem que
nada quebre. Como o registro por ano custa dois dicionários pequenos e responde exatamente "o que
mudou na planilha", ele entra nos metadados sempre — não só com `--verbose`, que é justamente a
execução que ninguém está olhando.

**O que a carga informa é por etapa, e a resposta útil é derivada.** Cada etapa reporta só o que
sabe (a coleta, o que baixou; o parse, o que parseou e as divergências de esquema; a consolidação, o
que entrou no parquet). Cruzando os blocos sai a pergunta que o operador faz de fato — *quais anos
do parquet estão desatualizados*, ou seja, os que estão lá sem terem baixado **e** parseado nesta
carga —, e o resultado já a entrega pronta em vez de deixar quem lê o log do daemon fazer a
interseção na cabeça.

**Conversão de tipos com erro estrito.** Vinte anos de planilha manual garantem a mesma coluna
vindo texto num ano e número em outro; sem conversão declarada o parquet sai com colunas `object` e
não se filtra por valor nem por período. Mas a conversão é `errors="raise"`: com `coerce`, o valor
que o parser não entendeu vira nulo e fica **indistinguível de célula vazia** — o dado degrada em
silêncio e o defeito só aparece numa análise, meses depois. Estrito, o ano cai inteiro, o erro vai
para os metadados e o parser se ajusta na iteração seguinte. É a troca certa: dado que falta é
visível, dado errado não.

**Um metadado, o do parquet.** O artefato desta carga é o parquet consolidado — é ele que será
consumido, e é dele que se quer saber quando foi atualizado. Registrar cada xlsx encheria o JSON de
vinte entradas de insumo descartável. Como a carga pode ter sucesso parcial, o registro de sucesso
**carrega as falhas por ano**: para isso o helper de `services/utils/metadados` ganha um campo
opcional de detalhes, aditivo — nenhum registro existente muda de forma, e a SPEC 007 não é editada
(quem documenta a extensão é esta SPEC).

**Falha parcial não aborta.** São ~20 arquivos num portal que responde 503; abortar tudo porque o
link de 2011 apodreceu significaria nunca mais atualizar 2026. O piso é "nenhum ano" — aí levanta, e
o registro de falha da 007 faz seu trabalho sem que o parquet bom seja sobrescrito.

**Nesta iteração não há management command.** A porta de entrada é o `run()` do script, que já é o
contrato. O comando nasce junto do app que vai consumir o dado (amostras para avaliação), e é lá que
a URL e os timeouts passam a vir de `settings` (§3.3). Até então eles são **default no `Config`** —
exatamente a regra da SPEC 006 para o que é constante do próprio script.

**Duas dependências novas:** `beautifulsoup4` (parser da página, sobre o backend `html.parser` da
stdlib — sem `lxml`) e `openpyxl` (o pandas não lê `.xlsx` sem ele). Escrever o parser com
`html.parser` na mão seria uma máquina de estados frágil sobre HTML não-semântico — descartado.

## Peças de referência a compor

- `@services/utils/io` → `escrever_atomico` (download e escrita de parquet, um lugar só),
  `write_parquet`/`write_parquet_to_data` e `config.data_dir()`. Ganha duas extensões, ambas no
  mesmo lugar que já sabe o que é `data/`: a **resolução de subpasta** (para `itbi_originais/` e
  `itbi_parseados/`) e a **leitura/escrita de DataFrame** — na mesma forma dos helpers de hoje (um
  par `..._to_data` + um que recebe a pasta). Pelo mesmo motivo da 006, se o script resolvesse isso,
  o próximo nasceria sem atomicidade.
- `@services/utils/metadados` → `registrar_execucao` / `Registro.sucesso()`: envolvem o trabalho do
  runner e gravam sucesso ou falha. Ganham o campo opcional de **detalhes**, onde entram as falhas
  por ano. O runner não ganha `try/except`.
- `@services/scripts/contrato.py` → `ScriptRunner`: a assinatura única do `run()`, conferida pelo
  `mypy` e pela varredura por descoberta de `tests/services/scripts/test_contrato.py` — que passa a
  cobrir este script sozinha, sem ninguém editá-la.
- `@services/utils/normalization` → `normalize_text`: casamento dos cabeçalhos e reconhecimento do
  padrão das abas. Ela já colapsa `-`, `_` e `/` em espaço, então `JAN-2026`, `ABR_2026` e `Jan/2026`
  caem todos em `JAN 2026` — o padrão das abas é uma regex sobre o texto normalizado, não três.
- `@services/integrations/wfs` → o **molde** do módulo de integração: `models.py` com os DTOs,
  `exceptions.py` com a árvore de erros próprios, cliente callable que recebe a política de retry no
  `__init__`, `__init__.py` que só reexporta. Compor o padrão, não o código — CQL e paginação não
  têm equivalente aqui. O `_request_with_retries`/`_handle_network_failure` do `WfsFetcher` é a
  **referência do laço** que vira utilitário genérico: mesma forma (range finito, jitter entre
  tentativas, tradução do erro de rede), acrescida do retry por status. O `WfsFetcher` **não é
  alterado** por esta SPEC.
- `@.claude/skills/management-commands/SKILL.md` → anatomia do script (`models.py` / `extractor.py`
  / `constants.py` / `runner.py` / `__init__.py`) e as regras de contrato e metadados. A parte de
  comando fica para a SPEC do app consumidor.
- `@.gitignore` → já ignora `data/*.tmp` (SPEC 006); ganha `data/itbi_originais/` e
  `data/itbi_parseados/`.

## Snippets sugeridos

```python
# services/scripts/itbi/constants.py — o dicionário único de saída, na ordem do parquet.
# Chave = cabeçalho legível da planilha; o casamento normaliza os dois lados (§6.1),
# porque a fonte tem acento, parênteses e ao menos um typo ("Regsitro").
MAPA_COLUNAS: dict[str, str] = {
    "N° do Cadastro (SQL)": "sql_num",
    "Nome do Logradouro": "logradouro_nome",
    "Número": "numero_porta",
    "Complemento": "complemento_endereco",
    "Referência": "referencia_endereco",
    "CEP": "cep",
    "Natureza de Transação": "natureza_transacao",
    "Valor de Transação (declarado pelo contribuinte)": "valor_transacao_declarado",
    "Data de Transação": "data_transacao",
    "Valor Venal de Referência": "valor_venal_de_referencia",
    "Proporção Transmitida (%)": "percentual_transmitido",
    "Valor Venal de Referência (proporcional)": "valor_venal_de_referencia_proporcional",
    "Base de Cálculo adotada": "valor_adotado_base_de_calculo",
    "Tipo de Financiamento": "financiamento_tipo",
    "Valor Financiado": "financiamento_valor",
    "Cartório de Regsitro": "cartorio",
    "Matrícula do Imóvel": "matricula",
    "Situação do SQL": "sql_situacao",
    "Área do Terreno (m2)": "area_terreno",
    "Testada (m)": "testada",
    "Fração Ideal": "fracao_ideal",
    "Área Construída (m2)": "area_construida",
    "Uso (IPTU)": "uso",
    "Descrição do uso (IPTU)": "uso_desc",
    "Padrão (IPTU)": "padrao_construtivo",
    "Descrição do padrão (IPTU)": "padrao_construtivo_desc",
    "ACC (IPTU)": "ano_construcao_corrigido",
}

# O que NÃO é texto. Conversão SEMPRE com errors="raise": com coerce, valor que o parser
# não entendeu viraria nulo e ficaria indistinguível de célula vazia.
COLUNAS_NUMERICAS: tuple[str, ...] = (
    "valor_transacao_declarado",
    "valor_venal_de_referencia",
    "percentual_transmitido",
    "valor_venal_de_referencia_proporcional",
    "valor_adotado_base_de_calculo",
    "financiamento_valor",
    "area_terreno",
    "testada",
    "fracao_ideal",
    "area_construida",
    "ano_construcao_corrigido",
)
COLUNAS_DATA: tuple[str, ...] = ("data_transacao",)

MESES: tuple[str, ...] = (
    "JAN",
    "FEV",
    "MAR",
    "ABR",
    "MAI",
    "JUN",
    "JUL",
    "AGO",
    "SET",
    "OUT",
    "NOV",
    "DEZ",
)
# Sobre o texto JÁ normalizado: normalize_text colapsa "-", "_" e "/" num espaço.
# O ano capturado aqui só reconhece a aba — a coluna `ano` vem sempre do portal.
PADRAO_ABA = re.compile(rf"^({'|'.join(MESES)}) (\d{{4}})$")

# Duas pastas: o que o portal entregou, e o último resultado BOM de cada ano.
PASTA_ORIGINAIS: str = "itbi_originais"
PASTA_PARSEADOS: str = "itbi_parseados"

# O nome do arquivo é o contrato entre as etapas: cada uma grava o ano nele e a seguinte
# lê o ano de lá — e por isso não precisa conhecer nem o portal nem a etapa anterior.
NOME_XLSX: str = "itbi_{ano}.xlsx"
NOME_PARQUET: str = "itbi_{ano}.parquet"
PADRAO_NOME_XLSX = re.compile(r"^itbi_(\d{4})\.xlsx$")
PADRAO_NOME_PARQUET = re.compile(r"^itbi_(\d{4})\.parquet$")
```

```python
# services/utils/http/ — o laço de retry, sem domínio nenhum: a próxima integração usa este.
class HttpRetryPolicy(BaseModel):
    request_timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_wait_min_seconds: float = 1.0
    retry_wait_max_seconds: float = 5.0
    # O WfsFetcher só repete em exceção de rede; portais de CMS falham por status.
    status_para_retry: tuple[int, ...] = ()


class HttpFetcher:
    """Callable: GET com retry. Devolve a resposta; quem a interpreta é o chamador."""

    def __init__(
        self,
        policy: HttpRetryPolicy,
        *,
        session: Session | None = None,
        user_agent: str | None = None,
        headers: Mapping[str, str] | None = None,
        verbose: bool = False,
    ) -> None:
        self._policy = policy
        # Session e não requests.get solto: os headers valem para todas as chamadas e a
        # conexão é reaproveitada nos ~20 downloads da carga.
        self._session = session or Session()
        if user_agent is not None:
            self._session.headers["User-Agent"] = user_agent
        if headers:
            self._session.headers.update(headers)  # depois: header cru vence o atalho
        self._verbose = verbose

    def __call__(self, url: str, **kwargs: Any) -> Response:
        # kwargs vai direto para o session.get: stream, params, headers da chamada.
        kwargs.setdefault("timeout", self._policy.request_timeout_seconds)
        for tentativa in range(self._policy.max_retries + 1):  # range FINITO → sem loop infinito
            resposta = self._tentar(url, tentativa, **kwargs)
            if resposta is not None:
                return resposta
        raise AssertionError("loop de retry terminou sem retornar nem levantar")

    def _tentar(self, url: str, tentativa: int, **kwargs: Any) -> Response | None:
        """A resposta boa, ou None quando ainda há tentativa; esgotado, levanta."""
        try:
            resposta = self._session.get(url, **kwargs)
        except (Timeout, ConnectionError) as exc:
            self._esperar_ou_desistir(url, repr(exc), tentativa)
            return None

        if resposta.status_code in self._policy.status_para_retry:
            self._esperar_ou_desistir(url, f"HTTP {resposta.status_code}", tentativa)
            return None

        try:
            resposta.raise_for_status()  # status fora da lista: definitivo, repetir não ajuda
        except HTTPError as exc:
            raise HttpStatusError(f"{url}: HTTP {resposta.status_code}") from exc
        return resposta

    def _esperar_ou_desistir(self, url: str, motivo: str, tentativa: int) -> None:
        total = self._policy.max_retries + 1
        if self._verbose:
            print(f"HTTP falha ({tentativa + 1}/{total}) em {url}: {motivo}")
        if tentativa >= self._policy.max_retries:
            raise HttpFetchError(f"{url}: {motivo} após {total} tentativas")
        time.sleep(
            random.uniform(
                self._policy.retry_wait_min_seconds,
                self._policy.retry_wait_max_seconds,
            )
        )
```

```python
# services/integrations/itbi/models.py — DTOs num módulo só; nada de schema solto no scraper.
# A política é da ITBI (valores); o laço que a obedece é de services/utils/http.
RETRY_ITBI: HttpRetryPolicy = HttpRetryPolicy(
    request_timeout_seconds=60.0,  # são arquivos, não JSON de página
    status_para_retry=(429, 500, 502, 503, 504),
)

# Identificar o cliente é cortesia com um portal público — e alguns CMS recusam UA vazio.
USER_AGENT_ITBI: str = "DIMAP GeoCoder (uso interno PMSP)"


# services/integrations/itbi/utils.py — o mesmo papel do build_fetcher do WFS: a integração
# entrega o cliente já com os defaults DELA, e o script não remonta isso campo a campo.
def build_fetcher(config: ItbiPortalConfig, *, verbose: bool = False) -> HttpFetcher:
    return HttpFetcher(config.retry, user_agent=USER_AGENT_ITBI, verbose=verbose)


class ItbiPortalConfig(BaseModel):
    url_pagina: str = URL_PAGINA_ITBI
    retry: HttpRetryPolicy = RETRY_ITBI


class PlanilhaItbi(BaseModel):
    ano: int
    url: str
```

```python
# services/integrations/itbi/downloader.py — atômico: uma queda no meio não substitui
# o xlsx do ano por um truncado (SPEC 006).
class ItbiPlanilhaDownloader:
    def __init__(self, fetcher: Callable[..., Response]) -> None:
        self._fetcher = fetcher

    def __call__(self, planilha: PlanilhaItbi, destino: Path) -> Path:
        # O erro do utilitário morre aqui: para fora deste pacote só sai exceção da ITBI.
        try:
            resposta = self._fetcher(planilha.url, stream=True)
        except HttpFetchError as exc:
            raise ItbiDownloadError(f"planilha de {planilha.ano}: {exc}") from exc
        return escrever_atomico(destino, lambda tmp: self._gravar(resposta, tmp))
```

```python
# services/scripts/itbi/runner.py — o run() COMPÕE as três etapas; um metadado só, o do parquet
def run(config: ItbiConfig, *, verbose: bool = False, manual: bool = True) -> ItbiResult:
    originais = subpasta_de_data(PASTA_ORIGINAIS)
    parseados = subpasta_de_data(PASTA_PARSEADOS)

    # UM fetcher para as duas chamadas: é o que faz a Session valer alguma coisa —
    # mesmos headers e mesma conexão para a página e para os ~20 downloads.
    fetcher = build_fetcher(config.portal, verbose=verbose)
    coletor = ItbiColetor(
        ItbiPortalScraper(fetcher),
        ItbiPlanilhaDownloader(fetcher),
    )

    with registrar_execucao(OUTPUT_FILENAME, manual=manual) as registro:
        coleta = coletor(config)                                      # portal    → xlsx
        parse = ItbiParser()(originais, parseados)                    # xlsx      → parquet/ano
        consolidacao = ItbiConsolidador()(parseados)                  # parquet/ano → parquet único
        output_path = write_dataframe_to_data(consolidacao.dados, OUTPUT_FILENAME)

        resultado = ItbiResult(
            coleta=coleta.stats,
            parse=parse.stats,
            consolidacao=consolidacao.stats,
            output_path=output_path,
            linhas_por_ano=consolidacao.linhas_por_ano if verbose else None,
        )
        # Sucesso parcial é sucesso — mas o que ficou velho, e o que caiu, tem que
        # sobreviver ao terminal: é daqui que sai o log do daemon dias depois.
        registro.sucesso(
            registros=resultado.consolidacao.total_records,
            detalhes=resultado.para_metadados(),
        )

    return resultado


# services/scripts/itbi/models.py — um bloco por etapa, e a pergunta do operador derivada deles
class ItbiResult(BaseModel):
    coleta: ColetaStats            # anos_baixados, falhas_por_ano
    parse: ParseStats              # anos_parseados, falhas_por_ano, divergências de esquema
    consolidacao: ConsolidacaoStats  # anos_no_parquet, total_records
    output_path: Path
    linhas_por_ano: dict[int, int] | None = None  # só apurado com verbose

    @property
    def anos_desatualizados(self) -> list[int]:
        """No parquet com dado de uma carga anterior: não baixou OU não parseou agora."""
        atualizados = set(self.coleta.anos_baixados) & set(self.parse.anos_parseados)
        return sorted(set(self.consolidacao.anos_no_parquet) - atualizados)


_contrato: ScriptRunner[ItbiConfig, ItbiResult] = run
```

```python
# services/scripts/itbi/coletor.py — ETAPA 1: portal → arquivos na pasta. Não abre planilha.
# Não apaga nada, e não decide o que entra no parquet: só atualiza o que conseguir.
class ItbiColetor:
    def __init__(
        self,
        scraper: Callable[[ItbiPortalConfig], list[PlanilhaItbi]],
        downloader: Callable[[PlanilhaItbi, Path], Path],
    ) -> None:
        self._scraper = scraper
        self._downloader = downloader

    def __call__(self, config: ItbiConfig) -> ColetaItbi:
        return self.pipeline(config)

    def _baixar(self, planilha: PlanilhaItbi, pasta: Path) -> None:
        try:
            self._downloader(planilha, pasta / NOME_XLSX.format(ano=planilha.ano))
            self._baixados.append(planilha.ano)
        except ItbiIntegrationError as exc:
            # Sem fallback: o xlsx da carga anterior continua em disco e o parse vai
            # encontrá-lo sozinho. Aqui só se registra que este ano não atualizou.
            self._falhas[planilha.ano] = f"{type(exc).__name__}: {exc}"
```

```python
# services/scripts/itbi/parser.py — ETAPA 2: um xlsx por vez → um parquet por ano.
# NÃO conhece o portal nem a coleta: parseia o que estiver em disco.
class ItbiParser:
    def __call__(self, originais: Path, parseados: Path) -> ParseItbi:
        return self.pipeline(originais, parseados)

    def _parsear(self, originais: Path, parseados: Path) -> None:
        for ano, xlsx in sorted(anos_em_disco(originais, PADRAO_NOME_XLSX).items()):
            try:
                quadro = self._ler_planilha(ano, xlsx)
            except ValueError as exc:
                # O parquet do ano NÃO é tocado: a carga anterior continua valendo, e é
                # ela que a consolidação vai usar. Vinte anos de planilha manual —
                # abortar porque 2011 parou de converter seria nunca mais atualizar 2026.
                self._falhas[ano] = f"{type(exc).__name__}: {exc}"
                continue
            # Só chega aqui o ano que parseou INTEIRO: a escrita é a última operação.
            write_dataframe(quadro, NOME_PARQUET.format(ano=ano), folder=parseados)
            self._parseados.append(ano)
```

```python
# services/scripts/itbi/consolidador.py — ETAPA 3: parquets por ano → parquet único.
# Não interpreta nada: os insumos já vêm com o esquema final, escritos por esta carga ou
# por uma anterior. É isso que impede o parquet de encolher quando o portal despublica um
# ano ou quando a planilha nova vem quebrada.
class ItbiConsolidador:
    def __call__(self, parseados: Path) -> ConsolidacaoItbi:
        return self.pipeline(parseados)

    def _consolidar(self, parseados: Path) -> ...:
        por_ano = anos_em_disco(parseados, PADRAO_NOME_PARQUET)
        if not por_ano:
            raise ItbiCargaVaziaError("nenhum ano parseado em disco: parquet anterior preservado")
        return pd.concat([read_dataframe(arquivo) for _, arquivo in sorted(por_ano.items())])
```

## Fora de escopo

- **Management command, leitura de `settings` e entrada no `ETAPAS`/daemon.** Esta iteração é só
  `services/`; a orquestração nasce com o app de **amostras para avaliação**, que é quem vai
  consumir o dado.
- **Consumir** o dado: catálogo em memória, matching de SQL, geocodificação dos endereços do ITBI,
  amostragem de ofertas — tudo isso é ação (§3.5) e vem em SPEC própria.
- Deduplicação, detecção de transações revisadas e validação de regra de negócio sobre valores.
  Esta SPEC entrega a base bruta, tipada e renomeada.
- **Migrar o `WfsFetcher` para o cliente HTTP de `services/utils/`.** O laço genérico nasce aqui e o
  WFS segue com o seu, intocado: a migração mexeria em quatro scripts de carga já entregues, por
  ganho nenhum nesta iteração. A duplicação é conhecida e deliberada, e some quando alguém tiver
  motivo para tocar o WFS.
- Arquivos **`.ods`** e qualquer outra publicação da mesma página.
- Carga do parquet em banco/PostGIS, API e interface web.
- Baixar só o que mudou (`If-Modified-Since`, hash do arquivo): 20 downloads por carga são baratos
  perto do custo de manter cache de invalidação — se doer, entra por patch.

## Testes (TDD)

- `test_scraper_extrai_ano_do_strong_e_resolve_url_relativa` — sobre um HTML fixture com um `<li>`
  de href relativo e outro absoluto (e um `.ods` em cada): saem duas planilhas, com o ano do
  `<strong>`, ambas as URLs absolutas, e nenhum `.ods`.
- `test_scraper_sem_secao_esperada_levanta_erro_proprio` — página sem
  `section.psp-agencies-content` levanta a exceção da integração, não `AttributeError`. É a borda
  que o CMS vai empurrar um dia.
- `test_http_fetcher_repete_em_503_e_levanta_erro_proprio_ao_esgotar` — sobre o cliente de
  `services/utils/`: um transporte dublê que devolve 503 é repetido até o limite da política e
  termina em exceção própria; 503 seguido de 200 devolve o 200. Fixa o modo de falha real desta
  fonte no lugar onde ele é reaproveitável.
- `test_parser_le_apenas_abas_no_padrao_mes_ano_e_deriva_mes` — xlsx sintético com `JAN-2026`,
  `ABR_2026` e `RESUMO`: só as duas primeiras entram, as duas variações de separador são
  reconhecidas e a coluna `mes` sai `1` e `4`.
- `test_parser_renomeia_colunas_e_deriva_is_financiamento` — o parquet do ano sai com os nomes do
  `MAPA_COLUNAS`, `ano` vindo do nome do arquivo, `is_financiamento` `False` para tipo de
  financiamento vazio/nulo e `True` caso contrário.
- `test_divergencia_de_esquema_entra_no_parquet_e_nos_metadados` — um ano com uma coluna a mais e
  outra a menos: a desconhecida não aparece no parquet, a ausente sai nula, o ano entra normalmente
  e as duas divergências chegam aos metadados — a desconhecida com o cabeçalho original, a ausente
  com o nome de saída.
- `test_xlsx_quebrado_nao_sobrescreve_o_parquet_do_ano` — o xlsx novo de um ano tem valor que não
  converte, e já existe o parquet daquele ano de uma carga anterior: o parquet do ano **não é
  tocado**, o ano continua no parquet final com o dado bom antigo, e aparece em
  `falhas_por_ano` do parse e em `anos_desatualizados`. É o teste do motivo de existirem duas
  pastas — sem ele, a etapa de parse "otimizada" para escrever antes de validar passaria.
- `test_ano_despublicado_ou_nao_baixado_continua_no_parquet` — o portal publica só 2025, mas há
  2024 e 2025 em disco: os **dois** entram no parquet, e 2024 sai em `anos_desatualizados`. Idem
  para um ano cujo download falha. Fixa a independência entre as etapas — se alguém voltar a passar
  a lista da coleta adiante, quebra aqui.
- `test_carga_sem_nenhum_ano_parseado_levanta` — pasta de parseados vazia: o `run()` levanta e o
  parquet consolidado anterior fica intacto.
- `test_run_sobrescreve_sem_acumular` — duas execuções seguidas sobre a mesma fonte produzem o mesmo
  parquet, e cada pasta termina com **um arquivo por ano**, o da última carga — sem cópia extra e
  sem `.tmp`.

## Patches

_Nenhum patch registrado até o momento._
