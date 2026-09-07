---
spec: documentos_oficiais/003
versao: v7
atualizado_em: 2026-09-07
testes_tdd: true
implementado: true
markers_obrigatorios: [artefato]
changelog:
  - v1: versão inicial
  - v2: marca d'água usa SVG já claro, clareado no lugar pelo comando `esmaecer_svg`
  - v3: tabela entra como bloco do documento, e a marcação da SF nasce como `MarcacaoDocumento`
  - v4: models viram submódulo, o tema vem do ambiente e as marcações concretas ganham pacote por
    papel timbrado
  - v5: implementado — services/domain/documento_oficial/ (models, estilos, escritores, marcas,
    marcacoes_concretas/fazenda_dimap, config, render, amostra), os dois comandos, o marker
    `artefato` + `--all` + `publicar_artefato`, a skill `documento-oficial` e os 10 testes do §8; o
    `RenderizarDocumentoOficial` ganhou um parâmetro `escritores` opcional (fora do snippet) para o
    teste de bloco sem escritor injetar um registro incompleto; `sec_fazenda_vertical.svg` esmaecido
  - v6: `publicar_artefato` também abre o artefato no visualizador padrão do SO ao gravar —
    conveniência de conferência local, não parte do produto do teste; a lógica de abertura mora
    em `tests/abrir_artefato.py`, submódulo à parte, não no corpo do `conftest.py`
  - v7: o cabeçalho vira UMA marca com o timbre à esquerda e a unidade à direita, o papel declara
    `margem_vertical_mm` para o rodapé não sair na aresta da folha, e a marca d'água é reesmaecida
    a 0,85 — a 0,93 ela não se via no papel
---

# SPEC documentos_oficiais/003 — Documento oficial como blocos e o papel timbrado da Fazenda

## 1 · User story
O administrador do cadastro gera um documento de amostra pelo terminal, no contexto de subir a emissão
de documentos oficiais, para conferir o timbre, a marca d'água e a numeração antes de qualquer ato
administrativo emitir documento de verdade.

## 2 · Condições de pronto
- [ ] Todo documento oficial é uma **sequência de blocos**, e o básico existe: **título, subtítulo em
      três níveis, parágrafo, parágrafo recuado, lista numerada, lista não numerada, tabela e
      imagem** — nenhum documento desenha por conta própria.
- [ ] Texto interpolado num bloco sai **como texto no papel**, e não como marcação do reportlab —
      inclusive dentro de célula de tabela, escapado **uma vez só**.
- [ ] O visual do documento — cor, fonte, corpo de cada nível, entrelinha e regras de tabela — é um
      **tema só, alimentado pelo ambiente**, com padrão preto sobre branco: nenhum bloco, escritor ou
      marca escreve cor ou medida.
- [ ] A tabela é declarada em **colunas e linhas de texto**, e a coluna só vira medida na página.
- [ ] O papel timbrado da Secretaria da Fazenda traz, em **toda página**, timbre, cabeçalho da unidade,
      marca d'água, numeração e rodapé de endereço — o corpo é lido por cima da marca d'água, **que se
      vê no papel**, sem perda de contraste.
- [ ] No cabeçalho, o timbre fica **à esquerda e a unidade à sua direita**, na mesma faixa: empilhados,
      os dois somariam altura e o cabeçalho comeria a página.
- [ ] **Nada do papel timbrado encosta na aresta da folha** — o rodapé de endereço e a numeração caem
      dentro da margem, ou a impressora os corta.
- [ ] A marcação nasce com **unidade, endereço e logotipos padrão**, e cada um é substituível na
      construção — sem edição de código e sem que o domínio leia configuração.
- [ ] `uv run python manage.py esmaecer_svg <caminho> --forca 0.85` clareia um SVG no lugar, **uma vez,
      à mão**: o arquivo claro é comitado, e a emissão do documento carrega o SVG como está.
- [ ] `uv run python manage.py gerar_documento_amostra <caminho>` grava um PDF de amostra com todos os
      tipos de bloco e mais de uma página, e a **tabela dela atravessa a quebra** — é onde se confere o
      cabeçalho repetido na continuação e a célula longa quebrando dentro da própria célula.
- [ ] Teste que produz arquivo para conferência humana roda atrás do marker **`artefato`**, grava fora
      do repositório e **imprime o caminho**; `uv run pytest --all` roda a suíte inteira.
- [ ] Existe a skill **`documento-oficial`**, e ela basta para escrever um documento novo sem ler o
      código do gerador: o vocabulário de blocos, a composição da marcação e a conferência da amostra.

## 3 · Domínio

`services/domain/documento_oficial/` é o domínio do documento oficial do sistema, e guarda quatro
coisas: **o que um documento diz**, **como isso vira página**, **qual papel timbrado ele usa** e os
**casos de uso** que produzem conteúdo — um por documento que o sistema emite. Hoje há um só, o de
amostra; a certidão de lançamento entra ao lado dele.

O corpo é uma **sequência de blocos**, e é o tipo do bloco — não um campo de configuração — que decide
como ele se escreve. Documento novo é arranjo de blocos existentes; bloco novo é subtipo novo aqui, com
o seu escritor no §6.

O bloco de tabela é o caso em que isso fica visível: ele declara **colunas e linhas de texto**, e nada
mais. Como a coluna vira medida, como a tabela quebra entre páginas e como o cabeçalho se repete é da
SPEC [documentos_oficiais/002](002-motor-de-tabela.md) — esta pergunta a ela apenas **que tabela montar
e com que estilo**.

O que se repete em toda página **não é conteúdo**: é a **marcação**. A SPEC
[documentos_oficiais/001](001-motor-de-pdf.md) entrega o vocabulário dela — `Marca`, `Marcacao`,
`MarcacaoDocumento`, `Folha` e `Faixa` —, e esta pergunta a ele **quais marcas compõem o papel timbrado
da Fazenda** e o que cada uma precisa saber para pintar.

Os models são um **pacote de cinco vocabulários** — os blocos, o conteúdo e seus valores padrão, o
papel timbrado, o tema e as operações —, reexportados pelo `__init__.py`.

