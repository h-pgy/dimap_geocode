from collections.abc import Callable
from io import BytesIO
from pathlib import Path

import pytest
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

from services.utils.pdf import QrCodePdfInput, qr_code_pdf
from services.utils.pdf.documento import DocumentoPdfInput, gerar_pdf
from services.utils.pdf.documento_marcado import MarcacaoDocumento
from services.utils.pdf.folha import Folha
from services.utils.pdf.marcacao import Marca, Marcacao, MarcasLadoALado
from services.utils.pdf.models import (
    A4,
    EstiloTexto,
    EstiloTraco,
    Faixa,
    Orientacao,
    Posicao,
    TamanhoPagina,
)
from services.utils.qr_code import QrCodeInput, gerar_qr_code

ESTILO_NORMAL = getSampleStyleSheet()["Normal"]
ESTILO_TEXTO_ROTULO = EstiloTexto(fonte="Helvetica", corpo_pt=10.0, cor=HexColor("#000000"))


class _MarcaFake(Marca):
    """Não pinta nada: só registra a faixa que recebeu, para o teste inspecionar."""

    def __init__(
        self,
        posicao: Posicao,
        altura_mm: float,
        largura_mm: float | None = None,
    ) -> None:
        self.posicao = posicao
        self.altura_mm = altura_mm
        self.largura_mm = largura_mm
        self.faixas_recebidas: list[Faixa] = []

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        self.faixas_recebidas.append(faixa)


def _marca(
    posicao: Posicao = Posicao.SUPERIOR,
    altura_mm: float = 10.0,
    largura_mm: float | None = None,
) -> _MarcaFake:
    return _MarcaFake(posicao=posicao, altura_mm=altura_mm, largura_mm=largura_mm)


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
        margem_vertical_mm=12.0,
        respiro_mm=3.0,
    )
    com_borda_inferior = Marcacao(
        marcas=(superior_a, superior_b, fundo, _marca(Posicao.INFERIOR, altura_mm=7.0)),
        margem_lateral_mm=15.0,
        margem_vertical_mm=12.0,
        respiro_mm=3.0,
    )

    margens = sem_borda_inferior.margens(tamanho)

    # A margem vertical entra nas duas bordas mesmo onde não há marca alguma: é a borda que a
    # impressora não alcança, e nem as marcas a ocupam.
    assert margens.superior_mm == 12.0 + 10.0 + 5.0 + 3.0
    assert margens.inferior_mm == 12.0 + 3.0
    assert margens.esquerda_mm == 15.0
    assert margens.direita_mm == 15.0
    # Acrescentar uma marca de borda aumenta a margem correspondente...
    assert com_borda_inferior.margens(tamanho).inferior_mm == 12.0 + 7.0 + 3.0
    # ...e a marca de fundo, presente nas duas, nunca altera margem nenhuma.
    assert com_borda_inferior.margens(tamanho).superior_mm == margens.superior_mm


# ---------------------------------------------------------------------------
# Faixas: uma por marca, empilhadas, sem sobreposição
# ---------------------------------------------------------------------------


def test_cada_marca_recebe_a_faixa_dela_sem_sobrepor() -> None:
    topo_1 = _marca(Posicao.SUPERIOR, altura_mm=10.0)
    topo_2 = _marca(Posicao.SUPERIOR, altura_mm=20.0)
    pe = _marca(Posicao.INFERIOR, altura_mm=5.0)
    marcacao = Marcacao(
        marcas=(topo_1, topo_2, pe),
        margem_lateral_mm=10.0,
        margem_vertical_mm=12.0,
        respiro_mm=0.0,
    )
    tamanho = A4.orientar(Orientacao.RETRATO)

    marcacao.pintar_bordas(_folha(tamanho))

    faixa_1 = topo_1.faixas_recebidas[0]
    faixa_2 = topo_2.faixas_recebidas[0]
    faixa_pe = pe.faixas_recebidas[0]

    # Nem a primeira marca superior nem a inferior encostam na aresta do papel.
    assert faixa_1.topo_mm == 12.0
    assert faixa_1.altura_mm == 10.0
    # A segunda marca superior começa exatamente onde a primeira termina: sem gap, sem overlap.
    assert faixa_2.topo_mm == faixa_1.topo_mm + faixa_1.altura_mm
    assert faixa_pe.topo_mm == tamanho.altura_mm - 12.0 - 5.0
    assert faixa_pe.altura_mm == 5.0
    # Nenhuma faixa de borda invade a área lateral reservada.
    assert faixa_1.esquerda_mm == 10.0
    assert faixa_1.largura_mm == tamanho.largura_mm - 20.0


