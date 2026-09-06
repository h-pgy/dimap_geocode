"""
Atos e leituras de titularidade (SPEC user_admin/014): definir e destituir titular, em transação —
o caminho único que a tela (SPEC 016) e os fictícios chamam para essa escrita —, e quem a unidade
pode titularizar.

Escreve em `Perfil`, mas mora aqui porque a vaga é da unidade: é ela que fica sem direção, e é a
página dela que cobra a nomeação. Só os models de `unidades` seguem cegos a `user_admin` — a
dependência de mão única é entre os models, não entre os atos.
"""

from datetime import date

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.unidades.models import Unidade, cargo_titulariza
from apps.user_admin.models import Perfil


def definir_titular(perfil: Perfil) -> None:
    """Destitui o anterior (com encerramentos) e marca o novo na mesma transação atômica."""
    with transaction.atomic():
        _destituir(perfil.unidade, exceto=perfil)
        perfil.e_titular = True
        perfil.full_clean()
        perfil.save(update_fields=["e_titular"])


def destituir_titular(unidade: Unidade) -> None:
    """Abre a vaga na unidade e encerra delegações estruturais e substituições vigentes."""
    with transaction.atomic():
        _destituir(unidade)


def candidatos_a_titular(unidade: Unidade) -> list[Perfil]:
    """Quem a unidade pode titularizar: o filtro estreita, o domínio decide.

    SPEC user_admin/027: exonerado não recebe nada de novo, e titularidade não é exceção — o mesmo
    `is_active=True` que `candidatos_a_delegado` já aplica."""
    lotados = Perfil.objects.filter(
        unidade=unidade,
        cargo_comissao__isnull=False,
        is_active=True,
    ).select_related("cargo_comissao")
    return [
        perfil
        for perfil in lotados
        if cargo_titulariza(
            perfil.cargo_comissao,
            exige_alta_administracao=unidade.tipo.exige_alta_administracao,
            nivel_minimo=unidade.tipo.nivel_minimo_titular,
        )
    ]


def _destituir(unidade: Unidade, exceto: Perfil | None = None) -> None:
    hoje = timezone.localdate()
    titulares = Perfil.objects.filter(unidade=unidade, e_titular=True)
    if exceto is not None and exceto.pk is not None:
        titulares = titulares.exclude(pk=exceto.pk)
    for titular in titulares:
        _encerrar_substituicoes_de_titularidade(titular, hoje)
    _encerrar_delegacoes_da_unidade(unidade, hoje)
    titulares.update(e_titular=False)


def _encerrar_delegacoes_da_unidade(unidade: Unidade, hoje: date) -> None:
    from apps.competencias.models.delegacao import Delegacao

    vigentes = Delegacao.objects.filter(unidade=unidade, data_inicio__lte=hoje).filter(
        Q(data_fim__isnull=True) | Q(data_fim__gt=hoje)
    )
    vigentes.update(data_fim=hoje)
    Delegacao.objects.filter(unidade=unidade, data_inicio__gt=hoje).delete()


def _encerrar_substituicoes_de_titularidade(titular: Perfil, hoje: date) -> None:
    from apps.user_admin.models import Substituicao

    vigentes = Substituicao.objects.filter(
        impedimento__perfil=titular,
        data_inicio__lte=hoje,
    ).filter(Q(data_fim__isnull=True) | Q(data_fim__gt=hoje))
    vigentes.update(data_fim=hoje)
    Substituicao.objects.filter(
        impedimento__perfil=titular,
        data_inicio__gt=hoje,
    ).delete()