**`services/domain/documento_oficial/models/blocos.py`**
```python
class BlocoDocumento(BaseModel):
    """Base dos blocos: o que todos compartilham é a posição no corpo, não atributo."""

    model_config = ConfigDict(frozen=True)


class BlocoTextual(BlocoDocumento):
    """A exceção: título, subtítulo e parágrafo são UMA linha de texto, e o que os separa é só qual
    estilo do tema os escreve. É esta base que o escritor genérico do §6 recebe."""

    texto: str


class Titulo(BlocoTextual):
    tipo: Literal["titulo"] = "titulo"


class Subtitulo(BlocoTextual):
    tipo: Literal["subtitulo"] = "subtitulo"
    # Nível é escala do mesmo bloco, não bloco próprio: o que muda é o corpo da fonte. Três níveis
    # bastam para a hierarquia de um ato administrativo, e o `Literal` recusa o quarto.
    nivel: Literal[1, 2, 3] = 1


class Paragrafo(BlocoTextual):
    tipo: Literal["paragrafo"] = "paragrafo"
    # Recuo é variação do mesmo bloco, não bloco próprio: o que muda é a margem, não a natureza do
    # que se lê. Transcrição e citação em documento oficial saem assim.
    recuado: bool = False


class Lista(BlocoDocumento):
    """Um bloco por lista, não por item: a numeração é a posição do item, e nada precisa contar."""

    tipo: Literal["lista"] = "lista"
    ordenada: bool = False
    itens: tuple[str, ...] = Field(min_length=1)


class Tabela(BlocoDocumento):
    """A coluna é declarada como TIPO — fixa em milímetros ou fluida por peso — e só vira medida na
    página. `ColunaFixa` e `ColunaFluida` são o vocabulário da SPEC 002."""

    tipo: Literal["tabela"] = "tabela"
    colunas: tuple[Coluna, ...] = Field(min_length=1)
    linhas: tuple[tuple[str, ...], ...] = Field(min_length=1)
    # `None` é a tabela sem cabeçalho, não um cabeçalho vazio: presença é dado, não bandeira.
    cabecalho: tuple[str, ...] | None = None


class Imagem(BlocoDocumento):
    tipo: Literal["imagem"] = "imagem"
    # Caminho já resolvido: o domínio não sabe onde ficam os estáticos do projeto.
    caminho: Path
    # Sem default: quanto a imagem ocupa é decisão do documento, não do tema.
    largura_mm: float


Bloco = Annotated[
    Titulo | Subtitulo | Paragrafo | Lista | Tabela | Imagem,
    Field(discriminator="tipo"),
]
```

**`services/domain/documento_oficial/models/conteudo.py`**
```python
class ConteudoDocumento(BaseModel):
    """O que o documento diz e como ele se identifica. Sem cabeçalho nem rodapé: aquilo é da
    marcação, não do conteúdo."""

    model_config = ConfigDict(frozen=True)

    # Vai para os metadados do PDF, e é o que o leitor mostra na barra de título.
    titulo: str
    # O nome com que o documento se salva ou se baixa. Quem monta o documento sabe qual é; a
    # orquestração só o repassa ao `Content-Disposition` ou ao arquivo.
    nome_arquivo: str
    blocos: tuple[Bloco, ...] = Field(min_length=1)


# Os valores institucionais são conhecimento de domínio, e o default mora AQUI — uma vez só. O
# ambiente sobrepõe pelo builder do §6; calado o ambiente, é isto que sai no papel.
UNIDADE_PADRAO = (
    "Secretaria da Fazenda",
    "Subsecretaria da Receita Municipal",
    "Departamento de Cadastro",
    "Divisão do Mapa de Valores",
)
ENDERECO_PADRAO = ("Rua Líbero Badaró, 190 - Centro, São Paulo - SP (CEP 01008-000)",)
```

**`services/domain/documento_oficial/models/marcacao.py`**
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
    margem_lateral_mm: float = 25.0
    # A borda que nem as marcas ocupam: sem ela o rodapé sai na aresta da folha e não imprime.
    margem_vertical_mm: float = 15.0
    respiro_mm: float = 8.0
```

**`services/domain/documento_oficial/models/tema.py`** — o design system do documento como dado: o que
entra pelo ambiente (`TemaConfig`) e o que os escritores consomem (`Tema`). Todo default mora aqui,
uma vez só.
```python
COR_HEX = r"^#[0-9A-Fa-f]{6}$"


class PaletaDocumento(BaseModel):
    """Documento oficial é preto sobre branco — o padrão abaixo é a norma do papel, e o ambiente
    existe para papel de exceção, não para colorir o ato. Hex, e não `Color` do reportlab: a
    paleta vem do ambiente, e converter é do montador do §6."""

    model_config = ConfigDict(frozen=True)

    tinta: str = Field(default="#000000", pattern=COR_HEX)
    tinta_secundaria: str = Field(default="#555555", pattern=COR_HEX)
    traco_tabela: str = Field(default="#999999", pattern=COR_HEX)
    fundo_cabecalho_tabela: str = Field(default="#E8E8E8", pattern=COR_HEX)


class TipografiaDocumento(BaseModel):
    """Um corpo por papel que o texto exerce no documento. Fonte serifada por norma do papel."""

    model_config = ConfigDict(frozen=True)

    fonte: str = "Times-Roman"
    fonte_negrito: str = "Times-Bold"
    corpo_titulo_pt: float = 14.0
    # Um corpo por nível de subtítulo, na ordem I, II, III: o nível do bloco indexa esta tupla.
    corpo_subtitulo_pt: tuple[float, float, float] = (12.0, 11.0, 10.0)
    corpo_paragrafo_pt: float = 11.0
    corpo_paragrafo_recuado_pt: float = 10.0
    corpo_celula_pt: float = 9.0
    corpo_cabecalho_marca_pt: float = 9.0
    corpo_rodape_marca_pt: float = 8.0
    # A entrelinha é FATOR do corpo, não medida por estilo: mudar o corpo sem mudar a entrelinha
    # junto é o que aperta o texto sem que nada recuse.
    fator_entrelinha: float = 1.45
    # A entrelinha das marcas é em milímetros porque a marca pinta em milímetros, não em fluxo.
    entrelinha_marca_mm: float = 4.2
    respiro_celula_mm: tuple[float, float] = (2.0, 1.4)
    espessura_traco_tabela_pt: float = 0.4


class TemaConfig(BaseModel):
    """O tema como o ambiente o declara."""

    model_config = ConfigDict(frozen=True)

    paleta: PaletaDocumento = PaletaDocumento()
    tipografia: TipografiaDocumento = TipografiaDocumento()


class Tema(BaseModel):
    """O tema já montado: é isto que escritores e marcas recebem, e o único lugar de onde tiram
    cor, fonte e medida."""

    # Carrega `ParagraphStyle`, `EstiloTexto` e `EstiloTabela` — ver Caveats.
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    estilos: dict[str, ParagraphStyle]
    estilo_tabela: EstiloTabela
    estilo_cabecalho_marca: EstiloTexto
    estilo_rodape_marca: EstiloTexto
    entrelinha_marca_mm: float
```

**`services/domain/documento_oficial/models/operacoes.py`** — os DTOs das duas pontas.
```python
class DocumentoAmostraInput(BaseModel):
    """O pedido da amostra. Sem caminho de saída: gravar é do comando, gerar é do domínio."""

    model_config = ConfigDict(frozen=True)

    # De onde a amostra partiu, para quem confere saber qual ambiente foi provado.
    ambiente: str
    momento: datetime


class RenderizarDocumentoInput(BaseModel):
    """O que o documento diz, e sobre que papel."""

    # `MarcacaoDocumento` é classe do motor, sem schema Pydantic — ver Caveats.
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    conteudo: ConteudoDocumento
    marcacao: MarcacaoDocumento


class DocumentoRenderizado(BaseModel):
    """O PDF pronto, com o nome que o conteúdo pediu: é o que a rota devolve e o que o comando
    grava. Bytes, nunca caminho — persistir é de quem chama."""

    model_config = ConfigDict(frozen=True)

    pdf: bytes
    nome_arquivo: str
