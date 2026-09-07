---
spec: documentos_oficiais/002
versao: v1
atualizado_em: 2026-09-06
testes_tdd: false
implementado: false
markers_obrigatorios: [artefato]
changelog:
  - v1: versão inicial
---

# SPEC documentos_oficiais/002 — Documento oficial como blocos e o papel timbrado da Fazenda

## 1 · User story
O administrador do cadastro gera um documento de amostra pelo terminal, no contexto de subir a emissão
de documentos oficiais, para conferir o timbre, a marca d'água e a numeração antes de qualquer ato
administrativo emitir documento de verdade.

## 2 · Condições de pronto
- [ ] Todo documento oficial é uma **sequência de blocos**, e o básico existe: **título, subtítulo,
      parágrafo, parágrafo recuado, lista numerada, lista não numerada e imagem** — nenhum documento
      desenha por conta própria.
- [ ] Texto interpolado num bloco sai **como texto no papel**, e não como marcação do reportlab.
- [ ] O papel timbrado da Secretaria da Fazenda traz, em **toda página**, timbre, cabeçalho da unidade,
      marca d'água, numeração e rodapé de endereço — o corpo é lido por cima da marca d'água, sem perda
      de contraste.
- [ ] A marcação nasce com **unidade, endereço e logotipos padrão**, e cada um é substituível na
      construção — sem edição de código e sem que o domínio leia configuração.
- [ ] `uv run python manage.py gerar_documento_amostra <caminho>` grava um PDF de amostra com todos os
      tipos de bloco e mais de uma página.
- [ ] Teste que produz arquivo para conferência humana roda atrás do marker **`artefato`**, grava fora
      do repositório e **imprime o caminho**; `uv run pytest --all` roda a suíte inteira.
- [ ] Existe a skill **`documento-oficial`**, e ela basta para escrever um documento novo sem ler o
      código do gerador: o vocabulário de blocos, a composição da marcação e a conferência da amostra.

## 3 · Domínio

`services/domain/documento_oficial/` é o domínio do documento oficial do sistema, e guarda três coisas:
**o que um documento diz**, **como isso vira página** e os **casos de uso** que produzem conteúdo — um
por documento que o sistema emite. Hoje há um só, o de amostra; a certidão de lançamento entra ao lado
dele.

O corpo é uma **sequência de blocos**, e é o tipo do bloco — não um campo de configuração — que decide
como ele se escreve. Documento novo é arranjo de blocos existentes; bloco novo é subtipo novo aqui, com
o seu escritor no §6.

O que se repete em toda página **não é conteúdo**: é a **marcação**. A SPEC
[documentos_oficiais/001](001-motor-de-pdf.md) entrega o vocabulário dela — `Marca`, `Marcacao`,
`MarcacaoDocumento`, `Folha` e `Faixa` —, e esta pergunta a ele **quais marcas compõem o papel timbrado
da Fazenda** e o que cada uma precisa saber para pintar.

