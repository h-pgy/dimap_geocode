---
spec: certidao_lancamento/001
versao: v6
atualizado_em: 2026-09-23
testes_tdd: true
implementado: true
markers_obrigatorios: [banco, artefato]
changelog:
  - v1: versão inicial
  - v2: composição com a gaveta de lote refatorada e LotePorIdentificador já implementado
  - v3: máscara progressiva no campo do processo SEI (data-mascara) e redesenho do glifo da ação
  - v4: inscrição da ação no catálogo central de competências (registro.py)
  - v5: router renomeado para acoes_lote com enforcement de SQL válido na borda
  - v6: "[bugfix] endereço do lote no modal, recusa de formulário inteira, emissão como desfecho e nota do rodapé em duas linhas"
---

# SPEC certidao_lancamento/001 — Certidão de Existência de Lançamento de um lote

## 1 · User story
O auditor fiscal com a concessão emite, pela gaveta do lote localizado, a Certidão de Existência de
Lançamento daquele lote para o interessado de um processo SEI, para obter um PDF selado que atesta o
lançamento do IPTU e mostra onde o imóvel fica.

## 2 · Condições de pronto
- [x] A gaveta do lote traz o poço **"Ações"** com o botão **"Emitir certidão de lançamento"** só para
      quem tem a concessão e apenas quando o lote possui **SQL válido**; sem nenhuma ação liberada ou em
      lote sem SQL (ex.: municipal), o poço **não aparece**.
- [x] O botão abre um modal que pede o **número do processo SEI** e o **nome do interessado**.
- [x] O campo do processo SEI possui **máscara progressiva** (`data-mascara="0000.0000/0000000-0"` via
      `@static/src/js/ui/campo_mascarado.js`), permitindo que a pessoa digite apenas números e a formatação
      `NNNN.AAAA/NNNNNNN-D` seja aplicada automaticamente em tempo real.
- [x] Processo fora do formato `NNNN.AAAA/NNNNNNN-D`, ou interessado em branco, volta ao modal com o
      campo destacado e a mensagem em português.
- [x] Lote **sem lançamento ativo**, **condominial** ou que **não existe mais** no GeoSampa abre o
      modal com o aviso de que a certidão não pode ser emitida pelo sistema, sem formulário — e a
      emissão recusa pelo mesmo critério.
- [x] Na emissão, o lote é **lido de novo no GeoSampa** pelo identificador do polígono — nenhum dado
      do imóvel vem do navegador.
- [x] A certidão traz o requerimento (interessado e processo), a identificação do imóvel, o despacho
      que declara o lançamento pelo SQL, a **planta de localização** do lote e o fecho selado.
- [x] O rodapé de toda página declara que a certidão foi emitida de forma automatizada e **quando os
      dados cadastrais foram consultados**.
- [x] A certidão emitida entra no **acervo**, confere pelo código e a segunda via devolve os mesmos
      bytes; o modal troca o formulário pelo botão de download.
- [x] A emissão fica **registrada** no Registro de Ações, com o código da certidão como alvo.
- [x] O design do poço de ações, do modal, do aviso e da confirmação foi aprovado no mock. O ícone da
      ação mora em caminho único e centralizado (`static/src/acoes/certidao_lancamento/emitir/icones/pequeno.svg`),
      satisfazendo o system check `competencias.E003`; os templates da aplicação consomem o ícone
      exclusivamente de forma centralizada (via templatetag `{% load icones %}{% icone_acao ... "pequeno" %}`),
      sem jamais recriar ou duplicar o SVG inline nos templates HTML.

