---
spec: documentos_oficiais/007
versao: v4
atualizado_em: 2026-09-08
testes_tdd: true
implementado: true
markers_obrigatorios: [artefato]
changelog:
  - v1: versão inicial
  - v2: o selo no papel passa a ser dois — o quadro compacto no pé de toda página e o quadro de fecho que encerra o documento —, com link curto e sem a unidade impressa.
  - v3: testes da §8 escritos (`tests/services/domain/documento_selado/`, `tests/services/domain/documento_oficial/test_fecho.py`, ajustes em `test_escritores.py`, `marcacoes_concretas/test_fazenda_dimap.py` e `tests/apps/core/test_gerar_documento_amostra.py`) e falhando por ausência dos módulos — `testes_tdd: true`
  - v4: implementado — `QuadroSeloConfig`/`SeloConfig` foram para `models/selo.py`, à parte de `marcacao.py`, para não fechar um ciclo de import com `conteudo.py` via o bloco `SeloDeFecho`; `implementado: true`
---

# SPEC documentos_oficiais/007 — Envelope do ato e selo no papel

## 1 · User story
O servidor da DIMAP lê o selo de um documento emitido, no contexto de conferir a procedência de uma
via que chegou às suas mãos, para saber quem praticou o ato, quando, e por onde conferi-lo.

## 2 · Condições de pronto
- [ ] O documento emitido com selo traz, no **canto inferior direito de toda página**, um quadro
      fechado com "Assinado eletronicamente", o QR à esquerda e o link curto à direita — tudo dentro
      da moldura.
- [ ] A **última coisa do documento** é o quadro de fecho, centralizado na página, com o QR grande, o
      endereço por extenso sob ele, o nome de quem assinou, o cargo e a data por extenso terminando
      em "às XXhXXmin".
- [ ] O cargo impresso é o **de comissão** quando houver e o **base** quando não houver; a unidade
      não aparece em nenhum dos dois quadros.
- [ ] O ato praticado **em substituição** diz, no quadro de fecho, por quem se respondia.
- [ ] O selo diz "assinado eletronicamente", nunca "assinado digitalmente".
- [ ] O QR e o endereço impresso levam ao **mesmo** documento e terminam no código; o impresso sai
      sem o esquema do endereço.
- [ ] O papel timbrado **sem** selo continua saindo como hoje, com o mesmo pé e as mesmas margens.
- [ ] O envelope embutido traz, **no mínimo**, todos os campos do registro de execução da ação: ação,
      autor, unidade, cargos, substituição, operação e alvo.
- [ ] A ação acrescenta campos próprios ao envelope, e um extra que repita chave do núcleo é
      **recusado na montagem**.
- [ ] O que está impresso nos quadros e o que está escrito no envelope são o **mesmo** ato: mesmo
      instante, mesmo autor, mesmo código.
- [ ] `uv run pytest -m artefato` grava o documento selado e imprime o caminho para a conferência
      visual dos dois quadros.

## 3 · Domínio
O envelope é o **retrato do ato no instante da emissão** — congelado, e por isso sem nada mutável
dentro dele. Ele espelha o que `ExecucaoAcao` (épico `autorizacao`) registra, denormalizado em texto,
porque chave estrangeira não viaja dentro de um PDF; e a pergunta que esta SPEC faz ao selo da SPEC
[documentos_oficiais/006](006-selo-de-integridade.md) é que forma têm os dados opacos que ele sela.

O selo no papel são **dois quadros do mesmo ato**: o compacto, que acompanha toda página, e o de
fecho, que encerra o documento. Os dois saem de um `SeloImpresso` só — a redação acontece uma vez.

A conferência visual dos quadros é a amostra do marker `artefato`, como na SPEC
[documentos_oficiais/004](004-qr-code.md): o entregável é papel, e não há mock HTML a aprovar.

