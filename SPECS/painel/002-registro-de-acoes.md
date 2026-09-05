---
spec: painel/002
versao: v10
atualizado_em: 2026-09-05
testes_tdd: true
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: a leitura do registro ganha alcance próprio — a própria unidade para quem não dirige, a
    subárvore dirigida para quem dirige —, e o critério de unidade só existe no card de quem dirige
  - v3: o critério de unidade é reconhecido como alvo nomeado, conferido pelo próprio recorte da
    consulta, e o administrador do sistema lê o registro inteiro
  - v4: a unidade deixa de ser critério opcional e passa a ser o ponto de partida da leitura — nasce
    na do leitor, abrange o que ele dirige abaixo dela, e escolher outra estreita para aquele sub-ramo
  - v5: a busca para nas 500 mais recentes e a tabela passa a exibir 50 por vez, com paginação; a
    tabela larga ganha rolagem horizontal com barra gravada própria
  - v6: o corte do teto deixa de ter aviso próprio e passa a ser o `+` na contagem da paginação
  - v7: o teto de 500 sai — a paginação percorre o resultado inteiro do período, e o número de
    páginas segue a contagem real
  - v8: a rota e o item do painel passam a se chamar pelo que fazem — listar o registro, não
    registrar a ação
  - v9: implementado — os 10 testes da SPEC passam (3 de domínio, 7 de banco); o parâmetro de
    unidade do card nasce como `unidade_partida`, e não `unidade`, para não colidir com a coluna
    homônima que o cabeçalho filtra na mesma query string
  - v10: todo caractere da paginação vira gravação que conta — cava escura própria, na medida do
    glifo
---

# SPEC painel/002 — Registro de Ações

## 1 · User story
O servidor da DIMAP consulta o registro de atos praticados no alcance que lhe cabe, buscando por
autor, unidade, cargo base, cargo em comissão e período, para saber quem praticou qual ato, sobre o
quê, e se podia.

## 2 · Condições de pronto
- [ ] A rota `/competencias/registro-acoes/` (`listar_registro_acoes`) manda o anônimo ao login e **não recusa servidor
      autenticado algum**: o que muda entre eles é **o que cada um vê**.
- [ ] A tela nasce na **própria unidade** do leitor e mostra as execuções dela e das unidades que ele
      **dirige abaixo** dela; quem não dirige nada vê só a sua, o administrador do sistema alcança o
      organograma inteiro, e o alcance vale **inclusive sobre unidade extinta**.
- [ ] O controle de **unidade** existe **só para quem dirige** alguma unidade: nasce com a própria
      selecionada, oferece as unidades do alcance, e escolher uma delas **estreita** a leitura para
      aquele sub-ramo. Para os demais o campo **não é renderizado**, e unidade **forjada fora do
      alcance** na query string devolve tabela **vazia**.
- [ ] A busca recorta **no banco** por autor, cargo base, cargo em comissão e período, combinados
      cumulativamente; critério em branco não recorta, e o período nasce nos **últimos 30 dias**.
- [ ] A tabela exibe **50 linhas por vez** e a paginação percorre o **resultado inteiro**: 600
      execuções são 12 páginas, e a última traz o resto.
- [ ] O cabeçalho da tabela filtra e ordena **sobre tudo que a busca devolveu** — não sobre a página
      exibida, e o número de páginas acompanha o que sobra do filtro —, e mudar um critério do card
      **preserva** os filtros do cabeçalho, e vice-versa.
- [ ] A tabela **rola na horizontal** dentro do próprio poço, com barra gravada própria; a página nunca
      rola na horizontal.
- [ ] Cada linha diz **momento, autor, unidade, cargo base, cargo em comissão, ação, operação, alvo
      e autorização** — a tentativa **negada** entre elas —, na ordem mais recente primeiro; ato praticado
      em substituição diz **por quem o autor respondia**.
- [ ] "Registro de Ações" aparece na aba **Administração do Sistema**, em grupo próprio no topo, para
      todo servidor autenticado.
- [ ] O design foi aprovado no mock e as peças novas foram portadas para o tema e o styleguide antes
      de qualquer template da aplicação usá-las.

## 3 · Domínio

