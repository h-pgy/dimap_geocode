"""Testes de services/domain/certidao_lancamento/certidao (SPEC certidao_lancamento/001): a
composição da declaração de existência de lançamento (dados relacionados, despacho do tipo escolhido,
ressalva e observações, planta opcional, rodapé com instante da consulta e amostra de artefato).
"""

from collections.abc import Callable
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image as PILImage, ImageDraw
from pydantic import ValidationError
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
    SentidoDespacho,
    TipoDespacho,
)
from services.domain.documento_oficial import (
    ConteudoDocumento,
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


def _pedido(**overrides: object) -> PedidoCertidao:
    defaults: dict[str, object] = {
        "processo": "6017.2026/0012345-6",
        "interessado": "Maria Salgado",
        "sentido": SentidoDespacho.DEFERIDO,
        "tipo_despacho": TipoDespacho.POSSUI_LANCAMENTO,
    }
    return PedidoCertidao(**(defaults | overrides))  # type: ignore[arg-type]


def _tipo_do_sentido(sentido: SentidoDespacho) -> TipoDespacho:
    return next(tipo for tipo in TipoDespacho if tipo.sentido is sentido)


def _certidao_input(
    pedido: PedidoCertidao | None = None,
    imovel: LoteAttributes | None = None,
    planta: PlantaLocalizacao | None = None,
) -> CertidaoLancamentoInput:
    return CertidaoLancamentoInput(
        envelope=_envelope(),
        pedido=pedido or _pedido(),
        imovel=imovel or _imovel(),
        planta=planta,
        consultado_em=datetime(2026, 9, 22, 14, 30, tzinfo=ZoneInfo("America/Sao_Paulo")),
        base_url="https://geocoder.dimap.pmsp/",
    )


def _conteudo(certidao: CertidaoLancamentoInput) -> ConteudoDocumento:
    return MontarCertidaoLancamento()(
        MontarCertidaoLancamentoInput(
            certidao=certidao,
            selo=_selo(certidao.envelope),
            quadro=SeloConfig().fecho,
        )
    )


def _textos(conteudo: ConteudoDocumento) -> list[str]:
    return [bloco.texto for bloco in conteudo.blocos if isinstance(bloco, Paragrafo)]


def _indice_do_despacho(textos: list[str]) -> int:
    return next(i for i, texto in enumerate(textos) if texto.startswith("Solicitação "))


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


def test_montar_certidao_declara_dados_e_despacho_do_tipo() -> None:
    certidao = _certidao_input(
        pedido=_pedido(interessado="Maria Salgado", cpf_cnpj="123.456.789-09"),
        imovel=_imovel(
            nome_logradouro="AV PAULISTA",
            numero_porta="100",
            codlog="123450",
            complemento="SALA 12",
        ),
    )

    conteudo = _conteudo(certidao)

    assert conteudo.titulo == (
        "Declaração de Existência/Inexistência de Lançamento Fiscal e Inscrição no Cadastro "
        "Imobiliário Fiscal – IPTU"
    )
    assert conteudo.nome_arquivo == f"certidao_lancamento_{certidao.envelope.codigo}.pdf"
    subtitulos = [b.texto for b in conteudo.blocos if isinstance(b, Subtitulo)]
    assert subtitulos[:2] == ["Dados relacionados à declaração", "Despacho"]
    assert any(isinstance(b, SeloDeFecho) for b in conteudo.blocos)

    # Dados relacionados: imóvel com codlog-DV, interessado com o CPF/CNPJ, processo e data
    textos = _textos(conteudo)
    assert "Identificação do imóvel: AV PAULISTA (codlog: 12345-0), número 100, complemento SALA 12." in textos
    assert "Nome do interessado: Maria Salgado (CPF/CNPJ: 123.456.789-09)" in textos
    assert "Processo SEI nº: 6017.2026/0012345-6" in textos
    assert "Data da declaração: 22/09/2026" in textos

    # Sem CPF/CNPJ, o interessado sai só pelo nome, sem parêntese vazio
    sem_documento = _textos(_conteudo(_certidao_input()))
    assert "Nome do interessado: Maria Salgado" in sem_documento

    # O texto do modelo, transcrito, para um tipo de cada sentido
    deferido = _textos(_conteudo(_certidao_input()))
    assert deferido[_indice_do_despacho(deferido)] == (
        "Solicitação DEFERIDA. Com base nas informações presentes no processo, declara-se que o imóvel "
        "possui lançamento do Imposto Predial e Territorial Urbano – IPTU – pelo contribuinte número "
        "005.003.0048-5."
    )
    indeferido = _textos(
        _conteudo(
            _certidao_input(
                pedido=_pedido(
                    sentido=SentidoDespacho.INDEFERIDO,
                    tipo_despacho=TipoDespacho.IMOVEL_NAO_LOCALIZADO,
                )
            )
        )
    )
    assert indeferido[_indice_do_despacho(indeferido)] == (
        "Solicitação INDEFERIDA. Com base nas informações presentes no processo, declara-se que não foi "
        "possível a localização do imóvel, já que as informações constantes no processo não são "
        "suficientes para a sua identificação inequívoca."
    )

    # Todos os tipos: a abertura sai do sentido, e só o deferimento cita o SQL
    for tipo in TipoDespacho:
        textos_do_tipo = _textos(
            _conteudo(_certidao_input(pedido=_pedido(sentido=tipo.sentido, tipo_despacho=tipo)))
        )
        despacho = textos_do_tipo[_indice_do_despacho(textos_do_tipo)]
        abertura = "DEFERIDA" if tipo.sentido is SentidoDespacho.DEFERIDO else "INDEFERIDA"
        assert despacho.startswith(f"Solicitação {abertura}. Com base nas informações presentes no processo, declara-se que")
        assert ("005.003.0048-5" in despacho) is (tipo.sentido is SentidoDespacho.DEFERIDO)


def test_despacho_poe_ressalva_e_observacoes_antes_da_validade() -> None:
    completo = _textos(
        _conteudo(
            _certidao_input(
                pedido=_pedido(incluir_ressalva=True, observacoes="Vistoria anexada ao processo.")
            )
        )
    )

    despacho = _indice_do_despacho(completo)
    assert completo[despacho + 1].startswith("Ressalta-se que a análise tem como base somente a situação factual")
    assert completo[despacho + 2] == "Vistoria anexada ao processo."
    assert completo[despacho + 3].startswith(
        "As informações prestadas nos termos deste despacho serão válidas por 90 (noventa) dias"
    )

    # Ressalva desmarcada e sem observações: a validade segue direto o despacho
    enxuto = _textos(_conteudo(_certidao_input(pedido=_pedido(incluir_ressalva=False))))
    assert not any(texto.startswith("Ressalta-se") for texto in enxuto)
    assert enxuto[_indice_do_despacho(enxuto) + 1].startswith("As informações prestadas nos termos")


def test_planta_segue_o_pedido_e_nota_com_instante_da_consulta() -> None:
    planta_png = b"\x89PNG\r\n\x1a\nfake-planta"

    for sentido in SentidoDespacho:
        pedido = {"sentido": sentido, "tipo_despacho": _tipo_do_sentido(sentido)}

        com_mapa = _conteudo(
            _certidao_input(
                pedido=_pedido(**pedido, incluir_planta=True),
                planta=_planta(png=planta_png),
            )
        )
        raster = next(b for b in com_mapa.blocos if isinstance(b, ImagemRaster))
        assert raster.largura_mm == 150.0
        assert raster.conteudo == planta_png
        assert "Localização do Imóvel" in [b.texto for b in com_mapa.blocos if isinstance(b, Subtitulo)]

        # Sem o mapa, a seção some inteira: nem imagem, nem subtítulo solto
        sem_mapa = _conteudo(_certidao_input(pedido=_pedido(**pedido, incluir_planta=False)))
        assert not any(isinstance(b, ImagemRaster) for b in sem_mapa.blocos)
        assert "Localização do Imóvel" not in [b.texto for b in sem_mapa.blocos if isinstance(b, Subtitulo)]

    # O pedido manda: planta que ele não inclui e mapa sem planta são recusados
    with pytest.raises(ValidationError):
        _certidao_input(pedido=_pedido(incluir_planta=False), planta=_planta())
    with pytest.raises(ValidationError):
        _certidao_input(pedido=_pedido(incluir_planta=True), planta=None)

    # A nota do rodapé declara a emissão automatizada e o instante da leitura do lote
    renderizado = _tipo_certidao()(_certidao_input())
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
    imovel = _imovel(
        nome_logradouro="AV PAULISTA",
        numero_porta="100",
        codlog="123450",
        complemento="APTO 42",
    )
    deferimento = _certidao_input(
        pedido=_pedido(
            interessado="Maria Salgado de Almeida",
            cpf_cnpj="123.456.789-09",
            incluir_ressalva=True,
            incluir_planta=True,
            observacoes="Vistoria realizada no processo 6017.2026/0012345-6.",
        ),
        imovel=imovel,
        planta=planta,
    )
    indeferimento = _certidao_input(
        pedido=_pedido(
            interessado="Maria Salgado de Almeida",
            sentido=SentidoDespacho.INDEFERIDO,
            tipo_despacho=TipoDespacho.IMOVEL_NAO_LOCALIZADO,
        ),
        imovel=imovel,
    )

    deferida = publicar_artefato(
        "certidao_lancamento_deferimento_com_planta.pdf",
        _tipo_certidao()(deferimento).pdf,
    )
    indeferida = publicar_artefato(
        "certidao_lancamento_indeferimento_sem_planta.pdf",
        _tipo_certidao()(indeferimento).pdf,
    )

    for caminho in (deferida, indeferida):
        assert caminho.exists()
        assert caminho.stat().st_size > 0
