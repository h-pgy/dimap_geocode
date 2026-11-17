---
spec: faq/006
versao: v1
atualizado_em: 2026-11-17
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC faq/006 — FAQ da tela: vínculo por rota e widget flutuante

## 1 · User story
O servidor da DIMAP, ou o cidadão, abre a ajuda no canto da tela em que está trabalhando e já encontra
as FAQs daquela tela, podendo ainda navegar pela FAQ inteira sem sair dela.

## 2 · Condições de pronto
- [ ] O design do botão flutuante e do painel que ele abre foi aprovado no mock e as peças foram
      portadas para o tema e o styleguide antes de o template da aplicação usá-las.
- [ ] Na edição da FAQ, o administrador escolhe, numa lista de telas com nome legível, em quais telas
      do sistema a FAQ aparece.
- [ ] Só são oferecidas as telas que o código declara como telas com ajuda. Uma rota de partial, de
      POST ou de administração não aparece na lista.
- [ ] Numa tela com ao menos uma FAQ visível ao leitor, aparece o botão de ajuda no canto inferior
      direito. Numa tela sem FAQ visível, o botão não aparece.
- [ ] O botão abre um painel com as FAQs daquela tela, em accordion (com imagens e players de vídeo
      contidos na largura do painel), e um "ver todas" que carrega a FAQ inteira no mesmo painel, com
      volta para as da tela.
- [ ] O painel respeita a visibilidade: o anônimo não vê FAQ interna, e rascunho não aparece para
      ninguém.
- [ ] Respostas de HTMX (partials) não pagam consulta nenhuma por causa do widget.
- [ ] Uma rota declarada que deixa de existir no código é apontada na subida (`manage.py check`), e o
      vínculo órfão é ignorado pelo widget.

## 3 · Domínio