**`services/domain/documento_oficial/models.py`**
```python
class BlocoDocumento(BaseModel):
    """Base dos blocos: bloco não compartilha atributo, compartilha posição no corpo."""

    model_config = ConfigDict(frozen=True)


class Titulo(BlocoDocumento):
    tipo: Literal["titulo"] = "titulo"
    texto: str


class Subtitulo(BlocoDocumento):
    tipo: Literal["subtitulo"] = "subtitulo"
    texto: str


class Paragrafo(BlocoDocumento):
    tipo: Literal["paragrafo"] = "paragrafo"
    texto: str
    # Recuo é variação do mesmo bloco, não bloco próprio: o que muda é a margem, não a natureza do
    # que se lê. Transcrição e citação em documento oficial saem assim.
    recuado: bool = False


class Lista(BlocoDocumento):
    """Um bloco por lista, não por item: a numeração é a posição do item, e nada precisa contar."""

    tipo: Literal["lista"] = "lista"
    ordenada: bool = False
    itens: tuple[str, ...] = Field(min_length=1)


class Imagem(BlocoDocumento):
    tipo: Literal["imagem"] = "imagem"
    # Caminho já resolvido: o domínio não sabe onde ficam os estáticos do projeto.
    caminho: Path
    largura_mm: float | None = None


Bloco = Annotated[
    Titulo | Subtitulo | Paragrafo | Lista | Imagem,
    Field(discriminator="tipo"),
]


class ConteudoDocumento(BaseModel):
    """O que o documento diz. Sem cabeçalho nem rodapé: aquilo é da marcação, não do conteúdo."""

    model_config = ConfigDict(frozen=True)

    # Vai para os metadados do PDF, e é o que o leitor mostra na barra de título.
    titulo: str
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


class MarcacaoConfig(BaseModel):
    """O que distingue um papel timbrado de outro. Os caminhos não têm default: eles dependem da
    raiz do projeto, que o domínio não conhece."""

    model_config = ConfigDict(frozen=True)

    logo_horizontal: Path
    logo_vertical: Path
    # Um nível por item, e não uma linha só: é a marca que decide se empilha ou junta.
    unidade: tuple[str, ...] = UNIDADE_PADRAO
    endereco: tuple[str, ...] = ENDERECO_PADRAO
    largura_timbre_mm: float = 58.0
    largura_marca_dagua_mm: float = 105.0
    forca_marca_dagua: float = 0.93


class DocumentoAmostraInput(BaseModel):
    """O pedido da amostra. Sem caminho de saída: gravar é do comando, gerar é do domínio."""

    model_config = ConfigDict(frozen=True)

    # De onde a amostra partiu, para quem confere saber qual ambiente foi provado.
    ambiente: str
    momento: datetime
```

## 4 · Fora de escopo
- A certidão de lançamento, sua rota protegida e o registro da execução — épico `documentos_oficiais`,
  SPEC própria.
- Armazenagem do documento emitido (quem emitiu, sobre o quê, quando) — SPEC da certidão.
- Sandbox de aprovação (gerar em temporário, o servidor revisar, só então salvar) e o gerenciador de
  temporários que ele exige — SPEC própria, depois desta.
- Assinatura digital, código de verificação e QR de autenticidade — sem dono ainda.
- Tabela como bloco — sem dono ainda; entra quando houver documento que precise dela.
- Marcação de outra secretaria ou de outro papel timbrado — sem dono ainda; o registro de marcações
  nasce com uma só.

## 5 · Peças de referência a compor
- `@services/utils/pdf` → `Marca`, `Marcacao`, `MarcacaoDocumento`, `gerar_pdf`, `carregar_vetor` e
  `esmaecer`: o motor entregue pela SPEC 001.
- `@services/domain/email` → o padrão de bloco, registro de escritores e tema próprio.
- `@services/utils/io` → `escrever_atomico`: a gravação do arquivo pelo comando de amostra.
- `@services/utils/smtp/config.py` → `SmtpSettingsLike` e `build_smtp_config`: o padrão de Protocol +
  builder que leva `settings` ao domínio.
- `@static/src/img/documento_oficial/sec_fazenda_horizontal.svg` → o logotipo do cabeçalho, vetorial,
  237,84 × 75,58 pt.
- `@static/src/img/documento_oficial/sec_fazenda_vertical.svg` → o logotipo da marca d'água, vetorial,
  168,16 × 144,41 pt.