**`services/domain/documento_selado/models.py`**
```python
class AutorDoAto(BaseModel):
    """Quem praticou, com a lotação e os cargos do dia. Texto, não referência: o envelope precisa
    dizer o mesmo daqui a dez anos, com a pessoa já aposentada e a unidade já extinta."""

    model_config = ConfigDict(frozen=True)

    nome: str
    # Não vai impressa em quadro nenhum: ela identifica a lotação no envelope e no timbre da folha.
    unidade: str
    cargo_base: str
    cargo_comissao: str | None = None
    # Preenchido só quando o ato foi praticado em substituição: descrever o ato pelo cargo de quem
    # assinou, sem dizer por quem ele respondia, atribui a competência à pessoa errada.
    substituindo: str | None = None


class AlvoDoAto(BaseModel):
    """Sobre o quê. Texto nos dois campos, como em `ExecucaoAcao`: o alvo é lote, logradouro,
    servidor ou unidade conforme a ação, e tipá-lo por entidade amarraria o envelope ao catálogo de
    entidades territoriais."""

    model_config = ConfigDict(frozen=True)

    tipo: str
    identificador: str


class EnvelopeAto(BaseModel):
    """O núcleo é obrigatório — é ele que faz o envelope descrever um ato, e não um arquivo qualquer.
    `extras` é o que cada ação acrescenta."""

    model_config = ConfigDict(frozen=True)

    versao: int = VERSAO_ENVELOPE
    codigo: str
    # O slug do contrato da ação (`<app>.<nome>`), que é o identificador estável dela.
    acao: str
    operacao: str = ""
    autor: AutorDoAto
    alvo: AlvoDoAto
    # Com fuso: "10:32" sem dizer de onde não descreve instante nenhum.
    emitido_em: AwareDatetime
    campos_publicos: tuple[str, ...] = ()
    extras: dict[str, Any] = Field(default_factory=dict)


class SeloImpresso(BaseModel):
    """O que vai IMPRESSO nos dois quadros, já redigido. Derivado do envelope, e não digitado ao
    lado dele: é o que impede o papel de dizer uma coisa e o arquivo, outra."""

    model_config = ConfigDict(frozen=True)

    chamada: str
    # O que o QR diz, inteiro.
    url_conferencia: str
    # O mesmo endereço sem o esquema: é o que se lê no papel e o que alguém digita.
    link_impresso: str
    assinante: str
    # Já resolvido: o de comissão quando existe, o base quando não.
    cargo: str
    substituindo: str | None = None
    # "8 de setembro de 2026, às 14h32min" — a data como ela sai impressa.
    data_por_extenso: str


class SeloImpressoInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    # O ato inteiro, não os campos dele soltos.
    envelope: EnvelopeAto
    # E só então o que é do processo: o endereço do ambiente, que o domínio não conhece.
    base_url: str
```

**`services/domain/documento_oficial/models/marcacao.py`** — a medida dos quadros no papel, ao lado
da config do papel timbrado, que **não** muda.
```python
class QuadroSeloConfig(BaseModel):
    """Quanto um quadro do selo ocupa. Medida de papel, como a do timbre e a da marca d'água — cor e
    espessura do traço não entram aqui: são tema."""

    model_config = ConfigDict(frozen=True)

    largura_mm: float
    # O símbolo dentro do quadro, descontados a moldura e o respiro interno.
    largura_qr_mm: float
    respiro_interno_mm: float


class SeloConfig(BaseModel):
    """Os dois quadros são a mesma peça em duas medidas. O QR do compacto não desce de 20 mm: abaixo
    disso o módulo fica menor que o mínimo de impressão (`MODULO_MINIMO_MM`)."""

    model_config = ConfigDict(frozen=True)

    compacto: QuadroSeloConfig = QuadroSeloConfig(
        largura_mm=68.0,
        largura_qr_mm=20.0,
        respiro_interno_mm=2.0,
    )
    fecho: QuadroSeloConfig = QuadroSeloConfig(
        largura_mm=90.0,
        largura_qr_mm=35.0,
        respiro_interno_mm=6.0,
    )
```

