---
spec: faq/007
versao: v1
atualizado_em: 2026-11-17
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
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
- [ ] Quando a melhor semelhança vem de um anexo ou de uma mídia (imagem/vídeo MP4), o resultado
      indica o título do anexo ou a legenda da mídia correspondente.
- [ ] Com o Ollama fora do ar, a busca não falha: recua para a busca textual sobre perguntas,
      variações e palavras-chave das FAQs visíveis.
- [ ] Buscas efetivas (a partir do tamanho mínimo) são registradas com o texto digitado, a data, a
      tela de origem (quando feitas pelo widget) e se encontraram resposta próxima. Buscas vazias ou
      curtas demais não são registradas.
- [ ] O indexador vetoriza cada frase distinta buscada no ciclo periódico e a reindexa se o modelo de
      embedding mudar, sem chamar o modelo para frases já indexadas.
- [ ] Só o superusuário acessa o painel de buscas (`faq:admin_buscas`); servidor comum recebe 403 e
      anônimo é levado ao login.
- [ ] O painel agrupa buscas semanticamente parecidas somando suas ocorrências, permite filtrar por
      período e por buscas sem cobertura, e mostra a FAQ publicada mais próxima de cada grupo.
- [ ] A partir de um grupo no painel, o administrador abre o formulário de nova FAQ já preenchido com
      a frase principal como pergunta, as demais como variações e as telas de origem marcadas.

## 3 · Domínio

A ontologia da FAQ é a de [faq/001](001-pagina-de-faq.md#3--domínio), a das mídias é a de
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


class PeriodoBuscas(StrEnum):
    SETE_DIAS = "7d"
    TRINTA_DIAS = "30d"
    NOVENTA_DIAS = "90d"
    TUDO = "tudo"


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
- Destacar o trecho exato dentro do texto do anexo ou o frame exato do vídeo no resultado da busca —
  sem dono ainda (mostra apenas o título do anexo ou a legenda da mídia).

## 5 · Peças de referência a compor
- `@apps/faq/semantica.py` → `buscar_semelhantes` (faq/005): consulta vetorial sobre FAQs, anexos e mídias.
- `@services/domain/faq/indexacao.py` → `PROMPT_CONSULTA`, `GeradorEmbedding` (faq/005): prompt e
  porta de vetorização das frases buscadas.
- `@services/domain/faq/visibilidade.py` → `visibilidades_para`, `eh_visivel` (faq/001): filtro de
  visibilidade nos resultados e na checagem de FAQ próxima.
- `@services/utils/normalization` → `normalize_text`: chave única da frase buscada.
- `@services/utils/fuzzy_matcher` → `fuzzy_match`: ranqueamento no fallback textual.
- `@apps/faq/acesso.py` → `superusuario_requerido` (faq/002): portão do painel de buscas.
- Skills: `ontologia`, `fuzzy-matcher`, `normalize-text`, `componentes-frontend`, `daisyui`,
  `htmx-skill`, `mock`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

> O comentário didático destes blocos existe só aqui e **não é portado** (CLAUDE.md §7.2).

**`services/domain/faq/busca_textual.py`** — fallback puro quando o Ollama está fora do ar. Passa os
textos brutos a `fuzzy_match` porque o módulo normaliza por dentro (skill `fuzzy-matcher`).

```python
LIMIAR_SCORE_FUZZY = 55.0
LIMIAR_DISTANCIA_BUSCA = 0.60


class PedidoBuscaFaq(BaseModel):
    consulta: str = Field(max_length=300)
    leitor: Leitor
    tela_origem: str | None = None
    limite: int = Field(default=10, ge=1, le=30)

    @field_validator("consulta", mode="before")
    @classmethod
    def _limpar(cls, valor: str) -> str:
        return valor.strip()


class ItemBuscaFaq(BaseModel):
    faq: Faq
    anexo_titulo: str | None = None      # preenchido só quando o melhor casamento veio de um anexo
    midia_legenda: str | None = None     # preenchido só quando o melhor casamento veio de imagem ou MP4


class ResultadoBuscaFaq(BaseModel):
    modo: ModoBusca
    itens: list[ItemBuscaFaq]


class BuscarTextual:
    def __call__(self, consulta: str, faqs: list[Faq], limite: int) -> list[Faq]:
        return self.pipeline(consulta, faqs, limite)

    def pipeline(self, consulta: str, faqs: list[Faq], limite: int) -> list[Faq]:
        # Cada texto buscável (pergunta, variações e palavras-chave) aponta para a sua FAQ, mantendo
        # o melhor score quando vários textos da mesma FAQ casam.
        candidatos = self._expandir_candidatos(faqs)
        if not candidatos:
            return []
        resultado = fuzzy_match(consulta, list(candidatos.keys()), limit=limite * 3)
        return self._melhores_faqs(resultado.matches, candidatos, limite)
```

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
        # Ordenar por frequência garante que a forma mais buscada pelo público vire a âncora do grupo.
        ordenadas = sorted(frases, key=lambda f: f.contagem.ocorrencias, reverse=True)
        acumuladores: list[_AcumuladorGrupo] = []
        for item in ordenadas:
            destino = self._mais_proximo(item.vetor, acumuladores, limiar)
            if destino is None:
                acumuladores.append(_AcumuladorGrupo.iniciar(item))
            else:
                destino.adicionar(item)
        grupos = [acc.consolidar() for acc in acumuladores]
        return sorted(grupos, key=lambda g: g.grupo.total_ocorrencias, reverse=True)
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
) -> ResultadoBuscaFaq:
    frase = FraseBuscada(texto=pedido.consulta)
    try:
        semelhantes = buscar_semelhantes(pedido.consulta, pedido.leitor, pedido.limite, gerador, modelo)
        relevantes = [s for s in semelhantes if s.distancia <= LIMIAR_DISTANCIA_BUSCA]
        resultado = ResultadoBuscaFaq(modo=ModoBusca.SEMANTICO, itens=_hidratar_itens(relevantes))
        teve_cobertura = any(s.distancia <= LIMIAR_LACUNA for s in relevantes)
    except OllamaIndisponivel:
        visiveis = carregar_faqs(visibilidades_para(pedido.leitor))
        faqs = buscar_textual(pedido.consulta, visiveis, pedido.limite)
        resultado = ResultadoBuscaFaq(
            modo=ModoBusca.TEXTUAL_FALLBACK,
            itens=[ItemBuscaFaq(faq=f) for f in faqs],
        )
        teve_cobertura = bool(faqs)
    registrar_busca(frase, pedido.tela_origem, teve_cobertura)
    return resultado


