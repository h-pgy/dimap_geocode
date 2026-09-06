"""
Testes dos tipos de identificação de `apps/user_admin/schemas.py` (SPEC criacao_usuarios/006): RF,
nome de pessoa e e-mail deixam de ser `str` com limite de tamanho e passam a saber a própria forma.

Sem marker: o que se fixa aqui é o DTO — a mesma regra que as duas telas passam a aplicar, sem
banco nem request no caminho.
"""

from pydantic import ValidationError

import pytest

from apps.user_admin.formularios import ler_novo_servidor
from apps.user_admin.schemas import EdicaoServidor, NovoServidor


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _valores_do_formulario(**overrides: object) -> dict[str, object]:
    """O POST cru das duas telas: `servidor_id` só a edição lê, `url_acesso` só a criação — cada
    DTO ignora o que não é dele."""
    valores: dict[str, object] = {
        "servidor_id": 1,
        "rf": "8123456",
        "nome": "Ana",
        "sobrenome": "Ávila",
        "email": "ana@prefeitura.sp.gov.br",
        "unidade_id": 1,
        "cargo_base_id": 1,
        "cargo_comissao_id": "",
        "url_acesso": "http://testserver/",
    }
    valores.update(overrides)
    return valores


def _novo_servidor(**overrides: object) -> NovoServidor:
    return NovoServidor.model_validate(_valores_do_formulario(**overrides))


def _edicao_servidor(**overrides: object) -> EdicaoServidor:
    return EdicaoServidor.model_validate(_valores_do_formulario(**overrides))


# ---------------------------------------------------------------------------
# RF: sete dígitos, com ou sem pontuação
# ---------------------------------------------------------------------------


def test_rf_normaliza_pontuacao_e_recusa_fora_do_formato() -> None:
    for digitado in ("812.345-6", "812345-6", "8123456"):
        assert _novo_servidor(rf=digitado).rf == "8123456"
        assert _edicao_servidor(rf=digitado).rf == "8123456"

    for torto in ("812345", "81234567", "sem dígito algum"):
        with pytest.raises(ValidationError):
            _novo_servidor(rf=torto)
        with pytest.raises(ValidationError):
            _edicao_servidor(rf=torto)


# ---------------------------------------------------------------------------
# Nome e sobrenome: letra, espaço, hífen e apóstrofo
# ---------------------------------------------------------------------------


def test_nome_de_gente_passa_e_o_resto_nao() -> None:
    for aceito in ("Ana d'Ávila", "Silva-Santos", "José"):
        assert _novo_servidor(nome=aceito, sobrenome=aceito).nome == aceito

    for recusado in ("12345", "Ana2", "Nogueira Jr."):
        with pytest.raises(ValidationError):
            _novo_servidor(nome=recusado)
        with pytest.raises(ValidationError):
            _novo_servidor(sobrenome=recusado)


def test_espacos_do_nome_sao_aparados_e_colapsados() -> None:
    servidor = _novo_servidor(nome="  Ana   Maria  ", sobrenome="  d'Ávila   Santos  ")

    assert servidor.nome == "Ana Maria"
    assert servidor.sobrenome == "d'Ávila Santos"


# ---------------------------------------------------------------------------
# E-mail: uma grafia só, para que duas não convivam como dois cadastros
# ---------------------------------------------------------------------------


def test_email_e_normalizado_em_caixa_baixa() -> None:
    assert _novo_servidor(email="ANA@Prefeitura.SP.gov.BR").email == "ana@prefeitura.sp.gov.br"
    assert _edicao_servidor(email="ANA@Prefeitura.SP.gov.BR").email == "ana@prefeitura.sp.gov.br"


# ---------------------------------------------------------------------------
# Obrigatoriedade não se confunde com formato
# ---------------------------------------------------------------------------


def test_campo_em_branco_erra_por_obrigatoriedade() -> None:
    leitura = ler_novo_servidor(_valores_do_formulario(rf="", nome=""))

    assert leitura.dto is None
    assert leitura.recusa is not None
    # Campo com BeforeValidator erra por comprimento GENÉRICO, e não por `string_too_short`: sem a
    # regra nova no catálogo, "preencha o RF" viraria "valor inválido".
    assert "Preencha o campo RF." in leitura.recusa.mensagens
    assert "Preencha o campo Nome." in leitura.recusa.mensagens
