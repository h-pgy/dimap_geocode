---
spec: documentos_oficiais/007
versao: v1
atualizado_em: 2026-09-07
testes_tdd: false
implementado: false
markers_obrigatorios: [artefato]
changelog:
  - v1: versão inicial
---

# SPEC documentos_oficiais/007 — Envelope do ato e selo no papel

## 1 · User story
O servidor da DIMAP lê o selo no pé de um documento emitido, no contexto de conferir a procedência de
uma via que chegou às suas mãos, para saber quem praticou o ato, quando, e por onde conferi-lo.

## 2 · Condições de pronto
- [ ] O documento emitido com selo traz, no pé de **toda página**, um quadro com o nome de quem
      praticou o ato, a data e a hora com fuso, o código do documento e o endereço de conferência
      por extenso.
- [ ] O quadro traz um QR que abre o mesmo endereço escrito por extenso ao lado dele.
- [ ] O ato praticado **em substituição** diz, no selo, por quem se respondia.
- [ ] O selo diz "assinado eletronicamente", nunca "assinado digitalmente".
- [ ] O papel timbrado **sem** selo continua saindo como hoje, com o mesmo pé e as mesmas margens.
- [ ] O envelope embutido traz, **no mínimo**, todos os campos do registro de execução da ação: ação,
      autor, unidade, cargos, substituição, operação e alvo.
- [ ] A ação acrescenta campos próprios ao envelope, e um extra que repita chave do núcleo é
      **recusado na montagem**.
- [ ] O que está impresso no selo e o que está escrito no envelope são o **mesmo** ato: mesmo
      instante, mesmo autor, mesmo código.
- [ ] `uv run pytest -m artefato` grava o documento selado e imprime o caminho para a conferência
      visual do quadro.

## 3 · Domínio
O envelope é o **retrato do ato no instante da emissão** — congelado, e por isso sem nada mutável
dentro dele. Ele espelha o que `ExecucaoAcao` (épico `autorizacao`) registra, denormalizado em texto,
porque chave estrangeira não viaja dentro de um PDF; e a pergunta que esta SPEC faz ao selo da SPEC
[documentos_oficiais/006](006-selo-de-integridade.md) é que forma têm os dados opacos que ele sela.

A conferência visual do quadro é a amostra do marker `artefato`, como na SPEC
[documentos_oficiais/004](004-qr-code.md): o entregável é papel, e não há mock HTML a aprovar.

**`services/domain/documento_selado/models.py`**
```python
class AutorDoAto(BaseModel):
    """Quem praticou, com a lotação e os cargos do dia. Texto, não referência: o envelope precisa
    dizer o mesmo daqui a dez anos, com a pessoa já aposentada e a unidade já extinta."""

    model_config = ConfigDict(frozen=True)

    nome: str
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
    """O que vai IMPRESSO no quadro, já em linhas prontas. Derivado do envelope, e não digitado ao
    lado dele: é o que impede o papel de dizer uma coisa e o arquivo, outra."""

    model_config = ConfigDict(frozen=True)

    linhas: tuple[str, ...]
    url_conferencia: str


class SeloImpressoInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    # O ato inteiro, não os campos dele soltos.
    envelope: EnvelopeAto
    # E só então o que é do processo: o endereço do ambiente, que o domínio não conhece.
    base_url: str
```

**`services/domain/documento_oficial/models/marcacao.py`** — a medida do quadro no papel, ao lado da
config do papel timbrado, que **não** muda.
```python
class SeloConfig(BaseModel):
    """Quanto o quadro do selo ocupa. Medida de papel, como a do timbre e a da marca d'água — cor e
    espessura do traço não entram aqui: são tema."""

    model_config = ConfigDict(frozen=True)

    largura_mm: float = 62.0
    # O símbolo dentro do quadro, descontados a moldura e o respiro interno.
    largura_qr_mm: float = 18.0
    respiro_interno_mm: float = 2.0
```