```

**`services/domain/documento_oficial/models/__init__.py`** — só reexporta (CLAUDE.md §7.2).
```python
from .blocos import (
    Bloco,
    BlocoDocumento,
    BlocoTextual,
    Imagem,
    Lista,
    Paragrafo,
    Subtitulo,
    Tabela,
    Titulo,
)
from .conteudo import ENDERECO_PADRAO, UNIDADE_PADRAO, ConteudoDocumento
from .marcacao import MarcacaoConfig
from .operacoes import DocumentoAmostraInput, DocumentoRenderizado, RenderizarDocumentoInput
from .tema import PaletaDocumento, Tema, TemaConfig, TipografiaDocumento
```

## 4 · Fora de escopo
- A certidão de lançamento, sua rota protegida e o registro da execução — épico `documentos_oficiais`,
  SPEC própria.
- Armazenagem do documento emitido (quem emitiu, sobre o quê, quando) — SPEC da certidão.
- Sandbox de aprovação (gerar em temporário, o servidor revisar, só então salvar) e o gerenciador de
  temporários que ele exige — SPEC própria, depois desta.
- Assinatura digital, código de verificação e QR de autenticidade — sem dono ainda.
- Imagem rasterizada (PNG, JPG) como bloco — o motor carrega vetor; entra quando houver documento que
  precise, e cobra da SPEC 001 um carregador de raster.
- Célula de tabela com imagem, lista ou tabela aninhada — a célula é texto; recorte da SPEC
  [documentos_oficiais/002](002-motor-de-tabela.md), sem dono ainda.
- Papel timbrado de outra secretaria — o pacote `marcacoes_concretas/` nasce com um submódulo e
  recebe os próximos sem tocar no resto; sem dono ainda.

## 5 · Peças de referência a compor
- `@services/utils/pdf` → `Marca`, `Marcacao`, `MarcacaoDocumento`, `EstiloTexto`, `gerar_pdf` e
  `carregar_vetor`: o motor entregue pela SPEC 001.
- `@services/utils/pdf/tabela` → `TabelaInput`, `tabela_pdf`, `EstiloTabela` e as regras visuais
  (`FundoDoCabecalho`, `GradeDeLinhas`, `Respiro`, `ZebraDoCorpo`): o motor de tabela da SPEC 002.
- `@services/utils/pdf/utils` → `esmaecer_svg` e `EsmaecerSvgInput`: preparação de ativo, fora do
  caminho de emissão — não é reexportado pelo `__init__.py` do motor.
- `@services/domain/email` → o padrão de bloco, registro de escritores e tema próprio.
- `@services/utils/io` → `escrever_atomico`: a gravação do arquivo pelo comando de amostra.
- `@services/utils/smtp/config.py` → `SmtpSettingsLike` e `build_smtp_config`: o padrão de Protocol +
  builder que leva `settings` ao domínio.
- `@static/src/img/documento_oficial/sec_fazenda_horizontal.svg` → o logotipo do cabeçalho, vetorial,
  237,84 × 75,58 pt.
- `@static/src/img/documento_oficial/sec_fazenda_vertical.svg` → o logotipo da marca d'água, vetorial,
  168,16 × 144,41 pt. Nasce saturado: o `esmaecer_svg` roda **uma vez sobre ele**, com `--forca 0.85`,
  e o arquivo claro é o que se comita. Reclarear pede o original de volta — ver Caveats.
- Skills: `ontologia`, `escrever-testes`, `management-commands`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`services/domain/documento_oficial/estilos.py`** — a fábrica do tema: `TemaConfig` (valores) vira
`Tema` (estilos prontos). É a única peça que converte hex em `Color` e corpo em entrelinha.
```python
class MontarTema:
    """Callable: os valores declarados viram os estilos que escritores e marcas usam."""

    def __call__(self, config: TemaConfig) -> Tema:
        return self.pipeline(config)

    def pipeline(self, config: TemaConfig) -> Tema:
        tinta = colors.HexColor(config.paleta.tinta)
        estilos = self._estilos(config, tinta)
        return Tema(
            estilos=estilos,
            estilo_tabela=self._tabela(config, estilos),
            estilo_cabecalho_marca=EstiloTexto(
                fonte=config.tipografia.fonte,
                corpo_pt=config.tipografia.corpo_cabecalho_marca_pt,
                cor=tinta,
            ),
            estilo_rodape_marca=EstiloTexto(
                fonte=config.tipografia.fonte,
                corpo_pt=config.tipografia.corpo_rodape_marca_pt,
                cor=colors.HexColor(config.paleta.tinta_secundaria),
            ),
            entrelinha_marca_mm=config.tipografia.entrelinha_marca_mm,
        )

    def _estilos(self, config: TemaConfig, tinta: Color) -> dict[str, ParagraphStyle]:
        tipo = config.tipografia
        estilos = {
            "titulo": self._estilo(
                "titulo",
                config,
                tinta,
                tipo.corpo_titulo_pt,
                tipo.fonte_negrito,
                alignment=TA_CENTER,
                spaceAfter=12,
            ),
            # O espaço entre parágrafos é do ESTILO, não de um Spacer entre blocos: assim o
            # escritor devolve um flowable só, e a quebra de página nunca deixa espaçador órfão.
            "paragrafo": self._estilo(
                "paragrafo",
                config,
                tinta,
                tipo.corpo_paragrafo_pt,
                tipo.fonte,
                alignment=TA_JUSTIFY,
                firstLineIndent=12,
                spaceAfter=8,
            ),
            "paragrafo_recuado": self._estilo(
                "paragrafo_recuado",
                config,
                tinta,
                tipo.corpo_paragrafo_recuado_pt,
                tipo.fonte,
                alignment=TA_JUSTIFY,
                leftIndent=28,
                rightIndent=14,
                spaceAfter=8,
            ),
            "item": self._estilo("item", config, tinta, tipo.corpo_paragrafo_pt, tipo.fonte),
            "celula": self._estilo("celula", config, tinta, tipo.corpo_celula_pt, tipo.fonte),
            "cabecalho_tabela": self._estilo(
                "cabecalho_tabela", config, tinta, tipo.corpo_celula_pt, tipo.fonte_negrito
            ),
        }
        # Um estilo por nível, nomeado pelo número: é a chave que o escritor de subtítulo monta a
        # partir do bloco, e é o que faz acrescentar nível ser acrescentar corpo na tupla.
        for nivel, corpo_pt in enumerate(tipo.corpo_subtitulo_pt, start=1):
            estilos[f"subtitulo_{nivel}"] = self._estilo(
                f"subtitulo_{nivel}", config, tinta, corpo_pt, tipo.fonte_negrito, spaceAfter=6
            )
        return estilos

    def _estilo(
        self,
        nome: str,
        config: TemaConfig,
        cor: Color,
        corpo_pt: float,
        fonte: str,
        **extras: object,
    ) -> ParagraphStyle:
        # A entrelinha SEMPRE sai do fator: nenhum estilo do documento a declara solta, e é isso
        # que impede um corpo trocado no ambiente sair com o texto apertado.
        return ParagraphStyle(
            nome,
            fontName=fonte,
            fontSize=corpo_pt,
            leading=corpo_pt * config.tipografia.fator_entrelinha,
            textColor=cor,
            **extras,
        )

    def _tabela(self, config: TemaConfig, estilos: dict[str, ParagraphStyle]) -> EstiloTabela:
        horizontal_mm, vertical_mm = config.tipografia.respiro_celula_mm
        # Sem `ZebraDoCorpo`: fundo de linha é opaco e apagaria a marca d'água — ver Caveats.
        return EstiloTabela(
            celula=estilos["celula"],
            cabecalho=estilos["cabecalho_tabela"],
            regras=(
                FundoDoCabecalho(colors.HexColor(config.paleta.fundo_cabecalho_tabela)),
                GradeDeLinhas(
                    colors.HexColor(config.paleta.traco_tabela),
                    config.tipografia.espessura_traco_tabela_pt,
                ),
                Respiro(horizontal_mm=horizontal_mm, vertical_mm=vertical_mm),
            ),
        )


