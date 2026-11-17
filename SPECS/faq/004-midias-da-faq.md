---
spec: faq/004
versao: v1
atualizado_em: 2026-11-17
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC faq/004 — Mídias da resposta: imagens e vídeos MP4

## 1 · User story
O administrador do sistema ilustra as respostas da FAQ com imagens e vídeos MP4 (enviados diretamente
ou importados do YouTube) e o leitor os visualiza na resposta, para que fluxos visuais do sistema
sejam compreendidos sem depender apenas de texto.

## 2 · Condições de pronto
- [ ] O design da seção de mídias (imagens na resposta, player de vídeo abaixo do texto, entrada
      separada do YouTube e modal de metadados) foi aprovado no mock e as peças foram portadas para o
      tema e o styleguide antes de o template da aplicação usá-las.
- [ ] Imagens embutidas via markdown (`![legenda](/faq/midias/<id>/)`) aparecem formatadas dentro da
      largura da caixa de texto; SVG, `javascript:`, `data:` e `<script>` são recusados ou removidos.
- [ ] Vídeos ligados à resposta aparecem em player MP4 abaixo do texto, com suporte a busca na barra
      de tempo (`HTTP Range`).
- [ ] Arrastar e soltar (ou selecionar) imagem (PNG/JPEG/WebP) ou vídeo MP4 na edição abre o modal de
      metadados exigindo a legenda (e descrição opcional) antes de enviar; cancelar não envia nada, e
      arquivo ou legenda inválida devolve erro em português.
- [ ] Importar por link do YouTube tem campo próprio: baixa o vídeo como MP4 primeiro e, dando certo,
      abre o modal de metadados com o título sugerido na legenda; se o YouTube bloquear, falhar ou
      passar do limite, devolve erro em português orientando o envio manual em MP4.
- [ ] Apenas URLs válidas do YouTube (`youtube.com`, `youtu.be`, `youtube-nocookie.com`) são aceitas
      pelo importador; qualquer outro domínio ou esquema é recusado.
- [ ] Vídeos vinculados à FAQ podem ser reordenados e removidos na edição.
- [ ] Reenvio ou reimportação do mesmo arquivo (mesmo SHA-256) não duplica o binário no banco e inclui
      o administrador em `usuarios_upload`.
- [ ] Imagem ou vídeo MP4 ligado só a FAQ interna ou em rascunho dá 404 para quem não pode vê-la; na
      edição, o administrador vê prévia do que enviou e não consegue vincular mídia de rascunho de
      outro administrador.
- [ ] Editar a resposta removendo uma imagem do markdown desvincula a imagem da FAQ automaticamente.

## 3 · Domínio

