---
spec: user_admin/016
versao: v1
atualizado_em: 2026-08-11
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
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
      abre a edição. A rota nasce **aberta**, exceção declarada aqui nos mesmos termos das SPECs 013
      e 015.
- [ ] A página tem **cabeçalho de identidade da unidade** — sigla, nome, tipo, nível, quantos
      servidores são lotados ali e o ponto na cor da unidade —, irmão do cabeçalho do servidor.
- [ ] O **Resumo** traz o que a unidade **é**, em texto — nome, sigla, tipo e o **cargo mínimo**
      exigido do titular, com o tipo **sem mínimo** lendo-se "alta administração" —, e, abaixo, a
      **bandeja de indicadores** com quantos servidores são lotados ali (com caminho para a listagem
      já filtrada) e qual é a unidade superior.
- [ ] A **Direção** responde "quem dirige aqui hoje" num **selo de quatro respostas**, que são as
      quatro da SPEC 014: titular, substituto, sem direção, sem titular. Titular e substituto
      aparecem **com foto ou iniciais** e **levam à página de cada um**, e a célula do titular
      ausente **é** a mensagem de erro, não um traço.
- [ ] As duas faltas são **acusadas em vermelho**, **antes** da bandeja de titular e substituto, e o
      texto diz a **causa e a saída**: sem titular, nomear; sem direção, designar substituto na
      página do titular.
- [ ] **Editar é modal**, como os três atos de titularidade: os campos do cadastro (SPEC 012)
      aparecem preenchidos e **lidos**, e cada um só vira campo quando alguém abre o **lápis ao lado
      do valor** — o botão redondo de vidro da listagem, com o glifo gravado por dentro, que se
      entinta enquanto o campo está aberto. O campo aberto é **poço**, que é o que neste design
      system se lê como "escreve-se aqui". O `submit` segue sem destino.
- [ ] O que a **validação pode recusar** naquele campo é dito em **aviso âmbar dentro dele**, e só
      **enquanto ele está aberto**: consequência de ato não se escreve em cinza miúdo, nem fica
      avisando sobre o que ninguém vai mudar.
- [ ] **Definir, trocar e destituir** titular são atos por **modal** na página, com a lista restrita a
      quem pode titularizar aquela unidade (SPEC 014). **Nenhum candidato** tem tela própria: o modal
      diz o que falta, em vez de abrir um campo vazio.
- [ ] Consumado o ato, a página **volta a responder** com a direção já refeita — selo, alarme,
      bandeja e botões —, e o modal está fechado.
- [ ] A rota do ato **recusa** o titular inadequado e a unidade que já tem titular: não é a lista da
      tela que garante a regra.
- [ ] Há **como chegar** à página: a unidade da listagem de servidores (SPEC 013) leva a ela.
- [ ] A **seção de exercício do servidor** (SPEC 015) acusa a **unidade sem direção** quando o
      afastado é o titular e não há substituto em exercício.
- [ ] O design foi aprovado no **mock** antes de qualquer código de aplicação, e as peças novas foram
      **portadas** para `static/src/tema-dimap.dev.css` e renderizadas no styleguide antes de
      qualquer template da aplicação usá-las.

## Contexto e decisões de arquitetura

Iteração de **interface e orquestração**: nenhum model novo, nenhuma migração. O dado, a regra e os
atos de titularidade são da SPEC 014, **pré-requisito desta**; aqui só se lê o que ela decide e se
chamam as funções que ela expõe.

**A página da unidade nasce aqui, e é isso que justifica a SPEC.** A SPEC 012 desenhou o formulário
de **cadastro** e deixou "editar e listar unidades" fora de escopo: existe rota de criar, e o partial
dos campos só tem `placeholder`. A unidade ganha agora a página que a SPEC 013 deu ao servidor —
mesma moldura, mesmo organismo em seções de poço. O partial dos campos passa a aceitar uma
instância: placeholder vira valor e a opção corrente vira `selected`, sem instância ele segue exato
como está, e o modal de nova unidade continua servido por ele.

**A ordem é a da pergunta: Resumo, Direção, editar.** O Resumo é o que a unidade **é** e o quanto ela
tem — quatro respostas de texto numa placa, mais o que se conta ou se navega na bandeja, onde o
número grande e o glifo têm o que fazer. A Direção é o que se veio saber. Editar é o que quase
ninguém veio fazer: sai da página e vira **modal**, atrás de um botão grande e centrado no fim. Com
isso **nada na página é campo** — a Direção grava pelos modais dela, o cadastro pelo modal de edição,
e a página em si só responde. É o que dispensa o botão de salvar solto no rodapé, que numa tela de
leitura nunca se sabe a que se refere.

