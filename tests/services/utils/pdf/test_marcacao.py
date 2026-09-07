from io import BytesIO

from reportlab.pdfgen.canvas import Canvas

from services.utils.pdf.folha import Folha
from services.utils.pdf.marcacao import Marca, Marcacao
from services.utils.pdf.models import A4, Faixa, Orientacao, Posicao, TamanhoPagina


class _MarcaFake(Marca):
    """Não pinta nada: só registra a faixa que recebeu, para o teste inspecionar."""

    def __init__(self, posicao: Posicao, altura_mm: float) -> None:
        self.posicao = posicao
        self.altura_mm = altura_mm
        self.faixas_recebidas: list[Faixa] = []

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        self.faixas_recebidas.append(faixa)


def _marca(posicao: Posicao = Posicao.SUPERIOR, altura_mm: float = 10.0) -> _MarcaFake:
    return _MarcaFake(posicao=posicao, altura_mm=altura_mm)


def _folha(tamanho: TamanhoPagina) -> Folha:
    return Folha(Canvas(BytesIO()), tamanho, pagina=1, total=1)


# ---------------------------------------------------------------------------
# Margens derivadas da soma das marcas
# ---------------------------------------------------------------------------


def test_marcacao_deriva_margens_da_soma_das_marcas() -> None:
    superior_a = _marca(Posicao.SUPERIOR, altura_mm=10.0)
    superior_b = _marca(Posicao.SUPERIOR, altura_mm=5.0)
    fundo = _marca(Posicao.FUNDO, altura_mm=999.0)
    tamanho = A4.orientar(Orientacao.RETRATO)
    sem_borda_inferior = Marcacao(
        marcas=(superior_a, superior_b, fundo),
        margem_lateral_mm=15.0,
        respiro_mm=3.0,
    )
    com_borda_inferior = Marcacao(
        marcas=(superior_a, superior_b, fundo, _marca(Posicao.INFERIOR, altura_mm=7.0)),
        margem_lateral_mm=15.0,
        respiro_mm=3.0,
    )

    margens = sem_borda_inferior.margens(tamanho)

    assert margens.superior_mm == 10.0 + 5.0 + 3.0
    assert margens.inferior_mm == 3.0
    assert margens.esquerda_mm == 15.0
    assert margens.direita_mm == 15.0
    # Acrescentar uma marca de borda aumenta a margem correspondente...
    assert com_borda_inferior.margens(tamanho).inferior_mm == 7.0 + 3.0
    # ...e a marca de fundo, presente nas duas, nunca altera margem nenhuma.
    assert com_borda_inferior.margens(tamanho).superior_mm == margens.superior_mm


# ---------------------------------------------------------------------------
# Faixas: uma por marca, empilhadas, sem sobreposição
# ---------------------------------------------------------------------------


def test_cada_marca_recebe_a_faixa_dela_sem_sobrepor() -> None:
    topo_1 = _marca(Posicao.SUPERIOR, altura_mm=10.0)
    topo_2 = _marca(Posicao.SUPERIOR, altura_mm=20.0)
    pe = _marca(Posicao.INFERIOR, altura_mm=5.0)
    marcacao = Marcacao(marcas=(topo_1, topo_2, pe), margem_lateral_mm=10.0, respiro_mm=0.0)
    tamanho = A4.orientar(Orientacao.RETRATO)

    marcacao.pintar_bordas(_folha(tamanho))

    faixa_1 = topo_1.faixas_recebidas[0]
    faixa_2 = topo_2.faixas_recebidas[0]
    faixa_pe = pe.faixas_recebidas[0]

    assert faixa_1.topo_mm == 0.0
    assert faixa_1.altura_mm == 10.0
    # A segunda marca superior começa exatamente onde a primeira termina: sem gap, sem overlap.
    assert faixa_2.topo_mm == faixa_1.topo_mm + faixa_1.altura_mm
    assert faixa_pe.topo_mm == tamanho.altura_mm - 5.0
    assert faixa_pe.altura_mm == 5.0
    # Nenhuma faixa de borda invade a área lateral reservada.
    assert faixa_1.esquerda_mm == 10.0
    assert faixa_1.largura_mm == tamanho.largura_mm - 20.0
