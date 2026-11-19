---
spec: faq/001
versao: v14
atualizado_em: 2026-11-19
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: imagens em markdown e vídeos (MP4 do sistema e YouTube) abaixo da resposta
  - v3: legenda e descrição como metadados de MidiaFaq
  - v4: modelo próprio para Resposta e renomeia autores_ids para usuarios_upload_ids
  - v5: separa imagens e vídeos para faq/004, mantendo aqui apenas texto markdown, links e seed
  - v6: vídeos saem do épico, e faq/004 fica só com imagens
  - v7: a seed reconhece a FAQ por um id próprio e respeita a edição e a exclusão do administrador
  - v8: o renderizador cobre tudo o que o editor de faq/002 produz
  - v9: a seed sai para faq/008, no fim do épico
  - v10: Formulacao vira Pergunta, o link se resolve em interno ou externo, a pergunta ocupada vira erro de domínio e o leitor carrega o RF
  - v11: palavra-chave vira entidade própria, em árvore de até três níveis e com relacionadas, ligada à FAQ por muitos-para-muitos
  - v12: o link de referência para o próprio sistema deixa de se chamar interno e se distingue da rota vinculada de faq/006
  - v13: estrutura de pacotes do épico, criada já nesta SPEC, com a persistência num lugar só e os modelos de entrada e saída por submódulo de domínio
  - v14: a FAQ do sistema vira atributo calculado da FAQ, e o portão de superusuário sai da árvore do épico para apps/core
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
- [ ] A resposta escrita em markdown aparece formatada (negrito, riscado, listas, listas de tarefas,
      links, tabelas e títulos). Título de qualquer nível aparece abaixo do título da página. HTML ou
      `<script>` embutido no texto não é executado.
- [ ] A resposta aberta mostra os links de referência e as FAQs relacionadas. Uma relacionada que o
      leitor não pode ver não aparece, nem como link.
- [ ] Um link de referência com o endereço completo de uma página do sistema é gravado como link
      **do sistema**, só com o caminho, e continua funcionando em outro ambiente. Na resposta, o do
      sistema abre na mesma aba e o externo em aba nova. `//site.com`, `javascript:` e endereço sem
      host são recusados.
- [ ] Duas FAQs não podem ter a mesma pergunta, mesmo com acento, caixa ou pontuação diferentes
      (`Como emito a certidão?` × `como emito a certidao`). Uma variação também não pode repetir a
      pergunta ou a variação de outra FAQ. A recusa diz qual FAQ já tem a pergunta.
- [ ] Subtema não tem subtema, e palavra-chave não passa do terceiro nível: pendurar um tema num
      subtema, ou uma palavra-chave numa de terceiro nível, é recusado.
- [ ] Uma palavra-chave pode nascer já relacionada a palavras de outros ramos, e a relação vale nos dois
      sentidos: criar `Imposto predial` relacionada a `IPTU` faz `IPTU` listar `Imposto predial`.
- [ ] Sem nenhuma FAQ visível ao leitor, a página mostra o estado vazio, não uma lista em branco.

## 3 · Domínio

A FAQ é uma resposta a uma pergunta, que pode ser feita de várias formas. A pergunta principal e as
variações são todas `Pergunta`, e **cada pergunta pertence a uma única FAQ no sistema inteiro**. Essa
unicidade é propriedade do conjunto de todas as perguntas: o `Faq` garante só a distinção dentro de si,
e a garantia entre FAQs é do banco (§6).

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


PROFUNDIDADE_PALAVRA_CHAVE = 3


class PalavraChave(BaseModel):
    """Termo de busca ausente do texto da FAQ (sigla, jargão). Com `pai`, especializa o termo acima."""
    id: int | None = None                # None = ainda não persistida
    nome: str = Field(min_length=2, max_length=60)
    pai: "PalavraChave | None" = None    # None = raiz
    relacionadas: list[int] = []         # ids de palavras de qualquer ramo, fora da hierarquia

    @computed_field
    @property
    def caminho(self) -> list[str]:
        # Da raiz até ela: ["IPTU", "Certidão", "Lançamento"].
        return [*(self.pai.caminho if self.pai is not None else []), self.nome]

    @model_validator(mode="after")
    def _tres_niveis(self) -> Self:
        if len(self.caminho) > PROFUNDIDADE_PALAVRA_CHAVE:
            raise ValueError("Palavra-chave tem no máximo três níveis.")
        if self.id is not None and self.id in self.relacionadas:
            raise ValueError("Uma palavra-chave não se relaciona consigo mesma.")
        return self


class Visibilidade(StrEnum):
    PUBLICA = "publica"              # qualquer um, com ou sem login
    INTERNA = "interna"              # só servidor autenticado


class Situacao(StrEnum):
    RASCUNHO = "rascunho"
    PUBLICADA = "publicada"