**`services/domain/documento_oficial/models/blocos.py`** — o quadro de fecho é **bloco**, não marca:
ele acontece uma vez, no fluxo do corpo, e é lá que "última coisa do documento" tem sentido.
```python
class SeloDeFecho(BlocoDocumento):
    """O quadro que encerra o documento. Guarda o selo redigido e a medida do quadro, nunca o
    desenho: o símbolo é derivado do endereço, como no bloco `QrCode`."""

    tipo: Literal["selo_de_fecho"] = "selo_de_fecho"
    selo: SeloImpresso
    # Sem default, como a largura da `Imagem`: quanto o quadro ocupa é decisão de quem emite.
    quadro: QuadroSeloConfig


# ALTERADO nesta SPEC: o fecho entra na união dos blocos.
Bloco = Annotated[
    Titulo | Subtitulo | Paragrafo | Lista | Tabela | Imagem | QrCode | SeloDeFecho,
    Field(discriminator="tipo"),
]
```

**`services/domain/documento_oficial/models/tema.py`** — as cores e as medidas do selo. A cor da
tabela não serve: ela é do traço de uma tabela, e o quadro do selo é outra peça.
```python
class PaletaSelo(BaseModel):
    """As cores do quadro, tiradas do design system do sistema — ciano do traço, tinta de título do
    assinante, cinza de apoio para o resto."""

    model_config = ConfigDict(frozen=True)

    traco: str = Field(default="#0096C7", pattern=COR_HEX)
    assinante: str = Field(default="#0D1B2A", pattern=COR_HEX)
    apoio: str = Field(default="#415A77", pattern=COR_HEX)


class PaletaDocumento(BaseModel):
    # ... os que já existem
    # ALTERADO nesta SPEC: campo novo. Aninhado, e não três campos soltos: as três cores só fazem
    # sentido juntas, e nenhuma delas vem do ambiente.
    selo: PaletaSelo = PaletaSelo()


class TipografiaDocumento(BaseModel):
    # ... os que já existem
    # ALTERADO nesta SPEC: campos novos. A espessura é em milímetros, como as demais medidas de
    # marca — o traço da tabela é em pontos porque quem o consome é o motor de tabela.
    espessura_traco_selo_mm: float = 0.3
    # Menor que o rodapé: é o corpo em que o endereço curto ainda cabe ao lado do símbolo.
    corpo_selo_compacto_pt: float = 7.0
    corpo_selo_assinante_pt: float = 12.0
    corpo_selo_apoio_pt: float = 8.5


class Tema(BaseModel):
    # ... os que já existem
    # ALTERADO nesta SPEC: campos novos, resolvidos como os estilos de texto já são. Os estilos do
    # quadro de fecho entram em `estilos`, porque quem os consome é um flowable.
    estilo_traco_selo: EstiloTraco
    estilo_selo_compacto: EstiloTexto
```

## 4 · Fora de escopo
- Guardar o documento emitido, a segunda via e a rota `/d/<codigo>` que o selo imprime — SPEC
  [documentos_oficiais/008](008-acervo-e-conferencia.md).
- Revogação: nada no envelope diz se o ato ainda vale, e nem poderia — SPEC própria, sem dono ainda.
- A ação de emitir certidão de lançamento, com seu contrato e seu card no painel — SPEC própria, sem
  dono ainda.
- `campos_publicos` declarado no contrato da ação, em vez de vir por parâmetro da emissão — sem dono
  ainda.
