---
spec: user_admin/015
versao: v11
atualizado_em: 2026-08-12
testes_tdd: true
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: a substituição passa a dizer o papel — enquanto vigora, o substituto responde pelo cargo do
        afastado e, se o afastado é o titular, dirige a unidade (SPEC 014), sem receber o vínculo de
        titularidade; a unicidade da titularidade deixa de depender da marca de exercício
  - v3: o alarme de unidade sem direção passa a ganhar código na SPEC 016 (a interface da
        titularidade), não na 014 — só o ponteiro muda
  - v4: a SPEC 014 foi implementada antes desta e deixou de fora a montagem do `EstadoDaDirecao`,
        que lia a substituição inexistente; esta SPEC passa a expor a leitura da substituição
        vigente que a 016 compõe, o andaime deixa de ter porta própria para criar impedimento, e os
        DTOs de domínio vão para `models.py`, como nos demais submódulos; a 014 deixa de declarar
        esta como pré-requisito (patch 002 dela), e a ordem numérica do épico volta a ser a ordem
        de implementação
  - v5: um servidor passa a cobrir **uma pessoa por vez** — a unicidade da substituição vigente vale
        dos dois lados, com índice parcial também no substituto, quem já cobre alguém sai da lista
        de candidatos e a leitura do lado exercido vira uma substituição, não um conjunto; em
        contrapartida, acumular a própria cadeira com a cobertura é explicitamente admitido (até
        responder por duas unidades), e a **mesma unidade deixa de ser regra**: vira o padrão da
        lista, com as demais atrás de um toggle que abre pela unidade superior
  - v6: o exercício deixa de ser coluna gravada e vira **leitura derivada de duas causas** —
        impedimento ativo e exoneração —, o que torna a inconsistência impossível em vez de vigiada
        e devolve a pessoa à cadeira sozinha quando o impedimento vence; a substituição passa a ser
        **do impedimento**, e por isso cai com ele sem escrita nenhuma
  - v7: a substituição ganha **período próprio**, contido no do impedimento e igual a ele por
        padrão — do que decorre que ela pode começar depois e terminar antes, deixando o afastado
        **sem cobertura** em parte do afastamento (e a unidade sem direção); designar passa a valer
        para impedimento **em aberto**, vigente ou futuro, o que faz duas férias da mesma pessoa
        poderem ter substitutos diferentes; **voltar ao exercício volta a ser ato** — e é o que
        encerra os impedimentos vigentes, sendo o único retorno antecipado; a exoneração deixa de
        ganhar campo próprio (é o `is_active` que o `contrib.auth` já tem); e, no desenho, cada
        impedimento em aberto passa a ser um **cartão** — painel erguido sobre o poço da seção, com o
        afastamento e a substituição em dois poços dentro —, de modo que o aninhamento, e não o
        recuo, diga de qual afastamento é cada substituto; **trocar o substituto** entra no escopo,
        como variante do mesmo ato, sobrescrevendo a designação
  - v8: cai o **um-para-um** com o impedimento, que era o que mancava a SPEC: um afastamento passa a
        ter **várias substituições não-sobrepostas**, o que dá a **cobertura em sequência** (uma
        pessoa na primeira semana, outra na segunda) e faz a **troca encerrar a anterior em vez de
        sobrescrevê-la** — o histórico de quem substituiu quando passa a existir por construção.
        Entra **encerrar substituição** (revogar sem pôr outra), o poço do substituto vira **lista**
        no cartão, e a invariante "duas pessoas não respondem pelas mesmas férias" deixa de ser
        constraint e vira **não-sobreposição decidida no domínio** — assumidamente sem garantia de
        banco
  - v9: com o afastamento podendo ter buracos, "está substituído" deixa de poder ser respondido pela
        **existência** de uma substituição: a pergunta é sempre "há substituição **vigente hoje**",
        e a SPEC proíbe qualquer leitura que responda sem a data. No desenho, nasce o átomo
        **calha da cobertura**: o afastamento inteiro como uma bandeja funda, com o sulco
        **entintado** nos pedaços que têm substituto e o poço vazio nos que não têm — o que torna os
        buracos visíveis antes de qualquer data ser lida, na proporção dos dias que duram
  - v10: a SPEC descrevia os atos e a regra e **não descrevia o que a tela recebe pronta** — a lista
         de candidatos prometida em dois lugares e sem dono, `NovoImpedimento`/`NovaSubstituicao`
         usados e nunca definidos, e a conversão dos trechos em medida atribuída ao `context.py` sem
         critério. Entra a **orquestração de leitura**: o contexto da seção, os DTOs de entrada dos
         atos e a montagem dos DTOs de domínio numa peça só, partilhada pelo `clean()` e pela lista.
         **Nenhuma rota nova**, e a SPEC passa a dizer isso explicitamente: as escritas por HTTP
         saem de escopo e ficam para o épico de ações, onde nascem protegidas — enquanto isso os
         diálogos renderizam com o submit sem destino, como o modal da SPEC 012, e "a rota recusa"
         vira "**o ato** recusa". Duas correções de desenho vêm junto: o toggle de alcance **não
         ganha rota** — as duas listas nascem renderizadas, como no mock —, e os campos de data do
         diálogo **vêm preenchidos** com a primeira lacuna, não em branco
  - v11: sem mudança de escopo — a prosa (abertura, "Contexto e decisões de arquitetura" e "Mock de
         validação") foi reescrita como se fosse a primeira versão: cada decisão enunciada por si,
         sem contrapor-se ao que versões anteriores diziam e sem repetir justificativa entre seções.
         O histórico de como se chegou aqui fica só neste changelog
---

# SPEC user_admin/015 — Exercício e substituição: quem está na cadeira e quem cobre

> Entram aqui as duas leituras que faltam ao sistema: **quem está exercendo o cargo hoje** e **quem
> responde por ele enquanto está fora**. A titularidade (SPEC 014) já existe e não é tocada por
> nenhum ato desta SPEC; quem compõe titular e substituto para dizer quem dirige a unidade é a
> **SPEC 016**.

- [x] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como responsável pela DIMAP, quero registrar o impedimento de um servidor e designar quem o
substitui, para que "quem está exercendo o cargo hoje" e "quem responde por ele enquanto está fora"
sejam dados do sistema — e para que a competência acompanhe quem efetivamente está lá, inclusive a
direção da unidade quando quem se afasta é o titular.

## Critérios de aceite

### Exercício
- [ ] Exercício é **leitura derivada**, não coluna: está em exercício quem **não tem impedimento
      vigente hoje** e **não está exonerado**. Não existe terceira causa de sair da cadeira, e não
      existe campo que possa contradizer as duas.
- [ ] Estar em exercício com impedimento vigente é **impossível por construção**: não há marca a
      reconciliar, rotina que reconcilie nem checagem que precise rodar.
- [ ] Vencido o impedimento, a pessoa **volta à cadeira sozinha** — sem ato, sem escrita e sem
      rotina. Registrar impedimento de **início futuro** também não tira ninguém da cadeira antes da
      data que ele declara.
- [ ] **Exoneração não ganha campo novo:** é o `is_active` do `contrib.auth`, que hoje não tem
      nenhum outro uso no projeto. O `Perfil` expõe `exonerado` como leitura (`not is_active`) para
      o domínio falar a língua do domínio. **O ato de exonerar é de outra SPEC.**
- [ ] **Voltar ao exercício** é ato explícito — o botão está na tela, o ato existe, e ligá-los é do
      épico de ações — e é o único retorno antecipado: encerra
      **todos** os impedimentos vigentes hoje (`data_fim = hoje`) e acerta as substituições deles na
      mesma transação.

### Substituição
- [ ] A substituição é **de um impedimento**, não de uma pessoa — e um impedimento pode ter
      **várias**, desde que **não se sobreponham**: uma pessoa cobre a primeira semana das férias e
      outra a segunda. Duas pessoas nunca respondem pelas mesmas férias **ao mesmo tempo**.
- [ ] Designa-se para impedimento **em aberto** — vigente **ou futuro**. Duas férias distintas da
      mesma pessoa podem ter **substitutos diferentes**, e a designação pode ser feita antes de o
      afastamento começar.
- [ ] A substituição tem **período próprio**, e por padrão ele é **o pedaço do impedimento que ainda
      está descoberto** — o impedimento inteiro quando não há nenhuma outra. Informado, o período só
      pode ser **mais estreito** que o do impedimento: nunca começa antes nem termina depois.
- [ ] Do período próprio decorre um estado que a tela precisa mostrar: **afastado sem substituto
      hoje**, porque a substituição ainda não começou ou já terminou. Se o afastado é o titular,
      isso deixa a **unidade sem direção** exatamente como se não houvesse substituto.
- [ ] Só se designa substituto para quem **tem cargo em comissão** e **não está exonerado** — o
      caminho não se oferece ao resto, e o **ato recusa igual**.
- [ ] **Encerrar a substituição** é ato próprio: em curso, ela **termina hoje** e o vínculo fica
      registrado até aqui; ainda não iniciada, é **apagada**, porque cobertura que nunca vigorou não
      é histórico, é registro sem fato.
- [ ] **Trocar o substituto** é uma transação com os dois atos: encerra a atual **na véspera** do dia
      em que a nova assume e designa a nova — em vez de sobrescrever. Assim não há dia com dois
      respondendo nem lacuna entre eles, e **quem saiu continua registrado**, com o período que de
      fato exerceu.
- [ ] O substituto **nunca é o próprio substituído**, não está exonerado, **não está impedido** no
      período da substituição e **não substitui outra pessoa** em período que se cruze com ele. Ter
      cargo em comissão — inclusive ser titular da própria unidade — **não impede** ninguém de
      substituir, e o resultado pode ser um servidor respondendo por duas unidades.
- [ ] O **substituído** nunca tem **duas substituições que se cruzem** no tempo — nem do mesmo
      impedimento, nem de impedimentos diferentes que se sobrepõem (a SPEC 002 permite a
      sobreposição). É **uma regra só**, e ela vale para os dois casos.
- [ ] A lista de candidatos traz **a unidade do substituído por padrão**; alcançar as demais é ato
      explícito na tela — um **toggle** que amplia a busca —, porque cobrir fora da unidade é raro.
      Ampliada, a lista começa pela **unidade superior** do substituído. O **ato aceita** o
      substituto de qualquer unidade, com ou sem o toggle.
- [ ] A lista filtra pelo período **que a designação vai ocupar por padrão**, e o **ato valida pelo
      período efetivo**. Filtrar é UX; recusar é do ato — e da rota que o chamar, quando ela
      existir (§3.5).
- [ ] Nenhuma dessas invariantes é constraint: **o banco só garante que o fim não antecede o
      início**. A não-sobreposição inteira — dos dois lados — é decidida no domínio e barrada no
      `clean()`, e a SPEC assume esse custo explicitamente.
- [ ] Enquanto vigora, o substituto **responde pelo cargo** do afastado — e, se o afastado é o
      **titular** da unidade, é o substituto quem **dirige a unidade** (SPEC 014). A designação
      **não marca nada no substituto**: `e_titular` continua com o afastado, e o que muda é a
      resposta da leitura derivada, não o vínculo.

### Tela, leitura e andaime
- [ ] A seção mostra **os impedimentos em aberto** — o vigente e os futuros —, cada um num
      **cartão** que contém o afastamento e a **lista das substituições dele**: as encerradas, a
      vigente e as que ainda vêm, cada uma com pessoa e período. É **de dentro do cartão** que se
      designa: o botão herda dele a resposta para "substituto de quê?", e com dois afastamentos em
      aberto não há dúvida sobre quem substitui qual.
- [ ] O **histórico de quem substituiu quando** sai dessa lista, sem tabela nova: cada troca deixa a
      anterior encerrada com o período que exerceu.
- [ ] A página mostra também **quem o servidor está substituindo**, com o período, e — quando ele
      está fora da cadeira — **por qual das duas causas**.
- [ ] **"Está substituído" nunca é respondido pela existência da linha.** Como o afastamento pode ter
      buracos, a pergunta é sempre "há substituição **vigente hoje**", e a data entra em **toda**
      leitura. Não existe, em lugar nenhum do código, helper, property ou template tag que responda
      "tem substituto?" sem a data — nem `impedimento.substituicoes.exists()`, nem
      `related_name` consultado direto na view ou no template.
- [ ] A **substituição vigente** de um perfil sai de **uma leitura só** — a que ele recebe e a que
      ele exerce —, e é ela que a página do servidor consome e que a SPEC 016 compõe com o titular
      para saber quem dirige a unidade hoje. Não há segunda consulta para a mesma pergunta.
- [ ] A vigência de um período ("vale hoje", com fim nulo = indeterminado) é **um predicado só**,
      usado por impedimento e por substituição.
- [ ] A regra de quem pode substituir quem é decidida em `services/` e é **testável sem banco**,
      inclusive a comparação de períodos.
- [ ] O **andaime** (`ficticios.py`) cria impedimento **pelo mesmo caminho da tela** — não há segunda
      porta para a mesma escrita —, e deixa exercitáveis o **titular afastado sem substituto**, o
      **titular afastado com substituto**, o **afastamento coberto por substitutos em sequência**
      (com uma já encerrada, para o histórico ter o que mostrar), o **afastado cuja substituição
      ainda não começou**, o **impedimento futuro já com substituto designado** e o **exonerado**.
      Rodar de novo devolve todos ao exercício, em vez de acumular afastamento.
- [ ] O design foi aprovado no **mock** antes de qualquer código de aplicação.

### A tela é leitura: nenhuma rota nova, nenhum submit com destino
- [ ] **Esta SPEC não grava por HTTP.** A seção é renderizada pela rota que já existe — a página do
      servidor (SPEC 007) —, e o que falta a ela é o **contexto**. Nenhuma rota nasce aqui.
- [ ] **Os cinco atos existem como funções** e são exercitados pelo **andaime** e pelos testes; quem
      os liga a um botão é o épico de ações, onde a rota nasce **protegida**. Enquanto isso, os
      diálogos renderizam e o **submit não tem destino**, como o modal de nova unidade (SPEC 012).
- [ ] Os diálogos nascem com **a lacuna proposta já nos campos de data** e com a **lista de
      candidatos já filtrada** pelo período que a designação vai ocupar — o servidor calcula uma vez,
      no render da seção, e é isso que torna a peça conferível na tela antes de existir escrita. O
      **toggle de alcance não tem rota**: as duas listas vêm renderizadas e ele troca qual aparece.
- [ ] A **medida da calha** (`left`/`width` de cada trecho) é calculada na orquestração a partir de
      `trechos()`; o domínio devolve períodos, nunca porcentagem.
- [ ] O contexto da seção sai de **uma passagem só** pelos impedimentos em aberto: os cartões, a
      agenda de cada um, a calha, a lacuna e os candidatos. Nada na página pergunta duas vezes a
      mesma coisa ao banco.

## Contexto e decisões de arquitetura

Esta SPEC mexe em persistência (`user_admin`: o model de substituição e o predicado de vigência), em
domínio (`services/domain/exercicio/`) e em interface (uma seção nova e quatro modais na página do
servidor). Ela não decide autorização: quem lê o exercício e o transforma em competência é o épico
`autorizacao`.

**Exercício é derivado, e de exatamente duas causas.** Sair da cadeira tem dois motivos e não há
terceiro: um **impedimento vigente** ou uma **exoneração**. Sendo assim, exercício não é estado
guardado — é a resposta de `não impedido hoje e não exonerado`. Uma coluna própria seria um terceiro
valor capaz de discordar dos dois que o produzem, e obrigaria a vigiar essa discordância. Derivado,
três coisas vêm de graça: a pessoa **volta sozinha** quando o impedimento vence, sem rotina que
reconcilie; o impedimento de **início futuro** tira da cadeira na data que ele declara, e não na hora
do registro — que é o que permite designar hoje o substituto das férias do mês que vem; e não existe
janela em que o sistema esteja mentindo. *Custo assumido:* o filtro que seria `WHERE em_exercicio`
vira um `EXISTS` sobre impedimentos mais `is_active` — a dezenas de servidores, uma cláusula a mais
numa consulta, e ela nasce num lugar só.

**A exoneração é o `is_active` que já existe.** O `contrib.auth` traz o booleano de conta ativa, e
ele não tem nenhum outro uso no projeto. Exonerado é quem não é mais servidor da DIMAP, e isso
implica exatamente o que `is_active=False` significa — inclusive não entrar no sistema, de graça,
porque o `ModelBackend` já recusa. Um campo `exonerado` ao lado seria um segundo booleano andando
sempre junto do primeiro. O `Perfil` expõe `exonerado` como **leitura**, porque a tela e o domínio
falam de exoneração, não de conta ativa. *Se um dia existir "desativar sem exonerar"* — servidor
cadastrado antes da posse, conta suspensa —, os dois significados se separam e o campo próprio nasce
ali.

**"Vigente hoje" é um predicado só.** Impedimento e substituição têm a **mesma convenção de
período**: `data_inicio` obrigatória, `data_fim` nula significando indeterminado. A condição de
vigência vira uma função em `models/periodo.py`, no mesmo lugar e pelo mesmo motivo que
`cargo_titulariza` (SPEC 014) mora em `models/titularidade.py`: `esta_impedido`, o exercício, as duas
leituras de substituição e o filtro de candidatos fazem **a mesma pergunta** — basta uma delas
esquecer o `data_fim` nulo para o sistema responder duas coisas sobre a mesma pessoa.

**A leitura mora ao lado da que já existe; a decisão continua no domínio.** `Perfil.esta_impedido`
(SPEC 002) já é leitura derivada no model, e `Perfil.em_exercicio` é a composição dela com uma coluna
da própria linha — mesma natureza, não é regra de negócio (§3.2). O que **é** regra de negócio — quem
pode substituir quem — fica em `services/domain/exercicio/`, sobre DTO, sem Django.

**A substituição é do impedimento, não da pessoa, e são várias.** Substitui-se alguém *porque* há um
impedimento, e a substituição não pode sobreviver à causa dela: pendurada no substituído, ela
precisaria que alguém escrevesse o término — e o retorno é justamente o que não escreve nada —, e o
resultado seria substituto vigente com o substituído já de volta na cadeira. Pendurada no
impedimento, ela nasce e morre com ele. E um afastamento não tem *um* substituto: tem uma **agenda** — a pessoa A na
primeira semana, a B na segunda, e um pedaço no meio sem ninguém, se for o caso. O que a regra proíbe
é **sobreposição**, não pluralidade. Cada substituição guarda o próprio período, sempre contido no do
impedimento — substituir quem está na cadeira não é substituir —, e daí caem três coisas sem custo:
cobrir só um trecho do afastamento; ler a **vigência da substituição sozinha**, sem compor com a do
impedimento a cada consulta, porque a contenção garante que uma vigente implica a outra; e ter o
**histórico** de quem substituiu quando, que é a própria lista, sem tabela nova.

**Por isso "tem substituto" não é pergunta que o sistema responda.** A pergunta que existe é "**há
substituição vigente hoje**", e ela carrega a data sempre. `substituicoes.exists()` responderia "sim"
para um afastamento cujo substituto sai amanhã, cuja cobertura acabou semana passada ou que só começa
em setembro — e o erro aqui não é de tela: é dizer que a unidade tem quem responda por ela quando não
tem. A leitura mora nas duas funções de `apps/user_admin/exercicio.py`, que compõem o predicado de
vigência, e **nada além delas responde essa pergunta** — nem view, nem template, nem property de
model.

*Consequência aceita, e é ela que o desenho precisa acomodar:* entre o início do afastamento e o
início da cobertura — ou depois que a cobertura termina — o afastado fica **sem substituto vigente**.
Se ele é o titular, a **unidade fica sem direção** nesse intervalo, exatamente como se ninguém
tivesse sido designado. A tela mostra isso; a leitura da direção (SPEC 016) o enxerga sem caso
especial, porque para ela "não há substituição vigente" é uma resposta só.

**Voltar ao exercício é o único retorno antecipado, e acerta as substituições na mesma transação.**
Criar impedimento não arrasta escrita nenhuma — ele *é* a causa —, e o fim do prazo também não, é uma
data passando. O que sobra como ato é voltar antes do previsto, e a forma honesta disso é dizer que o
impedimento acabou hoje. O ato encerra **todos** os vigentes: encerrar um só deixaria a pessoa fora
pelo outro, e o botão teria mentido. Como a contenção é validada na designação, o retorno antecipado
é o único evento que pode quebrá-la depois — então o mesmo ato trunca em hoje a substituição em curso
e **apaga** as que não começaram, em vez de deixar toda leitura compor as duas vigências para
descobrir que o registro está mentindo sobre quando a cobertura acabou.

**Encerrar é um ato; trocar são dois numa transação.** Tirar um substituto é dizer que a substituição
dele acabou: em curso, ela **termina hoje** e o que ele exerceu fica registrado; ainda não iniciada,
é **apagada**, porque registro sem fato não é histórico. Trocar é isso mais uma designação — encerra
a atual **na véspera** do dia em que a nova assume e cria a nova. A véspera é o que impede ao mesmo
tempo o dia com dois respondendo, que a não-sobreposição proíbe, e a lacuna de um dia, que deixaria a
unidade sem direção por descuido de formulário. E é a troca assim, e não sobrescrevendo, que
**produz o histórico**: quem saiu continua na lista, com o período que de fato exerceu — a única
informação que ninguém consegue reconstruir depois é sob a competência de quem o ato foi praticado
naquela semana.

**A regra é uma só, e é não-sobreposição — dos dois lados.** Ninguém substitui duas pessoas ao mesmo
tempo, e ninguém é substituído por duas ao mesmo tempo. A razão é a mesma nos dois casos: o
substituto responde *pelo cargo* do afastado, e duas substituições simultâneas deixariam sem resposta
única a pergunta de sob qual competência o ato foi praticado. Enunciada assim, ela cobre de uma vez
as duas do mesmo impedimento, as de impedimentos sobrepostos (a SPEC 002 permite a sobreposição) e o
mesmo substituto em dois lugares. O que **não** é proibido é acumular: um titular pode substituir
outro servidor e responder pelas duas unidades ao mesmo tempo, e o mesmo servidor pode substituir
duas pessoas em meses diferentes.

*Custo assumido, e é o principal desta SPEC:* nada disso é constraint. Índice parcial não expressa
não-sobreposição, e a alternativa que expressaria — `ExclusionConstraint` com `daterange` — exigiria
`btree_gist` e `django.contrib.postgres`, que o projeto não usa. A invariante fica em `services/`,
barrada no `clean()`, e por isso **escrita concorrente ou por shell escapa**. A dezenas de usuários
internos, com uma tela só gravando, o risco é aceito em troca de não carregar uma extensão e um
recurso de banco a mais — e é revisável se a operação mostrar o contrário.

**Sem cargo em comissão não há o que substituir; exonerado não se substitui.** Substituir é cobrir a
competência de um cargo em comissão; de quem não tem, não há competência a cobrir. E a exoneração não
abre cobertura de espécie alguma: a cadeira do exonerado não é coberta, é **preenchida** por outra
pessoa — isso é lotação e titularidade, não substituição.

**Quem substitui ocupa o papel, não recebe o vínculo.** Enquanto vigora, o substituto responde pelo
que o cargo do afastado responde — e, quando o afastado é o titular, isso é dirigir a unidade (SPEC
014). Nada é marcado no substituto: a titularidade é vínculo único por unidade, continua com quem se
afastou, e é isso que faz o retorno devolver a direção sem negociar com ninguém. Daí também que do
**substituto** não se exija — nem se vede — cargo em comissão: quem cobre tanto pode ser um
subordinado sem cargo quanto o titular de outra cadeira, e exigir cargo esvaziaria a designação
justamente nas unidades pequenas.

**A unidade não limita quem cobre — a tela é que ordena o comum.** A competência exercida é a do
cargo do afastado, e não depende de onde o substituto está lotado: cobrir de outra unidade é legítimo
e acontece. Mas é raro, e uma lista com todos os servidores da DIMAP faria o caso comum pagar pelo
excepcional — daí a lista nascer na unidade do substituído, as demais entrarem por comando explícito
e, quando entram, virem atrás da **unidade superior**, de onde a cobertura de fora costuma vir. É
ordenação de UX, não regra: quem valida a designação não pergunta pela unidade.

**A designação depende do estado de outras linhas, então vive no `clean()` — e a decisão, no
domínio.** Ao banco sobra o que é condição da própria linha: **fim não anterior ao início**. Todo o
resto cruza linha e tabela — contenção no período do impedimento, não-sobreposição dos dois lados,
cargo em comissão do substituído, exoneração de qualquer das pontas, as duas pontas sendo a mesma
pessoa — e vai para o `clean()`, com a regra em `services/domain/exercicio/` sobre DTO, testável sem
banco (§3.3). Detalhe que a troca obriga: ao validar uma substituição que já existe, **ela própria
não entra** nas listas de períodos do DTO, senão conflita consigo mesma.

**Montar os DTOs do domínio a partir do banco é uma peça só.** `AvaliadorDesignacao` recebe
`Substituido` e `Substituto` já preenchidos, e quem os preenche são dois chamadores: o `clean()`, que
valida uma designação, e a tela, que precisa saber quais candidatos passariam. Se cada um montar o
seu, "a mesma regra no `clean` e na lista" deixa de ser verdade no dia em que uma das montagens
esquecer um período. A montagem mora ao lado dos atos, em `apps/user_admin/exercicio.py`.

**A tela desta SPEC é leitura; a escrita por HTTP é do épico de ações.** A página do servidor já
existe, aberta pela exceção que a SPEC 013 declarou, e o que entra nela é **contexto — nenhuma rota
nasce aqui**. Os cinco atos são funções em transação, exercitadas pelo andaime e pelos testes; ligá-los
a uma rota é o que exige autenticação, autorização por perfil e registro da execução (SPEC
`autorizacao/004`), que ainda não existem. Fazer a rota agora seria abrir exceção de rota aberta para
**escrita** — onde ela custa caro — e refazê-la protegida depois. A seção entra conferível: mostra o
estado, os diálogos abrem com tudo calculado, e o submit não tem destino, como o modal de nova
unidade (SPEC 012). *Consequência aceita:* dá para ver e testar a página inteira, e não dá para mudar
nada por ela — quem produz os estados é o `ficticios.py`, chamando os atos pela mesma porta que a
rota vai chamar.

**A lista de candidatos e a lacuna proposta são calculadas no render da seção, e o toggle não tem
rota.** As duas listas — a da unidade do substituído e a ampliada — cabem numa consulta cada, são
dezenas de servidores, e ambas filtram pelo **período padrão da designação**, que não muda enquanto o
diálogo está aberto. Renderizadas juntas, o toggle só troca qual aparece; uma rota de alcance
existiria para recalcular algo que não muda.

**O andaime usa a mesma porta da tela.** O `ficticios.py` cria impedimento chamando os atos desta
SPEC, e não o model direto, pelo motivo que a SPEC 014 já aplicou aos atos de titularidade: quando a
criação passar a validar ou registrar o ato (épico `autorizacao`), o andaime não pode ser o caminho
que escapa. E, como a carga é repetível, a limpeza apaga os impedimentos fictícios — as substituições
caem junto, pela relação — e reativa quem ela mesma exonerou.

**O que esta SPEC deve à SPEC 016 é a leitura da substituição vigente.** A 014 entregou o
`EstadoDaDirecao` e o avaliador, mas não a função que monta o estado a partir do banco — ela lê
`Substituicao`, que só passa a existir aqui. A montagem fica para a 016, que é a primeira a
consumi-la e já tem titular e substituto carregados para a tela; escrevê-la aqui seria função sem
chamador. O que atravessa é a leitura da substituição vigente, a mesma que a página do servidor usa
para dizer quem cobre quem — uma função nos dois lugares, em vez de um predicado de vigência copiado
por tela.

## Peças de referência a compor
- `@apps/user_admin/models/impedimentos.py` → `Impedimento` e `TipoImpedimento`: o impedimento já
  existe e não muda de forma; o que ganha aqui é o predicado de vigência compartilhado e um dono
  para a substituição.
- `@apps/user_admin/models/user.py` → `Perfil.esta_impedido`: a leitura derivada que já existe e à
  qual `em_exercicio` e `exonerado` se somam. E `Perfil.e_titular` (SPEC 014): a marca que a
  designação **não** toca. `is_active` já está no model desde a SPEC 001.
- `@apps/user_admin/models/titularidade.py` (SPEC 014) → `cargo_titulariza`: o precedente de regra
  morando ao lado dos models e usada por `Perfil.clean` — é onde o predicado de período se encaixa.
- `@services/domain/titularidade/` (SPEC 014) → `EstadoDaDirecao` e `avaliar_direcao`: a leitura de
  quem dirige hoje já existe e é pura; o que falta a ela é o dado desta SPEC.
- `@apps/user_admin/titularidade.py` (SPEC 014) → `definir_titular` / `destituir_titular`: o
  precedente de "ato é função em transação, e há um caminho só" que os atos de exercício repetem.
- `@templates/user_admin/perfil_form.html` e os partials `_secao_identificacao.html` /
  `_secao_lotacao.html`: a seção nova é mais uma seção do mesmo organismo, não uma tela.
- `@templates/user_admin/partials/_modal_nova_unidade.html`: modal por checkbox nativo, irmão do
  formulário e nunca dentro dele (SPEC 012) — é o padrão que os modais desta SPEC repetem.
- `@apps/user_admin/schemas.py`: DTO construído na view, com o `PydanticValidationMiddleware`
  respondendo pelo erro; nada de `try/except` na view.
- `@apps/user_admin/views.py` → `editar_perfil` e `@apps/user_admin/context.py` →
  `contexto_editar_perfil`: a rota que já renderiza a página do servidor e o contexto em que a seção
  entra. Nenhuma rota nova nesta SPEC.
- `@apps/user_admin/ficticios.py`: o andaime da área administrativa — `_impedir` e
  `_limpar_impedimentos` já existem e passam a chamar os atos desta SPEC; `_titularizar` (SPEC 014)
  é quem diz quais afastados são titulares.
- Skills `componentes-frontend` (Atomic Design e o styleguide), `escrever-testes` (marker `banco`) e
  `test-django-views`.

## Mock de validação
`SPECS/user_admin/015-mock-exercicio-e-substituicao.html`, sobre o canvas administrativo vivo.

A seção de exercício nos **dez** estados que precisa cobrir:

1. **Em exercício**, sem impedimento registrado.
2. **Em exercício, com impedimento futuro** — e já com substituto designado: a tela precisa dizer que
   a pessoa **está na cadeira** enquanto mostra o afastamento que vem.
3. **Afastado sem substituto.**
4. **Titular afastado sem substituto** — o alarme de unidade sem direção, que só ganha código com a
   SPEC 016.
5. **Afastado com um substituto só**, cobrindo o afastamento inteiro — o caso comum.
6. **Afastamento com substitutos em sequência** — uma encerrada, uma vigente, uma por vir. É o estado
   que carrega o **histórico**, e o que ele exige do desenho é **ordem cronológica legível** e três
   presenças distinguíveis sem cor nova: o que passou recua (opacidade), o que vale hoje está em
   foco, o que vem tem a data à frente. Só as duas últimas têm ações.
7. **Afastado com a substituição fora do ar** — ela existe, mas começa depois ou já terminou: hoje
   ninguém responde pelo cargo, e se o afastado é o titular a unidade está sem direção do mesmo
   jeito. O desenho precisa de três coisas aqui: que o **cartão não suma** (o vínculo existe, some só
   o presente dele), que o período apareça, e que a ausência de hoje seja legível sem ler datas — a
   **calha da cobertura** com o poço vazio à direita, uma tarja âmbar dentro do próprio poço da
   substituição, e o alarme vermelho da unidade acima dos cartões, idêntico ao do estado 4. O botão
   de designar aqui propõe **o buraco**, não o afastamento inteiro — e a calha é o que mostra qual.
8. **Exonerado.**
9. **Afastado sem cargo em comissão** — onde o caminho de designar **não tem peça**, em vez de botão
   desabilitado.
10. **O outro lado** — a página de quem substitui, com o período da substituição.

Mais os **quatro** modais — o segundo em duas variantes:

- **Registrar impedimento** — o aviso diz que a saída da cadeira acontece na data de início e que o
  retorno acontece sozinho no fim.
- **Designar substituto** — com **de qual impedimento** numa placa fixa no topo do diálogo: é placa e
  não campo porque o botão que abre o modal mora **dentro do cartão** de um impedimento, então a
  pergunta já vem respondida e não se reescolhe aqui o que foi escolhido lá. E com o **período da
  substituição** (*Substitui a partir de* / *Substitui até*), dois campos de data **já preenchidos
  com o primeiro pedaço descoberto** do afastamento — em branco obrigariam a ler a calha e digitar de
  volta o que o servidor já calculou, e o caso comum passa a ser só confirmar. Editáveis, e a dica
  diz que o período só pode ser mais estreito que o afastamento e o que acontece com o resto dele se
  for; com afastamento indeterminado, *Substitui até* vem vazio, e vazio continua querendo dizer
  indeterminado. Os **dois alcances ficam no mesmo diálogo**: o toggle de outras unidades troca a
  lista sob um rótulo só, e a ampliada abre pela unidade superior.
- **Trocar substituto** — a **variante** do anterior, não outro diálogo: na aplicação é o mesmo
  partial, com os trechos que dependem de já haver substituto. Muda o título, o verbo do botão e o
  preenchimento (o atual vem selecionado e as datas vêm gravadas, porque campo vazio aqui diria
  "ocupa a lacuna" quando o período já existe), e ganha um campo que o de designar não tem: **a data
  em que a nova assume**. É dela que sai a véspera em que a anterior é encerrada, e o diálogo diz as
  duas coisas — quem sai e até quando fica registrado, quem entra e a partir de quando.
- **Encerrar substituição** — confirmação curta, dizendo o que acontece com o registro: em curso,
  termina hoje e **continua na lista**; ainda não iniciada, **some**. Mais o aviso de que o
  afastamento fica sem ninguém respondendo a partir daí.
- **Voltar ao exercício** — confirmação pura, porque o ato tem efeitos que não estão no seu
  enunciado: encerra os impedimentos vigentes hoje e acerta as substituições deles.

**Dois átomos novos e uma molécula, e a divisão é a do Atomic Design (§3.4):**

- **`.etched-line`** — um fio de gravação no tom de repouso do `.etched`.
- **`.etched-line-inked`** — o mesmo fio cheio de água, com as **pontas esmaecendo**.
- **`.calha-cobertura`** — a molécula: o afastamento inteiro como bandeja funda, com os dois fios
  correndo dentro e os nomes de quem responde por cada trecho.

Os átomos são **só material**: não posicionam nem dimensionam nada — quem decide onde o fio corre e
por quanto é a molécula. E a molécula é **só composição e medida**: material nenhum nasce nela — o
poço é o `.card-well`, os fios são os átomos, o âmbar é a cor semântica do tema.

A bandeja **nunca se preenche**: o poço continua poço de ponta a ponta, e o que muda de estado é o
fio no fundo dele — um material só mudando ao longo do tempo, não duas peças disputando a leitura. Os
nomes ficam nos **rótulos** abaixo de cada trecho, sem discos sobre a linha, que empilhariam peça
sobre a informação que o rótulo e a lista logo abaixo já dão.

*O esmaecimento das pontas não é enfeite:* entre dois trechos vizinhos de estados diferentes, uma
aresta viva leria como **duas peças encostadas**, e o que existe é **um fio só** — a transição faz a
leitura ser "aqui a tinta acaba". Ela ocupa **20% de cada ponta**, em porcentagem e não em px, para
ser proporcional ao trecho: um curto esmaece na mesma medida que um longo, em vez de sumir sob uma
ponta de tamanho fixo. A queda não é rampa reta — interpolação linear deixa uma "quina de luz" no
ponto em que começa, que é justamente a aresta que a peça existe para não ter.

*E a ponta nunca chega ao transparente:* ela para num **tom claro da mesma tinta**. Indo até zero, o
que aparece na borda é o vidro branco por baixo, e o trecho ganha uma auréola clara exatamente onde a
tinta acaba. Duas consequências de implementação: o esmaecimento é do **próprio fundo**, em
gradiente, e o brilho vem de `drop-shadow` (que segue o canal alfa e acompanha o tom), nunca de
`box-shadow` (que ignoraria o gradiente e desenharia a sombra da caixa inteira).

*Feita do zero em Tailwind, e não com o `steps` do daisyUI:* o steps mede **ordem**, e o trilho entre
dois nós tem sempre a mesma largura. Aqui a **largura é o que informa** — um buraco de três semanas
precisa parecer três vezes maior que um de uma. Do zero são cinco regras, todas de material que já
existe.

*Sem cor semântica nos fios nem na calha:* a diferença entre tinta e sulco é de **estado do mesmo
material**, contínua e comparável ao longo da linha, não um glifo tentando dizer sozinho um estado do
sistema — que é o que o tema veda. Quem **nomeia** o buraco é o **rótulo em âmbar** abaixo dele, e é
ele que garante a leitura sem depender de perceber diferença de tom. O vermelho continua fora: é da
unidade sem direção, não do trecho.

*Prazo indeterminado:* a calha **não termina, se dissolve** — uma máscara apaga a ponta direita.
Desenhar um fim mentiria sobre um fim que não existe, pela mesma razão que `data_fim` é nulo em vez
de uma data-sentinela.

*Quando ela aparece:* só com **mais de um trecho**. Um substituto cobrindo o afastamento inteiro é
uma calha cheia de ponta a ponta — não informa nada que a linha da pessoa já não diga.

*A escala é o que dá sentido à peça, e é regra, não acabamento:* `left` e `width` de cada trecho são
a **fração de dias** que ele ocupa no afastamento — `left = (início do trecho − início do
afastamento) / total` e `width = dias do trecho / total`, ambos **inclusivos das duas pontas**.
`trechos()` devolve os pedaços em ordem, com período e ocupante; a conversão para porcentagem é da
**view** (`context.py`), não do domínio — é medida de renderização, não conhecimento sobre território
ou processo. Com impedimento indeterminado não há denominador: a régua vai até a **última data
conhecida** e o resto dissolve, com a mesma máscara.

**A peça que estrutura a seção é um cartão, e ele não é classe nenhuma.** Cada impedimento em aberto
é um `.glass-panel` **erguido** sobre o poço da seção, com dois `.card-well` **afundados** dentro: um
para o afastamento, outro para **as substituições dele**. A alternância de material é o que diz
**pertencimento** — o substituto não está *perto* do impedimento, está *dentro* dele —, e é isso que
resolve o caso de dois afastamentos em aberto, onde recuo e proximidade resolveriam mal. O segundo
poço é uma **lista**, porque um afastamento tem uma agenda e não um substituto; vazio, ele continua
lá com o botão de designar dentro; sem cargo em comissão, ele **não existe**. Nada disso vira classe:
é composição de materiais que já estão no tema.

Duas moléculas nascem aqui: `.linha-pessoa` (pessoa identificada em uma linha, que se repete no
substituto designado e em quem se substitui) e `.tarja-vinculo`, cujo papel é o de **placa de aviso
assentada num poço** — o poço da seção, o do substituto dentro do cartão ou o painel espesso de um
modal —, com duas variantes: `-pendente`, para o vínculo que existe mas **não está valendo hoje**, e
`-critica`, para a unidade sem direção. **Escolher o substituto não inventa peça**: é o campo de
seleção de vidro da SPEC 011 (`data-select-onsen`), o mesmo da lotação — lista fechada de uma pessoa
é exatamente o que ele resolve, com filtro por texto, teclado e o `<select>` seguindo como o campo.

**A escala semântica fica fixada aqui**, e vale para as duas SPECs: verde é estar na cadeira; âmbar é
a pessoa fora dela, por impedimento ou por exoneração; **vermelho é só a unidade sem direção** — a
única condição da tela que trava competência administrativa. O selo do exercício descreve a pessoa e
nunca fica vermelho; quem escala é a tarja, porque quem está errado é o estado da unidade, não o
afastamento. O selo diz **a causa** quando a pessoa está fora: afastado e exonerado são o mesmo âmbar
e palavras diferentes.

O único token novo é de raio: **`--radius-placa` (0.625rem)**, entre `--radius-field` e
`--radius-box`. A placa assentada dentro de um poço não é campo nem caixa — quer ficar retangular,
mas quina viva não pertence a um material em que toda aresta é luz. Vira token, e não medida solta na
molécula, porque a titularidade (SPEC 014) assenta placas no mesmo poço e elas precisam da mesma
quina.

Aprovado o mock, as moléculas migram para `static/src/tema-dimap.dev.css` na camada de moléculas — a
calha entre elas —, **`.toggle-onsen`, `.etched-line` e `.etched-line-inked` para a camada de
átomos**, o raio entra em `html[data-theme="dimap"]` junto dos outros, e as peças são renderizadas no
styleguide da skill `componentes-frontend`, antes de qualquer template da aplicação usá-las. A calha
**não** depende dos `defs` de `#etched-onsen`: a tinta dela é fundo e sombra, não filtro SVG. Quem
depende é o toggle, cujo disco é gravação de verdade — sem os `defs`, ele continua lá, chapado.

> Consumo do raio: em Tailwind 4 é `border-radius: var(--radius-placa)` ou `rounded-(--radius-placa)`.
> O `rounded-[--x]` da v3 emite `border-radius: --x`, inválido, e cai em **raio zero** — os mocks de
> `autorizacao/006`, `007` e `008` estão de quina viva por isso e são corrigidos no mesmo porte.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md

# apps/user_admin/models/periodo.py — impedimento e substituição têm a mesma convenção de período
# (fim nulo = indeterminado). O predicado num lugar só: cinco leituras fazem esta mesma pergunta, e
# uma delas esquecendo o fim nulo faz o sistema responder duas coisas sobre a mesma pessoa.
def q_vigente_em(dia: date) -> Q:
    return Q(data_inicio__lte=dia) & (Q(data_fim__isnull=True) | Q(data_fim__gte=dia))


def q_em_aberto_em(dia: date) -> Q:
    """Vigente ou ainda por vir — é sobre estes que a tela oferece designar substituto."""
    return Q(data_fim__isnull=True) | Q(data_fim__gte=dia)
```

```python
# apps/user_admin/models/user.py
class Perfil(AbstractBaseUser, PermissionsMixin):
    # is_active já existe desde a SPEC 001 e não tinha outro uso: exonerado é quem não é mais
    # servidor da DIMAP, e isso é exatamente o que conta inativa significa — inclusive não entrar.
    @property
    def exonerado(self) -> bool:
        return not self.is_active

    @property
    def esta_impedido(self) -> bool:
        return self.impedimentos.filter(q_vigente_em(timezone.localdate())).exists()

    # Derivado, e de exatamente duas causas: coluna própria seria um terceiro valor capaz de
    # discordar das duas, e é essa discordância que a SPEC existe para tornar impossível.
    @property
    def em_exercicio(self) -> bool:
        return not self.exonerado and not self.esta_impedido
```

```python
# apps/user_admin/models/substituicao.py
class Substituicao(models.Model):
    # Várias por impedimento: o que a regra proíbe é sobreposição, não pluralidade — é assim que
    # uma pessoa cobre a primeira semana e outra a segunda.
    impedimento = models.ForeignKey(
        Impedimento,
        on_delete=models.CASCADE,
        related_name="substituicoes",
    )
    substituto = models.ForeignKey(
        "user_admin.Perfil",
        on_delete=models.PROTECT,
        related_name="substituicoes_exercidas",
    )
    # Período próprio, sempre contido no do impedimento: é o que permite substituir só parte do
    # afastamento e, ao mesmo tempo, ler a vigência da substituição sem compor com a dele.
    data_inicio = models.DateField()
    data_fim = models.DateField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            # A única coisa que não depende de outra linha, e por isso a única que o banco garante.
            models.CheckConstraint(
                condition=Q(data_fim__isnull=True) | Q(data_fim__gte=F("data_inicio")),
                name="substituicao_fim_nao_antecede_inicio",
            ),
        ]

    # Contenção no impedimento, não-sobreposição dos dois lados, cargo do substituído, exoneração
    # das duas pontas e as pontas sendo a mesma pessoa: tudo cruza linha, nada cabe em constraint.
    def clean(self) -> None: ...
