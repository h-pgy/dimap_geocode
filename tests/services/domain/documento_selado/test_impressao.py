import re

from django.utils import timezone

from services.domain.documento_selado import (
    AlvoDoAto,
    AutorDoAto,
    EnvelopeAto,
    SeloImpressoInput,
    gerar_codigo,
    montar_envelope,
    montar_selo_impresso,
)
from services.domain.documento_selado.constants import CHAMADA_SELO, ROTA_CONFERENCIA

BASE_URL = "https://geocode.dimap.sp.gov.br"


def _autor(**overrides: object) -> AutorDoAto:
    defaults: dict[str, object] = {
        "nome": "Fulano de Tal",
        "unidade": "DIMAP-1",
        "cargo_base": "Agente Fazendário",
        "cargo_comissao": "Chefe da Divisão do Mapa de Valores",
        "substituindo": None,
    }
    return AutorDoAto(**(defaults | overrides))


def _alvo(**overrides: object) -> AlvoDoAto:
    defaults: dict[str, object] = {"tipo": "lote", "identificador": "123.456.7890-1"}
    return AlvoDoAto(**(defaults | overrides))


def _envelope_ato(**overrides: object) -> EnvelopeAto:
    defaults: dict[str, object] = {
        "codigo": gerar_codigo(),
        "acao": "certidoes.lancamento",
        "operacao": "emissao",
        "autor": _autor(),
        "alvo": _alvo(),
        "emitido_em": timezone.now(),
    }
    return EnvelopeAto(**(defaults | overrides))


# ---------------------------------------------------------------------------
# O selo impresso, o QR e o envelope descrevem o MESMO ato
# ---------------------------------------------------------------------------


def test_impresso_qr_e_envelope_dizem_o_mesmo_ato() -> None:
    ato = _envelope_ato()

    selo = montar_selo_impresso(SeloImpressoInput(envelope=ato, base_url=BASE_URL))
    envelope = montar_envelope(ato)

    esperado = f"{BASE_URL}/{ROTA_CONFERENCIA}/{ato.codigo}"
    assert selo.url_conferencia == esperado
    assert selo.link_impresso == esperado.split("://", 1)[-1]
    assert selo.assinante == ato.autor.nome == envelope["autor"]["nome"]
    assert envelope["codigo"] == ato.codigo


# ---------------------------------------------------------------------------
# A chamada do selo é sempre "eletronicamente", nunca "digitalmente"
# ---------------------------------------------------------------------------


def test_selo_diz_assinado_eletronicamente() -> None:
    selo = montar_selo_impresso(SeloImpressoInput(envelope=_envelope_ato(), base_url=BASE_URL))

    assert selo.chamada == CHAMADA_SELO
    assert "eletronicamente" in selo.chamada
    assert "digitalmente" not in str(selo.model_dump())


# ---------------------------------------------------------------------------
# O fecho traz o cargo de comissão (ou o base), sem unidade, com a data por extenso
# ---------------------------------------------------------------------------


def test_fecho_traz_cargo_de_comissao_sem_unidade_e_data_por_extenso() -> None:
    momento = timezone.now()
    com_comissao = _envelope_ato(emitido_em=momento)
    sem_comissao = _envelope_ato(autor=_autor(cargo_comissao=None), emitido_em=momento)

    selo_com = montar_selo_impresso(SeloImpressoInput(envelope=com_comissao, base_url=BASE_URL))
    selo_sem = montar_selo_impresso(SeloImpressoInput(envelope=sem_comissao, base_url=BASE_URL))

    assert selo_com.cargo == com_comissao.autor.cargo_comissao
    assert selo_sem.cargo == sem_comissao.autor.cargo_base
    assert "unidade" not in selo_com.model_dump()
    assert re.search(r"às \d{2}h\d{2}min$", selo_com.data_por_extenso)
