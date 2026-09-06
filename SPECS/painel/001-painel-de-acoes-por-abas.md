---
spec: painel/001
versao: v5
atualizado_em: 2026-08-31
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: o grupo passa a misturar ato administrativo e view livre, e o template do item é do grupo,
    com sobreposição por item
  - v3: o item pode ficar fora de qualquer grupo, acima ou abaixo deles
  - v4: ação inscrita no registro sem card no painel é recusada na subida
  - v5: a skill `painel` entra como entregável, e acrescentar item passa a exigir decidir onde ele
    aparece, como se chama e que glifo carrega
---

# SPEC painel/001 — Painel de ações por abas

## 1 · User story
O servidor da DIMAP escolhe o que fazer no painel que abre logo após o login, entre apenas os atos que
sua caneta libera mais as telas abertas do sistema, para chegar ao que precisa sem conhecer a rota de
cada app.

## 2 · Condições de pronto
- [ ] Entrar no sistema leva ao painel — a página do próprio perfil deixa de ser o destino do login.
- [ ] O card de um **ato administrativo** aparece só para quem tem a caneta dele; o superusuário vê
      todos.
- [ ] O card de uma **view livre** aparece para todo servidor autenticado, sem passar por caneta
      alguma — e o mesmo grupo exibe as duas naturezas lado a lado.
- [ ] O que fica vazio some: grupo sem nenhum item visível não é renderizado, e aba sem grupo algum
      não aparece — nem a tab, nem o conteúdo.
- [ ] A aba básica aparece para todo servidor autenticado e é a que abre.
- [ ] Um item pode ficar **fora de qualquer grupo**, acima ou abaixo deles, e desenha com o template
      do seu continente — salvo quando declara o **seu**, que é como "Sair" vira botão solto no corpo
      da aba onde os demais são cartão em poço.
- [ ] "Sair" encerra a sessão por **POST**; o painel não expõe rota de logout por GET.
- [ ] Visitante anônimo não alcança o painel.
- [ ] Item com rota que não resolve, ou com ícone ausente, é recusado **na subida** — e também o
      painel sem nenhuma aba básica e a ação inscrita no registro que não tem card em aba alguma.
- [ ] Acrescentar item ao painel tem passo a passo na skill `painel`, e a skill
      `acao-administrativa` remete a ela no ponto em que a ação é declarada.
- [ ] O design foi aprovado no mock e as peças novas foram portadas para o tema e o styleguide antes
      de qualquer template da aplicação usá-las.

## 3 · Domínio

O painel é a estrutura **acima** do catálogo de ações: a aba agrupa por assunto, o grupo é o poço que
reúne os cards, e o card é um item — de duas naturezas, que convivem no mesmo grupo.

**`apps/painel/estrutura.py`**
```python
PARTIAL_CARTAO = "painel/partials/_card_item.html"


class ItemAcao(BaseModel):
    """Ato administrativo inscrito no registro: só aparece para quem tem a caneta."""

    model_config = ConfigDict(frozen=True)

    acao: AcaoImplementada
    # Nulo herda o do grupo. Declarado, é a liberdade de dar desenho próprio a UM item.
    partial: str | None = None
    variante_icone: VarianteIcone = VarianteIcone.GRANDE

    @model_validator(mode="after")
    def _variante_declarada(self) -> "ItemAcao":
        if self.variante_icone not in self.acao.acao.variantes_icone:
            raise ValueError(...)
        return self


class ItemLivre(BaseModel):
    """View do sistema que não é ato administrativo. Fora do registro: não é concedível nem
    delegável, não passa por caneta, e traz na mão o que a ação traz no contrato."""

    model_config = ConfigDict(frozen=True)

    # Mesmo formato `<app>.<nome>` das ações: é ele que encontra o SVG.
    slug: str
    nome: str
    tooltip: str
    url_name: str
    # O kwarg que recebe o pk do perfil da sessão. None quando a rota não tem argumento.
    argumento_perfil: str | None = None
    partial: str | None = None
    variante_icone: VarianteIcone = VarianteIcone.GRANDE


class Grupo(BaseModel):
    """O poço da aba. Rótulo e nada mais de texto — descrição por grupo repetiria o parágrafo da aba."""

    model_config = ConfigDict(frozen=True)

    rotulo: str
    itens: tuple[ItemAcao | ItemLivre, ...]
    # O template de todo item deste continente, salvo o que declarar o seu.
    partial_padrao: str = PARTIAL_CARTAO


class Aba(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    # As três faces que a aba mostra: o texto da tab, o que abre com ela, e o parágrafo abaixo.
    rotulo: str
    titulo: str
    descricao: str
    # Solto no corpo da aba, sem poço: dois campos e não uma posição, porque o que muda entre eles
    # é só onde o item entra na página.
    itens_acima: tuple[ItemAcao | ItemLivre, ...] = ()
    grupos: tuple[Grupo, ...] = ()
    itens_abaixo: tuple[ItemAcao | ItemLivre, ...] = ()
    partial_padrao: str = PARTIAL_CARTAO
    # Aba do sistema: nunca some, e é ela que garante painel não-vazio.
    basica: bool = False


class ContratoPainel(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Ordem de exibição é a de declaração: campo de ordenação seria um segundo lugar para o mesmo.
    abas: tuple[Aba, ...]
```

