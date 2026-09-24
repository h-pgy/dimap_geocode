"""Testes de services/domain/certidao_lancamento/models.py (SPEC certidao_lancamento/001):
validação do pedido (processo SEI e interessado) e restrições de admissibilidade do lote
para emissão da certidão (recusa de lote sem lançamento ou condominial).
"""

from datetime import datetime, timezone

from pydantic import ValidationError
import pytest

from services.domain.certidao_lancamento.models import (
    CertidaoLancamentoInput,
    PedidoCertidao,
)
from services.domain.documento_selado import AlvoDoAto, AutorDoAto, EnvelopeAto
from services.domain.lote_geocod.models import LoteAttributes
from services.domain.planta_localizacao import PlantaLocalizacao
from services.integrations.wms.models import BoundingBox


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


def _planta() -> PlantaLocalizacao:
    enquadramento = BoundingBox(
        minx=0.0,
        miny=0.0,
        maxx=100.0,
        maxy=100.0,
        crs="EPSG:31983",
    )
    return PlantaLocalizacao(png=b"\x89PNG\r\n\x1a\n", enquadramento=enquadramento)


# ---------------------------------------------------------------------------
# Validação do PedidoCertidao
# ---------------------------------------------------------------------------


def test_pedido_recusa_processo_fora_do_formato_sei() -> None:
    # Formato completo aceito
    pedido = PedidoCertidao(
        processo="6017.2026/0012345-6",
        interessado="Secretaria Municipal da Fazenda",
    )
    assert pedido.processo == "6017.2026/0012345-6"
    assert pedido.interessado == "Secretaria Municipal da Fazenda"

    # Formatos incorretos de processo SEI
    with pytest.raises(ValidationError):
        PedidoCertidao(processo="6017.2026/123-4", interessado="Secretaria Municipal da Fazenda")

    with pytest.raises(ValidationError):
        PedidoCertidao(processo="processo sei livre", interessado="Secretaria Municipal da Fazenda")

    with pytest.raises(ValidationError):
        PedidoCertidao(processo="6017.2026/00123456", interessado="Secretaria Municipal da Fazenda")

    with pytest.raises(ValidationError):
        PedidoCertidao(processo="6017-2026/0012345-6", interessado="Secretaria Municipal da Fazenda")

    # Interessado inválido (em branco ou curto demais)
    with pytest.raises(ValidationError):
        PedidoCertidao(processo="6017.2026/0012345-6", interessado="")

    with pytest.raises(ValidationError):
        PedidoCertidao(processo="6017.2026/0012345-6", interessado="ab")

    with pytest.raises(ValidationError):
        PedidoCertidao(processo="6017.2026/0012345-6", interessado="   ")


# ---------------------------------------------------------------------------
# Restrições de Admissibilidade do Lote (CertidaoLancamentoInput)
# ---------------------------------------------------------------------------


def test_certidao_input_recusa_lote_sem_lancamento_ou_condominial() -> None:
    pedido = PedidoCertidao(processo="6017.2026/0012345-6", interessado="João da Silva")
    envelope = _envelope()
    agora = datetime.now(timezone.utc)
    planta = _planta()

    # Lote municipal (sem lançamento ativo)
    lote_municipal = _imovel(digito=None, situacao="ATIVO")
    assert not lote_municipal.possui_lancamento
    with pytest.raises(ValidationError) as exc_info_municipal:
        CertidaoLancamentoInput(
            envelope=envelope,
            pedido=pedido,
            imovel=lote_municipal,
            planta=planta,
            consultado_em=agora,
            base_url="https://geocoder.dimap.pmsp/",
        )
    assert "O lote não possui lançamento ativo no cadastro." in str(exc_info_municipal.value)

    # Lote inativo (situação cancelada)
    lote_inativo = _imovel(digito="5", situacao="CANCELADO")
    assert not lote_inativo.possui_lancamento
    with pytest.raises(ValidationError) as exc_info_inativo:
        CertidaoLancamentoInput(
            envelope=envelope,
            pedido=pedido,
            imovel=lote_inativo,
            planta=planta,
            consultado_em=agora,
            base_url="https://geocoder.dimap.pmsp/",
        )
    assert "O lote não possui lançamento ativo no cadastro." in str(exc_info_inativo.value)

    # Lote-mãe de condomínio
    lote_condominial = _imovel(condominio="01")
    assert lote_condominial.is_condominio
    with pytest.raises(ValidationError) as exc_info_cond:
        CertidaoLancamentoInput(
            envelope=envelope,
            pedido=pedido,
            imovel=lote_condominial,
            planta=planta,
            consultado_em=agora,
            base_url="https://geocoder.dimap.pmsp/",
        )
    assert "Lote condominial: a certidão ainda não é emitida pelo sistema." in str(exc_info_cond.value)

    # Lote válido, ativo e não condominial constrói normalmente
    lote_valido = _imovel(condominio="00", situacao="ATIVO", digito="5")
    input_valido = CertidaoLancamentoInput(
        envelope=envelope,
        pedido=pedido,
        imovel=lote_valido,
        planta=planta,
        consultado_em=agora,
        base_url="https://geocoder.dimap.pmsp/",
    )
    assert input_valido.imovel.sql == "005.003.0048-5"


def test_certidao_input_recusa_planta_de_outro_tipo() -> None:
    pedido = PedidoCertidao(processo="6017.2026/0012345-6", interessado="João da Silva")

    with pytest.raises(ValidationError):
        CertidaoLancamentoInput(
            envelope=_envelope(),
            pedido=pedido,
            imovel=_imovel(),
            planta="isto não é uma planta",  # type: ignore[arg-type]
            consultado_em=datetime.now(timezone.utc),
            base_url="https://geocoder.dimap.pmsp/",
        )