```

```python
# services/domain/exercicio/models.py — os DTOs no models.py do submódulo, como nos demais
class Periodo(BaseModel):
    model_config = ConfigDict(frozen=True)

    inicio: date
    # Nulo = indeterminado, a mesma convenção dos models.
    fim: date | None


# Os dois papéis pedem coisas diferentes, e por isso são dois DTOs — não um com campos que só
# metade dos casos usa.
class Substituido(BaseModel):
    model_config = ConfigDict(frozen=True)

    perfil_id: int
    exonerado: bool
    tem_cargo_comissao: bool
    # Todas as que ele já recebe, deste impedimento e dos outros: duas simultâneas não dizem sob
    # qual competência o ato foi praticado, e a origem delas é indiferente para essa pergunta.
    # Ao validar uma substituição que já existe, ela própria fica de fora — senão conflita consigo.
    substituicoes_recebidas: tuple[Periodo, ...]


class Substituto(BaseModel):
    model_config = ConfigDict(frozen=True)

    perfil_id: int
    exonerado: bool
    # Substituir estando fora da própria cadeira é criar o vazio na origem.
    impedimentos: tuple[Periodo, ...]
    substituicoes_exercidas: tuple[Periodo, ...]


class Designacao(BaseModel):
    model_config = ConfigDict(frozen=True)

    periodo: Periodo
    periodo_do_impedimento: Periodo
    substituido: Substituido
    substituto: Substituto