## 3 · Domínio
A certidão é ato administrativo sobre um [LoteAttributes](../localizacao_lote/001-dados-do-lote-na-gaveta.md#3--domínio)
que `possui_lancamento`. Ao envelope da SPEC [documentos_oficiais/007](../documentos_oficiais/007-envelope-do-ato-e-selo-no-papel.md)
esta SPEC pergunta quem assina e sob qual código; ao acervo da [008](../documentos_oficiais/008-acervo-e-conferencia.md),
onde a via fica; à [planta](../documentos_oficiais/011-planta-de-localizacao.md), a imagem do lote em
destaque; e ao [LotePorIdentificador](../localizacao_lote/003-lotes-do-desenho.md#3--domínio) (já
implementado em `services/domain/lote_geocod`), o lote relido na emissão.

As ações sobre o lote ganham aqui o **router de ações do lote** (`apps/acoes_lote`): um contrato em
código diz quais ações o lote oferece, a rota faz o enforcement de receber um número de SQL formalmente
válido (`SSS.QQQ.LLLL-D`), e a gaveta recebe só as liberadas ao perfil.

**`services/domain/certidao_lancamento/models.py`**

```python
PADRAO_PROCESSO_SEI = r"^\d{4}\.\d{4}/\d{7}-\d$"


class PedidoCertidao(BaseModel):
    """O que o modal colhe: quem pede e em qual processo. É o que instrui a certidão junto com o lote."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    processo: str = Field(pattern=PADRAO_PROCESSO_SEI)
    interessado: str = Field(min_length=3, max_length=200)


class CertidaoLancamentoInput(BaseModel):
    """Tudo já apurado: o domínio do documento não vai ao WFS nem ao banco."""

    model_config = ConfigDict(frozen=True)

    envelope: EnvelopeAto
    pedido: PedidoCertidao
    imovel: LoteAttributes
    planta: PlantaLocalizacao
    # O instante da leitura do lote no GeoSampa: é ele, e não o da assinatura, que o rodapé declara.
    consultado_em: AwareDatetime
    base_url: str

    @model_validator(mode="after")
    def _imovel_certificavel(self) -> Self:
        if self.imovel.is_condominio:
            raise ValueError("Lote condominial: a certidão ainda não é emitida pelo sistema.")
        if not self.imovel.possui_lancamento:
            raise ValueError("O lote não possui lançamento ativo no cadastro.")
        return self
```

**`apps/acoes_lote/estrutura.py`** — o contrato do router de lote.

```python
PADRAO_SQL = r"^\d{3}\.\d{3}\.\d{4}-\d$"


class AcaoDeLote(BaseModel):
    """Uma ação oferecida sobre o lote fiscal. A rota recebe o identificador do polígono e o SQL."""

    model_config = ConfigDict(frozen=True)

    acao: AcaoImplementada
    url_name: str   # rota do modal da ação
    variante_icone: VarianteIcone = VarianteIcone.PEQUENO


class ContratoAcoesLote(BaseModel):
    """Coleção explícita do que opera sobre um lote fiscal."""

    model_config = ConfigDict(frozen=True)

    itens: tuple[AcaoDeLote, ...]
```

**Mock:** [001-mock-certidao-de-um-lote.html](001-mock-certidao-de-um-lote.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Certidão de conjunto de lotes — SPEC [certidao_lancamento/002](002-certidao-do-conjunto.md).
- Lote condominial — sem dono ainda (provável caso particular da certidão "a menor").
- Certidão negativa (inexistência de lançamento) — sem dono; emitida manualmente pelo técnico.
- Conferência do dígito verificador do processo SEI — sem dono ainda; só o formato é conferido.
- Card da ação no painel — não entra: a ação só existe sobre um lote localizado.

## 5 · Peças de referência a compor
- `@apps/competencias/emissao_certidao.py` → `emitir_certidao_atos`: sequência envelope → render → selo → acervo.
- `@services/domain/certidao_atos_administrativos/certidao.py` → `MontarCertidaoAtos`/`CertidaoAtos`: o molde do tipo selado.
- `@apps/competencias/protecao.py` → `acao_protegida`, `registrar_ato`.
- `@apps/competencias/registro.py` → `_construir_registro`: ponto único de inscrição no catálogo de ações do sistema.
- `@apps/competencias/resolucao.py` → `slugs_liberados`: o conjunto que o router filtra.
- `@services/utils/erros_formulario` → `Formulario`, `LeitorDeFormulario`: o modal com realce.
- `@services/domain/lote_geocod` → `LotePorIdentificador`, `LoteAttributes`, `LoteFeature`.
- `@templates/lote_geocoder/partials/_gaveta_lote.html` → a gaveta lateral montada por `MontarGavetaLote` (SPEC localizacao_lote/001): ponto de injeção condicional do poço de ações de lote via HTMX quando há SQL.
- `@templates/core/home.html` → `#poco-modal`: poço dos modais de ações do lote.
- `@static/src/js/ui/campo_mascarado.js` → máscara progressiva no input (`[data-mascara="0000.0000/0000000-0"]`).
- `@services/domain/planta_localizacao` → `GerarPlantaLocalizacao` (SPEC documentos_oficiais/011).
- Skills: `acao-administrativa`, `documento-oficial`, `erros-de-formulario`, `painel`, `mock`, `escrever-testes`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/certidao_lancamento/certidao.py`** — o único lugar em que esta certidão é redigida.

```python
TITULO = "Certidão de Existência de Lançamento"
DESPACHO = "Solicitação deferida."
FUNDAMENTO = (
    "Com base nas informações consultadas de forma automatizada junto à base de dados oficial do "
    "Município de São Paulo, declara-se que o imóvel acima identificado possui lançamento do Imposto "
    "Predial e Territorial Urbano (IPTU) pelo contribuinte número {sql}."
)
LARGURA_PLANTA_MM = 150.0


class MontarCertidaoLancamentoInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    certidao: CertidaoLancamentoInput
    selo: SeloImpresso
    quadro: QuadroSeloConfig


class MontarCertidaoLancamento:
    def __call__(self, pedido: MontarCertidaoLancamentoInput) -> ConteudoDocumento:
        return self.pipeline(pedido)

    def pipeline(self, pedido: MontarCertidaoLancamentoInput) -> ConteudoDocumento:
        return ConteudoDocumento(
            titulo=TITULO,
            nome_arquivo=f"certidao_lancamento_{pedido.certidao.envelope.codigo}.pdf",
            blocos=self._blocos(pedido),
        )

    def _blocos(self, pedido: MontarCertidaoLancamentoInput) -> tuple[Bloco, ...]:
        certidao = pedido.certidao
        return (
            Titulo(texto=TITULO),
            Subtitulo(texto="Requerimento"),
            Paragrafo(texto=self._requerimento(certidao.pedido)),
            Subtitulo(texto="Identificação do Imóvel"),
            Paragrafo(texto=self._identificacao(certidao.imovel)),
            Subtitulo(texto="Despacho"),
            Paragrafo(texto=DESPACHO),
            Paragrafo(texto=FUNDAMENTO.format(sql=certidao.imovel.sql)),
            Subtitulo(texto="Localização do Imóvel"),
            ImagemRaster(conteudo=certidao.planta.png, largura_mm=LARGURA_PLANTA_MM),
            Paragrafo(texto=f"São Paulo, {por_extenso(certidao.envelope.emitido_em)}."),
            SeloDeFecho(selo=pedido.selo, quadro=pedido.quadro),
        )

    def _identificacao(self, imovel: LoteAttributes) -> str:
        codlog_txt = f" (codlog: {imovel.codlog[:5]}-{imovel.codlog[5:]})" if imovel.codlog else ""
        texto = (
            f"O imóvel objeto desta certidão está localizado no endereço {imovel.nome_logradouro}{codlog_txt}, "
            f"número {imovel.numero_porta}"
        )
        return f"{texto}, complemento {imovel.complemento}." if imovel.complemento else f"{texto}."

    def _requerimento(self, pedido: PedidoCertidao) -> str:
        return f"Interessado: {pedido.interessado}. Processo SEI nº {pedido.processo}."


class CertidaoLancamento:
    """O tipo: conteúdo + papel selado com nota de rodapé + tema. Quem emite só preenche o DTO."""

    def __init__(self, tema: Tema, config: MarcacaoConfig, selo_config: SeloConfig) -> None:
        self._montar = MontarCertidaoLancamento()
        self._tema = tema
        self._config = config
        self._selo_config = selo_config
        self._renderizar = RenderizarDocumentoOficial(tema)

    def pipeline(self, pedido: CertidaoLancamentoInput) -> DocumentoRenderizado:
        selo = montar_selo_impresso(SeloImpressoInput(
            envelope=pedido.envelope,
            base_url=pedido.base_url,
        ))
        conteudo = self._montar(MontarCertidaoLancamentoInput(
            certidao=pedido,
            selo=selo,
            quadro=self._selo_config.fecho,
        ))
        marcacao = marcacao_fazenda_dimap_selado_com_nota(
            self._config,
            self._tema,
            selo,
            self._selo_config.compacto,
            nota=self._nota(pedido),
        )
        return self._renderizar(RenderizarDocumentoInput(conteudo=conteudo, marcacao=marcacao))

    def _nota(self, pedido: CertidaoLancamentoInput) -> tuple[str, ...]:
        # `consultado_em` chega no fuso local, resolvido pela orquestração: o domínio não importa
        # `django.utils.timezone`.
        momento = pedido.consultado_em
        # Cada item da tupla é UMA linha da faixa. Numa frase só o rodapé estoura e quebra no meio.
        return (
            "Certidão emitida de forma automatizada",
            f"Dados cadastrais consultados no GeoSampa em {momento:%d/%m/%Y} às {momento:%H:%M}",
        )
```

**`services/domain/documento_oficial/marcacoes_concretas/fazenda_dimap_selado_com_nota.py`** —
papel novo ao lado; `fazenda_dimap_selado` não muda.

```python
def marcacao_fazenda_dimap_selado_com_nota(
    config: MarcacaoConfig,
    tema: Tema,
    selo: SeloImpresso,
    quadro: QuadroSeloConfig,
    *,
    nota: tuple[str, ...],
) -> MarcacaoDocumento:
    # O mesmo papel selado, com a nota empilhada acima do endereço. A nota é de CADA emissão, como o selo.
    rodape = MarcasEmpilhadas(
        (
            NotaDeRodape(nota, tema.estilo_rodape_marca, tema.entrelinha_marca_mm),
            RodapeEndereco(config.endereco, tema.estilo_rodape_marca, tema.entrelinha_marca_mm),
            NumeracaoPaginas(tema.estilo_rodape_marca, tema.entrelinha_marca_mm),
        ),
        Posicao.INFERIOR,
    )
    ...
```

**`apps/certidao_lancamento/acoes_declaradas.py`**

```python
ACAO_EMITIR_CERTIDAO_LANCAMENTO = instanciar_acao(
    slug="certidao_lancamento.emitir",
    nome="Emitir certidão de existência de lançamento",
    nome_curto="Certidão de lançamento",
    tooltip="Emite o PDF selado que atesta o lançamento do IPTU do lote.",
    url_name="certidao_lancamento:modal",
    variantes_icone=frozenset({VarianteIcone.PEQUENO}),
    estrutural=False,
    alcance=None,
)
```

**`apps/competencias/registro.py`** — inscrição da ação no catálogo central de competências (skill `acao-administrativa` §3.2).

```python
from apps.certidao_lancamento.acoes_declaradas import ACAO_EMITIR_CERTIDAO_LANCAMENTO


def _construir_registro() -> RegistroAcoes:
    return RegistroAcoes(
        acoes=(
            ...,
            ACAO_EMITIR_CERTIDAO_LANCAMENTO,
        )
    )
```

**`static/src/acoes/certidao_lancamento/emitir/icones/pequeno.svg`** — ícone da ação (centralizado no projeto)

Conforme a convenção do projeto (skill `acao-administrativa` §3.3) e o system check `competencias.E003`,
o ícone da ação mora em um arquivo SVG único e centralizado na raiz de assets da ação, **NUNCA** sendo
recriado ou duplicado inline nos templates HTML da aplicação.

O SVG herda as cores do contexto (`currentColor`) e combina a base oficial do documento com a casinha
no canto superior esquerdo:

```xml
<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path fill-rule="evenodd" clip-rule="evenodd" d="M10.9436 1.25H13.0564C14.8942 1.24998 16.3498 1.24997 17.489 1.40314C18.6614 1.56076 19.6104 1.89288 20.3588 2.64124C20.6516 2.93414 20.6516 3.40901 20.3588 3.7019C20.0659 3.9948 19.591 3.9948 19.2981 3.7019C18.8749 3.27869 18.2952 3.02502 17.2892 2.88976C16.2615 2.75159 14.9068 2.75 13 2.75H11C9.09318 2.75 7.73851 2.75159 6.71085 2.88976C5.70476 3.02502 5.12511 3.27869 4.7019 3.7019C4.27869 4.12511 4.02502 4.70476 3.88976 5.71085C3.75159 6.73851 3.75 8.09318 3.75 10V14C3.75 15.9068 3.75159 17.2615 3.88976 18.2892C4.02502 19.2952 4.27869 19.8749 4.7019 20.2981C5.12511 20.7213 5.70476 20.975 6.71085 21.1102C7.73851 21.2484 9.09318 21.25 11 21.25H13C14.9068 21.25 16.2615 21.2484 17.2892 21.1102C18.2952 20.975 18.8749 20.7213 19.2981 20.2981C19.994 19.6022 20.2048 18.5208 20.2414 15.9892C20.2474 15.575 20.588 15.2441 21.0022 15.2501C21.4163 15.2561 21.7472 15.5967 21.7412 16.0108C21.7061 18.4383 21.549 20.1685 20.3588 21.3588C19.6104 22.1071 18.6614 22.4392 17.489 22.5969C16.3498 22.75 14.8942 22.75 13.0564 22.75H10.9436C9.10583 22.75 7.65019 22.75 6.51098 22.5969C5.33856 22.4392 4.38961 22.1071 3.64124 21.3588C2.89288 20.6104 2.56076 19.6614 2.40314 18.489C2.24997 17.3498 2.24998 15.8942 2.25 14.0564V9.94358C2.24998 8.10582 2.24997 6.65019 2.40314 5.51098C2.56076 4.33856 2.89288 3.38961 3.64124 2.64124C4.38961 1.89288 5.33856 1.56076 6.51098 1.40314C7.65019 1.24997 9.10582 1.24998 10.9436 1.25ZM18.1131 7.04556C19.1739 5.98481 20.8937 5.98481 21.9544 7.04556C23.0152 8.1063 23.0152 9.82611 21.9544 10.8869L17.1991 15.6422C16.9404 15.901 16.7654 16.076 16.5693 16.2289C16.3387 16.4088 16.0892 16.563 15.8252 16.6889C15.6007 16.7958 15.3659 16.8741 15.0187 16.9897L12.9351 17.6843C12.4751 17.8376 11.9679 17.7179 11.625 17.375C11.2821 17.0321 11.1624 16.5249 11.3157 16.0649L11.9963 14.0232C12.001 14.0091 12.0056 13.9951 12.0102 13.9813C12.1259 13.6342 12.2042 13.3993 12.3111 13.1748C12.437 12.9108 12.5912 12.6613 12.7711 12.4307C12.924 12.2346 13.099 12.0596 13.3578 11.8009C13.3681 11.7906 13.3785 11.7802 13.3891 11.7696L18.1131 7.04556ZM20.8938 8.10622C20.4188 7.63126 19.6488 7.63126 19.1738 8.10622L18.992 8.288C19.0019 8.32149 19.0132 8.3571 19.0262 8.39452C19.1202 8.66565 19.2988 9.02427 19.6372 9.36276C19.9757 9.70125 20.3343 9.87975 20.6055 9.97382C20.6429 9.9868 20.6785 9.99812 20.712 10.008L20.8938 9.8262C21.3687 9.35124 21.3687 8.58118 20.8938 8.10622ZM19.5664 11.1536C19.2485 10.9866 18.9053 10.7521 18.5766 10.4234C18.2479 10.0947 18.0134 9.75146 17.8464 9.43357L14.4497 12.8303C14.1487 13.1314 14.043 13.2388 13.9538 13.3532C13.841 13.4979 13.7442 13.6545 13.6652 13.8202C13.6028 13.9511 13.5539 14.0936 13.4193 14.4976L13.019 15.6985L13.3015 15.981L14.5024 15.5807C14.9064 15.4461 15.0489 15.3972 15.1798 15.3348C15.3455 15.2558 15.5021 15.159 15.6468 15.0462C15.7612 14.957 15.8686 14.8513 16.1697 14.5503L19.5664 11.1536ZM7.25 9C7.25 8.58579 7.58579 8.25 8 8.25H14.5C14.9142 8.25 15.25 8.58579 15.25 9C15.25 9.41421 14.9142 9.75 14.5 9.75H8C7.58579 9.75 7.25 9.41421 7.25 9ZM7.25 13C7.25 12.5858 7.58579 12.25 8 12.25H10.5C10.9142 12.25 11.25 12.5858 11.25 13C11.25 13.4142 10.9142 13.75 10.5 13.75H8C7.58579 13.75 7.25 13.4142 7.25 13ZM7.25 17C7.25 16.5858 7.58579 16.25 8 16.25H9.5C9.91421 16.25 10.25 16.5858 10.25 17C10.25 17.4142 9.91421 17.75 9.5 17.75H8C7.58579 17.75 7.25 17.4142 7.25 17Z" fill="currentColor"/>
  <path d="M1.2 5L4.5 2.2L7.8 5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M2.2 4.8V8.8H6.8V4.8" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M3.8 8.8V6.6H5.2V8.8" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
```

**`apps/acoes_lote/declaradas.py` e `resolucao.py`** — o router do lote: contrato × perfil.

```python
ACOES_LOTE = ContratoAcoesLote(
    itens=(
        AcaoDeLote(acao=ACAO_EMITIR_CERTIDAO_LANCAMENTO, url_name="certidao_lancamento:modal"),
    )
)


def acoes_liberadas(slugs: frozenset[str]) -> tuple[AcaoDeLote, ...]:
    # O router filtra; a rota decide. Esconder o botão não protege nada.
    return tuple(item for item in ACOES_LOTE.itens if item.acao.acao.slug in slugs)
```

**`apps/acoes_lote/views.py`** — rota aberta: recebe SQL e ID; anônimo ou lote sem SQL válido recebe o poço vazio, não um login.

```python
class ConsultaAcoesLote(BaseModel):
    """Enforcement: toda ação de lote exige o número de contribuinte (SQL) válido e o id do polígono."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    sql: str = Field(pattern=PADRAO_SQL)
    id: str = Field(pattern=r"^\d+$")


@require_GET
def acoes(request: HttpRequest) -> HttpResponse:
    try:
        consulta = ConsultaAcoesLote.model_validate(request.GET.dict())
    except ValidationError:
        return HttpResponse("")
    itens = acoes_liberadas(slugs_liberados(request.user))
    return render(request, TEMPLATE_POCO_ACOES, {"itens": itens, "id_entidade": consulta.id, "sql": consulta.sql})
```

```html
{# templates/lote_geocoder/partials/_gaveta_lote.html — a busca conhece o router, não as ações #}
{% if gaveta.lote.sql %}
  <div hx-get="{% url 'acoes_lote:acoes' %}?sql={{ gaveta.lote.sql }}&id={{ gaveta.lote.id_poligono }}" hx-trigger="load" hx-swap="outerHTML"></div>
{% endif %}
```

**`apps/certidao_lancamento/views.py`**

```python
@acao_protegida(ACAO_EMITIR_CERTIDAO_LANCAMENTO)
@require_GET
def modal(request: HttpRequest) -> HttpResponse:
    # contexto_modal decide entre formulário e aviso (lote que sumiu, sem lançamento, condominial).
    lote = ler_lote(request.GET.get("id", ""))
    return render(request, TEMPLATE_MODAL, contexto_modal(lote))


@acao_protegida(ACAO_EMITIR_CERTIDAO_LANCAMENTO)
@require_POST
def emitir(request: HttpRequest) -> HttpResponse:
    leitura = ler_pedido_certidao(request.POST)
    lote = ler_lote(request.POST.get("id", ""))
    if leitura.dto is None or lote is None or not lote.pode_certificar:
        return _modal_recusado(request, lote, request.POST, leitura.recusa)
    desfecho = emitir_certidao_lancamento(
        autor=_perfil(request),
        pedido=leitura.dto,
        lote=lote,
        base_url=request.build_absolute_uri("/"),
    )
    # Ortofoto indisponível recusa a emissão (SPEC refatoracao/002).
    if desfecho.documento is None:
        return _modal_recusado(request, lote, request.POST, desfecho.recusa)
    registrar_ato(
        request,
        operacao="emitir",
        alvo_tipo="documento",
        alvo_identificador=desfecho.documento.codigo,
    )
    return render(request, TEMPLATE_CERTIDAO_EMITIDA, {"codigo": desfecho.documento.codigo})
```

**`templates/core/home.html`** — o poço dos modais que as ações do lote abrem e carregamento da máscara.

```html
<div id="poco-modal" class="poco-modal"></div>
```
E no `{% block scripts %}`:
```html
<script type="module" src="{% static 'js/ui/campo_mascarado.js' %}"></script>
```

**`templates/acoes_lote/partials/_poco_acoes.html`** — sem item liberado, nada é desenhado; ícone centralizado via `icone_acao`.

```html
{% load icones %}
{% if itens %}
  <div class="card-well p-4 flex flex-col gap-2">
    <p class="text-overline">Ações</p>
    {% for item in itens %}
      <button type="button" class="btn btn-onsen btn-sm gap-2"
              hx-get="{% url item.url_name %}?id={{ id_entidade }}&sql={{ sql }}"
              hx-target="#poco-modal">
        <span class="w-4 h-4 shrink-0 flex items-center justify-center">
          {% icone_acao item.acao.acao.slug "pequeno" %}
        </span>
        {{ item.acao.acao.nome_curto }}
      </button>
    {% endfor %}
  </div>
{% endif %}
```

**`templates/certidao_lancamento/_modal.html`** — modal de emissão com máscara progressiva, ícone
centralizado e a tarja de recusa do projeto.

```html
{% load icones %}
<div class="modal modal-open modal-glass" role="dialog">
  <div class="modal-box modal-box-glass glass-panel-thick p-6 flex flex-col gap-5 w-11/12 max-w-lg shadow-2xl">
    <header class="flex items-center gap-3 border-b border-rocha-950/10 pb-4">
      <span class="icon-bubble w-11 h-11 bg-agua-500/15 border-agua-600/30 text-agua-700 shrink-0">
        <span class="w-6 h-6 flex items-center justify-center">
          {% icone_acao "certidao_lancamento.emitir" "pequeno" %}
        </span>
      </span>
      <div class="min-w-0">
        <p class="text-overline">Certidão de Existência de Lançamento</p>
        <p class="text-base font-bold text-rocha-950 leading-tight truncate">SQL {{ lote.feature.attributes.sql }}</p>
        <p class="text-xs text-base-content/70 truncate">{{ lote.feature.attributes.endereco_completo }}</p>
      </div>
    </header>

    {% if lote.pode_certificar %}
      {% include "partials/_tarja_recusa.html" with erros=recusa.mensagens titulo="Não foi possível emitir a certidão" %}

      <form hx-post="{% url 'certidao_lancamento:emitir' %}" hx-target="#poco-modal" hx-swap="outerHTML" class="flex flex-col gap-4">
        <input type="hidden" name="id" value="{{ lote.feature.attributes.id_poligono }}">

        <div class="flex flex-col gap-1">
          <label class="text-overline text-xs">Processo SEI</label>
          <input type="text"
                 name="processo"
                 value="{{ valores.processo }}"
                 data-mascara="0000.0000/0000000-0"
                 placeholder="0000.0000/0000000-0"
                 class="input input-glass input-sm w-full font-mono {{ recusa.realce.processo }}"
                 autofocus>
          <span class="form-field-hint">Formato obrigatório: NNNN.AAAA/NNNNNNN-D (máscara automática ao digitar)</span>
        </div>

        <div class="flex flex-col gap-1">
          <label class="text-overline text-xs">Nome do interessado</label>
          <input type="text"
                 name="interessado"
                 value="{{ valores.interessado }}"
                 placeholder="Nome completo ou razão social"
                 class="input input-glass input-sm w-full {{ recusa.realce.interessado }}">
          <span class="form-field-hint">Consta no requerimento da certidão oficial.</span>
        </div>

        <div class="modal-action mt-2 pt-3 border-t border-rocha-950/10">
          <button type="button" class="btn btn-glass btn-sm" onclick="document.getElementById('poco-modal').innerHTML = ''">Cancelar</button>
          <button type="submit" class="btn btn-onsen btn-sm">Emitir certidão</button>
        </div>
      </form>
    {% else %}
      {% include "partials/_tarja_recusa.html" with erros=motivos_recusa_lote titulo="Certidão indisponível para este lote" %}
      <div class="modal-action mt-2 pt-3 border-t border-rocha-950/10">
        <button type="button" class="btn btn-glass btn-sm" onclick="document.getElementById('poco-modal').innerHTML = ''">Fechar</button>
      </div>
    {% endif %}
  </div>
  <label class="modal-backdrop" onclick="document.getElementById('poco-modal').innerHTML = ''">Fechar</label>
</div>
```

**`apps/certidao_lancamento/emissao.py`** — orquestração; único ponto que lê settings.

```python
class LoteLido(BaseModel):
    """O lote como o GeoSampa respondeu na hora: geometria no CRS métrico (a planta a usa) e o instante."""

    feature: LoteFeature
    consultado_em: AwareDatetime


def ler_lote(id_poligono: str) -> LoteLido | None:
    # None = o polígono não existe mais na camada; o modal mostra o aviso em vez do formulário.
    feature = LotePorIdentificador(build_fetcher(settings))(LotePorIdentificadorInput(
        id_poligono=id_poligono,
        layer_name=WFS_LAYER_LOTE_CIDADAO,
        output_crs=MAP_INTERPOLATION_CRS,
    ))
    if feature is None:
        return None
    return LoteLido(feature=feature, consultado_em=timezone.localtime())


def emitir_certidao_lancamento(
    autor: Perfil,
    pedido: PedidoCertidao,
    lote: LoteLido,
    base_url: str,
) -> DesfechoEmissao:
    imovel = lote.feature.attributes
    envelope = EnvelopeAto(
        codigo=gerar_codigo(),
        acao=ACAO_EMITIR_CERTIDAO_LANCAMENTO.acao.slug,
        operacao="emitir",
        # Extraído de `competencias/emissao_certidao._envelope`, que passa a usá-lo: autor e cargo
        # substituído se redigem num lugar só para as duas certidões.
        autor=autor_do_ato(autor),
        alvo=AlvoDoAto(tipo="lote", identificador=imovel.sql or ""),
        emitido_em=timezone.localtime(),
        # O interessado é pessoa: fica no PDF, que só circula com quem o recebeu, e fora da ficha pública.
        campos_publicos=("contribuinte", "processo"),
        extras={"contribuinte": imovel.sql, "processo": pedido.processo},
    )
    planta = GerarPlantaLocalizacao(build_wms_fetcher(settings))(PlantaLocalizacaoInput(
        camadas=(CamadaPlanta(geometrias=(lote.feature.geometry,), estilo=EstiloGeometria.DESTAQUE),),
        config=planta_config(),
    ))
    renderizado = _tipo_certidao()(CertidaoLancamentoInput(
        envelope=envelope,
        pedido=pedido,
        imovel=imovel,
        planta=planta,
        consultado_em=lote.consultado_em,
        base_url=base_url,
    ))
    selado = selar_documento(SelarInput(
        pdf=renderizado.pdf,
        dados=montar_envelope(envelope),
        campos_publicos=envelope.campos_publicos,
        segredo=settings.ASSINATURA_SEGREDO,
        id_chave=settings.ASSINATURA_ID_CHAVE,
    ))
    return DesfechoEmissao(documento=guardar_documento(selado, envelope, execucao=None))
```

**`apps/painel/checks.py`**

```python
ACOES_SEM_CARD: frozenset[str] = frozenset({
    "user_admin.editar_servidor",
    "unidades.editar_unidade",
    # Opera sobre um lote localizado: o botão mora na gaveta do lote (apps/acoes_lote).
    "certidao_lancamento.emitir",
})
```

## 7 · Caveats
O router de ações de lote (`apps/acoes_lote`) é um contrato próprio, parecido com o
`ItemAcao` do painel. O card do painel e o botão da gaveta têm destino, variante de ícone e
parâmetro diferentes, e reusar o `ItemAcao` acoplaria a gaveta ao painel. O custo são duas
estruturas quase irmãs, e `painel.E004` só enxerga a ação pela linha em `ACOES_SEM_CARD`.

A gaveta do lote carrega o poço de ações por `hx-get` ao router apenas quando `gaveta.lote.sql`
estiver preenchido. É o que mantém a gaveta sem importar ação alguma e poupa requisição inútil em
lotes municipais, compondo tanto com a busca direta (`localizacao_lote/001`) quanto com o lote
mais próximo (`002`) e os lotes do desenho (`003`/`004`). O custo é uma segunda requisição por lote
localizado com SQL, também para o anônimo, que recebe o poço vazio.

O lote é lido **duas vezes** no WFS: ao abrir o modal (para decidir se há formulário) e na emissão.
A leitura da emissão é a que vale, porque o modal pode ficar aberto enquanto a camada muda. O custo é
uma ida a mais ao GeoSampa por certidão, e a certidão pode recusar na emissão o que o modal ofereceu.

O rodapé declara o instante da leitura do lote no WFS, e não a data da última carga do daemon. A
certidão atesta o que o GeoSampa respondeu naquele momento, e os parquets locais não entram na
emissão. O custo é que a data não diz desde quando o próprio GeoSampa foi atualizado pela fonte
dele.

O interessado fica fora de `campos_publicos`. É dado de pessoa, e a ficha de conferência abre para
quem tiver o código. O custo é que quem confere pelo código vê o SQL e o processo, mas não a quem a
certidão foi emitida.

Só o **formato** do processo SEI é conferido, não o dígito verificador. O algoritmo do dígito não
está documentado no projeto. O custo é aceitar número bem formado que não existe.

A nota do rodapé é quebrada **à mão**, uma string por linha, porque o motor de marcação não mede a
faixa e a linha longa atravessa o quadro do selo. O custo é que nada revalida a quebra: alongar o
texto volta a transbordar, e o teste não pega — o `extract_text` de um PDF devolve a linha inteira
mesmo quando ela sai da caixa, então só rasterizando (`pdftoppm`) se enxerga.

`CertidaoLancamentoInput` recusa lote sem lançamento ou condominial também no domínio, além do aviso
do modal. A regra "só se certifica lançamento que existe" não pode depender da tela. O custo é a
mesma condição escrita no template do modal e no validador.

## 8 · Testes (TDD)

**Comportamento**
- `test_pedido_recusa_processo_fora_do_formato_sei` — `6017.2026/123-4` e texto livre falham; o
  formato completo passa.
- `test_certidao_input_recusa_lote_sem_lancamento_ou_condominial` — lote municipal e lote-mãe de
  condomínio falham na construção.
- `test_montar_certidao_declara_requerimento_identificacao_e_despacho` — os blocos trazem interessado,
  processo, endereço com codlog-DV e o SQL no despacho.
- `test_certidao_traz_planta_e_nota_com_instante_da_consulta` — há um `ImagemRaster` e a nota do rodapé
  cita data e hora de `consultado_em`.
- `test_poco_de_acoes_lote_so_para_quem_tem_concessao_e_sql_valido` — anônimo e autenticado sem concessão
  recebem o poço vazio; com concessão e SQL válido, o botão aponta para o modal com o id e o sql *(marker `banco`)*.
- `test_router_acoes_lote_recusa_sql_invalido_ou_ausente` — parâmetros sem SQL ou com formato divergente
  do padrão `SSS.QQQ.LLLL-D` devolvem poço vazio sem erro 500 *(marker `banco`)*.
- `test_modal_de_lote_sem_lancamento_ou_inexistente_mostra_aviso_sem_formulario` — lote municipal e
  fetcher vazio abrem o aviso *(marker `banco`)*.
- `test_emissao_rele_lote_pelo_identificador` — o imóvel certificado é o que o fetcher fake devolve
  para o `id` do POST; campos de endereço mandados no POST são ignorados
  *(marker `banco`)*.
- `test_emissao_guarda_via_no_acervo_e_devolve_download` — `DocumentoEmitido` gravado, segunda via com
  os mesmos bytes, resposta com o link *(marker `banco`)*.
- `test_formulario_invalido_volta_ao_modal_com_realce` — 422 com `campo-realce-erro` no processo
  *(marker `banco`)*.
- `test_amostra_certidao_de_lancamento` — PDF com planta fictícia para conferência *(marker `artefato`)*.

**Segurança da ação** (skill `acao-administrativa`, fora do teto; todos com marker `banco`)
- `test_anonimo_no_modal_vai_ao_login_sem_linha` — #1.
- `test_sem_concessao_recebe_403_e_linha_de_negativa` — #2.
- `test_concessao_em_outra_unidade_nao_passa` — #3.
- `test_impedido_recebe_403_e_exonerado_vai_ao_login` — #4.
- `test_emissao_grava_autor_cargo_unidade_operacao_e_alvo` — #10.
- `test_abrir_modal_nao_registra_e_negativa_registra` — #12.
- `test_acao_inativa_nao_libera_com_concessao_gravada` — #13.
- `test_emitir_so_por_post` — #15.