montar_tema = MontarTema()
```

**`services/domain/documento_oficial/escritores.py`** — um escritor por bloco, cada um a única linha
do projeto que sabe **como aquele bloco vira flowable**. Título, subtítulo e parágrafo são o mesmo
gesto — texto num estilo —, então herdam de um genérico e declaram só qual estilo (ver Caveats).
```python
class EscritorTexto[B: BlocoTextual](ABC):
    """Base dos blocos de uma linha de texto. A herança define interface e nada mais: o que varia
    é o estilo, e `__call__` é o mesmo para os três."""

    def __init__(self, tema: Tema) -> None:
        self._tema = tema

    def __call__(self, bloco: B) -> Flowable:
        # `Paragraph` interpreta marcação própria do reportlab: o escape é daqui, como no e-mail.
        return Paragraph(_texto(bloco.texto), self._estilo(bloco))

    @abstractmethod
    def _estilo(self, bloco: B) -> ParagraphStyle: ...


class EscritorTitulo(EscritorTexto[Titulo]):
    def _estilo(self, bloco: Titulo) -> ParagraphStyle:
        return self._tema.estilos["titulo"]


class EscritorSubtitulo(EscritorTexto[Subtitulo]):
    def _estilo(self, bloco: Subtitulo) -> ParagraphStyle:
        return self._tema.estilos[f"subtitulo_{bloco.nivel}"]


class EscritorParagrafo(EscritorTexto[Paragrafo]):
    def _estilo(self, bloco: Paragrafo) -> ParagraphStyle:
        return self._tema.estilos["paragrafo_recuado" if bloco.recuado else "paragrafo"]


class EscritorLista:
    def __init__(self, tema: Tema) -> None:
        self._tema = tema

    def __call__(self, bloco: Lista) -> Flowable:
        return self.pipeline(bloco)

    def pipeline(self, bloco: Lista) -> Flowable:
        # `bulletType="1"` numera pela POSIÇÃO na lista: o número não é dado do bloco, e duas
        # listas seguidas recomeçam do 1 sem ninguém zerar contador.
        return ListFlowable(
            [ListItem(self._item(texto)) for texto in bloco.itens],
            bulletType="1" if bloco.ordenada else "bullet",
            bulletFontName=self._tema.estilos["item"].fontName,
            leftIndent=24,
        )

    def _item(self, texto: str) -> Flowable:
        return Paragraph(_texto(texto), self._tema.estilos["item"])


class EscritorTabela:
    """O bloco diz o que a tabela contém; o estilo é do tema, e a medida é do motor da SPEC 002."""

    def __init__(self, tema: Tema) -> None:
        self._tema = tema

    def __call__(self, bloco: Tabela) -> Flowable:
        return self.pipeline(bloco)

    def pipeline(self, bloco: Tabela) -> Flowable:
        return tabela_pdf(self._pedido(bloco))

    def _pedido(self, bloco: Tabela) -> TabelaInput:
        # Texto CRU, sem `_texto`: o `TabelaPdf` escapa cada célula ao montar o `Paragraph`.
        # Escapar aqui também sairia `&amp;` no papel.
        return TabelaInput(
            colunas=bloco.colunas,
            cabecalho=bloco.cabecalho,
            linhas=bloco.linhas,
            estilo=self._tema.estilo_tabela,
        )


class EscritorImagem:
    """SVG, não raster: o vetor é o que o motor carrega (SPEC 001), e é o que mantém o arquivo leve
    quando a mesma imagem se repete."""

    def __init__(self, tema: Tema) -> None:
        self._tema = tema

    def __call__(self, bloco: Imagem) -> Flowable:
        return self.pipeline(bloco)

    def pipeline(self, bloco: Imagem) -> Flowable:
        # `Drawing` já É um `Flowable`: o vetor entra no fluxo do corpo sem embrulho nenhum.
        desenho = carregar_vetor(bloco.caminho, bloco.largura_mm)
        desenho.hAlign = "CENTER"
        return desenho


def montar_escritores(tema: Tema) -> dict[str, Callable[[Any], Flowable]]:
    # O registro é a única lista de tipos do módulo: bloco novo entra aqui e em lugar nenhum mais.
    return {
        "titulo": EscritorTitulo(tema),
        "subtitulo": EscritorSubtitulo(tema),
        "paragrafo": EscritorParagrafo(tema),
        "lista": EscritorLista(tema),
        "tabela": EscritorTabela(tema),
        "imagem": EscritorImagem(tema),
    }
```

**`services/domain/documento_oficial/marcas.py`** — as marcas, genéricas por construção: nenhuma sabe
de qual secretaria é o papel, e todas recebem o que pintam. Cada uma pinta na faixa que recebeu e não
sabe o tamanho da página — é isto que deixa a `Marcacao` reordená-las sem que nenhuma se quebre.
```python
class TimbreHorizontal(Marca):
    """O logotipo da Secretaria, no alto de toda página."""

    posicao = Posicao.SUPERIOR

    def __init__(self, caminho_svg: Path, largura_mm: float) -> None:
        # O Drawing é carregado UMA vez e reusado em toda página: o SVG tem centenas de traços, e
        # reabri-lo por página seria o custo desta marca multiplicado pelo tamanho do documento.
        self._desenho = carregar_vetor(caminho_svg, largura_mm)
        # Medidas MEDIDAS do que a marca pinta, não constantes escritas à mão: mudar a largura do
        # timbre não pode deixar a moldura do corpo desatualizada (Caveats da SPEC 001), nem o
        # cabeçalho escrevendo a unidade por cima do logotipo.
        self.altura_mm = self._desenho.height / mm
        self.largura_mm = self._desenho.width / mm

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        folha.vetor(faixa.esquerda_mm, faixa.topo_mm, self._desenho, nome="timbre")


