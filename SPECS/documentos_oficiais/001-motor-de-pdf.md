---
spec: documentos_oficiais/001
versao: v1
atualizado_em: 2026-09-06
testes_tdd: false
implementado: false
changelog:
  - v1: versão inicial
---

# SPEC documentos_oficiais/001 — Motor de PDF: folha em milímetros, marcação composta e bytes

## 1 · User story
**Requisito não-funcional** — o sistema passa a saber virar conteúdo em PDF paginado, com o que se
repete em toda página declarado como composição de marcas independentes, sem que quem chama fale
coordenada de PDF nem veja o reportlab.

## 2 · Condições de pronto
- [ ] O PDF sai como **bytes**: nenhum arquivo é criado em disco durante a geração.
- [ ] A marcação se **repete integralmente em toda página**, inclusive na primeira e na última, e
      trocar a marcação troca tudo que se repete sem mudança alguma no corpo.
- [ ] Cada marca declara a **posição e a altura que reserva**, e a área útil do corpo é o que sobra
      depois de todas: nada do corpo invade a faixa de uma marca, e a marca de fundo não reserva área.
- [ ] A **marca de fundo é pintada sob o corpo**: o texto é lido por cima dela, sem perda de contraste.
- [ ] Um vetor **esmaecido sai uniforme** apesar de ter centenas de traços sobrepostos.
- [ ] A marca sabe **que página é e quantas há no total**: "Página X de Y" sai com Y igual ao total
      real de páginas.
- [ ] Conteúdo mais longo que uma página **quebra e continua** na seguinte, sem cortar linha ao meio.
- [ ] O mesmo vetor repetido **não é reescrito por página**: dobrar o número de páginas não dobra o
      tamanho do arquivo nem o tempo de geração.
- [ ] O documento aceita **marcação própria para a primeira, para a última e para páginas nomeadas por
      número** — onde nenhuma reivindica, vale a principal, que é obrigatória —, e a **orientação** é
      declarada pela marcação, com marcações divergentes **recusadas na construção**.

## 3 · Domínio

`services/utils/pdf/` não modela domínio: é o vocabulário da **página**. Ele conhece milímetros,
posições e faixas, e nada sobre o que o documento diz — quem sabe disso é o domínio que o consome
(SPEC [documentos_oficiais/003](003-documento-oficial-timbrado.md)).

A origem é o **canto superior esquerdo**, porque é como se lê uma página; o reportlab mede em pontos a
partir do rodapé, e a conversão morre na `Folha` do §6.

Os models são um pacote de dois vocabulários — a folha e o que cabe nela, e como uma linha se escreve
—, reexportados pelo `__init__.py`.

**`services/utils/pdf/models/pagina.py`**
```python
class Orientacao(StrEnum):
    RETRATO = "retrato"
    PAISAGEM = "paisagem"


class Posicao(StrEnum):
    """Onde a marca se pinta. FUNDO é a exceção: não reserva área e é pintada ANTES do corpo."""

    SUPERIOR = "superior"
    INFERIOR = "inferior"
    FUNDO = "fundo"


class TamanhoPagina(BaseModel):
    """A folha já orientada."""

    model_config = ConfigDict(frozen=True)

    largura_mm: float
    altura_mm: float


class FormatoPagina(BaseModel):
    """O papel antes de orientado: é `orientar()` que decide qual lado vira largura."""

    model_config = ConfigDict(frozen=True)

    menor_lado_mm: float
    maior_lado_mm: float

    def orientar(self, orientacao: Orientacao) -> TamanhoPagina: ...


A4 = FormatoPagina(menor_lado_mm=210.0, maior_lado_mm=297.0)
A3 = FormatoPagina(menor_lado_mm=297.0, maior_lado_mm=420.0)


class Margens(BaseModel):
    """A moldura que o corpo não invade."""

    model_config = ConfigDict(frozen=True)

    esquerda_mm: float
    direita_mm: float
    superior_mm: float
    inferior_mm: float


class Faixa(BaseModel):
    """O retângulo que pertence a UMA marca. Ela pinta aqui dentro e não conhece o resto da página."""

    model_config = ConfigDict(frozen=True)

    esquerda_mm: float
    topo_mm: float
    largura_mm: float
    altura_mm: float
```

