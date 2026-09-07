---
spec: documentos_oficiais/004
versao: v2
atualizado_em: 2026-09-07
testes_tdd: false
implementado: false
markers_obrigatorios: [artefato]
changelog:
  - v1: versão inicial
  - v2: o símbolo é escrito uma vez e referenciado, e ganha o escritor de rodapé ao lado do de corpo
---

# SPEC documentos_oficiais/004 — QR Code: conteúdo que vira símbolo vetorial no papel

## 1 · User story
O administrador do cadastro gera o documento de amostra pelo terminal, no contexto de subir a emissão
de documentos oficiais, para conferir com o celular que o QR impresso devolve exatamente o endereço
declarado.

## 2 · Condições de pronto
- [ ] O símbolo sai como **SVG vetorial em bytes**: nenhum arquivo é criado em disco durante a geração,
      e ampliá-lo não serrilha.
- [ ] O símbolo é **sempre um QR padrão**, nunca Micro QR: conteúdo curto sai no formato que qualquer
      leitor de celular lê.
- [ ] **Conteúdo vazio é recusado**, e conteúdo maior do que cabe no maior símbolo é recusado **dizendo
      o tamanho** — nunca sai truncado.
- [ ] A **zona de silêncio** entra no arquivo do símbolo: o QR não encosta no que estiver ao redor.
- [ ] Largura que deixe o **módulo abaixo do mínimo de impressão** é recusada na construção, e não
      descoberta no papel.
- [ ] O mesmo símbolo é **escrito uma vez no arquivo e só referenciado** onde aparece — em posições
      diferentes da mesma página e em toda página do documento.
- [ ] O QR entra no corpo como **bloco**, centralizado como um parágrafo, declarando o conteúdo e a
      largura em milímetros — nenhum documento desenha símbolo por conta própria.
- [ ] O QR entra no rodapé como **marca**, alinhado à direita da faixa do endereço, em toda página.
- [ ] O documento de amostra traz o QR no corpo e no rodapé, e `uv run pytest -m artefato` grava o PDF
      e imprime o caminho para a leitura com o celular.
- [ ] A skill `documento-oficial` descreve o bloco e a marca de QR: o que carregam, o que os recusa e
      como conferi-los.

## 3 · Domínio

`services/utils/qr_code/` não modela domínio: é o vocabulário do **símbolo** — o conteúdo, o nível de
correção, a zona de silêncio e o lado da matriz em módulos. Ele não conhece página, milímetro nem PDF:
assentar o símbolo no papel é do motor da SPEC [documentos_oficiais/001](001-motor-de-pdf.md), e decidir
o que o QR diz é do documento (SPEC [documentos_oficiais/003](003-documento-oficial-timbrado.md)).

**`services/utils/qr_code/models.py`**
```python
class CorrecaoQr(StrEnum):
    """Quanto do símbolo pode ser perdido e ele ainda ser lido. O valor é a letra do padrão, que é
    o que a biblioteca recebe."""

    BAIXA = "L"
    MEDIA = "M"
    QUARTIL = "Q"
    MAXIMA = "H"


class QrCodeInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    conteudo: str = Field(min_length=1)
    # Documento oficial é dobrado, carimbado e digitalizado: o padrão é o nível que tolera 25% de
    # perda, e não o mínimo.
    correcao: CorrecaoQr = CorrecaoQr.QUARTIL
    # A zona de silêncio se mede em MÓDULOS, não em milímetros: ela é do símbolo, não da página.
    silencio_modulos: int = Field(default=4, ge=1)


class QrCodeSvg(BaseModel):
    """O símbolo pronto. `modulos` é o lado da matriz COM o silêncio — é ele que divide a largura
    impressa e diz quanto milímetro cada módulo recebe."""

    model_config = ConfigDict(frozen=True)

    svg: bytes
    modulos: int
```

