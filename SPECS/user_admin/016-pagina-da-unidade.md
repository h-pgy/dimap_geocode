---
spec: user_admin/016
versao: v3
atualizado_em: 2026-08-13
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: a montagem do `EstadoDaDirecao` passa a ser desta SPEC — a 014 a deixou de fora por ler uma
        `Substituicao` que ainda não existia (patch 001 dela) —, e o substituto vem da
        `substituicao_vigente` da SPEC 015, não de helper próprio
  - v3: os três atos de titularidade deixam de ganhar rota — os modais renderizam com o submit sem
        destino e os atos seguem sendo as funções da SPEC 014, como a 015 fixou para os atos de
        exercício, e com isso caem o Post/Redirect/Get e os dois testes de rota; o cargo mínimo
        passa a ler a coluna `exige_alta_administracao` do tipo (SPEC 014 v9) em vez do mínimo
        nulo; as peças da 015 deixam de ser porte pendente, porque já estão no tema; e a prosa foi
        reescrita, sem histórico de decisão
---

# SPEC user_admin/016 — A página da unidade: quem dirige aqui hoje, e os atos de titularidade

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como responsável pela DIMAP, quero abrir a página de uma unidade e ver, antes de qualquer outra
coisa, **quem responde por ela hoje** — e nomear, trocar ou destituir o titular ali mesmo —, para que
a vaga e o afastamento sem cobertura sejam cobrados pela tela em vez de descobertos quando alguém
precisa de uma assinatura.

## Critérios de aceite
- [ ] A unidade **tem página própria**, em rota de leitura para uma unidade existente, com duas
      seções **nesta ordem** — **Resumo** e **Direção** — e, ao fim, um botão grande e centrado que
      abre a edição. A rota nasce **aberta**, pela exceção ao §3.5 declarada na SPEC 013.
- [ ] A página tem **cabeçalho de identidade da unidade** — sigla, nome, tipo, nível, quantos
      servidores são lotados ali e o ponto na cor da unidade —, irmão do cabeçalho do servidor.
- [ ] O **Resumo** traz o que a unidade **é**, em texto — nome, sigla, tipo e o **cargo mínimo**
      exigido do titular, com o tipo que **exige alta administração** lendo-se "Alta administração"
      —, e, abaixo, a **bandeja de indicadores** com quantos servidores são lotados ali (com caminho
      para a listagem já filtrada) e qual é a unidade superior.
- [ ] A **Direção** responde "quem dirige aqui hoje" num **selo de quatro respostas**, que são as
      quatro da SPEC 014: titular, substituto, sem direção, sem titular. Titular e substituto
      aparecem **com foto ou iniciais** e **levam à página de cada um**, e a célula do titular
      ausente **é** a mensagem de erro, não um traço.
- [ ] As duas faltas são **acusadas em vermelho**, **antes** da bandeja de titular e substituto, e o
      texto diz a **causa e a saída**: sem titular, nomear; sem direção, designar substituto na
      página do titular.
- [ ] **Editar é modal**: os campos do cadastro (SPEC 012) aparecem preenchidos e **lidos**, e cada
      um só vira campo quando alguém abre o **lápis ao lado do valor** — o botão redondo de vidro da
      listagem, com o glifo gravado por dentro, que se entinta enquanto o campo está aberto. O campo
      aberto é **poço**, que é o que neste design system se lê como "escreve-se aqui".
- [ ] O que a **validação pode recusar** naquele campo é dito em **aviso âmbar dentro dele**, e só
      **enquanto ele está aberto**: consequência de ato não se escreve em cinza miúdo, nem fica
      avisando sobre o que ninguém vai mudar.
- [ ] **Definir, trocar e destituir** titular são três **modais** na página, com a lista restrita a
      quem pode titularizar aquela unidade (SPEC 014). **Nenhum candidato** não tem tela própria: o
      modal diz o que falta, em vez de abrir um campo vazio.