# ---------------------------------------------------------------------------
# MarcasLadoALado: uma faixa só, com a altura da mais alta
# ---------------------------------------------------------------------------


def test_grupo_lado_a_lado_ocupa_uma_faixa_com_a_altura_da_mais_alta() -> None:
    baixa = _marca(altura_mm=5.0, largura_mm=20.0)
    media = _marca(altura_mm=10.0, largura_mm=20.0)
    alta = _marca(altura_mm=15.0, largura_mm=20.0)
    grupo = MarcasLadoALado((baixa, media, alta), Posicao.INFERIOR, respiro_mm=2.0)

    assert grupo.altura_mm == 15.0

    marcacao = Marcacao(
        marcas=(grupo,),
        margem_lateral_mm=10.0,
        margem_vertical_mm=12.0,
        respiro_mm=0.0,
    )
    tamanho = A4.orientar(Orientacao.RETRATO)

    # A SOMA das três daria 30 mm de margem; a maior sozinha dá 15 — é a maior que vale.
    assert marcacao.margens(tamanho).inferior_mm == 12.0 + 15.0


# ---------------------------------------------------------------------------
# Repartição: declaradas recebem o que pediram, a elástica recebe o resto
# ---------------------------------------------------------------------------


def test_marca_sem_largura_recebe_a_sobra_da_faixa() -> None:
    declarada_a = _marca(largura_mm=30.0)
    elastica = _marca(largura_mm=None)
    declarada_b = _marca(largura_mm=20.0)
    grupo = MarcasLadoALado((declarada_a, elastica, declarada_b), Posicao.SUPERIOR, respiro_mm=5.0)
    faixa = Faixa(esquerda_mm=0.0, topo_mm=0.0, largura_mm=100.0, altura_mm=10.0)

    grupo(faixa, _folha(A4.orientar(Orientacao.RETRATO)))

    assert declarada_a.faixas_recebidas[0].largura_mm == 30.0
    assert declarada_b.faixas_recebidas[0].largura_mm == 20.0
    # 100 - (30 + 20) - 2 respiros de 5 = 40.
    assert elastica.faixas_recebidas[0].largura_mm == 40.0


# ---------------------------------------------------------------------------
# Ordem: esquerda para a direita, com respiro entre as marcas
# ---------------------------------------------------------------------------


def test_grupo_reparte_da_esquerda_para_a_direita_com_respiro() -> None:
    primeira = _marca(largura_mm=30.0)
    segunda = _marca(largura_mm=20.0)
    terceira = _marca(largura_mm=10.0)
    grupo = MarcasLadoALado((primeira, segunda, terceira), Posicao.SUPERIOR, respiro_mm=4.0)
    # Largura exata do que o grupo pede: 30 + 20 + 10 + 2 respiros de 4 = 68.
    faixa = Faixa(esquerda_mm=5.0, topo_mm=0.0, largura_mm=68.0, altura_mm=10.0)

    grupo(faixa, _folha(A4.orientar(Orientacao.RETRATO)))

    faixa_1 = primeira.faixas_recebidas[0]
    faixa_2 = segunda.faixas_recebidas[0]
    faixa_3 = terceira.faixas_recebidas[0]
    assert faixa_1.esquerda_mm == 5.0
    assert faixa_2.esquerda_mm == faixa_1.esquerda_mm + faixa_1.largura_mm + 4.0
    assert faixa_3.esquerda_mm == faixa_2.esquerda_mm + faixa_2.largura_mm + 4.0
    # A última encosta exatamente na borda direita da faixa do grupo.
    assert faixa_3.esquerda_mm + faixa_3.largura_mm == faixa.esquerda_mm + faixa.largura_mm


# ---------------------------------------------------------------------------
# Recusa na construção: duas elásticas, ou grupo vazio
# ---------------------------------------------------------------------------


def test_grupo_com_duas_elasticas_ou_vazio_eh_recusado() -> None:
    with pytest.raises(ValueError):
        MarcasLadoALado((), Posicao.SUPERIOR, respiro_mm=0.0)
    with pytest.raises(ValueError):
        MarcasLadoALado(
            (_marca(largura_mm=None), _marca(largura_mm=None)),
            Posicao.SUPERIOR,
            respiro_mm=0.0,
        )


# ---------------------------------------------------------------------------
# Recusa ao pintar: larguras declaradas que não cabem na faixa
# ---------------------------------------------------------------------------