**`services/domain/documento_oficial/models/blocos.py`** — o bloco novo e a união, que é o que muda.
Os demais blocos seguem os da SPEC [documentos_oficiais/003](003-documento-oficial-timbrado.md).
```python
class QrCode(BlocoDocumento):
    """O bloco guarda o que o símbolo DIZ, nunca a imagem dele: o QR é derivado do conteúdo, e
    guardá-lo pronto seria o mesmo dado em dois lugares."""

    tipo: Literal["qr_code"] = "qr_code"
    conteudo: str = Field(min_length=1)
    # Sem default, como na `Imagem`: quanto o símbolo ocupa é decisão do documento, não do tema.
    largura_mm: float


Bloco = Annotated[
    # ALTERADO nesta SPEC: `QrCode` entra na união.
    Titulo | Subtitulo | Paragrafo | Lista | Tabela | Imagem | QrCode,
    Field(discriminator="tipo"),
]
```

**`services/domain/documento_oficial/models/marcacao.py`** — a config do papel timbrado, inteira, com
o campo novo. Quanto o QR do rodapé ocupa é medida do papel, como a do timbre e a da marca d'água.
```python
class MarcacaoConfig(BaseModel):
    """O que distingue um papel timbrado de outro. Os caminhos não têm default: eles dependem da
    raiz do projeto, que o domínio não conhece."""

    model_config = ConfigDict(frozen=True)

    logo_horizontal: Path
    # O SVG da marca d'água já é o claro no repositório: a marca não clareia nada.
    logo_vertical: Path
    # Um nível por item, e não uma linha só: é a marca que decide se empilha ou junta.
    unidade: tuple[str, ...] = UNIDADE_PADRAO
    endereco: tuple[str, ...] = ENDERECO_PADRAO
    largura_timbre_mm: float = 58.0
    largura_marca_dagua_mm: float = 105.0
    # ALTERADO nesta SPEC: campo novo. 25 mm é o menor valor em que uma URL de verificação com
    # correção QUARTIL ainda deixa cada módulo acima do mínimo de impressão (§6).
    largura_qr_rodape_mm: float = 25.0
    margem_lateral_mm: float = 25.0
    margem_vertical_mm: float = 15.0
    respiro_mm: float = 8.0
```

## 4 · Fora de escopo
- Legenda sob o símbolo, e mantê-la colada a ele na quebra de página — sem dono ainda.
- O código de verificação, a rota que o resolve e o registro do que foi emitido — SPEC da certidão de
  lançamento.
- A `Imagem` do corpo passar a ser referenciada como o QR, em vez de reescrita a cada ocorrência —
  sem dono ainda.
- QR na tela, inline num partial HTMX — sem dono ainda.
- Micro QR, Data Matrix e código de barras — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/utils/pdf/tabela/escritor.py` → `TabelaPdf`: a forma de um escritor do motor — callable,
  DTO de entrada, flowable de saída.
- `@services/domain/documento_oficial/marcas.py` → `RodapeEndereco`: as linhas de endereço no pé.
- `@services/domain/documento_oficial/marcas.py` → `CabecalhoTimbrado`: duas marcas lado a lado na
  mesma faixa, em vez de empilhadas.
- `@services/domain/documento_oficial/models/tema.py` → `Tema`: os estilos já resolvidos do documento.
- `@tests/conftest.py` → `publicar_artefato`: grava o artefato fora do repositório, imprime o caminho e
  o abre no visualizador do SO.
- Skills: `ontologia`, `escrever-testes`, `documento-oficial`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`services/utils/qr_code/gerador.py`** — o símbolo, e só. O que sai daqui é vetor pronto para ser
pintado, por quem for pintá-lo: papel hoje, tela quando houver.
```python
import io

import segno
from segno.encoder import DataOverflowError


