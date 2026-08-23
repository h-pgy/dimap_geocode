"""
Testes da carga do organograma a partir de `data/seed/unidades.json` (SPEC user_admin/008):
tipos e unidades gravados a partir do arquivo, idempotência por chave natural (`nome`/`sigla`),
independência da ordem das unidades no arquivo e aborto integral diante de qualquer falha.

Todos levam o marker `banco`: a hierarquia é validada em `clean()` contra a tabela (SPEC
user_admin/003), e nenhuma dessas regras se verifica sobre objeto não persistido.
"""

from typing import Any

from django.core.exceptions import ValidationError

import pytest

from apps.unidades.models import CorUnidade, TipoUnidade, Unidade
from apps.unidades.seeds import carregar_seed_unidades
from services.utils.io import subpasta_de_data, write_json_to_folder

banco = pytest.mark.banco

NOME_ARQUIVO_SEED = "unidades.json"


def _escrever_seed(tipos: list[dict[str, Any]], unidades: list[dict[str, Any]]) -> None:
    pasta = subpasta_de_data("seed")
    write_json_to_folder(
        pasta, NOME_ARQUIVO_SEED, {"tipos": tipos, "unidades": unidades}
    )


@banco
@pytest.mark.django_db
def test_carga_cria_tipos_e_unidades_do_arquivo() -> None:
    _escrever_seed(
        tipos=[
            {"nome": "Divisão", "nivel": 10, "nivel_minimo_titular": 1},
            {
                "nome": "Departamento",
                "nivel": 20,
                "tipos_filhos_vedados": ["Divisão"],
                "nivel_minimo_titular": 1,
            },
            {
                "nome": "Secretaria",
                "nivel": 30,
                "pode_ser_raiz": True,
                "exige_alta_administracao": True,
            },
        ],
        unidades=[
            {
                "nome": "Secretaria",
                "sigla": "SEC",
                "tipo": "Secretaria",
                "cor": "rocha-900",
            },
            {
                "nome": "Departamento",
                "sigla": "DPTO",
                "tipo": "Departamento",
                "pai": "SEC",
                "cor": "agua-700",
            },
        ],
    )

    carregar_seed_unidades()

    tipo_departamento = TipoUnidade.objects.get(nome="Departamento")
    assert tipo_departamento.nivel == 20
    assert tipo_departamento.pode_ser_raiz is False
    assert list(
        tipo_departamento.tipos_filhos_vedados.values_list("nome", flat=True)
    ) == ["Divisão"]

    tipo_secretaria = TipoUnidade.objects.get(nome="Secretaria")
    assert tipo_secretaria.nivel == 30
    assert tipo_secretaria.pode_ser_raiz is True

    unidade_sec = Unidade.objects.get(sigla="SEC")
    assert unidade_sec.tipo == tipo_secretaria
    assert unidade_sec.pai is None
    assert unidade_sec.cor == CorUnidade.ROCHA_900

    unidade_dpto = Unidade.objects.get(sigla="DPTO")
    assert unidade_dpto.tipo == tipo_departamento
    assert unidade_dpto.pai == unidade_sec
    assert unidade_dpto.cor == CorUnidade.AGUA_700


@banco
@pytest.mark.django_db
def test_carga_e_idempotente() -> None:
    tipos = [
        {
            "nome": "Secretaria",
            "nivel": 30,
            "pode_ser_raiz": True,
            "exige_alta_administracao": True,
        },
        {"nome": "Departamento", "nivel": 20, "nivel_minimo_titular": 1},
    ]
    _escrever_seed(
        tipos=tipos,
        unidades=[
            {"nome": "Secretaria", "sigla": "SEC", "tipo": "Secretaria"},
            {
                "nome": "Departamento",
                "sigla": "DPTO",
                "tipo": "Departamento",
                "pai": "SEC",
                "cor": "agua-700",
            },
        ],
    )
    carregar_seed_unidades()

    _escrever_seed(
        tipos=tipos,
        unidades=[
            {"nome": "Secretaria", "sigla": "SEC", "tipo": "Secretaria"},
            {
                "nome": "Departamento",
                "sigla": "DPTO",
                "tipo": "Departamento",
                "pai": "SEC",
                "cor": "sakura-600",
            },
        ],
    )
    carregar_seed_unidades()

    assert TipoUnidade.objects.count() == 2
    assert Unidade.objects.count() == 2
    assert Unidade.objects.get(sigla="DPTO").cor == CorUnidade.SAKURA_600