Duas perguntas distintas estruturam a tela: **o que vem do banco** (o card) e **o que sobra do que
veio** (o cabeçalho). A primeira é recorte novo; a segunda já existe e é a `ConsultaListagem`
genérica, parametrizada por mais um enum de colunas. Sobre as duas incide uma terceira, que não é
critério de ninguém: o **alcance de leitura** do próprio leitor.

**`services/domain/listagem_gestao/models/execucoes.py`**
```python
JANELA_PADRAO_DIAS = 30
# O que chega à tela de uma vez. Não há teto sobre o que a busca devolve: quem contém o volume é o
# período (§7).
TAMANHO_PAGINA = 50

SEM_CARGO_COMISSAO = "—"
SEM_AUTOR = "—"


class ColunaExecucao(StrEnum):
    """As colunas que o cabeçalho filtra e ordena. `momento` e a autorização ficam de fora: um é
    recortado pelo período do card, o outro é badge e não tem termo a digitar (§7). O valor de cada
    membro é o NOME do campo em `LinhaExecucao` — é por ele que o motor genérico lê a célula."""

    SERVIDOR = "servidor"
    UNIDADE = "unidade"
    CARGO = "cargo"
    COMISSAO = "comissao"
    ACAO = "acao"
    OPERACAO = "operacao"
    ALVO = "alvo"


class LinhaExecucao(BaseModel):
    """Uma linha já materializada da tabela do registro. Guarda o que a `ExecucaoAcao` gravou NO
    DIA do ato, não o que o cadastro do autor diz hoje."""

    pk: int
    # Formatado na materialização: a coluna só é lida, nunca filtrada nem ordenada pelo cabeçalho.
    momento: str
    servidor: str
    # Nulo quando o perfil do autor foi apagado — a FK é SET_NULL (SPEC autorizacao/004).
    servidor_pk: int | None = None
    unidade: str
    unidade_pk: int
    cor_unidade: str
    cargo: str
    comissao: str = SEM_CARGO_COMISSAO
    acao: str
    operacao: str = ""
    # "tipo: identificador", achatado num campo só — o alvo é texto livre e o par vira uma coisa
    # que se lê e se filtra de uma vez.
    alvo: str = ""
    autorizado: bool
    # Vazio quando o ato foi praticado por competência própria.
    substituindo: str = ""


ConsultaExecucoes = ConsultaListagem[ColunaExecucao]


class BuscaExecucoes(BaseModel):
    """O recorte que vai ao banco. Distinto de `ConsultaExecucoes`, que filtra em memória o que este
    recorte trouxe: aqui se decide QUAIS execuções existem para a tela; lá, quais delas sobram."""

    model_config = ConfigDict(frozen=True)

    # Primeiro campo e SEM default: as unidades que esta busca lê não são critério, são a condição
    # de existir busca. Já vêm resolvidas — o alcance do leitor cruzado com a unidade de onde ele
    # partiu (§6). Sem default, esquecê-las é erro de tipo, nunca registro inteiro vazando.
    unidades_lidas: frozenset[int]
    perfil_id: int | None = None
    cargo_base_id: int | None = None
    cargo_comissao_id: int | None = None
    # Sem default de campo: "hoje" é da orquestração, como o CRS — o domínio não lê relógio.
    inicio: date
    fim: date
```

A página é genérica como a consulta, e mora ao lado dela: quem pagina não sabe o que é uma
execução.