A ontologia da FAQ e da `Resposta` é a de [faq/001 §3](001-pagina-de-faq.md#3--domínio), já com
`anexos` de [faq/003 §3](003-anexos-da-faq.md#3--domínio). Esta SPEC acrescenta mídias binárias
(`MidiaFaq`) e vídeos MP4 (`VideoFaq`) ligados à resposta — inclusive os importados do YouTube.

```python
class TipoMidia(StrEnum):
    IMAGEM = "imagem"                # PNG, JPEG ou WebP
    VIDEO_MP4 = "video_mp4"


class MidiaFaq(BaseModel):
    """Mídia ilustrativa guardada no sistema. A identidade do binário é o hash SHA-256."""
    id: int | None = None
    tipo: TipoMidia
    legenda: str = Field(min_length=3, max_length=200)
    descricao: str = Field(default="", max_length=500)
    content_type: str
    nome_arquivo: str
    hash_conteudo: str = Field(pattern=r"^[0-9a-f]{64}$")
    tamanho_bytes: int = Field(gt=0)
    usuarios_upload_ids: list[int] = []


class VideoFaq(BaseModel):
    """Vídeo MP4 exibido abaixo da resposta."""
    midia_id: int
    titulo: str | None = Field(default=None, max_length=120)
    ordem: int = 0


# ALTERADO nesta SPEC: `Resposta` (faq/003) ganha `videos` e `midias_referenciadas`.
class Resposta(BaseModel):
    markdown: str = Field(min_length=1)         # pode referenciar /faq/midias/<id>/
    links: list[LinkReferencia] = []
    anexos: list[int] = []
    videos: list[VideoFaq] = []                 # NOVO: vídeos MP4 abaixo do texto

    @field_validator("markdown", mode="before")
    @classmethod
    def _nao_vazia(cls, valor: str) -> str:
        if not valor or not valor.strip():
            raise ValueError("A resposta não pode ficar em branco.")
        return valor

    @computed_field
    @property
    def midias_referenciadas(self) -> list[int]:
        return extrair_ids_midia_markdown(self.markdown)
```

**Mock:** [004-mock-midias-da-faq.html](004-mock-midias-da-faq.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Embeddings multimodais de imagens e frames de vídeos MP4 — faq/005.
- Contenção de imagens e players dentro do painel do widget flutuante — faq/006.
- Limpeza de mídias órfãs (enviadas ou importadas e depois descartadas antes de salvar) — sem dono ainda.
- Importação de vídeos de outras plataformas externas além do YouTube — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/utils/markdown` → `RenderizadorMarkdown` (faq/001): estendido no §6 para liberar `<img>`.
- `@services/domain/faq/visibilidade.py` → `eh_visivel` (faq/001): base da regra de visibilidade da mídia.
- `@services/domain/faq/autoria.py` → `pode_editar` (faq/002): reuso e posse de mídia na edição.
- `@apps/faq/acesso.py` → `superusuario_requerido` (faq/002): portão das rotas de mídia/YouTube.
- `@apps/faq/anexos.py` → padrão de `bytea` deduplicado por SHA-256 (faq/003).
- `Pillow` (já é dependência) → conferência de integridade e formato real das imagens.
- Skills: `ontologia`, `erros-de-formulario`, `componentes-frontend`, `daisyui`, `htmx-skill`,
  `mock`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

> O comentário didático destes blocos existe só aqui e **não é portado** (CLAUDE.md §7.2).

**`docker/Dockerfile.web`** e **`pyproject.toml`** — o estágio web recebe `ffmpeg` no `apt-get` e
`yt-dlp` nas dependências para baixar e muxar vídeos do YouTube em MP4.

**`services/domain/faq/midia.py`** — validação pura de mídias, URLs de YouTube e extração de
referências (limites vêm do app a partir de `FAQ_IMAGEM_TAMANHO_MAXIMO_BYTES`, padrão 5 MB, e
`FAQ_VIDEO_TAMANHO_MAXIMO_BYTES`, padrão 50 MB).

```python
DOMINIOS_YOUTUBE = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "youtube-nocookie.com"})


def validar_url_youtube(url: str) -> str:
    # Bloqueia esquemas não-HTTP e qualquer domínio fora da lista para evitar SSRF no yt-dlp.
    analise = urlparse(url.strip())
    if analise.scheme not in {"http", "https"} or analise.hostname not in DOMINIOS_YOUTUBE:
        raise MidiaInvalida("Informe um link válido do YouTube.")
    return url.strip()


def validar_imagem(conteudo: bytes, limite_bytes: int) -> str:
    # Pillow `Image.open(...).verify()` confirma PNG/JPEG/WEBP; SVG e HTML são recusados (XSS).
    ...


def validar_video_mp4(conteudo: bytes, limite_bytes: int) -> str:
    if len(conteudo) == 0 or len(conteudo) > limite_bytes or conteudo[4:8] != b"ftyp":
        raise MidiaInvalida("Envie um arquivo de vídeo MP4 válido dentro do limite de tamanho.")
    return "video/mp4"


def extrair_ids_midia_markdown(texto: str) -> list[int]:
    # Percorre tokens `image` do MarkdownIt: ignora blocos de código e texto corrido.
    ...
```

**`services/integrations/youtube/downloader.py`** — adaptador externo (`CLAUDE.md` §6.2). O domínio
nunca importa `yt_dlp`.

```python
class DownloadYouTubeInput(BaseModel):
    url: str
    max_bytes: int = Field(gt=0)
    timeout_s: int = Field(default=60, gt=0)


class VideoYouTubeBaixado(BaseModel):
    titulo_sugerido: str
    nome_arquivo: str
    conteudo: bytes


class DownloadYouTubeFalhou(Exception):
    """Qualquer falha do yt-dlp (bloqueio, privado, timeout ou tamanho acima do limite)."""


class BaixarVideoYouTube:
    def __call__(self, entrada: DownloadYouTubeInput) -> VideoYouTubeBaixado:
        return self.pipeline(entrada)

    def pipeline(self, entrada: DownloadYouTubeInput) -> VideoYouTubeBaixado:
        # Opera em TemporaryDirectory: `merge_output_format="mp4"`, `noplaylist=True`,
        # `max_filesize=entrada.max_bytes`, `socket_timeout=entrada.timeout_s`.
        # Qualquer erro ou ausência de MP4 dentro do teto vira DownloadYouTubeFalhou.
        ...
```

**`services/utils/http/range.py`** — resolve o cabeçalho `HTTP Range: bytes=...` para streaming de
MP4 com `206 Partial Content` (ou `416 Range Not Satisfiable`).

**`services/utils/markdown/renderizador.py`** — estende o renderizador de faq/001 para liberar
`"img"` em `TAGS_PERMITIDAS` e `{"a": {"href", "title"}, "img": {"src", "alt", "title"}}` em
`attributes`. URLs relativas (`/faq/midias/...`) passam limpas enquanto `javascript:` e `data:` seguem
bloqueados.

**`services/domain/faq/visibilidade.py`** e **`services/domain/faq/autoria.py`** — estendem os dois
módulos de faq/001 e faq/002:

```python
def midia_eh_visivel(faqs_da_midia: list[Faq], leitor: Leitor) -> bool:
    return any(eh_visivel(f, leitor) for f in faqs_da_midia)


def pode_usar_midia(midia: MidiaFaq, faqs_ligadas: list[Faq], editor: Editor) -> bool:
    if editor.perfil_id in midia.usuarios_upload_ids:
        return True
    return any(f.situacao is Situacao.PUBLICADA and f.visibilidade is Visibilidade.PUBLICA for f in faqs_ligadas) or any(
        pode_editar(f.autor_id, editor) for f in faqs_ligadas
    )
```

**`apps/faq/models.py`**

```python
class MidiaFaq(models.Model):
    tipo = models.CharField(max_length=12, choices=TipoMidia.choices)
    legenda = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, default="")
    content_type = models.CharField(max_length=40)
    nome_arquivo = models.CharField(max_length=255)
    arquivo = models.BinaryField()
    hash_conteudo = models.CharField(max_length=64, unique=True)
    tamanho_bytes = models.PositiveIntegerField()
    usuarios_upload = models.ManyToManyField("user_admin.Perfil", blank=True, related_name="midias_faq")
    enviado_em = models.DateTimeField(auto_now_add=True)


