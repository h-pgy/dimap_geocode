"""Testes de services/domain/certidao_lancamento/models.py (SPECs certidao_lancamento/001 e 002):
validação do pedido (processo SEI, interessado, CPF/CNPJ e o despacho do auditor) e restrições de
admissibilidade de cada imóvel do objeto da certidão (recusa de lote sem lançamento ou condominial).
"""

from datetime import datetime, timezone

from pydantic import ValidationError
import pytest

from services.domain.certidao_lancamento.models import (
    CertidaoLancamentoInput,
    ConjuntoDesenhado,
    LoteUnico,
    PedidoCertidao,
    SentidoDespacho,
    TipoDespacho,
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


def _pedido(**overrides: object) -> PedidoCertidao:
    defaults: dict[str, object] = {
        "processo": "6017.2026/0012345-6",
        "interessado": "João da Silva",
        "sentido": SentidoDespacho.DEFERIDO,
        "tipo_despacho": TipoDespacho.POSSUI_LANCAMENTO,
    }
    return PedidoCertidao(**(defaults | overrides))  # type: ignore[arg-type]


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


def test_pedido_recusa_campos_fora_do_formato_ou_texto_de_outro_sentido() -> None:
    pedido = _pedido(processo="6017.2026/0012345-6", interessado="Secretaria Municipal da Fazenda")
    assert pedido.processo == "6017.2026/0012345-6"
    assert pedido.interessado == "Secretaria Municipal da Fazenda"

    # Processo SEI fora do formato
    for processo in ("6017.2026/123-4", "processo sei livre", "6017.2026/00123456", "6017-2026/0012345-6"):
        with pytest.raises(ValidationError):
            _pedido(processo=processo)

    # Interessado em branco ou curto demais
    for interessado in ("", "ab", "   "):
        with pytest.raises(ValidationError):
            _pedido(interessado=interessado)

    # CPF/CNPJ: formatado passa; dígitos faltando falha; vazio é ausente
    assert _pedido(cpf_cnpj="123.456.789-09").cpf_cnpj == "123.456.789-09"
    assert _pedido(cpf_cnpj="12.345.678/0001-90").cpf_cnpj == "12.345.678/0001-90"
    assert _pedido(cpf_cnpj="").cpf_cnpj is None
    assert _pedido().cpf_cnpj is None
    for cpf_cnpj in ("123.456.789-0", "12.345.678/0001-9", "12345678909", "123.456"):
        with pytest.raises(ValidationError):
            _pedido(cpf_cnpj=cpf_cnpj)

    # O texto escolhido precisa ser do sentido que a chave declarou
    with pytest.raises(ValidationError) as exc_info:
        _pedido(
            sentido=SentidoDespacho.INDEFERIDO,
            tipo_despacho=TipoDespacho.POSSUI_LANCAMENTO,
        )
    assert "Escolha um dos textos de despacho indeferido." in str(exc_info.value)
    with pytest.raises(ValidationError):
        _pedido(
            sentido=SentidoDespacho.DEFERIDO,
            tipo_despacho=TipoDespacho.IMOVEL_NAO_LOCALIZADO,
        )

    coerente = _pedido(
        sentido=SentidoDespacho.INDEFERIDO,
        tipo_despacho=TipoDespacho.IMOVEL_NAO_LOCALIZADO,
    )
    assert coerente.tipo_despacho.sentido is coerente.sentido


# ---------------------------------------------------------------------------
# Restrições de Admissibilidade do Lote (CertidaoLancamentoInput)
# ---------------------------------------------------------------------------


def test_certidao_input_recusa_lote_sem_lancamento_ou_condominial() -> None:
    pedido = _pedido()
    envelope = _envelope()
    agora = datetime.now(timezone.utc)
    recusa = "Lotes sem lançamento ativo ou condominiais:"

    # Lote municipal (sem lançamento ativo)
    lote_municipal = _imovel(digito=None, situacao="ATIVO")
    assert not lote_municipal.possui_lancamento
    with pytest.raises(ValidationError) as exc_info_municipal:
        CertidaoLancamentoInput(
            envelope=envelope,
            pedido=pedido,
            objeto=LoteUnico(imovel=lote_municipal),
            planta=None,
            consultado_em=agora,
            base_url="https://geocoder.dimap.pmsp/",
        )
    assert recusa in str(exc_info_municipal.value)

    # Lote inativo (situação cancelada)
    lote_inativo = _imovel(digito="5", situacao="CANCELADO")
    assert not lote_inativo.possui_lancamento
    with pytest.raises(ValidationError) as exc_info_inativo:
        CertidaoLancamentoInput(
            envelope=envelope,
            pedido=pedido,
            objeto=LoteUnico(imovel=lote_inativo),
            planta=None,
            consultado_em=agora,
            base_url="https://geocoder.dimap.pmsp/",
        )
    assert recusa in str(exc_info_inativo.value)

    # Lote-mãe de condomínio
    lote_condominial = _imovel(condominio="01")
    assert lote_condominial.is_condominio
    with pytest.raises(ValidationError) as exc_info_cond:
        CertidaoLancamentoInput(
            envelope=envelope,
            pedido=pedido,
            objeto=LoteUnico(imovel=lote_condominial),
            planta=None,
            consultado_em=agora,
            base_url="https://geocoder.dimap.pmsp/",
        )
    assert recusa in str(exc_info_cond.value)

    # Lote válido, ativo e não condominial constrói normalmente
    lote_valido = _imovel(condominio="00", situacao="ATIVO", digito="5")
    input_valido = CertidaoLancamentoInput(
        envelope=envelope,
        pedido=pedido,
        objeto=LoteUnico(imovel=lote_valido),
        planta=None,
        consultado_em=agora,
        base_url="https://geocoder.dimap.pmsp/",
    )
    assert [imovel.sql for imovel in input_valido.objeto.imoveis] == ["005.003.0048-5"]

    # No conjunto a regra vale para cada lote: um impeditivo recusa a certidão inteira, e é nomeado
    outro_valido = _imovel(id_poligono="1002", lote="0049", digito="3")
    condominial_do_conjunto = _imovel(id_poligono="1003", lote="0050", digito="1", condominio="01")
    with pytest.raises(ValidationError) as exc_info_conjunto:
        CertidaoLancamentoInput(
            envelope=envelope,
            pedido=pedido,
            objeto=ConjuntoDesenhado(
                lotes=(lote_valido, outro_valido, condominial_do_conjunto),
                area_desenho_m2=1250.0,
            ),
            planta=None,
            consultado_em=agora,
            base_url="https://geocoder.dimap.pmsp/",
        )
    assert f"{recusa} 005.003.0050-1." in str(exc_info_conjunto.value)

    conjunto_valido = CertidaoLancamentoInput(
        envelope=envelope,
        pedido=pedido,
        objeto=ConjuntoDesenhado(lotes=(lote_valido, outro_valido), area_desenho_m2=1250.0),
        planta=None,
        consultado_em=agora,
        base_url="https://geocoder.dimap.pmsp/",
    )
    assert [imovel.sql for imovel in conjunto_valido.objeto.imoveis] == [
        "005.003.0048-5",
        "005.003.0049-3",
    ]


def test_certidao_input_recusa_planta_de_outro_tipo() -> None:
    pedido = _pedido(incluir_planta=True)

    with pytest.raises(ValidationError):
        CertidaoLancamentoInput(
            envelope=_envelope(),
            pedido=pedido,
            objeto=LoteUnico(imovel=_imovel()),
            planta="isto não é uma planta",  # type: ignore[arg-type]
            consultado_em=datetime.now(timezone.utc),
            base_url="https://geocoder.dimap.pmsp/",
        )