- Skills: `ontologia`, `escrever-testes`, `management-commands`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`services/domain/documento_oficial/tema.py`** — o design system do documento: fonte única dos valores
que os escritores e as marcas usam. Nenhum deles escreve cor, medida ou fonte.
```python
# Documento oficial é preto sobre branco, serifado e justificado: a norma do papel, não o tema da
# aplicação. Nenhum hex do Onsen de Inverno entra aqui — ver Caveats.
TINTA = colors.black
TINTA_SECUNDARIA = colors.HexColor("#555555")

TEMA_DOCUMENTO: dict[str, ParagraphStyle] = {
    "titulo": ParagraphStyle(
        "titulo",
        fontName="Times-Bold",
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        spaceAfter=12,
        textColor=TINTA,
    ),
    # O espaço entre parágrafos é do ESTILO, não de um Spacer entre blocos: assim o escritor
    # devolve um flowable só, e a quebra de página nunca deixa um espaçador órfão no topo.
    "paragrafo": ParagraphStyle(
        "paragrafo",
        fontName="Times-Roman",
        fontSize=11,
        leading=16,
        alignment=TA_JUSTIFY,
        firstLineIndent=12,
        spaceAfter=8,
        textColor=TINTA,
    ),
    "paragrafo_recuado": ParagraphStyle(
        "paragrafo_recuado",
        parent=...,  # o de cima, com as margens deslocadas e sem recuo de primeira linha
        leftIndent=28,
        rightIndent=14,
        firstLineIndent=0,
        fontSize=10,
    ),
    # ... "subtitulo" e "item", na mesma forma.
}

ESTILO_RODAPE = EstiloTexto(fonte="Times-Roman", corpo_pt=8, cor=TINTA_SECUNDARIA)
```

**`services/domain/documento_oficial/escritores.py`** — um escritor por bloco, cada um a única linha
do projeto que sabe **como aquele bloco vira flowable**.
```python
class EscritorParagrafo:
    def __call__(self, bloco: Paragrafo) -> Flowable:
        estilo = "paragrafo_recuado" if bloco.recuado else "paragrafo"
        # `Paragraph` interpreta marcação própria do reportlab: o escape é daqui, como no e-mail.
        return Paragraph(_texto(bloco.texto), TEMA_DOCUMENTO[estilo])


class EscritorLista:
    def __call__(self, bloco: Lista) -> Flowable:
        return self.pipeline(bloco)

    def pipeline(self, bloco: Lista) -> Flowable:
        # `bulletType="1"` numera pela POSIÇÃO na lista: o número não é dado do bloco, e duas
        # listas seguidas recomeçam do 1 sem ninguém zerar contador.
        return ListFlowable(
            [ListItem(self._item(texto)) for texto in bloco.itens],
            bulletType="1" if bloco.ordenada else "bullet",
            bulletFontName=TEMA_DOCUMENTO["item"].fontName,
            leftIndent=24,
        )

    def _item(self, texto: str) -> Flowable:
        return Paragraph(_texto(texto), TEMA_DOCUMENTO["item"])


# `EscritorTitulo`, `EscritorSubtitulo` e `EscritorImagem` seguem a mesma forma, no mesmo módulo.
# O registro é a única lista de tipos do módulo: bloco novo entra aqui e em lugar nenhum mais.
ESCRITORES: dict[str, Callable[[Any], Flowable]] = {
    "titulo": EscritorTitulo(),
    "subtitulo": EscritorSubtitulo(),
    "paragrafo": EscritorParagrafo(),
    "lista": EscritorLista(),
    "imagem": EscritorImagem(),
}
```

**`services/domain/documento_oficial/marcas.py`** — as marcas concretas. Cada uma pinta na faixa que
recebeu e não sabe o tamanho da página: é isto que deixa a `Marcacao` reordená-las sem que nenhuma se
quebre. O logotipo horizontal já traz "PREFEITURA DE SÃO PAULO / SECRETARIA DA FAZENDA", então o
`CabecalhoUnidade` nomeia só a unidade — nada é dito duas vezes. Ele e o `RodapeEndereco` vivem no
mesmo módulo e recebem as linhas prontas no `__init__`: nenhum texto institucional é literal na marca.
```python
class TimbreHorizontal(Marca):
    """O logotipo da Secretaria, no alto de toda página."""

    posicao = Posicao.SUPERIOR
    altura_mm = 20.0

    def __init__(self, caminho_svg: Path, largura_mm: float) -> None:
        # O Drawing é carregado UMA vez e reusado em toda página: o SVG tem centenas de traços, e
        # reabri-lo por página seria o custo desta marca multiplicado pelo tamanho do documento.
        self._desenho = carregar_vetor(caminho_svg, largura_mm)

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        folha.vetor(faixa.esquerda_mm, faixa.topo_mm, self._desenho, nome="timbre")


class MarcaDagua(Marca):
    """O logotipo vertical, clareado, no meio do papel. Reserva ZERO: o corpo passa por cima."""

    posicao = Posicao.FUNDO
    altura_mm = 0.0

    def __init__(self, caminho_svg: Path, largura_mm: float, forca: float) -> None:
        self._desenho = esmaecer(carregar_vetor(caminho_svg, largura_mm), forca)

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
    altura_mm = 8.0

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        folha.texto(
            faixa.esquerda_mm,
            faixa.topo_mm,
            f"Página {folha.pagina} de {folha.total}",
            ESTILO_RODAPE,
        )
```

