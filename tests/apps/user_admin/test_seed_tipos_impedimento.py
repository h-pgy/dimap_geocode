"""
Testes da carga de tipos de impedimento a partir de `data/seed/tipos_impedimento.json`
(SPEC user_admin/010): catálogo gravado a partir do arquivo, criação apenas do que falta por
chave natural (`nome`), `full_clean()` contra a `UniqueConstraint` condicional da sigla e aborto
integral diante de qualquer falha.

Todos levam o marker `banco`: a UniqueConstraint da sigla só se verifica sobre objeto persistido.
"""

from typing import Any

from django.core.exceptions import ValidationError

import pytest

from apps.user_admin.models import TipoImpedimento
from apps.user_admin.seeds import carregar_seed_tipos_impedimento
from services.utils.io import subpasta_de_data, write_json_to_folder

banco = pytest.mark.banco

NOME_ARQUIVO_SEED = "tipos_impedimento.json"


def _escrever_seed(tipos: list[dict[str, Any]]) -> None:
    pasta = subpasta_de_data("seed")
    write_json_to_folder(pasta, NOME_ARQUIVO_SEED, {"tipos": tipos})


@banco
@pytest.mark.django_db
def test_carga_cria_tipos_impedimento_do_arquivo() -> None:
    _escrever_seed(
        [
            {"nome": "Férias", "sigla": None},
            {"nome": "Licença Maternidade", "sigla": None},
            {"nome": "Licença para Tratar de Interesses Particulares", "sigla": "LIP"},
        ]
    )

    carregar_seed_tipos_impedimento()

    ferias = TipoImpedimento.objects.get(nome="Férias")
    assert ferias.sigla == ""

    maternidade = TipoImpedimento.objects.get(nome="Licença Maternidade")
    assert maternidade.sigla == ""

    lip = TipoImpedimento.objects.get(nome="Licença para Tratar de Interesses Particulares")
    assert lip.sigla == "LIP"


@banco
@pytest.mark.django_db
def test_carga_nao_toca_registro_existente() -> None:
    _escrever_seed([{"nome": "Licença Gala", "sigla": None}])
    carregar_seed_tipos_impedimento()

    _escrever_seed([{"nome": "Licença Gala", "sigla": "LG"}])
    carregar_seed_tipos_impedimento()

    # A sigla da segunda escrita não entra: o registro já existia.
    assert TipoImpedimento.objects.count() == 1
    assert TipoImpedimento.objects.get(nome="Licença Gala").sigla == ""


@banco
@pytest.mark.django_db
def test_sigla_duplicada_no_arquivo_aborta_sem_gravar_nada() -> None:
    _escrever_seed(
        [
            {"nome": "Licença Gala", "sigla": "LG"},
            {"nome": "Licença Nojo", "sigla": "LG"},
        ]
    )

    with pytest.raises(ValidationError):
        carregar_seed_tipos_impedimento()

    assert TipoImpedimento.objects.count() == 0


@banco
@pytest.mark.django_db
def test_dry_run_nao_persiste() -> None:
    _escrever_seed([{"nome": "Férias", "sigla": None}])

    carregar_seed_tipos_impedimento(dry_run=True)

    assert TipoImpedimento.objects.count() == 0