A ontologia da FAQ é a de [faq/001](001-pagina-de-faq.md#3--domínio), já com [`Resposta`](004-midias-da-faq.md#3--domínio)
estendida por anexos e mídias. Esta SPEC acrescenta a **tela**: uma página do sistema, identificada
pelo nome da rota Django, com um rótulo para o administrador.

```python
class Tela(BaseModel):
    """Página do sistema que oferece ajuda. Declarada em código, nunca cadastrada."""
    nome_rota: str = Field(pattern=r"^[a-z_]+:[a-z_]+$")    # "search:busca"
    rotulo: str                                             # "Mapa e busca", para o administrador


# ALTERADO nesta SPEC: `Faq` (faq/001) ganha `telas`.
class Faq(BaseModel):
    id: int | None = None
    pergunta: Formulacao
    variacoes: list[Formulacao] = []
    resposta: Resposta
    tema: Tema
    palavras_chave: list[str] = []
    visibilidade: Visibilidade = Visibilidade.PUBLICA
    situacao: Situacao = Situacao.RASCUNHO
    autor_id: int | None = None
    relacionadas: list[int] = []
    telas: list[str] = []                 # NOVO: `nome_rota` das telas em que a FAQ aparece
```

**Mock:** [006-mock-widget-faq-da-tela.html](006-mock-widget-faq-da-tela.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Busca dentro do painel do widget — faq/007.
- Ajuda por estado de tela (gaveta aberta, desenho selecionado) em vez de por rota — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/autenticacao/context_processors.py` → padrão de context processor do projeto.
- `@services/domain/faq/indice.py` → `MontarIndice` (faq/001): o accordion do painel é o mesmo índice.
- `@templates/faq/` → o partial do item do accordion (faq/001 e faq/004), reaproveitado no painel
  mantendo imagens e players de vídeo restritos à largura da caixa.
- `@apps/painel/checks.py` → padrão de system check do projeto.
- Skills: `componentes-frontend`, `daisyui`, `htmx-skill`, `mock`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

> O comentário didático destes blocos existe só aqui e **não é portado** (CLAUDE.md §7.2).

**`apps/faq/telas.py`** — o decorator **declara** a tela. Ele não mexe no contexto: só marca a view e
inscreve a tela num registro em memória, montado na importação das urls.

```python
_REGISTRO: dict[Callable[..., HttpResponse], str] = {}


def tela_com_ajuda(rotulo: str) -> Callable[[ViewFunc], ViewFunc]:
    def _marcar(view: ViewFunc) -> ViewFunc:
        _REGISTRO[view] = rotulo
        return view
    return _marcar


def telas_declaradas() -> list[Tela]:
    # Varre o resolver uma vez e cruza com as views marcadas: o nome da rota vem do urls.py, não do
    # decorator, então renomear a rota não deixa o registro desatualizado.
    return sorted(
        (Tela(nome_rota=nome, rotulo=_REGISTRO[view]) for nome, view in _rotas_nomeadas() if view in _REGISTRO),
        key=lambda t: t.rotulo,
    )
```

```python
# apps/search/views.py (exemplo de uso)
@tela_com_ajuda("Mapa e busca")
def pagina_busca(request: HttpRequest) -> HttpResponse: ...
```

**`apps/faq/context_processors.py`** — o context processor é o gancho do Django que roda em todo
`render()`. É preguiçoso: só consulta o banco se o template **ler** a variável, e só o `base.html` lê.

```python
def faq_da_tela(request: HttpRequest) -> dict[str, Any]:
    match = request.resolver_match
    if match is None or request.headers.get("HX-Request"):
        return {}
    leitor = Leitor(autenticado=request.user.is_authenticated)
    return {"faq_da_tela": SimpleLazyObject(lambda: _indice_da_tela(match.view_name, leitor))}


def _indice_da_tela(nome_rota: str, leitor: Leitor) -> IndiceFaq:
    faqs = carregar_faqs(visibilidades_para(leitor), tela=nome_rota)     # consulta.py, filtro por vínculo
    return montar_indice(MontagemIndiceInput(faqs=faqs, leitor=leitor))
```

```django
{# templates/base.html #}
{% if faq_da_tela.secoes %}
  {% include "faq/_widget.html" with indice=faq_da_tela %}
{% endif %}
```

**`apps/faq/models.py`**

```python
class VinculoTela(models.Model):
    faq = models.ForeignKey(Faq, on_delete=models.CASCADE, related_name="telas")
    nome_rota = models.CharField(max_length=120, db_index=True)

    class Meta:
        constraints = [models.UniqueConstraint("faq", "nome_rota", name="faq_tela_unica_por_faq")]
```

**`services/domain/faq/telas.py`** — a validação do vínculo é pura: recebe o catálogo pronto.

```python
def conferir_telas(pedidas: list[str], declaradas: list[Tela]) -> None:
    conhecidas = {t.nome_rota for t in declaradas}
    desconhecidas = [r for r in pedidas if r not in conhecidas]
    if desconhecidas:
        raise ValueError(f"Telas sem ajuda declarada: {', '.join(desconhecidas)}.")
```

O formulário de faq/002 ganha o multi-select de telas, alimentado por `telas_declaradas()`. A
regravação passa por `conferir_telas` antes de gravar.

**`apps/faq/checks.py`** — `faq.W001`: vínculo com `nome_rota` fora de `telas_declaradas()`. É aviso e
não erro: a subida não cai por causa de uma FAQ.

**Rotas** (abertas, decididas pela visibilidade): `faq:widget_tela` devolve o partial das FAQs de uma
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

**O vínculo guarda o nome da rota como texto, sem FK.** Rota é código, não linha de banco, e o
`manage.py check` é o que pega a divergência. Entre um deploy que remove a rota e a correção do
vínculo, a FAQ fica ligada a uma tela que não existe, sem efeito visível.

## 8 · Testes (TDD)
- `test_so_views_marcadas_viram_tela` — `telas_declaradas()` traz a view marcada com o nome da rota do
  `urls.py` e não traz uma view não marcada.
- `test_vincular_tela_nao_declarada_eh_recusado` — o formulário volta com erro em português no campo de
  telas, e nada é gravado. *(marker `banco`)*
- `test_widget_aparece_so_com_faq_visivel` — parametrizado: tela com FAQ pública mostra o botão; tela
  sem vínculo, ou só com rascunho, não mostra. *(marker `banco`)*
- `test_widget_esconde_interna_do_anonimo` — mesma tela com FAQ interna: o logado vê o botão, o anônimo
  não. *(marker `banco`)*
- `test_partial_htmx_nao_consulta_faq` — uma view de partial chamada com `HX-Request` não faz nenhuma
  consulta à tabela de vínculos (`django_assert_num_queries`). *(marker `banco`)*
- `test_ver_todas_e_voltar` — `faq:widget_todas` devolve o índice completo, e `faq:widget_tela` volta
  ao filtrado. *(marker `banco`)*
- `test_check_aponta_vinculo_orfao` — vínculo com rota inexistente gera `faq.W001`, e o widget o
  ignora. *(marker `banco`)*