**`services/domain/documento_oficial/config.py`** — a costura entre `settings` e o domínio, no padrão
do `services/utils/smtp/config.py`: o domínio declara o que precisa e nunca importa o Django.
```python
class DocumentoSettingsLike(Protocol):
    DOCUMENTO_LOGO_HORIZONTAL: Path
    DOCUMENTO_LOGO_VERTICAL: Path
    DOCUMENTO_UNIDADE: tuple[str, ...] | None
    DOCUMENTO_ENDERECO: tuple[str, ...] | None


def build_marcacao_config(source: DocumentoSettingsLike) -> MarcacaoConfig:
    # Só o que o ambiente DEFINIU é repassado: campo ausente deixa o default do MarcacaoConfig
    # valer. Passar `None` adiante sobrescreveria o padrão com vazio, e obrigaria o texto
    # institucional a existir aqui também — duas cópias livres para divergir.
    do_ambiente = {
        "unidade": source.DOCUMENTO_UNIDADE,
        "endereco": source.DOCUMENTO_ENDERECO,
    }
    return MarcacaoConfig(
        logo_horizontal=source.DOCUMENTO_LOGO_HORIZONTAL,
        logo_vertical=source.DOCUMENTO_LOGO_VERTICAL,
        **{chave: valor for chave, valor in do_ambiente.items() if valor is not None},
    )
```

**`config/settings.py`** — o caminho padrão dos logotipos, no mesmo lugar e formato do `MAP_FUNDO_DIR`.
É a única camada que conhece a raiz do projeto.
```python
DOCUMENTO_LOGO_HORIZONTAL = _env.documento_logo_horizontal or (
    BASE_DIR / "static" / "src" / "img" / "documento_oficial" / "sec_fazenda_horizontal.svg"
)
DOCUMENTO_LOGO_VERTICAL = _env.documento_logo_vertical or (
    BASE_DIR / "static" / "src" / "img" / "documento_oficial" / "sec_fazenda_vertical.svg"
)
# Sem default aqui: `None` é o que faz o padrão do MarcacaoConfig valer.
DOCUMENTO_UNIDADE = _env.documento_unidade
DOCUMENTO_ENDERECO = _env.documento_endereco
```

**`services/domain/documento_oficial/marcacoes.py`** — a marcação da SF é a composição das marcas, na
ordem em que se empilham. Trocar de papel timbrado é trocar esta tupla; trocar de unidade é trocar a
config.
```python
def marcacao_secretaria_fazenda(config: MarcacaoConfig) -> Marcacao:
    return Marcacao(
        marcas=(
            TimbreHorizontal(config.logo_horizontal, config.largura_timbre_mm),
            CabecalhoUnidade(config.unidade),
            MarcaDagua(
                config.logo_vertical,
                config.largura_marca_dagua_mm,
                config.forca_marca_dagua,
            ),
            RodapeEndereco(config.endereco),
            NumeracaoPaginas(),
        ),
        margem_lateral_mm=25.0,
        respiro_mm=8.0,
    )
```