class LinhasDeTexto(Marca):
    """Base das marcas que são linhas empilhadas — o cabeçalho da unidade e o rodapé de endereço.
    Recebe as linhas prontas: nenhum texto institucional é literal numa marca."""

    def __init__(self, linhas: tuple[str, ...], estilo: EstiloTexto, entrelinha_mm: float) -> None:
        self._linhas = linhas
        self._estilo = estilo
        self._entrelinha_mm = entrelinha_mm
        # As linhas vêm da config e podem ser mais que o padrão: com altura constante de classe,
        # uma unidade de seis níveis invadiria a faixa vizinha sem que nada recusasse.
        self.altura_mm = len(linhas) * entrelinha_mm

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        for numero, linha in enumerate(self._linhas, start=1):
            folha.texto(
                faixa.esquerda_mm,
                faixa.topo_mm + numero * self._entrelinha_mm,
                linha,
                self._estilo,
            )


class CabecalhoUnidade(LinhasDeTexto):
    """A unidade da DIMAP, um nível por linha. O logotipo já traz 'PREFEITURA DE SÃO PAULO /
    SECRETARIA DA FAZENDA', então esta marca nomeia só a unidade — nada é dito duas vezes."""

    posicao = Posicao.SUPERIOR


class RodapeEndereco(LinhasDeTexto):
    posicao = Posicao.INFERIOR


class CabecalhoTimbrado(Marca):
    """Timbre à esquerda, unidade à direita, na MESMA faixa. Empilhadas na tupla da marcação, as
    duas somariam altura e o cabeçalho comeria a página; lado a lado, a faixa é a do mais alto.

    Marca composta, e não uma marca que desenha as duas coisas: o timbre e a unidade continuam
    existindo sozinhos, e outro papel timbrado pode arranjá-los de outro jeito.
    """

    posicao = Posicao.SUPERIOR

    def __init__(
        self,
        timbre: TimbreHorizontal,
        unidade: CabecalhoUnidade,
        respiro_mm: float,
    ) -> None:
        self._timbre = timbre
        self._unidade = unidade
        self._recuo_unidade_mm = timbre.largura_mm + respiro_mm
        self.altura_mm = max(timbre.altura_mm, unidade.altura_mm)

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        self._timbre(faixa, folha)
        self._unidade(self._faixa_da_unidade(faixa), folha)

    def _faixa_da_unidade(self, faixa: Faixa) -> Faixa:
        # A faixa recebida, encurtada pela esquerda: a unidade herda dela a margem direita, e nunca
        # calcula posição na página — mesma regra das marcas simples.
        return faixa.model_copy(
            update={
                "esquerda_mm": faixa.esquerda_mm + self._recuo_unidade_mm,
                "largura_mm": faixa.largura_mm - self._recuo_unidade_mm,
            }
        )


class MarcaDagua(Marca):
    """O logotipo vertical no meio do papel. Reserva ZERO: o corpo passa por cima.

    O SVG que chega aqui já é o claro — clarear é preparação de ativo, feita uma vez à mão pelo
    comando do §6 e comitada, e não trabalho repetido a cada emissão.
    """

    posicao = Posicao.FUNDO
    altura_mm = 0.0

    def __init__(self, caminho_svg: Path, largura_mm: float) -> None:
        self._desenho = carregar_vetor(caminho_svg, largura_mm)

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        # Centralizada na FOLHA, e não na faixa: a marca de fundo ignora a moldura das outras.
        folha.vetor(
            (folha.tamanho.largura_mm - self._desenho.width / mm) / 2,
            (folha.tamanho.altura_mm - self._desenho.height / mm) / 2,
            self._desenho,
            nome="marca_dagua",
        )


class NumeracaoPaginas(Marca):
    """'Página X de Y'. O total vem da folha, que já o conhece."""

    posicao = Posicao.INFERIOR

    def __init__(self, estilo: EstiloTexto, entrelinha_mm: float) -> None:
        self._estilo = estilo
        self.altura_mm = entrelinha_mm

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        folha.texto(
            faixa.esquerda_mm,
            faixa.topo_mm,
            f"Página {folha.pagina} de {folha.total}",
            self._estilo,
        )
```

**`services/domain/documento_oficial/marcacoes_concretas/fazenda_dimap.py`** — um papel timbrado por
módulo. O pacote nasce com este e recebe os próximos sem que nada aqui mude: o `__init__.py` reexporta,
e quem escolhe o papel é a orquestração.
```python
def marcacao_fazenda_dimap(config: MarcacaoConfig, tema: Tema) -> MarcacaoDocumento:
    """A composição das marcas na ordem em que se empilham. Trocar de papel timbrado é escrever
    outro módulo ao lado deste; trocar de unidade é trocar a config."""
    # Só a principal: o papel da SF é o mesmo em toda página. Primeira, última e página nomeada
    # existem no motor (SPEC 001) e entram quando um documento pedir capa própria.
    return MarcacaoDocumento(
        principal=Marcacao(
            marcas=(
                CabecalhoTimbrado(
                    TimbreHorizontal(config.logo_horizontal, config.largura_timbre_mm),
                    CabecalhoUnidade(
                        config.unidade,
                        tema.estilo_cabecalho_marca,
                        tema.entrelinha_marca_mm,
                    ),
                    config.respiro_mm,
                ),
                MarcaDagua(config.logo_vertical, config.largura_marca_dagua_mm),
                RodapeEndereco(
                    config.endereco,
                    tema.estilo_rodape_marca,
                    tema.entrelinha_marca_mm,
                ),
                NumeracaoPaginas(tema.estilo_rodape_marca, tema.entrelinha_marca_mm),
            ),
            margem_lateral_mm=config.margem_lateral_mm,
            margem_vertical_mm=config.margem_vertical_mm,
            respiro_mm=config.respiro_mm,
        )
    )
```

**`services/domain/documento_oficial/marcacoes_concretas/__init__.py`** — só reexporta (CLAUDE.md
§7.2). É esta linha que cresce quando entra outro papel timbrado, e nada mais.
```python
from .fazenda_dimap import marcacao_fazenda_dimap

__all__ = ["marcacao_fazenda_dimap"]
```

**`services/domain/documento_oficial/config.py`** — a costura entre `settings` e o domínio, no padrão
do `services/utils/smtp/config.py`: o domínio declara o que precisa e nunca importa o Django.
```python
class DocumentoSettingsLike(Protocol):
    DOCUMENTO_LOGO_HORIZONTAL: Path
    DOCUMENTO_LOGO_VERTICAL: Path
    DOCUMENTO_UNIDADE: tuple[str, ...] | None
    DOCUMENTO_ENDERECO: tuple[str, ...] | None
    DOCUMENTO_COR_TINTA: str | None
    DOCUMENTO_COR_TINTA_SECUNDARIA: str | None
    DOCUMENTO_COR_TRACO_TABELA: str | None
    DOCUMENTO_COR_FUNDO_CABECALHO_TABELA: str | None
    DOCUMENTO_FONTE: str | None
    DOCUMENTO_FONTE_NEGRITO: str | None
    DOCUMENTO_CORPO_TITULO_PT: float | None
    DOCUMENTO_CORPO_SUBTITULO_PT: tuple[float, float, float] | None
    DOCUMENTO_CORPO_PARAGRAFO_PT: float | None
    DOCUMENTO_CORPO_PARAGRAFO_RECUADO_PT: float | None
    DOCUMENTO_CORPO_CELULA_PT: float | None
    DOCUMENTO_CORPO_CABECALHO_MARCA_PT: float | None
    DOCUMENTO_CORPO_RODAPE_MARCA_PT: float | None
    DOCUMENTO_FATOR_ENTRELINHA: float | None
    DOCUMENTO_ENTRELINHA_MARCA_MM: float | None