def test_larguras_que_nao_cabem_sao_recusadas_dizendo_quanto_falta() -> None:
    grupo = MarcasLadoALado(
        (_marca(largura_mm=60.0), _marca(largura_mm=60.0)),
        Posicao.SUPERIOR,
        respiro_mm=5.0,
    )
    # Pede 60 + 60 + 5 = 125 numa faixa de 100: faltam 25.
    faixa = Faixa(esquerda_mm=0.0, topo_mm=0.0, largura_mm=100.0, altura_mm=10.0)

    with pytest.raises(ValueError, match="25.0"):
        grupo(faixa, _folha(A4.orientar(Orientacao.RETRATO)))


# ---------------------------------------------------------------------------
# Alinhamento vertical: cada marca encosta no topo da faixa do grupo
# ---------------------------------------------------------------------------


def test_marcas_do_grupo_encostam_no_topo_da_faixa() -> None:
    baixa = _marca(altura_mm=5.0, largura_mm=20.0)
    alta = _marca(altura_mm=15.0, largura_mm=20.0)
    grupo = MarcasLadoALado((baixa, alta), Posicao.SUPERIOR, respiro_mm=0.0)
    faixa = Faixa(esquerda_mm=0.0, topo_mm=12.0, largura_mm=40.0, altura_mm=15.0)

    grupo(faixa, _folha(A4.orientar(Orientacao.RETRATO)))

    assert baixa.faixas_recebidas[0].topo_mm == 12.0
    assert baixa.faixas_recebidas[0].altura_mm == 5.0
    assert alta.faixas_recebidas[0].topo_mm == 12.0
    assert alta.faixas_recebidas[0].altura_mm == 15.0


# ---------------------------------------------------------------------------
# Artefato: grupo de três marcas cercado por moldura, para conferência visual
# ---------------------------------------------------------------------------


class _MarcaTexto(Marca):
    """Só para o artefato de conferência: escreve o próprio rótulo, sem depender de domínio algum."""

    posicao = Posicao.SUPERIOR

    def __init__(self, rotulo: str, altura_mm: float, largura_mm: float | None = None) -> None:
        self._rotulo = rotulo
        self.altura_mm = altura_mm
        self.largura_mm = largura_mm

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        folha.texto(faixa.esquerda_mm, faixa.topo_mm + self.altura_mm, self._rotulo, ESTILO_TEXTO_ROTULO)


class _GrupoComMoldura(Marca):
    """A combinação que a SPEC 005 existe para permitir sem repartição escrita à mão: o grupo
    lado a lado por dentro, o contorno na mesma faixa por fora."""

    posicao = Posicao.SUPERIOR

    def __init__(self, grupo: MarcasLadoALado, estilo: EstiloTraco) -> None:
        self._grupo = grupo
        self._estilo = estilo
        self.altura_mm = grupo.altura_mm

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        self._grupo(faixa, folha)
        folha.retangulo(
            faixa.esquerda_mm,
            faixa.topo_mm,
            faixa.largura_mm,
            faixa.altura_mm,
            self._estilo,
        )


@pytest.mark.artefato
def test_amostra_com_grupo_lado_a_lado_e_moldura(
    publicar_artefato: Callable[[str, bytes], Path],
) -> None:
    grupo = MarcasLadoALado(
        (
            _MarcaTexto("ESQUERDA", altura_mm=12.0, largura_mm=40.0),
            _MarcaTexto("CENTRO (elástica)", altura_mm=12.0, largura_mm=None),
            _MarcaTexto("DIREITA", altura_mm=12.0, largura_mm=30.0),
        ),
        Posicao.SUPERIOR,
        respiro_mm=4.0,
    )
    estilo_traco = EstiloTraco(cor=HexColor("#336633"), espessura_mm=0.5)
    marcacao = Marcacao(
        marcas=(_GrupoComMoldura(grupo, estilo_traco),),
        margem_lateral_mm=20.0,
        margem_vertical_mm=15.0,
        respiro_mm=6.0,
    )
    corpo = (Paragraph("Corpo do documento de conferência.", ESTILO_NORMAL),)

    pdf = gerar_pdf(
        DocumentoPdfInput(
            titulo="Grupo lado a lado com moldura",
            corpo=corpo,
            marcacao=MarcacaoDocumento(principal=marcacao),
        )
    )

    caminho = publicar_artefato("marcas_lado_a_lado_e_moldura.pdf", pdf)
    assert caminho.stat().st_size > 0


# ---------------------------------------------------------------------------
# Artefato: texto e QR nas duas ordens possíveis, e um selo de assinatura
# ---------------------------------------------------------------------------