O que a resolução devolve, no formato que o cartão já consome:

```python
class ItemResolvido(BaseModel):
    model_config = ConfigDict(frozen=True)

    partial: str
    url: str
    nome: str
    tooltip: str
    slug: str
    variante_icone: VarianteIcone


class GrupoResolvido(BaseModel):
    model_config = ConfigDict(frozen=True)

    rotulo: str
    itens: tuple[ItemResolvido, ...]


class AbaResolvida(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    rotulo: str
    titulo: str
    descricao: str
    itens_acima: tuple[ItemResolvido, ...]
    grupos: tuple[GrupoResolvido, ...]
    itens_abaixo: tuple[ItemResolvido, ...]

    def vazia(self) -> bool:
        return not (self.itens_acima or self.grupos or self.itens_abaixo)


class PainelResolvido(BaseModel):
    model_config = ConfigDict(frozen=True)

    abas: tuple[AbaResolvida, ...]
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`AcaoImplementada` e `VarianteIcone`](../autorizacao/001-catalogo-de-acoes-em-codigo.md) — "o que
  esta ação é, e quais variantes de ícone ela possui?".
- [`slugs_liberados`](../autorizacao/005-contrato-de-menu-e-router.md) — "quais slugs esta sessão pode
  executar?", com o atalho do superusuário.
- [`ResolvedorIcones`](../autorizacao/006-icones-e-renderizacao-do-menu.md) — "qual glifo desenha este
  slug?".

**Mock:** [001-mock-painel-de-acoes-por-abas.html](001-mock-painel-de-acoes-por-abas.html) — leia a
skill `mock`.

## 4 · Fora de escopo
- Ação **definir titular**: o ato de domínio existe em `apps/unidades/titularidade.py` e não tem rota
  web alguma — entra no grupo "Organograma" quando for inscrita. SPEC própria, sem dono ainda.
- **CRUD de cargos em comissão**: `CargoComissao` só entra por seed e só é lido. O grupo "Cargos em
  Comissão" nasce sem nenhum item e, por isso, não renderiza. SPEC própria, sem dono ainda.
- Ação **delegar competência**: as rotas de delegação existem em `apps/competencias/urls.py` sem
  contrato inscrito, autorizadas por conferência inline. Enquanto não for ação, não tem card. SPEC
  própria do épico `autorizacao`, sem dono ainda.
- Gaveta da entidade territorial: outro menu, escolhido pelo tipo da entidade — épico de busca.
- Busca e ordenação dentro do painel; aba que muda conforme o tipo de entidade — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/competencias/schemas.py` → `AcaoImplementada`: o que o `ItemAcao` envelopa.
- `@apps/competencias/resolucao.py` → `slugs_liberados`: o conjunto do perfil, com o atalho do
  superusuário.
- `@apps/competencias/icones.py` → `ResolvedorIcones` e a templatetag `icone_acao`: o SVG inline por
  slug e variante.