def _definidos[M: BaseModel](modelo: type[M], valores: Mapping[str, object]) -> M:
    # Só o que o ambiente DEFINIU é repassado: campo ausente deixa o default do model valer.
    # Passar `None` adiante sobrescreveria o padrão com vazio e obrigaria cada valor a existir
    # aqui também — duas cópias livres para divergir.
    return modelo(**{chave: valor for chave, valor in valores.items() if valor is not None})


def build_marcacao_config(source: DocumentoSettingsLike) -> MarcacaoConfig:
    return MarcacaoConfig(
        logo_horizontal=source.DOCUMENTO_LOGO_HORIZONTAL,
        logo_vertical=source.DOCUMENTO_LOGO_VERTICAL,
        **{
            chave: valor
            for chave, valor in (
                ("unidade", source.DOCUMENTO_UNIDADE),
                ("endereco", source.DOCUMENTO_ENDERECO),
            )
            if valor is not None
        },
    )


def build_tema_config(source: DocumentoSettingsLike) -> TemaConfig:
    return TemaConfig(
        paleta=_definidos(
            PaletaDocumento,
            {
                "tinta": source.DOCUMENTO_COR_TINTA,
                "tinta_secundaria": source.DOCUMENTO_COR_TINTA_SECUNDARIA,
                "traco_tabela": source.DOCUMENTO_COR_TRACO_TABELA,
                "fundo_cabecalho_tabela": source.DOCUMENTO_COR_FUNDO_CABECALHO_TABELA,
            },
        ),
        tipografia=_definidos(
            TipografiaDocumento,
            {
                "fonte": source.DOCUMENTO_FONTE,
                "corpo_titulo_pt": source.DOCUMENTO_CORPO_TITULO_PT,
                "corpo_subtitulo_pt": source.DOCUMENTO_CORPO_SUBTITULO_PT,
                # ... os demais corpos, o fator de entrelinha e a entrelinha das marcas
            },
        ),
    )
```

**`config/settings.py`** — os campos no `_Settings`, no mesmo padrão do `MAP_FUNDO_PONTOS`: default no
código, ambiente sobrepondo. É a única camada que conhece a raiz do projeto.
```python
class _Settings(BaseSettings):
    # ... os que já existem
    documento_logo_horizontal: Path | None = Field(default=None, alias="DOCUMENTO_LOGO_HORIZONTAL")
    documento_logo_vertical: Path | None = Field(default=None, alias="DOCUMENTO_LOGO_VERTICAL")
    documento_unidade: tuple[str, ...] | None = Field(default=None, alias="DOCUMENTO_UNIDADE")
    documento_endereco: tuple[str, ...] | None = Field(default=None, alias="DOCUMENTO_ENDERECO")
    documento_cor_tinta: str | None = Field(default=None, alias="DOCUMENTO_COR_TINTA")
    documento_fonte: str | None = Field(default=None, alias="DOCUMENTO_FONTE")
    documento_corpo_titulo_pt: float | None = Field(default=None, alias="DOCUMENTO_CORPO_TITULO_PT")
    documento_corpo_subtitulo_pt: tuple[float, float, float] | None = Field(
        default=None,
        alias="DOCUMENTO_CORPO_SUBTITULO_PT",
    )
    documento_fator_entrelinha: float | None = Field(
        default=None,
        alias="DOCUMENTO_FATOR_ENTRELINHA",
    )
    # ... as demais cores e corpos, na mesma forma

    @field_validator("documento_unidade", "documento_endereco", mode="before")
    @classmethod
    def _parse_linhas_institucionais(cls, v: Any) -> tuple[str, ...] | None:
        # `None` distingue "ambiente calado" de "lista vazia", e é ele que deixa o padrão do
        # domínio valer; o `_parse_lista_env` sozinho devolveria `[]` nos dois casos.
        return tuple(_parse_lista_env(v)) or None

    @field_validator("documento_corpo_subtitulo_pt", mode="before")
    @classmethod
    def _parse_corpos(cls, v: Any) -> tuple[float, ...] | None:
        return tuple(float(item) for item in _parse_lista_env(v)) or None


DOCUMENTO_LOGO_HORIZONTAL = _env.documento_logo_horizontal or (
    BASE_DIR / "static" / "src" / "img" / "documento_oficial" / "sec_fazenda_horizontal.svg"
)
DOCUMENTO_LOGO_VERTICAL = _env.documento_logo_vertical or (
    BASE_DIR / "static" / "src" / "img" / "documento_oficial" / "sec_fazenda_vertical.svg"
)
DOCUMENTO_UNIDADE = _env.documento_unidade
DOCUMENTO_ENDERECO = _env.documento_endereco
DOCUMENTO_COR_TINTA = _env.documento_cor_tinta
DOCUMENTO_FONTE = _env.documento_fonte
DOCUMENTO_CORPO_TITULO_PT = _env.documento_corpo_titulo_pt
DOCUMENTO_CORPO_SUBTITULO_PT = _env.documento_corpo_subtitulo_pt
DOCUMENTO_FATOR_ENTRELINHA = _env.documento_fator_entrelinha
# ... as demais, na mesma forma
```

**`services/domain/documento_oficial/render.py`** — blocos + marcação → o documento renderizado.
```python
class RenderizarDocumentoOficial:
    """Callable: o que o documento diz, sobre o papel que ele usa, vira PDF. O tema vem no
    construtor: é ele que decide como cada bloco se escreve, e não muda entre documentos."""

    def __init__(self, tema: Tema) -> None:
        self._escritores = montar_escritores(tema)

    def __call__(self, pedido: RenderizarDocumentoInput) -> DocumentoRenderizado:
        return self.pipeline(pedido)

    def pipeline(self, pedido: RenderizarDocumentoInput) -> DocumentoRenderizado:
        return DocumentoRenderizado(
            pdf=self._pdf(pedido),
            nome_arquivo=pedido.conteudo.nome_arquivo,
        )

    def _pdf(self, pedido: RenderizarDocumentoInput) -> bytes:
        return gerar_pdf(
            DocumentoPdfInput(
                titulo=pedido.conteudo.titulo,
                corpo=tuple(self._escrever(bloco) for bloco in pedido.conteudo.blocos),
                marcacao=pedido.marcacao,
            )
        )

    def _escrever(self, bloco: BlocoDocumento) -> Flowable:
        # Bloco sem escritor levanta KeyError na montagem — onde há teste e stack trace —, e não
        # como buraco silencioso num documento que alguém vai assinar.
        return self._escritores[bloco.tipo](bloco)