- [ ] **Nenhuma rota de escrita nasce aqui**: os quatro modais renderizam com o **submit sem
      destino**, e os atos seguem sendo as funções da SPEC 014, exercitadas pelo andaime e pelos
      testes.
- [ ] Há **como chegar** à página: a unidade da listagem de servidores (SPEC 013) leva a ela.
- [ ] A **seção de exercício do servidor** (SPEC 015) acusa a **unidade sem direção** quando o
      afastado é o titular e não há substituto em exercício.
- [ ] O design foi aprovado no **mock** antes de qualquer código de aplicação, e as peças novas foram
      **portadas** para `static/src/tema-dimap.dev.css` e renderizadas no styleguide antes de
      qualquer template da aplicação usá-las.

## Contexto e decisões de arquitetura

Iteração de **interface e orquestração**: nenhum model novo, nenhuma migração. O dado, a regra e os
atos de titularidade são da SPEC 014; a leitura de quem cobre o afastado é da SPEC 015. Aqui só se
lê o que elas decidem e se chamam as funções que elas expõem.

**A página da unidade nasce aqui, e é isso que justifica a SPEC.** A SPEC 012 entregou o formulário
de **cadastro** e deixou editar e listar unidades fora de escopo: existe rota de criar, e o partial
dos campos só tem `placeholder`. A unidade ganha agora a página que a SPEC 013 deu ao servidor —
mesma moldura, mesmo organismo em seções de poço. O partial dos campos passa a aceitar uma
instância: placeholder vira valor e a opção corrente vira `selected`; sem instância ele segue exato
como está, e o modal de nova unidade continua servido por ele.

**A ordem é a da pergunta: Resumo, Direção, editar.** O Resumo é o que a unidade **é** e o quanto ela
tem — respostas de texto numa placa, mais o que se conta ou se navega na bandeja. A Direção é o que
se veio saber. Editar é o que quase ninguém veio fazer: sai da página e vira **modal**, atrás de um
botão grande e centrado no fim. Com isso **nada na página é campo**, e some o botão de salvar solto
no rodapé, que numa tela de leitura nunca se sabe a que se refere. Consequência aceita: tipo e cargo
mínimo aparecem duas vezes — no Resumo como texto, no modal como campo —, o que poupa quem só lê de
abrir o modal para saber o porte da unidade.

**Dentro do modal, o campo nasce lido e o lápis o abre.** O campo nasce como rótulo gravado e valor
em texto, com o **botão redondo de vidro** (SPEC 013) ao lado **do valor**, não do rótulo, porque o
que se edita é o valor. Abrir entinta o glifo gravado e rebaixa o valor em **poço**, que é a
gramática de campo do design system. O estado é `checkbox` + `:has()`, como o cabeçalho afundado da
tabela e a paleta da SPEC 005 — nenhum estado de interface em JavaScript. Efeito colateral que se
quer: o que está aberto é o que se pretende mudar, e isso se vê sem ler os valores.

**Consequência de ato é aviso, não dica — e vive dentro do campo.** O que a validação recusa — mudar
o tipo para um que o titular não satisfaça, mudar a unidade superior contra o nível ou as vedações —
é a **tarja âmbar** da SPEC 015, com glifo, e não o `.form-field-hint`, que é cinza miúdo de apoio.
Cada aviso mora **dentro do campo a que pertence** e só aparece quando aquele campo é aberto: fixo no
rodapé da seção, ele avisaria o tempo todo sobre o que ninguém vai mudar — e um aviso que está sempre
lá deixa de ser lido.

**Dentro da Direção, o alarme vem antes da bandeja.** A notícia precede quem a explica: primeiro
"esta unidade está sem quem responda por ela", depois as células que mostram o titular afastado e o
substituto que não existe. Invertido, a tela pediria que o leitor descobrisse sozinho o que a placa
vermelha ia lhe dizer.

**O estado vem do domínio; o template escolhe a peça.** A view monta o `EstadoDaDirecao` e recebe a
`Direcao` (SPEC 014); o template acende selo e alarme pelo valor do enum. Remontar a causa no
template, com `{% if %}` sobre titular, exercício e substituição, duplicaria em linguagem de
apresentação exatamente a decisão que o domínio existe para concentrar.