**`services/utils/pdf/models/texto.py`**
```python
from reportlab.lib.colors import Color


class EstiloTexto(BaseModel):
    """O que a `Folha` precisa para escrever uma linha. Os valores vêm de quem chama, nunca daqui."""

    # `Color` é do reportlab e não tem schema Pydantic — ver Caveats.
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    fonte: str
    corpo_pt: float
    cor: Color
```

**`services/utils/pdf/models/__init__.py`** — só reexporta (CLAUDE.md §7.2).
```python
from .pagina import A3, A4, Faixa, FormatoPagina, Margens, Orientacao, Posicao, TamanhoPagina
from .texto import EstiloTexto

__all__ = [
    "A3",
    "A4",
    "EstiloTexto",
    "Faixa",
    "FormatoPagina",
    "Margens",
    "Orientacao",
    "Posicao",
    "TamanhoPagina",
]
```

## 4 · Fora de escopo
- Os blocos do documento oficial, seus escritores, o tema e as marcas concretas (timbre, marca d'água,
  rodapé) — SPEC `documentos_oficiais/003`.
- Retrato e paisagem no mesmo documento — sem dono ainda; aqui a orientação é do documento.
- Tabela — o flowable, as regras de estilo e o escritor dela: SPEC
  [documentos_oficiais/002](002-motor-de-tabela.md).
- Persistência do PDF gerado — o motor devolve bytes e quem chama decide o destino.

## 5 · Peças de referência a compor
- Skills: `ontologia`, `escrever-testes`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`services/utils/pdf/folha.py`** — a superfície de desenho, e a única peça do projeto que fala
coordenada de PDF.
```python
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas


class Folha:
    """UMA página sendo pintada. Ela sabe que número é e quantas há no total — é isso que permite
    'Página X de Y' sem ninguém contar página."""

    def __init__(self, canvas: Canvas, tamanho: TamanhoPagina, pagina: int, total: int) -> None:
        self._canvas = canvas
        self.tamanho = tamanho
        self.pagina = pagina
        self.total = total

    def texto(self, x_mm: float, y_mm: float, conteudo: str, estilo: EstiloTexto) -> None:
        self._canvas.setFont(estilo.fonte, estilo.corpo_pt)
        self._canvas.setFillColor(estilo.cor)
        self._canvas.drawString(x_mm * mm, self._y(y_mm), conteudo)

    def vetor(self, x_mm: float, y_mm: float, desenho: Drawing, nome: str) -> None:
        # O vetor vira Form XObject: escrito UMA vez no arquivo e só REFERENCIADO a cada página.
        # Redesenhá-lo por página multiplica tempo e tamanho pelo número de páginas — nove páginas
        # saem em 2,4 MB e 2,6 s redesenhando, contra 284 KB e 330 ms assim.
        if nome not in self._formas():
            self._canvas.beginForm(nome)
            # A posição é assada no form, porque a marca pinta sempre no mesmo ponto de toda
            # página. A altura entra na conta: a origem do reportlab é o canto INFERIOR.
            renderPDF.draw(desenho, self._canvas, x_mm * mm, self._y(y_mm) - desenho.height)
            self._canvas.endForm()
            self._formas().add(nome)
        self._canvas.doForm(nome)

    def _formas(self) -> set[str]:
        # O registro vive no CANVAS, não na folha: há uma folha por página e um canvas por
        # documento, e é o canvas que guarda os forms já escritos.
        return self._canvas.__dict__.setdefault("_formas_escritas", set())

    def _y(self, y_mm: float) -> float:
        # A inversão do eixo, num lugar só: y=0 é o topo da folha para quem chama.
        return (self.tamanho.altura_mm - y_mm) * mm
```