```

```python
# services/domain/exercicio/periodos.py
def se_sobrepoem(a: Periodo, b: Periodo) -> bool: ...


def contem(externo: Periodo, interno: Periodo) -> bool:
    """O período da substituição nunca começa antes nem termina depois do impedimento."""
    ...


def lacunas(impedimento: Periodo, ocupados: tuple[Periodo, ...]) -> tuple[Periodo, ...]:
    """Os pedaços do afastamento sem ninguém respondendo. A primeira lacuna é o período que a
    designação propõe por padrão."""
    ...


class Trecho(BaseModel):
    model_config = ConfigDict(frozen=True)

    periodo: Periodo
    # Nulo = ninguém responde neste trecho. É o que a calha deixa sem tinta.
    substituto_id: int | None


def trechos(impedimento: Periodo, ocupados: tuple[Trecho, ...]) -> tuple[Trecho, ...]:
    """O afastamento fatiado em ordem, cobertos e descobertos alternados. Existe para a linha da
    cobertura não ser montada intercalando duas listas no template (§3.1)."""
    ...
```

```python
# services/domain/exercicio/designacao.py
class AvaliadorDesignacao:
    """Quem pode cobrir quem, e quando. Sem Django: a regra é a mesma no clean, na lista da tela e
    no teste."""

    def __call__(self, designacao: Designacao) -> bool: ...
