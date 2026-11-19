---
spec: faq/005
versao: v3
atualizado_em: 2026-11-18
testes_tdd: false
implementado: false
markers_obrigatorios: [banco, integration]
changelog:
  - v1: versão inicial
  - v2: índice cobre só texto e imagem, e vídeo sai do escopo
  - v3: o ciclo não lê binários, a busca vetorial é exata e a busca tem timeout próprio
---

# SPEC faq/005 — Índice semântico da FAQ (EmbeddingGemma 2 + pgvector)

## 1 · User story
**Requisito não-funcional** — toda FAQ publicada, todo anexo e toda imagem própria ganham
representação vetorial no mesmo espaço semântico, atualizada sozinha depois de cada edição. É a base
da busca em texto livre de faq/007.

## 2 · Condições de pronto
- [ ] `docker compose up` sobe o Postgres com a extensão `vector`, o serviço `ollama` com a variante
      texto + visão do `embeddinggemma-2` já baixada e o serviço `indexador`. O `web` sobe e serve a
      FAQ mesmo com o `ollama` fora do ar.
- [ ] Uma FAQ criada ou editada fica indexada em até um intervalo do indexador (padrão 30 s), sem
      nenhuma ação do administrador.
- [ ] O índice de uma FAQ cobre a FAQ inteira (pergunta, tema, subtema, resposta sem URLs de mídia e
      palavras-chave) e também cada formulação (pergunta e variações) separadamente.
- [ ] O texto de cada anexo é dividido em trechos, e cada trecho é indexado.
- [ ] Cada imagem ligada a FAQ publicada ganha um vetor multimodal (imagem + legenda/descrição).
- [ ] Renomear um tema reindexa as FAQs daquele tema. FAQ, anexo ou imagem sem mudança não dispara
      chamada ao modelo nem leitura do arquivo binário no banco.
- [ ] Trocar o modelo de embedding na configuração reindexa tudo no ciclo seguinte.
- [ ] Com o `ollama` fora do ar, o indexador registra a falha, não grava índice pela metade e retoma
      sozinho quando o serviço volta.
- [ ] `manage.py buscar_faq "texto"` lista as FAQs mais próximas (inclusive por anexo ou imagem),
      respeitando a visibilidade de quem pergunta (`--autenticado`). Rascunho nunca aparece, e o
      anônimo recebe as públicas mais próximas mesmo quando os trechos mais próximos são de internas.

## 3 · Domínio

