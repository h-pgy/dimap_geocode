---
spec: faq/001
versao: v5
atualizado_em: 2026-11-17
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: imagens em markdown e vídeos (MP4 do sistema e YouTube) abaixo da resposta
  - v3: legenda e descrição como metadados de MidiaFaq
  - v4: modelo próprio para Resposta e renomeia autores_ids para usuarios_upload_ids
  - v5: separa imagens e vídeos para faq/004, mantendo aqui apenas texto markdown, links e seed
---

# SPEC faq/001 — Página de FAQ

## 1 · User story
Um servidor da DIMAP, ou um cidadão sem login, consulta a página de FAQ no contexto de uma dúvida sobre
o uso do sistema e encontra, sem pedir ajuda a ninguém, a pergunta já respondida, organizada por tema.

## 2 · Condições de pronto
- [ ] O design da página foi aprovado no mock e as peças foram portadas para o tema e o styleguide
      antes de o template da aplicação usá-las.
- [ ] `/faq/` lista as FAQs publicadas agrupadas por tema e, dentro do tema, por subtema. Clicar numa
      pergunta abre a resposta logo abaixo, em accordion.
- [ ] Sem login, a página mostra só as FAQs **públicas**. Com login, mostra também as **internas**.
      FAQ em **rascunho** não aparece para ninguém.
- [ ] A resposta escrita em markdown aparece formatada (negrito, listas, links e tabelas). HTML ou
      `<script>` embutido no texto não é executado.
- [ ] A resposta aberta mostra os links de referência e as FAQs relacionadas. Uma relacionada que o
      leitor não pode ver não aparece, nem como link.
- [ ] Duas FAQs não podem ter a mesma pergunta, mesmo com acento, caixa ou pontuação diferentes
      (`Como emito a certidão?` × `como emito a certidao`). Uma variação também não pode repetir a
      pergunta ou a variação de outra FAQ.
- [ ] Subtema não tem subtema: tentar pendurar um tema num subtema é recusado.
- [ ] `seed_faq` carrega os temas e as FAQs básicas de `data/seed/faq.json` e, rodado de novo, não
      duplica nem altera nada.
- [ ] Sem nenhuma FAQ visível ao leitor, a página mostra o estado vazio, não uma lista em branco.

## 3 · Domínio

A FAQ é uma resposta a uma pergunta, que pode ser feita de várias formas. A pergunta principal e as
variações são todas **formulações**, e cada formulação pertence a uma única FAQ no sistema inteiro.

```python
class Tema(BaseModel):
    """Assunto que agrupa FAQs. Com `pai`, é subtema. São no máximo dois níveis."""
    nome: str = Field(min_length=2, max_length=80)
    pai: "Tema | None" = None        # None = tema raiz
    ordem: int = 0                   # posição entre os irmãos na página

    @model_validator(mode="after")
    def _dois_niveis(self) -> Self:
        if self.pai is not None and self.pai.pai is not None:
            raise ValueError("Subtema não pode ter subtema.")
        return self


class Visibilidade(StrEnum):
    PUBLICA = "publica"              # qualquer um, com ou sem login
    INTERNA = "interna"              # só servidor autenticado


class Situacao(StrEnum):
    RASCUNHO = "rascunho"
    PUBLICADA = "publicada"


class Formulacao(BaseModel):
    """Uma forma de fazer a pergunta. A identidade é a `chave`, não o texto."""
    texto: str = Field(min_length=5, max_length=300)

    @computed_field
    @property
    def chave(self) -> str:
        return normalize_text(self.texto)


class LinkReferencia(BaseModel):
    """Link citado pela resposta: externo (https://...) ou tela do sistema (/caminho)."""
    titulo: str = Field(min_length=2, max_length=120)
    url: str = Field(pattern=r"^(https?://|/)")


class Resposta(BaseModel):
    """Conteúdo que responde às formulações: texto markdown e links de referência."""
    markdown: str = Field(min_length=1)
    links: list[LinkReferencia] = []

    @field_validator("markdown", mode="before")
    @classmethod
    def _nao_vazia(cls, valor: str) -> str:
        if not valor or not valor.strip():
            raise ValueError("A resposta não pode ficar em branco.")
        return valor


class Faq(BaseModel):
    id: int | None = None                         # None = ainda não persistida
    pergunta: Formulacao                          # a principal, exibida na lista
    variacoes: list[Formulacao] = []              # outras formas da mesma pergunta
    resposta: Resposta
    tema: Tema                                    # tema raiz ou subtema
    palavras_chave: list[str] = []                # siglas e termos ausentes do texto
    visibilidade: Visibilidade = Visibilidade.PUBLICA
    situacao: Situacao = Situacao.RASCUNHO
    autor_id: int | None = None                   # None = FAQ do sistema (carga da seed)
    relacionadas: list[int] = []                  # ids de outras FAQs

    @model_validator(mode="after")
    def _formulacoes_distintas(self) -> Self:
        chaves = [self.pergunta.chave, *(v.chave for v in self.variacoes)]
        if len(chaves) != len(set(chaves)):
            raise ValueError("A mesma formulação aparece duas vezes nesta FAQ.")
        if self.id is not None and self.id in self.relacionadas:
            raise ValueError("Uma FAQ não se relaciona consigo mesma.")
        return self


class Leitor(BaseModel):
    """Quem está lendo a página. O que importa é só se está autenticado."""
    autenticado: bool
```