**A montagem do `EstadoDaDirecao` é desta SPEC, e não repete consulta.** A orquestração já carrega
titular e substituto para renderizar as `.linha-pessoa`, e montar o DTO sobre eles é uma linha —
enquanto uma função que recebesse a unidade refaria as mesmas duas consultas. O substituto vem de
`substituicao_vigente` (SPEC 015), e não de um filtro escrito aqui: "há substituição vigente hoje"
nunca é respondido pela existência da linha, e o predicado de data não se copia por tela.

**A lista de candidatos é filtro no banco mais o predicado do domínio.** Perfis lotados na unidade
com cargo em comissão saem de uma consulta; quem serve, de `cargo_titulariza` (SPEC 014) — a mesma
regra que o `clean()` usa, sem cópia em `QuerySet`. Lista vazia **não é erro de tela**: é o
organograma dizendo que ninguém ali tem cargo para dirigir a unidade, e o modal diz o que falta e
onde se resolve (o cadastro do servidor), porque um `<select>` vazio não explicaria nada.

**A tela é leitura: nenhuma rota de escrita nasce aqui.** Os três atos de titularidade já existem
como funções em transação (SPEC 014), exercitadas pelo `ficticios.py` e pelos testes; ligá-los a uma
rota é o que exige autenticação, autorização por perfil e registro da execução, que ainda não
existem. Fazer a rota agora seria abrir exceção de rota aberta para **escrita** — onde ela custa caro
— e refazê-la protegida depois. Os modais renderizam com o **submit sem destino**, como o de nova
unidade (SPEC 012) e os da SPEC 015. *Consequência aceita:* dá para ver e testar a página nos quatro
estados da direção, e não dá para mudar nada por ela — quem produz os estados é o andaime, chamando
os atos pela mesma porta que a rota vai chamar.

**O cargo mínimo aparece em padrão, não em número.** O organograma fala "CDA-IV", não "nível 4": a
orquestração lê no catálogo um cargo de chefia do nível mínimo do tipo e mostra o `padrao` dele, em
vez de escrever a sigla da escala no template — que seria copiar dado de seed para dentro da
apresentação. O tipo que declara `exige_alta_administracao` lê-se **"Alta administração"** na mesma
célula: é exigência, não ausência, e por isso não escala para vermelho.

**A vaga é da unidade, e o alarme do afastamento é das duas telas.** A página da unidade acusa as
quatro respostas porque é o único lugar onde elas cabem juntas — na vaga não há servidor a quem
ancorar aviso nenhum. Já o titular afastado sem substituto aparece **também** na página dele, onde
está o caminho da saída: designar quem cubra. Mesma leitura, mesma peça, dois lugares.

**Nada de peça inventada, e duas moléculas novas.** Titular e substituto são a `.linha-pessoa`, o
alarme é a `.tarja-vinculo-critica`, o rosto é o `_imagem_perfil.html`, os modais são o `checkbox` da
SPEC 012, o campo de escolha é o select de vidro da SPEC 011, a gravação e o par repouso/entintado do
lápis são da SPEC 013 e a placa de resumo é a placa de gelo com rótulo e valor. Nascem a **bandeja de
indicadores** (`.stats-onsen`, com a variante `.stat-vaga`), que é o `stats` do daisyUI vestido de
placa fina, e o **campo que se abre para edição** (`.campo-onsen`) — e as duas são patrimônio do
design system antes de serem markup de template.

## Peças de referência a compor
- `@services/domain/titularidade/` (SPEC 014) → `Direcao`, `EstadoDaDirecao` e `avaliar_direcao`: a
  leitura de quem dirige hoje, pura e testada; esta SPEC só monta o estado que ela lê.
- `@apps/user_admin/titularidade.py` (SPEC 014) → `definir_titular` / `destituir_titular`: os atos
  em transação, que esta SPEC não reimplementa e não expõe por rota.