class GerarQrCode:
    """Callable: conteúdo → o símbolo em SVG. Vetor, e não raster: o QR é uma malha de quadrados, e
    quem o amplia ou o imprime em 600 dpi não pode receber pixel."""

    def __call__(self, pedido: QrCodeInput) -> QrCodeSvg:
        return self.pipeline(pedido)

    def pipeline(self, pedido: QrCodeInput) -> QrCodeSvg:
        simbolo = self._codificar(pedido)
        return QrCodeSvg(
            svg=self._svg(simbolo, pedido),
            # `symbol_size` já conta o silêncio dos dois lados: é a matriz como ela vai para o
            # arquivo, e é essa conta que a largura impressa divide.
            modulos=simbolo.symbol_size(scale=1, border=pedido.silencio_modulos)[0],
        )

    def _codificar(self, pedido: QrCodeInput) -> segno.QRCode:
        # `make_qr`, e não `make`: `make` degrada conteúdo curto para Micro QR, que boa parte dos
        # leitores de celular não lê. O nível declarado é o MÍNIMO — a biblioteca o eleva quando
        # a sobra cabe no mesmo símbolo.
        try:
            return segno.make_qr(pedido.conteudo, error=pedido.correcao.value)
        except DataOverflowError as erro:
            raise ValueError(
                f"Conteúdo de {len(pedido.conteudo)} caracteres não cabe em nenhum QR Code: {erro}"
            ) from erro

    def _svg(self, simbolo: segno.QRCode, pedido: QrCodeInput) -> bytes:
        buffer = io.BytesIO()
        # `scale=1`: cada módulo é uma unidade no SVG, e quem dá tamanho é a página. A declaração
        # XML e as classes CSS saem porque o svglib não as usa e só engordam os bytes.
        simbolo.save(
            buffer,
            kind="svg",
            scale=1,
            border=pedido.silencio_modulos,
            xmldecl=False,
            svgclass=None,
            lineclass=None,
        )
        return buffer.getvalue()


gerar_qr_code = GerarQrCode()
```

**`services/utils/qr_code/__init__.py`** — só reexporta (CLAUDE.md §7.2).
```python
from .gerador import GerarQrCode, gerar_qr_code
from .models import CorrecaoQr, QrCodeInput, QrCodeSvg