**`services/domain/documento_oficial/models/tema.py`** — o token novo do traço do selo, e o estilo já
resolvido que o `Tema` entrega. A cor da tabela não serve: ela é do traço de uma tabela, e o quadro
do selo é outra peça.
```python
class PaletaDocumento(BaseModel):
    # ... os que já existem
    # ALTERADO nesta SPEC: token novo.
    traco_selo: str = Field(default="#666666", pattern=COR_HEX)


class TipografiaDocumento(BaseModel):
    # ... os que já existem
    # ALTERADO nesta SPEC: campo novo. Em milímetros, como as demais medidas de marca — o traço da
    # tabela é em pontos porque quem o consome é o motor de tabela.
    espessura_traco_selo_mm: float = 0.3


class Tema(BaseModel):
    # ... os que já existem
    # ALTERADO nesta SPEC: campo novo, resolvido como os estilos de texto já são.
    estilo_traco_selo: EstiloTraco
```

## 4 · Fora de escopo
- Guardar o documento emitido, a segunda via e a tela de conferência — SPEC
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
  entre o texto do pé e o quadro do selo.
- `@services/utils/pdf/folha.py` → `Folha.retangulo`: a moldura do quadro.
- `@services/domain/documento_oficial/marcas.py` → `QrCodeRodape`, `LinhasDeTexto`: o símbolo e as
  linhas que o quadro compõe.
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
```

**`services/domain/documento_selado/codigo.py`**
```python
def gerar_codigo() -> str:
    """O identificador que vai no QR, no texto do selo e no acervo. Aleatório, nunca sequencial."""
    return "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(TAMANHO_CODIGO))
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
    """Callable: o envelope → as linhas do quadro. É o único lugar que redige o texto do selo."""

    def __call__(self, pedido: SeloImpressoInput) -> SeloImpresso:
        return self.pipeline(pedido)

    def pipeline(self, pedido: SeloImpressoInput) -> SeloImpresso:
        url = self._url(pedido)
        return SeloImpresso(linhas=self._linhas(pedido.envelope, url), url_conferencia=url)

    def _linhas(self, envelope: EnvelopeAto, url: str) -> tuple[str, ...]:
        return (
            # "eletronicamente", e não "digitalmente": assinatura digital tem sentido técnico
            # próprio no Brasil (certificado ICP-Brasil), e o selo daqui não é isso.
            f"Assinado eletronicamente por {envelope.autor.nome}",
            *self._substituicao(envelope.autor),
            f"{envelope.autor.cargo_comissao or envelope.autor.cargo_base} — {envelope.autor.unidade}",
            f"em {envelope.emitido_em.strftime(FORMATO_SELO)}",
            f"Código {envelope.codigo}",
            f"Confira em {url}",
        )

    def _substituicao(self, autor: AutorDoAto) -> tuple[str, ...]:
        if autor.substituindo is None:
            return ()
        return (f"em substituição a {autor.substituindo}",)

    def _url(self, pedido: SeloImpressoInput) -> str:
        return f"{pedido.base_url.rstrip('/')}/documentos/{pedido.envelope.codigo}"
```

**`services/domain/documento_oficial/marcas.py`** — a marca nova. Ela recebe **linhas prontas**: o
papel timbrado não conhece ato administrativo, e não é ele quem redige nada.
```python
class SeloAssinatura(Marca):
    """O quadro do selo: moldura, linhas à esquerda e QR à direita, tudo dentro da própria faixa."""

    posicao = Posicao.INFERIOR

    def __init__(self, selo: SeloImpresso, config: SeloConfig, tema: Tema) -> None:
        self._config = config
        self._qr = QrCodeRodape(selo.url_conferencia, config.largura_qr_mm)
        # O estilo do pé, não um novo: o selo é texto de rodapé, e inventar tipografia própria para
        # ele criaria um segundo tamanho de letra no mesmo pé da página.
        self._texto = LinhasDeTexto(
            selo.linhas, tema.estilo_rodape_marca, tema.entrelinha_marca_mm
        )
        self._traco = tema.estilo_traco_selo
        self.largura_mm = config.largura_mm
        # O maior dos dois, mais a folga da moldura dos dois lados.
        self.altura_mm = max(self._texto.altura_mm, self._qr.altura_mm) + 2 * config.respiro_interno_mm

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        folha.retangulo(faixa.esquerda_mm, faixa.topo_mm, faixa.largura_mm, self.altura_mm, self._traco)
        # O conteúdo recuado da moldura pelo respiro, para o texto não encostar no traço.
        interna = self._faixa_interna(faixa)
        self._texto(interna.model_copy(update={"largura_mm": interna.largura_mm - self._qr.largura_mm}), folha)
        self._qr(interna, folha)

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