**`services/domain/listagem_gestao/models/consulta.py`**
```python
class Pagina(BaseModel, Generic[LinhaT]):
    """Uma fatia de linhas e o que a navegação precisa saber sobre ela. `numero` e `total_paginas`
    são 1-based porque é o que a tela mostra — converter na borda seria converter duas vezes."""

    model_config = ConfigDict(frozen=True)

    linhas: tuple[LinhaT, ...]
    numero: int
    total_paginas: int
    total_linhas: int
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`ExecucaoAcao`](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md) — "quais atos foram
  praticados, por quem, com qual lotação e sobre o quê?"; é a única fonte da tela.
- [`alcance_do_perfil` e `unidades_dirigidas`](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md)
  — "que ramos este perfil dirige?"; é sobre esta resposta que o alcance de leitura se apoia, é a
  ausência dela que caracteriza quem não dirige nada, e é ela que já entrega o organograma inteiro
  ao superusuário.
- [`posicao_de`](../user_admin/018-arvore-hierarquica.md) — "o que pende da unidade de onde se
  parte?"; é a subárvore que o alcance recorta.
- [`ConsultaListagem` e `ListadorTabela`](../user_admin/021-lista-de-unidades.md) — "o que sobra
  destas linhas depois dos filtros do cabeçalho?", já respondida pelo motor genérico.
- [`ItemLivre` e `Grupo`](001-painel-de-acoes-por-abas.md) — "onde esta tela aparece no painel, e para
  quem?"; a resposta é: em grupo próprio da aba Administração do Sistema, para todo autenticado.

**Mock:** [002-mock-registro-de-acoes.html](002-mock-registro-de-acoes.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Buscar por **ação**, **operação** ou **autorização** no card: os três já filtram pelo cabeçalho,
  dentro do que a busca devolveu. Sem dono ainda.
- Alcance de leitura que **não seja por unidade** — acompanhar um servidor específico onde quer que
  ele passe a ser lotado. Sem dono ainda.
- **Exportação** do registro (CSV, PDF) — sem dono ainda.
- **Retenção e expurgo** das execuções — SPEC `autorizacao/004`, §4, sem dono ainda.
- Página do ato individual, com o detalhe completo de uma execução — sem dono ainda.
- Gravar a **unidade em que o ato produziu efeito** quando ela não é a de lotação do autor — SPEC
  `autorizacao/004`, §4, sem dono ainda; é sobre a lotação gravada que o alcance recorta (§7).

## 5 · Peças de referência a compor
- `@apps/competencias/consulta.py` → `alcance_do_perfil`: a subárvore de cada unidade dirigida,
  reduzida a ids, com a opção de incluir as extintas e o superusuário já tratado na origem.
- `@apps/unidades/consulta.py` → `posicao_de`: a subárvore da unidade de onde a leitura parte.
- `@apps/core/tabela` → `consulta_da_listagem`, `colunas_da_tabela` e `marca_descendente`: o cabeçalho
  filtrável que esta tabela divide com as de servidores, unidades e cargos.
- `@services/domain/listagem_gestao` → `ListadorTabela`: o filtro e a ordenação em memória, com a
  normalização canônica.
- `@apps/competencias/models` → `ExecucaoAcao`: a fonte das linhas.
- `@apps/unidades/paleta` → `hex_da_cor`: o hex do ponto da unidade na linha.
- `@templates/cargos/partials/_tabela_cargos.html` → a composição da tabela-onsen: poço rebaixado,
  bandeja de cabeçalho, barra de rolagem gravada.
- `@static/src/js/ui/tabela_onsen.js` e `@static/src/js/ui/scroll_etched.js` → ordenação, limpeza de
  filtros e a barra gravada.
- `@static/src/js/ui/select_onsen.js` → `.select-onsen`: os selects do card, com filtro por texto a
  partir de seis opções.
- Skills: `painel`, `componentes-frontend`, `mock`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

**`apps/competencias/consulta.py`** — os dois passos do alcance novo, ao lado do que já resolve o
alcance de ação: até onde o perfil PODE ler, e o que ele está lendo agora.
```python
def alcance_de_leitura(perfil: Perfil) -> frozenset[int]:
    """Até onde este perfil PODE ler o registro: a própria unidade sempre, mais a subárvore de cada
    unidade que dirige.

    Sem `if` para nenhum dos dois papéis, e é isso que a expressão mostra. Quem não dirige nada cai
    no caso base — `alcance_do_perfil` devolve conjunto vazio e sobra a lotação. O superusuário
    recebe o organograma inteiro pelo mesmo caminho: `ramos_do_alcance` já o trata na origem, para
    não espalhar `is_superuser` por quem a consulta.

    `com_extintas=True` porque o registro é histórico: unidade extinta ontem praticou atos que
    continuam sendo dela, e sumir com eles do alcance de quem a dirigia apagaria justamente o
    período que se quer auditar.
    """
    return frozenset({perfil.unidade_id}) | alcance_do_perfil(perfil, com_extintas=True)


