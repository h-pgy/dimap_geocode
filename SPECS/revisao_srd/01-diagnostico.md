# Diagnóstico do CLAUDE.md — DIMAP GeoCoder

> **STATUS (2026-07-31): implementado e encerrado.** As recomendações deste diagnóstico foram
> aplicadas — com as reversões e ajustes decididos pelo desenvolvedor, registrados no §8.1.1 e nas
> respostas em conversa. O CLAUDE.md novo **já está em vigor** na raiz do projeto e é a única fonte
> de verdade. Este arquivo fica **apenas como registro histórico** do raciocínio: não é para ser
> mantido em dia, corrigido ou consultado como norma. Onde ele divergir do CLAUDE.md, vale o
> CLAUDE.md.

Data: 2026-07-07. Base da análise: `CLAUDE.md` (584 linhas), as 10 skills de `.claude/skills/`,
a estrutura real de arquivos do projeto, `config/settings.py` e `pyproject.toml` (checagens
pontuais para confirmar divergências).

O CLAUDE.md é lido **em toda sessão de agente**. Cada linha dele custa contexto em todas as
conversas — enquanto uma skill só é carregada quando o assunto dela aparece. O critério do
diagnóstico é, portanto: **no CLAUDE.md fica o que é preciso saber sempre** (domínio, princípios
inegociáveis, fronteiras de camada, convenções transversais); **o que é preciso saber às vezes
vira skill referenciada**; e **o que é produto/planejamento vive em SPECS/ ou docs**.

---

## 1. Conteúdos que NÃO deveriam estar no CLAUDE.md

### 1.1 §9 "Fluxo de Dados (ponta a ponta)" — duplicação interna com §1

O diagrama ASCII de ~60 linhas do §9 narra o mesmo fluxo que a seção "O fluxo da aplicação - UX"
do §1 já narra em prosa (busca → roteamento → três desfechos → mapa → salvar em projeto). São
duas versões do mesmo conteúdo que precisam ser mantidas em sincronia manualmente — e já
divergem: o §9 descreve o fluxo de "salvar no projeto" e "reabrir projeto" como se existissem,
mas os apps `accounts` e `projects` ainda não foram criados.

**Recomendação:** manter **uma** descrição do fluxo, curta, na visão geral. O detalhe fino de
cada fluxo já vive nas SPECs (14 SPECs só em `SPECS/roteamento_busca/`), que são a fonte de
verdade por iteração.

### 1.2 §14 "Roadmap por Fase" — planejamento de produto, não instrução de agente

Problemas concretos:

- **Bug de numeração:** existem duas seções `## 14.` ("Regras Críticas" e "Roadmap por Fase").
- **Está desatualizado e vai desatualizar de novo:** os itens 1–3 da fase 1 (busca de
  logradouros, geocodificação de endereço, busca de lotes) já estão implementados — o roadmap
  não reflete isso e não há mecanismo para refletir. O estado real de implementação já é
  rastreado pelo front-matter `implementado:` das SPECs.
- Roadmap orienta **o que construir a seguir**, decisão do desenvolvedor — não é regra que o
  agente precise carregar em toda sessão.

**Recomendação:** ~~mover para `SPECS/ROADMAP.md`~~ → **decisão de 2026-07-31: descartar.** O
roadmap já estava desatualizado e foi integralmente superado pelo escopo de plataforma (ver §8.1).
Não vale migrar um artefato velho: o que existe é rastreado pelo front-matter `implementado:` das
SPECs, e o que virá é decidido SPEC a SPEC.

### 1.3 §8 — exemplo de código completo de management command

A regra ("comando fino: parsing + chamada ao script + feedback") é inegociável e fica. O
**exemplo de 15 linhas** é material de consulta ocasional — o padrão real e mais completo já
aparece na skill `wfs-fetcher` (seção "Orquestração"). Exemplo em CLAUDE.md envelhece sem ninguém
perceber.

