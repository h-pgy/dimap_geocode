from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from reportlab.pdfgen.canvas import Canvas

from services.domain.documento_oficial import (
    ENDERECO_PADRAO,
    UNIDADE_PADRAO,
    CabecalhoTimbrado,
    CabecalhoUnidade,
    MarcacaoConfig,
    RodapeEndereco,
    TemaConfig,
    TimbreHorizontal,
    montar_tema,
)
from services.utils.pdf import A4, Faixa, Folha, Orientacao

SVG_RETANGULO = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10" viewBox="0 0 20 10">
<rect x="0" y="0" width="20" height="10" fill="#336633" />
</svg>"""


class _UnidadeEspiada(CabecalhoUnidade):
    """Registra a faixa que recebeu, para o teste ver onde o cabeçalho a pôs sem ler o PDF."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.faixas_recebidas: list[Faixa] = []

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        self.faixas_recebidas.append(faixa)
        super().__call__(faixa, folha)


def _config(tmp_path: Path, **overrides: object) -> MarcacaoConfig:
    defaults: dict[str, object] = {
        "logo_horizontal": tmp_path / "h.svg",
        "logo_vertical": tmp_path / "v.svg",
    }
    return MarcacaoConfig.model_validate(defaults | overrides)


# ---------------------------------------------------------------------------
# Padrão institucional, substituição pelo ambiente e faixa que cresce com a linha
# ---------------------------------------------------------------------------


def test_config_da_marcacao_tem_padrao_e_aceita_substituicao(tmp_path: Path) -> None:
    tema = montar_tema(TemaConfig())
    padrao = _config(tmp_path)
    assert padrao.unidade == UNIDADE_PADRAO
    assert padrao.endereco == ENDERECO_PADRAO

    unidade_extensa = (*UNIDADE_PADRAO, "Núcleo de Amostra")
    endereco_customizado = ("Rua de Teste, 42 - Bairro Teste, São Paulo - SP",)
    substituida = _config(tmp_path, unidade=unidade_extensa, endereco=endereco_customizado)
    assert substituida.unidade == unidade_extensa
    assert substituida.endereco == endereco_customizado

    cabecalho_padrao = CabecalhoUnidade(
        padrao.unidade, tema.estilo_cabecalho_marca, tema.entrelinha_marca_mm
    )
    cabecalho_substituido = CabecalhoUnidade(
        substituida.unidade, tema.estilo_cabecalho_marca, tema.entrelinha_marca_mm
    )
    rodape_substituido = RodapeEndereco(
        substituida.endereco, tema.estilo_rodape_marca, tema.entrelinha_marca_mm
    )
    # A faixa do cabeçalho cresce com o número de linhas da unidade.
    assert cabecalho_substituido.altura_mm > cabecalho_padrao.altura_mm

    tamanho = A4.orientar(Orientacao.RETRATO)
    buffer = BytesIO()
    canvas = Canvas(buffer)
    folha = Folha(canvas, tamanho, pagina=1, total=1)
    faixa = Faixa(
        esquerda_mm=20.0,
        topo_mm=0.0,
        largura_mm=tamanho.largura_mm - 40.0,
        altura_mm=cabecalho_substituido.altura_mm,
    )
    cabecalho_substituido(faixa, folha)
    rodape_substituido(faixa, folha)
    canvas.showPage()
    canvas.save()

    texto = PdfReader(BytesIO(buffer.getvalue())).pages[0].extract_text()
    for linha in unidade_extensa:
        assert linha in texto
    assert endereco_customizado[0] in texto


# ---------------------------------------------------------------------------
# Cabeçalho: unidade AO LADO do timbre, não abaixo dele
# ---------------------------------------------------------------------------


def test_cabecalho_poe_a_unidade_ao_lado_do_timbre(tmp_path: Path) -> None:
    tema = montar_tema(TemaConfig())
    caminho = tmp_path / "h.svg"
    caminho.write_text(SVG_RETANGULO)
    timbre = TimbreHorizontal(caminho, largura_mm=58.0)
    unidade = CabecalhoUnidade(UNIDADE_PADRAO, tema.estilo_cabecalho_marca, tema.entrelinha_marca_mm)
    cabecalho = CabecalhoTimbrado(timbre, unidade, respiro_mm=8.0)

    # A faixa é a do mais alto dos dois, e não a soma: é o que impede o cabeçalho de comer a página.
    assert cabecalho.altura_mm == max(timbre.altura_mm, unidade.altura_mm)

    tamanho = A4.orientar(Orientacao.RETRATO)
    faixa = Faixa(
        esquerda_mm=25.0,
        topo_mm=15.0,
        largura_mm=tamanho.largura_mm - 50.0,
        altura_mm=cabecalho.altura_mm,
    )
    espiada = _UnidadeEspiada(UNIDADE_PADRAO, tema.estilo_cabecalho_marca, tema.entrelinha_marca_mm)
    CabecalhoTimbrado(timbre, espiada, respiro_mm=8.0)(
        faixa, Folha(Canvas(BytesIO()), tamanho, pagina=1, total=1)
    )

    faixa_unidade = espiada.faixas_recebidas[0]
    assert faixa_unidade.esquerda_mm == faixa.esquerda_mm + timbre.largura_mm + 8.0
    assert faixa_unidade.topo_mm == faixa.topo_mm
    # A unidade não passa da margem direita que a faixa do cabeçalho já respeita.
    borda_direita = faixa_unidade.esquerda_mm + faixa_unidade.largura_mm
    assert borda_direita == faixa.esquerda_mm + faixa.largura_mm