- Selo em documento gerado fora do `documento_oficial` — sem dono ainda.
- Assinatura visível de mais de um autor no mesmo documento — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/utils/assinatura` → `SelarDocumento`: o selo criptográfico que recebe o envelope como
  dados opacos.
- `@apps/competencias/registro_execucao.py` → `gravar_execucao`: os campos que o registro do ato
  guarda, e que o envelope espelha.
- `@apps/competencias/models/execucao.py` → `ExecucaoAcao`: as colunas do registro vivo.
- `@services/utils/pdf/marcacao.py` → `MarcasLadoALado`, `MarcasEmpilhadas`: a repartição da faixa
  entre o texto do pé e o quadro compacto.
- `@services/utils/pdf/folha.py` → `Folha.retangulo`: a moldura do quadro compacto.
- `@services/utils/pdf/qr_code.py` → `qr_code_pdf`, `MODULO_MINIMO_MM`: o símbolo e o piso de
  tamanho que ele impõe.
- `@services/domain/documento_oficial/marcas.py` → `QrCodeRodape`, `LinhasDeTexto`: o símbolo e as
  linhas que o quadro compacto compõe.
- `@services/domain/documento_oficial/escritores.py` → `EscritorQrCode`: o símbolo do quadro de
  fecho, já no fluxo do corpo.
- `@services/domain/documento_oficial/marcacoes_concretas/fazenda_dimap.py` →
  `marcacao_fazenda_dimap`: o papel timbrado ao lado do qual o selado nasce.
- Skills: `ontologia`, `documento-oficial`, `escrever-testes`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`services/domain/documento_selado/constants.py`**
```python
VERSAO_ENVELOPE = 1
# O que a ação não pode sobrescrever. Um extra chamado `autor` faria o documento mentir sobre quem
# praticou o ato — e mentiria com selo válido, porque o selo cobre o que estiver escrito.
CHAVES_RESERVADAS = frozenset(
    {"versao", "codigo", "acao", "operacao", "autor", "alvo", "emitido_em", "campos_publicos"}
)
# 12 caracteres num alfabeto de 32 dão ~60 bits: a rota de conferência é aberta (SPEC 008), e código
# adivinhável permitiria varrer o acervo inteiro.
TAMANHO_CODIGO = 12
# Base32 sem as letras que se confundem com dígito na leitura de um papel: I, L, O e U fora.
ALFABETO_CODIGO = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
# Rota de UMA letra: cada caractere a mais no endereço engorda a matriz do QR, e o quadro compacto
# não tem milímetro sobrando.
ROTA_CONFERENCIA = "d"
# "eletronicamente", e não "digitalmente": assinatura digital tem sentido técnico próprio no Brasil
# (certificado ICP-Brasil), e o selo daqui não é isso.
CHAMADA_SELO = "Assinado eletronicamente"
MESES = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)
```

**`services/domain/documento_selado/codigo.py`**
```python
def gerar_codigo() -> str:
    """O identificador que vai no QR, no endereço impresso e no acervo. Aleatório, nunca sequencial."""
    return "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(TAMANHO_CODIGO))
```

**`services/domain/documento_selado/datas.py`**
```python
def por_extenso(momento: datetime) -> str:
    """A data como ela sai no quadro de fecho. O momento chega já no fuso em que se quer lê-lo:
    converter aqui exigiria que o domínio conhecesse o fuso do ambiente."""
    return f"{momento.day} de {MESES[momento.month - 1]} de {momento.year}, às {momento:%Hh%Mmin}"
```

**`services/domain/documento_selado/envelope.py`** — o núcleo e os extras achatados num mapa só, que
é a forma que o selo da SPEC 006 recebe.
```python
class MontarEnvelope:
    """Callable: o ato → os dados opacos do selo. Achatar, e não aninhar os extras sob uma chave, é
    o que faz `campos_publicos` poder nomear qualquer campo do envelope pelo mesmo caminho."""

    def __call__(self, ato: EnvelopeAto) -> dict[str, Any]:
        return self.pipeline(ato)

    def pipeline(self, ato: EnvelopeAto) -> dict[str, Any]:
        self._recusar_colisao(ato.extras)
        nucleo = ato.model_dump(mode="json", exclude={"extras"})
        return {**nucleo, **ato.extras}

    def _recusar_colisao(self, extras: dict[str, Any]) -> None:
        colididas = CHAVES_RESERVADAS & extras.keys()
        if colididas:
            raise ValueError(
                f"{sorted(colididas)} são do núcleo do envelope e não podem vir como extras da ação."
            )