def unidades_lidas(perfil: Perfil, unidade_escolhida: int | None) -> frozenset[int]:
    """O que a tela lê AGORA: a subárvore da unidade de onde se parte, contida no alcance.

    A unidade nunca é ausência — quem não escolhe parte da própria, e é essa escolha implícita que
    faz a página nascer no ramo do leitor em vez de no registro inteiro.

    A interseção é a regra toda, e ela resolve os dois papéis de uma vez: para quem não dirige, o
    alcance é uma unidade só e a subárvore da própria lotação encolhe para ela; para quem dirige,
    a subárvore é o ramo e o alcance a deixa passar inteira. Fora do alcance nem se pergunta à
    árvore — é vazio, e não 403, porque aqui o alcance recorta o resultado, não barra a entrada.
    """
    alcance = alcance_de_leitura(perfil)
    partida = unidade_escolhida or perfil.unidade_id
    if partida not in alcance:
        return frozenset()
    return frozenset(posicao_de(partida, com_extintas=True).ego.ids) & alcance
```

**`services/domain/listagem_gestao/models/execucoes.py`** — a tradução da query string no recorte. O
alcance entra por parâmetro, não pela query string: ele é o que o leitor **é**, não o que ele pediu.
```python
@classmethod
def de_parametros(
    cls,
    parametros: Mapping[str, str],
    hoje: date,
    unidades_lidas: frozenset[int],
) -> Self:
    """`hoje` e as unidades lidas entram por parâmetro porque nenhum dos dois vem do cliente — a
    unidade que o usuário escolhe já foi cruzada com o alcance dele antes de chegar aqui (CLAUDE.md
    §3.3: autorização é orquestração)."""
    return cls.model_validate(
        {
            "unidades_lidas": unidades_lidas,
            # Select sem escolha manda o campo com valor vazio. Sem esta limpeza, "" chegaria ao
            # `int | None` do Pydantic e viraria ValidationError num formulário que o usuário
            # apenas deixou em branco.
            "perfil_id": parametros.get("perfil") or None,
            "cargo_base_id": parametros.get("cargo_base") or None,
            "cargo_comissao_id": parametros.get("cargo_comissao") or None,
            # Página carregada sem período: os últimos 30 dias. É o que impede a tela de abrir
            # arrastando o registro inteiro (§7).
            "inicio": parametros.get("inicio") or hoje - timedelta(days=JANELA_PADRAO_DIAS),
            "fim": parametros.get("fim") or hoje,
        }
    )
```

**`apps/competencias/historico.py`** — o recorte no banco e a materialização da linha. Módulo novo, ao
lado de `registro_execucao.py`: um grava o ato, o outro o lê.
```python
def linhas_de_execucoes(busca: BuscaExecucoes) -> list[LinhaExecucao]:
    return [_linha(execucao) for execucao in _recortadas(busca)]


def _recortadas(busca: BuscaExecucoes) -> Sequence[ExecucaoAcao]:
    """As unidades lidas PRIMEIRO e incondicionalmente; os critérios do usuário depois, cada um só
    se veio.

    Esta ordem é a regra: o conjunto de unidades não é um filtro entre outros que o usuário poderia
    relaxar — ele delimita o universo, e é por isso que `unidade` forjada fora do alcance devolve
    vazio em vez de linha alheia. Critério em branco não estreita nada; a ordem é sempre a
    cronológica reversa, que é a que o registro tem sentido de ser lido.
    """
    consulta = (
        ExecucaoAcao.objects.select_related(
            "acao",
            "perfil",
            "unidade",
            "cargo_base",
            "cargo_comissao",
            "substituindo",
        )
        .filter(unidade_id__in=busca.unidades_lidas)
        .filter(momento__date__gte=busca.inicio, momento__date__lte=busca.fim)
    )
    if busca.perfil_id is not None:
        consulta = consulta.filter(perfil_id=busca.perfil_id)
    if busca.cargo_base_id is not None:
        consulta = consulta.filter(cargo_base_id=busca.cargo_base_id)
    if busca.cargo_comissao_id is not None:
        consulta = consulta.filter(cargo_comissao_id=busca.cargo_comissao_id)
    # Sem fatia aqui: quem fatia é a paginação, depois do filtro do cabeçalho. Cortar no banco faria
    # o número de páginas mentir sobre quantos atos existem no período.
    return consulta.order_by("-momento")


