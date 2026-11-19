---
spec: faq/002
versao: v16
atualizado_em: 2026-11-19
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: upload de imagem inline no editor e vínculo de vídeos (MP4 e YouTube)
  - v3: separa entrada do YouTube de imagens/MP4 e abre modal de metadados no drag-and-drop
  - v4: adapta snippets ao modelo Resposta e renomeia autores para usuarios_upload
  - v5: extrai upload de imagens e vídeos para faq/004, mantendo aqui apenas edição textual
  - v6: vídeos saem do épico
  - v7: aponta o pré-preenchimento da FAQ nova para faq/007
  - v8: o editor deixa de oferecer fórmula e o bloco de imagem próprio do Crepe
  - v9: a FAQ do sistema passa a vir da seed de faq/008
  - v10: exclusão lógica com restauração, e a FAQ do sistema deixa de ser excluível
  - v11: lista de edição na tabela de vidro, e a relacionada excluída fica inerte até a restauração
  - v12: a conferência de pergunta ocupada passa a ser a de faq/001, e o link do formulário se resolve em interno ou externo
  - v13: cadastro de palavras-chave e escolha delas numa árvore horizontal no formulário
  - v14: o vínculo com as telas passa a se chamar rota vinculada, como em faq/006
  - v15: caminhos seguem a estrutura de pacotes de faq/001
  - v16: a área ganha cards na aba Administração do Sistema, visíveis só ao superusuário
---

# SPEC faq/002 — Edição da FAQ pelo administrador

## 1 · User story
O administrador do sistema (superusuário) escreve, revisa e publica FAQs, no contexto de uma área
própria, para manter a FAQ em dia sem depender de deploy nem de desenvolvedor.

## 2 · Condições de pronto
- [ ] O design da área de edição foi aprovado no mock e as peças foram portadas para o tema e o
      styleguide antes de o template da aplicação usá-las.
- [ ] A aba Administração do Sistema do painel traz o grupo "FAQ", com os cards "Lista de FAQs" e
      "Nova FAQ", **só para o superusuário**: os demais servidores não os veem, e a aba segue de pé para
      eles.
- [ ] Só superusuário entra nas telas de edição. Servidor logado sem a marca recebe 403, e anônimo é
      levado ao login.
- [ ] O administrador vê e edita só as FAQs **que ele criou** e as **FAQs do sistema** (sem autor,
      carregadas pela seed de faq/008). A FAQ de outro administrador não aparece na lista e não abre
      nem pelo id na URL. A FAQ do sistema pode ser editada e despublicada, mas não excluída: não há
      gesto de excluir para ela, e o POST forjado é recusado.
- [ ] A lista da área de edição é a tabela de vidro das telas de gestão: filtra por pergunta, tema,
      situação, visibilidade e autor, ordena por qualquer dessas colunas, e o alternador "Mostrar FAQs
      excluídas" revela as excluídas, com o gesto de restaurar na linha.
- [ ] A FAQ é escrita num editor visual (negrito, listas, links, títulos) e é gravada como markdown.
      Reaberta, aparece exatamente como foi escrita, e na página aparece com a mesma formatação.
- [ ] A FAQ nova nasce em **rascunho** e **pública**. Publicar faz a FAQ aparecer na página de FAQ, e
      despublicar a devolve a rascunho e a tira da página.
- [ ] Pergunta ou variação já usada por outra FAQ devolve o formulário com a mensagem em português no
      campo exato, e nada é gravado. Trocar a pergunta principal por uma variação da própria FAQ é
      aceito.
- [ ] O administrador cria e renomeia temas, subtemas e palavras-chave pela própria área de edição, e
      marca as palavras-chave da FAQ numa árvore horizontal: escolher uma palavra abre as filhas dela
      na coluna ao lado, e o que já foi marcado continua marcado ao trocar de ramo.
- [ ] Excluir uma FAQ a tira da página, da busca e da lista de edição, sem apagá-la do banco, e libera
      as perguntas dela para outra FAQ. Restaurá-la a devolve como rascunho; se uma pergunta dela foi
      reaproveitada nesse meio-tempo, a restauração é recusada com a pergunta ocupada na mensagem.
