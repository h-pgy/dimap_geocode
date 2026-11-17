---
spec: faq/005
versao: v1
atualizado_em: 2026-11-17
testes_tdd: false
implementado: false
markers_obrigatorios: [banco, integration]
changelog:
  - v1: versão inicial
---

# SPEC faq/005 — Índice semântico da FAQ (EmbeddingGemma 2 + pgvector)

## 1 · User story
**Requisito não-funcional** — toda FAQ publicada, todo anexo e toda mídia própria (imagens e frames
de vídeos MP4) ganham representação vetorial no mesmo espaço semântico, atualizada sozinha depois de
cada edição. É a base da busca em texto livre de faq/007.

## 2 · Condições de pronto
- [ ] `docker compose up` sobe o Postgres com a extensão `vector`, o serviço `ollama` com a variante
      de visão do `embeddinggemma-2` já baixada e o serviço `indexador`. O `web` sobe e serve a FAQ
      mesmo com o `ollama` fora do ar.
- [ ] Uma FAQ criada ou editada fica indexada em até um intervalo do indexador (padrão 30 s), sem
      nenhuma ação do administrador.
- [ ] O índice de uma FAQ cobre a FAQ inteira (pergunta, tema, subtema, resposta sem URLs de mídia,
      títulos de vídeos e palavras-chave) e também cada formulação (pergunta e variações)
      separadamente.
- [ ] O texto de cada anexo é dividido em trechos, e cada trecho é indexado.
- [ ] Cada imagem ligada a FAQ publicada ganha um vetor multimodal (imagem + legenda/descrição), e
      cada vídeo MP4 (inclusive importado do YouTube) ganha vetores dos seus frames-chave amostrados
      e dos metadados.
- [ ] Renomear um tema reindexa as FAQs daquele tema. FAQ, anexo ou mídia sem mudança não dispara
      chamada ao `ffmpeg` nem ao modelo.
- [ ] Trocar o modelo de embedding na configuração reindexa tudo no ciclo seguinte.
- [ ] Com o `ollama` fora do ar, o indexador registra a falha, não grava índice pela metade e retoma
      sozinho quando o serviço volta.
- [ ] `manage.py buscar_faq "texto"` lista as FAQs mais próximas (inclusive por anexo, imagem ou vídeo
      MP4), respeitando a visibilidade de quem pergunta (`--autenticado`). Rascunho nunca aparece.

## 3 · Domínio

