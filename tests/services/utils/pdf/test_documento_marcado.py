import pytest

from services.utils.pdf.documento_marcado import MarcacaoDocumento
from services.utils.pdf.marcacao import Marcacao
from services.utils.pdf.models import Orientacao


def _marcacao(orientacao: Orientacao = Orientacao.RETRATO) -> Marcacao:
    return Marcacao(marcas=(), margem_lateral_mm=10.0, respiro_mm=0.0, orientacao=orientacao)


# ---------------------------------------------------------------------------
# Resolução por especificidade
# ---------------------------------------------------------------------------


def test_marcacao_resolve_pela_especificidade() -> None:
    principal = _marcacao()
    primeira = _marcacao()
    ultima = _marcacao()
    especifica = _marcacao()
    documento = MarcacaoDocumento(
        principal=principal,
        primeira=primeira,
        ultima=ultima,
        marcacoes_especificas={2: especifica},
    )

    # Página nomeada vence primeira e última.
    assert documento.para(2, 3) is especifica
    # Extremo vence a principal.
    assert documento.para(1, 3) is primeira
    assert documento.para(3, 3) is ultima
    # Miolo (nem extremo, nem página nomeada) cai na principal.
    assert documento.para(3, 4) is principal
    # Documento de uma página só: a primeira vence a última.
    documento_de_uma_pagina = MarcacaoDocumento(principal=principal, primeira=primeira, ultima=ultima)
    assert documento_de_uma_pagina.para(1, 1) is primeira
    # Sem override algum, a principal vale em todas.
    documento_sem_override = MarcacaoDocumento(principal=principal)
    assert documento_sem_override.para(1, 5) is principal
    assert documento_sem_override.para(5, 5) is principal


# ---------------------------------------------------------------------------
# Orientação divergente é recusada na construção
# ---------------------------------------------------------------------------


def test_documento_recusa_orientacoes_divergentes() -> None:
    principal = _marcacao(Orientacao.RETRATO)
    especifica_paisagem = _marcacao(Orientacao.PAISAGEM)

    with pytest.raises(ValueError):
        MarcacaoDocumento(principal=principal, marcacoes_especificas={1: especifica_paisagem})
