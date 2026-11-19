---
spec: faq/007
versao: v5
atualizado_em: 2026-11-19
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: resultado aponta anexo ou imagem, e vídeo sai do escopo
  - v3: registro sem prefixos e com limite por IP, fallback por palavras e agrupamento em numpy
  - v4: o limiar do fallback textual é calibrado no teste desta SPEC, e não sobre a seed
  - v5: painel de buscas no molde do registro de ações: card de busca com período, tabela de vidro e paginação
---

# SPEC faq/007 — Busca em texto livre e sugestões a partir das buscas

## 1 · User story
O leitor pesquisa a FAQ em texto livre (na página ou no widget) enquanto o administrador acompanha
essas buscas agrupadas por semelhança semântica, para que dúvidas fora dos termos exatos encontrem
resposta e lacunas virem novas FAQs.

## 2 · Condições de pronto
- [ ] O design da caixa de busca (na página e no widget) e da tela de buscas mais feitas foi aprovado
      no mock e as peças foram portadas para o tema e o styleguide antes de o template da aplicação
      usá-las.
- [ ] Digitar uma pergunta na página `/faq/` ou no widget filtra as FAQs por semelhança semântica,
      respeitando a visibilidade do leitor, e limpar o campo restaura a lista normal.
- [ ] Quando a melhor semelhança vem de um anexo ou de uma imagem, o resultado indica o título do
      anexo ou a legenda da imagem correspondente.
- [ ] Com o Ollama fora do ar, lento ou respondendo fora do contrato, a busca não falha: recua para a
      busca textual por palavras sobre perguntas, variações e palavras-chave das FAQs visíveis. Uma
      consulta curta acha a pergunta longa que contém as palavras dela.
- [ ] Buscas efetivas (a partir do tamanho mínimo) são registradas com o texto digitado, a data, a
      tela de origem (quando feitas pelo widget, e só se for uma tela declarada) e se encontraram
      resposta próxima. Buscas vazias ou curtas demais não são registradas, e as pausas de uma mesma
      digitação viram um registro só, com o texto final.
- [ ] Acima do limite de buscas por minuto de um mesmo IP, a busca ainda responde, pela via textual,
      sem chamar o Ollama e sem registrar.
- [ ] O indexador vetoriza cada frase distinta buscada no ciclo periódico e a reindexa se o modelo de
      embedding mudar, sem chamar o modelo para frases já indexadas.
- [ ] Só o superusuário acessa o painel de buscas (`faq:admin_buscas`); servidor comum recebe 403 e
      anônimo é levado ao login.
- [ ] O painel de buscas segue o registro de ações: um card de busca com o período (últimos 30 dias
      quando nada é escolhido) e o alternador "só sem cobertura", e a tabela de vidro paginada dos
      grupos de buscas parecidas, com as ocorrências somadas, a FAQ publicada mais próxima de cada
      grupo e filtro e ordenação por pergunta sugerida e por variações.
- [ ] A partir de um grupo no painel, o administrador abre o formulário de nova FAQ (faq/002) já
      preenchido com a frase principal como pergunta, as demais como variações e as telas de origem
      marcadas. Nada é gravado até ele salvar.

## 3 · Domínio