```

```python
# apps/user_admin/exercicio.py — os atos e as leituras; mesma casa e mesmo padrão de
# titularidade.py (SPEC 014).
def registrar_impedimento(perfil: Perfil, dados: NovoImpedimento) -> Impedimento:
    """Grava o impedimento — que é, ele próprio, a saída do exercício, na data que ele declara."""
    # DTO, e não Impedimento pronto: é o que faz o andaime e a rota futura usarem a mesma porta.
    ...


def designar_substituto(impedimento: Impedimento, dados: NovaSubstituicao) -> Substituicao:
    """Período em branco vira a primeira lacuna do afastamento — o impedimento inteiro quando não há
    nenhuma outra substituição, inclusive com o fim nulo."""
    ...


def encerrar_substituicao(substituicao: Substituicao) -> None:
    """Em curso, termina hoje e fica registrada; ainda não iniciada, é apagada — registro sem fato
    não é histórico."""
    ...


def trocar_substituto(atual: Substituicao, dados: TrocaDeSubstituto) -> Substituicao:
    """Encerra a atual na VÉSPERA do dia em que a nova assume e designa a nova, na mesma transação.
    A véspera é o que evita tanto o dia com dois respondendo quanto a lacuna de um dia."""
    ...


def retornar_ao_exercicio(perfil: Perfil) -> None:
    """Encerra hoje TODOS os impedimentos vigentes — encerrar um só deixaria a pessoa fora pelo
    outro — e acerta as substituições: trunca a que está em curso, apaga as que não começaram."""
    ...


