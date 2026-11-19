---
spec: faq/003
versao: v8
atualizado_em: 2026-11-19
testes_tdd: false
implementado: false
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
---

# SPEC faq/003 — Anexos da FAQ com texto extraído

## 1 · User story
O administrador do sistema anexa PDFs e DOCX às FAQs no contexto da edição, para que o leitor baixe o
documento de referência e para que o texto do documento fique disponível para a busca.

## 2 · Condições de pronto
- [ ] O design da seção de anexos (na edição e na resposta aberta da página) foi aprovado no mock e as
      peças foram portadas para o tema e o styleguide antes de o template da aplicação usá-las.
- [ ] Na edição, inclusive de uma FAQ que ainda não foi gravada, o administrador envia um PDF ou DOCX
      novo, ou escolhe um anexo já existente pelo título. O anexo entra marcado na lista do
      formulário e fica ligado à FAQ quando ela é salva.
- [ ] Só entra arquivo cujo texto possa ser extraído, inclusive por OCR. Arquivo sem texto aproveitável
      é recusado com a mensagem *"Só são aceitos documentos cujo texto possa ser extraído (inclusive
      por OCR)."*, e nada é gravado.
- [ ] PDF escaneado, sem camada de texto, passa pelo OCR em português e é aceito.
- [ ] Arquivo que não é PDF nem DOCX de verdade é recusado, mesmo com a extensão certa.
- [ ] Arquivo acima do limite de tamanho, ou PDF com mais páginas que o limite de OCR, é recusado antes
      de qualquer extração, com o limite na mensagem.
- [ ] Um OCR que passa do prazo é interrompido, e o arquivo é recusado com o pedido de dividir o PDF.
- [ ] Enviar de novo um arquivo idêntico não cria um segundo anexo: o existente entra na lista.
- [ ] A resposta aberta na página de FAQ lista os anexos para download. Um anexo só baixa se estiver
      ligado a pelo menos uma FAQ que o leitor pode ver; nos outros casos dá 404.
- [ ] Desmarcar um anexo e salvar a FAQ o desliga sem apagá-lo: ele continua disponível para as outras
      FAQs. Salvar sem mexer na lista mantém os anexos como estavam.

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
    anexos: list[int] = []                   # NOVO: ids de Anexo, marcados no formulário; o vínculo não tem atributos

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
- Excluir anexo órfão (sem FAQ) e a tela do acervo de anexos — sem dono ainda.
- Outros formatos documentais (ODT, planilhas) — sem dono ainda.
- Extração assíncrona, em fila — sem dono ainda.

## 5 · Peças de referência a compor
- `pypdf` (já é dependência) → leitura da camada de texto do PDF.
- `@apps/documentos/models.py` → `DocumentoEmitido.arquivo`: o padrão de PDF em `bytea` na linha.
- `@apps/faq/acesso.py` → `superusuario_requerido` (faq/002): portão do upload.
- `@services/domain/faq/leitura/visibilidade.py` → `eh_visivel` (faq/001): base da regra de download.
- Skills: `erros-de-formulario`, `componentes-frontend`, `daisyui`, `htmx-skill`, `mock`,
  `escrever-testes`, `test-django-views`.

## 6 · Snippets

> O comentário didático destes blocos existe só aqui e **não é portado** (CLAUDE.md §7.2).

**`services/utils/extracao_texto/models.py`** — os limites. `services/` não lê settings: o app monta
este DTO a partir de `FAQ_ANEXO_TAMANHO_MAXIMO_BYTES` (padrão 20 MB), `FAQ_ANEXO_PAGINAS_MAXIMAS_OCR`
(padrão 40) e `FAQ_ANEXO_PRAZO_OCR_S` (padrão 120) e o entrega ao construtor do extrator.

```python
class LimitesExtracao(BaseModel):
    tamanho_maximo_bytes: int = Field(gt=0)
    paginas_maximas_ocr: int = Field(gt=0)
    prazo_ocr_s: float = Field(gt=0)


MINIMO_CARACTERES_UTEIS = 40           # menos que isso é capa, carimbo ou ruído de OCR
IDIOMA_OCR = "por"
DPI_OCR = 200
MENSAGEM_PRAZO_OCR = "O OCR deste PDF passou do tempo limite. Divida o arquivo e envie as partes."
```

**`services/utils/extracao_texto/extrator.py`** — utilitário geral, sem domínio de FAQ. A falha é uma
exceção própria; o chamador nunca vê `pypdf`, `docx` nem `tesseract`.

```python
class ExtracaoImpossivel(Exception):
    """O arquivo não rende texto aproveitável. A mensagem é a que vai para o usuário."""


class ExtratorTexto:
    def __init__(self, limites: LimitesExtracao) -> None:
        self._limites = limites

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
        total_paginas = self._conferir_paginas_para_ocr(conteudo)
        return self._validar(self._ocr_pagina_a_pagina(conteudo, total_paginas), OrigemTexto.OCR)

    def _ocr_pagina_a_pagina(self, conteudo: bytes, total_paginas: int) -> str:
        prazo = monotonic() + self._limites.prazo_ocr_s
        paginas: list[str] = []
        for numero in range(1, total_paginas + 1):
            if monotonic() > prazo:
                raise ExtracaoImpossivel(MENSAGEM_PRAZO_OCR)
            # Uma página por vez, em tons de cinza: a memória fica em uma página (~4 MB a 200 dpi),
            # e não nas 40 de uma vez.
            imagem = _rasterizar_pagina(conteudo, numero, DPI_OCR)
            paginas.append(_ocr_imagem(imagem, IDIOMA_OCR))
        return "\n".join(paginas)

    def _validar(self, texto: str, origem: OrigemTexto) -> TextoExtraido:
        if _uteis(texto) < MINIMO_CARACTERES_UTEIS:
            raise ExtracaoImpossivel(MENSAGEM_RECUSA)
        return TextoExtraido(conteudo=texto, origem=origem)
```

