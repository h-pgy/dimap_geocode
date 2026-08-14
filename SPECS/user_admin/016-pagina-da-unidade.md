---
spec: user_admin/016
versao: v4
atualizado_em: 2026-08-14
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: a montagem do `EstadoDaDirecao` passa a ser desta SPEC, e o substituto vem da
        `substituicao_vigente` da SPEC 015
  - v3: os três atos de titularidade deixam de ganhar rota — os modais renderizam com o submit sem
        destino —, e o cargo mínimo passa a ler `exige_alta_administracao` do tipo
  - v4: sem mudança de escopo — a SPEC foi reescrita no formato de seções numeradas da skill
        `specs`, com a justificativa toda concentrada em Caveats
---

# SPEC user_admin/016 — A página da unidade: quem dirige aqui hoje, e os atos de titularidade

## 1 · User story
O responsável pela DIMAP nomeia, troca ou destitui o titular de uma unidade na página dela, onde
antes de qualquer outra coisa vê quem responde pela unidade hoje, para que a vaga e o afastamento sem
cobertura sejam cobrados pela tela em vez de descobertos quando falta uma assinatura.

## 2 · Condições de pronto
- [ ] A unidade tem **página própria**, em rota **aberta** de leitura, alcançável pela unidade na
      listagem de servidores, com **cabeçalho de identidade** — sigla, nome, tipo, nível, quantos
      servidores são lotados ali e o ponto na cor da unidade —, duas seções **nesta ordem** (Resumo,
      Direção) e, ao fim, um botão que abre a edição.
- [ ] O **Resumo** traz nome, sigla, tipo e o **cargo mínimo** exigido do titular em **padrão de
      cargo** (`CDA-IV`), com o tipo que exige alta administração lendo-se "Alta administração"; e,
      abaixo, a bandeja de indicadores com quantos servidores são lotados ali — com caminho para a
      listagem já filtrada — e qual é a unidade superior.
- [ ] A **Direção** responde "quem dirige aqui hoje" em **uma de quatro** respostas — titular,
      substituto, sem direção, sem titular —, com titular e substituto aparecendo **com foto ou
      iniciais** e levando à página de cada um.
- [ ] As duas faltas são acusadas **antes** da bandeja de titular e substituto, e o texto diz **causa
      e saída**: sem titular, nomear; sem direção, designar substituto na página do titular.
- [ ] **Editar é modal**: os campos do cadastro (SPEC 012) aparecem preenchidos e **lidos**, e cada um
      só vira campo quando alguém abre o **lápis ao lado do valor**.
- [ ] O que a validação pode recusar naquele campo é dito **dentro dele**, e só **enquanto ele está
      aberto**.
- [ ] **Definir, trocar e destituir** titular são três modais, com a lista restrita a quem pode
      titularizar aquela unidade; **sem nenhum candidato**, o modal diz o que falta em vez de abrir um
      campo vazio.
- [ ] **Nenhuma rota de escrita nasce aqui**: os quatro modais renderizam com o **submit sem
      destino**, e os atos seguem sendo as funções da SPEC 014.
- [ ] A **seção de exercício do servidor** (SPEC 015) acusa a unidade **sem direção** quando o
      afastado é o titular e não há substituto em exercício.
- [ ] O design foi aprovado no **mock**, e `.stats-onsen` (com `.stat-vaga`) e `.campo-onsen` foram
      portadas para `static/src/tema-dimap.dev.css` e renderizadas no styleguide antes de qualquer
      template da aplicação usá-las.

## 3 · Domínio
Iteração de **interface e orquestração**: nenhum model novo, nenhuma migração, nenhum DTO de entrada
— a rota recebe só a chave da unidade na URL. O domínio consumido, e a pergunta que esta SPEC faz a
cada peça:

- [`EstadoDaDirecao` → `Direcao`, via `avaliar_direcao`](014-titular-da-unidade.md) — "quem dirige
  esta unidade hoje, e, se ninguém dirige, qual das duas faltas é?"; esta SPEC **monta** o estado
  sobre o titular e o substituto que a tela já carregou.