- `@apps/user_admin/models/titularidade.py` (SPEC 014) → `cargo_titulariza`: a mesma adequação que
  os `clean()` usam, e que a lista de candidatos consulta.
- `@apps/user_admin/exercicio.py` (SPEC 015) → `substituicao_vigente`: como se chega ao substituto
  de hoje. E `Perfil.em_exercicio`, que diz se titular e substituto estão na cadeira.
- `@templates/user_admin/partials/_secao_exercicio.html` e `@apps/user_admin/context.py` →
  `contexto_exercicio` (SPEC 015): a seção do servidor que ganha o alarme de unidade sem direção.
- `@templates/user_admin/unidade_form.html` e `@templates/user_admin/partials/_campos_unidade.html`:
  as três seções de campos já existem e são partial próprio; o que falta é renderizá-las com
  instância.
- `@templates/user_admin/partials/_identidade_perfil.html`: o cabeçalho de identidade do servidor —
  o da unidade é o irmão dele, não uma invenção.
- `@templates/user_admin/partials/_imagem_perfil.html`: foto ou iniciais já resolvidas (SPECs 004 e
  006).
- `@templates/user_admin/partials/_modal_nova_unidade.html`: modal por checkbox nativo, irmão do
  formulário e nunca dentro dele (SPEC 012) — o padrão que os quatro modais repetem.
- `.etched` e `.etched-rotulo` (SPEC 013): a gravação e o par repouso/entintado que o lápis repete —
  e os filtros SVG de que ela depende, já no `base.html`.
- `.linha-pessoa`, `.tarja-vinculo` / `.tarja-vinculo-critica` e `--radius-placa` (SPEC 015), já no
  tema e no styleguide; `.card-well`, `.glass-panel`, `.avatar-glass`, `.dot-unidade`, `.btn-onsen` /
  `.btn-glass`, `.select-glass` + `data-select-onsen` (SPEC 011) e `.text-overline`.
- `@apps/user_admin/views.py` + `@apps/user_admin/context.py` + `@apps/user_admin/schemas.py`: view
  fina, função de contexto e DTO construído na view, com o `PydanticValidationMiddleware`
  respondendo pelo erro.
- `@apps/user_admin/paleta.py` → `hex_da_cor`: o slug da cor da unidade vira hex na borda do app.
- `@templates/user_admin/partials/_corpo_servidores.html` e a query string da listagem (SPEC 013): a
  coluna de unidade vira o caminho de ida, e "ver na listagem" é o caminho de volta, com o filtro já
  aplicado.
- `@apps/user_admin/ficticios.py` (SPECs 014 e 015): os titulares marcados, a unidade deixada vaga e
  o titular afastado com e sem substituto são o que torna esta página exercitável nos quatro estados.
- Skills `componentes-frontend` (Atomic Design e o styleguide), `daisyui` (o componente `stats`),
  `escrever-testes` (marker `banco`) e `test-django-views`.

## Mock de validação
`SPECS/user_admin/016-mock-pagina-da-unidade.html`, sobre o canvas administrativo. A seção de direção
nos **quatro** estados — dirigida pelo titular; dirigida pelo substituto; sem direção; sem titular —,
a página inteira nas suas duas seções de leitura (Resumo e Direção) e os **quatro** modais: editar
unidade (com o campo nos dois estados, lido e aberto, e o aviso âmbar da hierarquia), definir titular
(com o caso de **nenhum candidato**, que a lista vazia sozinha não explicaria), trocar titular (com o
aviso de que o anterior é destituído no mesmo ato, inclusive afastado) e destituir (o ato que abre a
vaga).

**A escala semântica é a da SPEC 015, aplicada do lado da unidade:** verde é a unidade dirigida, por
quem for; vermelho é a unidade sem quem responda por ela. O âmbar não aparece na seção — ele descreve
a **pessoa** afastada, e a unidade só se importa com o que o afastamento deixa em aberto; nos modais
ele tem o outro papel que a 015 já lhe deu, o de consequência do ato que se vai confirmar. O selo
**não concorda em gênero** com quem dirige: o perfil não guarda gênero gramatical, e errar o de uma
pessoa real é pior do que a forma fixa.