```

**`services/domain/documento_selado/impressao.py`** — o que o papel diz, derivado do que o arquivo
guarda. Duas fontes de verdade para o mesmo instante seria o defeito mais fácil de não perceber.
```python
class MontarSeloImpresso:
    """Callable: o envelope → o texto dos dois quadros. É o único lugar que redige o selo."""

    def __call__(self, pedido: SeloImpressoInput) -> SeloImpresso:
        return self.pipeline(pedido)

    def pipeline(self, pedido: SeloImpressoInput) -> SeloImpresso:
        url = self._url(pedido)
        autor = pedido.envelope.autor
        return SeloImpresso(
            chamada=CHAMADA_SELO,
            url_conferencia=url,
            link_impresso=self._sem_esquema(url),
            assinante=autor.nome,
            # O de comissão manda: é ele que descreve a competência que praticou o ato.
            cargo=autor.cargo_comissao or autor.cargo_base,
            substituindo=autor.substituindo,
            data_por_extenso=por_extenso(pedido.envelope.emitido_em),
        )

    def _url(self, pedido: SeloImpressoInput) -> str:
        return f"{pedido.base_url.rstrip('/')}/{ROTA_CONFERENCIA}/{pedido.envelope.codigo}"

    def _sem_esquema(self, url: str) -> str:
        # O que se lê e se digita no papel: "https://" ocupa oito caracteres e não ajuda ninguém.
        return url.split("://", 1)[-1]
```

**`services/utils/pdf/quadro.py`** — a moldura em volta de flowables, que o motor ainda não tinha.
```python
class QuadroInput(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    conteudo: tuple[Flowable, ...]
    largura_mm: float
    traco: EstiloTraco
    respiro_mm: float


class QuadroPdf:
    """Callable: flowables → um quadro emoldurado, centrado na largura do corpo. Uma célula só: quem
    reparte espaço e quebra página é a `Table` do reportlab, e reimplementar `wrap`/`split` num
    flowable próprio seria refazer o que ela já faz."""

    def __call__(self, pedido: QuadroInput) -> Flowable:
        return self.pipeline(pedido)

    def pipeline(self, pedido: QuadroInput) -> Flowable:
        quadro = Table([[list(pedido.conteudo)]], colWidths=[pedido.largura_mm * mm])
        quadro.setStyle(self._estilo(pedido))
        # Centrado na moldura do corpo, e não encostado na margem esquerda.
        quadro.hAlign = "CENTER"
        return quadro

    def _estilo(self, pedido: QuadroInput) -> TableStyle:
        respiro = pedido.respiro_mm * mm
        return TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), pedido.traco.espessura_mm * mm, pedido.traco.cor),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), respiro),
                ("RIGHTPADDING", (0, 0), (-1, -1), respiro),
                ("TOPPADDING", (0, 0), (-1, -1), respiro),
                ("BOTTOMPADDING", (0, 0), (-1, -1), respiro),
            ]
        )
```

**`services/domain/documento_oficial/marcas.py`** — o quadro compacto. Ele recebe o selo **já
redigido**: o papel timbrado não conhece ato administrativo, e não é ele quem escreve nada.
```python
class SeloCompacto(Marca):
    """O quadro do pé: moldura, QR à esquerda e duas linhas à direita, tudo dentro da própria faixa."""

    posicao = Posicao.INFERIOR

    def __init__(self, selo: SeloImpresso, config: QuadroSeloConfig, tema: Tema) -> None:
        self._config = config
        self._qr = QrCodeRodape(selo.url_conferencia, config.largura_qr_mm)
        self._texto = LinhasDeTexto(
            (selo.chamada, selo.link_impresso),
            tema.estilo_selo_compacto,
            tema.entrelinha_marca_mm,
        )
        self._traco = tema.estilo_traco_selo
        self.largura_mm = config.largura_mm
        # O maior dos dois, mais a folga da moldura em cima e embaixo.
        self.altura_mm = (
            max(self._texto.altura_mm, self._qr.altura_mm) + 2 * config.respiro_interno_mm
        )

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        folha.retangulo(
            faixa.esquerda_mm,
            faixa.topo_mm,
            faixa.largura_mm,
            self.altura_mm,
            self._traco,
        )
        interna = self._faixa_interna(faixa)
        # A coluna do símbolo tem a largura DELE: `QrCodeRodape` se encosta na direita da faixa que
        # recebe, e é assim que ele cai na esquerda do quadro sem tocar na marca já entregue.
        self._qr(interna.model_copy(update={"largura_mm": self._qr.largura_mm}), folha)
        self._texto(self._coluna_do_texto(interna), folha)

    def _coluna_do_texto(self, interna: Faixa) -> Faixa:
        recuo = self._qr.largura_mm + self._config.respiro_interno_mm
        return interna.model_copy(
            update={
                "esquerda_mm": interna.esquerda_mm + recuo,
                "largura_mm": interna.largura_mm - recuo,
            }
        )

    def _faixa_interna(self, faixa: Faixa) -> Faixa:
        respiro = self._config.respiro_interno_mm
        return faixa.model_copy(
            update={
                "esquerda_mm": faixa.esquerda_mm + respiro,
                "topo_mm": faixa.topo_mm + respiro,
                "largura_mm": faixa.largura_mm - 2 * respiro,
            }
        )