def substituicao_vigente(perfil: Perfil) -> "Substituicao | None":
    """Quem cobre este perfil hoje. É o que a SPEC 016 compõe com o titular da unidade."""
    return Substituicao.objects.filter(
        q_vigente_em(timezone.localdate()),
        impedimento__perfil=perfil,
    ).first()


def substituicao_que_exerce(perfil: Perfil) -> "Substituicao | None":
    """Quem este perfil está substituindo hoje — no máximo uma, pela não-sobreposição, e é o outro
    lado da mesma leitura."""
    return Substituicao.objects.filter(
        q_vigente_em(timezone.localdate()),
        substituto=perfil,
    ).first()


def substituicoes_do_impedimento(impedimento: Impedimento) -> QuerySet[Substituicao]:
    """A agenda do afastamento, em ordem — encerradas, vigente e futuras. É o histórico da tela, e
    ele não precisa de tabela nenhuma além desta."""
    return impedimento.substituicoes.order_by("data_inicio").select_related("substituto")


def candidatos_a_substituto(impedimento: Impedimento, periodo: Periodo) -> list[Perfil]:
    """Quem passaria no avaliador para este período. A mesma montagem de DTO que o clean usa — se a
    tela montasse a sua, "a mesma regra nos dois lugares" viraria promessa."""
    ...
