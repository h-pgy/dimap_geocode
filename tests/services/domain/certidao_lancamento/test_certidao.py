"""Testes de services/domain/certidao_lancamento/certidao.py (SPEC certidao_lancamento/001):
a composição da Certidão de Existência de Lançamento (título, requerimento, identificação do imóvel,
despacho com fundamentação e SQL, planta raster, rodapé com instante da consulta e amostra de artefato).
"""

from collections.abc import Callable
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image as PILImage, ImageDraw
from pypdf import PdfReader
import pytest

from services.domain.certidao_lancamento.certidao import (
    CertidaoLancamento,
    MontarCertidaoLancamento,
    MontarCertidaoLancamentoInput,
)
from services.domain.certidao_lancamento.models import (
    CertidaoLancamentoInput,
    PedidoCertidao,
)
from services.domain.documento_oficial import (
    ImagemRaster,
    MarcacaoConfig,
    Paragrafo,
    SeloConfig,
    SeloDeFecho,
    Subtitulo,
    montar_tema,
)
from services.domain.documento_oficial.models import TemaConfig
from services.domain.documento_selado import (
    AlvoDoAto,
    AutorDoAto,
    EnvelopeAto,
    SeloImpresso,
    SeloImpressoInput,
    montar_selo_impresso,
)
from services.domain.geometry import PolygonGeometry
from services.domain.lote_geocod.models import LoteAttributes
from services.domain.planta_localizacao import (
    CamadaPlanta,
    EstiloGeometria,
    GerarPlantaLocalizacao,
    PlantaConfig,
    PlantaLocalizacao,
    PlantaLocalizacaoInput,
)
from services.integrations.wms.models import BoundingBox, WmsImage, WmsMapRequest

artefato = pytest.mark.artefato


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _envelope(**overrides: object) -> EnvelopeAto:
    defaults: dict[str, object] = {
        "codigo": "7K9M2X4P8QRT",
        "acao": "certidao_lancamento.emitir",
        "operacao": "emitir",
        "autor": AutorDoAto(
            nome="Marina Salgado de Almeida",
            unidade="DIMAP-1",
            cargo_base="Analista de Ordenamento Territorial",
            cargo_comissao="Diretora de Divisão",
        ),
        "alvo": AlvoDoAto(tipo="lote", identificador="005.003.0048-5"),
        "emitido_em": "2026-09-22T14:30:00Z",
        "campos_publicos": ("contribuinte", "processo"),
        "extras": {
            "contribuinte": "005.003.0048-5",
            "processo": "6017.2026/0012345-6",
        },
    }
    return EnvelopeAto(**(defaults | overrides))  # type: ignore[arg-type]


def _imovel(**overrides: object) -> LoteAttributes:
    defaults: dict[str, object] = {
        "id_poligono": "1001",
        "setor": "005",
        "quadra": "003",
        "lote": "0048",
        "tipo_lote": "F",
        "digito": "5",
        "codlog": "123450",
        "nome_logradouro": "AV PAULISTA",
        "numero_porta": "100",
        "complemento": None,
        "situacao": "ATIVO",
        "condominio": "00",
    }
    return LoteAttributes(**(defaults | overrides))  # type: ignore[arg-type]


def _selo(envelope: EnvelopeAto, base_url: str = "https://geocoder.dimap.pmsp/") -> SeloImpresso:
    return montar_selo_impresso(SeloImpressoInput(envelope=envelope, base_url=base_url))


PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99"
    b"=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _planta(png: bytes = PNG_1X1) -> PlantaLocalizacao:
    enquadramento = BoundingBox(
        minx=0.0,
        miny=0.0,
        maxx=100.0,
        maxy=100.0,
        crs="EPSG:31983",
    )
    return PlantaLocalizacao(png=png, enquadramento=enquadramento)


def _quadra(leste: float, norte: float, largura: float, fundo: float) -> PolygonGeometry:
    anel = [
        [leste, norte],
        [leste + largura, norte],
        [leste + largura, norte + fundo],
        [leste, norte + fundo],
        [leste, norte],
    ]
    return PolygonGeometry(type="Polygon", coordinates=[anel])


