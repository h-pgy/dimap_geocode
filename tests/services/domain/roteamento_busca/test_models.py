"""
Testes do EnderecoLoteParse (SPEC 010): exclusividade nome/codlog e o computed_field
`numero_padronizado` (= chave_numero_porta(numero_bruto)).
"""

import pytest
from pydantic import ValidationError

from services.domain.roteamento_busca import (
    CodlogParse,
    EnderecoLoteParse,
    LogradouroParse,
    TipoEntrada,
)


def _logradouro() -> LogradouroParse:
    return LogradouroParse(tipo_logradouro="avenida", nome="paulista")


def _codlog() -> CodlogParse:
    return CodlogParse(codlog="12345", digito_verificador="")


# ---------------------------------------------------------------------------
# Exclusividade: exatamente uma forma (logradouro OU codlog)
# ---------------------------------------------------------------------------


class TestExclusividade:
    def test_aceita_so_logradouro(self) -> None:
        p = EnderecoLoteParse(logradouro=_logradouro(), numero_bruto="100")
        assert p.logradouro is not None
        assert p.codlog is None
        assert p.tipo == TipoEntrada.ENDERECO_LOTE

    def test_aceita_so_codlog(self) -> None:
        p = EnderecoLoteParse(codlog=_codlog(), numero_bruto="100")
        assert p.codlog is not None
        assert p.logradouro is None

    def test_rejeita_ambos(self) -> None:
        with pytest.raises(ValidationError):
            EnderecoLoteParse(logradouro=_logradouro(), codlog=_codlog(), numero_bruto="100")

    def test_rejeita_nenhum(self) -> None:
        with pytest.raises(ValidationError):
            EnderecoLoteParse(numero_bruto="100")


# ---------------------------------------------------------------------------
# numero_padronizado — computed_field derivado de numero_bruto
# ---------------------------------------------------------------------------


class TestNumeroPadronizado:
    @pytest.mark.parametrize(
        "bruto, padronizado",
        [
            # numero_bruto já chega SEM marcador (parse_numero_porta o removeu); a chave
            # só normaliza/canoniza. Ex.: "s/n" -> "SN", "10-A" -> "10A".
            ("s/n", "SN"),
            ("10-A", "10A"),
            ("10 A", "10A"),
            ("100", "100"),
        ],
    )
    def test_valores(self, bruto: str, padronizado: str) -> None:
        p = EnderecoLoteParse(logradouro=_logradouro(), numero_bruto=bruto)
        assert p.numero_padronizado == padronizado

    def test_derivado_do_bruto(self) -> None:
        # não é um segundo campo de entrada: muda com numero_bruto
        p1 = EnderecoLoteParse(logradouro=_logradouro(), numero_bruto="s/n")
        p2 = EnderecoLoteParse(logradouro=_logradouro(), numero_bruto="100")
        assert p1.numero_padronizado == "SN"
        assert p2.numero_padronizado == "100"

    def test_aparece_no_dump(self) -> None:
        p = EnderecoLoteParse(logradouro=_logradouro(), numero_bruto="s/n")
        assert p.model_dump()["numero_padronizado"] == "SN"