class VideoFaq(models.Model):
    faq = models.ForeignKey(Faq, on_delete=models.CASCADE, related_name="videos")
    midia = models.ForeignKey(MidiaFaq, on_delete=models.PROTECT, related_name="videos_faq")
    titulo = models.CharField(max_length=120, blank=True, default="")
    ordem = models.PositiveSmallIntegerField(default=0)

# `Faq` ganha: midias = models.ManyToManyField(MidiaFaq, blank=True, related_name="faqs")
```

**`apps/faq/midia.py`** — upload local, importação via YouTube (baixa primeiro, depois modal) e
confirmação de metadados.

```python
def importar_youtube(url: str, editor: Editor, limites: LimitesMidia) -> MidiaFaqModel:
    url_limpa = validar_url_youtube(url)
    try:
        baixado = baixar_video_youtube(DownloadYouTubeInput(url=url_limpa, max_bytes=limites.video_max_bytes))
    except DownloadYouTubeFalhou as erro:
        raise MidiaInvalida("Não foi possível importar o vídeo do YouTube; envie o arquivo MP4 diretamente.") from erro
    envio = EnvioMidia(
        tipo=TipoMidia.VIDEO_MP4,
        legenda=(baixado.titulo_sugerido or "Vídeo importado do YouTube")[:200],
        nome_arquivo=baixado.nome_arquivo,
        conteudo=baixado.conteudo,
        limites=limites,
    )
    return receber_midia(envio, editor)


@transaction.atomic
def atualizar_metadados_midia(midia_id: int, legenda: str, descricao: str, editor: Editor) -> MidiaFaqModel:
    midia = get_object_or_404(MidiaFaqModel, pk=midia_id)
    if not midia.usuarios_upload.filter(pk=editor.perfil_id).exists():
        raise Http404
    midia.legenda = legenda
    midia.descricao = descricao
    midia.save(update_fields=["legenda", "descricao"])
    return midia
```

`receber_midia` deduplica por `(hash_conteudo, tipo)`, adicionando `editor.perfil_id` em
`usuarios_upload` quando o arquivo já existe. `gravar_faq` (faq/001) e `regravar_faq` (faq/002)
passam a validar `pode_usar_midia`, sincronizar `registro.midias` com
`resposta.midias_referenciadas` e recriar `VideoFaq` em ordem.

**Rotas e interface (`apps/faq/views.py` + `static/src/js/editor_markdown.js`):**

| Rota | Acesso | Comportamento |
|---|---|---|
| `faq:midia_exibir` | aberta / preview admin | checa `midia_eh_visivel` (ou `pode_usar_midia` para superusuário) e responde imagem ou MP4 com `HTTP Range` |
| `faq:admin_midia_enviar` | `superusuario_requerido` | recebe arquivo + `legenda` + `descricao` do modal de drag-and-drop; devolve partial HTML (`data-midia-url` para o Milkdown ou card do `VideoFaq`) |
| `faq:admin_youtube_importar` | `superusuario_requerido` | HTMX POST: baixa primeiro via `importar_youtube`; se falhar, devolve erro orientando subir MP4; se baixar, abre `#modal-midia-faq` com `midia_id` e título sugerido |
| `faq:admin_midia_metadados` | `superusuario_requerido` | HTMX POST do modal pós-YouTube: grava `legenda`/`descricao` e devolve o card do `VideoFaq` |