class _MarcaLinhas(Marca):
    """Só para o artefato: várias linhas empilhadas dentro da própria faixa horizontal."""

    posicao = Posicao.SUPERIOR

    def __init__(
        self,
        linhas: tuple[str, ...],
        altura_mm: float,
        entrelinha_mm: float,
        largura_mm: float | None = None,
    ) -> None:
        self._linhas = linhas
        self._entrelinha_mm = entrelinha_mm
        self.altura_mm = altura_mm
        self.largura_mm = largura_mm

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        for numero, linha in enumerate(self._linhas, start=1):
            folha.texto(
                faixa.esquerda_mm,
                faixa.topo_mm + numero * self._entrelinha_mm,
                linha,
                ESTILO_TEXTO_ROTULO,
            )


class _MarcaQr(Marca):
    """Só para o artefato: QR real, do mesmo utilitário que os documentos oficiais usam."""

    posicao = Posicao.SUPERIOR

    def __init__(self, conteudo: str, largura_mm: float) -> None:
        self._vetor = qr_code_pdf(
            QrCodePdfInput(simbolo=gerar_qr_code(QrCodeInput(conteudo=conteudo)), largura_mm=largura_mm)
        )
        self.altura_mm = self._vetor.desenho.height / mm
        self.largura_mm = self._vetor.desenho.width / mm

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        folha.vetor(faixa.esquerda_mm, faixa.topo_mm, self._vetor)


@pytest.mark.artefato
def test_amostra_com_texto_e_qr_nas_duas_ordens_e_selo_de_assinatura(
    publicar_artefato: Callable[[str, bytes], Path],
) -> None:
    respiro_mm = 6.0
    entrelinha_mm = 5.0
    estilo_traco = EstiloTraco(cor=HexColor("#336633"), espessura_mm=0.5)

    qr_bloco_1 = _MarcaQr("https://exemplo.sp.gov.br/verificar/1", largura_mm=40.0)
    texto_a_esquerda_qr_a_direita = MarcasLadoALado(
        (
            _MarcaLinhas(
                ("Bloco 1 — texto à esquerda,", "QR grande à direita."),
                altura_mm=qr_bloco_1.altura_mm,
                entrelinha_mm=entrelinha_mm,
            ),
            qr_bloco_1,
        ),
        Posicao.SUPERIOR,
        respiro_mm=respiro_mm,
    )

    qr_bloco_2 = _MarcaQr("https://exemplo.sp.gov.br/verificar/2", largura_mm=40.0)
    qr_a_esquerda_texto_a_direita = MarcasLadoALado(
        (
            qr_bloco_2,
            _MarcaLinhas(
                ("Bloco 2 — QR à esquerda,", "texto à direita."),
                altura_mm=qr_bloco_2.altura_mm,
                entrelinha_mm=entrelinha_mm,
            ),
        ),
        Posicao.SUPERIOR,
        respiro_mm=respiro_mm,
    )

    qr_bloco_3 = _MarcaQr("https://exemplo.sp.gov.br/verificar/3", largura_mm=30.0)
    grupo_da_assinatura = MarcasLadoALado(
        (
            qr_bloco_3,
            _MarcaLinhas(
                (
                    "Bloco 3 — QR e texto dentro",
                    "da mesma moldura: assinado",
                    "digitalmente por Fulano de Tal,",
                    "matrícula 12345, em 07/09/2026 14:32.",
                ),
                altura_mm=qr_bloco_3.altura_mm,
                entrelinha_mm=entrelinha_mm,
            ),
        ),
        Posicao.SUPERIOR,
        respiro_mm=respiro_mm,
    )
    # A moldura cerca o GRUPO inteiro — QR e texto por dentro da mesma faixa —, e não só o QR: é
    # isso que faz o selo de assinatura ler como uma peça só.
    selo_de_assinatura = _GrupoComMoldura(grupo_da_assinatura, estilo_traco)

    marcacao = Marcacao(
        marcas=(texto_a_esquerda_qr_a_direita, qr_a_esquerda_texto_a_direita, selo_de_assinatura),
        margem_lateral_mm=20.0,
        margem_vertical_mm=15.0,
        respiro_mm=respiro_mm,
    )
    corpo = (Paragraph("Corpo do documento de conferência.", ESTILO_NORMAL),)

    pdf = gerar_pdf(
        DocumentoPdfInput(
            titulo="Texto e QR nas duas ordens, e selo de assinatura",
            corpo=corpo,
            marcacao=MarcacaoDocumento(principal=marcacao),
        )
    )

    caminho = publicar_artefato("texto_e_qr_com_selo_de_assinatura.pdf", pdf)
    assert caminho.stat().st_size > 0