**`services/utils/pdf/vetor.py`** — carregar o SVG e prepará-lo. `esmaecer` carrega a descoberta que
mais importa nesta SPEC.
```python
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import Color
from reportlab.lib.units import mm
from svglib.svglib import svg2rlg


class CarregarVetor:
    """Callable: caminho de SVG → Drawing do reportlab, na largura pedida. Vetor de ponta a ponta:
    nada é rasterizado."""

    def __call__(self, caminho: Path, largura_mm: float) -> Drawing:
        desenho = svg2rlg(str(caminho))
        fator = (largura_mm * mm) / desenho.width
        desenho.width *= fator
        desenho.height *= fator
        desenho.scale(fator, fator)
        return desenho


def esmaecer(desenho: Drawing, forca: float) -> Drawing:
    """Clareia cada cor CONTRA O BRANCO do papel, em vez de aplicar transparência.

    Alpha por forma seria o caminho óbvio e está errado aqui: um logotipo tem centenas de traços
    sobrepostos, e alpha COMPÕE a cada camada — 0,08 repetido vinte vezes satura em quase opaco.
    Clareando a cor, sobreposição não escurece: vinte formas cinza-claro empilhadas continuam
    cinza-claro.
    """
    for atributo in ("fillColor", "strokeColor"):
        cor = getattr(desenho, atributo, None)
        if cor is not None:
            setattr(desenho, atributo, _clarear(cor, forca))
    for filho in getattr(desenho, "contents", ()):
        esmaecer(filho, forca)
    return desenho


def _clarear(cor: Color, forca: float) -> Color:
    return cor.clone(
        red=cor.red + (1 - cor.red) * forca,
        green=cor.green + (1 - cor.green) * forca,
        blue=cor.blue + (1 - cor.blue) * forca,
    )


carregar_vetor = CarregarVetor()
```

**`services/utils/pdf/marcacao.py`** — a composição. A `Marca` é ABC porque aqui a herança define
interface, e nada mais (CLAUDE.md §7.1). A `Marcacao` empilha as marcas por posição, dá a cada uma a
faixa dela, e **deriva** as margens da soma do que reservaram.
```python
class Marca(ABC):
    """O que se pinta em toda página, fora do fluxo do corpo."""

    posicao: Posicao
    altura_mm: float

    @abstractmethod
    def __call__(self, faixa: Faixa, folha: Folha) -> None: ...


class Marcacao:
    """Callable em duas camadas: o fundo vai ANTES do corpo, as bordas DEPOIS. Marca nova entra na
    tupla e em lugar nenhum mais — nem nas margens, que são derivadas."""

    orientacao: Orientacao

    def __init__(
        self,
        marcas: tuple[Marca, ...],
        margem_lateral_mm: float,
        respiro_mm: float,
        orientacao: Orientacao = Orientacao.RETRATO,
    ) -> None:
        self._marcas = marcas
        self.orientacao = orientacao
        self._margem_lateral_mm = margem_lateral_mm
        # A distância entre a última marca e a primeira linha do corpo: sem ela o texto encosta.
        self._respiro_mm = respiro_mm

    def margens(self, tamanho: TamanhoPagina) -> Margens:
        # SOMA, não máximo: duas marcas na mesma posição se empilham, não se sobrepõem. É isto que
        # faz acrescentar uma marca não pedir recálculo de margem em lugar nenhum. FUNDO fica de
        # fora da conta por construção: ela não reserva área, o corpo passa por cima dela.
        return Margens(
            esquerda_mm=self._margem_lateral_mm,
            direita_mm=self._margem_lateral_mm,
            superior_mm=self._reservado(Posicao.SUPERIOR) + self._respiro_mm,
            inferior_mm=self._reservado(Posicao.INFERIOR) + self._respiro_mm,
        )

    def pintar_fundo(self, folha: Folha) -> None:
        # A faixa da marca de fundo é a folha inteira: ela não disputa área com ninguém.
        inteira = Faixa(
            esquerda_mm=0.0,
            topo_mm=0.0,
            largura_mm=folha.tamanho.largura_mm,
            altura_mm=folha.tamanho.altura_mm,
        )
        for marca in self._marcas:
            if marca.posicao is Posicao.FUNDO:
                marca(inteira, folha)

    def pintar_bordas(self, folha: Folha) -> None:
        for marca, faixa in self._faixas(folha.tamanho):
            marca(faixa, folha)

    def _faixas(self, tamanho: TamanhoPagina) -> Iterator[tuple[Marca, Faixa]]:
        # As de cima descem do topo na ordem declarada; as de baixo sobem do pé. A marca recebe a
        # faixa pronta e nunca calcula posição absoluta — é o que a mantém trocável e reordenável.
        topo = 0.0
        pe = tamanho.altura_mm
        largura = tamanho.largura_mm - 2 * self._margem_lateral_mm
        for marca in self._marcas:
            if marca.posicao is Posicao.SUPERIOR:
                yield marca, Faixa(
                    esquerda_mm=self._margem_lateral_mm,
                    topo_mm=topo,
                    largura_mm=largura,
                    altura_mm=marca.altura_mm,
                )
                topo += marca.altura_mm
            elif marca.posicao is Posicao.INFERIOR:
                pe -= marca.altura_mm
                yield marca, Faixa(
                    esquerda_mm=self._margem_lateral_mm,
                    topo_mm=pe,
                    largura_mm=largura,
                    altura_mm=marca.altura_mm,
                )

    def _reservado(self, posicao: Posicao) -> float:
        return sum(marca.altura_mm for marca in self._marcas if marca.posicao is posicao)
```