@transaction.atomic
def registrar_busca(frase: FraseBuscada, tela_origem: str | None, teve_cobertura: bool) -> None:
    # get_or_create por `chave` evita chamar o Ollama para grafias equivalentes da mesma dúvida.
    alvo, _ = FraseBuscadaModel.objects.get_or_create(
        chave=frase.chave,
        defaults={"texto_representativo": frase.texto},
    )
    RegistroBuscaModel.objects.create(
        frase=alvo,
        texto_original=frase.texto,
        tela_origem=tela_origem,
        teve_cobertura=teve_cobertura,
    )
```

**`apps/faq/indexador.py`** — estende o `ciclo` de faq/005 para vetorizar também as frases buscadas
pendentes com `PROMPT_CONSULTA`, permitindo comparar cada grupo contra `TrechoIndexado` sem chamar o
Ollama quando o administrador abre o painel.

```python
def _indexar_frases_buscadas(gerador: GeradorEmbedding, modelo: ModeloEmbedding) -> None:
    pendentes = list(FraseBuscadaModel.objects.filter(Q(vetor__isnull=True) | ~Q(modelo=modelo.nome))[:LOTE_FRASES])
    if not pendentes:
        return
    entradas = [EntradaEmbedding(texto=PROMPT_CONSULTA.format(consulta=f.texto_representativo)) for f in pendentes]
    vetores = gerador(PedidoEmbedding(modelo=modelo, entradas=entradas))
    with transaction.atomic():
        for obj, vetor in zip(pendentes, vetores, strict=True):
            obj.vetor = vetor
            obj.modelo = modelo.nome
        FraseBuscadaModel.objects.bulk_update(pendentes, ["vetor", "modelo"])
```

**`apps/faq/sugestoes.py`** — agrega os registros do período, chama `AgruparBuscas` e resolve a FAQ
publicada mais próxima pelo centróide de cada grupo (consultando `TrechoIndexado` direto no Postgres).

```python
def sugerir_grupos(
    periodo: PeriodoBuscas,
    apenas_sem_cobertura: bool,
    modelo: ModeloEmbedding,
) -> list[GrupoBuscas]:
    frases = _carregar_frases_vetorizadas(periodo, apenas_sem_cobertura, modelo, MAXIMO_FRASES_AGRUPAMENTO)
    grupos_com_centroide = agrupar_buscas(frases)
    return [_anexar_faq_proxima(item, modelo) for item in grupos_com_centroide]