```

**`services/domain/documento_oficial/escritores.py`** — o quadro de fecho, no fluxo do corpo.
```python
class EscritorSeloDeFecho:
    """O quadro que encerra o documento: o símbolo centrado e, sob ele, o endereço, quem assinou, o
    cargo e a data. Uma linha por peça, cada uma no estilo que o tema já resolveu."""

    def __init__(self, tema: Tema) -> None:
        self._tema = tema
        # O mesmo escritor do bloco de QR: o símbolo do fecho não é um desenho diferente.
        self._qr = EscritorQrCode()

    def __call__(self, bloco: SeloDeFecho) -> Flowable:
        return self.pipeline(bloco)

    def pipeline(self, bloco: SeloDeFecho) -> Flowable:
        return quadro_pdf(
            QuadroInput(
                conteudo=(self._simbolo(bloco), *self._linhas(bloco.selo)),
                largura_mm=bloco.quadro.largura_mm,
                traco=self._tema.estilo_traco_selo,
                respiro_mm=bloco.quadro.respiro_interno_mm,
            )
        )

    def _simbolo(self, bloco: SeloDeFecho) -> Flowable:
        return self._qr(
            QrCode(conteudo=bloco.selo.url_conferencia, largura_mm=bloco.quadro.largura_qr_mm)
        )

    def _linhas(self, selo: SeloImpresso) -> tuple[Flowable, ...]:
        return (
            self._apoio(selo.link_impresso),
            Paragraph(_texto(selo.assinante), self._tema.estilos["selo_assinante"]),
            self._apoio(selo.cargo),
            *self._substituicao(selo),
            self._apoio(selo.data_por_extenso),
        )

    def _substituicao(self, selo: SeloImpresso) -> tuple[Flowable, ...]:
        if selo.substituindo is None:
            return ()
        return (self._apoio(f"em substituição a {selo.substituindo}"),)

    def _apoio(self, texto: str) -> Flowable:
        return Paragraph(_texto(texto), self._tema.estilos["selo_apoio"])


def montar_escritores(tema: Tema) -> dict[str, Callable[[Any], Flowable]]:
    return {
        # ... os que já existem
        "selo_de_fecho": EscritorSeloDeFecho(tema),
    }
```

**`services/domain/documento_oficial/fecho.py`** — quem põe o quadro no fim. O documento não se
assina sozinho: quem escreve o conteúdo não conhece o selo, e quem emite não reescreve o conteúdo.
```python
class AcrescentarSeloDeFecho:
    """Callable: o conteúdo + o selo → o mesmo conteúdo com o quadro no ÚLTIMO bloco. É o único
    ponto que decide onde o fecho entra, e por isso nenhum documento consegue assiná-lo no meio."""

    def __call__(self, pedido: SeloDeFechoInput) -> ConteudoDocumento:
        return self.pipeline(pedido)

    def pipeline(self, pedido: SeloDeFechoInput) -> ConteudoDocumento:
        bloco = SeloDeFecho(selo=pedido.selo, quadro=pedido.quadro)
        return pedido.conteudo.model_copy(
            update={"blocos": (*pedido.conteudo.blocos, bloco)}
        )