Consequência aceita: tipo e cargo mínimo aparecem duas vezes — no Resumo como texto, no modal como
campo. É a diferença entre ler e mudar, e poupa quem só lê de abrir o modal para saber o porte da
unidade.

**Dentro do modal, o campo nasce lido e o lápis o abre.** Um formulário inteiro de campos claros não
diz que é editável — foi o que o mock mostrou. Aqui o campo nasce como rótulo gravado e valor em
texto, com o **botão redondo de vidro da listagem** (SPEC 013) ao lado **do valor**, não do rótulo,
porque o que se edita é o valor. Abrir entinta o glifo gravado e rebaixa o valor em **poço**, que é a
gramática de campo do design system. O estado é `checkbox` + `:has()`, como o cabeçalho afundado da
tabela e a paleta da SPEC 005 — nenhum estado de interface em JavaScript. Efeito colateral que se
quer: o que está aberto é o que se pretende mudar, e isso se vê sem ler os valores.

**Consequência de ato é aviso, não dica — e vive dentro do campo.** O que a validação recusa — mudar
o tipo para um que o titular não satisfaça, mudar a unidade superior contra o nível ou as vedas — sai
do `.form-field-hint`, que é cinza miúdo de apoio, e vira a **tarja âmbar** da SPEC 015, com glifo:
no modal, âmbar é a cor da consequência que se precisa saber antes de confirmar, e é o mesmo registro
que o aviso da troca de titular já usa. Cada aviso mora **dentro do campo a que pertence**, e por
isso só aparece quando aquele campo é aberto: fixo no rodapé da seção, ele avisava o tempo todo sobre
o que ninguém ia mudar — e um aviso que está sempre lá deixa de ser lido.

**Dentro da Direção, o alarme vem antes da bandeja.** A notícia precede quem a explica: primeiro
"esta unidade está sem quem responda por ela", depois as células que mostram o titular afastado e o
substituto que não existe. Invertido, a tela pediria que o leitor descobrisse sozinho o que a placa
vermelha ia lhe dizer.

**O estado vem do domínio; o template escolhe a peça.** A view monta o `EstadoDaDirecao` e recebe a
`Direcao` (SPEC 014); o template acende selo e alarme pelo valor do enum. Remontar a causa no
template, com `{% if %}` sobre titular, exercício e substituição, duplicaria em linguagem de
apresentação exatamente a decisão que o domínio existe para concentrar — e as duas cópias divergiriam
na primeira mudança.

**O ato grava e a página renasce (Post/Redirect/Get), em vez de trocar um pedaço por HTMX.** O modal
é `checkbox` nativo (SPEC 012) e não fecha por resposta do servidor sem JavaScript de estado;
redirecionar para a própria página fecha o modal de graça, refaz a leitura da direção **inteira** — o
selo, o alarme, a bandeja e quais botões existem mudam todos juntos — e faz o `F5` não repetir o ato.
Custo aceito: a página recarrega num ato raro, praticado por dezenas de usuários.

**A lista de candidatos é filtro no banco mais o predicado do domínio.** Perfis lotados na unidade com
cargo em comissão saem de uma consulta; quem serve, do `AvaliadorTitularidade` (SPEC 014) — a mesma
regra do `clean()`, sem cópia em `QuerySet`. Lista vazia **não é erro de tela**: é o organograma
dizendo que ninguém ali tem cargo para dirigir a unidade, e o modal diz o que falta e onde se resolve
(o cadastro do servidor), porque um `<select>` vazio não explicaria nada.

**A tela filtra, a rota decide** (§3.5). A lista restrita é UX; a rota revalida a adequação e a
unicidade antes de gravar, e é a validação do model que responde pelo erro — sem `try/except` na view.

**O cargo mínimo aparece em padrão, não em número.** O organograma fala "CDA-IV", não "nível 4": a
orquestração lê no catálogo um cargo de chefia do nível mínimo e mostra o `padrao` dele, em vez de
escrever a sigla da escala no template — que seria copiar dado de seed para dentro da apresentação.
Mínimo nulo lê-se **"Alta administração"**, na mesma célula: é exigência, não ausência, e por isso não
escala para vermelho.