**`services/utils/pdf/documento_marcado.py`** — a estratégia central: qual `Marcacao` vale em cada
página. É ela que o `DocumentoPdf` recebe, no lugar de uma `Marcacao` solta.
```python
class MarcacaoDocumento:
    """A principal é obrigatória e vale onde nenhuma outra reivindica a página."""

    def __init__(
        self,
        principal: Marcacao,
        primeira: Marcacao | None = None,
        ultima: Marcacao | None = None,
        *,
        # Keyword-only porque é o parâmetro de exceção: quem o usa está nomeando página por
        # número, e o nome no ponto de chamada é o que impede trocá-lo de posição sem perceber.
        marcacoes_especificas: Mapping[int, Marcacao] | None = None,
    ) -> None:
        self._principal = principal
        self._primeira = primeira
        self._ultima = ultima
        self._especificas = dict(marcacoes_especificas or {})
        self._validar()

    def para(self, pagina: int, total: int) -> Marcacao:
        # A ordem é a da especificidade: número exato vence extremo, e extremo vence a principal.
        # `primeira` antes de `ultima` decide o documento de UMA página, em que a mesma folha é
        # as duas coisas — e a primeira é a que o autor tinha em mente.
        if (especifica := self._especificas.get(pagina)) is not None:
            return especifica
        if pagina == 1 and self._primeira is not None:
            return self._primeira
        if pagina == total and self._ultima is not None:
            return self._ultima
        return self._principal

    def margens(self, tamanho: TamanhoPagina) -> Margens:
        # O MAIOR de cada borda, entre todas as marcações. A moldura do corpo é fixada antes de
        # existir página alguma, então ela precisa caber a marcação mais alta — é o que permite
        # capa com timbre grande e miolo com timbre compacto sem a paginação mudar.
        todas = [m.margens(tamanho) for m in self._todas()]
        return Margens(
            esquerda_mm=max(m.esquerda_mm for m in todas),
            direita_mm=max(m.direita_mm for m in todas),
            superior_mm=max(m.superior_mm for m in todas),
            inferior_mm=max(m.inferior_mm for m in todas),
        )

    def orientacao(self) -> Orientacao:
        return self._principal.orientacao

    def _validar(self) -> None:
        # Uma orientação por documento: o `pagesize` do reportlab é do documento inteiro, e
        # misturar retrato com paisagem exigiria PageTemplates — ver Fora de escopo.
        divergentes = {m.orientacao for m in self._todas()}
        if len(divergentes) > 1:
            raise ValueError(f"Marcações de orientações diferentes no mesmo documento: {divergentes}")
        # Página 0 ou negativa é erro de quem chama, e silenciá-la deixaria a marcação sumir.
        if invalidas := [n for n in self._especificas if n < 1]:
            raise ValueError(f"Página específica precisa ser 1-based: {sorted(invalidas)}")

    def _todas(self) -> tuple[Marcacao, ...]:
        opcionais = (self._primeira, self._ultima, *self._especificas.values())
        return (self._principal, *(m for m in opcionais if m is not None))
```

**`services/utils/pdf/numeracao.py`** — o corpo é montado UMA vez; a marcação inteira é pintada na
volta, quando o total de páginas já existe. É isso que torna "última página" resolvível — inclusive
para a camada de fundo, que no `onPage` do reportlab conheceria o número da página mas não o total.
```python
from reportlab.pdfgen.canvas import Canvas


class CanvasMarcado(Canvas):
    """Guarda cada página em vez de emiti-la, e só no `save` — com o total na mão — decide qual
    marcação vale em cada uma e a pinta."""

    def __init__(
        self,
        *args: object,
        marcacao: MarcacaoDocumento,
        tamanho: TamanhoPagina,
        **kwargs: object,
    ):
        super().__init__(*args, **kwargs)
        self._paginas: list[dict[str, Any]] = []
        self._marcacao = marcacao
        self._tamanho = tamanho

    def showPage(self) -> None:  # noqa: N802 — assinatura do reportlab
        self._paginas.append(dict(self.__dict__))
        # Sem reiniciar a página, o estado do canvas não se separa entre uma e outra e o
        # documento sai com menos páginas do que o conteúdo pede.
        self._startPage()

    def save(self) -> None:
        total = len(self._paginas)
        for numero, estado in enumerate(self._paginas, start=1):
            self.__dict__.update(estado)
            self._pintar(numero, total)
            super().showPage()
        super().save()

    def _pintar(self, numero: int, total: int) -> None:
        marcacao = self._marcacao.para(numero, total)
        folha = Folha(self, self._tamanho, pagina=numero, total=total)
        corpo = self._code
        # O fundo tem de ficar SOB o corpo. Como o corpo já desenhou, esvazia-se o código da
        # página, pinta-se o fundo e devolve-se o corpo por cima — a ordem no content stream é a
        # ordem de empilhamento do PDF. Sem isto a marca de fundo cobriria o que o documento diz.
        self._code = []
        marcacao.pintar_fundo(folha)
        self._code = self._code + corpo
        marcacao.pintar_bordas(folha)
```