Duas moléculas nascem. A primeira é a **`.stats-onsen`**, o `stats` do daisyUI vestido de placa. O
componente dá a grade, os rótulos e a figura; o design system dá a pele — a bandeja é uma placa de
gelo **fina** e cada indicador é um poço, compostos no HTML, e é a alternância poço → placa → poço
que mantém o degrau legível. Fina, e não espessa: o gelo espesso existe para separar figura de fundo
sobre interface escura (SPEC 011), e aqui a bandeja está entre dois brancos — o poço da seção
embaixo, os poços das células em cima —, onde empilhá-lo fecha a vista. A placa de resumo, vizinha de
poço, usa a mesma espessura pelo mesmo motivo. A classe nova cuida só do que é do componente:
derrubar o fundo opaco do daisyUI, dar o respiro entre os poços e trocar o traço divisor por luz. A
variante `.stat-vaga` é a célula do titular quando não há titular: em vez de campo vazio — que se lê
como "ainda não carregou" — a célula **é** a mensagem de erro.

A segunda é o **`.campo-onsen`**: rótulo gravado e valor em texto no repouso, poço e lápis entintado
quando aberto. Ela não inventa material nenhum — o sulco é o `.etched` da SPEC 013, o poço é a sombra
do `.card-well` e o campo por dentro é o `.input-glass`/`.select-glass` de sempre; o que a classe faz
é ligar os três a um estado de `checkbox`.

Nenhum token novo em nenhuma das duas: raio, materiais e escalas são os existentes. E a placa de
resumo **não é peça nova**: é a placa de gelo com uma grade de rótulo e valor, porque o que a unidade
é são respostas de texto — a bandeja fica para o que se conta ou se navega.

Aprovado o mock, `.stats-onsen` (com `.stat-vaga`) e `.campo-onsen` migram para
`static/src/tema-dimap.dev.css` na camada de moléculas e são renderizadas no styleguide da skill
`componentes-frontend`, antes de qualquer template da aplicação usá-las. O que o mock repete da SPEC
015 — o raio da placa, a linha de pessoa, a tarja — **não** se porta daqui: já está no tema.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md

# apps/user_admin/context.py
def contexto_unidade(unidade: Unidade) -> dict[str, Any]:
    titular = unidade.titular
    # A vigente vem da SPEC 015: o filtro por data não se copia por tela.
    substituicao = substituicao_vigente(titular) if titular else None
    substituto = substituicao.substituto if substituicao else None
    return (
        contexto_fundo_admin()
        | _catalogos_de_unidade()
        | {
            "unidade": unidade,
            "titular": titular,
            "substituto": substituto,
            # O template acende selo e alarme pelo enum; a causa é decidida no domínio.
            "direcao": avaliar_direcao(_estado_da_direcao(titular, substituto)),
            "candidatos": candidatos_a_titular(unidade),
            "cargo_minimo": _rotulo_do_minimo(unidade.tipo),
            "total_lotados": unidade.perfis.count(),
        }
    )
```

```python
# apps/user_admin/context.py — a montagem que a SPEC 014 deixou de fora (patch 001 dela): sobre o
# titular e o substituto que a tela já carregou, sem refazer as duas consultas.
def _estado_da_direcao(
    titular: Perfil | None,
    substituto: Perfil | None,
) -> EstadoDaDirecao:
    return EstadoDaDirecao(
        tem_titular=titular is not None,
        titular_em_exercicio=bool(titular and titular.em_exercicio),
        # O substituto fora de exercício não cobre ninguém: a unidade fica sem direção.
        substituto_do_titular_em_exercicio=bool(substituto and substituto.em_exercicio),
    )
