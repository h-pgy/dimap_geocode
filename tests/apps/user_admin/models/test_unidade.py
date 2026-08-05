"""
Testes de TipoUnidade e da hierarquia de Unidade (SPEC user_admin/003): nível do tipo como regra
geral de subordinação, veda nominal de tipos-filho como exceção, exigência de pai para tipo que não
encabeça árvore, convivência de raízes paralelas e a constraint de que uma unidade não é pai de si
mesma. Inclui também a cor da unidade (SPEC user_admin/005): choices/default e a sugestão de cor a
partir do pai.

Todos levam o marker `banco`: a veda é M2M e a constraint é do Postgres — nenhum dos dois se
verifica sobre objeto não persistido.
"""

from django.core.exceptions import ValidationError
from django.db import IntegrityError

import pytest

from apps.user_admin.models import CorUnidade, TipoUnidade, Unidade

banco = pytest.mark.banco


def _tipo(**overrides: object) -> TipoUnidade:
    # Raiz por padrão aqui (no model o default é o oposto): a maioria dos casos monta a árvore de
    # cima para baixo e não deve esbarrar na exigência de pai.
    dados: dict[str, object] = {
        "nome": "Departamento",
        "nivel": 10,
        "pode_ser_raiz": True,
    }
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(**overrides: object) -> Unidade:
    dados: dict[str, object] = {
        "nome": "Unidade Teste",
        "sigla": "UT",
    }
    dados.update(overrides)
    # Criar o tipo só quando não veio um: TipoUnidade.nome é unique e um default ansioso colidiria
    # com o tipo que o próprio teste montou.
    if "tipo" not in dados:
        dados["tipo"] = _tipo()
    unidade = Unidade(**dados)  # type: ignore[arg-type]
    unidade.full_clean()
    unidade.save()
    return unidade


@banco
@pytest.mark.django_db
def test_unidade_filha_exige_nivel_menor_que_o_do_pai() -> None:
    tipo_pai = _tipo(nome="Departamento", nivel=20)
    tipo_nivel_igual = _tipo(nome="Outro Departamento", nivel=20)
    tipo_nivel_maior = _tipo(nome="Secretaria", nivel=30)
    tipo_nivel_menor = _tipo(nome="Divisão", nivel=10)
    pai = _unidade(nome="Departamento", sigla="DPTO", tipo=tipo_pai)

    filha_nivel_menor = Unidade(nome="Divisão", sigla="DIV", tipo=tipo_nivel_menor, pai=pai)
    filha_nivel_menor.full_clean()
    filha_nivel_menor.save()
    assert filha_nivel_menor.pai == pai

    filha_nivel_igual = Unidade(nome="Depto Igual", sigla="DPTOI", tipo=tipo_nivel_igual, pai=pai)
    with pytest.raises(ValidationError):
        filha_nivel_igual.full_clean()

    filha_nivel_maior = Unidade(nome="Secretaria", sigla="SEC", tipo=tipo_nivel_maior, pai=pai)
    with pytest.raises(ValidationError):
        filha_nivel_maior.full_clean()


@banco
@pytest.mark.django_db
def test_tipo_pai_recusa_filha_de_tipo_vedado() -> None:
    tipo_coordenadoria = _tipo(nome="Coordenadoria", nivel=20)
    tipo_departamento = _tipo(nome="Departamento", nivel=15)
    tipo_divisao = _tipo(nome="Divisão", nivel=10)
    tipo_coordenadoria.tipos_filhos_vedados.add(tipo_divisao)

    coordenadoria = _unidade(nome="Coordenadoria", sigla="COORD", tipo=tipo_coordenadoria)
    departamento = _unidade(nome="Departamento", sigla="DPTO", tipo=tipo_departamento)

    divisao_sob_coordenadoria = Unidade(
        nome="Divisão",
        sigla="DIV1",
        tipo=tipo_divisao,
        pai=coordenadoria,
    )
    with pytest.raises(ValidationError):
        divisao_sob_coordenadoria.full_clean()

    divisao_sob_departamento = Unidade(
        nome="Divisão",
        sigla="DIV2",
        tipo=tipo_divisao,
        pai=departamento,
    )
    divisao_sob_departamento.full_clean()
    divisao_sob_departamento.save()
    assert divisao_sob_departamento.pai == departamento