```

```python
# apps/user_admin/schemas.py — o DTO de entrada dos atos, hoje construído pelo andaime e amanhã pela
# rota do épico de ações. A validação que depende de outras linhas é do clean, não daqui.
class NovoImpedimento(BaseModel):
    tipo: int
    data_inicio: date
    # Em branco = prazo indeterminado, a mesma convenção dos models.
    data_fim: DataOpcional = None


class NovaSubstituicao(BaseModel):
    substituto: int
    # A tela manda as datas já propostas; em branco continua valendo, porque é assim que o andaime
    # designa sem repetir o cálculo da lacuna.
    data_inicio: DataOpcional = None
    data_fim: DataOpcional = None


class TrocaDeSubstituto(BaseModel):
    substituto: int
    # "Assume em" — obrigatório, porque é a véspera dela que encerra a substituição que sai.
    data_inicio: date
    data_fim: DataOpcional = None
```

```python
# apps/user_admin/context.py — a seção entra no contexto da página que já existe; nenhuma view nova.
def contexto_editar_perfil(perfil: Perfil) -> dict[str, Any]:
    return ... | contexto_exercicio(perfil)
def contexto_exercicio(perfil: Perfil) -> dict[str, Any]:
    """A seção e os diálogos dela: os cartões dos impedimentos em aberto, a agenda de cada um, a
    lacuna que a designação propõe e os candidatos dos dois alcances."""
    ...


