"""Testes de services/domain/certidao_lancamento/certidao.py (SPEC certidao_lancamento/001):
a composição da Certidão de Existência de Lançamento (título, requerimento, identificação do imóvel,
despacho com fundamentação e SQL, planta raster, rodapé com instante da consulta e amostra de artefato).
"""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from services.domain.documento_oficial import (
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
from services.domain.lote_geocod.models import LoteAttributes

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


def _planta(png: bytes = b"\x89PNG\r\n\x1a\nfake-planta") -> MagicMock:
    planta = MagicMock()
    planta.png = png
    return planta


# ---------------------------------------------------------------------------
# Testes de comportamento (SPEC 001 §8)
# ---------------------------------------------------------------------------


def test_montar_certidao_declara_requerimento_identificacao_e_despacho() -> None:
    from services.domain.certidao_lancamento.certidao import (  # type: ignore[import-not-found]
        MontarCertidaoLancamento,
        MontarCertidaoLancamentoInput,
    )
    from services.domain.certidao_lancamento.models import (  # type: ignore[import-not-found]
        CertidaoLancamentoInput,
        PedidoCertidao,
    )

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


def test_certidao_traz_planta_e_nota_com_instante_da_consulta() -> None:
    from services.domain.certidao_lancamento.certidao import (  # type: ignore[import-not-found]
        CertidaoLancamento,
        MontarCertidaoLancamento,
        MontarCertidaoLancamentoInput,
    )
    from services.domain.certidao_lancamento.models import (  # type: ignore[import-not-found]
        CertidaoLancamentoInput,
        PedidoCertidao,
    )

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

    # Verifica a presença da planta raster
    raster = next(
        b for b in conteudo.blocos
        if getattr(b, "tipo", None) == "imagem_raster" or b.__class__.__name__ == "ImagemRaster"
    )
    assert getattr(raster, "largura_mm") == 150.0
    assert getattr(raster, "conteudo") == planta_png

    # Verifica a nota de rodapé com o instante da consulta cadastral
    tema = montar_tema(TemaConfig())
    config = MarcacaoConfig(
        logo_horizontal=Path("static/src/img/documento_oficial/sec_fazenda_horizontal.svg"),
        logo_vertical=Path("static/src/img/documento_oficial/sec_fazenda_vertical.svg"),
    )
    tipo = CertidaoLancamento(tema=tema, config=config, selo_config=SeloConfig())
    nota = tipo._nota(certidao_input)
    assert nota == (
        "Certidão emitida de forma automática",
        "Dados cadastrais consultados em 22/09/2026 - 14:30 no GeoSampa",
    )


@artefato
def test_amostra_certidao_de_lancamento(
    publicar_artefato: Callable[[str, bytes], Path],
) -> None:
    from services.domain.certidao_lancamento.certidao import CertidaoLancamento  # type: ignore[import-not-found]
    from services.domain.certidao_lancamento.models import (  # type: ignore[import-not-found]
        CertidaoLancamentoInput,
        PedidoCertidao,
    )

    # PNG 1x1 mínimo válido para o motor de PDF renderizar sem erro
    png_minimo = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
        b"\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99"
        b"=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    tema = montar_tema(TemaConfig())
    config = MarcacaoConfig(
        logo_horizontal=Path("static/src/img/documento_oficial/sec_fazenda_horizontal.svg"),
        logo_vertical=Path("static/src/img/documento_oficial/sec_fazenda_vertical.svg"),
    )
    tipo = CertidaoLancamento(tema=tema, config=config, selo_config=SeloConfig())

    envelope = _envelope()
    pedido = PedidoCertidao(processo="6017.2026/0012345-6", interessado="Maria Salgado de Almeida")
    imovel = _imovel(
        nome_logradouro="AV PAULISTA",
        numero_porta="100",
        codlog="123450",
        complemento="APTO 42",
    )
    certidao_input = CertidaoLancamentoInput(
        envelope=envelope,
        pedido=pedido,
        imovel=imovel,
        planta=_planta(png=png_minimo),
        consultado_em=datetime(2026, 9, 22, 14, 30, tzinfo=ZoneInfo("America/Sao_Paulo")),
        base_url="https://geocoder.dimap.pmsp/",
    )

    renderizado = tipo.pipeline(certidao_input)
    caminho = publicar_artefato("certidao_lancamento_amostra.pdf", renderizado.pdf)

    assert caminho.exists()
    assert caminho.stat().st_size > 0