**Mock:** [001-mock-pagina-de-faq.html](001-mock-pagina-de-faq.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Criar, editar, publicar e despublicar FAQ pela interface do administrador — faq/002.
- Anexos documentais (PDF/DOCX) com texto extraído, ligados às respostas — faq/003.
- Imagens embutidas no markdown e vídeos MP4 (inclusive importados do YouTube) na resposta — faq/004.
- Índice semântico, embeddings e pgvector — faq/005.
- Telas do sistema vinculadas por nome de rota e o widget flutuante filtrado — faq/006.
- Busca em texto livre na FAQ e o painel das buscas mais feitas — faq/007.

## 5 · Peças de referência a compor
- `@services/utils/normalization` → `normalize_text`: a chave da formulação.
- `@apps/user_admin/models` → `Perfil`: o autor da FAQ.
- `@middleware de validação Pydantic` (SPEC infraestrutura/001): `ValidationError` na fronteira, sem `try/except`.
- Skills: `ontologia`, `seeds`, `management-commands`, `componentes-frontend`, `daisyui`, `mock`,
  `escrever-testes`, `test-django-views`, `normalize-text`.

## 6 · Snippets

> O comentário didático destes blocos existe só aqui e **não é portado** (CLAUDE.md §7.2).

**`apps/faq/models.py`** — só persistência. As unicidades da regra de negócio são constraints.

```python
class Tema(models.Model):
    nome = models.CharField(max_length=80)
    pai = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="subtemas")
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            # Nome único entre irmãos. A raiz precisa de condição própria: NULL ≠ NULL no Postgres.
            models.UniqueConstraint(Lower("nome"), "pai", name="faq_tema_nome_unico_no_pai"),
            models.UniqueConstraint(Lower("nome"), condition=Q(pai__isnull=True), name="faq_tema_nome_unico_na_raiz"),
        ]

    def clean(self) -> None:
        # Dois níveis: o banco não consegue dizer isso sem trigger (Caveats).
        if self.pai_id is not None and self.pai.pai_id is not None:
            raise ValidationError({"pai": "Subtema não pode ter subtema."})


class Faq(models.Model):
    resposta_markdown = models.TextField()
    tema = models.ForeignKey(Tema, on_delete=models.PROTECT, related_name="faqs")
    palavras_chave = ArrayField(models.CharField(max_length=60), default=list, blank=True)
    visibilidade = models.CharField(max_length=10, choices=Visibilidade.choices, default=Visibilidade.PUBLICA)
    situacao = models.CharField(max_length=10, choices=Situacao.choices, default=Situacao.RASCUNHO)
    autor = models.ForeignKey("user_admin.Perfil", on_delete=models.PROTECT, null=True, blank=True)
    relacionadas = models.ManyToManyField("self", symmetrical=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)


class Formulacao(models.Model):
    faq = models.ForeignKey(Faq, on_delete=models.CASCADE, related_name="formulacoes")
    texto = models.CharField(max_length=300)
    # Guardada só para o UNIQUE: `normalize_text` não tem equivalente em SQL (Caveats).
    chave = models.CharField(max_length=300, unique=True)
    eh_principal = models.BooleanField(default=False)

    class Meta:
        constraints = [
            # No máximo uma principal por FAQ. O "ao menos uma" é garantido por `gravar_faq` (Caveats).
            models.UniqueConstraint("faq", condition=Q(eh_principal=True), name="faq_uma_formulacao_principal"),
        ]


class LinkReferencia(models.Model):
    faq = models.ForeignKey(Faq, on_delete=models.CASCADE, related_name="links")
    titulo = models.CharField(max_length=120)
    url = models.CharField(max_length=500)
    ordem = models.PositiveSmallIntegerField(default=0)
```

**`apps/faq/cadastro.py`** — a única porta de escrita. A seed usa esta função, e faq/002 vai usar a
mesma.

```python
@transaction.atomic
def gravar_faq(faq: Faq) -> int:
    # O DTO já validou forma e formulações repetidas DENTRO da FAQ. A repetição ENTRE FAQs é o
    # UNIQUE de `Formulacao.chave` que barra, com IntegrityError, na mesma transação.
    registro = FaqModel.objects.create(
        resposta_markdown=faq.resposta.markdown,
        tema=_tema_persistido(faq.tema),
        palavras_chave=faq.palavras_chave,
        visibilidade=faq.visibilidade,
        situacao=faq.situacao,
        autor_id=faq.autor_id,
    )
    FormulacaoModel.objects.create(faq=registro, texto=faq.pergunta.texto, chave=faq.pergunta.chave, eh_principal=True)
    FormulacaoModel.objects.bulk_create(
        FormulacaoModel(faq=registro, texto=v.texto, chave=v.chave) for v in faq.variacoes
    )
    LinkReferenciaModel.objects.bulk_create(
        LinkReferenciaModel(faq=registro, titulo=l.titulo, url=l.url, ordem=i)
        for i, l in enumerate(faq.resposta.links)
    )
    registro.relacionadas.set(faq.relacionadas)
    return registro.pk
```

**`services/domain/faq/visibilidade.py`** — a regra de quem vê o quê. A query do app usa essa regra
para filtrar no banco, e o índice reaplica a mesma regra sobre o que recebe.

```python
def visibilidades_para(leitor: Leitor) -> frozenset[Visibilidade]:
    if leitor.autenticado:
        return frozenset({Visibilidade.PUBLICA, Visibilidade.INTERNA})
    return frozenset({Visibilidade.PUBLICA})


def eh_visivel(faq: Faq, leitor: Leitor) -> bool:
    # Rascunho não é "interno": não aparece para ninguém na página.
    return faq.situacao is Situacao.PUBLICADA and faq.visibilidade in visibilidades_para(leitor)
```

**`services/domain/faq/indice.py`** — monta a árvore tema → subtema → FAQs da página.

```python
class MontagemIndiceInput(BaseModel):
    faqs: list[Faq]
    leitor: Leitor


class ItemIndice(BaseModel):
    faq: Faq
    relacionadas: list[Faq]                # já podadas para o que o leitor vê


class SecaoSubtema(BaseModel):
    subtema: Tema
    itens: list[ItemIndice]


class SecaoTema(BaseModel):
    tema: Tema
    itens: list[ItemIndice]                # FAQs penduradas direto no tema raiz
    subtemas: list[SecaoSubtema]


class IndiceFaq(BaseModel):
    secoes: list[SecaoTema]                # vazia = estado vazio da página


class MontarIndice:
    def __call__(self, entrada: MontagemIndiceInput) -> IndiceFaq:
        return self.pipeline(entrada)

    def pipeline(self, entrada: MontagemIndiceInput) -> IndiceFaq:
        visiveis = self._visiveis(entrada)
        por_id = {f.id: f for f in visiveis}
        itens = [self._item(f, por_id) for f in visiveis]
        return IndiceFaq(secoes=self._agrupar(itens))

    def _visiveis(self, entrada: MontagemIndiceInput) -> list[Faq]:
        # Defesa em profundidade: o índice não confia que a query já filtrou.
        return [f for f in entrada.faqs if eh_visivel(f, entrada.leitor)]

    def _item(self, faq: Faq, por_id: dict[int | None, Faq]) -> ItemIndice:
        # Relacionada fora de `por_id` é rascunho ou interna para este leitor: some sem deixar rastro.
        relacionadas = [por_id[i] for i in faq.relacionadas if i in por_id]
        return ItemIndice(faq=faq, relacionadas=relacionadas)

    def _agrupar(self, itens: list[ItemIndice]) -> list[SecaoTema]:
        # Temas por (ordem, nome). Dentro da seção, FAQs pela ordem alfabética da pergunta.
        # Tema ou subtema sem FAQ visível não gera seção.
        ...
```

**`services/utils/markdown/renderizador.py`** — markdown → HTML seguro. É utilitário geral: faq/002
usa o mesmo renderizador na pré-visualização do editor, e faq/004 abre a tag `<img>` nele.

```python
TAGS_PERMITIDAS = frozenset({
    "p", "br", "strong", "em", "code", "pre", "blockquote",
    "ul", "ol", "li", "a", "h3", "h4", "table", "thead", "tbody", "tr", "th", "td",
})
ESQUEMAS_PERMITIDOS = frozenset({"http", "https", "mailto"})


class RenderizadorMarkdown:
    def __init__(self) -> None:
        # html=False: HTML cru dentro do markdown sai escapado, e não interpretado.
        self._md = MarkdownIt("commonmark", {"html": False}).enable("table")

    def __call__(self, texto: str) -> str:
        return self.pipeline(texto)

    def pipeline(self, texto: str) -> str:
        html = self._md.render(texto)
        # Segunda barreira: mesmo que o parser deixe passar algo, o nh3 corta pela allowlist.
        return nh3.clean(
            html,
            tags=TAGS_PERMITIDAS,
            attributes={"a": {"href", "title"}},
            url_schemes=ESQUEMAS_PERMITIDOS,
            link_rel="noopener noreferrer",
        )
```

**`apps/faq/views.py`** — rota **aberta**, declarada aqui (CLAUDE.md §3.5).

```python
def pagina_faq(request: HttpRequest) -> HttpResponse:
    leitor = Leitor(autenticado=request.user.is_authenticated)
    faqs = carregar_faqs(visibilidades_para(leitor))      # apps/faq/consulta.py: queryset → list[Faq]
    indice = montar_indice(MontagemIndiceInput(faqs=faqs, leitor=leitor))
    return render(request, "faq/pagina.html", {"indice": indice})
```

O template renderiza a resposta pelo filtro `{{ item.faq.resposta.markdown|markdown }}`
(`apps/faq/templatetags/faq_markdown.py`), que chama o `RenderizadorMarkdown` e marca a saída como
segura.

**`data/seed/faq.json`** — chave natural do tema: `(nome, pai)`. Chave natural da FAQ: a `chave` da
pergunta. As FAQs da seed nascem `publicada`, com `autor_id = None`.

```json
{
  "temas": [
    {"nome": "Busca", "ordem": 1},
    {"nome": "Endereço", "pai": "Busca", "ordem": 1},
    {"nome": "Lote", "pai": "Busca", "ordem": 2},
    {"nome": "Logradouro", "pai": "Busca", "ordem": 3},
    {"nome": "Mapa", "ordem": 2},
    {"nome": "Documentos emitidos", "ordem": 3},
    {"nome": "Acesso", "ordem": 4}
  ],
  "faqs": [
    {
      "tema": ["Busca", "Endereço"],
      "pergunta": "Como busco um endereço?",
      "variacoes": ["Onde digito o endereço para localizar no mapa?"],
      "palavras_chave": ["endereço", "número", "geocodificação"],
      "visibilidade": "publica",
      "resposta": "Digite o logradouro e o número na **barra de busca**...",
      "links": [],
      "relacionadas": ["O que é o codlog e como busco por ele?"]
    }
  ]
}
```

Perguntas iniciais da seed (o texto das respostas é revisado por você na implementação):

| Tema / subtema | Pergunta |
|---|---|
| Busca / Endereço | Como busco um endereço? |
| Busca / Lote | Como encontro um lote pelo número do contribuinte (SQL)? |
| Busca / Logradouro | O que é o codlog e como busco por ele? |
| Mapa | Como desenho um ponto, uma linha ou um polígono no mapa? |
| Documentos emitidos | Como confiro a autenticidade de um documento emitido pelo sistema? |
| Acesso | Como consigo acesso ao sistema? |
| Acesso | Esqueci minha senha. O que faço? |

**`apps/faq/seeds/faq.py`** — segue a skill `seeds`. Há duas passadas: temas raiz e depois subtemas;
FAQs e depois relacionadas, ligadas por pergunta e **só entre as FAQs criadas nesta carga**. Tudo roda
num único `transaction.atomic()`, e cada FAQ é gravada por `gravar_faq`.

## 7 · Caveats

**A chave normalizada da formulação é guardada, embora seja derivada.** `normalize_text` não tem
equivalente em SQL, e o UNIQUE que impede duas FAQs com a mesma pergunta só existe sobre uma coluna.
Se a regra de normalização mudar, as chaves gravadas ficam desatualizadas até uma regravação em massa,
que não existe hoje.

**"Toda FAQ tem uma formulação principal" vale no banco só pela metade.** A constraint garante no
máximo uma, e o "ao menos uma" depende de toda escrita passar por `gravar_faq`, numa transação só.
Uma escrita feita direto no ORM pode deixar uma FAQ sem pergunta.

**Os dois níveis de tema ficam fora do banco.** A regra vive no `clean()` e no DTO, e expressar
profundidade em constraint pediria trigger. Um `Tema.objects.create` direto, sem `full_clean()`,
consegue criar um terceiro nível.

**A rota `/faq/` é aberta, contra o padrão "rota protegida" do CLAUDE.md §3.5.** A FAQ é informação
sobre o uso do sistema, não ato administrativo, e a FAQ pública existe justamente para quem não tem
login. A proteção do conteúdo interno passa a depender só da regra de visibilidade, nas duas camadas
(query e índice).

**Duas dependências novas: `markdown-it-py` e `nh3`.** Renderizar markdown a partir do texto de um
administrador exige um parser e um sanitizador mantidos; escrever os dois à mão seria pior. O HTML
chega ao template marcado como seguro, e a allowlist do `nh3` passa a ser a barreira contra XSS.

**A página renderiza o markdown de todas as FAQs a cada request.** O volume esperado é de dezenas a
poucas centenas de FAQs, então o custo é desprezível. Se crescer, o HTML renderizado passa a ser cache
por FAQ, invalidado na gravação.

**As FAQs da seed não têm autor.** Elas são bootstrap do sistema, e nenhum superusuário existe com
certeza no momento da carga. A regra "o admin edita só as que criou", de faq/002, precisa dizer o que
acontece com essas.

## 8 · Testes (TDD)
- `test_formulacao_repetida_entre_faqs_eh_recusada` — parametrizado: pergunta repetida com outra
  grafia e variação igual à pergunta de outra FAQ levantam `IntegrityError`, sem gravar a segunda
  FAQ. *(marker `banco`)*
- `test_subtema_nao_aceita_filho` — `full_clean()` de um tema cujo pai é subtema levanta
  `ValidationError` em `pai`. *(marker `banco`)*
- `test_visibilidade_da_pagina_por_leitor` — parametrizado: anônimo vê só pública publicada, logado vê
  pública e interna publicadas, e rascunho não aparece em nenhum dos dois casos (GET `/faq/`).
  *(marker `banco`)*
- `test_indice_agrupa_por_tema_e_subtema_em_ordem` — temas e subtemas saem por `(ordem, nome)`, as
  FAQs em ordem alfabética, e tema sem FAQ visível não gera seção.
- `test_relacionada_invisivel_nao_vaza` — uma pública relacionada a uma interna não lista a interna
  para o leitor anônimo.
- `test_markdown_nao_executa_html_embutido` — `<script>`, `onclick` e `javascript:` no texto não
  sobrevivem à renderização, e `**negrito**`, listas e tabelas sobrevivem.
- `test_seed_faq_cria_e_nao_toca_o_que_existe` — carrega hierarquia de temas, formulações, links e
  relacionadas; recarregar com o JSON alterado não duplica nem reescreve. *(marker `banco`)*
- `test_seed_faq_invalida_aborta_sem_gravar` — um subtema de subtema no JSON aborta a carga, e nenhum
  tema nem FAQ persiste; `dry_run=True` também não persiste nada (parametrizado). *(marker `banco`)*
