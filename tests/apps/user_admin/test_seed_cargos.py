"""
Testes da carga de cargos a partir de `data/seed/cargos.json` (SPEC user_admin/009):
cargo base e cargo em comissão gravados a partir do arquivo, idempotência por chave natural
(`sigla`/`nome`), `full_clean()` de `CargoComissao` e aborto integral diante de qualquer falha.

Todos levam o marker `banco`: a regra alta_administracao × nivel × e_chefia é validada em
`clean()` contra a tabela (SPEC user_admin/001), e a constraint só se verifica sobre objeto
persistido.
"""

from typing import Any

from django.core.exceptions import ValidationError

import pytest

from apps.user_admin.models import CargoBase, CargoComissao
from apps.user_admin.seeds import carregar_seed_cargos
from services.utils.io import subpasta_de_data, write_json_to_folder

banco = pytest.mark.banco

NOME_ARQUIVO_SEED = "cargos.json"


def _escrever_seed(
    cargo_base: list[dict[str, Any]], cargo_comissao: list[dict[str, Any]]
) -> None:
    pasta = subpasta_de_data("seed")
    write_json_to_folder(
        pasta,
        NOME_ARQUIVO_SEED,
        {"cargo_base": cargo_base, "cargo_comissao": cargo_comissao},
    )


@banco
@pytest.mark.django_db
def test_carga_cria_cargo_base_e_cargo_comissao_do_arquivo() -> None:
    _escrever_seed(
        cargo_base=[
            {"nome": "Auditor Fiscal Tributário Municipal", "sigla": "AFTM"},
        ],
        cargo_comissao=[
            {
                "nome": "Secretária/o Municipal",
                "sigla": "SEC",
                "nivel": None,
                "e_chefia": True,
                "alta_administracao": True,
            },
            {
                "nome": "Diretor de Divisão",
                "sigla": "CDA",
                "nivel": 4,
                "e_chefia": True,
                "alta_administracao": False,
            },
        ],
    )

    carregar_seed_cargos()

    cargo_base = CargoBase.objects.get(sigla="AFTM")
    assert cargo_base.nome == "Auditor Fiscal Tributário Municipal"

    alta_adm = CargoComissao.objects.get(nome="Secretária/o Municipal")
    assert alta_adm.sigla == "SEC"
    assert alta_adm.nivel is None
    assert alta_adm.e_chefia is True
    assert alta_adm.alta_administracao is True

    diretor = CargoComissao.objects.get(nome="Diretor de Divisão")
    assert diretor.sigla == "CDA"
    assert diretor.nivel == 4
    assert diretor.e_chefia is True
    assert diretor.alta_administracao is False


@banco
@pytest.mark.django_db
def test_carga_e_idempotente() -> None:
    _escrever_seed(
        cargo_base=[{"nome": "Assistente Administrativo de Gestão", "sigla": "AAG"}],
        cargo_comissao=[
            {
                "nome": "Diretor de Divisão",
                "sigla": "CDA",
                "nivel": 4,
                "e_chefia": True,
                "alta_administracao": False,
            },
        ],
    )
    carregar_seed_cargos()

    _escrever_seed(
        cargo_base=[
            {"nome": "Assistente Administrativo de Gestão II", "sigla": "AAG"}
        ],
        cargo_comissao=[
            {
                "nome": "Diretor de Divisão",
                "sigla": "CDA",
                "nivel": 5,
                "e_chefia": True,
                "alta_administracao": False,
            },
        ],
    )
    carregar_seed_cargos()

    assert CargoBase.objects.count() == 1
    assert CargoComissao.objects.count() == 1
    assert (
        CargoBase.objects.get(sigla="AAG").nome
        == "Assistente Administrativo de Gestão II"
    )
    assert CargoComissao.objects.get(nome="Diretor de Divisão").nivel == 5


@banco
@pytest.mark.django_db
def test_cargo_comissao_invalido_aborta_sem_gravar_nada() -> None:
    _escrever_seed(
        cargo_base=[{"nome": "Assistente Administrativo de Gestão", "sigla": "AAG"}],
        cargo_comissao=[
            {
                "nome": "Cargo Inválido",
                "sigla": "CDA",
                "nivel": 4,
                "e_chefia": True,
                "alta_administracao": True,
            },
        ],
    )

    with pytest.raises(ValidationError):
        carregar_seed_cargos()

    assert CargoBase.objects.count() == 0
    assert CargoComissao.objects.count() == 0


@banco
@pytest.mark.django_db
def test_dry_run_nao_persiste() -> None:
    _escrever_seed(
        cargo_base=[{"nome": "Assistente Administrativo de Gestão", "sigla": "AAG"}],
        cargo_comissao=[
            {
                "nome": "Diretor de Divisão",
                "sigla": "CDA",
                "nivel": 4,
                "e_chefia": True,
                "alta_administracao": False,
            },
        ],
    )

    carregar_seed_cargos(dry_run=True)

    assert CargoBase.objects.count() == 0
    assert CargoComissao.objects.count() == 0
