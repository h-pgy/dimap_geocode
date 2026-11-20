---
spec: faq/003
versao: v21
atualizado_em: 2026-11-19
testes_tdd: false
implementado: true
markers_obrigatorios: [banco, integration]
changelog:
  - v1: versão inicial
  - v2: atualiza Faq com videos e delimita Anexo (documento com OCR) frente a MidiaFaq
  - v3: move anexos para o modelo Resposta
  - v4: ajusta Resposta e ponteiros após extrair mídias para faq/004 e índice para faq/005
  - v5: vídeos saem do épico
  - v6: OCR página a página, com prazo e sem disputar CPU com o web
  - v7: o vínculo do anexo é gravado com o formulário da FAQ, como o das imagens
  - v8: caminhos seguem a estrutura de pacotes de faq/001
  - v9: o portão de superusuário vem de apps/core
  - v10: parâmetros do extrator num DTO de config montado dos settings, e a leitura da FAQ devolve os anexos ligados
  - v11: a exceção do extrator vai para um módulo erros.py
  - v12: aceita também DOC e ODT, com o seletor de arquivo restrito às quatro extensões
  - v13: o DOC deixa de ser lido e é recusado com o pedido de salvar como DOCX
  - v14: a contagem do prazo do OCR ganha métodos próprios
  - v15: o OCR ganha módulo próprio, com o PDF gravado uma vez e o prazo restante como timeout de cada página
  - v16: o arquivo novo é enviado e gravado junto com o salvar da FAQ, e a edição abandonada não deixa anexo no banco
  - v17: um extrator por formato, composto e despachado por ExtratorTexto, e uma rota que confere o arquivo ao ser escolhido, sem gravar
  - v18: o fail-safe vira gerenciador de contexto, e o comentário que vai para o código ganha marca própria
  - v19: a montagem do extrator nomeia cada peça antes de compor
  - v20: ExtratorTexto monta as próprias peças no construtor, e a função de montagem sai
  - v21: os anexos da edição viram linhas no estilo da tabela de vidro, com botão para ler o texto extraído e X para tirar o anexo da FAQ, e uma chave alterna entre enviar arquivo e buscar já enviado
---

# SPEC faq/003 — Anexos da FAQ com texto extraído

## 1 · User story
O administrador do sistema anexa documentos PDF, DOCX e ODT às FAQs no contexto da edição, para que o leitor baixe o
documento de referência e para que o texto do documento fique disponível para a busca.

## 2 · Condições de pronto
- [ ] O design da seção de anexos (na edição e na resposta aberta da página) foi aprovado no mock e as
      peças foram portadas para o tema e o styleguide antes de o template da aplicação usá-las.
- [ ] Na edição, inclusive de uma FAQ que ainda não foi gravada, o administrador escolhe um ou mais
      arquivos PDF, DOCX ou ODT novos no campo de arquivo do formulário, ou escolhe um anexo já existente
      pelo título. Uma chave de duas posições ("Arquivo novo" × "Já enviado") alterna entre
      o campo de arquivo e a busca. O arquivo novo só é lido e gravado quando a FAQ é salva, e fica ligado a ela no mesmo
      salvar; o título do anexo novo é o nome do arquivo, sem a extensão.
- [ ] Uma edição abandonada sem salvar não grava anexo nenhum.
- [ ] Ao escolher os arquivos, cada um é conferido na hora, sem gravar nada: o formulário mostra, por
      arquivo, a recusa com a mensagem, ou o aceite, avisando quando o texto vai sair por OCR no salvar.
- [ ] Um arquivo recusado no salvar devolve o formulário com a mensagem no campo de arquivo, prefixada
      pelo nome do arquivo, e nada da FAQ nem dos anexos é gravado. Todos os campos voltam preenchidos,
      inclusive o de arquivo.
- [ ] Só entra arquivo cujo texto possa ser extraído, inclusive por OCR. Arquivo sem texto aproveitável
      é recusado com a mensagem *"Só são aceitos documentos cujo texto possa ser extraído (inclusive
      por OCR)."*, e nada é gravado.
- [ ] PDF escaneado, sem camada de texto, passa pelo OCR em português e é aceito.
- [ ] O seletor de arquivo do formulário só oferece arquivos `.pdf`, `.docx`, `.doc` e `.odt`.
- [ ] Um ODT (LibreOffice Writer) com texto é aceito, e um DOCX salvo pelo LibreOffice é aceito como
      DOCX.
- [ ] Um DOC (Word 97–2003) é recusado, e nada é gravado, com a mensagem *"Arquivos .doc (Word 97–2003)
      não são aceitos. Abra o arquivo no Word ou no LibreOffice, salve como DOCX e envie de novo."*
- [ ] Arquivo que não é PDF, DOCX nem ODT de verdade é recusado, mesmo com a extensão certa.
- [ ] Arquivo acima do limite de tamanho é recusado antes de qualquer leitura, e PDF escaneado com mais
      páginas que o limite de OCR é recusado antes do OCR, os dois com o limite na mensagem.