**A vaga é da unidade, e o alarme do afastamento é das duas telas.** A página da unidade acusa as
quatro respostas porque é o único lugar onde elas cabem juntas — na vaga não há servidor a quem
ancorar aviso nenhum. Já o titular afastado sem substituto aparece **também** na página dele, onde
está o caminho da saída: designar quem cubra. Mesma leitura, mesma peça, dois lugares.

**Nada de peça inventada, e duas moléculas novas.** Titular e substituto são a `.linha-pessoa`, o
alarme é a `.tarja-vinculo-critica`, o rosto é o `_imagem_perfil.html`, os modais são o `checkbox` da
SPEC 012, o campo de escolha é o select de vidro da SPEC 011, a gravação e o par repouso/entintado do
lápis são da SPEC 013 e a placa de resumo é a placa de gelo com rótulo e valor. Nascem a **bandeja de
indicadores** (`.stats-onsen`, com a variante `.stat-vaga`), que é o `stats` do daisyUI vestido de
placa fina, e o **campo que se abre para edição** (`.campo-onsen`) — e as duas são patrimônio do design
system antes de serem markup de template.

## Peças de referência a compor
- SPEC 014 (**pré-requisito**): `services/domain/titularidade/` → `Direcao`, `EstadoDaDirecao`,
  `AvaliadorDirecao` e `AvaliadorTitularidade`; e as funções de ato `definir_titular` /
  `destituir_titular`, que gravam em transação. Esta SPEC não reimplementa nenhuma delas.
- SPEC 015 (**pré-requisito**): `Perfil.em_exercicio` e a `Substituicao` vigente — as duas marcas de
  que a leitura da direção é feita —, mais a seção de exercício da página do servidor, que ganha o
  alarme.
- `@templates/user_admin/unidade_form.html` e `@templates/user_admin/partials/_campos_unidade.html`:
  as três seções de campos já existem e são partial próprio; o que falta é renderizá-las com
  instância.
- `@templates/user_admin/partials/_identidade_perfil.html`: o cabeçalho de identidade do servidor —
  o da unidade é o irmão dele, não uma invenção.
- `@templates/user_admin/partials/_imagem_perfil.html`: foto ou iniciais já resolvidas (SPECs 004 e
  006).
- `@templates/user_admin/partials/_modal_nova_unidade.html`: modal por checkbox nativo, irmão do
  formulário e nunca dentro dele (SPEC 012) — o padrão que os três modais repetem.
- `.etched` e `.etched-rotulo` (SPEC 013): a gravação e o par repouso/entintado que o lápis repete —
  e os filtros SVG de que ela depende, já no `base.html`.
- `.linha-pessoa` e `.tarja-vinculo` / `.tarja-vinculo-critica` (SPEC 015); `.card-well`,
  `.glass-panel-thick`, `.avatar-glass`, `.dot-unidade`, `.btn-onsen` / `.btn-glass`,
  `.select-glass` + `data-select-onsen` (SPEC 011) e `.text-overline`.
- `@apps/user_admin/views.py` + `@apps/user_admin/context.py` + `@apps/user_admin/schemas.py`: view
  fina, função de contexto e DTO construído na view, com o `PydanticValidationMiddleware`
  respondendo pelo erro.
- `@apps/user_admin/paleta.py` → `hex_da_cor`: o slug da cor da unidade vira hex na borda do app.
- `@templates/user_admin/partials/_corpo_servidores.html` e a query string da listagem (SPEC 013): a
  coluna de unidade vira o caminho de ida, e "ver na listagem" é o caminho de volta, com o filtro já
  aplicado.
- `@apps/user_admin/ficticios.py` (SPEC 014): os titulares marcados e a unidade deixada vaga são o
  que torna esta página exercitável nos quatro estados.
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
variante `.stat-vaga` é a célula do titular quando não há titular: em vez de campo vazio — que se lê como "ainda não carregou" — a célula **é** a
mensagem de erro.

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
015 (o raio da placa, a linha de pessoa, a tarja) **não** se porta daqui: é porte daquela SPEC, que
vem antes.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md