- `@apps/competencias/checks.py` → `GABARITO_CAMINHO_ICONE` e o padrão de system check por registro.
- `@apps/competencias/registro.py` → `REGISTRO`: as ações inscritas que o check confere.
- `@templates/competencias/partials/_card_acao.html` → o cartão que os dois tipos de item desenham.
- `@templates/user_admin/perfil.html` → o `<form method="post">` de encerrar sessão com
  `btn-etched btn-etched-swell etched`.
- `@static/src/tema-dimap.dev.css` → `.card-well`, `.text-overline`, `.menu-acoes-cartoes`: o poço do
  grupo, seu rótulo e a grade dos cartões.
- Skills: `componentes-frontend`, `mock`, `ontologia`, `escrever-testes`.

## 6 · Snippets

**`apps/painel/abas_declaradas.py`** — a estrutura em código: é aqui que se lê o painel inteiro, e é
aqui que se vê ato e view livre no mesmo poço.
```python
ABA_MINHA_CONTA = Aba(
    slug="painel.minha_conta",
    rotulo="Minha conta",
    titulo="Minha conta",
    descricao=(
        "Seus dados de acesso e identificação no sistema. Não são atos administrativos: estão "
        "disponíveis para todo servidor autenticado, qualquer que seja o cargo ou a unidade."
    ),
    basica=True,
    grupos=(
        Grupo(
            rotulo="Meus dados",
            itens=(
                ItemLivre(
                    slug="painel.meus_dados",
                    nome="Meus dados",
                    tooltip="Sua identificação, lotação e cargos, como o sistema os registra.",
                    url_name="user_admin:pagina_perfil",
                    # A rota do próprio perfil pede o pk: quem o fecha é a sessão, não a declaração.
                    argumento_perfil="pk",
                ),
            ),
        ),
        Grupo(rotulo="Senha", itens=(ITEM_SENHA,)),
    ),
    # Fora de poço e depois dos grupos: sair não é um assunto ao lado dos outros, é o último gesto
    # da página. Único item com template próprio — a rota só encerra a sessão por POST com o token
    # CSRF dela, e nenhum <a href> faz isso.
    itens_abaixo=(
        ItemLivre(
            slug="painel.sair",
            nome="Encerrar sessão",
            tooltip="Sai do sistema neste navegador.",
            url_name="autenticacao:logout",
            partial="painel/partials/_botao_sair.html",
        ),
    ),
)

ABA_RECURSOS_HUMANOS = Aba(
    slug="painel.recursos_humanos",
    rotulo="Recursos Humanos",
    titulo="Recursos Humanos",
    descricao=(
        "O quadro de pessoal da DIMAP: quem está cadastrado, onde está lotado e quais cargos ocupa "
        "— e quem está afastado ou respondendo pelo cargo de outro. Alcança as unidades que você "
        "dirige e as subordinadas a elas."
    ),
    grupos=(
        Grupo(
            rotulo="Servidores",
            itens=(
                # Consultar o quadro é leitura aberta: some para ninguém.
                ItemLivre(
                    slug="painel.lista_servidores",
                    nome="Lista de servidores",
                    tooltip="Todo o quadro, filtrável por unidade, cargo e situação.",
                    url_name="user_admin:listar_servidores",
                ),
                ItemAcao(acao=ACAO_CRIAR_SERVIDOR),
                ItemAcao(acao=ACAO_EDITAR_SERVIDOR),
            ),
        ),
        Grupo(
            rotulo="Impedimentos e Substituições",
            itens=(
                ItemAcao(acao=ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR),
                ItemAcao(acao=ACAO_DESIGNAR_SUBSTITUTO),
            ),
        ),
    ),
)

ABA_ESTRUTURA = Aba(
    slug="painel.estrutura_administrativa",
    rotulo="Estrutura Administrativa",
    titulo="Estrutura Administrativa",
    descricao=(
        "A forma da DIMAP: as unidades que a compõem, como se subordinam, os cargos em comissão que "
        "existem e quem responde pela direção de cada uma."
    ),
    grupos=(
        Grupo(
            rotulo="Organograma",
            itens=(
                ItemLivre(
                    slug="painel.lista_unidades",
                    nome="Ver o organograma",
                    tooltip="A árvore de unidades e a tabela filtrável que a acompanha.",
                    url_name="unidades:listar_unidades",
                ),
                ItemAcao(acao=ACAO_CRIAR_UNIDADE),
                ItemAcao(acao=ACAO_EDITAR_UNIDADE),
                ItemAcao(acao=ACAO_CRIAR_UNIDADE_RAIZ),
            ),
        ),
        # Nasce sem item nenhum (§4) e, pela cascata, não renderiza. Declarado porque o lugar dele na
        # estrutura já está decidido.
        Grupo(rotulo="Cargos em Comissão", itens=()),
    ),
)

ABA_ATRIBUICOES = Aba(
    slug="painel.atribuicoes",
    rotulo="Atribuições",
    titulo="Atribuições e Competências",
    descricao=(
        "Quem pode praticar cada ato administrativo. Primeiro a unidade recebe a atribuição da ação; "
        "depois a competência é distribuída entre os cargos que a exercem, e pode ser delegada "
        "nominalmente a um servidor."
    ),
    grupos=(
        Grupo(rotulo="Atribuições das unidades", itens=(ItemAcao(acao=ACAO_DEFINIR_ATRIBUICAO),)),
        Grupo(rotulo="Competências e Delegações", itens=(ItemAcao(acao=ACAO_CONCEDER),)),
        # Plenos poderes não é competência de unidade nem delegação: grupo próprio, que some inteiro
        # para quem não é superusuário.
        Grupo(rotulo="Administração do Sistema", itens=(ItemAcao(acao=ACAO_TORNAR_ADMINISTRADOR),)),
    ),
)

PAINEL = ContratoPainel(
    abas=(ABA_MINHA_CONTA, ABA_RECURSOS_HUMANOS, ABA_ESTRUTURA, ABA_ATRIBUICOES),
)
```