```

**`services/domain/documento_oficial/amostra.py`** — o corpo da amostra, e só ele. Cada documento do
sistema ganha um módulo assim ao lado deste.
```python
class MontarDocumentoAmostra:
    """Callable: o pedido vira o que o documento vai dizer. Todos os tipos de bloco aparecem, os
    três níveis de subtítulo também, e o texto é longo o bastante para virar a página — é o que
    prova a marcação repetida. A tabela leva linhas de enchimento e uma célula de texto longo pelo
    mesmo motivo: tabela curta não quebra, e o cabeçalho repetido fica sem prova."""

    def __call__(self, pedido: DocumentoAmostraInput) -> ConteudoDocumento: ...


montar_documento_amostra = MontarDocumentoAmostra()
```

**`apps/core/management/commands/esmaecer_svg.py`** — o comando é fino e roda **à mão**, sobre o próprio
arquivo: quem acrescenta uma marca d'água nova clareia o SVG uma vez, comita o arquivo claro e nunca
mais volta aqui. Ele não é chamado por nada da emissão.
```python
class Command(BaseCommand):
    help = "Clareia um SVG no lugar, para uso como marca d'água."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("caminho", type=Path)
        parser.add_argument("--forca", type=float, default=0.93)

    def handle(self, *args: object, **options: object) -> None:
        resultado = esmaecer_svg(
            EsmaecerSvgInput(caminho=options["caminho"], forca=options["forca"])
        )
        self.stdout.write(
            self.style.SUCCESS(f"{resultado.cores_clareadas} cores clareadas em {resultado.caminho}.")
        )
```

**`apps/core/management/commands/gerar_documento_amostra.py`** — o comando é fino: lê `settings`, monta
os DTOs, chama as peças e grava. Sem `--verbose` nem `--automatico`: essas são do contrato dos comandos
de carga (`ScriptRunner`, SPEC `ingestao_dados/006`), e este não é um deles.
```python
class Command(BaseCommand):
    help = "Grava um PDF de amostra com todos os blocos e a marcação oficial da SF."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("caminho", type=Path)

    def handle(self, *args: object, **options: object) -> None:
        conteudo = montar_documento_amostra(
            DocumentoAmostraInput(ambiente=settings.ALLOWED_HOSTS[0], momento=timezone.now())
        )
        # A orquestração é o único ponto que toca `settings`, e é ela que escolhe o papel
        # timbrado; o domínio recebe tema e config prontos.
        tema = montar_tema(build_tema_config(settings))
        marcacao = marcacao_fazenda_dimap(build_marcacao_config(settings), tema)
        renderizado = RenderizarDocumentoOficial(tema)(
            RenderizarDocumentoInput(conteudo=conteudo, marcacao=marcacao)
        )
        escrever_atomico(Path(options["caminho"]), renderizado.pdf)
        self.stdout.write(self.style.SUCCESS(f"Amostra gravada em {options['caminho']}."))
```

**`pyproject.toml`** — o marker novo, no mesmo regime dos que já existem, mais a retenção que impede o
acúmulo. `retention_count = 1` conta **sessões**: cada execução apaga a anterior inteira e preserva
todos os artefatos da atual, então PDF de um serviço e PNG de outro convivem.
```toml
[tool.pytest.ini_options]
addopts = "-m 'not integration and not banco and not artefato'"
tmp_path_retention_count = 1
tmp_path_retention_policy = "all"
markers = [
    # ... os que já existem
    "artefato: gera arquivo para conferência humana e imprime o caminho (rode com: pytest -m artefato)",
]
```

**`tests/abrir_artefato.py`** — submódulo à parte, e não corpo do `conftest.py`: é a única peça que
sabe abrir um arquivo no visualizador padrão do SO, e o `conftest.py` só a importa. Um comando por SO,
guardado como string literal no módulo; se o executável não existir ou o comando estourar o timeout,
vira **warning**, nunca falha do teste.
```python
COMANDO_ABRIR_ARTEFATO_POR_SO: dict[str, str] = {
    "Linux": "xdg-open {caminho}",
    "Darwin": "open {caminho}",
    "Windows": 'cmd /c start "" {caminho}',
}
# Alguns visualizadores só devolvem o controle do processo quando fecham; o timeout é o que
# impede a suíte de travar esperando alguém fechar o artefato na tela.
TIMEOUT_ABRIR_ARTEFATO_S = 2.0


def abrir_artefato(caminho: Path) -> None:
    """Tenta abrir o artefato no visualizador padrão do SO — best-effort, nunca condição do
    teste."""
```

**`tests/conftest.py`** — a fixture e a flag são **infraestrutura de suíte**, não desta SPEC: nascem
aqui porque este é o primeiro serviço que gera arquivo para olho humano, e servem o snapshot do mapa e
a exportação que vierem depois. O contrato completo está na skill `escrever-testes` (§3.6 e §4.2).
```python
@pytest.fixture
def publicar_artefato(tmp_path, capsys) -> Callable[[str, bytes], Path]:
    """Grava o artefato onde ele sobreviva à sessão, imprime onde ele está e chama
    `abrir_artefato`."""


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--all", action="store_true", help="Roda a suíte inteira, markers inclusive.")


def pytest_configure(config: pytest.Config) -> None:
    # O `-m` herdado do addopts é o que exclui as camadas pesadas; --all simplesmente o esvazia.
    if config.getoption("--all"):
        config.option.markexpr = ""