```

**`services/domain/documento_oficial/marcacoes_concretas/fazenda_dimap_selado.py`** — o papel
timbrado com selo, **ao lado** do que já existe. Trocar de papel timbrado é escrever outro módulo:
`fazenda_dimap` não muda, e o QR genérico do pé some porque o do selo o substitui.
```python
def marcacao_fazenda_dimap_selado(
    config: MarcacaoConfig,
    tema: Tema,
    selo: SeloImpresso,
    quadro: QuadroSeloConfig,
) -> MarcacaoDocumento:
    return MarcacaoDocumento(
        principal=Marcacao(
            marcas=(
                CabecalhoTimbrado(...),
                MarcaDagua(config.logo_vertical, config.largura_marca_dagua_mm),
                # Endereço e paginação empilhados à esquerda; o quadro compacto à direita, com
                # largura declarada. Quem não declara largura — a coluna de texto — fica com a sobra.
                MarcasLadoALado(
                    (
                        MarcasEmpilhadas(
                            (
                                RodapeEndereco(config.endereco, tema.estilo_rodape_marca, tema.entrelinha_marca_mm),
                                NumeracaoPaginas(tema.estilo_rodape_marca, tema.entrelinha_marca_mm),
                            ),
                            Posicao.INFERIOR,
                        ),
                        SeloCompacto(selo, quadro, tema),
                    ),
                    Posicao.INFERIOR,
                    config.respiro_mm,
                ),
            ),
            margem_lateral_mm=config.margem_lateral_mm,
            margem_vertical_mm=config.margem_vertical_mm,
            respiro_mm=config.respiro_mm,
        )
    )
```

**`apps/core/management/commands/gerar_documento_amostra.py`** — a orquestração, que é quem monta o
ato uma vez e o usa nas três pontas. O quadro do pé, o quadro de fecho e o arquivo saem do **mesmo**
`SeloImpresso`, e é isso que os impede de divergirem.
```python
        ato = EnvelopeAto(
            codigo=gerar_codigo(),
            acao="documentos.amostra",
            autor=AutorDoAto(nome="Fulano de Tal", unidade="DIMAP-1", cargo_base="Analista"),
            alvo=AlvoDoAto(tipo="amostra", identificador="—"),
            # UMA vez: chamar o relógio de novo na hora de selar daria um papel que se contradiz
            # com o próprio arquivo por alguns milissegundos.
            emitido_em=timezone.localtime(),
            campos_publicos=("acao", "autor", "alvo", "emitido_em"),
        )
        selo = montar_selo_impresso(SeloImpressoInput(envelope=ato, base_url=base_url))
        selo_config = SeloConfig()
        conteudo = acrescentar_selo_de_fecho(
            SeloDeFechoInput(conteudo=conteudo, selo=selo, quadro=selo_config.fecho)
        )
        marcacao = marcacao_fazenda_dimap_selado(
            build_marcacao_config(settings),
            tema,
            selo,
            selo_config.compacto,
        )
        selado = selar_documento(
            SelarInput(
                pdf=renderizar_documento_oficial(RenderizarDocumentoInput(conteudo=conteudo, marcacao=marcacao)),
                dados=montar_envelope(ato),
                campos_publicos=ato.campos_publicos,
                segredo=SecretStr(settings.ASSINATURA_SEGREDO),
                id_chave=settings.ASSINATURA_ID_CHAVE,
            )
        )