A ontologia da FAQ é a de [faq/001](001-pagina-de-faq.md#3--domínio), a do anexo é a de
[faq/003](003-anexos-da-faq.md#3--domínio) e a das mídias é a de [faq/004](004-midias-da-faq.md#3--domínio).
Esta SPEC pergunta a elas que conteúdo (textual ou visual) representa cada uma no espaço vetorial. O
índice é **derivado**: tudo nele pode ser reconstruído a partir das FAQs, dos anexos e das mídias.

```python
class OrigemTrecho(StrEnum):
    FAQ_INTEIRA = "faq_inteira"          # pergunta + tema + resposta + títulos de vídeo + palavras-chave
    FORMULACAO = "formulacao"            # uma pergunta ou variação, sozinha
    ANEXO = "anexo"                      # um pedaço do texto extraído do anexo
    IMAGEM = "imagem"                    # imagem MidiaFaq (visual + legenda e descrição)
    VIDEO_FRAME = "video_frame"          # frame-chave amostrado de um vídeo MP4
    VIDEO_METADADO = "video_metadado"    # legenda e descrição do vídeo MP4


class TrechoIndexavel(BaseModel):
    """Unidade que vira um vetor. A identidade é o hash: muda texto, mídia ou modelo, muda o vetor."""
    origem: OrigemTrecho
    faq_id: int | None = None
    anexo_id: int | None = None
    midia_id: int | None = None
    posicao: int = 0                     # ordem do trecho (no anexo) ou do frame (no vídeo MP4)
    titulo: str                          # usado no prompt textual quando aplicável
    texto: str = ""
    midia_hash: str | None = None        # sha256 da MidiaFaq quando há componente visual
    imagem_bytes: bytes | None = None    # bytes da imagem ou do frame JPEG; não persiste no índice

    @model_validator(mode="after")
    def _uma_ponta_e_conteudo(self) -> Self:
        pontas = sum(p is not None for p in (self.faq_id, self.anexo_id, self.midia_id))
        if pontas != 1:
            raise ValueError("O trecho pertence a exatamente uma ponta (FAQ, anexo ou mídia).")
        if not self.texto and self.imagem_bytes is None:
            raise ValueError("O trecho precisa de texto ou imagem para gerar embedding.")
        return self

    def hash_para(self, modelo: ModeloEmbedding) -> str:
        identidade = (
            f"{modelo.nome}|{modelo.dimensoes}|{self.origem}|{self.posicao}"
            f"|{self.midia_hash or ''}|{self.prompt_texto()}"
        )
        return sha256(identidade.encode()).hexdigest()

    def prompt_texto(self) -> str:
        if self.imagem_bytes is not None:
            return self.texto
        return PROMPT_DOCUMENTO.format(titulo=self.titulo, texto=self.texto)


class ModeloEmbedding(BaseModel):
    nome: str                            # tag Ollama com visão, ex.: "embeddinggemma-2"
    dimensoes: int = Field(gt=0)         # 768, a dimensão nativa unificada


class FaqSemelhante(BaseModel):
    faq_id: int
    distancia: float = Field(ge=0)       # cosseno; menor = mais próximo
    origem: OrigemTrecho                 # de onde veio o trecho mais próximo
    anexo_id: int | None = None          # quando a proximidade veio de um anexo
    midia_id: int | None = None          # quando a proximidade veio de imagem ou vídeo MP4
```

## 4 · Fora de escopo
- A caixa de busca, o registro das buscas e o painel de sugestões — faq/007.
- Indexar FAQ em rascunho para a pré-visualização da busca — sem dono ainda; o indexador cobre só
  as publicadas.
- Reduzir a dimensão (MRL 512/256/128) para economizar espaço — sem dono ainda.
- Transcrição ou embedding da trilha de áudio dos vídeos MP4 e de imagens internas de PDFs — sem
  dono ainda.

## 5 · Peças de referência a compor
- `@services/utils/markdown` (faq/001) → o parser markdown-it, para tirar o markdown da resposta.
- `@services/domain/faq/visibilidade.py` → `visibilidades_para` (faq/001): filtro da busca.
- `@apps/faq/models.py` → `Faq`, `Formulacao`, `Tema`, `Anexo`, `MidiaFaq`, `VideoFaq` (faq/001,
  faq/003 e faq/004).
- `requests` (já é dependência) → transporte do cliente Ollama.
- `@docker/Dockerfile.web` → imagem base compartilhada com `ffmpeg` (introduzido em faq/004).
- `@docker/Dockerfile.daemon` e o serviço `daemon` do compose → padrão de processo fora do web.
- Skills: `management-commands`, `escrever-testes`.

## 6 · Snippets

> O comentário didático destes blocos existe só aqui e **não é portado** (CLAUDE.md §7.2).

**`docker-compose.yml`**

```yaml
  db:
    build:
      context: .
      dockerfile: docker/Dockerfile.db      # postgis/postgis:17-3.5 + postgresql-17-pgvector

  ollama:
    image: ollama/ollama
    entrypoint: ["/bin/sh", "/scripts/ollama-entrypoint.sh"]   # `serve` + `pull` do modelo se faltar
    environment:
      # Variante com visão do EmbeddingGemma 2 (ex.: 440M texto+visão ou 740M multimodal completo).
      OLLAMA_MODELO_EMBEDDING: ${OLLAMA_MODELO_EMBEDDING:-embeddinggemma-2}
    volumes:
      - ollama_modelos:/root/.ollama
      - ./docker/ollama-entrypoint.sh:/scripts/ollama-entrypoint.sh:ro
    healthcheck:
      # Saudável só quando o modelo está baixado: o indexador não começa antes disso.
      test: ["CMD-SHELL", "ollama show $${OLLAMA_MODELO_EMBEDDING} > /dev/null"]
      interval: 10s
      retries: 60

  indexador:
    build:
      context: .
      dockerfile: docker/Dockerfile.web
    command: ["python", "manage.py", "indexar_faq", "--continuo"]
    environment: *ambiente-django          # mesmas variáveis de banco do web + OLLAMA_URL
    depends_on:
      db:
        condition: service_healthy
      ollama:
        condition: service_healthy
  # O `web` NÃO depende do `ollama`: a FAQ funciona sem índice.

volumes:
  ollama_modelos:
```

**`config/settings.py`** — configuração lida pelo Pydantic Settings e entregue a `services/` por DTO.

```python
OLLAMA_URL = _env.ollama_url                                   # http://ollama:11434
FAQ_MODELO_EMBEDDING = ModeloEmbedding(nome=_env.ollama_modelo_embedding, dimensoes=768)
FAQ_INDEXADOR_INTERVALO_S = _env.faq_indexador_intervalo_s     # 30
FAQ_MAX_FRAMES_VIDEO = _env.faq_max_frames_video               # 8
```

**`services/integrations/ollama/cliente.py`** — o adaptador multimodal. O domínio nunca vê
`requests` nem base64.

```python
class EntradaEmbedding(BaseModel):
    texto: str | None = None
    imagem_bytes: bytes | None = None

    @model_validator(mode="after")
    def _nao_vazia(self) -> Self:
        if self.texto is None and self.imagem_bytes is None:
            raise ValueError("Entrada de embedding exige texto ou imagem.")
        return self


class PedidoEmbedding(BaseModel):
    modelo: ModeloEmbedding
    entradas: list[EntradaEmbedding] = Field(min_length=1)


class OllamaIndisponivel(Exception): ...        # rede, timeout, 5xx
class OllamaRespostaInvalida(Exception): ...    # JSON inesperado, dimensão errada


class ClienteEmbeddingOllama:
    def __init__(self, config: ConfigOllama) -> None:
        self._config = config

    def __call__(self, pedido: PedidoEmbedding) -> list[list[float]]:
        return self.pipeline(pedido)

    def pipeline(self, pedido: PedidoEmbedding) -> list[list[float]]:
        corpo = self._requisitar(pedido)
        return self._validar(corpo, pedido)

    def _serializar_entrada(self, item: EntradaEmbedding) -> dict[str, str]:
        bloco: dict[str, str] = {}
        if item.texto is not None:
            bloco["text"] = item.texto
        if item.imagem_bytes is not None:
            bloco["image"] = b64encode(item.imagem_bytes).decode("ascii")
        return bloco

    def _requisitar(self, pedido: PedidoEmbedding) -> dict[str, Any]:
        payload = {
            "model": pedido.modelo.nome,
            "input": [self._serializar_entrada(e) for e in pedido.entradas],
            "truncate": True,
        }
        try:
            resposta = requests.post(f"{self._config.url}/api/embed", json=payload, timeout=self._config.timeout_s)
            resposta.raise_for_status()
        except requests.RequestException as erro:
            raise OllamaIndisponivel(str(erro)) from erro
        return resposta.json()

    def _validar(self, corpo: dict[str, Any], pedido: PedidoEmbedding) -> list[list[float]]:
        vetores = corpo.get("embeddings")
        # Modelo trocado no servidor sem trocar a config estragaria o índice em silêncio.
        if not isinstance(vetores, list) or len(vetores) != len(pedido.entradas) or any(
            len(v) != pedido.modelo.dimensoes for v in vetores
        ):
            raise OllamaRespostaInvalida("Resposta do Ollama fora do contrato.")
        return vetores
```

**`services/utils/extracao_frames/extrator.py`** — utilitário geral sem domínio. Amostra até
`max_frames` imagens JPEG distribuídas ao longo da duração do MP4 usando `ffmpeg` / `ffprobe` em
diretório temporário.

**`services/domain/faq/indexacao.py`** — que conteúdo representa o quê. O domínio depende de uma
porta, não do Ollama.

```python
# Formato de prompt do EmbeddingGemma: documento e consulta são prefixados de jeitos diferentes.
# A conferência contra o card do EmbeddingGemma 2 fica para a retomada desta SPEC.
PROMPT_DOCUMENTO = "title: {titulo} | text: {texto}"
PROMPT_CONSULTA = "task: search result | query: {consulta}"


class GeradorEmbedding(Protocol):
    def __call__(self, pedido: PedidoEmbedding) -> list[list[float]]: ...


def trechos_da_faq(faq: Faq) -> list[TrechoIndexavel]:
    caminho_tema = " › ".join(_ancestrais(faq.tema))            # "Busca › Endereço"
    titulos_videos = ", ".join(v.titulo for v in faq.resposta.videos if v.titulo)
    # `markdown_para_texto` mantém texto `alt` de imagens e descarta URLs internas `/faq/midias/...`.
    partes = [
        caminho_tema,
        markdown_para_texto(faq.resposta.markdown),
        titulos_videos,
        ", ".join(faq.palavras_chave),
    ]
    inteira = TrechoIndexavel(
        origem=OrigemTrecho.FAQ_INTEIRA,
        faq_id=faq.id,
        titulo=faq.pergunta.texto,
        texto="\n".join(p for p in partes if p),
    )
    formulacoes = [
        TrechoIndexavel(origem=OrigemTrecho.FORMULACAO, faq_id=faq.id, titulo="none", texto=f.texto)
        for f in [faq.pergunta, *faq.variacoes]
    ]
    return [inteira, *formulacoes]


def trecho_da_imagem(midia: MidiaFaq, imagem_bytes: bytes) -> TrechoIndexavel:
    legenda_e_desc = "\n".join(p for p in (midia.legenda, midia.descricao) if p)
    return TrechoIndexavel(
        origem=OrigemTrecho.IMAGEM,
        midia_id=midia.id,
        titulo=midia.legenda,
        texto=legenda_e_desc,
        midia_hash=midia.hash_conteudo,
        imagem_bytes=imagem_bytes,
    )


def trechos_do_video_mp4(midia: MidiaFaq, frames: list[bytes]) -> list[TrechoIndexavel]:
    metadado = TrechoIndexavel(
        origem=OrigemTrecho.VIDEO_METADADO,
        midia_id=midia.id,
        titulo=midia.legenda,
        texto="\n".join(p for p in (midia.legenda, midia.descricao) if p),
        midia_hash=midia.hash_conteudo,
    )
    trechos_frames = [
        TrechoIndexavel(
            origem=OrigemTrecho.VIDEO_FRAME,
            midia_id=midia.id,
            posicao=i,
            titulo=midia.legenda,
            texto=midia.legenda,
            midia_hash=midia.hash_conteudo,
            imagem_bytes=frame,
        )
        for i, frame in enumerate(frames)
    ]
    return [metadado, *trechos_frames]
```

**`services/domain/faq/trechos.py`** — divisão do texto do anexo.

```python
TAMANHO_TRECHO = 1200          # caracteres; folga ampla dentro da janela de contexto do modelo
SOBREPOSICAO = 200             # a frase cortada na borda aparece inteira em um dos dois lados


def trechos_do_anexo(anexo: Anexo) -> list[TrechoIndexavel]:
    # Corta preferindo fim de parágrafo, depois fim de frase, e só então no meio da palavra.
    pedacos = dividir_com_sobreposicao(anexo.texto.conteudo, TAMANHO_TRECHO, SOBREPOSICAO)
    return [
        TrechoIndexavel(origem=OrigemTrecho.ANEXO, anexo_id=anexo.id, posicao=i, titulo=anexo.titulo, texto=p)
        for i, p in enumerate(pedacos)
    ]
```

**`services/domain/faq/reconciliacao.py`** — o coração do indexador. Não há fila nem sinal: a cada
ciclo, o que **deveria** estar indexado é comparado, por hash, com o que **está**.

```python
class PlanoReconciliacao(BaseModel):
    a_gerar: list[TrechoIndexavel]       # hash desejado ausente do banco
    a_remover: list[str]                 # hash no banco que ninguém mais deseja


def planejar(desejados: list[TrechoIndexavel], existentes: set[str], modelo: ModeloEmbedding) -> PlanoReconciliacao:
    por_hash = {t.hash_para(modelo): t for t in desejados}
    return PlanoReconciliacao(
        a_gerar=[t for h, t in por_hash.items() if h not in existentes],
        a_remover=sorted(existentes - por_hash.keys()),
    )
```

**`apps/faq/indexador.py`** — a orquestração com o banco. Uma transação por FAQ, por anexo e por
mídia: se o Ollama cai no meio, cada unidade fica inteira no estado antigo ou inteira no novo.

```python
def ciclo(gerador: GeradorEmbedding, modelo: ModeloEmbedding, max_frames: int) -> ResumoCiclo:
    for faq in faqs_publicadas_como_dto():                    # rascunho sai do índice
        _reconciliar(trechos_da_faq(faq), TrechoModel.objects.filter(faq_id=faq.id), gerador, modelo)
    for anexo in anexos_ligados_a_publicadas_como_dto():
        _reconciliar(trechos_do_anexo(anexo), TrechoModel.objects.filter(anexo_id=anexo.id), gerador, modelo)
    for midia in midias_ligadas_a_publicadas_como_dto():
        _reconciliar_midia(midia, gerador, modelo, max_frames)
    _remover_trechos_orfaos_ou_rascunho()


def _reconciliar_midia(midia_row, gerador, modelo, max_frames) -> None:
    existentes_qs = TrechoModel.objects.filter(midia_id=midia_row.id)
    # Para MP4, confere antes pelo hash do metadado + modelo: evita rodar ffmpeg em vídeo inalterado.
    if midia_row.tipo == TipoMidia.VIDEO_MP4 and _video_ja_atualizado(midia_row, existentes_qs, modelo):
        return
    desejados = _trechos_para_midia(midia_row, max_frames)
    _reconciliar(desejados, existentes_qs, gerador, modelo)
```

O comando `indexar_faq --continuo` chama `ciclo` em laço, dorme `FAQ_INDEXADOR_INTERVALO_S` e, diante
de `OllamaIndisponivel`, registra no log e tenta de novo no ciclo seguinte, sem sair do processo.

**`apps/faq/models.py`**

```python
class TrechoIndexado(models.Model):
    origem = models.CharField(max_length=16, choices=OrigemTrecho.choices)
    faq = models.ForeignKey(Faq, on_delete=models.CASCADE, null=True, related_name="trechos")
    anexo = models.ForeignKey(Anexo, on_delete=models.CASCADE, null=True, related_name="trechos")
    midia = models.ForeignKey(MidiaFaq, on_delete=models.CASCADE, null=True, related_name="trechos")
    posicao = models.PositiveIntegerField(default=0)
    texto = models.TextField()
    modelo = models.CharField(max_length=80)
    hash_fonte = models.CharField(max_length=64)
    vetor = VectorField(dimensions=768)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(faq__isnull=False, anexo__isnull=True, midia__isnull=True)
                    | Q(faq__isnull=True, anexo__isnull=False, midia__isnull=True)
                    | Q(faq__isnull=True, anexo__isnull=True, midia__isnull=False)
                ),
                name="faq_trecho_uma_ponta",
            ),
            # Três índices parciais porque NULL ≠ NULL no Postgres impede UNIQUE único com FKs nulas.
            models.UniqueConstraint("faq", "hash_fonte", condition=Q(faq__isnull=False), name="faq_trecho_hash_faq"),
            models.UniqueConstraint("anexo", "hash_fonte", condition=Q(anexo__isnull=False), name="faq_trecho_hash_anexo"),
            models.UniqueConstraint("midia", "hash_fonte", condition=Q(midia__isnull=False), name="faq_trecho_hash_midia"),
        ]
        indexes = [
            HnswIndex(name="faq_trecho_vetor_hnsw", fields=["vetor"], opclasses=["vector_cosine_ops"]),
        ]
```

A primeira migração do app nesta SPEC é `VectorExtension()` (do pacote `pgvector`).

**`apps/faq/semantica.py`** — a consulta que faq/007 consome. A visibilidade entra no SQL, por junção, e
não é copiada para a linha do trecho.

```python
def buscar_semelhantes(consulta: str, leitor: Leitor, k: int, gerador: GeradorEmbedding, modelo: ModeloEmbedding) -> list[FaqSemelhante]:
    entrada = EntradaEmbedding(texto=PROMPT_CONSULTA.format(consulta=consulta))
    vetor = gerador(PedidoEmbedding(modelo=modelo, entradas=[entrada]))[0]
    visiveis = Q(situacao=Situacao.PUBLICADA, visibilidade__in=visibilidades_para(leitor))
    faqs_visiveis = FaqModel.objects.filter(visiveis)
    candidatos = (
        TrechoModel.objects.filter(modelo=modelo.nome)
        .filter(
            Q(faq__in=faqs_visiveis)
            | Q(anexo__faqs__in=faqs_visiveis)
            | Q(midia__faqs__in=faqs_visiveis)
            | Q(midia__videos_faq__faq__in=faqs_visiveis)
        )
        .annotate(distancia=CosineDistance("vetor", vetor))
        .order_by("distancia")[: k * FATOR_CANDIDATOS]
    )
    # Um trecho de anexo ou mídia aponta para várias FAQs: o domínio expande e fica com o melhor por FAQ.
    return melhor_por_faq(_como_ocorrencias(candidatos, faqs_visiveis), k)    # services/domain/faq/ranking.py
```

## 7 · Caveats

**O compose ganha dois serviços e o banco passa a ter imagem própria.** O `postgis/postgis` não traz
`pgvector`, e o modelo exige um runtime próprio; o `indexador` reaproveita o `Dockerfile.web` (que já
inclui `ffmpeg` desde faq/004). O custo é a RAM do Ollama (~2–3 GB com a variante de visão carregada)
e manter `Dockerfile.db` na atualização do PostGIS.

**Vídeos MP4 são representados por frames amostrados e metadados textuais, sem transcrição de áudio.**
O `/api/embed` do Ollama não processa `.mp4` bruto diretamente, então amostrar até 8 frames cobre
telas e demonstrações visuais sem explodir o número de vetores. Falas do vídeo que não apareçam
visualmente nem na legenda/descrição ficam fora da busca.

**O indexador reconcilia por varredura periódica, sem fila nem sinal.** A varredura por hash pega
também o que nenhum evento de FAQ avisaria, como a renomeação de um tema, e sinal está vedado pelo
CLAUDE.md §3.2. O custo é uma latência de até um intervalo, e cada ciclo percorre todas as FAQs
publicadas, O(n), que é aceitável para centenas de FAQs.

**O texto do trecho é copiado para a tabela do índice.** É o que permite mostrar o trecho do anexo que
casou e calcular o hash sem reler a fonte. Entre a edição e o próximo ciclo, o índice descreve a versão
anterior da FAQ.

**A dimensão do vetor está fixa na migração.** O `VectorField` precisa da dimensão no schema. Trocar
para um modelo de outra dimensão exige migração nova e reindexação total; só o nome do modelo (mesma
dimensão) troca pela configuração.

**O formato do prompt depende do modelo.** Os prefixos `title:`/`task:` são os do EmbeddingGemma e
precisam ser conferidos para a versão 2. Trocar de família de modelo exige revisar os prompts junto, e
o hash garante a reindexação.

**A tag exata de visão do `embeddinggemma-2` no Ollama é configuração a confirmar na retomada.** Antes
de escrever os testes de integração, valida-se o nome exato da tag com suporte a visão e a dimensão
nativa.

**O índice HNSW é aproximado.** Para o volume esperado a perda de recall é desprezível, e a busca exata
exigiria varrer a tabela. Um resultado muito próximo pode, raramente, ficar de fora.

## 8 · Testes (TDD)
- `test_trechos_da_faq_cobrem_a_faq_e_cada_formulacao` — 1 trecho inteiro + 1 por formulação. O
  inteiro traz `Tema › Subtema`, a resposta sem sintaxe markdown, `alt` de imagens (sem `/faq/midias/`),
  títulos de vídeos e palavras-chave.
- `test_trechos_do_anexo_cobrem_o_texto_com_sobreposicao` — nenhum trecho passa do tamanho, trechos
  vizinhos se sobrepõem, e a união recompõe o texto inteiro.
- `test_ciclo_indexa_faq_e_ignora_inalterada` — com gerador falso, a FAQ publicada ganha os trechos
  com modelo e hash certos, e o segundo ciclo não chama o gerador. *(marker `banco`)*
- `test_ciclo_indexa_imagem_e_video_mp4_sem_rechamar_inalterados` — imagem gera trecho multimodal
  (`IMAGEM`) e MP4 gera `VIDEO_METADADO` + frames (`VIDEO_FRAME`); no segundo ciclo não chama
  extrator de frames nem gerador. *(marker `banco`)*
- `test_renomear_tema_reindexa_so_o_trecho_inteiro` — o trecho inteiro é trocado, e os de formulação
  ficam. *(marker `banco`)*
- `test_troca_de_modelo_reindexa_tudo` — mudar `ModeloEmbedding.nome` regera todos os trechos e remove
  os do modelo antigo. *(marker `banco`)*
- `test_ollama_fora_mantem_o_indice_anterior` — gerador que levanta `OllamaIndisponivel` deixa os
  trechos da FAQ editada exatamente como estavam. *(marker `banco`)*
- `test_cliente_ollama_serializa_multimodal_e_traduz_falhas` — envia `text` e `image` em base64 no
  JSON de `/api/embed`; timeout e 500 viram `OllamaIndisponivel`, dimensão errada vira
  `OllamaRespostaInvalida`.
- `test_busca_semelhante_respeita_visibilidade_inclusive_em_anexo_e_midia` — com vetores sintéticos,
  anônimo não recebe FAQ interna nem resultado vindo de anexo/imagem/MP4 ligado só a interna ou
  rascunho. *(marker `banco`)*
- `test_embedding_real_aproxima_parafrases_e_imagem` — com o Ollama de pé, `como emito a certidão`
  aproxima `onde tiro a certidão`, e texto descritivo aproxima a imagem correspondente no mesmo espaço
  de 768 dimensões. *(marker `integration`)*
