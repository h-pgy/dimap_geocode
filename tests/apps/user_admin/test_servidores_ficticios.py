"""
Testes dos servidores fictícios (SPEC user_admin/013): o andaime que torna a listagem exercitável
no sistema. O que importa fixar é a borda que protege o banco — a remoção apaga a faixa de RF
reservada e nada além dela.

Marker `banco`: perfil, unidade e cargo são tabelas.
"""

import pytest

from apps.user_admin.ficticios import (
    FAIXA_RF_FICTICIA,
    QUANTIDADE_FICTICIOS,
    criar_servidores_ficticios,
    remover_servidores_ficticios,
)
from apps.user_admin.models import (
    CargoBase,
    CargoComissao,
    CorUnidade,
    Perfil,
    TipoImpedimento,
    TipoUnidade,
    Unidade,
)

banco = pytest.mark.banco


def _catalogos_gravados() -> Unidade:
    tipo = TipoUnidade.objects.create(
        nome="Divisão",
        nivel=10,
        pode_ser_raiz=True,
    )
    unidade = Unidade.objects.create(
        nome="Divisão de Mapeamento",
        sigla="DIMAP-1",
        tipo=tipo,
        cor=CorUnidade.AGUA_700,
    )
    CargoBase.objects.create(
        nome="Analista de Ordenamento Territorial",
        sigla="AOT",
    )
    CargoComissao.objects.create(
        sigla="CDA",
        nivel=2,
        e_chefia=True,
        nome="Diretor de Divisão",
    )
    TipoImpedimento.objects.create(
        nome="Férias",
        sigla="FER",
    )
    return unidade


@banco
@pytest.mark.django_db
def test_remover_ficticios_poupa_os_servidores_reais() -> None:
    unidade = _catalogos_gravados()
    real = Perfil.objects.create_user(
        rf="812345",
        nome="Servidor",
        sobrenome="de Verdade",
        cargo_base=CargoBase.objects.get(sigla="AOT"),
        unidade=unidade,
    )
    criar_servidores_ficticios()

    assert Perfil.objects.count() == QUANTIDADE_FICTICIOS + 1

    remocao = remover_servidores_ficticios()

    assert remocao.removidos == QUANTIDADE_FICTICIOS
    assert list(Perfil.objects.values_list("rf", flat=True)) == [real.rf]


@banco
@pytest.mark.django_db
def test_ficticios_titularizam_e_deixam_uma_unidade_vaga() -> None:
    tipo = TipoUnidade.objects.create(
        nome="Divisão Fictícios",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=4,
    )
    Unidade.objects.create(nome="Divisão Fictícios 1", sigla="DIVF1", tipo=tipo)
    Unidade.objects.create(nome="Divisão Fictícios 2", sigla="DIVF2", tipo=tipo)
    CargoBase.objects.create(nome="Analista Fictícios", sigla="ANF")
    CargoComissao.objects.create(
        sigla="CDA",
        nivel=4,
        e_chefia=True,
        nome="Diretor de Divisão Fictícios",
    )
    TipoImpedimento.objects.create(nome="Férias Fictícios", sigla="FERF")

    criar_servidores_ficticios()

    titulares = Perfil.objects.filter(rf__in=FAIXA_RF_FICTICIA, e_titular=True)
    assert titulares.exists()
    unidades_sem_titular = Unidade.objects.exclude(
        pk__in=titulares.values_list("unidade_id", flat=True)
    )
    assert unidades_sem_titular.exists()