__all__ = [
    "CorrecaoQr",
    "GerarQrCode",
    "QrCodeInput",
    "QrCodeSvg",
    "gerar_qr_code",
]
```

**`services/utils/pdf/forma.py`** — o vetor escrito UMA vez no arquivo e referenciado onde aparecer.
É a peça que a marca do cabeçalho já usava por dentro da `Folha`, agora com nome próprio, porque o
corpo do documento também precisa dela.
```python
class VetorNomeado(BaseModel):
    """Um desenho e o NOME sob o qual ele entra no arquivo. O nome identifica o desenho, nunca o
    lugar em que ele aparece: é isso que faz o mesmo símbolo em toda página ser uma referência só,
    e dois símbolos diferentes na mesma página não se confundirem."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    desenho: Drawing
    nome: str


class DesenharForma:
    """Callable: escreve o vetor no arquivo na primeira vez que ele aparece e, daí em diante, só o
    referencia. `x` e `y` são o canto INFERIOR esquerdo, em pontos, no eixo do reportlab."""

    def __call__(self, canvas: Canvas, vetor: VetorNomeado, x: float, y: float) -> None:
        return self.pipeline(canvas, vetor, x, y)

    def pipeline(self, canvas: Canvas, vetor: VetorNomeado, x: float, y: float) -> None:
        self._escrever_uma_vez(canvas, vetor)
        self._referenciar(canvas, vetor.nome, x, y)

    def _escrever_uma_vez(self, canvas: Canvas, vetor: VetorNomeado) -> None:
        if vetor.nome in self._formas(canvas):
            return
        canvas.beginForm(vetor.nome)
        # Na ORIGEM do form, e não na posição final: quem posiciona é a translação da referência, e é
        # ela que permite o mesmo desenho aparecer em pontos diferentes sem um form por ponto.
        renderPDF.draw(vetor.desenho, canvas, 0, 0)
        canvas.endForm()
        self._formas(canvas).add(vetor.nome)

    def _referenciar(self, canvas: Canvas, nome: str, x: float, y: float) -> None:
        # `doForm` desenha no estado gráfico corrente: transladar antes é o que posiciona a
        # referência, e o `saveState` é o que impede a translação de vazar para o resto da página.
        canvas.saveState()
        canvas.translate(x, y)
        canvas.doForm(nome)
        canvas.restoreState()

    def _formas(self, canvas: Canvas) -> set[str]:
        # O registro vive no CANVAS: há um canvas por documento, e é ele que guarda os forms já
        # escritos.
        return canvas.__dict__.setdefault("_formas_escritas", set())


class VetorReferenciado(Flowable):
    """O mesmo vetor, agora no FLUXO do corpo. `Drawing` também é `Flowable`, mas se reescreve por
    ocorrência; este referencia, e é o que permite repetir o símbolo sem repetir os bytes."""

    def __init__(self, vetor: VetorNomeado) -> None:
        super().__init__()
        self._vetor = vetor
        self.width = vetor.desenho.width
        self.height = vetor.desenho.height
        self.hAlign = "CENTER"

    def wrap(self, largura_disponivel: float, altura_disponivel: float) -> tuple[float, float]:
        return self.width, self.height

    def draw(self) -> None:
        # A origem do canvas já é o canto inferior esquerdo do flowable quando o platypus chama
        # `draw`: a translação restante é zero.
        desenhar_forma(self.canv, self._vetor, 0.0, 0.0)


desenhar_forma = DesenharForma()
```

**`services/utils/pdf/folha.py`** — o método inteiro, alterado: a `Folha` deixa de conhecer a mecânica
do form e passa a só converter milímetro em ponto.
```python
    # ALTERADO nesta SPEC: recebe o `VetorNomeado` no lugar de desenho + nome soltos, e delega a
    # escrita do form. `y_mm` continua sendo o TOPO do desenho, medido do alto da folha.
    def vetor(self, x_mm: float, y_mm: float, vetor: VetorNomeado) -> None:
        desenhar_forma(
            self._canvas,
            vetor,
            x_mm * mm,
            # A altura entra na conta: a origem do reportlab é o canto INFERIOR.
            self._y(y_mm) - vetor.desenho.height,
        )
```

**`services/utils/pdf/vetor.py`** — a peça de imagem do motor, que passa a aceitar o SVG que nunca
tocou o disco.
```python
class CarregarVetor:
    """Callable: SVG → `Drawing` do reportlab, na largura pedida. Vetor de ponta a ponta: nada é
    rasterizado."""

    # ALTERADO nesta SPEC: a origem passa a ser caminho OU SVG em memória. O símbolo do QR nasce em
    # bytes; gravar um temporário só para reabri-lo seria IO a cada documento emitido e uma pasta a
    # limpar.
    def __call__(self, origem: Path | BinaryIO, largura_mm: float) -> Drawing:
        desenho = svg2rlg(str(origem) if isinstance(origem, Path) else origem)
        if desenho is None:
            raise ValueError(f"SVG inválido ou ilegível: {origem}")
        fator = (largura_mm * mm) / desenho.width
        desenho.width *= fator
        desenho.height *= fator
        desenho.scale(fator, fator)
        return desenho
```

**`services/utils/pdf/qr_code.py`** — o símbolo virando medida de página, ao lado do `vetor.py` que ele
especializa. É aqui que a medida ilegível é recusada e que o símbolo ganha a identidade com que entra
no arquivo. **Não é escritor**: quem escreve são as duas peças de `documento_oficial` abaixo, e as
duas partem daqui.
```python
# Abaixo disto o módulo some na impressão a laser e no scanner do protocolo.
MODULO_MINIMO_MM = 0.5


class QrCodePdfInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    # O símbolo inteiro, não o conteúdo dele: gerar o QR é do utilitário, e recopiar conteúdo e
    # correção aqui seria a mesma declaração em dois lugares.
    simbolo: QrCodeSvg
    largura_mm: float

    @model_validator(mode="after")
    def _modulo_cabe_no_papel(self) -> "QrCodePdfInput":
        # Recusar aqui, e não na impressão: símbolo pequeno demais sai bonito no PDF e só falha no
        # celular de quem recebeu o documento.
        modulo_mm = self.largura_mm / self.simbolo.modulos
        if modulo_mm < MODULO_MINIMO_MM:
            raise ValueError(
                f"{self.largura_mm} mm deixam cada módulo com {modulo_mm:.2f} mm, abaixo do mínimo "
                f"de {MODULO_MINIMO_MM} mm: este símbolo precisa de ao menos "
                f"{self.simbolo.modulos * MODULO_MINIMO_MM:.1f} mm."
            )
        return self


class QrCodePdf:
    """Callable: símbolo → o vetor nomeado do QR. Especialização do caminho de imagem do motor — o
    SVG do QR entra pelo mesmo `carregar_vetor` do timbre e da marca d'água, e nada aqui redesenha
    nada."""

    def __call__(self, pedido: QrCodePdfInput) -> VetorNomeado:
        return self.pipeline(pedido)

    def pipeline(self, pedido: QrCodePdfInput) -> VetorNomeado:
        return VetorNomeado(
            desenho=carregar_vetor(BytesIO(pedido.simbolo.svg), pedido.largura_mm),
            nome=self._nome(pedido),
        )

    def _nome(self, pedido: QrCodePdfInput) -> str:
        # O nome sai do que se desenha — os bytes do símbolo e a largura que os escala. Dois QRs de
        # conteúdos diferentes na mesma página ganham forms distintos, e o mesmo QR repetido em
        # toda página ganha o MESMO, sem ninguém batizar nada à mão.
        digest = sha256(pedido.simbolo.svg).hexdigest()[:12]
        return f"qr_{digest}_{int(pedido.largura_mm * 100)}"


qr_code_pdf = QrCodePdf()
```

**`services/utils/pdf/__init__.py`** — passa a reexportar a forma e o símbolo, como já faz com a tabela
e com o carregador de vetor.
```python
from .forma import DesenharForma, VetorNomeado, VetorReferenciado, desenhar_forma
from .qr_code import MODULO_MINIMO_MM, QrCodePdf, QrCodePdfInput, qr_code_pdf
```

**`services/domain/documento_oficial/escritores.py`** — o **primeiro escritor**: o QR no fluxo do
corpo, centralizado como um parágrafo.
```python
class EscritorQrCode:
    """O bloco diz o que o QR carrega; gerar o símbolo é do utilitário e assentá-lo é do motor.
    Sem `Tema` no construtor: um QR não tem cor, fonte nem entrelinha a herdar."""

    def __call__(self, bloco: QrCode) -> Flowable:
        return self.pipeline(bloco)

    def pipeline(self, bloco: QrCode) -> Flowable:
        # `VetorReferenciado`, e não o `Drawing` cru: o símbolo entra no arquivo uma vez, e o mesmo
        # QR repetido no corpo vira referência em vez de bytes novos.
        return VetorReferenciado(self._vetor(bloco))

    def _vetor(self, bloco: QrCode) -> VetorNomeado:
        return qr_code_pdf(
            QrCodePdfInput(
                simbolo=gerar_qr_code(QrCodeInput(conteudo=bloco.conteudo)),
                largura_mm=bloco.largura_mm,
            )
        )


def montar_escritores(tema: Tema) -> dict[str, Callable[[Any], Flowable]]:
    return {
        # ... os que já existem
        "qr_code": EscritorQrCode(),
    }
```

**`services/domain/documento_oficial/marcas.py`** — o **segundo escritor**: o QR fora do fluxo, no pé
de toda página. `TimbreHorizontal` e `MarcaDagua` aparecem inteiras porque a chamada à `Folha` mudou.
```python
class TimbreHorizontal(Marca):
    """O logotipo da Secretaria, no alto de toda página."""

    posicao = Posicao.SUPERIOR

    def __init__(self, caminho_svg: Path, largura_mm: float) -> None:
        # ALTERADO nesta SPEC: o desenho carrega o nome junto. Ele segue carregado UMA vez e reusado
        # em toda página: o SVG tem centenas de traços, e reabri-lo por página seria o custo desta
        # marca multiplicado pelo tamanho do documento.
        self._vetor = VetorNomeado(desenho=carregar_vetor(caminho_svg, largura_mm), nome="timbre")
        # Medidas do que a marca pinta, não constantes escritas à mão: mudar a largura do timbre
        # não pode deixar a moldura do corpo desatualizada (Caveats da SPEC 001).
        self.altura_mm = self._vetor.desenho.height / mm
        self.largura_mm = self._vetor.desenho.width / mm

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        folha.vetor(faixa.esquerda_mm, faixa.topo_mm, self._vetor)


class MarcaDagua(Marca):
    """O logotipo vertical no meio do papel. Reserva ZERO: o corpo passa por cima."""

    posicao = Posicao.FUNDO
    altura_mm = 0.0

    def __init__(self, caminho_svg: Path, largura_mm: float) -> None:
        # ALTERADO nesta SPEC: idem `TimbreHorizontal`.
        self._vetor = VetorNomeado(
            desenho=carregar_vetor(caminho_svg, largura_mm), nome="marca_dagua"
        )

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        # Centralizada na FOLHA, e não na faixa: a marca de fundo ignora a moldura das outras.
        folha.vetor(
            (folha.tamanho.largura_mm - self._vetor.desenho.width / mm) / 2,
            (folha.tamanho.altura_mm - self._vetor.desenho.height / mm) / 2,
            self._vetor,
        )


class QrCodeRodape(Marca):
    """O símbolo de verificação no pé, encostado na DIREITA da faixa. Recebe o que o QR diz, nunca
    o desenho: quem gera o símbolo é o utilitário, como no bloco do corpo."""

    posicao = Posicao.INFERIOR

    def __init__(self, conteudo: str, largura_mm: float) -> None:
        self._vetor = qr_code_pdf(
            QrCodePdfInput(
                simbolo=gerar_qr_code(QrCodeInput(conteudo=conteudo)),
                largura_mm=largura_mm,
            )
        )
        # Medida do que a marca pinta, como no timbre: o símbolo escolhe a versão do QR conforme o
        # conteúdo, e uma altura escrita à mão desalinharia com a matriz que saiu.
        self.altura_mm = self._vetor.desenho.height / mm
        self.largura_mm = self._vetor.desenho.width / mm

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        # O canto direito da faixa, e não a esquerda: o endereço ocupa a esquerda do mesmo pé.
        folha.vetor(
            faixa.esquerda_mm + faixa.largura_mm - self.largura_mm,
            faixa.topo_mm,
            self._vetor,
        )


class RodapeComQr(Marca):
    """Endereço à esquerda, QR à direita, na MESMA faixa — o espelho do `CabecalhoTimbrado`.
    Empilhadas, as duas marcas somariam a altura de cada uma e o pé comeria a página."""

    posicao = Posicao.INFERIOR

    def __init__(self, endereco: RodapeEndereco, qr_code: QrCodeRodape) -> None:
        self._endereco = endereco
        self._qr_code = qr_code
        self.altura_mm = max(endereco.altura_mm, qr_code.altura_mm)

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        self._endereco(faixa, folha)
        self._qr_code(faixa, folha)
```

**`services/domain/documento_oficial/marcacoes_concretas/fazenda_dimap.py`** — o papel timbrado passa a
aceitar o que o QR de verificação diz; sem ele, o pé é o de sempre.
```python
def marcacao_fazenda_dimap(
    config: MarcacaoConfig,
    tema: Tema,
    qr_verificacao: str | None = None,
) -> MarcacaoDocumento:
    return MarcacaoDocumento(
        principal=Marcacao(
            marcas=(
                CabecalhoTimbrado(...),
                MarcaDagua(config.logo_vertical, config.largura_marca_dagua_mm),
                _rodape(config, tema, qr_verificacao),
                NumeracaoPaginas(tema.estilo_rodape_marca, tema.entrelinha_marca_mm),
            ),
            ...
        )
    )


def _rodape(config: MarcacaoConfig, tema: Tema, qr_verificacao: str | None) -> Marca:
    # `None` é o documento SEM verificação, e não um QR vazio: a maioria dos atos não tem código a
    # conferir, e um símbolo em branco no pé seria pior que símbolo nenhum.
    endereco = RodapeEndereco(config.endereco, tema.estilo_rodape_marca, tema.entrelinha_marca_mm)
    if qr_verificacao is None:
        return endereco
    return RodapeComQr(endereco, QrCodeRodape(qr_verificacao, config.largura_qr_rodape_mm))
```

**`services/domain/documento_oficial/amostra.py`** — o endereço que a conferência com o celular tem
para comparar, num lugar só, e o QR do corpo que o carrega.
```python
def url_de_conferencia(ambiente: str) -> str:
    """O que os DOIS QRs da amostra dizem — o do corpo e o do rodapé. Montar a URL nos dois pontos
    de chamada deixaria a conferência passar com um deles apontando para outro lugar."""
    return f"https://{ambiente}/documentos/amostra"


    def _blocos(self, pedido: DocumentoAmostraInput) -> tuple[Bloco, ...]:
        return (
            # ... os que já existem
            QrCode(conteudo=url_de_conferencia(pedido.ambiente), largura_mm=30.0),
        )
```

**`apps/core/management/commands/gerar_documento_amostra.py`** — a orquestração, que é quem sabe o
ambiente e monta a marcação.
```python
        marcacao = marcacao_fazenda_dimap(
            build_marcacao_config(settings),
            tema,
            qr_verificacao=url_de_conferencia(ambiente),
        )
```

**`pyproject.toml`** — `segno` codifica o QR e escreve o SVG; sem dependência de teste nova, porque o
`pypdf` da SPEC 001 é o que confere o que entrou na página.
```toml
dependencies = [
    # ... as que já existem
    "segno>=1.6",
]
```

## 7 · Caveats
A escrita do form sai da `Folha` para peça própria, desenha na origem em vez de assar a posição, e
`Folha.vetor` passa a receber `VetorNomeado` no lugar de desenho + nome soltos — alterando peça já
entregue pela SPEC 001 e as duas marcas que a chamam. É o que permite o mesmo símbolo aparecer no corpo
e no pé, em pontos diferentes de páginas diferentes, sem um form por posição, e o que prende o nome ao
desenho em vez de ao ponto de chamada. O custo é churn em código implementado e nos testes que o fixam,
e a limitação declarada na SPEC 001 deixa de valer para quem a lê sem esta ao lado.

O `carregar_vetor` passa a aceitar SVG em memória além de caminho, alterando peça já entregue pela SPEC
001. O símbolo do QR nasce em bytes, e gravar um temporário só para reabri-lo seria IO a cada emissão e
uma pasta a limpar. O custo é que a assinatura descrita na SPEC 001 deixa de ser a vigente.

O nome do form sai de um `sha256` dos bytes do SVG truncado em 12 dígitos hexadecimais, mais a largura
em centésimos de milímetro. É o que faz a identidade do desenho ser o próprio desenho, sem ninguém
batizar símbolo à mão. O custo é uma colisão teórica em 48 bits, que faria dois QRs distintos de mesma
largura desenharem o mesmo símbolo.

`segno` entra como dependência para algo que o reportlab, já na árvore, sabe fazer (`QrCodeWidget`). É
o que mantém `services/utils/qr_code/` neutro — devolve SVG, e serve à tela tanto quanto ao papel — e
conserva `services/utils/pdf/` como a única costura do projeto com o reportlab. O custo é uma
dependência a mais para uma capacidade que já existia na árvore.

`services/utils/pdf/` passa a conhecer `services/utils/qr_code/`, que antes não conhecia. A recusa por
módulo ilegível é regra de página, em milímetros, e só o motor fala milímetro: deixá-la fora dele
obrigaria cada documento que imprime um QR a repetir a conta. O custo é que o motor deixa de ser
genérico quanto ao que assenta — ele agora sabe que existe um tipo de símbolo.

O mínimo de 0,5 mm por módulo é constante do motor, e não valor de tema nem de ambiente: é limite
físico de impressão e leitura, não escolha visual do documento. O custo é que papel ou impressora que
tolerem menos exigem mexer no código, e nada avisa quem imprime em condição pior que a prevista.

O QR do rodapé reserva a própria altura na faixa, e uma URL de verificação com correção QUARTIL sai em
45 módulos — 25 mm no mínimo legível. Reservar é o que impede o corpo de passar por cima dele, como a
marca d'água faz. O custo é cerca de 14 mm a mais de margem inferior em todo documento que traga o
símbolo no pé, e um símbolo que só é "pequeno" perto da página.

`marcacao_fazenda_dimap` ganha um parâmetro opcional e o papel timbrado passa a saber que existe QR de
verificação. Papel timbrado é a composição das marcas do documento, e o pé com símbolo é uma delas. O
custo é que emitir um documento com verificação exige a orquestração passar o conteúdo do QR duas vezes
— uma para o bloco do corpo, outra para a marcação.

## 8 · Testes (TDD)
- `test_simbolo_sai_como_svg_vetorial_em_memoria` — o retorno traz bytes de SVG que o `svg2rlg` lê como
  `Drawing`, e nenhum arquivo é criado no diretório de trabalho durante a geração.
- `test_simbolo_eh_sempre_qr_padrao_com_silencio` — conteúdo de um caractere sai em QR padrão, e não em
  Micro QR; `modulos` é o lado da matriz mais o silêncio dos dois lados.
- `test_conteudo_vazio_e_longo_demais_sao_recusados` — conteúdo vazio levanta na construção do input;
  conteúdo acima da capacidade do maior símbolo levanta dizendo o tamanho, em vez de sair truncado.
- `test_largura_que_deixa_o_modulo_ilegivel_eh_recusada` — largura abaixo de `modulos × 0,5 mm` levanta
  na construção do pedido, e a largura no limite passa.
- `test_carregar_vetor_aceita_caminho_e_memoria` — o mesmo SVG lido do disco e lido de bytes produz
  `Drawing` de mesmas medidas.
- `test_mesmo_vetor_em_posicoes_diferentes_referencia_uma_forma_so` — o mesmo símbolo no corpo e em
  toda página declara UM Form XObject; dobrar as páginas não muda a contagem nem dobra o arquivo, e a
  página não declara XObject de imagem: o símbolo é traço, não bitmap.
- `test_qrs_de_conteudos_diferentes_ganham_formas_distintas` — dois QRs de conteúdos diferentes na
  mesma página declaram dois forms, e o mesmo conteúdo em larguras diferentes também.
- `test_bloco_de_qr_vira_o_simbolo_do_conteudo` — o bloco chega pelo registro de escritores e sai o
  flowable do símbolo na largura declarada, centralizado no corpo.
- `test_qr_do_rodape_pinta_a_direita_da_faixa` — a marca desenha encostada na borda direita da faixa
  recebida, e a faixa do pé passa a ter a altura do símbolo, não a das linhas de endereço.
- `test_amostra_com_qr_no_corpo_e_no_rodape` — grava a amostra com os dois símbolos e imprime o
  caminho, para a leitura com o celular. *(marker `artefato`)*