**`services/domain/documento_oficial/render.py`** — blocos + marcação → bytes.
```python
class RenderizarDocumentoOficial:
    """Callable: ConteudoDocumento + MarcacaoDocumento → os bytes do PDF."""

    def __init__(self, escritores: Mapping[str, Callable[[Any], Flowable]] | None = None) -> None:
        self._escritores = dict(escritores or ESCRITORES)

    def __call__(self, conteudo: ConteudoDocumento, marcacao: MarcacaoDocumento) -> bytes:
        return self.pipeline(conteudo, marcacao)

    def pipeline(self, conteudo: ConteudoDocumento, marcacao: MarcacaoDocumento) -> bytes:
        return gerar_pdf(
            DocumentoPdfInput(
                titulo=conteudo.titulo,
                corpo=tuple(self._escrever(bloco) for bloco in conteudo.blocos),
                marcacao=marcacao,
            )
        )

    def _escrever(self, bloco: BlocoDocumento) -> Flowable:
        # Bloco sem escritor levanta KeyError na montagem — onde há teste e stack trace —, e não
        # como buraco silencioso num documento que alguém vai assinar.
        return self._escritores[bloco.tipo](bloco)


renderizar_documento_oficial = RenderizarDocumentoOficial()
```

**`services/domain/documento_oficial/amostra.py`** — o corpo da amostra, e só ele. Cada documento do
sistema ganha um módulo assim ao lado deste.
```python
class MontarDocumentoAmostra:
    """Callable: o pedido vira o que o documento vai dizer. Todos os tipos de bloco aparecem, e o
    texto é longo o bastante para virar a página — é o que prova a marcação repetida."""

    def __call__(self, pedido: DocumentoAmostraInput) -> ConteudoDocumento: ...


montar_documento_amostra = MontarDocumentoAmostra()
```

**`apps/core/management/commands/gerar_documento_amostra.py`** — o comando é fino: lê `settings`, monta
o DTO, chama as peças e grava. Sem `--verbose` nem `--automatico`: essas são do contrato dos comandos
de carga (`ScriptRunner`, SPEC `ingestao_dados/006`), e este não é um deles.
```python
class Command(BaseCommand):
    help = "Grava um PDF de amostra com todos os blocos e a marcação oficial da SF."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("caminho", type=Path)

    def handle(self, *args: object, **options: object) -> None:
        pedido = DocumentoAmostraInput(
            ambiente=settings.ALLOWED_HOSTS[0],
            momento=timezone.now(),
        )
        conteudo = montar_documento_amostra(pedido)
        # A orquestração é o único ponto que toca `settings`; o domínio recebe a config pronta.
        marcacao = marcacao_secretaria_fazenda(build_marcacao_config(settings))
        escrever_atomico(Path(options["caminho"]), renderizar_documento_oficial(conteudo, marcacao))
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

**`tests/conftest.py`** — a fixture e a flag são **infraestrutura de suíte**, não desta SPEC: nascem
aqui porque este é o primeiro serviço que gera arquivo para olho humano, e servem o snapshot do mapa e
a exportação que vierem depois. O contrato completo está na skill `escrever-testes` (§3.6 e §4.2).
```python
@pytest.fixture
def publicar_artefato(tmp_path, capsys) -> Callable[[str, bytes], Path]:
    """Grava o artefato onde ele sobreviva à sessão e imprime onde ele está."""


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--all", action="store_true", help="Roda a suíte inteira, markers inclusive.")


def pytest_configure(config: pytest.Config) -> None:
    # O `-m` herdado do addopts é o que exclui as camadas pesadas; --all simplesmente o esvazia.
    if config.getoption("--all"):
        config.option.markexpr = ""