**`apps/painel/resolucao.py`** — a cascata: o item filtra, o grupo some vazio, a aba some sem grupo.
```python
class ResolvedorPainel:
    """A regra inteira do painel está aqui: quem não tem caneta não vê o ato, o que é livre nunca
    some, e o que ficou vazio desaparece."""

    def __call__(self, montagem: MontagemPainel) -> PainelResolvido:
        return self.pipeline(montagem)

    def pipeline(self, montagem: MontagemPainel) -> PainelResolvido:
        abas = (self._aba(aba, montagem) for aba in montagem.painel.abas)
        # A aba básica sobrevive por ser básica, não por ter sobrado item: é ela que impede o painel
        # de abrir vazio.
        return PainelResolvido(abas=tuple(aba for aba in abas if not aba.vazia() or aba.basica))

    def _aba(self, aba: Aba, montagem: MontagemPainel) -> AbaResolvida:
        grupos = (self._grupo(grupo, montagem) for grupo in aba.grupos)
        return AbaResolvida(
            slug=aba.slug,
            rotulo=aba.rotulo,
            titulo=aba.titulo,
            descricao=aba.descricao,
            # O avulso passa pelo MESMO filtro: estar fora de poço é posição na página, não dispensa.
            itens_acima=self._itens(aba.itens_acima, aba.partial_padrao, montagem),
            grupos=tuple(grupo for grupo in grupos if grupo.itens),
            itens_abaixo=self._itens(aba.itens_abaixo, aba.partial_padrao, montagem),
        )

    def _grupo(self, grupo: Grupo, montagem: MontagemPainel) -> GrupoResolvido:
        return GrupoResolvido(
            rotulo=grupo.rotulo,
            itens=self._itens(grupo.itens, grupo.partial_padrao, montagem),
        )

    def _itens(
        self,
        itens: tuple[ItemAcao | ItemLivre, ...],
        partial_padrao: str,
        montagem: MontagemPainel,
    ) -> tuple[ItemResolvido, ...]:
        return tuple(
            self._item(item, partial_padrao, montagem.perfil_id)
            for item in itens
            if self._visivel(item, montagem.slugs_liberados)
        )

    def _visivel(self, item: ItemAcao | ItemLivre, slugs_liberados: frozenset[str]) -> bool:
        # O livre não é ato: não há caneta que o libere, e por isso não há caneta que o esconda.
        if isinstance(item, ItemLivre):
            return True
        return item.acao.acao.slug in slugs_liberados

    def _item(self, item: ItemAcao | ItemLivre, partial_padrao: str, perfil_id: int) -> ItemResolvido:
        # As duas naturezas convergem para o MESMO resolvido: o template desenha um card só, e o
        # padrão do continente só cede quando o item traz o seu.
        partial = item.partial or partial_padrao
        if isinstance(item, ItemLivre):
            argumentos = {item.argumento_perfil: perfil_id} if item.argumento_perfil else {}
            return ItemResolvido(
                partial=partial,
                url=reverse(item.url_name, kwargs=argumentos),
                nome=item.nome,
                tooltip=item.tooltip,
                slug=item.slug,
                variante_icone=item.variante_icone,
            )
        acao = item.acao.acao
        return ItemResolvido(
            partial=partial,
            url=reverse(item.acao.url_name),
            nome=acao.nome,
            tooltip=acao.tooltip,
            slug=acao.slug,
            variante_icone=item.variante_icone,
        )
```

