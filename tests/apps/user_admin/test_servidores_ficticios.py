"""
Testes dos servidores fictícios (SPEC user_admin/013): o andaime que torna a listagem exercitável
no sistema. O que importa fixar é a borda que protege o banco — a remoção apaga a faixa de RF
reservada e nada além dela.

Marker `banco`: perfil, unidade e cargo são tabelas.
"""

import pytest

from apps.user_admin.ficticios import (
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