- [ ] Um OCR que passa do prazo é interrompido, e o arquivo é recusado com o pedido de dividir o PDF.
- [ ] Enviar de novo um arquivo idêntico não cria um segundo anexo: o existente é ligado à FAQ.
- [ ] A resposta aberta na página de FAQ lista os anexos para download. Um anexo só baixa se estiver
      ligado a pelo menos uma FAQ que o leitor pode ver; nos outros casos dá 404.
- [ ] Na edição, os anexos ligados aparecem em linhas no estilo da tabela de vidro, sem cabeçalho
      (título, tipo, tamanho e origem do texto). Cada linha tem um botão que abre, num modal, o texto extraído do anexo, e um X que o tira
      da lista. Só o administrador vê a tabela e o texto.
- [ ] Tirar um anexo da lista pelo X e salvar a FAQ o desliga sem apagá-lo: ele continua disponível
      para as outras FAQs. Salvar sem mexer na lista mantém os anexos como estavam.

## 3 · Domínio

O anexo é um documento de referência textual (PDF, DOCX ou ODT), independente da FAQ: um mesmo anexo serve
a várias FAQs, e a identidade dele é o conteúdo (hash), não o nome do arquivo. [`Faq`](001-pagina-de-faq.md#3--domínio)
já compõe `Resposta`, e esta SPEC acrescenta `anexos` a ela.

```python
class TipoDocumento(StrEnum):            # services/utils/extracao_texto: não é conceito da FAQ
    PDF = "pdf"
    DOCX = "docx"
    ODT = "odt"                              # OpenDocument, o formato nativo do LibreOffice Writer


class OrigemTexto(StrEnum):              # idem
    CAMADA_DE_TEXTO = "camada_de_texto"      # PDF digital, DOCX ou ODT
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


# ALTERADO nesta SPEC: `Resposta` (faq/001, em services/domain/faq/conteudo/models/faq.py) ganha `anexos`.
class Resposta(BaseModel):
    """Conteúdo que responde às perguntas: texto markdown, links de referência e anexos."""
    markdown: str = Field(min_length=1)
    links: list[LinkReferencia] = []
    anexos: list[int] = []                   # NOVO: ids de Anexo, os da lista do formulário; o vínculo não tem atributos

    @field_validator("markdown", mode="before")
    @classmethod
    def _nao_vazia(cls, valor: str) -> str:
        if not valor or not valor.strip():
            raise ValueError("A resposta não pode ficar em branco.")
        return valor
```

**Mock:** [003-mock-anexos-da-faq.html](003-mock-anexos-da-faq.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Imagens embutidas na resposta — faq/004.
- Divisão do texto em trechos e embeddings dos anexos — faq/005.
- Excluir anexo desligado de todas as FAQs e a tela do acervo de anexos — sem dono ainda.
- Renomear o título de um anexo — sem dono ainda.
- Outros formatos documentais (RTF, ODT plano `.fodt`, modelos `.ott`/`.dotx`, planilhas) — sem dono ainda.
- Extração assíncrona, em fila — sem dono ainda.

## 5 · Peças de referência a compor
- `pypdf` (já é dependência) → leitura da camada de texto do PDF.
- `@apps/documentos/models.py` → `DocumentoEmitido.arquivo`: o padrão de PDF em `bytea` na linha.
- `@apps/core/acesso.py` → `superusuario_requerido` (faq/002): portão da busca de anexos.
- `@apps/faq/gestao/formularios.py` → `salvar_faq_nova`, `salvar_faq_existente` e `_gravando` (faq/002):
  o salvar que passa a receber os arquivos.
- `@services/domain/faq/leitura/visibilidade.py` → `eh_visivel` (faq/001): base da regra de download.
- Skills: `erros-de-formulario`, `componentes-frontend`, `daisyui`, `htmx-skill`, `mock`,
  `escrever-testes`, `test-django-views`.

## 6 · Snippets

> O comentário didático destes blocos existe só aqui e **não é portado** (CLAUDE.md §7.2). A exceção é
> o comentário marcado com `[portar]`: ele vai para o código, sem a marca.

**`services/utils/extracao_texto/models.py`** (a config) — no padrão de `SmtpConfig` e `PlantaConfig`.
`services/` não lê settings: o app reextrai os settings para constantes locais, monta o DTO e o
entrega ao construtor do extrator. O que fica como constante é regra do produto ou texto ao usuário,
não ajuste de ambiente.

```python
MINIMO_CARACTERES_UTEIS = 40           # menos que isso é capa, carimbo ou ruído de OCR; TextoExtraido o usa


class ExtracaoConfig(BaseModel):
    """Limites e parâmetros do OCR. Nasce na orquestração (settings) e é injetada no extrator."""

    model_config = ConfigDict(frozen=True)

    tamanho_maximo_bytes: int = Field(gt=0)
    paginas_maximas_ocr: int = Field(gt=0)
    prazo_ocr_s: float = Field(gt=0)
    idioma_ocr: str = Field(min_length=3)        # precisa do pacote tesseract-ocr-<idioma> na imagem
    dpi_ocr: int = Field(gt=0)
```

| Setting | Padrão | Campo |
|---|---|---|
| `FAQ_ANEXO_TAMANHO_MAXIMO_BYTES` | 20 MB | `tamanho_maximo_bytes` |
| `FAQ_ANEXO_PAGINAS_MAXIMAS_OCR` | 40 | `paginas_maximas_ocr` |
| `FAQ_ANEXO_PRAZO_OCR_S` | 120 | `prazo_ocr_s` |
| `FAQ_ANEXO_IDIOMA_OCR` | `"por"` | `idioma_ocr` |
| `FAQ_ANEXO_DPI_OCR` | 200 | `dpi_ocr` |

Os padrões vivem só nos settings (lidos do `.env`, com entrada no `.env.example`); o DTO não repete
nenhum.

O pacote `services/utils/extracao_texto/` é um utilitário geral, sem domínio de FAQ. Cada formato tem o
seu extrator, e todos cumprem o mesmo contrato: `__call__` devolve o texto, e `conferir` diz se o
arquivo é aceitável e de que origem o texto vai sair, sem rodar o OCR. `ExtratorTexto` não extrai nada:
monta os extratores, confere o tamanho, pergunta o tipo ao `DetectorTipo` e despacha para o extrator do tipo.

| Módulo | Peça | Única biblioteca que importa |
|---|---|---|
| `models.py` | `TipoDocumento`, `OrigemTexto`, `TextoExtraido`, `ExtracaoConfig`, o contrato `Extrator` | — |
| `erros.py` | `ExtracaoImpossivel` | — |
| `aproveitamento.py` | `texto_aproveitavel`, `tem_texto_util` | — |
| `deteccao.py` | `DetectorTipo` | `zipfile` |
| `extrator_docx.py` | `ExtratorDocx` | `python-docx` |
| `extrator_odt.py` | `ExtratorOdt` | `zipfile`, `xml.etree` |
| `extrator_pdf.py` | `ExtratorPdf` (compõe um `Extrator` para o OCR) | `pypdf` |
| `extrator_ocr.py` | `ExtratorOcr` | `pdf2image`, `pytesseract` |
| `extrator.py` | `ExtratorTexto` | — |

O `__init__.py` reexporta `ExtratorTexto`, `ExtracaoConfig`,
`ExtracaoImpossivel`, `TipoDocumento`, `OrigemTexto` e `TextoExtraido`; o chamador nunca vê `pypdf`,
`docx` nem `tesseract`.

**`models.py`** — o contrato. É um `Protocol`, não uma ABC: os extratores não herdam nada.

```python
class Extrator(Protocol):
    def __call__(self, conteudo: bytes) -> TextoExtraido: ...

    def conferir(self, conteudo: bytes) -> OrigemTexto: ...
```

**`erros.py`**

```python
class ExtracaoImpossivel(Exception):
    """O arquivo não rende texto aproveitável. A mensagem é a que vai para o usuário."""
```

**`aproveitamento.py`** — a regra do mínimo, num lugar só, usada por todos os extratores.

```python
MENSAGEM_RECUSA = "Só são aceitos documentos cujo texto possa ser extraído (inclusive por OCR)."


def tem_texto_util(texto: str) -> bool:
    return sum(caractere.isalnum() for caractere in texto) >= MINIMO_CARACTERES_UTEIS


def texto_aproveitavel(texto: str, origem: OrigemTexto) -> TextoExtraido:
    if not tem_texto_util(texto):
        raise ExtracaoImpossivel(MENSAGEM_RECUSA)
    return TextoExtraido(conteudo=texto, origem=origem)
```

**`deteccao.py`** — o tipo pelos bytes, nunca pela extensão.

```python
MENSAGEM_FORMATO = "Só são aceitos arquivos PDF, DOCX ou ODT."
MENSAGEM_DOC = (
    "Arquivos .doc (Word 97–2003) não são aceitos. "
    "Abra o arquivo no Word ou no LibreOffice, salve como DOCX e envie de novo."
)
ASSINATURA_PDF = b"%PDF-"
ASSINATURA_ZIP = b"PK\x03\x04"
ASSINATURA_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
MIMETYPE_ODT = b"application/vnd.oasis.opendocument.text"


class DetectorTipo:
    def __call__(self, conteudo: bytes) -> TipoDocumento:
        if conteudo.startswith(ASSINATURA_PDF):
            return TipoDocumento.PDF
        if conteudo.startswith(ASSINATURA_ZIP):
            return self._tipo_do_zip(conteudo)
        if conteudo.startswith(ASSINATURA_OLE):
            # Formato binário do Office 97–2003: quem tem o arquivo tem um editor que salva em DOCX.
            raise ExtracaoImpossivel(MENSAGEM_DOC)
        raise ExtracaoImpossivel(MENSAGEM_FORMATO)

    def _tipo_do_zip(self, conteudo: bytes) -> TipoDocumento:
        with ZipFile(BytesIO(conteudo)) as pacote:
            membros = set(pacote.namelist())
            # O DOCX do LibreOffice tem o mesmo `word/document.xml` do DOCX do Word.
            if "word/document.xml" in membros:
                return TipoDocumento.DOCX
            # O ODT se declara no membro `mimetype`; ODS e ODP têm outro valor ali.
            if "mimetype" in membros and pacote.read("mimetype") == MIMETYPE_ODT:
                return TipoDocumento.ODT
        raise ExtracaoImpossivel(MENSAGEM_FORMATO)
```

**`extrator_docx.py`**

```python
class ExtratorDocx:
    def __call__(self, conteudo: bytes) -> TextoExtraido:
        documento = Document(BytesIO(conteudo))
        return texto_aproveitavel("\n".join(self._trechos(documento)), OrigemTexto.CAMADA_DE_TEXTO)

    def conferir(self, conteudo: bytes) -> OrigemTexto:
        return self(conteudo).origem

    def _trechos(self, documento: DocumentoDocx) -> Iterator[str]:
        yield from (paragrafo.text for paragrafo in documento.paragraphs)
        for tabela in documento.tables:
            for linha in tabela.rows:
                yield from (celula.text for celula in linha.cells)
```

**`extrator_odt.py`** — `zipfile` e `xml.etree` da stdlib bastam; não vale uma dependência.

```python
NAMESPACE_TEXTO = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
# Parágrafo e título; as células de tabela do ODT são feitas de parágrafos.
BLOCOS_DE_TEXTO = {f"{{{NAMESPACE_TEXTO}}}p", f"{{{NAMESPACE_TEXTO}}}h"}


class ExtratorOdt:
    def __call__(self, conteudo: bytes) -> TextoExtraido:
        with ZipFile(BytesIO(conteudo)) as pacote:
            raiz = ElementTree.fromstring(pacote.read("content.xml"))
        trechos = ("".join(no.itertext()) for no in raiz.iter() if no.tag in BLOCOS_DE_TEXTO)
        return texto_aproveitavel("\n".join(trechos), OrigemTexto.CAMADA_DE_TEXTO)

    def conferir(self, conteudo: bytes) -> OrigemTexto:
        return self(conteudo).origem
```

**`extrator_pdf.py`** — a camada de texto primeiro; sem texto útil nela, o PDF é escaneado e vai para
o OCR que recebeu.

```python
class ExtratorPdf:
    def __init__(self, ocr: Extrator) -> None:
        self._ocr = ocr

    def __call__(self, conteudo: bytes) -> TextoExtraido:
        camada = self._camada(conteudo)
        if tem_texto_util(camada):
            return texto_aproveitavel(camada, OrigemTexto.CAMADA_DE_TEXTO)
        return self._ocr(conteudo)

    def conferir(self, conteudo: bytes) -> OrigemTexto:
        if tem_texto_util(self._camada(conteudo)):
            return OrigemTexto.CAMADA_DE_TEXTO
        return self._ocr.conferir(conteudo)

    def _camada(self, conteudo: bytes) -> str:
        leitor = PdfReader(BytesIO(conteudo))
        return "\n".join(pagina.extract_text() or "" for pagina in leitor.pages)
```

**`extrator_ocr.py`** — o PDF inteiro como imagem, página a página. `conferir` só checa o teto de
páginas: é o que a rota de conferência usa para não rodar o OCR.

```python
MENSAGEM_PAGINAS = "PDFs escaneados podem ter até {limite} páginas. Divida o arquivo e envie as partes."
MENSAGEM_PRAZO_OCR = "O OCR deste PDF passou do tempo limite. Divida o arquivo e envie as partes."
TIMEOUT_TESSERACT = "Tesseract process timeout"


class ExtratorOcr:
    def __init__(self, config: ExtracaoConfig) -> None:
        self._config = config

    def __call__(self, conteudo: bytes) -> TextoExtraido:
        return self.pipeline(conteudo)

    def pipeline(self, conteudo: bytes) -> TextoExtraido:
        with self._arquivo_temporario(conteudo) as caminho:
            total_paginas = self._conferir_paginas(caminho)
            prazo = self._iniciar_prazo()
            paginas = [
                self._ler_pagina(caminho, numero, prazo) for numero in range(1, total_paginas + 1)
            ]
        return texto_aproveitavel("\n".join(paginas), OrigemTexto.OCR)

    def conferir(self, conteudo: bytes) -> OrigemTexto:
        with self._arquivo_temporario(conteudo) as caminho:
            self._conferir_paginas(caminho)
        return OrigemTexto.OCR

    @contextmanager
    def _arquivo_temporario(self, conteudo: bytes) -> Iterator[Path]:
        # O poppler lê de arquivo; gravar uma vez evita regravar o PDF inteiro a cada página.
        with NamedTemporaryFile(suffix=".pdf") as arquivo:
            arquivo.write(conteudo)
            arquivo.flush()
            yield Path(arquivo.name)

    def _conferir_paginas(self, caminho: Path) -> int:
        total = int(pdfinfo_from_path(caminho)["Pages"])
        if total > self._config.paginas_maximas_ocr:
            raise ExtracaoImpossivel(MENSAGEM_PAGINAS.format(limite=self._config.paginas_maximas_ocr))
        return total

    def _ler_pagina(self, caminho: Path, numero: int, prazo: float) -> str:
        # Uma página por vez, em tons de cinza: a memória fica em uma página (~4 MB a 200 dpi).
        imagem = self._rasterizar(caminho, numero, self._tempo_restante(prazo))
        return self._ler_imagem(imagem, self._tempo_restante(prazo))

    def _rasterizar(self, caminho: Path, numero: int, timeout_s: float) -> Image:
        try:
            imagens = convert_from_path(
                caminho,
                dpi=self._config.dpi_ocr,
                first_page=numero,
                last_page=numero,
                grayscale=True,
                timeout=timeout_s,
            )
        except PDFPopplerTimeoutError as erro:
            raise ExtracaoImpossivel(MENSAGEM_PRAZO_OCR) from erro
        return imagens[0]

    def _ler_imagem(self, imagem: Image, timeout_s: float) -> str:
        try:
            return pytesseract.image_to_string(imagem, lang=self._config.idioma_ocr, timeout=timeout_s)
        except RuntimeError as erro:
            # O pytesseract sinaliza o timeout com um RuntimeError genérico; só a mensagem o distingue.
            if str(erro) != TIMEOUT_TESSERACT:
                raise
            raise ExtracaoImpossivel(MENSAGEM_PRAZO_OCR) from erro

    def _iniciar_prazo(self) -> float:
        # Relógio monotônico: um ajuste de hora do sistema no meio do OCR não adianta nem atrasa o prazo.
        return monotonic() + self._config.prazo_ocr_s

    def _tempo_restante(self, prazo: float) -> float:
        restante = prazo - monotonic()
        if restante <= 0:
            raise ExtracaoImpossivel(MENSAGEM_PRAZO_OCR)
        return restante
```

**`extrator.py`** — a fachada: monta os extratores no construtor e despacha para o do tipo.

```python
MENSAGEM_TAMANHO = "O arquivo passa do limite de {limite_mb} MB."


class ExtratorTexto:
    def __init__(self, config: ExtracaoConfig) -> None:
        extrator_ocr = ExtratorOcr(config=config)
        extrator_pdf = ExtratorPdf(ocr=extrator_ocr)
        extrator_docx = ExtratorDocx()
        extrator_odt = ExtratorOdt()
        self._config = config
        self._detectar_tipo = DetectorTipo()
        self._extratores: dict[TipoDocumento, Extrator] = {
            TipoDocumento.PDF: extrator_pdf,
            TipoDocumento.DOCX: extrator_docx,
            TipoDocumento.ODT: extrator_odt,
        }

    def __call__(self, conteudo: bytes) -> tuple[TipoDocumento, TextoExtraido]:
        return self.pipeline(conteudo)

    def pipeline(self, conteudo: bytes) -> tuple[TipoDocumento, TextoExtraido]:
        tipo = self._tipo(conteudo)
        with self._recusando_falhas():
            return tipo, self._extratores[tipo](conteudo)

    def conferir(self, conteudo: bytes) -> tuple[TipoDocumento, OrigemTexto]:
        tipo = self._tipo(conteudo)
        with self._recusando_falhas():
            return tipo, self._extratores[tipo].conferir(conteudo)

    def _tipo(self, conteudo: bytes) -> TipoDocumento:
        if len(conteudo) > self._config.tamanho_maximo_bytes:
            limite_mb = self._config.tamanho_maximo_bytes // 1_000_000
            raise ExtracaoImpossivel(MENSAGEM_TAMANHO.format(limite_mb=limite_mb))
        with self._recusando_falhas():
            return self._detectar_tipo(conteudo)

    @contextmanager
    def _recusando_falhas(self) -> Iterator[None]:
        # Fail-safe: qualquer falha de biblioteca é recusa do arquivo, nunca anexo sem texto.
        try:
            yield
        except ExtracaoImpossivel:
            # [portar] Recusa com mensagem própria passa intacta.
            raise
        except Exception as erro:
            raise ExtracaoImpossivel(MENSAGEM_RECUSA) from erro

```

Dependências pelo `uv`: `python-docx`, `pdf2image` e `pytesseract` (o `pypdf` já é). Os pacotes
`tesseract-ocr`, `tesseract-ocr-por` e `poppler-utils` entram no `apt-get` de
`docker/Dockerfile.web`, junto com `ENV OMP_THREAD_LIMIT=1`: por padrão o tesseract abre uma thread
por núcleo e disputa a CPU com os outros requests do web.

**`apps/faq/models/arquivos.py`**

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

# Faq (apps/faq/models/conteudo.py) ganha:
anexos = models.ManyToManyField("faq.Anexo", blank=True, related_name="faqs")
```

**`apps/faq/anexos/recebimento.py`** — o recebimento dos arquivos, em dois tempos. `preparar_anexos`
roda fora de transação: confere o hash e extrai o texto só do arquivo que ainda não existe, e o OCR,
que pode levar minutos, não segura lock no banco. `gravar_anexos` roda dentro da transação do salvar e
só faz INSERT. A config sai dos settings como em `planta_config()` de
`apps/certidao_lancamento/emissao.py`.

```python
FAQ_ANEXO_TAMANHO_MAXIMO_BYTES: int = settings.FAQ_ANEXO_TAMANHO_MAXIMO_BYTES
FAQ_ANEXO_PAGINAS_MAXIMAS_OCR: int = settings.FAQ_ANEXO_PAGINAS_MAXIMAS_OCR
FAQ_ANEXO_PRAZO_OCR_S: float = settings.FAQ_ANEXO_PRAZO_OCR_S
FAQ_ANEXO_IDIOMA_OCR: str = settings.FAQ_ANEXO_IDIOMA_OCR
FAQ_ANEXO_DPI_OCR: int = settings.FAQ_ANEXO_DPI_OCR


class EnvioAnexo(BaseModel):
    nome_arquivo: str = Field(min_length=1, max_length=255)
    conteudo: bytes = Field(min_length=1)

    @computed_field
    @property
    def titulo(self) -> str:
        return Path(self.nome_arquivo).stem[:160]


class AnexoNovo(BaseModel):
    """Arquivo já extraído e ainda não gravado."""
    envio: EnvioAnexo
    hash_conteudo: str
    tipo: TipoDocumento
    texto: TextoExtraido


class AnexosPreparados(BaseModel):
    existentes: list[int] = []                # mesmo hash de um anexo já gravado: só se liga
    novos: list[AnexoNovo] = []


def extracao_config() -> ExtracaoConfig:
    return ExtracaoConfig(
        tamanho_maximo_bytes=FAQ_ANEXO_TAMANHO_MAXIMO_BYTES,
        paginas_maximas_ocr=FAQ_ANEXO_PAGINAS_MAXIMAS_OCR,
        prazo_ocr_s=FAQ_ANEXO_PRAZO_OCR_S,
        idioma_ocr=FAQ_ANEXO_IDIOMA_OCR,
        dpi_ocr=FAQ_ANEXO_DPI_OCR,
    )


def preparar_anexos(envios: list[EnvioAnexo]) -> AnexosPreparados:
    config = extracao_config()
    extrair_texto = ExtratorTexto(config)
    preparados = AnexosPreparados()
    for envio in envios:
        hash_conteudo = sha256(envio.conteudo).hexdigest()
        existente = (
            AnexoModel.objects.filter(hash_conteudo=hash_conteudo)
            .values_list("pk", flat=True)
            .first()
        )
        if existente is not None:
            # Mesmo arquivo, mesmo anexo. Título e texto do primeiro envio prevalecem.
            preparados.existentes.append(existente)
            continue
        try:
            tipo, texto = extrair_texto(envio.conteudo)
        except ExtracaoImpossivel as erro:
            # Com vários arquivos no mesmo salvar, a mensagem precisa dizer qual foi recusado.
            raise ExtracaoImpossivel(f"{envio.nome_arquivo}: {erro}") from erro
        preparados.novos.append(
            AnexoNovo(envio=envio, hash_conteudo=hash_conteudo, tipo=tipo, texto=texto)
        )
    return preparados


def gravar_anexos(preparados: AnexosPreparados, editor: Editor) -> list[int]:
    ids = list(preparados.existentes)
    for novo in preparados.novos:
        # get_or_create: o mesmo arquivo duas vezes no envio, ou gravado por outro salvar entre a
        # preparação e a transação, vira o mesmo anexo em vez de violar o unique do hash.
        registro, _ = AnexoModel.objects.get_or_create(
            hash_conteudo=novo.hash_conteudo,
            defaults={
                "titulo": novo.envio.titulo,
                "nome_arquivo": novo.envio.nome_arquivo,
                "tipo": novo.tipo,
                "arquivo": novo.envio.conteudo,
                "tamanho_bytes": len(novo.envio.conteudo),
                "texto": novo.texto.conteudo,
                "origem_texto": novo.texto.origem,
                "enviado_por_id": editor.perfil_id,
            },
        )
        ids.append(registro.pk)
    return ids
```

**O salvar da FAQ recebe os arquivos.** O `<form>` da FAQ ganha
`hx-encoding="multipart/form-data"`, e a view passa `request.FILES.getlist("novos_anexos")` para
`salvar_faq_nova` e `salvar_faq_existente` (`apps/faq/gestao/formularios.py`). A ordem dentro delas:

1. `ler_faq` valida o formulário. Se recusa, volta sem ler arquivo nenhum: erro de pergunta não custa
   um OCR.
2. `preparar_anexos` lê os arquivos. `ExtracaoImpossivel` vira recusa no controle `novos_anexos`, pelo
   mesmo `TradutorDeRecusa` de `_gravando` (skill `erros-de-formulario`), e nada foi gravado.
3. Numa só `transaction.atomic`: `gravar_anexos` grava os novos, os ids entram em `resposta.anexos`
   junto com os da lista, e `gravar_faq` ou `regravar_faq` grava a FAQ. Se a gravação da FAQ é
   recusada (pergunta ocupada), o rollback leva os anexos novos junto.

**A conferência ao escolher o arquivo.** O `<input type="file" name="novos_anexos" multiple>` tem
`hx-post` para `faq:admin_anexo_conferir`, com `hx-trigger="change"`,
`hx-encoding="multipart/form-data"` e `hx-params="novos_anexos"` (sem ele, o input dentro do `<form>`
mandaria o formulário inteiro). A view chama `ExtratorTexto.conferir` em cada arquivo e devolve, logo
abaixo do campo, uma linha por arquivo no mesmo estilo das linhas de anexo: nome, tipo, tamanho e um
selo com o veredito ("Entra ao salvar", "OCR ao salvar" ou "Recusado"), com a mensagem de
`ExtracaoImpossivel` ou o aviso do OCR embaixo do nome. Não grava nada e não consulta o
banco. O input também leva `hx-preserve` com `id` fixo: a resposta 422 do salvar substitui o
`<form>`, mas mantém o mesmo nó do input, com os arquivos escolhidos.

O mesmo input leva
`accept=".pdf,.docx,.doc,.odt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/msword,application/vnd.oasis.opendocument.text"`:
a extensão filtra o seletor no desktop, e o MIME é o que o seletor do celular entende. É só
conveniência; quem decide é a detecção pelos bytes.

**O vínculo é gravado com o formulário, como o das imagens em faq/004.** `gravar_faq` (faq/001) e
`regravar_faq` (faq/002) passam a sincronizar `registro.anexos` com `resposta.anexos`: os ids da
lista (um `<input type="hidden" name="anexo">` por linha) mais os ids que `gravar_anexos` acabou de
devolver. No sentido inverso, `faq_do_registro` (`apps/faq/conteudo/consulta.py`) passa a preencher
`resposta.anexos` com os ids ligados: sem isso a FAQ reaberta viria com a lista vazia, e salvar sem
mexer nela desligaria todos. Tirar da lista e salvar é o desligamento, e nenhuma rota grava, liga ou
desliga anexo fora do salvar. Um id de anexo da lista que não existe devolve erro no campo de anexos,
antes de qualquer extração.

**A lista é redesenhada no servidor, como os blocos de links e de relacionadas (faq/002).** O X de
uma linha e o clique num resultado da busca pedem `faq:admin_bloco_anexos` com os ids da lista e
`remover` ou `adicionar`; a rota devolve a tabela inteira, e o resultado da busca é limpo junto, por
OOB. A tabela é o único alvo: o campo de arquivo e a conferência, fora dela, não são tocados.

**`services/domain/faq/leitura/visibilidade.py`** — a regra do download, ao lado das de faq/001.

```python
def anexo_eh_baixavel(faqs_do_anexo: list[Faq], leitor: Leitor) -> bool:
    # O anexo não tem visibilidade própria: herda a da FAQ mais aberta a que está ligado.
    return any(eh_visivel(f, leitor) for f in faqs_do_anexo)
```

**Rotas** (`apps/faq/anexos/urls.py`): `faq:anexo_baixar` (aberta, decidida por `anexo_eh_baixavel`, `Content-Disposition:
attachment`), `faq:admin_anexo_conferir` (confere os arquivos
escolhidos, sem gravar), `faq:admin_anexo_buscar` (busca por título, em HTMX), `faq:admin_bloco_anexos` (a tabela de anexos redesenhada com um a mais ou a menos) e `faq:admin_anexo_texto` (o modal com o texto extraído, no poço de modal
da página de edição, fora do `<form>`). As quatro de administração ficam atrás de
`superusuario_requerido`.

## 7 · Caveats

**O OCR roda síncrono, dentro do request do salvar.** Fila é exceção a justificar (CLAUDE.md §3.5), e
o envio de anexo é raro. Três limites seguram o custo: o teto de páginas recusa antes de começar, a
rasterização página a página mantém uma página só na memória, e o prazo interrompe o OCR antes de
prender a thread por minutos. Enquanto o OCR roda, uma thread do web fica ocupada e o administrador
espera sem barra de progresso. O prazo vale por arquivo: vários PDFs escaneados no mesmo salvar somam
as esperas. Um documento maior que os limites precisa ser dividido antes do envio.

**O arquivo é lido duas vezes: na conferência e no salvar.** A conferência não grava nada, então o
salvar recebe os bytes de novo e extrai de novo. Para DOCX, ODT e PDF digital o custo é pequeno. O OCR
não roda na conferência: ela só confere o teto de páginas do PDF escaneado. Por isso a recusa de um
OCR (página em branco, prazo) só aparece no salvar. Aí o `hx-preserve` mantém os arquivos escolhidos,
mas o input não remove um arquivo só de uma escolha múltipla: o administrador escolhe de novo sem o
arquivo recusado.

**O texto extraído só se vê depois de gravado.** O arquivo recém-escolhido ainda não foi extraído (a
conferência não roda o OCR), então o botão do texto existe só nos anexos da lista. Quem quer conferir
o OCR de um PDF escaneado salva a FAQ e reabre; se o texto não presta, tira o anexo pelo X e salva de novo.

**O título do anexo novo é o nome do arquivo.** Um campo de título por arquivo pediria montar a lista
de arquivos escolhidos em JS. O administrador que quer um título bom nomeia o arquivo antes de enviar.

**O container web ganha tesseract e poppler.** O OCR exige binários do sistema, e um serviço separado
só para isso seria infraestrutura demais para o volume esperado. A imagem fica maior, e a suíte de OCR
roda só sob o marker `integration`, onde os binários existem.

**O DOC é recusado, não convertido.** Ler o formato binário do Word 97–2003 exige um programa externo
(`antiword`, sem manutenção, ou o LibreOffice, que põe centenas de MB na imagem). Quem tem um `.doc`
tem um editor que o salva como DOCX, então o custo passa para um gesto do administrador. O `.doc`
continua no seletor de arquivo para que a recusa explique o que fazer. A detecção é pela assinatura
OLE, então uma planilha XLS ou uma apresentação PPT recebem a mesma mensagem.

**O arquivo vive em `bytea`, junto do texto extraído.** É o padrão já adotado no acervo de documentos
emitidos: uma linha, uma transação, nenhum storage a operar. O banco cresce com os anexos, e o limite de
tamanho é o controle.

**Anexo reenviado mantém o título do primeiro envio.** A identidade é o conteúdo, e dois títulos para o
mesmo arquivo seriam o mesmo dado em dois lugares. O administrador que esperava renomear no reenvio não
consegue; renomear fica sem dono.

**Anexo desligado de todas as FAQs fica no banco.** Desligar não apaga, para o anexo continuar
disponível na busca. Não há tela de exclusão. Ele não baixa por ninguém (nenhuma FAQ visível), mas
ocupa espaço até existir a limpeza. Edição abandonada não gera esse caso: nada é gravado antes do
salvar.

**O download é aberto e herda a visibilidade das FAQs.** O anexo não tem visibilidade própria, então
ligar um anexo interno a uma FAQ pública o torna público. Quem decide é quem liga.

## 8 · Testes (TDD)
- `test_docx_rende_texto_de_paragrafos_e_tabelas` — o texto de uma célula de tabela aparece no
  extraído.
- `test_pdf_digital_usa_camada_de_texto` — `ExtratorPdf` com um OCR falso: sai
  `origem=camada_de_texto`, e o OCR falso não é chamado.
- `test_pdf_escaneado_passa_pelo_ocr` — um PDF-imagem com texto em português sai `origem=ocr`, com
  as palavras esperadas. *(marker `integration`)*
- `test_arquivo_sem_texto_eh_recusado` — PDF de página em branco levanta `ExtracaoImpossivel` com a
  mensagem de recusa. *(marker `integration`)*
- `test_falha_da_biblioteca_vira_recusa` — PDF corrompido levanta `ExtracaoImpossivel`, nunca
  outra exceção.
- `test_odt_rende_texto_de_paragrafos_e_tabelas` — sai `tipo=odt`, `origem=camada_de_texto`, e o
  texto de uma célula de tabela aparece no extraído.
- `test_doc_eh_recusado_com_pedido_de_docx` — um DOC levanta `ExtracaoImpossivel` com `MENSAGEM_DOC`.
- `test_extensao_mentirosa_eh_recusada` — parametrizado: um ZIP qualquer chamado `.docx`, uma planilha
  ODS chamada `.odt` e um texto chamado `.pdf` são recusados com
  `MENSAGEM_FORMATO`.
- `test_limites_recusam_antes_de_extrair` — tamanho acima do teto é recusado sem chamar o detector
  nem extrator nenhum; PDF escaneado acima do teto de páginas é recusado sem rasterizar página
  nenhuma. *(marker `integration`)*
- `test_conferencia_nao_roda_ocr` — `conferir` de um PDF escaneado dentro do teto devolve `ocr` sem
  rasterizar página nenhuma, e de um DOC devolve a recusa `MENSAGEM_DOC`. *(marker `integration`)*
- `test_rota_de_conferencia_nao_grava` — o POST de um arquivo bom e de um recusado em
  `faq:admin_anexo_conferir` devolve um item por arquivo, com a mensagem no recusado, e nenhum
  `Anexo` passa a existir. *(marker `banco`)*
- `test_ocr_que_passa_do_prazo_eh_recusado` — com `prazo_ocr_s` mínimo, um PDF escaneado de duas
  páginas levanta `ExtracaoImpossivel` com `MENSAGEM_PRAZO_OCR`. *(marker `integration`)*
- `test_reenvio_do_mesmo_arquivo_reaproveita_o_anexo` — duas FAQs salvas com o mesmo arquivo ficam
  ligadas ao mesmo `Anexo`, e a extração roda uma vez. *(marker `banco`)*
- `test_salvar_recusado_nao_grava_nada` — parametrizado: com um arquivo recusado, e com um arquivo bom
  numa FAQ cuja pergunta já é de outra, o POST devolve 422 e não sobra `Anexo` nem FAQ nova. No
  primeiro caso a mensagem está no campo `novos_anexos` com o nome do arquivo. *(marker `banco`)*
- `test_anexos_ligam_e_desligam_ao_salvar_a_faq` — uma FAQ nova salva com um arquivo novo fica ligada
  a ele; reaberta, salva sem mexer na lista, continua ligada; tirado pelo X e salvo, o vínculo some e o
  `Anexo` continua no banco. *(marker `banco`)*
- `test_texto_extraido_so_para_superusuario` — o GET de `faq:admin_anexo_texto` mostra o texto e a
  origem ao superusuário, dá 403 ao usuário comum e 404 a anexo inexistente. *(marker `banco`)*
- `test_download_segue_a_faq_mais_aberta` — parametrizado: ligado só a interna → 404 para anônimo; ligado
  também a pública → baixa; ligado só a rascunho → 404 para todos. *(marker `banco`)*