def _calha(impedimento: Impedimento) -> list[dict[str, Any]]:
    # left/width em porcentagem: medida de renderização, não conhecimento de domínio — trechos()
    # devolve períodos e a régua sai daqui.
    ...
```

```python
# apps/user_admin/ficticios.py
def _limpar_exercicio(self) -> None:
    # A carga é repetível: sem isso, o afastamento da vez passada se somaria ao desta.
    # As substituições caem junto com os impedimentos, pela relação.
    fic = Perfil.objects.filter(rf__in=FAIXA_RF_FICTICIA)
    Impedimento.objects.filter(perfil__in=fic).delete()
    fic.update(is_active=True)


def _impedir(self, perfil: Perfil, tipo: TipoImpedimento) -> None:
    # Pela mesma porta da tela: quando a criação passar a validar e registrar o ato (épico
    # autorizacao), o andaime não pode ser o caminho que escapa.
    registrar_impedimento(perfil, NovoImpedimento(tipo=tipo.pk, data_inicio=..., data_fim=None))
```

## Fora de escopo
- A **montagem** do `EstadoDaDirecao` a partir do banco e o **alarme** de unidade sem direção —
  SPEC 016, que compõe a leitura desta com o titular da 014 (ver Contexto).
- **O ato de exonerar** — SPEC própria. Aqui entram a leitura que depende do `is_active` e a
  renderização do estado; não entram o caminho na tela nem os efeitos sobre lotação e titularidade.
- Titularidade e o efeito do exercício sobre ela — SPEC 014; nada aqui altera `e_titular` nem a
  unicidade dele.
- Cadeia de substituição: substituto do substituto, e redesignação automática quando o substituto se
  impede. O substituto que se afasta durante a cobertura deixa o cargo sem quem responda — a leitura
  da direção (SPEC 016) enxerga isso e acende o alarme —, mas nada entra no lugar dele sozinho.
- Editar o impedimento (tipo e datas) ou excluí-lo pela tela — esta iteração **cria** e **encerra**,
  e encerrar é o ato de voltar ao exercício.
- **Editar uma substituição encerrada**, ou reabrir o período dela: o que passou fica como está.
- A seção lista os impedimentos **em aberto**; os afastamentos **já encerrados** não aparecem — e com
  eles fica de fora o histórico de substituições deles, que existe no banco mas não tem tela.
- **Garantia de banco para a não-sobreposição** (`ExclusionConstraint` com `daterange` e
  `btree_gist`): decidido no domínio, com o risco de escrita concorrente assumido (ver Contexto).
- Rotina que reconcilie exercício com impedimentos vencidos: não há o que reconciliar, porque não há
  marca gravada (ver Contexto).
- **As rotas de escrita dos atos** (registrar impedimento, designar, trocar, encerrar, voltar ao
  exercício) — épico de ações, onde nascem protegidas e com a execução registrada. Aqui os atos são
  funções, exercitadas pelo andaime e pelos testes, e os diálogos renderizam com o **submit sem
  destino**, como o modal de nova unidade (SPEC 012). Gravar o cadastro do servidor pela tela segue
  igualmente sem destino.
- Autenticação, autorização por perfil e registro da execução do ato — épico `autorizacao`.
- Qualquer efeito de autorização decorrente do exercício ou da substituição — épico `autorizacao`.
- Aplicar a migração: o agente gera, quem aplica é o usuário (CLAUDE.md §4).

## Testes (TDD)
Os quatro primeiros são domínio puro e rodam na suíte padrão; os demais carregam o marker `banco`,
declarado em `markers_obrigatorios`. São mais que o usual porque a garantia saiu do banco: o que
antes uma constraint fixava agora só existe se estes testes existirem.

- `test_periodos_com_fim_indeterminado_se_sobrepoem` — a comparação de períodos com `fim=None`, que é
  onde este tipo de regra costuma errar, e que agora é a **única** guarda da invariante:
  indeterminado cruza tudo que vem depois do seu início; períodos que se encostam pelas pontas
  (um termina no dia em que o outro começa) **se sobrepõem**, e um termina na véspera do outro, não;
  e a contenção recusa substituição que termine depois de um impedimento com fim definido. Sem banco.
- `test_trechos_e_lacunas_do_afastamento` — sem substituição nenhuma, há um trecho só, descoberto, e
  é o afastamento inteiro (fim nulo inclusive); com uma no meio, sobram as duas pontas descobertas;
  coberto de ponta a ponta, nenhuma lacuna e um trecho por substituição, na ordem. É daí que saem o
  período proposto por padrão e a calha da cobertura. Sem banco.
- `test_designacao_exige_substituido_com_cargo_e_sem_substituicao_no_periodo` — recusa o substituído
  sem cargo em comissão, o exonerado e o que já é substituído em período que cruza — venha a outra
  substituição **do mesmo impedimento ou de outro sobreposto**; aceita a que fica em sequência, sem
  cruzar. Sem banco.
- `test_designacao_exige_substituto_livre_no_periodo` — recusa quem está impedido no período, quem
  está exonerado, quem já substitui alguém em período que se cruza e o próprio substituído; aceita o
  substituto de outra unidade, com cargo em comissão próprio, e o que substitui outra pessoa em
  período que não cruza. Sem banco.
- `test_exercicio_deriva_do_impedimento_e_da_exoneracao` — sem impedimento e ativo, está em
  exercício; com impedimento vigente, não; **com impedimento vencido, volta sem que nada escreva**;
  com impedimento de início futuro, segue em exercício; inativo sem impedimento, fora.
  *(marker `banco`)*
- `test_substituicao_nasce_na_lacuna_do_afastamento_e_so_estreita` — em branco, a substituição fica
  com as datas do impedimento (fim nulo inclusive) quando é a primeira, e com a lacuna restante
  quando não é; informada mais estreita, é aceita; começando antes ou terminando depois do
  impedimento, é recusada. *(marker `banco`)*
- `test_um_afastamento_aceita_substitutos_em_sequencia` — duas substituições do mesmo impedimento,
  em períodos que não se cruzam, são aceitas e cada uma vigora no seu tempo; a que cruzaria é
  recusada. *(marker `banco`)*
- `test_afastado_pode_ficar_sem_substituto_vigente` — com a substituição ainda por começar ou já
  terminada, o perfil segue fora de exercício e `substituicao_vigente` responde `None` **mesmo
  havendo substituição gravada** para aquele impedimento; e responde a certa no dia em que uma delas
  vale. É este teste que fixa que a resposta não vem da existência da linha. *(marker `banco`)*
- `test_encerrar_substituicao_registra_ou_apaga` — em curso, ela termina hoje e continua na lista;
  ainda não iniciada, some. *(marker `banco`)*
- `test_trocar_substituto_encerra_a_anterior_na_vespera` — depois da troca há **duas** linhas: a
  anterior encerrada na véspera do dia em que a nova assume, e a nova a partir dele. Sem dia com
  dois vigentes e sem lacuna entre elas. *(marker `banco`)*
- `test_voltar_ao_exercicio_encerra_impedimentos_e_acerta_substituicoes` — encerrados **todos** os
  vigentes, o perfil volta a exercer; a substituição em curso termina hoje e as que não começaram
  são apagadas. *(marker `banco`)*
- `test_designar_substituto_nao_mexe_na_titularidade` — designado o substituto de um titular
  afastado, `e_titular` continua com o afastado e o substituto segue sem a marca; a leitura da
  direção (SPEC 014), montada sobre essas linhas, responde `SUBSTITUTO`. *(marker `banco`)*
- `test_secao_mostra_a_agenda_do_afastamento` — o cartão traz as substituições do impedimento em
  ordem, com a encerrada, a vigente e a futura distinguíveis; traz o impedimento futuro com o
  substituto já designado; e distingue afastado de exonerado. *(marker `banco`)*
- `test_modal_de_designar_propoe_a_lacuna_e_os_candidatos` — o diálogo do impedimento vem com as
  datas do primeiro pedaço descoberto (e *Substitui até* vazio quando o afastamento é
  indeterminado), com a lista da unidade do substituído sem quem está impedido ou cobrindo alguém no
  período, e com a lista ampliada abrindo pela unidade superior. *(marker `banco`)*
- `test_ficticios_deixam_os_estados_de_exercicio_exercitaveis` — depois da carga há titular afastado
  com substituto, titular afastado sem substituto, afastamento com substitutos **em sequência**,
  afastado com a substituição fora do ar, impedimento futuro já designado e exonerado; e rodar duas
  vezes não acumula afastamento. *(marker `banco`)*

## Patches

_Nenhum patch registrado até o momento._