class Pergunta(BaseModel):
    """Uma forma de fazer a pergunta. A identidade é a `chave`, não o texto."""
    texto: str = Field(min_length=5, max_length=300)

    @computed_field
    @property
    def chave(self) -> str:
        return normalize_text(self.texto)


class LinkDoSistema(BaseModel):
    """Endereço do próprio sistema citado na resposta. Guarda só o caminho, que sobrevive à troca de ambiente."""
    tipo: Literal["sistema"] = "sistema"
    caminho: str = Field(pattern=r"^/(?!/)", max_length=500)     # "/x", nunca "//x"

    @property
    def href(self) -> str:
        return self.caminho


class LinkExterno(BaseModel):
    tipo: Literal["externo"] = "externo"
    url: Annotated[HttpUrl, UrlConstraints(max_length=500)]      # recusa javascript:, ftp:, host vazio

    @property
    def href(self) -> str:
        return str(self.url)


class LinkReferencia(BaseModel):
    """Link citado pela resposta, para o leitor seguir. Do sistema ou externo é decidido pela resolução (§6)."""
    titulo: str = Field(min_length=2, max_length=120)
    destino: Annotated[LinkDoSistema | LinkExterno, Field(discriminator="tipo")]


class Resposta(BaseModel):
    """Conteúdo que responde às perguntas: texto markdown e links de referência."""
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
    pergunta: Pergunta                            # a principal, exibida na lista
    variacoes: list[Pergunta] = []                # outras formas da mesma pergunta
    resposta: Resposta
    tema: Tema                                    # tema raiz ou subtema
    palavras_chave: list[PalavraChave] = []       # de qualquer nível; os ancestrais vêm pelo `caminho`
    visibilidade: Visibilidade = Visibilidade.PUBLICA
    situacao: Situacao = Situacao.RASCUNHO
    autor_id: int | None = None                   # None = FAQ do sistema, sem autor (seed de faq/008)
    relacionadas: list[int] = []                  # ids de outras FAQs

    @computed_field
    @property
    def eh_do_sistema(self) -> bool:
        return self.autor_id is None

    @model_validator(mode="after")
    def _perguntas_distintas(self) -> Self:
        chaves = [self.pergunta.chave, *(v.chave for v in self.variacoes)]
        if len(chaves) != len(set(chaves)):
            raise ValueError("A mesma pergunta aparece duas vezes nesta FAQ.")
        if self.id is not None and self.id in self.relacionadas:
            raise ValueError("Uma FAQ não se relaciona consigo mesma.")
        return self


class Leitor(BaseModel):
    """Quem lê a FAQ: servidor logado, identificado pelo RF, ou visitante sem login."""
    rf: str | None = Field(default=None, min_length=1)          # None = sem login

    @computed_field
    @property
    def eh_interno(self) -> bool:
        return self.rf is not None