- [ ] Uma relacionada excluída não aparece para o leitor e, na edição da outra FAQ, aparece marcada como
      excluída, sem link nem gesto de remover. Salvar a edição não desfaz o relacionamento, e restaurar
      a excluída o traz de volta nas duas FAQs.

## 3 · Domínio

A ontologia da FAQ e da `Resposta` é a de [faq/001 §3](001-pagina-de-faq.md#3--domínio). Esta SPEC
pergunta a ela quem pode alterar ou excluir uma FAQ e como uma FAQ existente é regravada. A FAQ do
sistema é a de `autor_id = None`. Relacionamento com FAQ excluída é **inerte**: existe, mas não se
mostra ao leitor nem se edita.

```python
# ALTERADO nesta SPEC: `Situacao` (faq/001) ganha EXCLUIDA.
class Situacao(StrEnum):
    RASCUNHO = "rascunho"
    PUBLICADA = "publicada"
    EXCLUIDA = "excluida"                 # NOVO: exclusão lógica; restaurada, volta a RASCUNHO


class Editor(BaseModel):
    """O superusuário que está editando. A marca de superusuário é conferida na view."""
    perfil_id: int


class Edicao(BaseModel):
    """Pedido de regravação de uma FAQ existente, pelo editor."""
    faq: Faq                              # com `id` preenchido; `autor_id` é ignorado na regravação
    editor: Editor

    @model_validator(mode="after")
    def _sem_excluir_pela_edicao(self) -> Self:
        if self.faq.situacao is Situacao.EXCLUIDA:
            raise ValueError("A exclusão é feita pelo botão de excluir.")
        return self
```

Pergunta que esta SPEC faz ao painel ([painel/001](../painel/001-painel-de-acoes-por-abas.md)): este
item é só do superusuário? O `ItemLivre` e a `MontagemPainel` são alterados, e valem como abaixo.

```python
class ItemLivre(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    nome: str
    tooltip: str
    url_name: str
    argumento_perfil: str | None = None
    partial: str | None = None
    variante_icone: VarianteIcone = VarianteIcone.GRANDE
    somente_superusuario: bool = False    # ALTERADO nesta SPEC: campo novo; o item some para os demais


class MontagemPainel(BaseModel):
    model_config = ConfigDict(frozen=True)

    painel: ContratoPainel
    slugs_liberados: frozenset[str]
    perfil_id: int
    eh_superusuario: bool = False         # ALTERADO nesta SPEC: campo novo
```

**Mock:** [002-mock-edicao-de-faq.html](002-mock-edicao-de-faq.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Anexos documentais (PDF/DOCX) com extração de texto na edição — faq/003.
- Envio de imagens no editor e modal de metadados — faq/004.
- Rotas vinculadas da FAQ (as telas em que o widget de ajuda a oferece) — faq/006.
- Abrir `faq:admin_nova` já preenchido a partir do painel de buscas — faq/007.
- Excluir ou mover tema ou palavra-chave — sem dono ainda; hoje os dois são protegidos (`PROTECT`).
- Expurgo definitivo de FAQ excluída — sem dono ainda.
- Histórico de versões da FAQ — sem dono ainda.
- Transferir a autoria de uma FAQ para outro administrador — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/faq/conteudo/cadastro.py` → `gravar_faq` (faq/001): a criação; a regravação desta SPEC compõe com ela.
- `@apps/faq/conteudo/cadastro.py` → `conferir_perguntas_livres` e `PerguntaJaRespondida` (faq/001): a pergunta ocupada.
- `@apps/faq/taxonomia/cadastro.py` → `gravar_palavra_chave` (faq/001): a criação da palavra-chave, já com as relacionadas.
- `@services/domain/faq/conteudo/links.py` → `resolver_destino` (faq/001) e `DOMINIOS_DO_SISTEMA`: o link digitado.
- `@services/utils/markdown` → `RenderizadorMarkdown` (faq/001): a FAQ editada é exibida por ele.
- `@services/utils/erros_formulario` → o erro de formulário com o campo destacado.
- `@services/domain/listagem_gestao` → `ListadorTabela` e `ConsultaListagem`: filtro por coluna e ordenação.
- `@apps/core/tabela.py` → `consulta_da_listagem` e `colunas_da_tabela`: query string → consulta e cabeçalho.
- `@templates/user_admin/partials/_tabela_servidores.html` → tabela de vidro, alternador de exonerados e
  gesto crítico por linha (SPECs user_admin/013 e 027): o molde da lista de FAQs.
- `@apps/painel/abas_declaradas.py` → `ABA_ADMINISTRACAO`, `ItemLivre` e `_botao_voltar_painel.html`: o lugar
  e o molde dos cards.
- `@middleware de validação Pydantic` (SPEC infraestrutura/001): `ValidationError` na fronteira.
- Skills: `erros-de-formulario`, `pydantic-validation-errors`, `componentes-frontend`, `daisyui`,
  `htmx-skill`, `mock`, `painel`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

> O comentário didático destes blocos existe só aqui e **não é portado** (CLAUDE.md §7.2).

**`services/domain/faq/edicao/autoria.py`** — a regra de quem altera o quê. É pura, e o app a usa tanto para
filtrar a lista quanto para recusar o id forjado.

```python
def eh_do_sistema(autor_id: int | None) -> bool:
    return autor_id is None


def pode_editar(autor_id: int | None, editor: Editor) -> bool:
    # FAQ do sistema (sem autor) é de todos os administradores; a dos outros, de ninguém além do autor.
    return eh_do_sistema(autor_id) or autor_id == editor.perfil_id


def pode_excluir(autor_id: int | None, editor: Editor) -> bool:
    # A FAQ do sistema é editável por todos e excluível por ninguém: a seed (faq/008) conta com ela.
    return not eh_do_sistema(autor_id) and pode_editar(autor_id, editor)
```

**`apps/faq/acesso.py`** — o portão das rotas de edição.

```python
def superusuario_requerido(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    @wraps(view)
    @login_required
    def _protegida(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not request.user.is_superuser:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return _protegida
```

**`apps/faq/gestao/consulta.py`** — a FAQ alheia some com 404, e não com 403: a existência dela não é
informação para quem não é o autor. A excluída também: só a restauração a enxerga.

```python
SITUACOES_ATIVAS = frozenset({Situacao.RASCUNHO, Situacao.PUBLICADA})


def faq_editavel(
    faq_id: int,
    editor: Editor,
    situacoes: frozenset[Situacao] = SITUACOES_ATIVAS,
) -> FaqModel:
    # Editar, publicar ou excluir uma FAQ já excluída dá 404; restaurar passa {EXCLUIDA}.
    registro = get_object_or_404(FaqModel, pk=faq_id, situacao__in=situacoes)
    if not pode_editar(registro.autor_id, editor):
        raise Http404
    return registro


def faqs_editaveis(
    editor: Editor,
    situacoes: frozenset[Situacao] = SITUACOES_ATIVAS,
) -> QuerySet[FaqModel]:
    # Com o alternador "Mostrar FAQs excluídas" ligado, a tabela pede SITUACOES_ATIVAS | {EXCLUIDA}.
    return FaqModel.objects.filter(
        Q(autor__isnull=True) | Q(autor_id=editor.perfil_id),
        situacao__in=situacoes,
    )
```

**`apps/faq/gestao/cadastro.py`** — a regravação. As perguntas antigas saem antes de as novas entrarem, na
mesma transação. Assim, promover uma variação a pergunta principal não colide com ela mesma no UNIQUE.

```python
@transaction.atomic
def regravar_faq(edicao: Edicao) -> None:
    registro = faq_editavel(edicao.faq.id, edicao.editor)
    # faq/001: a própria FAQ não conta, e a colisão sobe como PerguntaJaRespondida antes do IntegrityError.
    conferir_perguntas_livres([edicao.faq.pergunta, *edicao.faq.variacoes], faq_id=edicao.faq.id)
    registro.perguntas.all().delete()
    registro.links.all().delete()
    _aplicar_campos(registro, edicao.faq)             # resposta_markdown, tema, palavras-chave, visibilidade, situação
    _gravar_perguntas(registro, edicao.faq)
    _gravar_links(registro, edicao.faq.resposta.links)
    registro.relacionadas.set(_relacionadas_regravadas(registro, edicao.faq.relacionadas))


def _relacionadas_regravadas(registro: FaqModel, pedidas: list[int]) -> set[int]:
    # A relacionada excluída não vem no formulário, porque é inerte: regravar só o pedido apagaria o
    # relacionamento, e a restauração não teria o que devolver. Por isso ela é preservada aqui.
    # Relacionar com uma excluída que não estava ligada (id forjado) é ignorado.
    excluidas = set(
        registro.relacionadas.filter(situacao=Situacao.EXCLUIDA).values_list("pk", flat=True)
    )
    ativas = set(
        FaqModel.objects.filter(pk__in=pedidas, situacao__in=SITUACOES_ATIVAS).values_list("pk", flat=True)
    )
    return ativas | excluidas
```

`gravar_faq` (faq/001) passa a recusar `EXCLUIDA` como a `Edicao`.

**`apps/faq/gestao/formularios.py`** — o formulário traduz o que o domínio recusou para o controle certo
(skill `erros-de-formulario`). O link chega como texto e só vira `LinkReferencia` aqui.

```python
def campos_ocupados(erro: PerguntaJaRespondida, faq: Faq) -> list[str]:
    # A mensagem vai no controle da pergunta ocupada e não diz qual FAQ a tem, embora o erro saiba (Caveats).
    campos = {p.chave: campo for campo, p in _perguntas_com_campo(faq)}
    return [campos[o.pergunta.chave] for o in erro.ocupadas]


def link_do_formulario(titulo: str, url: str) -> LinkReferencia:
    # URL recusada (`//x`, `javascript:`, sem host) volta como ValidationError no controle daquele link.
    return LinkReferencia(titulo=titulo, destino=resolver_destino(url, DOMINIOS_DO_SISTEMA))
```

**`apps/faq/gestao/cadastro.py`** — exclusão e restauração. `Pergunta.chave` (faq/001) passa a `null=True`:
a chave nula libera a pergunta no UNIQUE, que não compara nulos, e o texto fica para a restauração.

```python
@transaction.atomic
def excluir_faq(faq_id: int, editor: Editor) -> None:
    registro = faq_editavel(faq_id, editor)
    if not pode_excluir(registro.autor_id, editor):
        raise PermissionDenied              # FAQ do sistema: 403, e nada muda
    registro.situacao = Situacao.EXCLUIDA
    registro.save(update_fields=["situacao", "atualizado_em"])
    registro.perguntas.update(chave=None)


@transaction.atomic
def restaurar_faq(faq_id: int, editor: Editor) -> None:
    registro = faq_editavel(faq_id, editor, situacoes=frozenset({Situacao.EXCLUIDA}))
    linhas = list(registro.perguntas.all())
    # Mesma conferência da regravação: a pergunta reaproveitada por outra FAQ volta na mensagem.
    conferir_perguntas_livres([Pergunta(texto=l.texto) for l in linhas], faq_id=registro.pk)
    for linha in linhas:
        linha.chave = normalize_text(linha.texto)
    PerguntaModel.objects.bulk_update(linhas, ["chave"])
    registro.situacao = Situacao.RASCUNHO   # volta fora da página: republicar é decisão do admin
    registro.save(update_fields=["situacao", "atualizado_em"])
```

**`apps/faq/gestao/context.py`** — o formulário recebe as relacionadas separadas: as ativas viram controle
(link e gesto de remover), as excluídas só aparecem marcadas. A página do leitor não precisa de nada
novo: `MontarIndice` (faq/001) já poda a relacionada que não é `PUBLICADA`.

```python
def relacionadas_do_formulario(registro: FaqModel) -> dict[str, list[FaqModel]]:
    todas = list(registro.relacionadas.all())
    return {
        "relacionadas_ativas": [f for f in todas if f.situacao != Situacao.EXCLUIDA],
        "relacionadas_inertes": [f for f in todas if f.situacao == Situacao.EXCLUIDA],
    }
```

O seletor de novas relacionadas não oferece FAQ excluída.

**`services/domain/listagem_gestao/models/faqs.py`** — a lista de FAQs é mais uma tabela de gestão,
filtrada e ordenada pelo `ListadorTabela` existente, como servidores e unidades.

```python
class ColunaFaq(StrEnum):
    PERGUNTA = "pergunta"
    TEMA = "tema"
    SITUACAO = "situacao"
    VISIBILIDADE = "visibilidade"
    AUTOR = "autor"


class LinhaFaq(BaseModel):
    pk: int
    pergunta: str
    tema: str                              # "Busca › Endereço"
    situacao: str                          # rótulo: "Rascunho", "Publicada", "Excluída"
    visibilidade: str                      # rótulo: "Pública", "Interna"
    autor: str                             # nome do autor, ou "Sistema"
    eh_do_sistema: bool                    # sem gesto de excluir na linha
    excluida: bool                         # linha marcada, com o gesto de restaurar


ConsultaFaqs = ConsultaListagem[ColunaFaq]
ListarFaqs = ListadorTabela[LinhaFaq, ColunaFaq]          # em listagem.py, ao lado dos outros
```

**Publicar e despublicar** são o mesmo POST que troca `situacao` entre `RASCUNHO` e `PUBLICADA`,
protegido por `faq_editavel`, e valem também para a FAQ do sistema. `EXCLUIDA` só chega por
`excluir_faq`.

**`static/src/js/editor_markdown.js`** — o editor é **Milkdown (Crepe)**, empacotado pelo `esbuild` no
estágio de build do front-end (`package.json`), sem CDN. O JS só espelha o markdown num `<textarea>`
oculto do `<form>`. Validação e gravação são do servidor.

```javascript
// Estado visual do controle (CLAUDE.md §7.2), aprovado nesta SPEC: o editor é a única peça de JS.
const crepe = new Crepe({
  root: alvo,
  defaultValue: campo.value,
  // Fora o que o renderizador de faq/001 não mostra: a fórmula, e o bloco de imagem do Crepe, que
  // aceitaria endereço externo (a imagem entra pelo fluxo de faq/004).
  features: { [Crepe.Feature.Latex]: false, [Crepe.Feature.ImageBlock]: false },
});
crepe.on((ouvinte) => ouvinte.markdownUpdated((_ctx, markdown) => { campo.value = markdown; }));
await crepe.create();
```

O resto do que o Crepe oferece (títulos de qualquer nível, riscado, lista de tarefas, tabela, linha
horizontal) o renderizador de faq/001 cobre, e o teste `test_renderizador_cobre_o_markdown_do_editor`
fixa isso.

**Árvore horizontal de palavras-chave** — colunas lado a lado, uma por nível, até três. Escolher uma
palavra troca as colunas à direita pela coluna das filhas dela, num GET HTMX. As marcadas ficam numa
lista à parte, fora das colunas, e é ela que leva os ids ao `<form>`: trocar de ramo descarta colunas,
nunca marcação. A navegação e a marcação são HTMX, sem JS próprio.

**`apps/faq/taxonomia/palavras_chave.py`** — a coluna é a única consulta da árvore. Ela recebe as marcadas para
devolver o checkbox de cada filha já no estado certo.

```python
class OpcaoPalavraChave(BaseModel):
    pk: int
    nome: str
    marcada: bool
    tem_filhas: bool


def coluna_de_palavras_chave(pai_id: int | None, marcadas: set[int]) -> list[OpcaoPalavraChave]:
    filhas = PalavraChaveModel.objects.filter(pai_id=pai_id).annotate(qtd_filhas=Count("filhas"))
    return [
        OpcaoPalavraChave(
            pk=f.pk,
            nome=f.nome,
            marcada=f.pk in marcadas,
            tem_filhas=f.qtd_filhas > 0,           # sem filhas, escolher não abre coluna
        )
        for f in filhas.order_by(Lower("nome"))
    ]
```

**Rotas** — todas protegidas por `superusuario_requerido`. As da FAQ ficam em `apps/faq/gestao/urls.py`,
as de tema e palavra-chave em `apps/faq/taxonomia/urls.py`, e as duas listas entram na de
`apps/faq/urls.py` (faq/001):

| Rota | O que faz |
|---|---|
| `faq:admin_lista` | página com a tabela de vidro das FAQs editáveis |
| `faq:admin_corpo` | o `<tbody>` filtrado e ordenado, alvo do HTMX; `excluidas=1` inclui as excluídas |
| `faq:admin_nova` | formulário de criação |
| `faq:admin_editar` | formulário de edição |
| `faq:admin_situacao` | publicar / despublicar (POST) |
| `faq:admin_excluir` | modal de confirmação (GET) e exclusão lógica (POST); recusada na FAQ do sistema |
| `faq:admin_restaurar` | restauração como rascunho (POST), pelo gesto da linha excluída |
| `faq:admin_palavras_chave_coluna` | a coluna das filhas (GET, alvo do HTMX); sem `pai`, as raízes; as marcadas chegam pelo `hx-include` da lista |
| `faq:admin_palavra_chave_nova` / `faq:admin_palavra_chave_renomear` | palavras-chave, em qualquer dos três níveis |
| `faq:admin_tema_novo` / `faq:admin_tema_renomear` | temas e subtemas |

**`apps/painel/resolucao.py`** — o item livre continua fora da cascata de competência; a única exceção é a
marca de superusuário, que o `ItemLivre` declara e a resolução confere.

```python
def _visivel(self, item: ItemAcao | ItemLivre, montagem: MontagemPainel) -> bool:
    if isinstance(item, ItemLivre):
        # Só esconde o card: a barreira real é `superusuario_requerido`, na rota.
        return montagem.eh_superusuario or not item.somente_superusuario
    return item.acao.acao.slug in montagem.slugs_liberados
```

`apps/painel/views.py` passa `eh_superusuario=perfil.is_superuser` à `MontagemPainel`.

**`apps/painel/abas_declaradas.py`** — novo grupo em `ABA_ADMINISTRACAO`, depois de "Administradores". Grupo
sem item visível não renderiza, então os demais servidores não o veem. Os dois destinos são telas
próprias, e levam `{% include "partials/_botao_voltar_painel.html" %}`.

```python
Grupo(
    rotulo="FAQ",
    itens=(
        ItemLivre(
            slug="painel.lista_faqs",
            nome="Lista de FAQs",
            tooltip="As FAQs que você pode editar, com filtro, exclusão e restauração.",
            url_name="faq:admin_lista",
            somente_superusuario=True,
        ),
        ItemLivre(
            slug="painel.nova_faq",
            nome="Nova FAQ",
            tooltip="Escreve uma FAQ nova, que nasce como rascunho.",
            url_name="faq:admin_nova",
            somente_superusuario=True,
        ),
    ),
),
```

Os SVGs ficam em `static/src/acoes/painel/lista_faqs/icones/grande.svg` e
`static/src/acoes/painel/nova_faq/icones/grande.svg`.

## 7 · Caveats

**A edição da FAQ não é ação administrativa (CLAUDE.md §3.5).** A FAQ documenta o uso do sistema, não
um processo da DIMAP, e a competência é só "ser superusuário". Por isso a execução **não é registrada**
em `ExecucaoAcao`, e quem mudou o quê se sabe só por `autor` e `atualizado_em`.

**O painel de faq/001 é alterado: o `ItemLivre` deixa de ser sempre visível.** O campo novo tem default
`False`, então nenhum item existente muda. A marca de superusuário passa a existir em dois lugares, o
card e `superusuario_requerido`, e só o segundo é barreira; um card escondido não protege rota alguma.
`painel/001` descreve o `ItemLivre` sem o campo, e esta SPEC é a que vale até ela ser revista.

**Uma terceira peça de JavaScript entra no projeto: o editor Milkdown, com etapa de bundle.** Escrever
markdown à mão afastaria quem mantém a FAQ, e um editor visual não sai de HTMX. O custo é uma
dependência de front-end mantida por terceiros e um passo de build a mais no container do CSS.

**A pré-checagem revela que uma pergunta já existe, mesmo quando ela está no rascunho de outro
administrador.** A unicidade é global, e esconder a colisão deixaria o administrador sem saber por que
a gravação falhou. O que vaza é só que a pergunta está ocupada, não a FAQ nem o autor.

**Regravar apaga e recria perguntas e links.** É o jeito mais simples de manter o UNIQUE consistente
quando uma variação vira pergunta principal. Os ids dessas linhas não são estáveis, e nada pode apontar
para eles.

**A FAQ do sistema é editável e despublicável por qualquer superusuário, continua sem autor depois da
edição e não é excluível.** Ela é bootstrap compartilhado, não obra de alguém, e a seed (faq/008)
conta com a existência dela. Duas edições simultâneas sobre a mesma FAQ do sistema seguem a regra "a
última gravação vence", sem aviso, e uma FAQ do sistema despublicada fica fora da página até alguém
republicá-la.

**A FAQ excluída fica no banco com a chave das perguntas nula.** É o que libera a pergunta no UNIQUE
sem perder o texto que a restauração recalcula. "Chave nula ⇔ FAQ excluída" depende de `excluir_faq` e
`restaurar_faq` serem as únicas portas dessa transição.

**A FAQ excluída mantém os vínculos: relacionadas, rotas vinculadas, anexos e imagens.** Toda leitura de 001 a 007
filtra por `PUBLICADA`, então ela some sem tocar nessas SPECs, e a restaurada volta inteira. O custo é
que toda consulta nova sobre FAQ precisa lembrar desse filtro.

**O relacionamento com FAQ excluída é preservado pela regravação, e não pelo formulário.** A relacionada
inerte não tem controle na tela, e só `_relacionadas_regravadas` impede que salvar a apague. Enquanto a
outra está excluída, o administrador não consegue desfazer o relacionamento: precisa restaurá-la,
remover e excluir de novo.

**A tabela de FAQs carrega todas as linhas editáveis e filtra em memória.** É o padrão do
`ListadorTabela`, e o volume esperado é de dezenas a poucas centenas de FAQs. Se crescer, a tabela
precisa de paginação, como a de execuções.

## 8 · Testes (TDD)
- `test_rotas_de_edicao_exigem_superusuario` — parametrizado sobre as rotas: anônimo → login, logado
  sem marca → 403; e o painel mostra o grupo "FAQ" ao superusuário e o esconde do servidor comum, que
  ainda vê a aba. *(marker `banco`)*
- `test_faq_de_outro_admin_nao_aparece_nem_abre` — some da lista, e GET/POST com o id forjado dá 404.
  *(marker `banco`)*
- `test_faq_do_sistema_eh_editavel_e_despublicavel_mas_nao_excluivel` — dois administradores editam e
  despublicam a mesma FAQ sem autor, e ela continua sem autor; o botão de excluir não aparece para
  ela, e o POST forjado em `faq:admin_excluir` dá 403 sem mudar nada. *(marker `banco`)*
- `test_formulario_devolve_erro_no_campo` — parametrizado: variação igual à pergunta de outra FAQ
  volta com a mensagem em português no controle daquela variação, e subtema sob subtema e
  palavra-chave sob uma de terceiro nível, no campo `pai`; nada muda no banco. *(marker `banco`)*
- `test_lista_de_faqs_filtra_ordena_e_revela_excluidas` — `faq:admin_corpo` filtra por tema e
  ordena por pergunta; a excluída só aparece com `excluidas=1`, marcada e com o gesto de restaurar, e
  a FAQ do sistema sai sem o gesto de excluir. *(marker `banco`)*
- `test_promover_variacao_a_pergunta_principal` — trocar pergunta e variação de lugar regrava sem
  colisão. *(marker `banco`)*
- `test_faq_nova_nasce_rascunho_e_publica_e_publicacao_muda_a_pagina` — criada sem tocar nos dois
  controles, não aparece em `/faq/` até ser publicada; publicada aparece para anônimo, e despublicada
  some. *(marker `banco`)*
- `test_markdown_editado_volta_identico` — o markdown enviado é o mesmo que reabre no formulário,
  byte a byte. *(marker `banco`)*
- `test_excluir_eh_logico_e_restaurar_volta_rascunho` — a excluída some de `/faq/` e da lista de
  edição, continua no banco, e outra FAQ grava a mesma pergunta; restaurar uma excluída de pergunta
  livre a devolve como rascunho, e restaurar uma de pergunta reaproveitada é recusado com a mensagem,
  sem mudar nada. *(marker `banco`)*
- `test_relacionada_excluida_fica_inerte_e_volta_na_restauracao` — com A e B relacionadas e B
  excluída: `/faq/` não mostra B na resposta de A, o formulário de A traz B só como inerte, regravar A
  mantém o vínculo, e restaurar e republicar B o devolve na resposta de A. *(marker `banco`)*
- `test_arvore_de_palavras_chave_abre_filhas_e_preserva_marcadas` — `faq:admin_palavras_chave_coluna`
  sem `pai` devolve só as raízes; com `pai=IPTU` devolve as filhas de `IPTU`, em ordem alfabética, com
  o checkbox da filha que veio no `hx-include` já marcado; marcar uma palavra num ramo, abrir outro e
  marcar outra, e salvar, grava as duas na FAQ. *(marker `banco`)*