**`apps/painel/checks.py`** — o que o registro de ações já cobra das ações, cobrado dos itens livres;
e, no outro sentido, o painel cobrado de dar destino a toda ação inscrita.
```python
# Ação que deliberadamente não tem card no painel — a que só existe dentro de outra tela, ou a que
# opera sobre entidade territorial. Uma linha por exceção; hoje, nenhuma.
ACOES_SEM_CARD: frozenset[str] = frozenset()


# O registro entra por argumento, como em `competencias.checks`: o check registrado injeta o global,
# e o teste monta o seu.
def validar_painel(painel: ContratoPainel, registro: RegistroAcoes) -> list[Error]:
    erros: list[Error] = []
    if not any(aba.basica for aba in painel.abas):
        # Sem ela, o servidor sem caneta alguma cai numa página sem nada — e o login o manda para lá.
        erros.append(Error("Painel sem nenhuma aba básica.", id="painel.E001"))

    for item in _itens_livres(painel):
        prefixo, nome = item.slug.split(".")
        caminho = GABARITO_CAMINHO_ICONE.format(
            app=prefixo,
            nome=nome,
            variante=item.variante_icone.value,
        )
        if finders.find(caminho) is None:
            erros.append(Error(f"Ícone de '{item.slug}' não encontrado em '{caminho}'.", id="painel.E002"))
        if not _rota_existe(item.url_name):
            erros.append(Error(f"url_name '{item.url_name}' de '{item.slug}' não resolve.", id="painel.E003"))

    return erros + _acoes_orfas(painel, registro)


def _acoes_orfas(painel: ContratoPainel, registro: RegistroAcoes) -> list[Error]:
    com_card = {item.acao.acao.slug for item in _itens_acao(painel)}
    return [
        # Sem card, o ato segue atribuível e concedível — e sem caminho até a rota que o executa.
        Error(f"Ação '{item.acao.slug}' inscrita no registro e sem card no painel.", id="painel.E004")
        for item in registro.todas()
        if item.acao.slug not in com_card | ACOES_SEM_CARD
    ]
```

**`apps/painel/views.py`** — orquestração, e nada além dela.
```python
@login_required
def painel(request: HttpRequest) -> HttpResponse:
    perfil = cast(Perfil, request.user)
    resolvido = ResolvedorPainel()(
        MontagemPainel(
            painel=PAINEL,
            slugs_liberados=slugs_liberados(perfil),
            perfil_id=perfil.pk,
        )
    )
    return render(request, "painel/painel.html", {"painel": resolvido, **contexto_fundo_admin()})
```

`apps/autenticacao/views.py` passa a redirecionar para `painel:painel` nos dois pontos que hoje
apontam para `user_admin:pagina_perfil` — o login e a validação do OTP de primeiro acesso.

