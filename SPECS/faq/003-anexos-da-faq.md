---
spec: faq/003
versao: v4
atualizado_em: 2026-11-17
testes_tdd: false
implementado: false
markers_obrigatorios: [banco, integration]
changelog:
  - v1: versão inicial
  - v2: atualiza Faq com videos e delimita Anexo (documento com OCR) frente a MidiaFaq
  - v3: move anexos para o modelo Resposta
  - v4: ajusta Resposta e ponteiros após extrair mídias para faq/004 e índice para faq/005
---

# SPEC faq/003 — Anexos da FAQ com texto extraído

## 1 · User story
O administrador do sistema anexa PDFs e DOCX às FAQs no contexto da edição, para que o leitor baixe o
documento de referência e para que o texto do documento fique disponível para a busca.

## 2 · Condições de pronto
- [ ] O design da seção de anexos (na edição e na resposta aberta da página) foi aprovado no mock e as
      peças foram portadas para o tema e o styleguide antes de o template da aplicação usá-las.
- [ ] Na edição, o administrador envia um PDF ou DOCX novo, ou escolhe um anexo já existente pelo
      título, e o anexo passa a estar ligado à FAQ.
- [ ] Só entra arquivo cujo texto possa ser extraído, inclusive por OCR. Arquivo sem texto aproveitável
      é recusado com a mensagem *"Só são aceitos documentos cujo texto possa ser extraído (inclusive
      por OCR)."*, e nada é gravado.
- [ ] PDF escaneado, sem camada de texto, passa pelo OCR em português e é aceito.
- [ ] Arquivo que não é PDF nem DOCX de verdade é recusado, mesmo com a extensão certa.
- [ ] Arquivo acima do limite de tamanho, ou PDF com mais páginas que o limite de OCR, é recusado antes
      de qualquer extração, com o limite na mensagem.
- [ ] Enviar de novo um arquivo idêntico não cria um segundo anexo: o existente é ligado à FAQ.
- [ ] A resposta aberta na página de FAQ lista os anexos para download. Um anexo só baixa se estiver
      ligado a pelo menos uma FAQ que o leitor pode ver; nos outros casos dá 404.
- [ ] Desligar um anexo de uma FAQ não o apaga: ele continua disponível para as outras FAQs.

## 3 · Domínio