```

**`.claude/skills/documento-oficial/SKILL.md`** — entregável desta SPEC, não subproduto: o gerador é
infraestrutura que outras ações vão consumir, e sem a skill cada ação nova descobre o vocabulário
lendo `services/domain/documento_oficial/`. Cobre: os blocos existentes e o que cada um carrega, e que
bloco novo é subtipo + escritor no registro; escrever um documento criando o módulo do caso de uso ao
lado de `amostra.py`; compor a marcação com `MarcacaoDocumento` (principal obrigatória,
`primeira`/`ultima`, `marcacoes_especificas` keyword-only, ordem de resolução, orientação do
documento); onde os valores moram (unidade e endereço no domínio, caminhos dos logotipos em
`settings`, via `build_marcacao_config`); conferir com `uv run pytest -m artefato`; e o que **não**
fazer — desenhar fora dos escritores, escrever hex ou medida fora do tema, persistir o PDF aqui.

## 7 · Caveats
O documento oficial tem tema próprio — preto sobre branco, serifado, justificado —, e não porta a
paleta "Onsen de Inverno" do §3.4 do CLAUDE.md. Documento assinado por servidor público segue a norma
visual do papel, e um título em água clara leria como material promocional, não como ato
administrativo. O custo é um segundo design system no projeto, que não acompanha o primeiro quando ele
muda, e nada avisa quando divergirem.

Os escritores e as marcas tipam `Flowable`, `ParagraphStyle` e `Drawing` do reportlab dentro de
`services/domain/`. É a mesma decisão do e-mail, que escreve HTML no domínio: o formato de saída é
conhecimento do escritor, e extrair uma representação neutra intermediária duplicaria a ontologia dos
blocos sem nada em troca. O custo é o domínio importar a biblioteca — mitigado por importá-la sempre
pelo `__init__.py` de `services.utils.pdf`, para que haja uma costura só a trocar.

O texto institucional tem default no domínio e os caminhos dos logotipos não: aqueles são conhecimento
de domínio, estes dependem do `BASE_DIR`, que só a camada de settings conhece. O custo é a assimetria —
quem procura "onde fica o padrão" acha a unidade e o endereço em `models.py` e os arquivos em
`config/settings.py`.

O teste de artefato **não apaga** o PDF que gera, ao contrário de tudo o mais nesta SPEC, que produz
bytes e não toca em disco. Arquivo apagado num `finally` não pode ser aberto por quem o pediu, e o
produto deste teste é justamente o arquivo. O custo é lixo em disco — contido por
`tmp_path_retention_count = 1`, que apaga a sessão anterior a cada execução, fora do repositório.

Os SVGs versionados são conversão dos EPS oficiais do manual de identidade visual da PMSP, feita uma
vez fora do projeto (`gs` → PDF, `pdftocairo -svg`, corte na caixa do traço e precisão reduzida a duas
casas). O EPS é formato proprietário e não entra no repositório. O custo é que atualizar o logotipo não
é trocar um arquivo: é refazer a conversão à mão, e nada no projeto a reproduz.

## 8 · Testes (TDD)
- `test_cada_bloco_sai_com_o_estilo_do_tema` — o flowable de cada bloco carrega o `ParagraphStyle` da
  peça correspondente de `TEMA_DOCUMENTO`, e o parágrafo recuado carrega o dele.
- `test_lista_numera_pela_posicao_e_recomeca` — lista ordenada sai 1, 2, 3; não ordenada sai com
  marcador; duas listas seguidas recomeçam do 1.
- `test_texto_de_bloco_eh_escapado` — `&` e `<b>` no texto de um bloco chegam como texto no PDF, não
  como marcação do reportlab.
- `test_bloco_sem_escritor_falha_na_montagem` — bloco cujo tipo não está no registro levanta na
  montagem, em vez de sumir do documento.
- `test_config_da_marcacao_tem_padrao_e_aceita_substituicao` — sem valores de ambiente, a unidade e o
  endereço saem os padrão; definidos no ambiente, são os do ambiente que aparecem no cabeçalho e no
  rodapé.
- `test_papel_da_fazenda_traz_as_cinco_marcas_em_toda_pagina` — num documento de três páginas, timbre,
  cabeçalho, marca d'água, numeração e rodapé aparecem nas três, e a marca d'água precede o corpo no
  content stream de cada uma.
- `test_comando_grava_a_amostra_no_caminho_pedido` — o comando grava um PDF não vazio no caminho
  passado e não escreve em mais lugar nenhum.
- `test_amostra_para_conferencia` — grava a amostra num diretório temporário e imprime o caminho, para
  a conferência visual do timbre, da marca d'água e da numeração. *(marker `artefato`)*