```

**`.claude/skills/documento-oficial/SKILL.md`** — entregável desta SPEC, não subproduto: o gerador é
infraestrutura que outras ações vão consumir, e sem a skill cada ação nova descobre o vocabulário
lendo `services/domain/documento_oficial/`. Cobre: os blocos existentes e o que cada um carrega, os
três níveis de subtítulo, e que bloco novo é subtipo + escritor no registro; a tabela — declarar
`ColunaFixa`/`ColunaFluida` e linhas de texto, e que o visual vem do tema, nunca do documento;
escrever um documento criando o módulo do caso de uso ao lado de `amostra.py`; montar o tema com
`montar_tema(build_tema_config(settings))` na orquestração e passá-lo ao renderizador; escolher o
papel timbrado em `marcacoes_concretas/` e que papel novo é módulo novo ali; compor a marcação com
`MarcacaoDocumento` (principal obrigatória, `primeira`/`ultima`, `marcacoes_especificas`
keyword-only, ordem de resolução, orientação do documento); onde os valores moram (unidade, endereço
e tema com default no domínio, caminhos dos logotipos em `settings`, ambiente sobrepondo pelos
builders); a marca d'água: **perguntar ao usuário** onde está o SVG e se ele já foi esmaecido — se
não, rodar `esmaecer_svg` sobre o arquivo **uma vez** e comitar o resultado; a emissão nunca clareia
nada; conferir com `uv run pytest -m artefato`; e o que **não** fazer — desenhar fora dos escritores,
escrever hex ou medida fora do tema, chamar o `esmaecer_svg` em tempo de request, persistir o PDF
aqui.

## 7 · Caveats
O documento oficial tem tema próprio — preto sobre branco, serifado, justificado —, e não porta a
paleta "Onsen de Inverno" do §3.4 do CLAUDE.md. Documento assinado por servidor público segue a norma
visual do papel, e um título em água clara leria como material promocional, não como ato
administrativo. O custo é um segundo design system no projeto, que não acompanha o primeiro quando ele
muda, e nada avisa quando divergirem.

Título, subtítulo e parágrafo são escritos por classes que **herdam** de `EscritorTexto`, e o
CLAUDE.md §7.1 trata herança como exceção rara. É o caso que a regra abre: a base é ABC, define a
interface `_estilo` e nada mais — os três fazem o mesmo gesto, e compor traria um parâmetro de estilo
que cada ponto de chamada teria de acertar. O custo é que o escritor de texto deixa de ser trocável
por qualquer callable: quem acrescentar um bloco textual herda ou reescreve o `__call__`.

O tema deixou de ser constante de módulo e passou a ser construído a partir do ambiente, então nenhum
escritor ou marca existe sem um `Tema` no construtor e não há singleton `renderizar_documento_oficial`.
É o que tira cor e medida de dentro do domínio e as põe onde a orquestração as resolve, como os CRS da
busca. O custo é que a orquestração passa a montar o tema a cada emissão — barato, mas repetido, e nada
impede duas rotas montarem temas diferentes por descuido.

O `Tema` e o `RenderizarDocumentoInput` carregam `ParagraphStyle`, `EstiloTabela` e
`MarcacaoDocumento` do reportlab e do motor, com `arbitrary_types_allowed`. É a mesma decisão do
e-mail, que escreve HTML no domínio: o formato de saída é conhecimento do escritor, e extrair uma
representação neutra intermediária duplicaria a ontologia dos blocos sem nada em troca. O custo é o
domínio importar a biblioteca — mitigado por importá-la sempre pelo `__init__.py` de
`services.utils.pdf`, para que haja uma costura só a trocar.

O `estilo_tabela` do tema não compõe `ZebraDoCorpo`, embora a regra exista no motor. Fundo de linha é
opaco no reportlab e apagaria a marca d'água em todo o retângulo da tabela, contrariando a condição de
que o corpo se leia por cima dela. O custo é que tabela longa se lê só pela grade, sem a alternância
que ajuda o olho a seguir a linha — e o fundo do cabeçalho, que se mantém, cobre a marca d'água na
primeira linha.

A tabela do documento só recusa linha com número de células divergente na montagem do flowable, dentro
do `TabelaInput` da SPEC 002, e não na construção do bloco. Repetir o validador no `Tabela` seria a
mesma invariante em dois lugares, livres para divergir. O custo é que o erro aparece ao renderizar, e
não ao montar o conteúdo — mesma chamada síncrona, mas um passo depois do ponto onde o dado errado
nasceu.

O texto institucional e o tema têm default no domínio; os caminhos dos logotipos, não. Aqueles são
conhecimento de domínio, estes dependem do `BASE_DIR`, que só a camada de settings conhece. O custo é a
assimetria — quem procura "onde fica o padrão" acha a unidade, o endereço e as cores em `models/` e os
arquivos em `config/settings.py`.

O teste de artefato **não apaga** o PDF que gera, ao contrário de tudo o mais nesta SPEC, que produz
bytes e não toca em disco. Arquivo apagado num `finally` não pode ser aberto por quem o pediu, e o
produto deste teste é justamente o arquivo. O custo é lixo em disco — contido por
`tmp_path_retention_count = 1`, que apaga a sessão anterior a cada execução, fora do repositório.

O `esmaecer_svg` clareia **no lugar** e é destrutivo: clarear duas vezes ou acertar a força depois
exige o SVG saturado de volta, e o único lugar onde ele existe é o histórico do git (`git show
<commit>:<caminho>`). É o preço de não versionar dois arquivos por logotipo, um saturado e um claro,
com nada garantindo que continuem sendo o mesmo desenho. O custo é que a força é escolhida sem ensaio
barato — quem a mudar restaura o original antes.

Os SVGs versionados são conversão dos EPS oficiais do manual de identidade visual da PMSP, feita uma
vez fora do projeto (`gs` → PDF, `pdftocairo -svg`, corte na caixa do traço e precisão reduzida a duas
casas). O EPS é formato proprietário e não entra no repositório. O custo é que atualizar o logotipo não
é trocar um arquivo: é refazer a conversão à mão, e nada no projeto a reproduz.

## 8 · Testes (TDD)
- `test_cada_bloco_sai_com_o_estilo_do_tema` — o flowable de cada bloco carrega o `ParagraphStyle` da
  peça correspondente; o parágrafo recuado carrega o dele, e cada nível de subtítulo o corpo do seu
  nível.
- `test_tema_vem_do_ambiente_e_cai_no_padrao` — sem valores de ambiente o tema sai preto sobre branco
  nos corpos padrão; corpo e cor definidos no ambiente aparecem nos estilos, e a entrelinha de cada
  estilo acompanha o corpo pelo fator.
- `test_lista_numera_pela_posicao_e_recomeca` — lista ordenada sai 1, 2, 3; não ordenada sai com
  marcador; duas listas seguidas recomeçam do 1.
- `test_bloco_tabela_vira_a_tabela_do_motor_com_o_estilo_do_tema` — colunas, cabeçalho e linhas do
  bloco chegam à tabela montada com o estilo do tema, e bloco com linha de tamanho divergente levanta
  na montagem.
- `test_texto_de_bloco_eh_escapado` — `&` e `<b>` no texto de um bloco chegam como texto no PDF, não
  como marcação do reportlab; em célula de tabela, escapados uma vez só.
- `test_bloco_sem_escritor_falha_na_montagem` — bloco cujo tipo não está no registro levanta na
  montagem, em vez de sumir do documento.
- `test_config_da_marcacao_tem_padrao_e_aceita_substituicao` — sem valores de ambiente, a unidade e o
  endereço saem os padrão; definidos no ambiente, são os do ambiente que aparecem no cabeçalho e no
  rodapé, e a faixa do cabeçalho cresce com o número de linhas.
- `test_cabecalho_poe_a_unidade_ao_lado_do_timbre` — a faixa do cabeçalho é a do mais alto dos dois, e
  não a soma; a unidade recebe a faixa recuada da largura do timbre mais o respiro, começando no mesmo
  topo e terminando na mesma borda direita.
- `test_papel_da_fazenda_traz_as_cinco_marcas_em_toda_pagina` — num documento de três páginas, timbre,
  cabeçalho, marca d'água, numeração e rodapé aparecem nas três, e a marca d'água precede o corpo no
  content stream de cada uma.
- `test_comando_grava_a_amostra_no_caminho_pedido` — o comando grava um PDF não vazio no caminho
  passado e não escreve em mais lugar nenhum.
- `test_amostra_para_conferencia` — grava a amostra num diretório temporário e imprime o caminho, para
  a conferência visual do timbre lado a lado com a unidade, da marca d'água, da tabela atravessando a
  quebra com o cabeçalho repetido, do rodapé dentro da margem e da numeração. *(marker `artefato`)*