# Quadra fictícia em SIRGAS 2000 / UTM 23S: o lote certificado e os vizinhos que o situam.
_LOTE_CERTIFICADO = _quadra(333_040.0, 7_394_010.0, 12.0, 30.0)
_LOTES_VIZINHOS = (
    _quadra(333_022.0, 7_394_010.0, 16.0, 30.0),
    _quadra(333_054.0, 7_394_010.0, 14.0, 30.0),
    _quadra(333_022.0, 7_393_966.0, 46.0, 30.0),
)


def _ortofoto_sintetica(req: WmsMapRequest) -> WmsImage:
    """Fundo procedural no lugar do GeoSampa: a amostra precisa rodar sem rede, e o que se confere
    nela é o desenho da planta sobre um raster, não a fidelidade da imagem aérea."""
    lado = req.width or 1600
    imagem = PILImage.new("RGB", (lado, lado), (126, 132, 116))
    pincel = ImageDraw.Draw(imagem)
    passo = lado // 16
    for indice in range(0, lado, passo):
        tom = 104 + (indice // passo % 5) * 9
        pincel.rectangle([indice, 0, indice + passo // 2, lado], fill=(tom, tom + 6, tom - 12))
    # Duas faixas claras cruzando: leem-se como o arruamento sob os polígonos.
    pincel.rectangle([0, lado // 2 - 14, lado, lado // 2 + 14], fill=(158, 154, 148))
    pincel.rectangle([lado // 2 - 12, 0, lado // 2 + 12, lado], fill=(158, 154, 148))
    buffer = BytesIO()
    imagem.save(buffer, format="PNG")
    return WmsImage(
        content=buffer.getvalue(),
        content_type="image/png",
        width=lado,
        height=lado,
        layer=req.layer,
        bbox=req.bbox,
    )


def _tipo_certidao() -> CertidaoLancamento:
    config = MarcacaoConfig(
        logo_horizontal=Path("static/src/img/documento_oficial/sec_fazenda_horizontal.svg"),
        logo_vertical=Path("static/src/img/documento_oficial/sec_fazenda_vertical.svg"),
    )
    return CertidaoLancamento(
        tema=montar_tema(TemaConfig()),
        config=config,
        selo_config=SeloConfig(),
    )


# ---------------------------------------------------------------------------
# Testes de comportamento (SPEC 001 §8)
# ---------------------------------------------------------------------------


def test_montar_certidao_declara_requerimento_identificacao_e_despacho() -> None:
    envelope = _envelope()
    pedido = PedidoCertidao(processo="6017.2026/0012345-6", interessado="Maria Salgado")
    imovel = _imovel(
        nome_logradouro="AV PAULISTA",
        numero_porta="100",
        codlog="123450",
        complemento="SALA 12",
    )
    momento_consulta = datetime(2026, 9, 22, 14, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))
    certidao_input = CertidaoLancamentoInput(
        envelope=envelope,
        pedido=pedido,
        imovel=imovel,
        planta=_planta(),
        consultado_em=momento_consulta,
        base_url="https://geocoder.dimap.pmsp/",
    )
    selo = _selo(envelope)
    quadro = SeloConfig().fecho

    montador = MontarCertidaoLancamento()
    conteudo = montador(MontarCertidaoLancamentoInput(
        certidao=certidao_input,
        selo=selo,
        quadro=quadro,
    ))

    assert conteudo.titulo == "Certidão de Existência de Lançamento"
    assert conteudo.nome_arquivo == f"certidao_lancamento_{envelope.codigo}.pdf"

    # Requerimento
    paragrafos = [b.texto for b in conteudo.blocos if isinstance(b, Paragrafo)]
    assert any("Interessado: Maria Salgado. Processo SEI nº 6017.2026/0012345-6." in t for t in paragrafos)

    # Identificação do imóvel com codlog e complemento
    assert any("AV PAULISTA (codlog: 12345-0), número 100, complemento SALA 12." in t for t in paragrafos)

    # Despacho e fundamentação com SQL
    assert any("Solicitação deferida." in t for t in paragrafos)
    assert any(
        "declara-se que o imóvel acima identificado possui lançamento do Imposto Predial e Territorial Urbano (IPTU) pelo contribuinte número 005.003.0048-5."
        in t
        for t in paragrafos
    )

    # Subtítulos da estrutura
    subtitulos = [b.texto for b in conteudo.blocos if isinstance(b, Subtitulo)]
    assert "Requerimento" in subtitulos
    assert "Identificação do Imóvel" in subtitulos
    assert "Despacho" in subtitulos
    assert "Localização do Imóvel" in subtitulos

    # Selo de fecho
    assert any(isinstance(b, SeloDeFecho) for b in conteudo.blocos)


def test_certidao_traz_planta_raster_na_largura_pedida() -> None:
    envelope = _envelope()
    pedido = PedidoCertidao(processo="6017.2026/0012345-6", interessado="Maria Salgado")
    imovel = _imovel()
    planta_png = b"\x89PNG\r\n\x1a\nfake-planta"
    planta = _planta(png=planta_png)
    momento_consulta = datetime(2026, 9, 22, 14, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))

    certidao_input = CertidaoLancamentoInput(
        envelope=envelope,
        pedido=pedido,
        imovel=imovel,
        planta=planta,
        consultado_em=momento_consulta,
        base_url="https://geocoder.dimap.pmsp/",
    )

    montador = MontarCertidaoLancamento()
    conteudo = montador(MontarCertidaoLancamentoInput(
        certidao=certidao_input,
        selo=_selo(envelope),
        quadro=SeloConfig().fecho,
    ))

    raster = next(b for b in conteudo.blocos if isinstance(b, ImagemRaster))
    assert raster.largura_mm == 150.0
    assert raster.conteudo == planta_png


def test_rodape_declara_emissao_automatizada_e_instante_da_consulta() -> None:
    envelope = _envelope()
    certidao_input = CertidaoLancamentoInput(
        envelope=envelope,
        pedido=PedidoCertidao(
            processo="6017.2026/0012345-6",
            interessado="Maria Salgado",
        ),
        imovel=_imovel(),
        planta=_planta(),
        consultado_em=datetime(2026, 9, 22, 14, 30, tzinfo=ZoneInfo("America/Sao_Paulo")),
        base_url="https://geocoder.dimap.pmsp/",
    )

    renderizado = _tipo_certidao()(certidao_input)

    texto = PdfReader(BytesIO(renderizado.pdf)).pages[0].extract_text()
    assert "de forma automatizada" in texto
    assert "22/09/2026" in texto
    assert "14:30" in texto


@artefato
def test_amostra_certidao_de_lancamento(
    publicar_artefato: Callable[[str, bytes], Path],
) -> None:
    # A planta sai do pipeline de verdade (`GerarPlantaLocalizacao`), não de bytes fabricados: a
    # amostra só serve para conferir a olho se for a saída que o sistema produz.
    planta = GerarPlantaLocalizacao(ortofoto=_ortofoto_sintetica)(
        PlantaLocalizacaoInput(
            camadas=(
                CamadaPlanta(geometrias=_LOTES_VIZINHOS, estilo=EstiloGeometria.CONTEXTO),
                CamadaPlanta(geometrias=(_LOTE_CERTIFICADO,), estilo=EstiloGeometria.DESTAQUE),
            ),
            config=PlantaConfig(camada_ortofoto="geoportal:ORTO_RGB", crs=31983),
        )
    )
    certidao_input = CertidaoLancamentoInput(
        envelope=_envelope(),
        pedido=PedidoCertidao(
            processo="6017.2026/0012345-6",
            interessado="Maria Salgado de Almeida",
        ),
        imovel=_imovel(
            nome_logradouro="AV PAULISTA",
            numero_porta="100",
            codlog="123450",
            complemento="APTO 42",
        ),
        planta=planta,
        consultado_em=datetime(2026, 9, 22, 14, 30, tzinfo=ZoneInfo("America/Sao_Paulo")),
        base_url="https://geocoder.dimap.pmsp/",
    )

    renderizado = _tipo_certidao()(certidao_input)
    caminho = publicar_artefato("certidao_lancamento_amostra.pdf", renderizado.pdf)

    assert caminho.exists()
    assert caminho.stat().st_size > 0