# apps/user_admin/context.py
def contexto_unidade(unidade: Unidade) -> dict[str, Any]:
    titular = unidade.titular
    substituto = _substituto_vigente(titular)
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
# apps/user_admin/context.py
def candidatos_a_titular(unidade: Unidade) -> list[Perfil]:
    """Quem a unidade pode titularizar: o filtro estreita, o domínio decide."""
    lotados = Perfil.objects.filter(
        unidade=unidade,
        cargo_comissao__isnull=False,
    ).select_related("cargo_comissao")
    return [perfil for perfil in lotados if _pode_titularizar(perfil, unidade.tipo)]
```

```python
# apps/user_admin/schemas.py
class EscolhaDeTitular(BaseModel):
    titular: int


# apps/user_admin/views.py
def definir_titular_da_unidade(request: HttpRequest, pk: int) -> HttpResponse:
    unidade = get_object_or_404(Unidade, pk=pk)
    escolha = EscolhaDeTitular.model_validate(request.POST.dict())
    perfil = get_object_or_404(Perfil, pk=escolha.titular, unidade=unidade)
    # A lista da tela é UX; a regra é revalidada aqui, antes de gravar (§3.5).
    definir_titular(perfil)
    # PRG: o modal fecha porque a página renasce, e o F5 não repete o ato.
    return redirect("user_admin:ver_unidade", pk=unidade.pk)
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
- **Gravar os demais campos da unidade** pela página: o formulário da SPEC 012 segue sem destino — o
  que grava aqui são os três modais de titularidade.
- A **regra e o dado** da titularidade: models, índice, adequação, leitura da direção e as funções de
  ato são da SPEC 014, **pré-requisito desta**.
- **Listagem de unidades**, criar unidade por esta página e criar **tipo** de unidade: a ida para cá
  é pela listagem de servidores, e cadastrar unidade continua sendo a tela da SPEC 012.
- **Desde quando** a unidade está vaga, e histórico de quem já dirigiu: exigiria guardar a data da
  destituição (fora de escopo na SPEC 014) — a tela diz que falta, não desde quando.
- Escolher **quem responde** pela unidade vaga: a tela diz que o superior responde, mas nomeá-lo é
  regra do épico `autorizacao`.
- **Fechar o modal por resposta do servidor** e trocar só um pedaço da página: resolvido pelo
  redirect (ver Contexto).
- **Gravar campo a campo** pelo lápis: abrir um campo é gesto de tela, não requisição — o que grava é
  o modal inteiro, e o do cadastro segue sem destino.
- Editar, encerrar ou excluir impedimento e substituição pela página da unidade — são atos da SPEC
  015, na página do servidor.
- Autenticação, autorização por perfil e **registro** da execução do ato — épico `autorizacao`, nos
  mesmos termos da exceção declarada na SPEC 015.

## Testes (TDD)
Todos fixam contrato HTTP/partial e tocam o banco: carregam o marker `banco`, declarado em
`markers_obrigatorios`. O domínio da direção e da adequação já é testado sem banco na SPEC 014 e não
se repete aqui.

- `test_pagina_da_unidade_traz_o_resumo_e_quem_dirige` — GET devolve 200 com nome, sigla, tipo e
  cargo mínimo no resumo, a unidade superior na bandeja, o titular em exercício no selo, e os campos
  do cadastro preenchidos no modal de edição.
  *(marker `banco`)*
- `test_pagina_distingue_as_duas_faltas` — unidade vaga acusa "sem titular"; titular afastado sem
  substituto acusa "sem direção"; com substituto em exercício, nenhuma das duas é acusada.
  *(marker `banco`)*
- `test_modal_lista_so_quem_pode_titularizar` — a lista traz a chefia que satisfaz o mínimo do tipo e
  não traz o assessor de nível alto, o servidor sem cargo em comissão nem quem é de outra unidade;
  sem nenhum candidato, a página traz o aviso em vez do campo. *(marker `banco`)*
- `test_definir_e_trocar_titular_gravam_e_redirecionam` — o POST marca o novo titular, destitui o
  anterior e responde 302 para a página da unidade. *(marker `banco`)*
- `test_rota_recusa_titular_inadequado` — POST com perfil que não satisfaz o mínimo do tipo não grava,
  ainda que a lista da tela nunca o oferecesse. *(marker `banco`)*
- `test_secao_do_servidor_acusa_unidade_sem_direcao` — a página do titular afastado sem substituto
  acusa a unidade sem direção, e para de acusar quando há substituto em exercício. *(marker `banco`)*

## Patches

_Nenhum patch registrado até o momento._