**`services/utils/pdf/documento.py`** — flowables + marcação → bytes. O buffer é `BytesIO`: o reportlab
escreve em qualquer file-like, então **não há arquivo temporário nem pasta a limpar**.
```python
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, SimpleDocTemplate


class DocumentoPdfInput(BaseModel):
    # `Flowable` é do reportlab e não tem schema Pydantic — ver Caveats.
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    titulo: str
    corpo: tuple[Flowable, ...]
    marcacao: MarcacaoDocumento
    formato: FormatoPagina = A4


class DocumentoPdf:
    """Callable: o que fluir pelo corpo, dentro da moldura que a marcação deixou, vira PDF."""

    def __call__(self, pedido: DocumentoPdfInput) -> bytes:
        return self.pipeline(pedido)

    def pipeline(self, pedido: DocumentoPdfInput) -> bytes:
        buffer = BytesIO()
        # Sem `onFirstPage`/`onLaterPages`: as duas camadas são pintadas pelo canvas, na volta.
        # Aqui o corpo só flui dentro da moldura, sem saber que marcação vai receber.
        self._montar(buffer, pedido).build(
            list(pedido.corpo),
            canvasmaker=partial(
                CanvasMarcado,
                marcacao=pedido.marcacao,
                tamanho=self._tamanho(pedido),
            ),
        )
        return buffer.getvalue()

    def _tamanho(self, pedido: DocumentoPdfInput) -> TamanhoPagina:
        return pedido.formato.orientar(pedido.marcacao.orientacao())

    def _montar(self, buffer: BytesIO, pedido: DocumentoPdfInput) -> SimpleDocTemplate:
        tamanho = self._tamanho(pedido)
        margens = pedido.marcacao.margens(tamanho)
        return SimpleDocTemplate(
            buffer,
            pagesize=(tamanho.largura_mm * mm, tamanho.altura_mm * mm),
            leftMargin=margens.esquerda_mm * mm,
            rightMargin=margens.direita_mm * mm,
            topMargin=margens.superior_mm * mm,
            bottomMargin=margens.inferior_mm * mm,
            title=pedido.titulo,
        )


gerar_pdf = DocumentoPdf()
```

**`pyproject.toml`** — `reportlab` desenha o PDF; `svglib` converte SVG em vetor que o reportlab
assenta (`svg2rlg`); `pypdf` é só de teste, e é o que permite afirmar "o vetor está nas três páginas"
em vez de só conferir que os bytes começam com `%PDF`.
```toml
dependencies = [
    # ... as que já existem
    "reportlab>=4.2",
    "svglib>=1.5",
]

[dependency-groups]
dev = [
    # ... as que já existem
    "pypdf>=5.1",
]
```

## 7 · Caveats
`esmaecer` clareia cada cor contra o branco em vez de aplicar transparência. Alpha por forma compõe a
cada camada e satura num vetor de centenas de traços sobrepostos, chapando a marca por cima do corpo.
O custo é que a técnica só funciona sobre fundo branco: documento impresso em papel colorido ou com
fundo próprio precisaria de transparência de verdade.

A interface do módulo tipa objetos do reportlab — `Flowable`, `Drawing`, `Canvas` e `Color` —, com
`arbitrary_types_allowed` nos models que os carregam. `services/utils/pdf/` é uma casca fina sobre a
biblioteca, e uma representação neutra intermediária só duplicaria o vocabulário dela. O custo é que
trocar de biblioteca reescreve o módulo inteiro — contido por ele ser a única costura do projeto com o
reportlab, sempre importado pelo `__init__.py`.