@banco
@pytest.mark.django_db
def test_ordem_do_arquivo_e_irrelevante() -> None:
    _escrever_seed(
        tipos=[
            {
                "nome": "Secretaria",
                "nivel": 30,
                "pode_ser_raiz": True,
                "exige_alta_administracao": True,
            },
            {"nome": "Departamento", "nivel": 20, "nivel_minimo_titular": 1},
        ],
        unidades=[
            # Filha declarada antes da superior: a segunda passagem é quem liga o pai.
            {
                "nome": "Departamento",
                "sigla": "DPTO",
                "tipo": "Departamento",
                "pai": "SEC",
            },
            {"nome": "Secretaria", "sigla": "SEC", "tipo": "Secretaria"},
        ],
    )

    carregar_seed_unidades()

    assert Unidade.objects.get(sigla="DPTO").pai == Unidade.objects.get(sigla="SEC")


@banco
@pytest.mark.django_db
def test_pai_inexistente_aborta_sem_gravar_nada() -> None:
    _escrever_seed(
        tipos=[{"nome": "Departamento", "nivel": 20, "nivel_minimo_titular": 1}],
        unidades=[
            {
                "nome": "Departamento",
                "sigla": "DPTO",
                "tipo": "Departamento",
                "pai": "SEC-FANTASMA",
            },
        ],
    )

    with pytest.raises(Unidade.DoesNotExist):
        carregar_seed_unidades()

    assert TipoUnidade.objects.count() == 0
    assert Unidade.objects.count() == 0


@banco
@pytest.mark.django_db
def test_hierarquia_invalida_e_recusada() -> None:
    # Nível não superior: o departamento não subordina a secretaria, mesmo nomeado como pai.
    _escrever_seed(
        tipos=[
            {
                "nome": "Secretaria",
                "nivel": 10,
                "pode_ser_raiz": True,
                "exige_alta_administracao": True,
            },
            {"nome": "Departamento", "nivel": 20, "nivel_minimo_titular": 1},
        ],
        unidades=[
            {"nome": "Secretaria", "sigla": "SEC", "tipo": "Secretaria"},
            {
                "nome": "Departamento",
                "sigla": "DPTO",
                "tipo": "Departamento",
                "pai": "SEC",
            },
        ],
    )
    with pytest.raises(ValidationError):
        carregar_seed_unidades()
    assert TipoUnidade.objects.count() == 0
    assert Unidade.objects.count() == 0

    # Tipo de filha vedado no pai: nível permitiria, mas a veda nominal recusa.
    _escrever_seed(
        tipos=[
            {
                "nome": "Coordenadoria",
                "nivel": 30,
                "pode_ser_raiz": True,
                "tipos_filhos_vedados": ["Divisão"],
                "nivel_minimo_titular": 1,
            },
            {"nome": "Divisão", "nivel": 10, "nivel_minimo_titular": 1},
        ],
        unidades=[
            {"nome": "Coordenadoria", "sigla": "COORD", "tipo": "Coordenadoria"},
            {"nome": "Divisão", "sigla": "DIV", "tipo": "Divisão", "pai": "COORD"},
        ],
    )
    with pytest.raises(ValidationError):
        carregar_seed_unidades()
    assert TipoUnidade.objects.count() == 0
    assert Unidade.objects.count() == 0


@banco
@pytest.mark.django_db
def test_seed_grava_minimo_ou_exigencia_de_alta_administracao_do_tipo() -> None:
    _escrever_seed(
        tipos=[
            {
                "nome": "Divisão",
                "nivel": 10,
                "pode_ser_raiz": True,
                "nivel_minimo_titular": 4,
            },
            {"nome": "Subsecretaria", "nivel": 20, "exige_alta_administracao": True},
        ],
        unidades=[
            {"nome": "Divisão", "sigla": "DIV", "tipo": "Divisão"},
        ],
    )

    carregar_seed_unidades()

    tipo_divisao = TipoUnidade.objects.get(nome="Divisão")
    assert tipo_divisao.nivel_minimo_titular == 4
    assert tipo_divisao.exige_alta_administracao is False

    tipo_subsecretaria = TipoUnidade.objects.get(nome="Subsecretaria")
    assert tipo_subsecretaria.exige_alta_administracao is True
    assert tipo_subsecretaria.nivel_minimo_titular is None