A ontologia da FAQ é a de [faq/001](001-pagina-de-faq.md#3--domínio), a das imagens é a de
[faq/004](004-midias-da-faq.md#3--domínio), a do índice vetorial é a de
[faq/005](005-indice-semantico.md#3--domínio) e a das telas é a de [faq/006](006-faq-da-tela.md#3--domínio).
Esta SPEC pergunta a elas quais FAQs respondem a uma dúvida em texto livre e quais FAQs já cobrem
cada grupo de dúvidas buscadas.

```python
MINIMO_CARACTERES_BUSCA = 4
LIMIAR_LACUNA = 0.45                     # distância cosseno acima da qual o grupo é considerado lacuna


class ModoBusca(StrEnum):
    SEMANTICO = "semantico"
    TEXTUAL_FALLBACK = "textual_fallback"


class RecorteBuscas(BaseModel):
    """O que vai ao banco no painel: quais registros entram no agrupamento."""
    inicio: date                         # sem default: "hoje" é da orquestração (JANELA_PADRAO_DIAS)
    fim: date
    apenas_sem_cobertura: bool = False


class FraseBuscada(BaseModel):
    """Dúvida distinta buscada pelos leitores. A identidade é a `chave`, não a grafia exata."""
    texto: str = Field(min_length=MINIMO_CARACTERES_BUSCA, max_length=300)

    @computed_field
    @property
    def chave(self) -> str:
        return normalize_text(self.texto)


class RegistroBusca(BaseModel):
    """Fato de uma busca realizada; guarda `teve_cobertura` apurado no momento em que ocorreu."""
    frase: FraseBuscada
    digitacao: UUID                      # uma caixa de busca aberta; as pausas dela refinam o mesmo registro
    tela_origem: str | None = None       # nome_rota quando buscado pelo widget; None = /faq/
    teve_cobertura: bool
    realizada_em: datetime


class ContagemFrase(BaseModel):
    """Agregado de ocorrências de uma frase buscada dentro de uma janela de consulta."""
    frase: FraseBuscada
    ocorrencias: int = Field(ge=1)
    sem_cobertura: int = Field(ge=0)
    telas: list[str] = []


class GrupoBuscas(BaseModel):
    """Agrupamento semântico derivado, ordenado da frase mais frequente para as demais."""
    frases: list[ContagemFrase] = Field(min_length=1)
    faq_proxima: Faq | None = None
    distancia_faq: float | None = Field(default=None, ge=0)

    @computed_field
    @property
    def pergunta_sugerida(self) -> str:
        return self.frases[0].frase.texto

    @computed_field
    @property
    def total_ocorrencias(self) -> int:
        return sum(f.ocorrencias for f in self.frases)

    @computed_field
    @property
    def ocorrencias_sem_cobertura(self) -> int:
        return sum(f.sem_cobertura for f in self.frases)

    @computed_field
    @property
    def eh_lacuna(self) -> bool:
        return self.distancia_faq is None or self.distancia_faq > LIMIAR_LACUNA
```

**Mock:** [007-mock-busca-e-sugestoes.html](007-mock-busca-e-sugestoes.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Geração automática do texto da resposta por LLM a partir dos anexos — sem dono ainda.
- Arquivar ou marcar manualmente um grupo de buscas como ignorado no painel — sem dono ainda.
- Registrar a identidade do usuário autor da busca — sem dono ainda (o registro é anônimo).
- Destacar o trecho exato dentro do texto do anexo no resultado da busca — sem dono ainda (mostra
  apenas o título do anexo ou a legenda da imagem).

## 5 · Peças de referência a compor
- `@apps/faq/semantica.py` → `buscar_semelhantes` (faq/005): consulta vetorial sobre FAQs, anexos e imagens.
- `@services/domain/faq/indexacao.py` → `PROMPT_CONSULTA`, `GeradorEmbedding` (faq/005): prompt e
  porta de vetorização das frases buscadas.
- `@services/domain/faq/visibilidade.py` → `visibilidades_para`, `eh_visivel` (faq/001): filtro de
  visibilidade nos resultados e na checagem de FAQ próxima.
- `@services/utils/normalization` → `normalize_text`: chave única da frase buscada.
- `@services/utils/fuzzy_matcher` → `fuzzy_match`: ranqueamento no fallback textual, com o algoritmo
  novo `token_set`.
- `@apps/faq/acesso.py` → `superusuario_requerido` (faq/002): portão do painel de buscas.
- `@services/domain/listagem_gestao` → `ListadorTabela`, `paginar` e `JANELA_PADRAO_DIAS`: filtro do
  cabeçalho, paginação depois do filtro e o período padrão.
- `@templates/competencias/partials/` → `_busca_execucoes.html`, `_tabela_execucoes.html` e
  `_paginacao_execucoes.html` (SPEC painel/002): o molde do card de busca, da tabela e da paginação.
- `@apps/faq/telas.py` → `telas_declaradas` (faq/006): conferência de `tela_origem` e da `tela` do
  pré-preenchimento.
- `numpy` → já está no `uv.lock` como dependência transitiva; entra como direta (`uv add numpy`) para
  o agrupamento.
- Cache do Django (o padrão, em memória do processo) → contador do limite por IP.
- Skills: `ontologia`, `fuzzy-matcher`, `normalize-text`, `componentes-frontend`, `daisyui`,
  `htmx-skill`, `mock`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

> O comentário didático destes blocos existe só aqui e **não é portado** (CLAUDE.md §7.2).

**`services/domain/faq/busca_textual.py`** — fallback puro quando o Ollama está fora do ar. Passa os
textos brutos a `fuzzy_match` porque o módulo normaliza por dentro (skill `fuzzy-matcher`).

```python
LIMIAR_SCORE_FUZZY = 70.0               # calibrado em test_fallback_textual_acha_pergunta_longa_...
LIMIAR_DISTANCIA_BUSCA = 0.60


class PedidoBuscaFaq(BaseModel):
    consulta: str = Field(max_length=300)
    leitor: Leitor
    digitacao: UUID
    tela_origem: str | None = None
    limite: int = Field(default=10, ge=1, le=30)

    @field_validator("consulta", mode="before")
    @classmethod
    def _limpar(cls, valor: str) -> str:
        return valor.strip()


class ItemBuscaFaq(BaseModel):
    faq: Faq
    anexo_titulo: str | None = None      # preenchido só quando o melhor casamento veio de um anexo
    midia_legenda: str | None = None     # preenchido só quando o melhor casamento veio de uma imagem


class ResultadoBuscaFaq(BaseModel):
    modo: ModoBusca
    itens: list[ItemBuscaFaq]


class BuscarTextual:
    def __call__(self, consulta: str, faqs: list[Faq], limite: int) -> list[Faq]:
        return self.pipeline(consulta, faqs, limite)

    def pipeline(self, consulta: str, faqs: list[Faq], limite: int) -> list[Faq]:
        # Texto → ids das FAQs: a mesma palavra-chave em duas FAQs aponta para as duas, e nenhuma some.
        # Cada FAQ fica com o melhor score entre os seus textos.
        candidatos = self._expandir_candidatos(faqs)          # dict[str, set[int]]
        if not candidatos:
            return []
        # `token_set` compara palavras, não a string inteira: "emitir certidão" casa com a pergunta longa.
        resultado = fuzzy_match(consulta, list(candidatos), limit=limite * 3, algorithm="token_set")
        return self._melhores_faqs(resultado.matches, candidatos, faqs, limite)
```

**`services/utils/fuzzy_matcher/matcher.py`** (ALTERADO nesta SPEC) — `algorithm` ganha
`"token_set"`, que usa `fuzz.token_set_ratio`. Os chamadores atuais continuam no `"levenshtein"`, e a
skill `fuzzy-matcher` ganha a linha do algoritmo novo.

**`services/domain/faq/agrupamento.py`** — agrupamento semântico guloso e cálculo do centróide
normalizado de cada grupo, em domínio puro.

```python
LIMIAR_AGRUPAMENTO_BUSCAS = 0.25         # distância cosseno máxima ao centróide do grupo
MAXIMO_FRASES_AGRUPAMENTO = 500


class FraseVetorizada(BaseModel):
    contagem: ContagemFrase
    vetor: list[float]


class GrupoComCentroide(BaseModel):
    grupo: GrupoBuscas
    centroide: list[float]               # usado pelo app para consultar a FAQ mais próxima no pgvector


class AgruparBuscas:
    def __call__(
        self,
        frases: list[FraseVetorizada],
        limiar: float = LIMIAR_AGRUPAMENTO_BUSCAS,
    ) -> list[GrupoComCentroide]:
        return self.pipeline(frases, limiar)

    def pipeline(self, frases: list[FraseVetorizada], limiar: float) -> list[GrupoComCentroide]:
        if not frases:
            return []
        # Ordenar por frequência garante que a forma mais buscada pelo público vire a âncora do grupo.
        ordenadas = sorted(frases, key=lambda f: f.contagem.ocorrencias, reverse=True)
        vetores = _normalizadas(np.asarray([f.vetor for f in ordenadas], dtype=np.float32))
        grupos = [self._consolidar(ordenadas, indices) for indices in self._agrupar(vetores, limiar)]
        return sorted(grupos, key=lambda g: g.grupo.total_ocorrencias, reverse=True)

    def _agrupar(self, vetores: NDArray[np.float32], limiar: float) -> list[list[int]]:
        somas = np.empty((0, vetores.shape[1]), dtype=np.float32)     # soma dos vetores de cada grupo
        membros: list[list[int]] = []
        for i, vetor in enumerate(vetores):
            # Um produto matriz × vetor mede a frase contra todos os centróides de uma vez.
            distancias = 1.0 - _normalizadas(somas) @ vetor
            destino = int(np.argmin(distancias)) if membros else None
            if destino is None or distancias[destino] > limiar:
                somas = np.vstack([somas, vetor])
                membros.append([i])
            else:
                somas[destino] += vetor
                membros[destino].append(i)
        return membros
```

**`apps/faq/models.py`**

```python
class FraseBuscada(models.Model):
    chave = models.CharField(max_length=300, unique=True)
    texto_representativo = models.CharField(max_length=300)
    # Preenchido em ciclo pelo indexador (PROMPT_CONSULTA); vazio enquanto pendente.
    modelo = models.CharField(max_length=80, default="")
    vetor = VectorField(dimensions=768, null=True, blank=True)


class RegistroBusca(models.Model):
    frase = models.ForeignKey(FraseBuscada, on_delete=models.CASCADE, related_name="registros")
    digitacao = models.UUIDField(db_index=True)
    texto_original = models.CharField(max_length=300)
    tela_origem = models.CharField(max_length=120, null=True, blank=True)
    teve_cobertura = models.BooleanField()
    realizada_em = models.DateTimeField(auto_now_add=True, db_index=True)
```

**`apps/faq/busca.py`** — orquestra busca semântica, fallback textual e registro da ocorrência.

```python
def buscar_na_faq(
    pedido: PedidoBuscaFaq,
    gerador: GeradorEmbedding,
    modelo: ModeloEmbedding,
    dentro_do_limite: bool,
) -> ResultadoBuscaFaq:
    if not dentro_do_limite:
        # Acima do limite, a busca ainda responde, mas não ocupa o Ollama nem entra no painel.
        return _buscar_textual(pedido)
    try:
        semelhantes = buscar_semelhantes(pedido.consulta, pedido.leitor, pedido.limite, gerador, modelo)
        relevantes = [s for s in semelhantes if s.distancia <= LIMIAR_DISTANCIA_BUSCA]
        resultado = ResultadoBuscaFaq(modo=ModoBusca.SEMANTICO, itens=_hidratar_itens(relevantes))
        teve_cobertura = any(s.distancia <= LIMIAR_LACUNA for s in relevantes)
    except (OllamaIndisponivel, OllamaRespostaInvalida):
        # Resposta fora do contrato também recua: o leitor nunca vê erro 500 por causa do índice.
        resultado = _buscar_textual(pedido)
        teve_cobertura = bool(resultado.itens)
    registrar_busca(
        FraseBuscada(texto=pedido.consulta),
        pedido.digitacao,
        pedido.tela_origem,
        teve_cobertura,
    )
    return resultado


def _buscar_textual(pedido: PedidoBuscaFaq) -> ResultadoBuscaFaq:
    visiveis = carregar_faqs(visibilidades_para(pedido.leitor))
    faqs = buscar_textual(pedido.consulta, visiveis, pedido.limite)
    return ResultadoBuscaFaq(modo=ModoBusca.TEXTUAL_FALLBACK, itens=[ItemBuscaFaq(faq=f) for f in faqs])


@transaction.atomic
def registrar_busca(
    frase: FraseBuscada,
    digitacao: UUID,
    tela_origem: str | None,
    teve_cobertura: bool,
) -> None:
    # get_or_create por `chave` evita chamar o Ollama para grafias equivalentes da mesma dúvida.
    alvo, _ = FraseBuscadaModel.objects.get_or_create(
        chave=frase.chave,
        defaults={"texto_representativo": frase.texto},
    )
    anterior = (
        RegistroBuscaModel.objects.filter(digitacao=digitacao)
        .select_related("frase")
        .order_by("-id")
        .first()
    )
    if anterior is not None and eh_continuacao(anterior.frase.chave, alvo.chave):
        frase_anterior = anterior.frase
        anterior.frase = alvo
        anterior.texto_original = frase.texto
        anterior.teve_cobertura = teve_cobertura
        anterior.save()
        _apagar_se_orfa(frase_anterior)          # "como emi" não sobra para o indexador vetorizar
        return
    RegistroBuscaModel.objects.create(
        frase=alvo,
        digitacao=digitacao,
        texto_original=frase.texto,
        tela_origem=tela_origem,
        teve_cobertura=teve_cobertura,
    )
```

**`services/domain/faq/registro_busca.py`** — quando a busca nova é a mesma dúvida ainda sendo escrita.

```python
def eh_continuacao(chave_anterior: str, chave_nova: str) -> bool:
    # Digitar ou apagar no fim do campo deixa uma chave como prefixo da outra.
    return chave_nova.startswith(chave_anterior) or chave_anterior.startswith(chave_nova)
```

**`apps/faq/limite.py`** — o limite por IP. `FAQ_BUSCA_LIMITE_POR_MINUTO` vem do settings (padrão 30;
quem digita com pausas faz uma busca a cada poucos segundos).

```python
def dentro_do_limite(ip: str) -> bool:
    # Cache padrão do Django, em memória do processo: o limite é por worker e aproximado (Caveats).
    chave = f"faq_busca:{ip}:{int(time()) // 60}"
    cache.add(chave, 0, timeout=60)
    return cache.incr(chave) <= FAQ_BUSCA_LIMITE_POR_MINUTO
```

A view lê o IP de `REMOTE_ADDR`, passa `dentro_do_limite(ip)` a `buscar_na_faq`, usa o cliente
`FAQ_OLLAMA_BUSCA` (faq/005, timeout de 3 s) e só repassa `tela_origem` se ela estiver em
`telas_declaradas()`; outra vira `None`.

**`apps/faq/indexador.py`** — estende o `ciclo` de faq/005 para vetorizar também as frases buscadas
pendentes com `PROMPT_CONSULTA`, permitindo comparar cada grupo contra `TrechoIndexado` sem chamar o
Ollama quando o administrador abre o painel.

```python
LOTE_FRASES = 64                         # frases por chamada ao Ollama


def _indexar_frases_buscadas(gerador: GeradorEmbedding, modelo: ModeloEmbedding) -> None:
    pendentes_qs = FraseBuscadaModel.objects.filter(Q(vetor__isnull=True) | ~Q(modelo=modelo.nome)).order_by("id")
    # Lote a lote até zerar: depois de uma troca de modelo, todas as frases ficam pendentes de uma vez.
    while pendentes := list(pendentes_qs[:LOTE_FRASES]):
        entradas = [EntradaEmbedding(texto=PROMPT_CONSULTA.format(consulta=f.texto_representativo)) for f in pendentes]
        vetores = gerador(PedidoEmbedding(modelo=modelo, entradas=entradas))
        with transaction.atomic():
            for obj, vetor in zip(pendentes, vetores, strict=True):
                obj.vetor = vetor
                obj.modelo = modelo.nome
            FraseBuscadaModel.objects.bulk_update(pendentes, ["vetor", "modelo"])
```

**`services/domain/faq/agrupamento.py`** — a linha da tabela de vidro envelopa o grupo. As duas
colunas de texto são lidas pelo `ListadorTabela` existente; ocorrências, cobertura e FAQ mais próxima
são colunas gravadas, sem filtro nem seta.

```python
class ColunaGrupoBuscas(StrEnum):
    PERGUNTA_SUGERIDA = "pergunta_sugerida"
    VARIACOES = "variacoes"


class LinhaGrupoBuscas(BaseModel):
    item: GrupoComCentroide

    @property
    def pergunta_sugerida(self) -> str:
        return self.item.grupo.pergunta_sugerida

    @property
    def variacoes(self) -> str:
        return " · ".join(f.frase.texto for f in self.item.grupo.frases[1:])


ConsultaGruposBuscas = ConsultaListagem[ColunaGrupoBuscas]
listar_grupos_buscas = ListadorTabela[LinhaGrupoBuscas, ColunaGrupoBuscas]()
```

**`apps/faq/sugestoes.py`** — agrega os registros do recorte, chama `AgruparBuscas`, aplica o
cabeçalho, pagina e só então resolve a FAQ publicada mais próxima pelo centróide (consultando
`TrechoIndexado` direto no Postgres). A ordem é a do registro de ações: filtro → página → enriquecimento.

```python
def sugerir_grupos(
    recorte: RecorteBuscas,
    consulta: ConsultaGruposBuscas,
    modelo: ModeloEmbedding,
    pagina: int,
) -> Pagina[GrupoBuscas]:
    frases = _carregar_frases_vetorizadas(recorte, modelo, MAXIMO_FRASES_AGRUPAMENTO)
    linhas = [LinhaGrupoBuscas(item=item) for item in agrupar_buscas(frases)]
    # Sem seta ativa, vale a ordem do agrupamento: mais ocorrências primeiro.
    filtradas = listar_grupos_buscas(linhas, consulta)
    fatia = paginar(filtradas, pagina, TAMANHO_PAGINA)
    # A FAQ mais próxima custa uma consulta por grupo: só a página exibida paga.
    return Pagina(
        linhas=tuple(_anexar_faq_proxima(linha.item, modelo) for linha in fatia.linhas),
        numero=fatia.numero,
        total_paginas=fatia.total_paginas,
        total_linhas=fatia.total_linhas,
    )
```

`RecorteBuscas` nasce na view como `BuscaExecucoes` (SPEC painel/002): `inicio` e `fim` da query
string, ou os últimos `JANELA_PADRAO_DIAS` a partir do `hoje` que a view passa.

**Rotas e interface:**

| Rota | Acesso | Comportamento |
|---|---|---|
| `faq:buscar` | aberta (HTMX GET) | se `len(q.strip()) < MINIMO_CARACTERES_BUSCA`, devolve o partial da página inteira; senão chama `buscar_na_faq` e devolve `_resultados_busca.html` |
| `faq:widget_buscar` | aberta (HTMX GET) | igual, com `tela_origem` opcional; com `q` curto/vazio restaura o partial de `faq:widget_tela` ou `faq:widget_todas` |
| `faq:admin_buscas` | `superusuario_requerido` | página com o card de busca (`inicio`, `fim`, `sem_cobertura`) e a tabela de vidro dos grupos; cada linha tem o link para `faq:admin_nova` (faq/002) pré-preenchido via query string (`pergunta`, `variacao`, `tela`) |
| `faq:admin_buscas_corpo` | `superusuario_requerido` | o `<tbody>` e a paginação, alvo do HTMX do card e do cabeçalho, que viajam juntos (`hx-include`) |

O gatilho das caixas de busca usa `hx-trigger="input changed delay:500ms, search"`, para enviar só
quando o leitor pausa ou confirma, e `hx-sync="this:replace"`, para que a busca nova cancele a que
ainda está em voo. O partial da caixa traz um `<input type="hidden" name="digitacao">` com um UUID
gerado pelo servidor a cada renderização da caixa, enviado por `hx-include`.

**ALTERA faq/002: `faq:admin_nova` aceita valores iniciais por query string.** O GET lê `pergunta`,
`variacao` (repetível) e `tela` (repetível) e só os põe como `initial` do formulário. Nada é gravado até
o POST, que passa pelas validações de sempre, e `tela` fora de `telas_declaradas()` é descartada.

## 7 · Caveats

**`FraseBuscada.chave` é guardada em coluna, embora seja derivada.** A normalização `normalize_text`
não tem equivalente direto em SQL, e agrupar ocorrências equivalentes por `chave` é o que impede
chamar o Ollama repetidamente para a mesma frase. Se a regra de normalização mudar, chaves antigas e
novas deixam de convergir.

**O fallback textual não lê o conteúdo dos anexos.** Quando o Ollama cai, `BuscarTextual` consulta
apenas pergunta, variações e palavras-chave via `fuzzy_match`, porque varrer texto bruto de anexos em
tempo de request seria lento. O custo é perda temporária de alcance sobre anexos e imagens durante uma
queda do serviço de embeddings. E, como `token_set` dá nota máxima à consulta contida no texto, uma
consulta de uma palavra comum ("como") casa com muitas perguntas enquanto durar o fallback.

**A busca espera o Ollama por no máximo 3 s.** Passado isso, ela recua para o texto, e uma das threads
do web não fica presa num modelo lento. O modelo fica sempre carregado (faq/005), então o recuo por
lentidão só deve acontecer logo depois de um reinício do Ollama.

**O registro junta as pausas da mesma digitação pelo prefixo.** Cada pausa de 500 ms ainda chega ao
servidor, e a busca nova substitui o registro anterior da mesma `digitacao` quando uma chave é
prefixo da outra. Uma correção no meio da palavra feita sem pausa ("certidap" → "certidao") gera dois
registros, e a grafia errada fica no painel.

**O limite por IP vive no cache em memória de cada processo.** Sem `CACHES` configurado, o Django
guarda o contador no próprio worker: com 2 workers o limite efetivo pode chegar ao dobro, e um
reinício zera as contagens. Com o gunicorn atendendo direto, `REMOTE_ADDR` é o IP do leitor. Se um
proxy entrar na frente, o limite precisa ler o cabeçalho que ele preencher; senão, todos os leitores
dividem um IP só e esgotam o limite juntos.

**O agrupamento é guloso, em numpy, sobre as 500 frases mais frequentes do período.** Evita
biblioteca de clusterização, e o pior caso (500 frases, 500 grupos) fica abaixo de um segundo. O custo
é depender da ordem por frequência e ignorar termos de uma só ocorrência se o histórico crescer além do
teto. A FAQ mais próxima é calculada só para os grupos da página exibida.

**Ocorrências, cobertura e FAQ mais próxima são colunas gravadas, sem filtro nem seta.** O
`ListadorTabela` compara o texto normalizado, o que ordenaria "10" antes de "9", e a FAQ mais próxima
só existe depois da paginação. A ordem por ocorrências é a padrão, e some quando o administrador
ordena por uma coluna de texto.

**O domínio da FAQ passa a conhecer `listagem_gestao`.** A linha do grupo é tipada para o
`ListadorTabela` genérico, em vez de recopiar filtro e ordenação. Uma mudança no contrato do listador
atinge também o painel de buscas.

**A cobertura do dia (`teve_cobertura`) e a FAQ mais próxima no painel podem divergir.** A primeira
congela se o usuário encontrou resposta na hora da busca; a segunda consulta as FAQs publicadas hoje
para mostrar se a lacuna continua aberta. Um grupo antigo "sem cobertura" pode já aparecer coberto por
uma FAQ publicada depois.

**Frases buscadas durante queda do Ollama entram no painel só após o próximo ciclo do indexador.** O
painel lê apenas frases que já possuem vetor no modelo ativo para continuar abrindo sem depender do
Ollama no ar. O atraso máximo é o intervalo do indexador depois que o serviço volta.

## 8 · Testes (TDD)
- `test_busca_semantica_retorna_faqs_e_respeita_visibilidade` — encontra FAQ publicada por semelhança
  (indicando título do anexo ou legenda da imagem quando o match vem deles), omite interna para
  anônimo e rascunho para todos. *(marker `banco`)*
- `test_busca_recua_para_fallback_textual_quando_ollama_cai` — parametrizado: com gerador levantando
  `OllamaIndisponivel` ou `OllamaRespostaInvalida`, a busca retorna FAQs via `fuzzy_match` em
  `modo=textual_fallback` sem erro HTTP. *(marker `banco`)*
- `test_fallback_textual_acha_pergunta_longa_e_palavra_chave_repetida` — em domínio puro,
  "emitir certidão" acha "Como emito a certidão de lançamento do IPTU?", e uma palavra-chave presente
  em duas FAQs devolve as duas.
- `test_busca_curta_ou_vazia_nao_registra_e_restaura_lista` — texto menor que
  `MINIMO_CARACTERES_BUSCA` não cria `RegistroBusca` e devolve a listagem padrão na página e no
  widget. *(marker `banco`)*
- `test_buscas_equivalentes_compartilham_frase_buscada` — `"Como tiro a certidão?"` e `"como tiro a
  certidao"`, em digitações diferentes, criam dois `RegistroBusca` (um com `tela_origem`) ligados à
  mesma `FraseBuscada`; uma `tela_origem` fora de `telas_declaradas()` é gravada como `None`.
  *(marker `banco`)*
- `test_pausas_da_mesma_digitacao_viram_um_registro` — "como emi" e depois "como emitir a certidão"
  na mesma `digitacao` deixam um registro, com o texto final, e a `FraseBuscada` de "como emi" deixa de
  existir; "esqueci a senha" na mesma `digitacao` cria um segundo registro. *(marker `banco`)*
- `test_busca_acima_do_limite_nao_chama_ollama_nem_registra` — passado o limite por minuto do IP, a
  busca responde em `modo=textual_fallback`, o gerador não é chamado e nenhum `RegistroBusca` é
  criado. *(marker `banco`)*
- `test_indexador_vetoriza_frases_e_reindexa_ao_trocar_modelo` — gera vetor só para frases pendentes
  com `PROMPT_CONSULTA` e reindexa todas se `ModeloEmbedding.nome` mudar. *(marker `banco`)*
- `test_agrupamento_junta_vetores_proximos_e_soma_ocorrencias` — em domínio puro, frases próximas
  compõem um grupo com a mais frequente como `pergunta_sugerida` e totais somados; frases distantes
  ficam em grupos separados.
- `test_painel_buscas_exige_superusuario` — anônimo vai ao login e servidor comum recebe 403 em
  `faq:admin_buscas`. *(marker `banco`)*
- `test_painel_indica_lacuna_ou_faq_proxima_e_preenche_nova_faq` — grupo distante é marcado como
  lacuna, grupo próximo exibe a FAQ correspondente, e o link de criação abre `faq:admin_nova` com
  pergunta, variações e telas preenchidas sem gravar nada. *(marker `banco`)*
- `test_painel_filtra_por_periodo_e_sem_cobertura` — sem período escolhido, valem os últimos 30
  dias; com o cabeçalho filtrando por variação, a paginação conta só os grupos que sobraram; registros
  fora de `inicio`/`fim`, e os já cobertos com o alternador ligado, saem dos totais. *(marker `banco`)*