**`.claude/skills/painel/SKILL.md`** — o roteiro de acrescentar item, e o portão que impede ação sem
lugar. Sucinta: é o agente que a lê, e o detalhe já está no resto desta SPEC.
```markdown
---
name: painel
description: Como acrescentar um item ao painel de ações — item livre e card de ação, o SVG que o
  slug determina, grupo e aba novos. Use SEMPRE que for expor uma tela nova no painel e SEMPRE ao
  declarar uma ação administrativa.
---

## Antes de acrescentar qualquer item: pergunte, nunca decida
Onde o item aparece, como se chama e que glifo carrega é decisão de quem conhece o processo — e ação
sem card derruba a subida (`painel.E004`). Pergunte, nesta ordem:

1. **Ação:** ela entra no painel? Se não, qual o destino dela — e o motivo, que vira a linha em
   `ACOES_SEM_CARD`.
2. Em qual aba: uma das declaradas em `abas_declaradas.py`, ou uma nova?
3. Em qual grupo dela — ou fora de poço, acima ou abaixo dos grupos?
4. Em que posição dentro do grupo? A ordem exibida é a de declaração.
5. Aba nova: rótulo da tab, título e o parágrafo de descrição?
6. Grupo novo: rótulo?
7. Qual o glifo do ícone? Proponha o desenho em palavras e **espere o ok antes de gravar o
   arquivo** — nenhum item chega ao painel com ícone escolhido por conta própria.
8. **Item livre:** `nome` do card, `tooltip` (que é a descrição impressa nele) e `slug` — este
   determina a pasta do SVG. Na ação os três vêm do contrato e não se pergunta de novo.

## Acrescentar item livre
<a view protegida, o SVG em `acoes/painel/<nome>/icones/`, o `ItemLivre` na posição, o que o check
cobra — e por que ele não entra no registro de ações>

## Acrescentar card de ação
<a ordem: skill `acao-administrativa` primeiro, inscrição no registro, um SVG por variante
declarada, e só então o `ItemAcao`>

## Grupo e aba novos
<os campos de cada um, grupo vazio que não renderiza, e `basica` como flag de uma aba só>

## Desenho próprio
<`partial` do item sobrepõe o do grupo; componente novo nasce no design system, aprovado no mock>
```

A skill `acao-administrativa` ganha, no ponto em que a ação é declarada, uma linha remetendo à skill
`painel`: é ali que a pergunta precisa acontecer, não depois de a ação estar escrita.

> ⚠️ Os comentários acima são didáticos e **não são portados**: no código vale o §7.2 do CLAUDE.md.

## 7 · Caveats

**O item livre não é registrado em lugar nenhum.** Inscrevê-lo no registro de ações o tornaria
atribuível e concedível, e é justamente a distinção entre ato e leitura pública que o registro curado
existe para manter (CLAUDE.md §3.5). Custo: a rota de um item livre não é conferida na execução — quem
a protege, se precisar, é o `login_required` dela, não o painel.

**O template do item mora no grupo, e o item o sobrepõe.** Ler o `partial` do contrato da ação faria
todo card do painel nascer com a forma de linha que aquele campo declara, e obrigaria a mudar as dez
ações para mudar o desenho de uma tela. Custo: o mesmo ato desenha diferente conforme o menu que o
exibe, e o contrato da ação deixa de ser a fonte única do seu partial.

**Os tipos e o resolvedor do painel moram em `apps/painel`, não em `services/`.** A cascata resolve
`reverse` do Django, e separar a regra do que ela compõe poria metade de cada lado. Custo: uma regra de
negócio real fica fora de `services/`, e testá-la exige as URLs do Django carregadas.

**O ícone de item livre mora em `static/src/acoes/painel/<nome>/icones/`.** É o único gabarito que o
`ResolvedorIcones` conhece, e um segundo resolvedor custaria mais que o desvio. Custo: a pasta chamada
`acoes/` passa a guardar glifos do que deliberadamente não é ação, e a população deles cresce a cada
tela que o painel adotar.

**`apps/painel` importa `competencias`, `user_admin`, `unidades` e `autenticacao`.** É o segundo módulo
— depois de `apps/competencias/registro.py` — que conhece todos os apps de uma vez. Custo: a ordem de
import fica amarrada, e erro de declaração derruba a subida em vez de aparecer no render.