**Recomendação:** manter a regra em uma frase; mover o exemplo para uma skill
`management-commands` (proposta em `skills_sugeridas/`), junto com a ordem do pipeline de dados
(cargas → variações → cache), que hoje está solta no fim do §8.

### 1.4 §1 — nível de detalhe da narrativa de produto

A visão geral é valiosa (o agente precisa entender o domínio), mas hoje mistura três coisas:
(a) o que o sistema é; (b) a especificação UX detalhada da busca (comportamento de keyup,
sugestões, pop-up de endereço fiscal exato); (c) o modelo futuro de usuários/projetos/layers com
regras de CRUD. Os itens (b) e (c) são **especificação de produto** — o lugar deles é SPEC (o
fluxo de busca, aliás, já foi especificado e re-especificado em `SPECS/roteamento_busca/` e
`SPECS/design/`; a narrativa do CLAUDE.md já diverge do implementado em detalhes como o fuzzy
fallback).

**Recomendação:** comprimir §1 para ~40 linhas: o que é, as três fontes de dados, os três tipos
de busca → três geometrias, e o conceito de projeto/layer em um parágrafo (as regras finas de
layer homogêneo ficam, porque são princípio de arquitetura — ver §7.3).

### 1.5 Notas de rodapé da stack (§2) — verbosidade de setup one-shot

