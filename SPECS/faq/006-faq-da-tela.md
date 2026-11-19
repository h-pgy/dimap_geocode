---
spec: faq/006
versao: v6
atualizado_em: 2026-11-19
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: painel sem player de vídeo, que sai do épico
  - v3: o decorator marca a view por atributo, e a ordem dos decorators deixa de importar
  - v4: o Faq vigente acompanha a palavra-chave em árvore de faq/001
  - v5: o vínculo da FAQ com a tela passa a se chamar rota vinculada, muitos-para-muitos e distinto do link de referência
  - v6: caminhos seguem a estrutura de pacotes de faq/001
---

# SPEC faq/006 — FAQ da tela: rotas vinculadas e widget flutuante

## 1 · User story
O servidor da DIMAP, ou o cidadão, abre a ajuda no canto da tela em que está trabalhando e já encontra
as FAQs daquela tela, podendo ainda navegar pela FAQ inteira sem sair dela.

## 2 · Condições de pronto
- [ ] O design do botão flutuante e do painel que ele abre foi aprovado no mock e as peças foram
      portadas para o tema e o styleguide antes de o template da aplicação usá-las.
- [ ] Na edição da FAQ, o administrador escolhe as **rotas vinculadas** dela, numa lista de telas com
      nome legível: as telas do sistema em que a FAQ aparece no widget. Uma FAQ pode ter várias rotas
      vinculadas, e uma rota pode estar vinculada a várias FAQs.
- [ ] Só são oferecidas as telas que o código declara como telas com ajuda. Uma rota de partial, de
      POST ou de administração não aparece na lista.
- [ ] Numa tela com ao menos uma FAQ visível ao leitor, aparece o botão de ajuda no canto inferior
      direito. Numa tela sem FAQ visível, o botão não aparece.
- [ ] O botão abre um painel com todas as FAQs vinculadas àquela rota, em accordion (com as imagens contidas na
      largura do painel), e um "ver todas" que carrega a FAQ inteira no mesmo painel, com volta para
      as da tela.
- [ ] O painel respeita a visibilidade: o anônimo não vê FAQ interna, e rascunho não aparece para
      ninguém.
- [ ] Respostas de HTMX (partials) não pagam consulta nenhuma por causa do widget.
- [ ] Uma rota vinculada que deixa de existir no código é apontada na subida (`manage.py check`), e o
      widget a ignora.

## 3 · Domínio