```

**Rotas e interface:**

| Rota | Acesso | Comportamento |
|---|---|---|
| `faq:buscar` | aberta (HTMX GET) | se `len(q.strip()) < MINIMO_CARACTERES_BUSCA`, devolve o partial da página inteira; senão chama `buscar_na_faq` e devolve `_resultados_busca.html` |
| `faq:widget_buscar` | aberta (HTMX GET) | igual, com `tela_origem` opcional; com `q` curto/vazio restaura o partial de `faq:widget_tela` ou `faq:widget_todas` |
| `faq:admin_buscas` | `superusuario_requerido` | lista os `GrupoBuscas` com filtros `periodo` e `so_sem_cobertura`, e link para `faq:admin_nova` (`faq/002`) pré-preenchido via query string (`pergunta`, `variacao`, `tela`) |

O gatilho das caixas de busca usa `hx-trigger="input changed delay:500ms, search"` para enviar só
quando o leitor pausa ou confirma.

## 7 · Caveats

**`FraseBuscada.chave` é guardada em coluna, embora seja derivada.** A normalização `normalize_text`
não tem equivalente direto em SQL, e agrupar ocorrências equivalentes por `chave` é o que impede
chamar o Ollama repetidamente para a mesma frase. Se a regra de normalização mudar, chaves antigas e
novas deixam de convergir.

**O fallback textual não lê o conteúdo dos anexos.** Quando o Ollama cai, `BuscarTextual` consulta
apenas pergunta, variações e palavras-chave via `fuzzy_match`, porque varrer texto bruto de anexos em
tempo de request seria lento. O custo é perda temporária de alcance sobre anexos e mídias durante uma
queda do serviço de embeddings.

**Prefixos intermediários durante a digitação dependem do debounce do navegador.** Só o tamanho
mínimo bloqueia no servidor, e o `delay:500ms` segura as teclas rápidas sem manter estado de sessão.
Alguém digitando em pausas longas pode gravar um termo incompleto no histórico.

**O agrupamento é guloso e cortado no teto de frases mais frequentes.** Rodar em memória sobre até
500 frases evita biblioteca pesada de clusterização e mantém o painel responsivo em milissegundos. O
custo é depender da ordem por frequência e ignorar termos de uma só ocorrência se o histórico crescer
além do teto.

**A cobertura do dia (`teve_cobertura`) e a FAQ mais próxima no painel podem divergir.** A primeira
congela se o usuário encontrou resposta na hora da busca; a segunda consulta as FAQs publicadas hoje
para mostrar se a lacuna continua aberta. Um grupo antigo "sem cobertura" pode já aparecer coberto por
uma FAQ publicada depois.

**Frases buscadas durante queda do Ollama entram no painel só após o próximo ciclo do indexador.** O
painel lê apenas frases que já possuem vetor no modelo ativo para continuar abrindo sem depender do
Ollama no ar. O atraso máximo é o intervalo do indexador depois que o serviço volta.

## 8 · Testes (TDD)
- `test_busca_semantica_retorna_faqs_e_respeita_visibilidade` — encontra FAQ publicada por semelhança
  (indicando título do anexo ou legenda da mídia quando o match vem deles), omite interna para
  anônimo e rascunho para todos. *(marker `banco`)*
- `test_busca_recua_para_fallback_textual_quando_ollama_cai` — com gerador levantando
  `OllamaIndisponivel`, a busca retorna FAQs via `fuzzy_match` em `modo=textual_fallback` sem erro
  HTTP. *(marker `banco`)*
- `test_busca_curta_ou_vazia_nao_registra_e_restaura_lista` — texto menor que
  `MINIMO_CARACTERES_BUSCA` não cria `RegistroBusca` e devolve a listagem padrão na página e no
  widget. *(marker `banco`)*
- `test_buscas_equivalentes_compartilham_frase_buscada` — `"Como tiro a certidão?"` e `"como tiro a
  certidao"` criam dois `RegistroBusca` (um com `tela_origem`) ligados à mesma `FraseBuscada`.
  *(marker `banco`)*
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
- `test_painel_filtra_por_periodo_e_sem_cobertura` — registros fora da janela ou já cobertos são
  excluídos dos totais quando os filtros correspondentes estão ativos. *(marker `banco`)*