OCR: `pdf2image` (poppler) rasteriza a página (`first_page`/`last_page` iguais, `grayscale=True`), e
`pytesseract` (tesseract com `por`) lê a imagem. DOCX: `python-docx`, parágrafos e células de tabela.
Os pacotes `tesseract-ocr`, `tesseract-ocr-por` e `poppler-utils` entram no `apt-get` de
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

**`apps/faq/anexos/recebimento.py`** — o upload: hash primeiro, extração só se o arquivo é novo. O upload não
liga o anexo a FAQ nenhuma.

```python
@transaction.atomic
def receber_anexo(envio: EnvioAnexo, editor: Editor) -> AnexoModel:
    conteudo = envio.conteudo
    hash_conteudo = sha256(conteudo).hexdigest()
    existente = AnexoModel.objects.filter(hash_conteudo=hash_conteudo).first()
    if existente is not None:
        # Mesmo arquivo, mesmo anexo. Título e texto do primeiro envio prevalecem.
        return existente
    tipo, texto = extrair_texto(conteudo)            # ExtracaoImpossivel sobe antes de qualquer INSERT
    return AnexoModel.objects.create(
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
```

A view captura `ExtracaoImpossivel` e devolve o `<form>` com a mensagem no campo do arquivo (skill
`erros-de-formulario`). No sucesso, devolve o item da lista de anexos do formulário: um checkbox
`anexos` marcado, com o título.

**O vínculo é gravado com o formulário, como o das imagens em faq/004.** `gravar_faq` (faq/001) e
`regravar_faq` (faq/002) passam a sincronizar `registro.anexos` com `resposta.anexos`, que vem dos
checkboxes marcados. Assim a FAQ nova recebe anexo antes da primeira gravação, desmarcar e salvar é o
desligamento, e nenhuma rota liga ou desliga anexo fora do formulário. Um id de anexo que não existe
devolve erro no campo de anexos, antes da gravação.

**`services/domain/faq/leitura/visibilidade.py`** — a regra do download, ao lado das de faq/001.

```python
def anexo_eh_baixavel(faqs_do_anexo: list[Faq], leitor: Leitor) -> bool:
    # O anexo não tem visibilidade própria: herda a da FAQ mais aberta a que está ligado.
    return any(eh_visivel(f, leitor) for f in faqs_do_anexo)
```

**Rotas** (`apps/faq/anexos/urls.py`): `faq:anexo_baixar` (aberta, decidida por `anexo_eh_baixavel`, `Content-Disposition:
attachment`), `faq:admin_anexo_enviar` (devolve o item da lista), `faq:admin_anexo_buscar` (busca por
título, em HTMX) e `faq:admin_anexo_item` (o item da lista de um anexo escolhido na busca, acrescentado
com `hx-swap="beforeend"`). As três de administração ficam atrás de `superusuario_requerido`.

## 7 · Caveats

**O OCR roda síncrono, dentro do request do upload.** Fila é exceção a justificar (CLAUDE.md §3.5), e
o envio de anexo é raro. Três limites seguram o custo: o teto de páginas recusa antes de começar, a
rasterização página a página mantém uma página só na memória, e o prazo interrompe o OCR antes de
prender a thread por minutos. Enquanto o OCR roda, uma thread do web fica ocupada e o administrador
espera sem barra de progresso. Um documento maior que os limites precisa ser dividido antes do envio.

**O container web ganha tesseract e poppler.** O OCR exige binários do sistema, e um serviço separado
só para isso seria infraestrutura demais para o volume esperado. A imagem fica maior, e a suíte de OCR
roda só sob o marker `integration`, onde os binários existem.

**O arquivo vive em `bytea`, junto do texto extraído.** É o padrão já adotado no acervo de documentos
emitidos: uma linha, uma transação, nenhum storage a operar. O banco cresce com os anexos, e o limite de
tamanho é o controle.

**Anexo reenviado mantém o título do primeiro envio.** A identidade é o conteúdo, e dois títulos para o
mesmo arquivo seriam o mesmo dado em dois lugares. O administrador que esperava renomear no reenvio não
consegue; renomear fica sem dono.

**Anexo órfão fica no banco.** Desligar não apaga, e o anexo enviado numa edição que não foi salva
também fica sem FAQ. Não há tela de exclusão. Ele não baixa por ninguém (nenhuma FAQ visível), mas
ocupa espaço até existir a limpeza.

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
- `test_ocr_que_passa_do_prazo_eh_recusado` — com `prazo_ocr_s` mínimo, um PDF escaneado de duas
  páginas levanta `ExtracaoImpossivel` com `MENSAGEM_PRAZO_OCR`. *(marker `integration`)*
- `test_reenvio_do_mesmo_arquivo_reaproveita_o_anexo` — dois envios do mesmo arquivo devolvem o mesmo
  `Anexo`, e a extração roda uma vez. *(marker `banco`)*
- `test_upload_recusado_nao_grava_nada` — nenhum `Anexo` depois da recusa. *(marker `banco`)*
- `test_anexos_ligam_e_desligam_ao_salvar_a_faq` — uma FAQ nova salva com um anexo marcado fica
  ligada a ele; reaberta, salva sem mexer na lista, continua ligada; desmarcado e salvo, o vínculo
  some e o `Anexo` continua no banco. *(marker `banco`)*
- `test_download_segue_a_faq_mais_aberta` — parametrizado: ligado só a interna → 404 para anônimo; ligado
  também a pública → baixa; ligado só a rascunho → 404 para todos. *(marker `banco`)*