```

Uma FAQ marcada com uma palavra-chave responde também pelos ancestrais dela: marcar
`IPTU › Certidão › Lançamento` basta para a FAQ ser achada por `IPTU`. O nome da palavra-chave é único
entre as irmãs, não no sistema: `Certidão` pode existir sob `IPTU` e sob `ITBI`. As relacionadas ligam
palavras de ramos diferentes, fora da hierarquia, e a ligação vale nos dois sentidos.

O link de referência é conteúdo da resposta: o leitor o segue, e ele pode apontar para fora ou para uma
página do sistema. Ele não diz em que tela a FAQ aparece — isso é a **rota vinculada** de
[faq/006](006-faq-da-tela.md#3--domínio), que nunca é exibida na resposta.

**Mock:** [001-mock-pagina-de-faq.html](001-mock-pagina-de-faq.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Criar, editar, publicar e despublicar FAQ pela interface do administrador — faq/002.
- Anexos documentais (PDF/DOCX) com texto extraído, ligados às respostas — faq/003.
- Imagens embutidas no markdown — faq/004.
- Vídeos na resposta (MP4 enviado ou importado do YouTube) — sem dono ainda.
- Índice semântico, embeddings e pgvector — faq/005.
- Cadastro e renomeação de palavras-chave, e a escolha delas na árvore horizontal do formulário — faq/002.
- Palavra-chave no índice semântico e no fallback textual da busca, com os ancestrais — faq/005 e faq/007.
- Controle das palavras relacionadas no formulário de faq/002, e o uso delas na busca (sinônimo,
  "veja também") — sem dono ainda.
- Rotas vinculadas (as telas em que a FAQ é oferecida pelo widget de ajuda) e o widget filtrado por elas — faq/006.
- Busca em texto livre na FAQ, o registro de quem buscou o quê (pelo RF do leitor) e o painel das
  buscas mais feitas — faq/007.
- Carga inicial de temas e FAQs (seed) — faq/008.

## 5 · Peças de referência a compor
- `@services/utils/normalization` → `normalize_text`: a chave da pergunta.
- `@apps/user_admin/models` → `Perfil`: o autor da FAQ e o `rf` do leitor.
- `@middleware de validação Pydantic` (SPEC infraestrutura/001): `ValidationError` na fronteira, sem `try/except`.
- Skills: `ontologia`, `componentes-frontend`, `daisyui`, `mock`, `escrever-testes`,
  `test-django-views`, `normalize-text`.

## 6 · Snippets

> O comentário didático destes blocos existe só aqui e **não é portado** (CLAUDE.md §7.2).

**Estrutura do épico** — esta SPEC cria os pacotes já neste formato, com os módulos que ela usa
(marcados com ●). As SPECs seguintes acrescentam os outros nas pastas previstas. Nenhuma SPEC do
épico cria módulo fora desta árvore: o que não couber nela muda esta seção antes.

- **Persistência num lugar só.** Todo `models.Model` do épico mora em `apps/faq/models/`, num arquivo
  com o nome do submódulo de domínio a que pertence, com uma pasta de migrações só.
- **Entrada e saída por submódulo.** Cada submódulo de `services/domain/faq/` tem a pasta `models/`
  com os modelos Pydantic dele (a ontologia do §3 de cada SPEC e os DTOs das operações). As regras
  ficam ao lado, em módulos próprios.
- **Caso de uso por pasta.** Cada pasta de `apps/faq/` com rota tem `urls.py` e `views.py` próprios.
  `apps/faq/urls.py` só concatena os `urlpatterns`, sob um `app_name = "faq"` único. A pasta do app e o
  submódulo de domínio se relacionam N:N (CLAUDE.md §5).
- Todo `__init__.py` só reexporta.

```
apps/faq/
├── apps.py                    ●
├── urls.py                    ●  concatena os urlpatterns das pastas
├── leitor.py                  ●  leitor_de                                          001
├── models/                    ●
│   ├── conteudo.py            ●  Faq, Pergunta, LinkReferencia                      001 · 002 · 003 · 004 · 008
│   ├── taxonomia.py           ●  Tema, PalavraChave                                 001
│   ├── arquivos.py               Anexo, MidiaFaq                                    003 · 004
│   ├── telas.py                  RotaVinculada                                      006
│   ├── indexacao.py              TrechoIndexado                                     005
│   └── busca.py                  FraseBuscada, RegistroBusca                        007
├── migrations/                ●
├── conteudo/                  ●  sem rota
│   ├── cadastro.py            ●  gravar_faq, conferir_perguntas_livres              001 · 003 · 004 · 006
│   └── consulta.py            ●  carregar_faqs                                      001 · 006
├── taxonomia/                 ●
│   ├── cadastro.py            ●  gravar_palavra_chave; temas (002)                  001 · 002
│   ├── palavras_chave.py         coluna_de_palavras_chave                           002
│   ├── urls.py · views.py        temas e palavras-chave do administrador            002
├── pagina/                    ●
│   ├── urls.py · views.py     ●  faq:pagina                                         001
├── gestao/
│   ├── urls.py · views.py        faq:admin_lista … faq:admin_restaurar              002
│   ├── cadastro.py               regravar_faq, excluir_faq, restaurar_faq           002 · 003 · 004 · 006
│   ├── consulta.py               faq_editavel, faqs_editaveis                       002
│   ├── formularios.py            campos_ocupados, link_do_formulario                002
│   └── context.py                relacionadas_do_formulario                         002
├── anexos/
│   ├── urls.py · views.py        faq:anexo_baixar, faq:admin_anexo_*                003
│   └── recebimento.py            receber_anexo                                      003
├── midias/
│   ├── urls.py · views.py        faq:midia_exibir, faq:admin_midia_enviar           004
│   └── recebimento.py            receber_midia                                      004
├── telas/
│   ├── urls.py · views.py        faq:widget_tela, faq:widget_todas                  006
│   ├── declaracao.py             tela_com_ajuda, telas_declaradas                   006
│   ├── context_processors.py     faq_da_tela                                        006
│   └── checks.py                 faq.W001                                           006
├── indexacao/                    sem rota
│   ├── indexador.py              ciclo                                              005 · 007
│   └── semantica.py              buscar_semelhantes                                 005
├── busca/
│   ├── urls.py · views.py        faq:buscar, faq:widget_buscar                      007
│   ├── busca.py                  buscar_na_faq, registrar_busca                     007
│   └── limite.py                 dentro_do_limite                                   007
├── sugestoes/
│   ├── urls.py · views.py        faq:admin_buscas, faq:admin_buscas_corpo           007
│   └── sugestoes.py              sugerir_grupos                                     007
├── seeds/faq.py                                                                     008
├── management/commands/          indexar_faq.py, buscar_faq.py (005) · seed_faq.py (008)
└── templatetags/
    └── faq_markdown.py        ●  filtro `markdown`                                  001

