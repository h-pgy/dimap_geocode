from datetime import datetime

import pytest
from django.utils import timezone

from services.domain.documento_selado import AlvoDoAto, AutorDoAto, EnvelopeAto, montar_envelope


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
        "codigo": "ABCDEFGHJKMN",
        "acao": "certidoes.lancamento",
        "operacao": "emissao",
        "autor": _autor(),
        "alvo": _alvo(),
        "emitido_em": timezone.now(),
    }
    return EnvelopeAto(**(defaults | overrides))


# ---------------------------------------------------------------------------
# O mapa achatado carrega todos os campos do registro de execução
# ---------------------------------------------------------------------------


def test_envelope_traz_todos_os_campos_do_registro_de_execucao() -> None:
    ato = _envelope_ato()

    resultado = montar_envelope(ato)

    assert resultado["acao"] == ato.acao
    assert resultado["operacao"] == ato.operacao
    assert resultado["autor"]["unidade"] == ato.autor.unidade
    assert resultado["autor"]["cargo_base"] == ato.autor.cargo_base
    assert resultado["autor"]["cargo_comissao"] == ato.autor.cargo_comissao
    assert resultado["autor"]["substituindo"] == ato.autor.substituindo
    assert resultado["alvo"]["tipo"] == ato.alvo.tipo
    assert resultado["alvo"]["identificador"] == ato.alvo.identificador
    assert isinstance(datetime.fromisoformat(resultado["emitido_em"]), datetime)


# ---------------------------------------------------------------------------
# Extra que repete chave do núcleo é recusado na montagem
# ---------------------------------------------------------------------------


def test_extra_que_colide_com_o_nucleo_eh_recusado() -> None:
    colidido = _envelope_ato(extras={"autor": "outro"})

    with pytest.raises(ValueError, match="autor"):
        montar_envelope(colidido)

    livre = _envelope_ato(extras={"prioridade": "alta"})

    resultado = montar_envelope(livre)

    assert resultado["prioridade"] == "alta"
    assert resultado["acao"] == livre.acao