## 7 · Caveats

**O download do YouTube via `yt-dlp` depende de serviço externo sujeito a bloqueios anti-bot.** O
YouTube pode recusar IPs de servidor ou alterar o player, exigindo atualizações frequentes da lib. O
fluxo assume esse risco orientando o administrador a subir o MP4 manualmente sempre que a importação
falhar.

**Importar do YouTube roda síncrono na requisição HTTP, e o container `web` ganha `ffmpeg` e
`yt-dlp`.** Fila assíncrona é exceção (CLAUDE.md §3.5), e a importação acontece apenas na área do
administrador. O custo é o worker aguardar o download (limitado por timeout e `max_bytes`) e o aumento
da imagem web — reaproveitada pelo indexador em faq/005.

**Imagens e vídeos MP4 ficam em `bytea` no Postgres.** Guardar na linha segue o padrão de documentos
e anexos e evita operar storage externo na escala do sistema. O custo é ler o vídeo na memória do
worker durante o streaming `Range`, limitado por `FAQ_VIDEO_TAMANHO_MAXIMO_BYTES`.

**O vídeo baixado e descartado no modal ou a imagem removida do texto ficam órfãos no banco.** Não há
rotina de coleta de lixo ainda. Eles seguem inacessíveis ao público (`midia_eh_visivel` exige FAQ
visível vinculada) até existir limpeza.

**O drag-and-drop segura o `File` no navegador durante o modal e lê `data-midia-*` do partial HTML.**
Navegadores não permitem preencher `<input type="file">` por script após um drop, e retornar HTML em
vez de JSON preserva o HATEOAS do CLAUDE.md §3.1.

## 8 · Testes (TDD)
- `test_markdown_permite_imagem_e_barra_xss_e_svg` — `![legenda](/faq/midias/1/)` gera `<img>`,
  enquanto `<script>`, `onerror=`, `javascript:`, `data:` e upload de SVG são recusados.
- `test_validacao_imagem_e_mp4_pelos_bytes` — Pillow aceita PNG/JPEG/WebP e recusa falso positivo;
  MP4 exige box `ftyp` e limite de tamanho.
- `test_extrair_ids_midia_ignora_blocos_de_codigo` — links `/faq/midias/<id>/` dentro de cercas de
  código markdown não entram em `midias_referenciadas`.
- `test_url_youtube_bloqueia_outros_dominios_ssrf` — `youtube.com` e `youtu.be` passam; IP local,
  `file://` e outros domínios são recusados.
- `test_downloader_youtube_traduz_falha_e_respeita_tamanho` — erro de extrator, bloqueio e vídeo
  acima de `max_bytes` viram `DownloadYouTubeFalhou`.
- `test_midia_respeita_visibilidade_e_range_http` — imagem/MP4 ligada só a interna ou rascunho dá 404
  para anônimo; publicada entrega imagem e responde `206 Partial Content` com `Content-Range` no
  pedido `Range` do MP4. *(marker `banco`)*
- `test_upload_drag_and_drop_exige_legenda_deduplica_e_isola_rascunho` — envio sem `legenda` devolve
  erro em português; reenvio do mesmo arquivo inclui o segundo admin em `usuarios_upload`; mídia de
  rascunho de outro admin é recusada na gravação. *(marker `banco`)*
- `test_importar_youtube_grava_mp4_e_atualiza_metadados_no_modal` — `importar_youtube` grava a
  `MidiaFaq` com título sugerido e abre o modal; confirmar metadados atualiza `legenda` e `descricao`
  e bloqueia alteração por outro admin. *(marker `banco`)*
- `test_falha_no_youtube_orienta_subir_mp4_sem_gravar` — quando o downloader falha, a rota devolve o
  erro pedindo o envio do MP4 e nenhuma `MidiaFaq` é gravada. *(marker `banco`)*
- `test_editar_resposta_atualiza_vinculos_de_imagens_e_ordem_de_videos` — remover imagem do markdown
  desvincula `Faq.midias` e reordenar `VideoFaq` persiste na nova ordem. *(marker `banco`)*