services/domain/faq/
├── conteudo/                  ●
│   ├── models/
│   │   ├── faq.py             ●  Faq, Pergunta, Resposta, Visibilidade, Situacao    001 · 002 · 003 · 004 · 006
│   │   └── links.py           ●  LinkReferencia, LinkDoSistema, LinkExterno         001
│   ├── erros.py               ●  PerguntaOcupada, PerguntaJaRespondida              001
│   └── links.py               ●  resolver_destino, destino_gravado                  001
├── taxonomia/                 ●
│   └── models/
│       ├── tema.py            ●  Tema                                               001
│       └── palavra_chave.py   ●  PalavraChave                                       001
├── leitura/                   ●
│   ├── models/
│   │   ├── leitor.py          ●  Leitor                                             001
│   │   └── indice.py          ●  MontagemIndiceInput, ItemIndice, SecaoTema, …      001
│   ├── visibilidade.py        ●  visibilidades_para, eh_visivel; anexo e imagem     001 · 003 · 004
│   └── indice.py              ●  MontarIndice                                       001
├── edicao/
│   ├── models/edicao.py          Editor, Edicao                                     002
│   └── autoria.py                pode_excluir, pode_usar_midia                     002 · 004
├── arquivos/
│   ├── models/
│   │   ├── anexo.py              Anexo                                              003
│   │   └── midia.py              MidiaFaq                                           004
│   └── midia.py                  validar_imagem, extrair_ids_midia_markdown         004
├── telas/
│   ├── models/tela.py            Tela                                               006
│   └── conferencia.py            conferir_rotas_vinculadas                          006
├── indexacao/
│   ├── models/
│   │   ├── trecho.py             OrigemTrecho, TrechoIndexavel                      005
│   │   ├── embedding.py          ModeloEmbedding                                    005
│   │   ├── semelhanca.py         FaqSemelhante                                      005
│   │   └── reconciliacao.py      PlanoReconciliacao                                 005
│   ├── embedding.py              PROMPT_DOCUMENTO, PROMPT_CONSULTA, GeradorEmbedding 005
│   ├── trechos.py                trechos_da_faq, trecho_da_imagem, trechos_do_anexo 005
│   ├── reconciliacao.py          planejar                                           005
│   └── ranking.py                melhor_por_faq                                     005
└── busca/
    ├── models/
    │   ├── busca.py              ModoBusca, PedidoBuscaFaq, ItemBuscaFaq, ResultadoBuscaFaq  007
    │   ├── registro.py           FraseBuscada, RegistroBusca, RecorteBuscas, ContagemFrase   007
    │   └── agrupamento.py        GrupoBuscas, FraseVetorizada, GrupoComCentroide             007
    ├── busca_textual.py          BuscarTextual                                      007
    ├── registro_busca.py         eh_continuacao                                     007
    └── agrupamento.py            AgruparBuscas                                      007
```

Fora da árvore, no lugar dos outros do mesmo tipo: `services/utils/markdown/` (001), `services/utils/extracao_texto/`
(003), `services/integrations/ollama/` (005) e as linhas de tabela de gestão em
`services/domain/listagem_gestao/models/` (002 e 007). As páginas ficam na raiz de `templates/faq/`
(● `pagina.html`), e os partials em `templates/faq/partials/<pasta do app>/`. Os testes espelham as
duas árvores: `tests/apps/faq/<pasta do app>/` e `tests/services/domain/faq/<submódulo>/`.

**`apps/faq/models/taxonomia.py`** — só persistência. As unicidades da regra de negócio são constraints.

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


class PalavraChave(models.Model):
    nome = models.CharField(max_length=60)
    pai = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="filhas")
    # Simétrica: relacionar A a B já põe A nas relacionadas de B, numa linha só da tabela de junção.
    relacionadas = models.ManyToManyField("self", symmetrical=True, blank=True)

    class Meta:
        constraints = [
            # As mesmas duas do Tema: nome único entre irmãs, com a raiz em condição própria.
            models.UniqueConstraint(Lower("nome"), "pai", name="faq_palavra_chave_nome_unico_no_pai"),
            models.UniqueConstraint(
                Lower("nome"),
                condition=Q(pai__isnull=True),
                name="faq_palavra_chave_nome_unico_na_raiz",
            ),
        ]

    def clean(self) -> None:
        # Três níveis: o pai já estar no terceiro faria desta a quarta. Fora do banco, como no Tema (Caveats).
        if self.pai_id is not None and self.pai.pai_id is not None and self.pai.pai.pai_id is not None:
            raise ValidationError({"pai": "Palavra-chave tem no máximo três níveis."})
```

**`apps/faq/models/conteudo.py`**