- [`cargo_titulariza`](014-titular-da-unidade.md) — "este perfil pode titularizar esta unidade?", a
  mesma adequação que os `clean()` usam, aplicada à lista de candidatos.
- [`substituicao_vigente` e `Perfil.em_exercicio`](015-exercicio-e-substituicao.md) — "quem cobre o
  titular hoje?" e "titular e substituto estão na cadeira?".
- [`Unidade` e `TipoUnidade`](001-models-perfil-cargos-unidade.md) — nome, sigla, tipo, unidade
  superior, cor, e o par `exige_alta_administracao` × `nivel_minimo_titular` que decide o cargo
  mínimo.

**Mock:** [016-mock-pagina-da-unidade.html](016-mock-pagina-da-unidade.html) — leia a skill `mock`.

## 4 · Fora de escopo
- **As rotas de escrita** dos três atos de titularidade e da edição da unidade — épico de ações.
- Autenticação, autorização por perfil e **registro** da execução do ato — épico `autorizacao`.
- Escolher **quem responde** pela unidade vaga — épico `autorizacao`.
- **Desde quando** a unidade está vaga e histórico de quem já dirigiu — sem dono ainda; exigiria a
  data da destituição, que a SPEC 014 não guarda.
- Editar, encerrar ou excluir impedimento e substituição por esta página — SPEC 015, na página do
  servidor.
- **Listagem de unidades** e criar unidade ou tipo de unidade por esta página — cadastrar unidade
  segue na SPEC 012; listar unidades, sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/titularidade/` → `avaliar_direcao`, `Direcao`, `EstadoDaDirecao`: quem dirige a
  unidade hoje, a partir do estado.
- `@apps/user_admin/titularidade.py` → `definir_titular` / `destituir_titular`: os atos em transação.
- `@apps/user_admin/models/titularidade.py` → `cargo_titulariza`: a adequação do cargo ao tipo.
- `@apps/user_admin/exercicio.py` → `substituicao_vigente`; e `Perfil.em_exercicio`: quem cobre e quem
  está na cadeira.
- `@templates/user_admin/partials/_campos_unidade.html`: as três seções de campos do cadastro.
- `@templates/user_admin/partials/_identidade_perfil.html` e `_imagem_perfil.html`: o cabeçalho de
  identidade e o rosto já resolvido em foto ou iniciais.
- `@templates/user_admin/partials/_modal_nova_unidade.html`: modal por checkbox nativo, irmão do
  formulário e nunca dentro dele.
- `@static/src/tema-dimap.dev.css` → `.linha-pessoa`, `.tarja-vinculo-critica`, `.etched`,
  `.card-well`, `.glass-panel`, `.select-glass`, `.dot-unidade`, `.btn-onsen` / `.btn-glass`.
- `@apps/user_admin/ficticios.py`: os titulares marcados, a unidade vaga e o titular afastado com e
  sem substituto — os quatro estados da direção já semeados.
- Skills: `componentes-frontend`, `daisyui`, `mock`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

**`apps/user_admin/views.py`**
```python
def pagina_unidade(request: HttpRequest, pk: int) -> HttpResponse:
    unidade = get_object_or_404(Unidade.objects.select_related("tipo", "pai"), pk=pk)
    return render(request, "user_admin/unidade.html", contexto_unidade(unidade))
```

**`apps/user_admin/context.py`**
```python
def contexto_unidade(unidade: Unidade) -> dict[str, Any]:
    """Uma passagem só: quem a tela carrega para desenhar é quem ela usa para decidir."""
    titular = unidade.titular
    # A vigente vem da SPEC 015: o predicado de data não se copia por tela.
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

**`apps/user_admin/context.py`** — a montagem que o avaliador da SPEC 014 lê, sobre o titular e o
substituto que a tela já tem em mãos.
```python
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

**`apps/user_admin/context.py`**
```python
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