def _linha(execucao: ExecucaoAcao) -> LinhaExecucao:
    # Nada aqui vem do cadastro de hoje: unidade e cargos saem das colunas que a SPEC
    # autorizacao/004 copiou para a linha no dia do ato.
    autor = execucao.perfil
    coberto = execucao.substituindo
    return LinhaExecucao(
        pk=execucao.pk,
        momento=localtime(execucao.momento).strftime(FORMATO_MOMENTO),
        servidor=f"{autor.nome} {autor.sobrenome}" if autor else SEM_AUTOR,
        servidor_pk=execucao.perfil_id,
        unidade=execucao.unidade.sigla,
        unidade_pk=execucao.unidade_id,
        cor_unidade=hex_da_cor(execucao.unidade.cor),
        cargo=execucao.cargo_base.nome,
        comissao=execucao.cargo_comissao.nome if execucao.cargo_comissao else SEM_CARGO_COMISSAO,
        acao=execucao.acao.nome,
        operacao=execucao.operacao,
        # O par vira um campo só: é assim que a coluna se lê e é assim que o cabeçalho a filtra.
        alvo=f"{execucao.alvo_tipo}: {execucao.alvo_identificador}" if execucao.alvo_tipo else "",
        autorizado=execucao.autorizado,
        substituindo=f"{coberto.nome} {coberto.sobrenome}" if coberto else "",
    )
```

**`services/domain/listagem_gestao/paginacao.py`** — a fatia, e a única regra dela: número forjado
não estoura, encosta.
```python
def paginar(linhas: Sequence[LinhaT], numero: int, tamanho: int) -> Pagina[LinhaT]:
    """Pagina DEPOIS do filtro do cabeçalho, nunca antes: paginar o conjunto cru faria a página 2 de
    um resultado filtrado mostrar linhas que o filtro já tinha descartado.

    O número é preso entre 1 e a última página em vez de recusado — `?pagina=999` é dedo torto ou
    link velho, não tentativa de nada, e devolver erro para isso troca uma tela por uma falha.
    Lista vazia tem UMA página, não zero: "página 1 de 0" não é frase que se escreva na tela.
    """
    total_paginas = max(1, ceil(len(linhas) / tamanho))
    atual = min(max(numero, 1), total_paginas)
    inicio = (atual - 1) * tamanho
    return Pagina(
        linhas=tuple(linhas[inicio : inicio + tamanho]),
        numero=atual,
        total_paginas=total_paginas,
        total_linhas=len(linhas),
    )
```

**`apps/competencias/context.py`** — a ordem das quatro camadas, que é a regra desta tela; e o que o
card mostra, que é consequência da primeira delas.
```python
def contexto_corpo_execucoes(perfil: Perfil, parametros: Mapping[str, str]) -> dict[str, Any]:
    # Unidades lidas → banco → memória → página, nesta ordem e sem atalho. O cabeçalho nunca vê
    # linha que a busca não trouxe, a busca nunca vê linha fora do alcance, e a paginação é a
    # ÚLTIMA: fatiar antes do filtro daria uma página 2 com linhas que o filtro descartou.
    busca = BuscaExecucoes.de_parametros(
        parametros,
        hoje=timezone.localdate(),
        unidades_lidas=unidades_lidas(perfil, _unidade_escolhida(parametros)),
    )
    filtradas = listar_execucoes(linhas_de_execucoes(busca), consulta_da_listagem(parametros, ColunaExecucao))
    return {"pagina": paginar(filtradas, _numero_da_pagina(parametros), TAMANHO_PAGINA)}


def _opcoes_de_unidade(perfil: Perfil) -> list[Unidade]:
    """Vazio para quem não dirige nada, e o template não desenha o campo.

    Um select de uma opção só não é escolha — é decoração que ocupa espaço e sugere um recorte que
    não existe. A ausência do controle é a mensagem, como a coluna sem peça na bandeja do cabeçalho
    (skill `componentes-frontend`); campo cinza desabilitado seria o contrário disso.

    As extintas entram na lista: elas estão no alcance, e é justamente o período em que existiram
    que se quer poder abrir.
    """
    if not unidades_dirigidas(perfil):
        return []
    return list(Unidade.todas.filter(pk__in=alcance_de_leitura(perfil)).order_by("sigla"))