A ontologia da FAQ é a de [faq/001](001-pagina-de-faq.md#3--domínio), a do anexo é a de
[faq/003](003-anexos-da-faq.md#3--domínio) e a das imagens é a de [faq/004](004-midias-da-faq.md#3--domínio).
Esta SPEC pergunta a elas que conteúdo (textual ou visual) representa cada uma no espaço vetorial. O
índice é **derivado**: tudo nele pode ser reconstruído a partir das FAQs, dos anexos e das imagens.

```python
class OrigemTrecho(StrEnum):
    FAQ_INTEIRA = "faq_inteira"          # pergunta + tema + resposta + palavras-chave
    FORMULACAO = "formulacao"            # uma pergunta ou variação, sozinha
    ANEXO = "anexo"                      # um pedaço do texto extraído do anexo
    IMAGEM = "imagem"                    # imagem MidiaFaq (visual + legenda e descrição)


class TrechoIndexavel(BaseModel):
    """Unidade que vira um vetor. A identidade é o hash: muda texto, imagem ou modelo, muda o vetor."""
    origem: OrigemTrecho
    faq_id: int | None = None
    anexo_id: int | None = None
    midia_id: int | None = None
    posicao: int = 0                     # ordem do trecho no anexo
    titulo: str                          # usado no prompt textual quando aplicável
    texto: str = ""
    # sha256 da imagem; presente = trecho multimodal. Os bytes não entram no DTO: o hash não depende
    # deles, e o indexador só os lê para o trecho que vai mesmo ao modelo.
    midia_hash: str | None = None

    @model_validator(mode="after")
    def _uma_ponta_e_conteudo(self) -> Self:
        pontas = sum(p is not None for p in (self.faq_id, self.anexo_id, self.midia_id))
        if pontas != 1:
            raise ValueError("O trecho pertence a exatamente uma ponta (FAQ, anexo ou mídia).")
        if not self.texto and self.midia_hash is None:
            raise ValueError("O trecho precisa de texto ou imagem para gerar embedding.")
        return self

    def hash_para(self, modelo: ModeloEmbedding) -> str:
        identidade = (
            f"{modelo.nome}|{modelo.dimensoes}|{self.origem}|{self.posicao}"
            f"|{self.midia_hash or ''}|{self.prompt_texto()}"
        )
        return sha256(identidade.encode()).hexdigest()

    def prompt_texto(self) -> str:
        if self.midia_hash is not None:
            return self.texto
        return PROMPT_DOCUMENTO.format(titulo=self.titulo, texto=self.texto)


class ModeloEmbedding(BaseModel):
    nome: str                            # tag Ollama com visão, ex.: "embeddinggemma-2:440m"
    dimensoes: int = Field(gt=0)         # 768, a dimensão nativa unificada


class FaqSemelhante(BaseModel):
    faq_id: int
    distancia: float = Field(ge=0)       # cosseno; menor = mais próximo
    origem: OrigemTrecho                 # de onde veio o trecho mais próximo
    anexo_id: int | None = None          # quando a proximidade veio de um anexo
    midia_id: int | None = None          # quando a proximidade veio de uma imagem
```

## 4 · Fora de escopo
- A caixa de busca, o registro das buscas e o painel de sugestões — faq/007.
- Indexar FAQ em rascunho para a pré-visualização da busca — sem dono ainda; o indexador cobre só
  as publicadas.
- Reduzir a dimensão (MRL 512/256/128) para economizar espaço — sem dono ainda.
- Vídeos no índice (frames e trilha de áudio) — sem dono ainda, junto com os vídeos da resposta.
- Imagens internas de PDFs — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/utils/markdown` (faq/001) → o parser markdown-it, para tirar o markdown da resposta.
- `@services/domain/faq/visibilidade.py` → `visibilidades_para` (faq/001): filtro da busca.
- `@apps/faq/models.py` → `Faq`, `Formulacao`, `Tema`, `Anexo`, `MidiaFaq` (faq/001, faq/003 e
  faq/004).
- `requests` (já é dependência) → transporte do cliente Ollama.
- `@docker/Dockerfile.web` → a imagem do `web`, reaproveitada pelo `indexador`.
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
    image: ollama/ollama:0.40.4      # a primeira estável com imagem no /api/embed
    # `serve`, `pull` do modelo se faltar e um embed de aquecimento, que deixa o modelo carregado.
    entrypoint: ["/bin/sh", "/scripts/ollama-entrypoint.sh"]
    environment:
      # 440M = texto + visão. O `latest` é o 740M, que carrega também o encoder de áudio.
      OLLAMA_MODELO_EMBEDDING: ${OLLAMA_MODELO_EMBEDDING:-embeddinggemma-2:440m}
      # Sem descarregar: o padrão solta o modelo após 5 min parado, e a busca seguinte esperaria a recarga.
      OLLAMA_KEEP_ALIVE: "-1"
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
    # Troca o entrypoint.sh: migração, seeds e ortofotos são do `web`, e rodar em dois serviços disputaria.
    entrypoint: ["python", "manage.py", "indexar_faq", "--continuo"]
    # Na primeira subida, o banco ainda pode estar sem as tabelas que o `web` vai migrar.
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-dimap_geocode}
      POSTGRES_USER: ${POSTGRES_USER:-dimap}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-dimap}
      POSTGRES_HOST: db
      POSTGRES_PORT: 5432
      DJANGO_SETTINGS_MODULE: ${DJANGO_SETTINGS_MODULE:-config.settings}
      OLLAMA_URL: http://ollama:11434
    volumes:
      - .:/app                          # mesmo bind mount do `web`
    depends_on:
      db:
        condition: service_healthy
      ollama:
        condition: service_healthy
  # O `web` ganha `OLLAMA_URL` (para a busca de faq/007), mas NÃO depende do `ollama`: a FAQ funciona
  # sem índice.

volumes:
  ollama_modelos:
```

**`config/settings.py`** — configuração lida pelo Pydantic Settings e entregue a `services/` por DTO.

```python
OLLAMA_URL = _env.ollama_url                                   # http://ollama:11434
FAQ_MODELO_EMBEDDING = ModeloEmbedding(nome=_env.ollama_modelo_embedding, dimensoes=768)
# Dois clientes: a busca desiste rápido e recua para o texto; o indexador espera o modelo trabalhar.
FAQ_OLLAMA_BUSCA = ConfigOllama(url=OLLAMA_URL, timeout_s=_env.faq_ollama_timeout_busca_s)          # 3
FAQ_OLLAMA_INDEXADOR = ConfigOllama(url=OLLAMA_URL, timeout_s=_env.faq_ollama_timeout_indexador_s)  # 120
FAQ_INDEXADOR_INTERVALO_S = _env.faq_indexador_intervalo_s     # 30
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
        # Item multimodal do /api/embed (Ollama ≥ 0.40.4): objeto com `text` e/ou `image` em base64.
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
    # `markdown_para_texto` mantém texto `alt` de imagens e descarta URLs internas `/faq/midias/...`.
    partes = [
        caminho_tema,
        markdown_para_texto(faq.resposta.markdown),
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


def trecho_da_imagem(midia: MidiaFaq) -> TrechoIndexavel:
    legenda_e_desc = "\n".join(p for p in (midia.legenda, midia.descricao) if p)
    return TrechoIndexavel(
        origem=OrigemTrecho.IMAGEM,
        midia_id=midia.id,
        titulo=midia.legenda,
        texto=legenda_e_desc,
        midia_hash=midia.hash_conteudo,
    )
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
imagem: se o Ollama cai no meio, cada unidade fica inteira no estado antigo ou inteira no novo.

```python
def ciclo(gerador: GeradorEmbedding, modelo: ModeloEmbedding) -> ResumoCiclo:
    # As três consultas usam `.defer("arquivo")`: um ciclo sem mudança não tira binário do banco.
    for faq in faqs_publicadas_como_dto():                    # rascunho sai do índice
        _reconciliar(trechos_da_faq(faq), TrechoModel.objects.filter(faq_id=faq.id), gerador, modelo)
    for anexo in anexos_ligados_a_publicadas_como_dto():
        _reconciliar(trechos_do_anexo(anexo), TrechoModel.objects.filter(anexo_id=anexo.id), gerador, modelo)
    for midia in midias_ligadas_a_publicadas_como_dto():
        _reconciliar([trecho_da_imagem(midia)], TrechoModel.objects.filter(midia_id=midia.id), gerador, modelo)
    _remover_trechos_orfaos_ou_rascunho()


def _entrada(trecho: TrechoIndexavel) -> EntradaEmbedding:
    # Chamado só para `plano.a_gerar`: a imagem sai do banco quando vai mesmo ao modelo.
    if trecho.midia_id is None:
        return EntradaEmbedding(texto=trecho.prompt_texto())
    arquivo = MidiaFaqModel.objects.values_list("arquivo", flat=True).get(pk=trecho.midia_id)
    return EntradaEmbedding(texto=trecho.prompt_texto() or None, imagem_bytes=bytes(arquivo))
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
        # Sem índice vetorial: a busca é exata (Caveats).
```

A primeira migração do app nesta SPEC é `VectorExtension()` (do pacote `pgvector`).

**`apps/faq/semantica.py`** — a consulta que faq/007 consome. A visibilidade entra no SQL, por junção, e
não é copiada para a linha do trecho.

```python
# Uma FAQ ocupa vários trechos (inteira, formulações, anexos), e k × 5 trechos cobre k FAQs na prática.
FATOR_CANDIDATOS = 5


def buscar_semelhantes(
    consulta: str,
    leitor: Leitor,
    k: int,
    gerador: GeradorEmbedding,
    modelo: ModeloEmbedding,
) -> list[FaqSemelhante]:
    entrada = EntradaEmbedding(texto=PROMPT_CONSULTA.format(consulta=consulta))
    vetor = gerador(PedidoEmbedding(modelo=modelo, entradas=[entrada]))[0]
    faqs_visiveis = FaqModel.objects.filter(situacao=Situacao.PUBLICADA, visibilidade__in=visibilidades_para(leitor))
    candidatos = (
        TrechoModel.objects.filter(modelo=modelo.nome)
        .filter(
            # EXISTS, e não JOIN: um anexo ligado a três FAQs visíveis não vira três linhas na janela.
            Q(faq__in=faqs_visiveis)
            | Exists(faqs_visiveis.filter(anexos=OuterRef("anexo_id")))
            | Exists(faqs_visiveis.filter(midias=OuterRef("midia_id")))
        )
        .annotate(distancia=CosineDistance("vetor", vetor))
        .order_by("distancia")[: k * FATOR_CANDIDATOS]
    )
    # Um trecho de anexo ou imagem aponta para várias FAQs: o domínio expande e fica com o melhor por FAQ.
    return melhor_por_faq(_como_ocorrencias(candidatos, faqs_visiveis), k)    # services/domain/faq/ranking.py
```

## 7 · Caveats

**O compose ganha dois serviços e o banco passa a ter imagem própria.** O `postgis/postgis` não traz
`pgvector`, e o modelo exige um runtime próprio; o `indexador` reaproveita o `Dockerfile.web`. O
custo é a RAM do Ollama com a variante 440m carregada o tempo todo (`OLLAMA_KEEP_ALIVE=-1`; a medir,
o download tem ~0,7 GB) e manter `Dockerfile.db` na atualização do PostGIS.

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

**O embedding de imagem depende de um contrato do Ollama que a documentação pública ainda não
descreve.** O código da 0.40.4 aceita no `/api/embed` o item `{"text", "image"}`, com a imagem em
base64, mas a página da API só fala de texto, e as notas de versão não dizem se o caminho de imagem
roda no runner Linux. Por isso a imagem do Ollama fica fixada nessa versão, e o primeiro teste
`integration` a passar é o que confirma que a `embeddinggemma-2:440m` devolve vetor de imagem com
768 dimensões.

**A busca vetorial é exata, sem índice HNSW.** O HNSW escolhe os vizinhos aproximados antes do filtro
de visibilidade: se os mais próximos forem trechos de FAQs internas, o anônimo recebe menos
resultados que o pedido, ou nenhum. Com centenas de FAQs e alguns milhares de trechos, varrer a
tabela inteira custa poucas dezenas de milissegundos. Se a tabela passar de dezenas de milhares de
trechos, o HNSW volta com `hnsw.iterative_scan` ligado.

**O `indexador` usa a imagem do `web`, mas não o entrypoint dele.** Migração, seeds e ortofotos rodam
só no `web`. Na primeira subida o indexador pode começar antes das migrações e cair, e o `restart`
o traz de volta até o banco estar pronto.

## 8 · Testes (TDD)
- `test_trechos_da_faq_cobrem_a_faq_e_cada_formulacao` — 1 trecho inteiro + 1 por formulação. O
  inteiro traz `Tema › Subtema`, a resposta sem sintaxe markdown, `alt` de imagens (sem `/faq/midias/`)
  e palavras-chave.
- `test_trechos_do_anexo_cobrem_o_texto_com_sobreposicao` — nenhum trecho passa do tamanho, trechos
  vizinhos se sobrepõem, e a união recompõe o texto inteiro.
- `test_ciclo_indexa_faq_e_ignora_inalterada` — com gerador falso, a FAQ publicada ganha os trechos
  com modelo e hash certos, e o segundo ciclo não chama o gerador. *(marker `banco`)*
- `test_ciclo_indexa_imagem_sem_rechamar_inalterada` — a imagem gera um trecho multimodal (`IMAGEM`)
  com os bytes e a legenda; no segundo ciclo o gerador não é chamado e nenhuma consulta lê a coluna
  `arquivo` (`CaptureQueriesContext`). *(marker `banco`)*
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
  anônimo não recebe FAQ interna nem resultado vindo de anexo ou imagem ligado só a interna ou
  rascunho, e recebe k públicas mesmo quando os trechos mais próximos da consulta são de internas.
  *(marker `banco`)*
- `test_embedding_real_aproxima_parafrases_e_imagem` — com o Ollama de pé, `como emito a certidão`
  aproxima `onde tiro a certidão`, e texto descritivo aproxima a imagem correspondente no mesmo espaço
  de 768 dimensões. *(marker `integration`)*