```python
class Faq(models.Model):
    resposta_markdown = models.TextField()
    # Referência por string: o modelo de outro arquivo do pacote entra sem import circular.
    tema = models.ForeignKey("faq.Tema", on_delete=models.PROTECT, related_name="faqs")
    # Muitos-para-muitos: a tabela de junção tem as duas FKs, e a busca filtra por elas.
    palavras_chave = models.ManyToManyField("faq.PalavraChave", blank=True, related_name="faqs")
    visibilidade = models.CharField(max_length=10, choices=Visibilidade.choices, default=Visibilidade.PUBLICA)
    situacao = models.CharField(max_length=10, choices=Situacao.choices, default=Situacao.RASCUNHO)
    autor = models.ForeignKey("user_admin.Perfil", on_delete=models.PROTECT, null=True, blank=True)
    relacionadas = models.ManyToManyField("self", symmetrical=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)


class Pergunta(models.Model):
    # A FK diz "esta linha é de uma FAQ só"; o UNIQUE de `chave` diz "esta pergunta é de uma FAQ só".
    faq = models.ForeignKey(Faq, on_delete=models.CASCADE, related_name="perguntas")
    texto = models.CharField(max_length=300)
    # Guardada só para o UNIQUE: `normalize_text` não tem equivalente em SQL (Caveats).
    chave = models.CharField(max_length=300, unique=True)
    eh_principal = models.BooleanField(default=False)

    class Meta:
        constraints = [
            # No máximo uma principal por FAQ. O "ao menos uma" é garantido por `gravar_faq` (Caveats).
            models.UniqueConstraint("faq", condition=Q(eh_principal=True), name="faq_uma_pergunta_principal"),
        ]


class LinkReferencia(models.Model):
    faq = models.ForeignKey(Faq, on_delete=models.CASCADE, related_name="links")
    titulo = models.CharField(max_length=120)
    url = models.CharField(max_length=500)        # o `href` do destino: caminho, se do sistema
    ordem = models.PositiveSmallIntegerField(default=0)
```

**`services/domain/faq/conteudo/erros.py`** — a colisão entre FAQs, dita em termos do domínio.

```python
class PerguntaOcupada(BaseModel):
    pergunta: Pergunta
    faq_id: int                                   # a FAQ que já tem esta pergunta


class PerguntaJaRespondida(Exception):
    """Uma ou mais perguntas já pertencem a outra FAQ."""

    def __init__(self, ocupadas: list[PerguntaOcupada]) -> None:
        super().__init__(f"{len(ocupadas)} pergunta(s) já pertence(m) a outra FAQ.")
        self.ocupadas = ocupadas
```

**`apps/faq/conteudo/cadastro.py`** — a única porta de escrita. faq/002 e a seed de faq/008 usam a
mesma função, e a regravação de faq/002 reusa `conferir_perguntas_livres`.

```python
def gravar_faq(faq: Faq) -> int:
    perguntas = [faq.pergunta, *faq.variacoes]
    # O DTO já recusou pergunta repetida DENTRO da FAQ. Aqui se confere ENTRE FAQs, antes de gravar,
    # para a recusa dizer qual FAQ é a dona.
    conferir_perguntas_livres(perguntas, faq_id=faq.id)
    try:
        return _criar(faq)
    except IntegrityError:
        # Corrida: outra gravação ocupou a pergunta entre a conferência e o INSERT. Conferir de novo
        # transforma a colisão em PerguntaJaRespondida; se a violação foi outra, o erro original sobe.
        conferir_perguntas_livres(perguntas, faq_id=faq.id)
        raise


def conferir_perguntas_livres(perguntas: list[Pergunta], faq_id: int | None) -> None:
    por_chave = {p.chave: p for p in perguntas}
    donas = list(
        PerguntaModel.objects.filter(chave__in=por_chave)
        .exclude(faq_id=faq_id)                   # na regravação, as da própria FAQ não contam
        .values_list("chave", "faq_id")
    )
    if donas:
        raise PerguntaJaRespondida([PerguntaOcupada(pergunta=por_chave[c], faq_id=f) for c, f in donas])


@transaction.atomic
def _criar(faq: Faq) -> int:
    # Transação própria (savepoint, se o chamador já abriu uma): o IntegrityError desfaz só esta FAQ,
    # e a conferência de `gravar_faq` ainda consegue consultar o banco depois dele.
    registro = FaqModel.objects.create(
        resposta_markdown=faq.resposta.markdown,
        tema=_tema_persistido(faq.tema),
        visibilidade=faq.visibilidade,
        situacao=faq.situacao,
        autor_id=faq.autor_id,
    )
    PerguntaModel.objects.create(faq=registro, texto=faq.pergunta.texto, chave=faq.pergunta.chave, eh_principal=True)
    PerguntaModel.objects.bulk_create(
        PerguntaModel(faq=registro, texto=v.texto, chave=v.chave) for v in faq.variacoes
    )
    LinkReferenciaModel.objects.bulk_create(
        LinkReferenciaModel(faq=registro, titulo=l.titulo, url=l.destino.href, ordem=i)
        for i, l in enumerate(faq.resposta.links)
    )
    registro.palavras_chave.set(_palavras_chave_persistidas(faq.palavras_chave))
    registro.relacionadas.set(faq.relacionadas)
    return registro.pk


def _palavras_chave_persistidas(palavras: list[PalavraChave]) -> list[PalavraChaveModel]:
    # Resolve cada uma pelo `caminho`, nível a nível, criando o que falta por `gravar_palavra_chave`
    # (taxonomia/cadastro.py): a seed de faq/008 grava por caminho, e o formulário de faq/002 só manda
    # palavras que já existem. Grava-se só a marcada, nunca os ancestrais, que a busca deriva.
    ...
```

