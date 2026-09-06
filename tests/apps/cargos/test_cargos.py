"""
Testes de CargoComissao (SPEC user_admin/001): padrão legível, faixa do nível, a exclusividade
entre nível e alta administração, e a exigência de chefia para alta administração.
"""

from django.core.exceptions import ValidationError

import pytest

from apps.cargos.models import CargoComissao


def _cargo(**overrides: object) -> CargoComissao:
    dados: dict[str, object] = {
        "sigla": "CDA",
        "nivel": 1,
        "e_chefia": True,
        "alta_administracao": False,
        "nome": "Cargo Teste",
    }
    dados.update(overrides)
    return CargoComissao(**dados)  # type: ignore[arg-type]


def _full_clean_sem_db(cargo: CargoComissao) -> None:
    # validate_unique/validate_constraints fazem query de existência no banco; estes testes não
    # pedem a fixture `db`, então só clean_fields() + clean() entram em jogo.
    cargo.full_clean(validate_unique=False, validate_constraints=False)


def test_padrao_do_cargo_comissao_usa_algarismo_romano() -> None:
    comum = _cargo(sigla="CDA", nivel=4, nome="Diretor de Divisão")
    assert comum.padrao == "CDA-IV"

    alta_administracao = _cargo(
        sigla="SEC",
        nivel=None,
        alta_administracao=True,
        nome="Secretário",
    )
    assert alta_administracao.padrao == "SEC"


def test_nivel_do_cargo_comissao_fora_da_faixa_nao_valida() -> None:
    for nivel_invalido in (0, 7):
        with pytest.raises(ValidationError) as exc:
            _full_clean_sem_db(_cargo(nivel=nivel_invalido))
        assert "nivel" in exc.value.message_dict

    for nivel_valido in (1, 6):
        _full_clean_sem_db(_cargo(nivel=nivel_valido))


def test_nivel_e_alta_administracao_sao_mutuamente_exclusivos() -> None:
    sem_nivel = _cargo(nivel=None, nome="Cargo sem nível")
    with pytest.raises(ValidationError) as exc:
        _full_clean_sem_db(sem_nivel)
    assert "nivel" in exc.value.message_dict

    alta_administracao_com_nivel = _cargo(
        sigla="SEC",
        nivel=3,
        alta_administracao=True,
        nome="Secretário com nível",
    )
    with pytest.raises(ValidationError) as exc:
        _full_clean_sem_db(alta_administracao_com_nivel)
    assert "nivel" in exc.value.message_dict


def test_alta_administracao_exige_cargo_de_chefia() -> None:
    assessoramento_alta_administracao = _cargo(
        sigla="ASS",
        nivel=None,
        e_chefia=False,
        alta_administracao=True,
        nome="Assessor da alta administração",
    )
    with pytest.raises(ValidationError) as exc:
        _full_clean_sem_db(assessoramento_alta_administracao)
    assert "alta_administracao" in exc.value.message_dict


def test_natureza_do_cargo_e_o_rotulo_legivel() -> None:
    assert _cargo(e_chefia=True).natureza == "Chefia"
    assert _cargo(e_chefia=False).natureza == "Assessoramento"
