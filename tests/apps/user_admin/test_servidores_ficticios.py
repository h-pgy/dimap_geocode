"""
Testes dos servidores fictícios (SPEC user_admin/013): o andaime que torna a listagem exercitável
no sistema. O que importa fixar é a borda que protege o banco — a remoção apaga a faixa de RF
reservada e nada além dela. A SPEC user_admin/015 estende o mesmo andaime para deixar
exercitáveis os estados de exercício e substituição, pela mesma porta dos atos (`exercicio.py`).

Marker `banco`: perfil, unidade e cargo são tabelas.
"""

from django.db.models import Q
from django.utils import timezone

import pytest

from apps.user_admin.exercicio import substituicao_vigente, substituicoes_do_impedimento
from apps.user_admin.ficticios import (
    FAIXA_RF_FICTICIA,
    QUANTIDADE_FICTICIOS,
    criar_servidores_ficticios,
    remover_servidores_ficticios,
)
from apps.unidades.models import CorUnidade, TipoUnidade, Unidade
from apps.cargos.models import CargoBase, CargoComissao
from apps.user_admin.models import (
    Impedimento,
    Perfil,
    TipoImpedimento,
)

banco = pytest.mark.banco


def _catalogos_gravados() -> Unidade:
    tipo = TipoUnidade.objects.create(
        nome="Divisão",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=2,
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


def _catalogo_diverso_para_exercicio() -> None:
    # Diversidade suficiente para o andaime distribuir os seis estados de exercício exigidos pela
    # SPEC user_admin/015 entre os fictícios: várias unidades titularizáveis, vários cargos e mais
    # de um tipo de impedimento.
    tipo_unidade = TipoUnidade.objects.create(
        nome="Divisão Fictícios Exercício",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )
    for indice in range(6):
        Unidade.objects.create(
            nome=f"Divisão Fictícios Exercício {indice}",
            sigla=f"DIVFE{indice}",
            tipo=tipo_unidade,
        )
    CargoBase.objects.create(nome="Analista Fictícios Exercício", sigla="ANFE")
    for indice, nivel in enumerate((1, 2, 3)):
        CargoComissao.objects.create(
            sigla=f"CD{indice}",
            nivel=nivel,
            e_chefia=True,
            nome=f"Diretor Fictícios Exercício {indice}",
        )
    for nome in ("Férias FE", "Licença FE", "Afastamento FE"):
        TipoImpedimento.objects.create(nome=nome)


@banco
@pytest.mark.django_db
def test_ficticios_deixam_os_estados_de_exercicio_exercitaveis() -> None:
    _catalogo_diverso_para_exercicio()

    criar_servidores_ficticios()

    hoje = timezone.localdate()
    ficticios = Perfil.objects.filter(rf__in=FAIXA_RF_FICTICIA)
    titulares_afastados = (
        ficticios.filter(e_titular=True)
        .filter(
            Q(impedimentos__data_inicio__lte=hoje)
            & (
                Q(impedimentos__data_fim__isnull=True)
                | Q(impedimentos__data_fim__gte=hoje)
            )
        )
        .distinct()
    )

    # Titular afastado com substituto e titular afastado sem substituto: os dois precisam existir.
    assert any(
        substituicao_vigente(titular) is not None for titular in titulares_afastados
    )
    assert any(substituicao_vigente(titular) is None for titular in titulares_afastados)

    # Afastamento com substitutos em sequência: mais de uma substituição do mesmo impedimento, com
    # ao menos uma já encerrada — é daí que sai o histórico da tela.
    impedimentos_ficticios = Impedimento.objects.filter(perfil__in=ficticios)
    assert any(
        substituicoes_do_impedimento(impedimento).count() > 1
        and substituicoes_do_impedimento(impedimento).filter(data_fim__lt=hoje).exists()
        for impedimento in impedimentos_ficticios
    )

    # Afastado com a substituição fora do ar: há vínculo gravado, mas nenhum vale hoje.
    assert any(
        perfil.esta_impedido
        and substituicao_vigente(perfil) is None
        and Impedimento.objects.filter(
            perfil=perfil, substituicoes__isnull=False
        ).exists()
        for perfil in ficticios
    )

    # Impedimento futuro já com substituto designado: a pessoa segue em exercício até a data
    # chegar, e a cobertura já está de pé.
    impedimento_futuro_designado = impedimentos_ficticios.filter(
        data_inicio__gt=hoje, substituicoes__isnull=False
    ).first()
    assert impedimento_futuro_designado is not None
    assert impedimento_futuro_designado.perfil.em_exercicio is True

    # O exonerado.
    assert ficticios.filter(is_active=False).exists()

    # Rodar de novo devolve todos ao exercício, em vez de acumular afastamento.
    total_impedimentos_antes = impedimentos_ficticios.count()
    criar_servidores_ficticios()
    assert (
        Impedimento.objects.filter(perfil__in=ficticios).count()
        == total_impedimentos_antes
    )