**`apps/faq/taxonomia/cadastro.py`**

```python
@transaction.atomic
def gravar_palavra_chave(palavra: PalavraChave) -> int:
    # A porta única de criação: a área de edição de faq/002 e a resolução por caminho acima passam aqui.
    registro = PalavraChaveModel(nome=palavra.nome, pai_id=palavra.pai.id if palavra.pai else None)
    registro.full_clean()                         # quarto nível e nome repetido entre irmãs sobem aqui
    registro.save()
    # Na criação, não no passo seguinte: a palavra já nasce ligada, numa transação só.
    registro.relacionadas.set(palavra.relacionadas)
    return registro.pk
```

**`services/domain/faq/conteudo/links.py`** — do sistema ou externo é o que a URL diz, contra os domínios do
sistema que a orquestração passa. Quem recebe link como texto (o formulário de faq/002, a seed de
faq/008) chama `resolver_destino` com `DOMINIOS_DO_SISTEMA`; quem lê do banco chama `destino_gravado`.

```python
def resolver_destino(url: str, dominios_do_sistema: frozenset[str]) -> LinkDoSistema | LinkExterno:
    partes = urlsplit(url.strip())
    if not partes.scheme and not partes.netloc:
        return LinkDoSistema(caminho=partes.geturl())      # "/x"; "x" e "" caem no pattern
    if partes.hostname in dominios_do_sistema:
        # O domínio é do ambiente, não do link: sobra o caminho, que vale em qualquer ambiente.
        return LinkDoSistema(caminho=urlunsplit(("", "", partes.path or "/", partes.query, partes.fragment)))
    # "//x" tem host e não tem esquema: cai aqui, e o HttpUrl recusa. Idem "javascript:" e "https://".
    return LinkExterno(url=url.strip())


def destino_gravado(valor: str) -> LinkDoSistema | LinkExterno:
    # O gravado já diz o tipo: o do sistema foi reduzido ao caminho na entrada. Ler não precisa dos domínios.
    return LinkDoSistema(caminho=valor) if valor.startswith("/") else LinkExterno(url=valor)
```

**`config/settings.py`** — os domínios em que o sistema é servido. Não sai do `ALLOWED_HOSTS`, cujo
default é `*`.

```python
dominios_do_sistema: list[str] = Field(
    default_factory=lambda: ["localhost", "127.0.0.1"],
    alias="DOMINIOS_DO_SISTEMA",
)
# entra no field_validator de lista separada por vírgula, ao lado de allowed_hosts

DOMINIOS_DO_SISTEMA = frozenset(_env.dominios_do_sistema)
```

**`services/domain/faq/leitura/visibilidade.py`** — a regra de quem vê o quê. A query do app usa essa regra
para filtrar no banco, e o índice reaplica a mesma regra sobre o que recebe.

```python
def visibilidades_para(leitor: Leitor) -> frozenset[Visibilidade]:
    if leitor.eh_interno:
        return frozenset({Visibilidade.PUBLICA, Visibilidade.INTERNA})
    return frozenset({Visibilidade.PUBLICA})


def eh_visivel(faq: Faq, leitor: Leitor) -> bool:
    # Rascunho não é "interno": não aparece para ninguém na página.
    return faq.situacao is Situacao.PUBLICADA and faq.visibilidade in visibilidades_para(leitor)
```

**`services/domain/faq/leitura/models/indice.py`** — a entrada e a saída da montagem do índice.

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
```

**`services/domain/faq/leitura/indice.py`** — monta a árvore tema → subtema → FAQs da página.

```python
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

**`services/utils/markdown/renderizador.py`** — markdown → HTML seguro. É utilitário geral, e faq/004
abre a tag `<img>` nele. O markdown que ele recebe é o que o editor de faq/002 (Milkdown/Crepe, GFM)
grava, então ele cobre tudo o que o editor oferece: títulos de qualquer nível, riscado, lista de
tarefas, tabela e linha horizontal.