O anexo é um documento de referência textual (PDF ou DOCX), independente da FAQ: um mesmo anexo serve
a várias FAQs, e a identidade dele é o conteúdo (hash), não o nome do arquivo. [`Faq`](001-pagina-de-faq.md#3--domínio)
já compõe `Resposta`, e esta SPEC acrescenta `anexos` a ela.

```python
class TipoDocumento(StrEnum):            # services/utils/extracao_texto: não é conceito da FAQ
    PDF = "pdf"
    DOCX = "docx"


class OrigemTexto(StrEnum):              # idem
    CAMADA_DE_TEXTO = "camada_de_texto"      # PDF digital ou DOCX
    OCR = "ocr"                              # PDF escaneado


class TextoExtraido(BaseModel):          # idem
    """O texto aproveitável de um arquivo. Não existe TextoExtraido vazio: a extração falha antes."""
    conteudo: str = Field(min_length=MINIMO_CARACTERES_UTEIS)
    origem: OrigemTexto


class Anexo(BaseModel):
    id: int | None = None
    titulo: str = Field(min_length=2, max_length=160)
    nome_arquivo: str
    tipo: TipoDocumento
    hash_conteudo: str = Field(pattern=r"^[0-9a-f]{64}$")   # sha256 dos bytes
    tamanho_bytes: int = Field(gt=0)
    texto: TextoExtraido
    enviado_por_id: int


# ALTERADO nesta SPEC: `Resposta` (faq/001) ganha `anexos`.
class Resposta(BaseModel):
    markdown: str = Field(min_length=1)
    links: list[LinkReferencia] = []
    anexos: list[int] = []                   # NOVO: ids de Anexo; o vínculo não tem atributos

    @field_validator("markdown", mode="before")
    @classmethod
    def _nao_vazia(cls, valor: str) -> str:
        if not valor or not valor.strip():
            raise ValueError("A resposta não pode ficar em branco.")
        return valor
```

**Mock:** [003-mock-anexos-da-faq.html](003-mock-anexos-da-faq.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Imagens embutidas e vídeos ilustrativos da resposta — faq/004.
- Divisão do texto em trechos e embeddings dos anexos — faq/005.
- Excluir anexo órfão (sem FAQ) e a tela do acervo de anexos — sem dono ainda.
- Outros formatos documentais (ODT, planilhas) — sem dono ainda.
- Extração assíncrona, em fila — sem dono ainda.

## 5 · Peças de referência a compor
- `pypdf` (já é dependência) → leitura da camada de texto do PDF.
- `@apps/documentos/models.py` → `DocumentoEmitido.arquivo`: o padrão de PDF em `bytea` na linha.
- `@apps/faq/acesso.py` → `superusuario_requerido` (faq/002): portão do upload.
- `@services/domain/faq/visibilidade.py` → `eh_visivel` (faq/001): base da regra de download.
- Skills: `erros-de-formulario`, `componentes-frontend`, `daisyui`, `htmx-skill`, `mock`,
  `escrever-testes`, `test-django-views`.

## 6 · Snippets

> O comentário didático destes blocos existe só aqui e **não é portado** (CLAUDE.md §7.2).

**`services/utils/extracao_texto/models.py`** — os limites. `services/` não lê settings: o app monta
este DTO a partir de `FAQ_ANEXO_TAMANHO_MAXIMO_BYTES` (padrão 20 MB) e `FAQ_ANEXO_PAGINAS_MAXIMAS_OCR`
(padrão 40) e o entrega ao construtor do extrator.

```python
class LimitesExtracao(BaseModel):
    tamanho_maximo_bytes: int = Field(gt=0)
    paginas_maximas_ocr: int = Field(gt=0)


MINIMO_CARACTERES_UTEIS = 40           # menos que isso é capa, carimbo ou ruído de OCR
IDIOMA_OCR = "por"
```

**`services/utils/extracao_texto/extrator.py`** — utilitário geral, sem domínio de FAQ. A falha é uma
exceção própria; o chamador nunca vê `pypdf`, `docx` nem `tesseract`.

```python
class ExtracaoImpossivel(Exception):
    """O arquivo não rende texto aproveitável. A mensagem é a que vai para o usuário."""


class ExtratorTexto:
    def __call__(self, conteudo: bytes) -> tuple[TipoDocumento, TextoExtraido]:
        return self.pipeline(conteudo)

    def pipeline(self, conteudo: bytes) -> tuple[TipoDocumento, TextoExtraido]:
        self._conferir_tamanho(conteudo)
        tipo = self._detectar_tipo(conteudo)            # pelos bytes, nunca pela extensão
        try:
            texto = self._extrair(tipo, conteudo)
        except ExtracaoImpossivel:
            raise
        except Exception as erro:
            # Fail-safe: qualquer falha da biblioteca é recusa do arquivo, nunca anexo sem texto.
            raise ExtracaoImpossivel(MENSAGEM_RECUSA) from erro
        return tipo, texto

    def _detectar_tipo(self, conteudo: bytes) -> TipoDocumento:
        if conteudo.startswith(b"%PDF-"):
            return TipoDocumento.PDF
        # DOCX é um ZIP com `word/document.xml`; um ZIP qualquer renomeado não passa.
        if conteudo.startswith(b"PK\x03\x04") and _zip_tem(conteudo, "word/document.xml"):
            return TipoDocumento.DOCX
        raise ExtracaoImpossivel("Só são aceitos arquivos PDF ou DOCX.")

    def _extrair(self, tipo: TipoDocumento, conteudo: bytes) -> TextoExtraido:
        if tipo is TipoDocumento.DOCX:
            return self._validar(_texto_docx(conteudo), OrigemTexto.CAMADA_DE_TEXTO)
        camada = _texto_camada_pdf(conteudo)
        if _uteis(camada) >= MINIMO_CARACTERES_UTEIS:
            return self._validar(camada, OrigemTexto.CAMADA_DE_TEXTO)
        self._conferir_paginas_para_ocr(conteudo)
        return self._validar(_texto_ocr_pdf(conteudo, IDIOMA_OCR), OrigemTexto.OCR)

    def _validar(self, texto: str, origem: OrigemTexto) -> TextoExtraido:
        if _uteis(texto) < MINIMO_CARACTERES_UTEIS:
            raise ExtracaoImpossivel(MENSAGEM_RECUSA)
        return TextoExtraido(conteudo=texto, origem=origem)
```

OCR: `pdf2image` (poppler) rasteriza a página, e `pytesseract` (tesseract com `por`) lê a imagem.
DOCX: `python-docx`, parágrafos e células de tabela. Os pacotes `tesseract-ocr`, `tesseract-ocr-por` e
`poppler-utils` entram no `apt-get` de `docker/Dockerfile.web`.

**`apps/faq/models.py`**

```python
class Anexo(models.Model):
    titulo = models.CharField(max_length=160)
    nome_arquivo = models.CharField(max_length=255)
    tipo = models.CharField(max_length=4, choices=TipoDocumento.choices)
    # Mesmo padrão do acervo de documentos emitidos: o arquivo vive na linha.
    arquivo = models.BinaryField()
    hash_conteudo = models.CharField(max_length=64, unique=True)
    tamanho_bytes = models.PositiveIntegerField()
    texto = models.TextField()
    origem_texto = models.CharField(max_length=16, choices=OrigemTexto.choices)
    enviado_por = models.ForeignKey("user_admin.Perfil", on_delete=models.PROTECT)
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # A regra "não existe anexo sem texto" também no banco, não só no extrator.
            models.CheckConstraint(condition=~Q(texto=""), name="faq_anexo_com_texto"),
        ]

# Faq ganha:
anexos = models.ManyToManyField(Anexo, blank=True, related_name="faqs")
```

**`apps/faq/anexos.py`** — o upload: hash primeiro, extração só se o arquivo é novo.

```python
@transaction.atomic
def receber_anexo(faq: FaqModel, envio: EnvioAnexo, editor: Editor) -> AnexoModel:
    conteudo = envio.conteudo
    hash_conteudo = sha256(conteudo).hexdigest()
    existente = AnexoModel.objects.filter(hash_conteudo=hash_conteudo).first()
    if existente is not None:
        # Mesmo arquivo, mesmo anexo: só se liga. Título e texto do primeiro envio prevalecem.
        faq.anexos.add(existente)
        return existente
    tipo, texto = extrair_texto(conteudo)            # ExtracaoImpossivel sobe antes de qualquer INSERT
    anexo = AnexoModel.objects.create(
        titulo=envio.titulo,
        nome_arquivo=envio.nome_arquivo,
        tipo=tipo,
        arquivo=conteudo,
        hash_conteudo=hash_conteudo,
        tamanho_bytes=len(conteudo),
        texto=texto.conteudo,
        origem_texto=texto.origem,
        enviado_por_id=editor.perfil_id,
    )
    faq.anexos.add(anexo)
    return anexo
```

A view captura `ExtracaoImpossivel` e devolve o `<form>` com a mensagem no campo do arquivo (skill
`erros-de-formulario`).

**`services/domain/faq/visibilidade.py`** — a regra do download, ao lado das de faq/001.

```python
def anexo_eh_baixavel(faqs_do_anexo: list[Faq], leitor: Leitor) -> bool:
    # O anexo não tem visibilidade própria: herda a da FAQ mais aberta a que está ligado.
    return any(eh_visivel(f, leitor) for f in faqs_do_anexo)
```

**Rotas:** `faq:anexo_baixar` (aberta, decidida por `anexo_eh_baixavel`, `Content-Disposition:
attachment`), `faq:admin_anexo_enviar`, `faq:admin_anexo_ligar`, `faq:admin_anexo_desligar` e
`faq:admin_anexo_buscar` (busca por título, em HTMX). As quatro de administração ficam atrás de
`superusuario_requerido` e de `faq_editavel`.

## 7 · Caveats

**O OCR roda síncrono, dentro do request do upload.** Um PDF escaneado de 40 páginas leva dezenas de
segundos, mas fila é exceção a justificar (CLAUDE.md §3.5), e o envio de anexo é raro. O teto de
páginas é o que impede um upload de prender um worker por minutos, e um documento maior precisa ser
dividido antes do envio.

**O container web ganha tesseract e poppler.** O OCR exige binários do sistema, e um serviço separado
só para isso seria infraestrutura demais para o volume esperado. A imagem fica maior, e a suíte de OCR
roda só sob o marker `integration`, onde os binários existem.

**O arquivo vive em `bytea`, junto do texto extraído.** É o padrão já adotado no acervo de documentos
emitidos: uma linha, uma transação, nenhum storage a operar. O banco cresce com os anexos, e o limite de
tamanho é o controle.

**Anexo reenviado mantém o título do primeiro envio.** A identidade é o conteúdo, e dois títulos para o
mesmo arquivo seriam o mesmo dado em dois lugares. O administrador que esperava renomear no reenvio não
consegue; renomear fica sem dono.

**Anexo órfão fica no banco.** Desligar não apaga, e não há tela de exclusão. Ele não baixa por
ninguém (nenhuma FAQ visível), mas ocupa espaço até existir a limpeza.

**O download é aberto e herda a visibilidade das FAQs.** O anexo não tem visibilidade própria, então
ligar um anexo interno a uma FAQ pública o torna público. Quem decide é quem liga.

## 8 · Testes (TDD)
- `test_docx_rende_texto_de_paragrafos_e_tabelas` — o texto de uma célula de tabela aparece no
  extraído.
- `test_pdf_digital_usa_camada_de_texto` — sai `origem=camada_de_texto`, sem chamar o OCR.
- `test_pdf_escaneado_passa_pelo_ocr` — um PDF-imagem com texto em português sai `origem=ocr`, com
  as palavras esperadas. *(marker `integration`)*
- `test_arquivo_sem_texto_eh_recusado` — PDF de página em branco levanta `ExtracaoImpossivel` com a
  mensagem de recusa. *(marker `integration`)*
- `test_falha_da_biblioteca_vira_recusa` — PDF corrompido levanta `ExtracaoImpossivel`, nunca
  outra exceção.
- `test_extensao_mentirosa_eh_recusada` — um ZIP qualquer chamado `.docx` e um texto chamado `.pdf` são
  recusados.
- `test_limites_recusam_antes_de_extrair` — tamanho acima do teto e PDF escaneado acima do teto de
  páginas são recusados sem chamar o extrator nem o OCR.
- `test_reenvio_do_mesmo_arquivo_reaproveita_o_anexo` — duas FAQs, um só `Anexo`, e a extração roda
  uma vez. *(marker `banco`)*
- `test_upload_recusado_nao_grava_nada` — nenhum `Anexo` e nenhum vínculo depois da recusa.
  *(marker `banco`)*
- `test_download_segue_a_faq_mais_aberta` — parametrizado: ligado só a interna → 404 para anônimo; ligado
  também a pública → baixa; ligado só a rascunho → 404 para todos. *(marker `banco`)*