**`services/domain/documento_oficial/marcacoes_concretas/fazenda_dimap_selado.py`** — o papel
timbrado com selo, **ao lado** do que já existe. Trocar de papel timbrado é escrever outro módulo:
`fazenda_dimap` não muda, e o QR genérico do pé some porque o do selo o substitui.
```python
def marcacao_fazenda_dimap_selado(
    config: MarcacaoConfig,
    tema: Tema,
    selo: SeloImpresso,
    selo_config: SeloConfig,
) -> MarcacaoDocumento:
    return MarcacaoDocumento(
        principal=Marcacao(
            marcas=(
                CabecalhoTimbrado(...),
                MarcaDagua(config.logo_vertical, config.largura_marca_dagua_mm),
                # Endereço e paginação empilhados à esquerda; o quadro do selo à direita, com
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
                        SeloAssinatura(selo, selo_config, tema),
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
ato uma vez e o usa nas duas pontas. O papel e o arquivo saem do **mesmo** `EnvelopeAto`, e é isso
que os impede de divergirem.
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
        marcacao = marcacao_fazenda_dimap_selado(
            build_marcacao_config(settings),
            tema,
            montar_selo_impresso(SeloImpressoInput(envelope=ato, base_url=base_url)),
            SeloConfig(),
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
dentro do domínio. Derivar as linhas do envelope num lugar só é o que garante que papel e arquivo
digam o mesmo ato. O custo é que mudar a redação do selo mexe no domínio, e não no tema.

O nome, o cargo e a unidade do autor — e, quando houver, de quem ele substituía — saem impressos e
escritos num arquivo que circula fora da DIMAP. É a mesma identidade que o documento oficial já
estampa, e sem ela o selo não atribui o ato a ninguém. O custo é que a substituição, que é informação
interna de impedimento, passa a acompanhar toda via do documento.

A paleta, a tipografia e o `Tema` ganham o traço do selo — três campos novos em peças já entregues
pela SPEC 003. Traço de tabela é o token de outra peça, e reusá-lo amarraria a moldura do selo à
aparência das tabelas. O custo é que o tema do documento cresce com um token que só uma marca usa.

`campos_publicos` chega por parâmetro da emissão, e não declarado no contrato da ação. Estender
`AcaoImplementada` tocaria a máquina do épico `autorizacao`, entregue e em uso. O custo é que a
mesma ação pode declarar conjuntos diferentes em pontos de chamada diferentes, e nada verifica isso.

## 8 · Testes (TDD)
- `test_envelope_traz_todos_os_campos_do_registro_de_execucao` — o mapa achatado tem ação, autor,
  unidade, cargos, substituição, operação e alvo, e nenhum deles pode faltar na construção.
- `test_extra_que_colide_com_o_nucleo_eh_recusado` — extra chamado `autor` levanta na montagem,
  dizendo qual chave colidiu; extra de nome livre entra ao lado do núcleo.
- `test_selo_impresso_e_envelope_descrevem_o_mesmo_ato` — as linhas trazem o mesmo autor, o mesmo
  instante e o mesmo código que o envelope embutido, a partir de um único `EnvelopeAto`.
- `test_selo_diz_assinado_eletronicamente` — a primeira linha usa "eletronicamente" e em nenhuma
  linha aparece "digitalmente".
- `test_ato_em_substituicao_aparece_no_selo` — com `substituindo` preenchido sai a linha de
  substituição; sem ele, o quadro tem uma linha a menos.
- `test_url_de_conferencia_leva_o_codigo` — o endereço impresso por extenso e o conteúdo do QR são o
  mesmo, e terminam no código do documento.
- `test_codigo_eh_aleatorio_no_alfabeto_sem_ambiguidade` — dois códigos seguidos diferem, têm 12
  caracteres e nenhum deles é `I`, `L`, `O` ou `U`.
- `test_marcacao_selada_reparte_o_pe_entre_texto_e_quadro` — o pé sai numa faixa só, com o texto à
  esquerda e o quadro na largura declarada à direita, e a altura da faixa é a do quadro.
- `test_papel_timbrado_sem_selo_permanece_identico` — `marcacao_fazenda_dimap` produz as mesmas
  margens e o mesmo pé de antes desta SPEC.
- `test_amostra_selada_com_quadro_no_pe` — grava o documento com o quadro no pé de toda página e
  imprime o caminho, para a leitura do QR com o celular. *(marker `artefato`)*