As notas sobre psycopg 3 ("o pacote chama-se psycopg, não existe psycopg3, instala-se com pip
install...") e sobre PostGIS são conhecimento de **setup inicial**, que já aconteceu — o banco
está configurado (`settings.py` já usa o backend postgis). O aviso que ainda tem valor recorrente
é um só: "toda nova pasta de templates precisa de `@source`" — e esse já está coberto (melhor)
pela skill `componentes-frontend` §8.

**Recomendação:** manter a tabela da stack; reduzir as três notas a duas linhas cada.

### 1.6 Apêndice "Regra de workflow do usuário (memorizada)" — mal posicionado

A regra (SPEC antes de código + **aguardar aprovação do usuário**) é importante demais para viver
como apêndice colado depois do roadmap. Ela complementa o §4 e deveria estar **dentro** dele.
O detalhe "aguardar aprovação" hoje só existe nesse apêndice — no §4 não.

**Recomendação:** fundir no §4.

---

## 2. Duplicações com skills — referenciar em vez de repetir

Direção saudável de duplicação: **CLAUDE.md declara o princípio (uma frase) e aponta a skill;
a skill carrega o como.** Hoje há repetições nos dois sentidos:

| Conteúdo no CLAUDE.md | Skill que já cobre | O que fazer |
|---|---|---|
| §7.1 normalização única + §11 "Normalização única" + item do checklist §14 — a mesma regra aparece **3×** no próprio arquivo | `normalize-text` (regra inegociável, import, exemplos) | Uma única menção: "matching textual usa a normalização única — ver skill `normalize-text`" |
| Regra de matching fuzzy (§1 "Regra para matching", §7.3 "Match exato vs. variação") — 2× no arquivo | `fuzzy-matcher` (assinatura, algoritmos, retorno) | Manter o princípio (código = lookup exato; texto = variações + fuzzy) **uma vez**; o como é a skill |
| Nota Tailwind 4/DaisyUII do §2 + §11 "Estilização" (`@source`, `@plugin "daisyui"`) | `componentes-frontend` §8 (setup completo, armadilhas de build) e `daisyui` | Referenciar. O CLAUDE.md nem menciona o design system "Onsen de Inverno" — a referência à skill é mais útil que a nota que lá está |
| §7.2 detalhes de integração WFS (contratos Pydantic expostos no `__init__`, exceções próprias) | `wfs-fetcher` (uso completo, CQL, retry, orquestração) | Manter o princípio de fronteira (2 linhas); apontar a skill |
| §13 Política de Testes — o passo "validar a implementação (smoke test manual)" | `test-django-views` (o pipeline concreto de smoke test) | Manter a política (é regra de workflow, lugar certo é o CLAUDE.md), encurtar e apontar a skill para o *como validar* |
| §4 aponta a skill de SPECs — correto, mas com **caminho quebrado**: `@.claude/SKILLS/specs/SKILL.md` (a pasta real é `.claude/skills/`, minúscula — em Linux o caminho não resolve) e o nome da skill é `write-spec` | `write-spec` (specs) | Corrigir caminho/nome |
| §11 regra de JS restrito e §7.3 CRS/reprojeção | `leaflet-map` **cita** o CLAUDE.md (direção correta: skill → CLAUDE.md) | Nada a remover — apenas **não deixar crescer** detalhe de mapa no CLAUDE.md; novos detalhes vão para a skill |

Duas observações nesse tema:

- **O middleware de validação Pydantic não é mencionado no CLAUDE.md.** É uma peça estrutural
  (toda view depende dele — não se escreve `try/except ValidationError`), documentada apenas na
  skill `pydantic-validation-errors`. O CLAUDE.md deveria ter uma linha nas convenções apontando
  para ela, senão um agente que não ative a skill reimplementa o tratamento.
- **A skill `htmx` e a `daisyui` são referências de biblioteca** (importadas de docs oficiais).
  Não há duplicação relevante com o CLAUDE.md — as convenções HTMX do §11 (`delay`/`changed`,
  alvos explícitos) são projeto-específicas e devem ficar.

---

## 3. O que está FALTANDO no CLAUDE.md

### 3.1 Índice de skills do projeto (a lacuna mais importante)

O CLAUDE.md referencia **uma** skill (specs, com caminho errado). Existem **dez**. As skills de
uso obrigatório (`normalize-text`, `fuzzy-matcher`, `pydantic-validation-errors`,
`componentes-frontend`) declaram "use SEMPRE que..." — mas o agente só descobre isso se a skill
for ativada. Um índice curto no CLAUDE.md ("mexeu em X → consulte a skill Y") fecha esse ciclo e
é o que permite **remover** as duplicações do §2 deste diagnóstico com segurança.

### 3.2 A tabela de apps diverge do código real

`settings.py` registra 8 apps: `core`, `search`, `logradouro_matcher`, `lote_matcher`,
`address_geocoder`, `mapping`, `logradouro_geocoder`, `lote_geocoder`. A tabela do §6:

- **Não lista** `logradouro_geocoder` nem `lote_geocoder` (a separação matcher/geocoder foi uma
  decisão de arquitetura real — matcher resolve *sugestão/identificação*, geocoder resolve a
  *geometria* — e está invisível no documento);
- **Lista** `accounts` e `projects`, que não existem, sem marcá-los como futuros;
- Atribui persistência aos apps ("O que persiste"), mas **nenhum app de domínio tem models
  hoje** — os dados de busca vivem em parquet (`data/*.parquet`) + caches em memória.

### 3.3 O estado real da persistência

O documento afirma "PostGIS desde o início (não há fase SQLite)" e descreve models geométricos
como se existissem. A realidade: PostGIS está **configurado** (engine + extensão), mas o runtime
de busca opera sobre **parquet + catálogos cacheados em memória** (há inclusive SPEC de warmup:
`SPECS/infraestrutura/003-catalog-eager-warmup.md`); os models espaciais entram com o épico de
projetos. Um agente que leia o CLAUDE.md hoje procura models que não existem. Falta um parágrafo
honesto de **estado atual**: o que já está de pé, o que é alvo.

### 3.4 Comandos de desenvolvimento incorretos/incompletos (§12)

- **Testes:** o §12 manda `uv run python manage.py test`, mas o projeto usa **pytest**
  (`pyproject.toml` tem `[tool.pytest.ini_options]`, com marker `integration` documentado:
  `pytest -m integration`). A skill `test-django-views` também fala em pytest.
- **Docker:** existem `docker-compose.yml`, `Dockerfile`, `entrypoint.sh` e `.env.example` — o
  CLAUDE.md não diz uma palavra sobre como subir o banco/ambiente, nem que a configuração vem de
  `.env` (o settings lê `_env.postgres_*`).

### 3.5 Convenção de idioma

O código mistura inglês estrutural e português de domínio (`roteamento_busca`, `secoes.py`,
`nome_camada`, docstrings PT-BR). É uma convenção real e não escrita — vale uma linha, senão um
agente "arruma" nomes para inglês.

### 3.6 Como saber o que já foi implementado

O front-matter `implementado:` das SPECs é o registro oficial do que existe. O CLAUDE.md nunca
diz isso — só a skill de SPECs. Uma linha no §4 ("para saber o que já existe, consulte os
front-matters em SPECS/") economiza exploração repetida em toda sessão.

---

## 4. Skills que estão faltando (resumo — rascunhos em `skills_sugeridas/`)

| Skill proposta | Por quê | Prioridade |
|---|---|---|
| `wms-fetcher` | `services/integrations/wms` existe e já deu problema real (commit "arrumando problema na requisicao pro geosampa... wms para a ortofoto que tava barrando"). O irmão WFS tem skill; o WMS não. | Alta |
| `catalogos-lookup` | Os catálogos cacheados (`services/utils/cache.py`, warmup eager) são consultados por praticamente todo fluxo de busca; a interface de lookup é a peça que vai trocar para Redis — ninguém deveria acoplar fora dela. | Alta |
| `fluxo-busca` | 14 SPECs iteraram o padrão "filtro regex → view roteadora → seção de sugestão → partial". Cada novo tipo de entrada re-deriva o padrão lendo SPECs antigas. Uma skill fixa o esqueleto. | Alta |
| `management-commands` | Absorve o §8 do CLAUDE.md (regra + exemplo + ordem do pipeline de dados). | Média |
| `leaflet-eventos` | Prometida explicitamente pela própria skill `leaflet-map` ("fora do escopo: skill futura"). Necessária quando entrar o modo projeto/digitalização (Fase 2). | Baixa (placeholder) |

Os rascunhos estão escritos como **esqueletos com TODOs**: eu deliberadamente não li o código
fonte módulo a módulo nesta revisão, então assinaturas e nomes exatos precisam ser confirmados
contra o código antes de promover cada rascunho para `.claude/skills/`.

---

## 5. Correções pontuais (bugs do documento)

1. `@.claude/SKILLS/specs/SKILL.md` → `.claude/skills/specs/SKILL.md` (case-sensitive).
2. Duas seções numeradas `## 14.`.
3. Typos: "imóvle" (§1), "logradoro" (§1), "estamso" (§10.5).
4. §10.5 ("não use `from __future__`") é regra válida mas está redigida como desabafo — cabe uma
   linha nas convenções.
5. **Atenção ao migrar:** algumas skills citam parágrafos do CLAUDE.md atual pelo número, e a
   renumeração quebra essas citações. **Levantamento linha a linha no §8**, com a redação
   sugerida para cada ocorrência.

---

## 6. Efeito esperado

Com as mudanças propostas (ver `02-claude-md-proposto.md`), o CLAUDE.md cai de ~584 para ~300
linhas, sem perder nenhuma regra inegociável: o que saiu virou referência a skill (carregada só
quando o tema aparece), foi para `SPECS/ROADMAP.md`, ou era duplicata interna. E o documento
passa a dizer a verdade sobre o estado do código — que é o requisito mínimo para um arquivo de
contexto ser confiável.

---

## 7. Adendo (2026-07-07) — decisão: catálogos in-memory ficam; Redis descartado

Discutido após a revisão. O CLAUDE.md original tratava o dict em memória como provisório
("cache de lookup migra de dict em memória para Redis"). A avaliação inverteu essa premissa e a
versão proposta (§1 e §6.3) já registra a decisão:

- **Redis não aumenta a confiabilidade neste caso.** Os catálogos são read-only, determinísticos
  e reconstruíveis a partir dos parquets de `data/`; os modos de falha reais (parquet
  desatualizado, custo de warmup) não são resolvidos por Redis — que, por sua vez, adiciona modos
  de falha novos (serviço fora, rede, cache vazio pós-restart, dessincronia com o pipeline).
- **Os padrões de acesso exigem o corpus in-process.** Fuzzy match (rapidfuzz) sobre todas as
  linhas e filtros vetorizados em pandas não são executáveis do lado do servidor Redis; migrar
  significaria transportar o dataset inteiro por rede a cada request ou abandonar rapidfuzz/pandas.
- **A aplicação é de uso interno** (confirmado pelo usuário em 2026-07-07): escala de dezenas de
  usuários, 1–2 workers — a duplicação de memória por worker é irrelevante nesse porte.
- **Plano B, se um dia houver pressão de memória multi-worker:** mover lookups exatos/prefixo
  (contribuinte, codlog) para o **PostgreSQL já existente na stack** (queries indexadas), mantendo
  in-memory apenas o corpus de fuzzy (o menor — `nomes_logradouros.parquet` ~1MB).
- **O que continua valendo:** todo consumo passa pela interface dos catálogos (nunca ler
  `data/*.parquet` direto em view/domínio) — é isso que mantém qualquer migração futura barata.
  O rascunho `skills_sugeridas/catalogos-lookup/` foi atualizado para refletir a decisão.

---

## 8. Adendo (2026-07-31) — escopo maduro e impacto nas skills

Revisão feita depois que o escopo real do projeto foi explicitado. O diagnóstico original
(2026-07-07) tratou o sistema como um geocodificador; ele é outra coisa, e isso muda o CLAUDE.md
mais do que qualquer enxugamento.

### 8.1 O que mudou no entendimento do sistema

O DIMAP GeoCoder é uma **plataforma de uso interno que modela processos de trabalho da DIMAP cujo
input inicial é uma localização no território urbano**. A geocodificação é a porta de entrada, não
o produto. O fluxo: **localização → entidade territorial tipada (com sua ontologia) → gaveta**, e a
gaveta oferece **Informações** (dado público, sem login) e **Ações** (Atos Administrativos, com
login, autorização por perfil e auditoria). Cada processo da DIMAP vira uma ação nova.

Decisões confirmadas com o usuário nesta data, registradas no CLAUDE.md proposto (§3.4–§3.6):

- **Uma ação = um app Django próprio**, com submódulos próprios em `services/domain/` (relação
  N:N). **A busca não pode ser contaminada:** dependência de mão única, contato só via contrato.
- **Rotas de ação são deny by default**; rota aberta só por declaração explícita na SPEC.
- **Informação ≠ Ação:** ação exige login porque é ato administrativo e precisa de imputação —
  daí a exigência de **registro de toda execução** (quem, com qual perfil, sobre o quê, quando).
- **A gaveta filtra, a rota decide** — a UI esconder o botão não é autorização.
- **Perfil é model próprio** herdando de `contrib.auth`, com models de cargo e unidade; há um
  **perfil padrão** (autorização universal, autenticação ainda obrigatória).
- **Mapeamento perfil → ação é código**, no contrato da ação, decidido pelo desenvolvedor — nunca
  configurável em runtime.
- **Roteador de ações:** rota que recebe perfil + tipo de entidade e devolve as ações disponíveis.
- **Ações são síncronas por padrão**; fila só se a SPEC de uma ação específica justificar.

Somam-se a elas, na mesma data: **rigor de design system + Atomic Design** como princípio de
arquitetura (nenhum componente de UI fora do design system; cada nível composto pelo nível
imediatamente inferior; átomo novo nasce no design system, nunca como marcação solta); **DuckDB**
na stack, para consulta analítica sobre os parquets de `data/`; e **LIDAR / nuvens de pontos 3D**
como escopo futuro, com ferramental a ser definido em SPEC própria — o CLAUDE.md registra a
intenção justamente para que ninguém improvise a escolha de biblioteca antes disso.

E a mudança de maior impacto no fluxo de trabalho: **o projeto adotou TDD**. A política anterior
("testes só sob demanda explícita, nunca junto da SPEC") está **revogada**. O ciclo passa a ser
SPEC *com testes* aprovada → testes escritos e falhando → implementação até passarem → validação.
O argumento que sustentava a política antiga se inverte: ele dizia que gerar teste antes da
validação humana desperdiça ciclo — mas com os testes **dentro da SPEC**, a validação humana
acontece justamente ali, antes do código. A restrição que permanece é de **volume**: poucos testes
e bem escolhidos (~3 a 6 numa SPEC típica), fixando comportamento observável, sem perseguir
cobertura.

### 8.1.1 Recomendações deste diagnóstico que foram revertidas

Três recomendações dos §§1–3 **não valem mais**, por decisão do usuário em 2026-07-31:

- **§3.1 ("índice de skills é a lacuna mais importante") — revertida.** As `description` das skills
  já entram no contexto do agente em toda sessão; um índice no CLAUDE.md é duplicação de token sem
  ganho de descoberta. O que fica no CLAUDE.md é a **regra** ("nunca chamar rapidfuzz direto",
  "nunca ler parquet direto", "nenhum componente fora do design system") — a skill certa é achada
  pela própria descrição. O índice só volta se existir uma skill *sobre criar skills* que exija
  registro central e tenha dono.
- **§3.2 ("a tabela de apps diverge do código real") — resolvida por remoção, não por correção.**
  A tabela app a app sai do CLAUDE.md: ela muda com frequência e vai divergir de novo.
  `INSTALLED_APPS` é a fonte de verdade. O que fica documentado são os **padrões de organização**
  (matcher × geocoder, um app por ação) e, sobretudo, a fronteira `apps/` × `services/` — que é o
  que de fato precisa ser sabido em toda sessão.
- **§1.4 ("comprimir a visão geral") — cumprida de outro jeito.** A visão geral não encolheu: foi
  *reescrita* para descrever a plataforma em vez do geocodificador.

Correção de conteúdo na mesma leva: um endereço que bate **exatamente** com um endereço fiscal
resolve para **polígono** (o imóvel cadastrado no IPTU). A descrição anterior — pop-up oferecendo
ponto *ou* polígono — está errada e foi removida da proposta.

### 8.2 Skills que citam o CLAUDE.md por número — ajustes ao adotar

A renumeração quebra as citações abaixo. Levantamento por `grep` no código real das skills:

| Skill | Linha | Citação atual | Ajuste |
|---|---|---|---|
| `specs` | 94–95 | "princípios de arquitetura (§3)… e o estilo (§10)" | §3 permanece; **§10 → §7** |
| `specs` | 131–132 | "quais princípios de §3 do CLAUDE.md se aplicam" | §3 permanece — sem ajuste |
| `specs` | 141 | "sem violar §3 nem §10" | **§10 → §7** |
| `leaflet-map` | 24 | "Regras de fronteira (§11 do CLAUDE.md…)" | **§11 → §7.2** |
| `leaflet-map` | 31 | "O domínio reprojeta para 4326 antes de mandar (§7.3)" | **§7.3 → §6.3** |
| `leaflet-map` | 208 | "(§11: JS não monta UI)" | **§11 → §7.2** |
| `test-django-views` | 3 *(front-matter `description`)* | "CLAUDE.md §13" | **§13 → §9** |
| `test-django-views` | 10 | "§13 do CLAUDE.md: 'validar a implementação…'" | **§13 → §9** |
| `test-django-views` | 98 | "(CLAUDE.md §13)" | **§13 → §9** |
| `wfs-fetcher` | 16 | "Ver §3.3 do CLAUDE.md" | **inalterado** (§3.3 segue sendo o isolamento de camadas) |

Atenção a dois falsos positivos: os `§` de `componentes-frontend` e o `§3` da linha 64 de
`leaflet-map` são referências **internas à própria skill**, não ao CLAUDE.md — não mexer.

**Recomendação preferível a corrigir o número:** trocar a citação numérica pelo **nome da seção**
("princípios de arquitetura", "política de testes", "estilo e convenções"). Nomes sobrevivem à
próxima renumeração; números não. O ajuste da linha 3 de `test-django-views` é o mais sensível —
está no front-matter, que é o que o agente lê para decidir ativar a skill.

### 8.3 Skills com divergência de conteúdo (não só de número)

**`leaflet-map`, linha 133** — afirma que "cada layer do projeto tem `cor` de display — §1 do
CLAUDE.md", tratando projetos/layers como algo existente. **Não existem** — são escopo futuro, e o
CLAUDE.md proposto **deixou de mencioná-los** (a seção "Entradas futuras" foi removida por decisão
do usuário: escopo futuro é assunto de SPEC, não de contexto carregado toda sessão). A citação da
skill fica, portanto, **apontando para o vazio** — precisa ser reescrita como referência a escopo
futuro, autocontida na própria skill, ou a cor será procurada num model que não está lá.

**`test-django-views`** — a skill se apresenta como "o *validar a implementação* do fluxo de SPEC"
e afirma que o smoke test "não fica versionado como suíte de testes". Com o TDD, o smoke test
deixa de ser *a* validação e passa a ser **um passo complementar**: a validação principal é a suíte
que a SPEC definiu e que foi escrita antes do código; o smoke test continua útil para o que o
teste automatizado não cobre bem (HTML do partial renderizado, caminhos de erro na interface).
Ajustar o enquadramento — nas linhas 3, 10 e 98 — junto com a renumeração §13 → §9.

**`specs`** — já foi **atualizada em 2026-07-31** (não é pendência): a seção "Notas de teste" virou
"**Testes (TDD)**", com instrução explícita de listar poucos testes essenciais (~3 a 6), e o item
de checklist "nenhum teste unitário foi escrito ou comprometido" foi substituído. Restam nela
apenas as citações numéricas do §8.2.

### 8.4 Skills que o novo escopo sugere (fora do escopo desta revisão)

**Prioridade alta — `geo-crs` (lacuna aberta pelo enxugamento).** Ao tirar do CLAUDE.md a subseção
de projeção (nível de abstração baixo demais para contexto sempre carregado), estes detalhes
ficaram **sem nenhum lugar**: SIRGAS 2000/UTM 23S (EPSG:31983) do GeoSampa × WGS84 (EPSG:4326) do
Leaflet, as settings `MAP_INTERPOLATION_CRS`/`MAP_OUTPUT_CRS` e como elas chegam ao domínio via
DTO, o uso de `Transform` e dos objetos GEOS/GDAL, e a definição do CRS canônico de armazenamento
quando a persistência de geometria entrar. `leaflet-map` cobre só a renderização. O CLAUDE.md
mantém a **regra** (§7.2), mas o *como* precisa desta skill — é a única perda real do enxugamento.

Registro para quando a plataforma de ações começar — **não são para criar agora**: uma skill do
**contrato de ação** (como declarar perfil autorizado, como registrar a execução auditada, como o
app se apresenta ao roteador) será tão obrigatória quanto `normalize-text` é hoje, porque é o ponto
onde a regra de mão única (§3.4 do CLAUDE.md) ou se sustenta, ou vaza. As propostas do §4 deste
diagnóstico (`wms-fetcher`, `catalogos-lookup` — **já promovida** —, `fluxo-busca`,
`management-commands`, `leaflet-eventos`) seguem válidas.