A ontologia da FAQ é a de [faq/001](001-pagina-de-faq.md#3--domínio), já com [`Resposta`](004-midias-da-faq.md#3--domínio)
estendida por anexos e imagens. Esta SPEC acrescenta a **tela**, uma página do sistema identificada
pelo nome da rota Django, com um rótulo para o administrador, e a **rota vinculada**, que liga a FAQ às
telas em que o widget a oferece. A relação é muitos-para-muitos. A rota vinculada não é
[link de referência](001-pagina-de-faq.md#3--domínio): não aparece na resposta, só decide onde a FAQ
é oferecida.

```python
class Tela(BaseModel):
    """Página do sistema que oferece ajuda. Declarada em código, nunca cadastrada."""
    nome_rota: str = Field(pattern=r"^[a-z_]+:[a-z_]+$")    # "search:busca"
    rotulo: str                                             # "Mapa e busca", para o administrador


# ALTERADO nesta SPEC: `Faq` (faq/001) ganha `rotas_vinculadas`.
class Faq(BaseModel):
    id: int | None = None
    pergunta: Pergunta
    variacoes: list[Pergunta] = []
    resposta: Resposta
    tema: Tema
    palavras_chave: list[PalavraChave] = []
    visibilidade: Visibilidade = Visibilidade.PUBLICA
    situacao: Situacao = Situacao.RASCUNHO
    autor_id: int | None = None
    relacionadas: list[int] = []
    rotas_vinculadas: list[str] = []      # NOVO: `nome_rota` das telas em que o widget oferece a FAQ
```

**Mock:** [006-mock-widget-faq-da-tela.html](006-mock-widget-faq-da-tela.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Busca dentro do painel do widget — faq/007.
- Ajuda por estado de tela (gaveta aberta, desenho selecionado) em vez de por rota — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/autenticacao/context_processors.py` → padrão de context processor do projeto.
- `@services/domain/faq/leitura/indice.py` → `MontarIndice` (faq/001): o accordion do painel é o mesmo índice.
- `@templates/faq/partials/pagina/` → o partial do item do accordion (faq/001 e faq/004), reaproveitado no painel
  mantendo as imagens restritas à largura da caixa.
- `@apps/painel/checks.py` → padrão de system check do projeto.
- Skills: `componentes-frontend`, `daisyui`, `htmx-skill`, `mock`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

> O comentário didático destes blocos existe só aqui e **não é portado** (CLAUDE.md §7.2).

**`apps/faq/telas/declaracao.py`** — o decorator **declara** a tela. Ele não mexe no contexto: só grava o rótulo
num atributo da view.

```python
ATRIBUTO_ROTULO = "tela_com_ajuda_rotulo"


def tela_com_ajuda(rotulo: str) -> Callable[[ViewFunc], ViewFunc]:
    def _marcar(view: ViewFunc) -> ViewFunc:
        # Atributo, e não registro pela identidade da função: o `wraps` de `login_required` e dos
        # outros decorators copia o `__dict__`, então a marca sobrevive em qualquer ordem.
        setattr(view, ATRIBUTO_ROTULO, rotulo)
        return view
    return _marcar


def telas_declaradas() -> list[Tela]:
    # O nome da rota vem do urls.py, não do decorator: renomear a rota não deixa a marca desatualizada.
    return sorted(
        (Tela(nome_rota=nome, rotulo=rotulo) for nome, view in _rotas_nomeadas() if (rotulo := _rotulo(view))),
        key=lambda t: t.rotulo,
    )


def _rotulo(view: Callable[..., HttpResponse]) -> str | None:
    # View de classe: o `as_view()` não copia o `__dict__`, mas guarda a classe em `view_class`.
    classe = getattr(view, "view_class", None)
    return getattr(view, ATRIBUTO_ROTULO, None) or getattr(classe, ATRIBUTO_ROTULO, None)
```

```python
# apps/search/views.py (exemplo de uso)
@tela_com_ajuda("Mapa e busca")
def pagina_busca(request: HttpRequest) -> HttpResponse: ...
```

**`apps/faq/telas/context_processors.py`** — o context processor é o gancho do Django que roda em todo
`render()`. É preguiçoso: só consulta o banco se o template **ler** a variável, e só o `base.html` lê.

```python
def faq_da_tela(request: HttpRequest) -> dict[str, Any]:
    match = request.resolver_match
    if match is None or request.headers.get("HX-Request"):
        return {}
    leitor = leitor_de(request)                                    # apps/faq/leitor.py (faq/001)
    return {"faq_da_tela": SimpleLazyObject(lambda: _indice_da_tela(match.view_name, leitor))}


def _indice_da_tela(nome_rota: str, leitor: Leitor) -> IndiceFaq:
    faqs = carregar_faqs(visibilidades_para(leitor), rota_vinculada=nome_rota)     # apps/faq/conteudo/consulta.py
    return montar_indice(MontagemIndiceInput(faqs=faqs, leitor=leitor))
```

```django
{# templates/base.html #}
{% if faq_da_tela.secoes %}
  {% include "faq/partials/telas/_widget.html" with indice=faq_da_tela %}
{% endif %}
```

**`apps/faq/models/telas.py`**

```python
class RotaVinculada(models.Model):
    # A junção FAQ × rota. A rota não é linha de banco (Caveats): o lado dela é o nome, indexado para o
    # widget, que pergunta "quais FAQs desta rota?".
    faq = models.ForeignKey("faq.Faq", on_delete=models.CASCADE, related_name="rotas_vinculadas")
    nome_rota = models.CharField(max_length=120, db_index=True)

    class Meta:
        constraints = [models.UniqueConstraint("faq", "nome_rota", name="faq_rota_vinculada_unica")]
```

**`services/domain/faq/telas/conferencia.py`** — a validação da rota vinculada é pura: recebe o catálogo pronto.

```python
def conferir_rotas_vinculadas(pedidas: list[str], declaradas: list[Tela]) -> None:
    conhecidas = {t.nome_rota for t in declaradas}
    desconhecidas = [r for r in pedidas if r not in conhecidas]
    if desconhecidas:
        raise ValueError(f"Telas sem ajuda declarada: {', '.join(desconhecidas)}.")
```

O formulário de faq/002 ganha o multi-select de rotas vinculadas, alimentado por `telas_declaradas()`.
A regravação passa por `conferir_rotas_vinculadas` antes de gravar.

**`apps/faq/telas/checks.py`** — `faq.W001`: rota vinculada com `nome_rota` fora de `telas_declaradas()`. É aviso e
não erro: a subida não cai por causa de uma FAQ.

**Rotas** (`apps/faq/telas/urls.py`; abertas, decididas pela visibilidade): `faq:widget_tela` devolve o partial das FAQs de uma
tela, para a volta do "ver todas"; `faq:widget_todas` devolve o partial do índice completo.

## 7 · Caveats

**A granularidade é a página, não o estado da página.** O mapa é uma rota só, e as gavetas mudam por
HTMX sem trocar de rota. Por isso uma FAQ sobre "a gaveta do lote" aparece em todo o mapa. Ajuda por
estado de tela fica sem dono.

**A tela é declarada por decorator, não descoberta.** Introspectar o resolver ofereceria partials e
rotas de POST ao administrador. Uma tela nova só ganha ajuda quando alguém a marca no código.

**O context processor roda em todo `render()`, e o widget mora no `base.html`.** O `SimpleLazyObject` e
o desvio para `HX-Request` fazem a consulta acontecer só em página inteira que extende o `base.html`. O
custo é uma consulta indexada por página inteira, inclusive nas telas sem FAQ.

**A rota vinculada guarda o nome da rota como texto, sem FK.** Rota é código, não linha de banco, e o
`manage.py check` é o que pega a divergência. Entre um deploy que remove a rota e a correção da rota
vinculada, a FAQ fica ligada a uma tela que não existe, sem efeito visível.

## 8 · Testes (TDD)
- `test_so_views_marcadas_viram_tela` — parametrizado: `telas_declaradas()` traz, com o nome da rota
  do `urls.py`, a view marcada acima e abaixo de `@login_required` e a view de classe marcada, e não
  traz uma view não marcada.
- `test_rota_vinculada_nao_declarada_eh_recusada` — o formulário volta com erro em português no campo
  de rotas vinculadas, e nada é gravado. *(marker `banco`)*
- `test_widget_aparece_so_com_faq_visivel` — parametrizado: tela com duas FAQs públicas vinculadas
  mostra o botão e lista as duas no painel; tela sem FAQ vinculada, ou só com rascunho, não mostra.
  *(marker `banco`)*
- `test_widget_esconde_interna_do_anonimo` — mesma tela com FAQ interna: o logado vê o botão, o anônimo
  não. *(marker `banco`)*
- `test_partial_htmx_nao_consulta_faq` — uma view de partial chamada com `HX-Request` não faz nenhuma
  consulta à tabela de rotas vinculadas (`django_assert_num_queries`). *(marker `banco`)*
- `test_ver_todas_e_voltar` — `faq:widget_todas` devolve o índice completo, e `faq:widget_tela` volta
  ao filtrado. *(marker `banco`)*
- `test_check_aponta_rota_vinculada_orfa` — rota vinculada inexistente no código gera `faq.W001`, e o
  widget a ignora. *(marker `banco`)*