**O painel resolve a estrutura inteira a cada request.** São dezenas de itens sobre um conjunto de
slugs que o backend de competência já cacheia por instância de usuário, e memoizar por perfil traria
invalidação para um custo que não se mede. Custo: a resolução é O(n) sobre um catálogo que cresce a
cada ação e a cada tela nova do projeto.

**O contrato de menu de `apps/competencias/menus.py` deixa de existir**, junto com
`menus_declarados.py` e os partials `_menu_acoes.html` e `_item_menu.html`. O painel é o mesmo
roteamento num nível acima, com item de duas naturezas e template por grupo, e manter os dois faria a
mesma ação aparecer em dois agrupamentos livres para divergir. Custo: a gaveta da entidade territorial,
quando existir, monta o menu dela sobre `Grupo`, e não sobre um contrato pensado para ela.

**O painel é o único destino de uma ação inscrita, e o check cobra isso na subida.** Com o contrato
de menu extinto, `abas_declaradas.py` é o único lugar que resolve a rota de um ato, e ação sem card
fica atribuível, concedível e inexecutável. Custo: `apps/painel/checks.py` passa a conhecer o
`REGISTRO`, e a ação que legitimamente não pertence ao painel — a que operar sobre entidade
territorial, quando a gaveta existir — só passa por uma linha em `ACOES_SEM_CARD`.

**O passo a passo de acrescentar item mora na skill, não nesta SPEC.** A skill é o que se lê antes
de mexer no painel, e repetir o roteiro aqui faria a SPEC ser consultada para operação de rotina.
Custo: o gabarito do ícone e os nomes dos campos passam a existir em dois lugares, e mudar a
estrutura do painel obriga a reescrever a skill no mesmo commit.

**Aba vazia some sem dizer nada.** Sinalizar "existem atos que você não alcança" exigiria enumerar o
que o usuário não pode, que é informação de competência alheia. Custo: quem tem poucas canetas não tem
pista de que o painel tem mais.

## 8 · Testes (TDD)

Comportamento — puros, sobre o resolvedor, com o conjunto de slugs montado no teste:

- `test_grupo_mistura_ato_filtrado_e_view_livre` — sem a caneta do ato, o grupo continua no painel com
  só o item livre dentro.
- `test_grupo_sem_item_visivel_nao_entra_no_painel` — grupo cujos itens são todos atos não liberados
  não aparece na aba resolvida.
- `test_aba_sem_grupo_visivel_nao_entra_no_painel` — aba com todos os grupos vazios some inteira.
- `test_aba_basica_entra_sem_caneta_alguma` — com o conjunto de slugs vazio, a aba básica resolve
  inteira, com os dois grupos e o avulso de sair.
- `test_ordem_declarada_preservada_em_abas_grupos_e_itens` — o que sobra mantém a ordem do contrato,
  nos três níveis.
- `test_item_usa_partial_do_continente_e_o_proprio_quando_declara` — o item sem `partial` recebe o
  padrão do grupo ou da aba que o contém; o de "Sair" recebe o seu.
- `test_item_avulso_resolve_fora_dos_grupos_e_passa_pelo_mesmo_filtro` — o avulso chega em
  `itens_acima`/`itens_abaixo`, na ordem declarada, e o que é ato sem caneta não chega.
- `test_item_livre_com_argumento_resolve_url_com_o_perfil_da_sessao` — "Meus dados" aponta para a
  página do perfil de quem está na sessão, e o item sem argumento resolve sem kwargs.
- `test_check_recusa_painel_sem_aba_basica` — contrato sem `basica=True` devolve `painel.E001`.
- `test_check_recusa_item_livre_com_rota_que_nao_resolve` — `url_name` inexistente devolve
  `painel.E003`.
- `test_check_recusa_acao_inscrita_sem_card_no_painel` — ação do registro que não aparece em item
  algum devolve `painel.E004`; a que está em `ACOES_SEM_CARD` passa.

Contrato HTTP — carregam o marker `banco`:

- `test_painel_exige_login` — anônimo não recebe o painel. *(marker `banco`)*
- `test_login_leva_ao_painel` — autenticar redireciona para a rota do painel, não para a página do
  perfil. *(marker `banco`)*