```

**`apps/competencias/views.py`** — duas views finas, e é nelas que as camadas se encontram: a mesma
query string carrega os critérios do card e os filtros do cabeçalho; o perfil, só a sessão dá.
```python
@login_required
def listar_registro_acoes(request: HttpRequest) -> HttpResponse:
    """Sem `acao_protegida`: ler o registro não é ato administrativo, e ninguém é recusado aqui —
    o que o alcance faz é decidir o que cada um vê, não se entra (§7)."""
    perfil = cast(Perfil, request.user)
    return render(request, TEMPLATE_REGISTRO_ACOES_LIST, contexto_registro_acoes(perfil, request.GET.dict()))


@login_required
def corpo_execucoes(request: HttpRequest) -> HttpResponse:
    """Alvo do swap: só o <tbody>. Recebe card e cabeçalho na MESMA query string — é isso que faz
    mudar um critério não apagar os filtros, e vice-versa —, e recalcula o alcance a cada chamada:
    ele nunca viaja pelo cliente."""
    perfil = cast(Perfil, request.user)
    return render(request, TEMPLATE_CORPO_EXECUCOES, contexto_corpo_execucoes(perfil, request.GET.dict()))
```

**`templates/competencias/registro_acoes_list.html`** — a coreografia HTMX: dois formulários, um alvo, e
cada um incluindo os campos do outro. Sem isso, o último gesto apagaria o anterior.
```html
<form id="busca-execucoes"
      hx-get="{% url 'competencias:corpo_execucoes' %}"
      hx-trigger="change"
      hx-target="#corpo-execucoes"
      hx-swap="outerHTML"
      hx-include="#tabela-execucoes thead">
  {# Só para quem dirige: sem opções, sem controle. Nasce na unidade do leitor. #}
  {% if unidades %}...{% endif %}
</form>

<table id="tabela-execucoes"
       hx-get="{% url 'competencias:corpo_execucoes' %}"
       hx-trigger="input delay:300ms, ordenacao"
       hx-target="#corpo-execucoes"
       hx-swap="outerHTML"
       hx-include="find thead, #busca-execucoes">

<!-- A paginação vive FORA da <table>: <tbody> não tem irmão que a acomode. Ela dispara para o
     mesmo alvo e volta por swap fora de banda, como a barra de cargos já faz. -->
<div id="paginacao-execucoes"
     hx-get="{% url 'competencias:corpo_execucoes' %}"
     hx-target="#corpo-execucoes"
     hx-swap="outerHTML"
     hx-include="#tabela-execucoes thead, #busca-execucoes">
  <button type="button" name="pagina" value="2" class="paginacao-onsen-alvo">2</button>
</div>
```

**`templates/competencias/partials/_corpo_execucoes.html`** — o `<tbody>` e, fora de banda, a
paginação: uma resposta, dois pedaços da tela.
```html
<tbody id="corpo-execucoes">…</tbody>

{% include "competencias/partials/_paginacao_execucoes.html" with oob=True %}
```

**`apps/painel/abas_declaradas.py`** — o grupo novo, primeiro da aba: o histórico não é um assunto ao
lado dos cargos, é o que atravessa todos eles.
```python
ABA_ADMINISTRACAO = Aba(
    ...,
    grupos=(
        # Item livre: não é ato, não passa por caneta, e por isso este grupo mantém a aba de pé
        # para quem não administra o sistema. Quem entra vê o alcance dele, que nunca é vazio.
        Grupo(
            rotulo="Registro de Ações",
            itens=(
                ItemLivre(
                    slug="painel.lista_registro_acoes",
                    nome="Registro de Ações",
                    tooltip="Os atos praticados no seu alcance: quem, com qual cargo, sobre o quê e se podia.",
                    url_name="competencias:listar_registro_acoes",
                ),
            ),
        ),
        Grupo(rotulo="Administradores", ...),
        ...
    ),
)
```

O glifo é **lista com carimbo** — três linhas de lista com um carimbo circular sobre a última —, em
`static/src/acoes/painel/lista_registro_acoes/icones/grande.svg`, com `stroke: currentColor` e sem cor
dentro do arquivo. Sem ele, o check `painel.E002` derruba a subida.

> ⚠️ Os comentários acima são didáticos e **não são portados**: no código vale o §7.2 do CLAUDE.md.

## 7 · Caveats

**O alvo existe e é sempre um só — quem o resolve, quando a requisição não o nomeia, é o
servidor.** `conferir_alvo` só roda dentro de `acao_protegida`, e ainda que rodasse ele **passa**
quando a leitura não nomeia alvo (`protecao.py`, `if not valores: return`): é exatamente a abertura
da página, onde a query string vem vazia e a unidade de partida é preenchida aqui — passar ali
devolveria o registro inteiro. Custo: a conferência do alvo é escrita de novo, como interseção de
conjuntos em vez de barreira, e duas noções de alcance passam a conviver em
`apps/competencias/consulta.py`.

**A tela é leitura e não ato — e daí decorrem o lugar dela e o silêncio sobre quem a abre.** Ninguém
pode ser impedido de abri-la (a skill `acao-administrativa` é explícita: rotina sem perfil capaz de
**não** poder executá-la não é ação), o §3.5 pede app próprio para **ação**, e o model, a projeção e o
gravador do rastro já moram em `apps/competencias`. Custo: quem leu o registro de quem não aparece em
lugar nenhum, e `competencias` acumula mais uma tela, passando a conhecer `apps/unidades/paleta` para
pintar o ponto da unidade na linha.

**O recorte é sobre a unidade de lotação do autor, não sobre a unidade em que o ato produziu efeito.**
É a única unidade que a `ExecucaoAcao` grava (SPEC `autorizacao/004`, §4). Custo: um ato praticado
**sobre** uma unidade por quem é lotado fora dela não aparece para quem dirige a unidade atingida — e
aparece para quem dirige a do autor.

**Unidade extinta entra no alcance (`com_extintas=True`), ao contrário do que as ações fazem.** O
registro é histórico, e o alcance de ação existe para dizer onde se pode agir hoje. Custo: o mesmo
`alcance_do_perfil` responde duas perguntas diferentes conforme a flag, e trocar o default lá muda
silenciosamente o que esta tela mostra.

**Não há teto sobre o resultado: o período e o alcance são os únicos contenedores.** Cortar no banco
faria o número de páginas mentir sobre quantos atos existem no período, e paginar no banco exigiria
levar o filtro do cabeçalho junto — o que quebraria a normalização única do §6.1, que exige a mesma
função de texto na preparação e na consulta. Custo: quem dirige a unidade-raiz com período largo
materializa em memória todas as execuções da janela, na tabela que mais cresce do projeto.

**A paginação é a última camada e acontece em memória, depois do filtro do cabeçalho.** Fatiar antes
daria uma página 2 com linhas que o filtro já tinha descartado, e levar a filtragem ao banco refaria o
motor que as outras quatro listagens compartilham. Custo: nenhuma linha do período é poupada de ser
materializada, mesmo quando só 50 vão para a tela.

**Cada swap refaz o pipeline inteiro — alcance, árvore, banco, filtro e fatia.** O conjunto de unidades
não pode viajar pelo cliente, e cacheá-lo exigiria invalidar a cada mudança de organograma ou de
titularidade, o mesmo problema que a SPEC `autorizacao/003` já adiou. Custo: trocar de página ou digitar
uma tecla no cabeçalho carrega a árvore hierárquica duas vezes — uma por unidade dirigida, outra pela
subárvore de partida — e relê todas as execuções do período para devolver 50 linhas.

**A tabela de vidro ganha um segundo eixo: `scroll_etched.js` passa a medir os dois, `--coluna-barra`
sobe do rolador para o poço e a tabela larga recebe uma largura mínima.** A barra gravada é vertical
desde a SPEC `user_admin/013`, o rolador esconde as duas barras nativas (`scrollbar-width: none`), e
as barras são irmãs do rolador — de lá não enxergam a medida que impede uma de correr por baixo da
outra. Custo: uma peça implementada muda para todas as tabelas do sistema — as outras quatro passam a
carregar o código de um eixo que não usam —, e a largura mínima fica sendo decisão de cada tabela, não
do componente: quem esquecer o modificador volta a espremer as colunas.

**Período invertido devolve vazio, não erro.** Recusá-lo com `ValidationError` trocaria o `<tbody>`
pelo partial de erro 422 dentro da `<table>`, que não fica de pé ali. Custo: quem inverte as datas vê
"nenhuma execução" e não sabe por quê; data malformada, essa sim, cai no middleware.

**A coluna Momento não filtra nem ordena.** O recorte por tempo é do card, e o motor genérico ordena
por texto normalizado — o que ordenaria "05/09/2026" antes de "31/08/2026". Custo: ordenar por outra
coluna perde a cronologia, e só recarregar a busca a devolve.

**A gravação da paginação passa a carregar informação.** Número, seta e reticência são lidos pela
tinta cheia da rocha-950, e não pelo relevo, o que contraria a regra de que o sulco no gelo nunca
carrega informação. O número da página não tem outro portador: tirá-lo da gravação seria escrever a
paginação fora do material em que o resto do poço está escrito. Custo: a família `.etched` ganha um
membro cuja tinta é de texto, e cada peça nova de gravação passa a ter que decidir de que lado está.

**A paginação já entregue é recomposta na medida do sulco e na tinta.** A medida grande é escolhida
pelo tamanho do alvo, mas quem recebe o filtro é o glifo — num numeral de 16px a banda escura passa
por cima da forma inteira. Custo: uma peça no ar e no styleguide muda de aparência, e o raio da pílula
sai do markup para virar regra da própria molécula, levando junto o `!important` que estava lá.

## 8 · Testes (TDD)

Domínio — puros, sobre o DTO e o motor de listagem:

- `test_busca_sem_criterio_nasce_nos_trinta_dias_e_sem_recorte` — query string vazia vira período de
  30 dias até hoje, com o alcance recebido intacto e os selects em branco resolvidos para `None` —
  nunca id inválido nem `ValidationError`.
- `test_paginacao_fatia_e_prende_o_numero_nos_limites` — 120 linhas viram 3 páginas de 50; `?pagina=0`
  e `?pagina=999` encostam na primeira e na última; lista vazia tem uma página, não zero.
- `test_cabecalho_filtra_e_ordena_dentro_das_linhas_da_busca` — o motor genérico sobre `LinhaExecucao`
  filtra por servidor e por ação com normalização canônica e ordena descendente; fixa que cada membro
  de `ColunaExecucao` casa com um campo da linha, sem o que o filtro casaria com tudo.

Banco — exercitam `ExecucaoAcao` gravada e as views reais:

- `test_leitura_parte_da_propria_unidade` — sem unidade na query string, quem não dirige nada lê só
  a sua; quem dirige lê a sua e as que dirige abaixo dela; o superusuário lê todas; e a unidade
  extinta do ramo continua alcançada. *(marker `banco`)*
- `test_unidade_escolhida_estreita_ou_esvazia` — quem dirige e escolhe uma subordinada lê aquele ramo
  e nada acima dele; `?unidade=<pk alheio>` não traz linha alguma, para quem dirige e para quem não.
  *(marker `banco`)*
- `test_card_oferece_unidade_so_para_quem_dirige` — a tela de quem dirige traz o controle com as
  unidades do alcance e a própria já selecionada; a de quem não dirige não traz o controle.
  *(marker `banco`)*
- `test_busca_combina_autor_cargos_e_periodo_cumulativamente` — os critérios aplicam AND, e execução
  fora da janela de datas não vem. *(marker `banco`)*
- `test_linha_diz_a_autorizacao_a_cobertura_e_o_autor_apagado` — a negada aparece marcada como não
  autorizada, o ato em substituição traz o coberto, o ato por competência própria não, e execução com
  `perfil` nulo materializa sem quebrar. *(marker `banco`)*
- `test_paginacao_percorre_o_resultado_inteiro` — com 600 execuções no alcance, a tela declara 12
  páginas, mostra 50 na primeira e traz as 50 últimas na décima segunda. *(marker `banco`)*
- `test_corpo_aplica_alcance_busca_filtros_e_pagina_da_mesma_query_string` — a rota de corpo recebe
  critérios do card, filtros do cabeçalho e número de página juntos, e aplica os quatro recortes na
  ordem alcance → banco → memória → página. *(marker `banco`)*