```

```python
# apps/user_admin/context.py
def candidatos_a_titular(unidade: Unidade) -> list[Perfil]:
    """Quem a unidade pode titularizar: o filtro estreita, o domínio decide."""
    lotados = Perfil.objects.filter(
        unidade=unidade,
        cargo_comissao__isnull=False,
    ).select_related("cargo_comissao")
    return [
        perfil
        for perfil in lotados
        if cargo_titulariza(
            perfil.cargo_comissao,
            exige_alta_administracao=unidade.tipo.exige_alta_administracao,
            nivel_minimo=unidade.tipo.nivel_minimo_titular,
        )
    ]
```

```python
# apps/user_admin/context.py
def _rotulo_do_minimo(tipo: TipoUnidade) -> str:
    # O organograma fala em padrão de cargo, não em número de nível.
    if tipo.exige_alta_administracao:
        return ROTULO_ALTA_ADMINISTRACAO
    cargo = CargoComissao.objects.filter(
        e_chefia=True,
        nivel=tipo.nivel_minimo_titular,
    ).first()
    return cargo.padrao if cargo else ""
```

```html
<!-- templates/user_admin/partials/_secao_direcao.html -->
{% if direcao == "sem_titular" %}
  {% include "user_admin/partials/_alarme_direcao.html" with titulo=alarme_sem_titular %}
{% elif direcao == "sem_direcao" %}
  {% include "user_admin/partials/_alarme_direcao.html" with titulo=alarme_sem_direcao %}
{% endif %}
```

## Fora de escopo
- **As rotas de escrita** dos três atos de titularidade e do cadastro da unidade — épico de ações,
  onde nascem protegidas e com a execução registrada (ver Contexto). Aqui os modais renderizam com o
  submit sem destino, como na SPEC 015.
- A **regra e o dado** da titularidade: models, índice, adequação, o **avaliador** da direção e as
  funções de ato são da SPEC 014. Daqui é só a **montagem** do `EstadoDaDirecao` que o avaliador lê
  (patch 001 da 014).
- **Listagem de unidades**, criar unidade por esta página e criar **tipo** de unidade: a ida para cá
  é pela listagem de servidores, e cadastrar unidade continua sendo a tela da SPEC 012.
- **Desde quando** a unidade está vaga, e histórico de quem já dirigiu: exigiria guardar a data da
  destituição (fora de escopo na SPEC 014) — a tela diz que falta, não desde quando.
- Escolher **quem responde** pela unidade vaga: a tela diz que o superior responde, mas nomeá-lo é
  regra do épico `autorizacao`.
- **Gravar campo a campo** pelo lápis: abrir um campo é gesto de tela, não requisição.
- Editar, encerrar ou excluir impedimento e substituição pela página da unidade — são atos da SPEC
  015, na página do servidor.
- Autenticação, autorização por perfil e **registro** da execução do ato — épico `autorizacao`.

## Testes (TDD)
Todos fixam contrato HTTP/partial e tocam o banco: carregam o marker `banco`, declarado em
`markers_obrigatorios`. O domínio da direção e da adequação já é testado sem banco na SPEC 014 e não
se repete aqui.

- `test_pagina_da_unidade_traz_o_resumo_e_quem_dirige` — GET devolve 200 com nome, sigla, tipo e
  cargo mínimo no resumo, a unidade superior na bandeja, o titular em exercício no selo, e os campos
  do cadastro preenchidos no modal de edição. *(marker `banco`)*
- `test_pagina_distingue_as_duas_faltas` — unidade vaga acusa "sem titular"; titular afastado sem
  substituto acusa "sem direção"; com substituto em exercício, nenhuma das duas é acusada.
  *(marker `banco`)*
- `test_modal_lista_so_quem_pode_titularizar` — a lista traz a chefia que satisfaz o mínimo do tipo e
  não traz o assessor de nível alto, o servidor sem cargo em comissão nem quem é de outra unidade;
  sem nenhum candidato, a página traz o aviso em vez do campo. *(marker `banco`)*
- `test_secao_do_servidor_acusa_unidade_sem_direcao` — a página do titular afastado sem substituto
  acusa a unidade sem direção, e para de acusar quando há substituto em exercício. *(marker `banco`)*

## Patches

_Nenhum patch registrado até o momento._