```

## 7 · Caveats
O envelope repete, em texto, o que `ExecucaoAcao` guarda em colunas — o mesmo dado em dois lugares.
O selo precisa ser conferível com o acervo fora do ar, e um envelope que dissesse "consulte o banco
para saber quem assinou" não valeria nada offline. O custo é duplicação assumida, mitigada por ela
ser **congelada**: o envelope é um retrato, e retrato não diverge do retratado — envelhece.

`services/domain/documento_selado/` redige o texto que vai impresso no papel, o que é apresentação
dentro do domínio. Derivar as linhas do envelope num lugar só é o que garante que os dois quadros e o
arquivo digam o mesmo ato. O custo é que mudar a redação do selo mexe no domínio, e não no tema.

`documento_oficial` passa a importar `SeloImpresso` de `documento_selado` — o papel timbrado conhece
um DTO do ato. A alternativa era o quadro receber seis strings soltas, que é a mesma ontologia
desmontada na fronteira. O custo é uma dependência de mão única entre dois submódulos de domínio, que
precisa continuar de mão única.

O nome, o cargo e — quando houver — quem o autor substituía saem impressos num arquivo que circula
fora da DIMAP. É a mesma identidade que o documento oficial já estampa, e sem ela o selo não atribui
o ato a ninguém. O custo é que a substituição, que é informação interna de impedimento, passa a
acompanhar toda via do documento.

A hora impressa sai no fuso em que a orquestração entrega o instante, e o papel não diz qual é. Um
"(horário de Brasília)" dentro do quadro é ruído para quem lê, e o envelope guarda o instante com o
deslocamento. O custo é que o papel, sozinho, é ambíguo diante de um leitor de outro fuso.

A paleta, a tipografia e o `Tema` ganham as cores e as medidas do selo, e elas **não** vêm do
ambiente, ao contrário de todas as outras. O quadro é identidade do ato e sai do design system do
sistema, não do papel de exceção que cada ambiente configura. O custo é que trocar a cor do selo é
mudar código, e não `.env`.

O quadro de fecho é emoldurado pela `Table` do reportlab, uma célula só, e não pelo motor de tabela
do projeto. Escrever um flowable próprio significaria reimplementar `wrap` e `split`, que é
exatamente o que a `Table` já resolve. O custo é uma segunda forma de desenhar moldura dentro do
mesmo motor — a da `Folha` para as marcas, a da `Table` para o corpo.

`campos_publicos` chega por parâmetro da emissão, e não declarado no contrato da ação. Estender
`AcaoImplementada` tocaria a máquina do épico `autorizacao`, entregue e em uso. O custo é que a
mesma ação pode declarar conjuntos diferentes em pontos de chamada diferentes, e nada verifica isso.

## 8 · Testes (TDD)
- `test_envelope_traz_todos_os_campos_do_registro_de_execucao` — o mapa achatado tem ação, autor,
  unidade, cargos, substituição, operação e alvo, e nenhum deles pode faltar na construção.
- `test_extra_que_colide_com_o_nucleo_eh_recusado` — extra chamado `autor` levanta na montagem,
  dizendo qual chave colidiu; extra de nome livre entra ao lado do núcleo.
- `test_impresso_qr_e_envelope_dizem_o_mesmo_ato` — a partir de um único `EnvelopeAto`, o texto do
  selo, o endereço do QR e o envelope trazem o mesmo autor, o mesmo instante e o mesmo código, e o
  endereço impresso é o do QR sem o esquema.
- `test_selo_diz_assinado_eletronicamente` — a chamada usa "eletronicamente" e em nenhum campo do
  selo aparece "digitalmente".
- `test_fecho_traz_cargo_de_comissao_sem_unidade_e_data_por_extenso` — com cargo em comissão sai ele,
  sem ele sai o base; a unidade não aparece em campo nenhum e a data termina em "às XXhXXmin".
- `test_ato_em_substituicao_aparece_no_fecho` — com `substituindo` preenchido sai a linha de
  substituição; sem ele, o quadro tem uma linha a menos.
- `test_selo_de_fecho_eh_o_ultimo_bloco_do_conteudo` — acrescentar o fecho preserva os blocos
  originais na ordem e põe o quadro no fim, mesmo num conteúdo que já termina em tabela.
- `test_codigo_eh_aleatorio_no_alfabeto_sem_ambiguidade` — dois códigos seguidos diferem, têm 12
  caracteres e nenhum deles é `I`, `L`, `O` ou `U`.
- `test_papel_timbrado_sem_selo_permanece_identico` — `marcacao_fazenda_dimap` produz as mesmas
  margens e o mesmo pé de antes desta SPEC.
- `test_amostra_selada_com_os_dois_quadros` — grava o documento com o quadro compacto no pé de toda
  página e o de fecho encerrando o corpo, e imprime o caminho para a leitura dos QRs com o celular.
  *(marker `artefato`)*