**`apps/user_admin/context.py`**
```python
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

**`templates/user_admin/partials/_secao_direcao.html`**
```html
<!-- O template escolhe a peça pelo enum; não remonta a causa com {% if %} sobre exercício. -->
{% if direcao == "sem_titular" %}
  {% include "user_admin/partials/_alarme_direcao.html" with titulo=alarme_sem_titular %}
{% elif direcao == "sem_direcao" %}
  {% include "user_admin/partials/_alarme_direcao.html" with titulo=alarme_sem_direcao %}
{% endif %}
```

## 7 · Caveats
A rota de leitura da unidade **nasce aberta**, pela exceção ao §3.5 declarada na SPEC 013. Enquanto
não há autenticação, exigir login numa tela de leitura tornaria a página inexercitável, e nada aqui é
ato administrativo. Custo: quando o épico `autorizacao` chegar, esta rota precisa ser revisitada junto
com as demais da área administrativa.

**Nenhuma rota de escrita nasce nesta SPEC**, e os quatro modais renderizam com o submit sem destino.
Ligar os atos da SPEC 014 a uma rota é o que exige autenticação, autorização por perfil e registro da
execução, que ainda não existem — e abrir exceção de rota aberta para **escrita** custaria refazê-la
protegida depois. Custo aceito: dá para ver e testar a página nos quatro estados da direção, e não dá
para mudar nada por ela; quem produz os estados é o andaime, chamando os atos pela mesma porta que a
rota vai chamar.

**Tipo e cargo mínimo aparecem duas vezes na tela** — no Resumo como texto, no modal como campo. Quem
só quer saber o porte da unidade não deveria precisar abrir o modal de edição. Custo: dois lugares
renderizando o mesmo dado, que divergem se um deles mudar de fonte.

**A lista de candidatos filtra no banco e decide em Python**, chamando `cargo_titulariza` perfil a
perfil. Copiar o predicado para `QuerySet` duplicaria em SQL a regra que os `clean()` já aplicam, e a
divergência entre as duas cópias só apareceria em produção. Custo: O(n) sobre os lotados da unidade —
dezenas de pessoas, com o cargo já resolvido por `select_related`.

**A montagem do `EstadoDaDirecao` vive na orquestração**, não no domínio: a tela já carregou titular e
substituto para desenhá-los, e uma função que recebesse a unidade refaria as duas consultas. Custo: a
composição do estado é responsabilidade do `context.py`, e outra tela que precise da mesma leitura
tem de chamar esta peça em vez de reescrevê-la.

**O rótulo do cargo mínimo é lido no catálogo de cargos**, procurando um cargo de chefia do nível
mínimo do tipo. Escrever a sigla da escala no template seria copiar dado de seed para dentro da
apresentação. Custo: uma consulta por página, e rótulo vazio se nenhum cargo de chefia tiver aquele
nível — estado que o seed da SPEC 009 não produz, mas que o código não pode supor impossível.

## 8 · Testes (TDD)
Todos fixam contrato HTTP/partial e tocam o banco: carregam o marker `banco`. O domínio da direção e
da adequação já é testado sem banco na SPEC 014 e não se repete aqui.

- `test_pagina_da_unidade_traz_o_resumo_e_quem_dirige` — GET devolve 200 com nome, sigla, tipo e cargo
  mínimo em padrão de cargo no resumo, a unidade superior e o total de lotados na bandeja, e o titular
  em exercício na direção. *(marker `banco`)*
- `test_pagina_distingue_as_duas_faltas` — unidade vaga acusa "sem titular"; titular afastado sem
  substituto acusa "sem direção"; com substituto em exercício, nenhuma das duas é acusada.
  *(marker `banco`)*
- `test_modal_de_edicao_vem_preenchido_e_sem_destino` — os campos do cadastro trazem os valores da
  unidade e a opção corrente selecionada, e o formulário do modal não declara destino de submit.
  *(marker `banco`)*
- `test_modal_lista_so_quem_pode_titularizar` — a lista traz a chefia que satisfaz o mínimo do tipo e
  não traz o assessor de nível alto, o servidor sem cargo em comissão nem quem é de outra unidade;
  sem nenhum candidato, a página traz o aviso em vez do campo. *(marker `banco`)*
- `test_secao_do_servidor_acusa_unidade_sem_direcao` — a página do titular afastado sem substituto
  acusa a unidade sem direção, e para de acusar quando há substituto em exercício. *(marker `banco`)*