```python
TAGS_PERMITIDAS = frozenset({
    "p", "br", "hr", "strong", "em", "s", "code", "pre", "blockquote",
    "ul", "ol", "li", "input", "a", "h3", "h4", "table", "thead", "tbody", "tr", "th", "td",
})
ESQUEMAS_PERMITIDOS = frozenset({"http", "https", "mailto"})


class RenderizadorMarkdown:
    def __init__(self) -> None:
        # html=False: HTML cru dentro do markdown sai escapado, e não interpretado.
        self._md = (
            MarkdownIt("commonmark", {"html": False})
            .enable(["table", "strikethrough"])
            .use(tasklists_plugin)                 # mdit_py_plugins: `- [ ]` vira checkbox desabilitado
        )
        self._md.core.ruler.push("nivelar_titulos", _nivelar_titulos)

    def __call__(self, texto: str) -> str:
        return self.pipeline(texto)

    def pipeline(self, texto: str) -> str:
        html = self._md.render(texto)
        # Segunda barreira: mesmo que o parser deixe passar algo, o nh3 corta pela allowlist.
        return nh3.clean(
            html,
            tags=TAGS_PERMITIDAS,
            attributes={"a": {"href", "title"}, "input": {"type", "checked", "disabled"}},
            # O único <input> que sobrevive é o checkbox da lista de tarefas, sempre só de leitura.
            set_tag_attribute_values={"input": {"type": "checkbox", "disabled": "disabled"}},
            url_schemes=ESQUEMAS_PERMITIDOS,
            link_rel="noopener noreferrer",
        )


def _nivelar_titulos(state: StateCore) -> None:
    # A página já usa h1 e h2: o título da resposta desce para h3/h4, seja qual for o nível escrito.
    for token in state.tokens:
        if token.type in ("heading_open", "heading_close"):
            token.tag = "h3" if token.tag in ("h1", "h2", "h3") else "h4"
```

**`apps/faq/leitor.py`** — a request vira `Leitor` num lugar só; a página, o widget de faq/006 e a
busca de faq/007 usam esta função.

```python
def leitor_de(request: HttpRequest) -> Leitor:
    # Todo Perfil tem RF (é o USERNAME_FIELD): logado ⇔ RF preenchido.
    return Leitor(rf=request.user.rf if request.user.is_authenticated else None)
```

**`apps/faq/pagina/views.py`** — rota **aberta**, declarada aqui (CLAUDE.md §3.5).

```python
def pagina_faq(request: HttpRequest) -> HttpResponse:
    leitor = leitor_de(request)
    faqs = carregar_faqs(visibilidades_para(leitor))      # apps/faq/conteudo/consulta.py: queryset → list[Faq]
    indice = montar_indice(MontagemIndiceInput(faqs=faqs, leitor=leitor))
    return render(request, "faq/pagina.html", {"indice": indice})
```

**`apps/faq/pagina/urls.py`** e **`apps/faq/urls.py`** — a pasta declara as próprias rotas, e a raiz só
as junta. As SPECs seguintes acrescentam uma linha à lista da raiz por pasta nova.

```python
# apps/faq/pagina/urls.py — sem app_name: o namespace é o da raiz.
urlpatterns = [
    path("", views.pagina_faq, name="pagina"),
]


# apps/faq/urls.py
from .pagina.urls import urlpatterns as pagina

app_name = "faq"

urlpatterns = [
    *pagina,
]
```

O template renderiza a resposta pelo filtro `{{ item.faq.resposta.markdown|markdown }}`
(`apps/faq/templatetags/faq_markdown.py`), que chama o `RenderizadorMarkdown` e marca a saída como
segura. O link de referência sai com `href="{{ link.destino.href }}"`; o `LinkExterno` ganha
`target="_blank" rel="noopener noreferrer"`. `carregar_faqs` monta o destino com `destino_gravado`.

## 7 · Caveats

**A chave normalizada da pergunta é guardada, embora seja derivada.** `normalize_text` não tem
equivalente em SQL, e o UNIQUE que impede duas FAQs com a mesma pergunta só existe sobre uma coluna.
Se a regra de normalização mudar, as chaves gravadas ficam desatualizadas até uma regravação em massa,
que não existe hoje.

**"Uma pergunta pertence a uma única FAQ" vive só no banco.** A unicidade é do conjunto de todas as
perguntas, que nenhum DTO enxerga, e o `Faq` valida só a repetição dentro de si. Uma escrita que não
passe por `gravar_faq` ou pela regravação de faq/002 esbarra no UNIQUE com um `IntegrityError` cru, sem
dizer qual FAQ é a dona.

**"Toda FAQ tem uma pergunta principal" vale no banco só pela metade.** A constraint garante no
máximo uma, e o "ao menos uma" depende de toda escrita passar por `gravar_faq`, numa transação só.
Uma escrita feita direto no ORM pode deixar uma FAQ sem pergunta.

**Os dois níveis de tema e os três de palavra-chave ficam fora do banco.** A regra vive no `clean()` e
no DTO, e expressar profundidade em constraint pediria trigger. Um `create` direto no ORM, sem
`full_clean()`, consegue criar um nível a mais em qualquer das duas árvores.

**As palavras relacionadas são gravadas antes de terem consumidor.** A relação já existe na criação para
que o significado dela (sinônimo, "veja também") se decida depois sem migração nem recadastro. O custo é
uma relação sem semântica fixa: o que for relacionado antes dessa decisão pode precisar de revisão quando
a busca passar a usá-la.