@banco
@pytest.mark.django_db
def test_tipo_nao_raiz_exige_pai() -> None:
    tipo_secretaria = _tipo(nome="Secretaria", nivel=30)
    tipo_divisao = _tipo(nome="Divisão", nivel=10, pode_ser_raiz=False)
    secretaria = _unidade(nome="Secretaria", sigla="SEC", tipo=tipo_secretaria)

    divisao_sem_pai = Unidade(nome="Divisão", sigla="DIV", tipo=tipo_divisao)
    with pytest.raises(ValidationError):
        divisao_sem_pai.full_clean()

    divisao_com_pai = Unidade(nome="Divisão", sigla="DIV", tipo=tipo_divisao, pai=secretaria)
    divisao_com_pai.full_clean()
    divisao_com_pai.save()
    assert divisao_com_pai.pai == secretaria


@banco
@pytest.mark.django_db
def test_unidades_sem_pai_convivem() -> None:
    tipo_secretaria = _tipo(nome="Secretaria", nivel=30)
    raiz_a = _unidade(nome="Secretaria A", sigla="SECA", tipo=tipo_secretaria)
    raiz_b = _unidade(nome="Secretaria B", sigla="SECB", tipo=tipo_secretaria)

    assert raiz_a.pai is None
    assert raiz_b.pai is None


@banco
@pytest.mark.django_db
def test_unidade_nao_pode_ser_pai_de_si_mesma() -> None:
    unidade = _unidade()

    with pytest.raises(IntegrityError):
        Unidade.objects.filter(pk=unidade.pk).update(pai=unidade.pk)


@banco
@pytest.mark.django_db
def test_filhas_lista_as_unidades_subordinadas() -> None:
    tipo_departamento = _tipo(nome="Departamento", nivel=20)
    tipo_divisao = _tipo(nome="Divisão", nivel=10)
    departamento = _unidade(nome="Departamento", sigla="DPTO", tipo=tipo_departamento)
    divisao_1 = Unidade(nome="Divisão 1", sigla="DIV1", tipo=tipo_divisao, pai=departamento)
    divisao_1.full_clean()
    divisao_1.save()
    divisao_2 = Unidade(nome="Divisão 2", sigla="DIV2", tipo=tipo_divisao, pai=departamento)
    divisao_2.full_clean()
    divisao_2.save()
    outra_raiz = _unidade(nome="Outra Raiz", sigla="RAIZ2", tipo=tipo_departamento)

    assert set(departamento.filhas.all()) == {divisao_1, divisao_2}
    assert outra_raiz.filhas.count() == 0


@banco
@pytest.mark.django_db
def test_unidade_recusa_cor_fora_da_paleta_e_nasce_com_a_padrao() -> None:
    sem_cor = _unidade(nome="Sem Cor", sigla="SCOR")
    assert sem_cor.cor == CorUnidade.AGUA_700

    tipo = _tipo(nome="Departamento Cor Invalida", nivel=20)
    cor_invalida = Unidade(
        nome="Cor Invalida",
        sigla="CINV",
        tipo=tipo,
        cor="hex-livre-nao-existe",
    )
    with pytest.raises(ValidationError):
        cor_invalida.full_clean()


@banco
@pytest.mark.django_db
def test_cor_sugerida_vem_do_pai_e_cai_no_padrao_na_raiz() -> None:
    tipo_departamento = _tipo(nome="Departamento Sugestao", nivel=20)
    tipo_divisao = _tipo(nome="Divisao Sugestao", nivel=10)
    pai = _unidade(
        nome="Departamento Sugestao",
        sigla="DSUG",
        tipo=tipo_departamento,
        cor=CorUnidade.SAKURA_600,
    )
    filha = Unidade(
        nome="Divisao Sugestao",
        sigla="DIVS",
        tipo=tipo_divisao,
        pai=pai,
        cor=CorUnidade.ROCHA_700,
    )
    filha.full_clean()
    filha.save()

    assert filha.cor_sugerida == CorUnidade.SAKURA_600
    assert pai.cor_sugerida == CorUnidade.AGUA_700
