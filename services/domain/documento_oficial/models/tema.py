from pydantic import BaseModel, ConfigDict, Field
from reportlab.lib.styles import ParagraphStyle

from services.utils.pdf import EstiloTabela, EstiloTexto

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