**A rota `/faq/` é aberta, contra o padrão "rota protegida" do CLAUDE.md §3.5.** A FAQ é informação
sobre o uso do sistema, não ato administrativo, e a FAQ pública existe justamente para quem não tem
login. A proteção do conteúdo interno passa a depender só da regra de visibilidade, nas duas camadas
(query e índice).

**Os domínios do sistema são um setting novo, `DOMINIOS_DO_SISTEMA`.** É o que reconhece como do sistema
a URL completa de uma página, e o `ALLOWED_HOSTS` não serve, porque o default dele é `*`. Produção com o
setting errado grava a URL do próprio sistema como link externo, que quebra na troca de domínio.

**Três dependências novas: `markdown-it-py`, `mdit-py-plugins` e `nh3`.** Renderizar markdown a partir
do texto de um administrador exige um parser e um sanitizador mantidos; escrever os dois à mão seria
pior. O `mdit-py-plugins` entra só pela lista de tarefas, que o editor de faq/002 produz. O HTML chega
ao template marcado como seguro, e a allowlist do `nh3` passa a ser a barreira contra XSS.

**O editor e o renderizador são duas implementações de markdown.** O Milkdown, em JavaScript, grava; o
markdown-it, em Python, exibe. O que garante que o leitor vê o que o administrador escreveu é o teste
com uma amostra de tudo o que o editor oferece. Atualizar o Milkdown pode trazer uma construção nova,
e a amostra precisa acompanhar.

**A página renderiza o markdown de todas as FAQs a cada request.** O volume esperado é de dezenas a
poucas centenas de FAQs, então o custo é desprezível. Se crescer, o HTML renderizado passa a ser cache
por FAQ, invalidado na gravação.

**A estrutura de pacotes do épico inteiro é fixada aqui, antes de as SPECs seguintes existirem em
código.** O épico tem 11 modelos e 24 rotas, e sem um mapa cada SPEC empilharia o seu no mesmo
`models.py` e no mesmo `views.py`. Os caminhos citados pelas SPECs 002 a 008 ficam presos a esta
árvore, e mudá-la exige editar esta seção e cada SPEC que cita o caminho.

## 8 · Testes (TDD)
- `test_pergunta_repetida_entre_faqs_eh_recusada` — parametrizado: pergunta repetida com outra
  grafia e variação igual à pergunta de outra FAQ levantam `PerguntaJaRespondida` com o id da FAQ
  dona, sem gravar a segunda FAQ. *(marker `banco`)*
- `test_resolver_destino_classifica_o_link` — parametrizado: `/certidoes/` é do sistema;
  `https://localhost/certidoes/?x=1`, com `localhost` entre os domínios, é do sistema com
  `/certidoes/?x=1`; `https://www.prefeitura.sp.gov.br/` é externo; `//site.com`,
  `javascript:alert(1)`, `https://` e `certidoes` levantam `ValidationError`.
- `test_hierarquia_recusa_nivel_alem_do_limite` — parametrizado: `full_clean()` de um tema cujo pai é
  subtema, e de uma palavra-chave cujo pai está no terceiro nível, levanta `ValidationError` em `pai`.
  *(marker `banco`)*
- `test_faq_grava_palavra_chave_pelo_caminho` — gravar uma FAQ com `IPTU › Certidão` cria as duas
  palavras uma vez só, liga a FAQ só a `Certidão`, e uma segunda FAQ com o mesmo caminho reaproveita
  as duas. *(marker `banco`)*
- `test_palavra_chave_nasce_relacionada_nos_dois_sentidos` — `gravar_palavra_chave` de uma palavra com
  `relacionadas=[IPTU]` grava as duas pontas: a nova lista `IPTU`, e `IPTU` lista a nova. *(marker `banco`)*
- `test_visibilidade_da_pagina_por_leitor` — parametrizado: anônimo vê só pública publicada, logado vê
  pública e interna publicadas, e rascunho não aparece em nenhum dos dois casos (GET `/faq/`).
  *(marker `banco`)*
- `test_indice_agrupa_por_tema_e_subtema_em_ordem` — temas e subtemas saem por `(ordem, nome)`, as
  FAQs em ordem alfabética, e tema sem FAQ visível não gera seção.
- `test_relacionada_invisivel_nao_vaza` — uma pública relacionada a uma interna não lista a interna
  para o leitor anônimo.
- `test_markdown_nao_executa_html_embutido` — `<script>`, `onclick` e `javascript:` no texto não
  sobrevivem à renderização, e `**negrito**`, listas e tabelas sobrevivem.
- `test_renderizador_cobre_o_markdown_do_editor` — uma amostra com cada construção que o editor de
  faq/002 oferece (`#` a `######`, `~~riscado~~`, `- [ ]`/`- [x]`, tabela, `---`, citação, bloco de
  código) sai sem nenhuma sintaxe crua no HTML; `#` e `##` saem como `h3`, e o checkbox sai
  desabilitado.