A marcação inteira é pintada na volta, com as páginas já montadas, e o fundo entra sob o corpo
esvaziando e recompondo o `_code` da página — atributo interno do canvas do reportlab. É o que torna
"Página X de Y" e "última página" resolvíveis, inclusive para o fundo, e o que evita montar o documento
duas vezes (impossível: flowable consumido num build sai vazio no seguinte). O custo é duplo: o
documento inteiro reside em memória durante a montagem, irrelevante para poucas páginas e não para um
relatório de centenas; e a dependência de um detalhe não-público da biblioteca, que uma atualização
pode mudar sem aviso — o teste da camada de fundo é o que avisaria.

A moldura do corpo reserva o **maior** de cada borda entre todas as marcações do documento, e não a da
principal. A moldura é fixada antes de existir página alguma, então precisa caber a marcação mais
alta — é o que permite capa com timbre grande e miolo com timbre compacto sem a paginação mudar. O
custo é folga em branco nas páginas de marcação mais baixa, que ninguém recupera.

A orientação é do documento inteiro, declarada pela marcação principal, e marcação divergente é
recusada na construção. O `pagesize` do `SimpleDocTemplate` vale para o documento todo, e misturar
orientações exigiria trocá-lo por `BaseDocTemplate` com um `PageTemplate` por orientação. O custo é
não haver anexo em paisagem dentro de um documento retrato até que uma SPEC pague esse preço.

O vetor de uma marca é escrito como Form XObject, com a posição assada dentro dele. É o que mantém
tempo e tamanho constantes no número de páginas, em vez de lineares. O custo é que uma marca que
queira pintar o mesmo desenho em posições diferentes conforme a página precisa de um form por posição
— ou de voltar a desenhar direto, abrindo mão do ganho.

A altura de cada marca é constante de classe, escrita à mão, e não medida do que ela pinta. Medir texto
antes de desenhar exigiria a fonte carregada no momento da declaração, o que amarraria a marca ao
canvas. O custo é que marca cujo conteúdo cresça além da altura declarada invade a faixa vizinha sem
que nada recuse — o teste de faixa pega o caso conhecido, não todos.

## 8 · Testes (TDD)
- `test_documento_sai_como_bytes_sem_tocar_o_disco` — o retorno começa com `%PDF` e nenhum arquivo é
  criado no diretório de trabalho durante a geração.
- `test_marcacao_deriva_margens_da_soma_das_marcas` — a margem superior é a soma das alturas das marcas
  de cima mais o respiro; acrescentar uma marca de borda aumenta a margem, e a de fundo não altera
  margem nenhuma.
- `test_cada_marca_recebe_a_faixa_dela_sem_sobrepor` — marcas na mesma posição recebem faixas
  empilhadas na ordem declarada, e nenhuma faixa invade a outra.
- `test_marca_de_fundo_fica_atras_do_corpo` — no content stream da página, o desenho da marca de fundo
  precede o texto do corpo.
- `test_esmaecer_nao_escurece_com_sobreposicao` — todo traço do desenho esmaecido sai acima do limiar
  de clareza, inclusive os que se sobrepõem, e nenhuma cor conserva o valor original.
- `test_marcacao_resolve_pela_especificidade` — página nomeada em `marcacoes_especificas` vence
  primeira e última; extremo vence a principal; num documento de uma página só, `primeira` vence
  `ultima`; sem override algum, a principal vale em todas.
- `test_documento_recusa_orientacoes_divergentes` — marcação de página em paisagem junto de principal
  em retrato levanta na construção, não na geração.
- `test_moldura_cabe_a_marcacao_mais_alta` — com primeira página de marcação mais alta que o miolo, a
  margem superior do corpo é a da primeira, e a paginação é a mesma de um documento sem override.
- `test_conteudo_longo_quebra_e_repete_a_marcacao` — conteúdo que ocupa três páginas gera três páginas,
  sem linha cortada, e o vetor da marcação aparece nas três, aferido pelos XObjects declarados em
  `/Resources` de cada página.
- `test_vetor_eh_escrito_uma_vez_so` — o mesmo documento com o dobro de páginas declara o mesmo número
  de Form XObjects, e o arquivo não dobra de tamanho.
- `test_numeracao_diz_o_total_real` — o mesmo documento sai com "Página 1 de 3" na primeira e
  "Página 3 de 3" na última.
