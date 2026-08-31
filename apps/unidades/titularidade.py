"""
Atos e leituras de titularidade (SPEC user_admin/014): definir e destituir titular, em transação —
o caminho único que a tela (SPEC 016) e os fictícios chamam para essa escrita —, e quem a unidade
pode titularizar.

Escreve em `Perfil`, mas mora aqui porque a vaga é da unidade: é ela que fica sem direção, e é a
página dela que cobra a nomeação. Só os models de `unidades` seguem cegos a `user_admin` — a
dependência de mão única é entre os models, não entre os atos.
"""

from django.db import transaction

from apps.unidades.models import Unidade, cargo_titulariza
from apps.user_admin.models import Perfil


def definir_titular(perfil: Perfil) -> None:
    """Destitui o titular anterior — afastado ou não — e marca o novo na mesma transação: o índice
    recusa os dois marcados, ainda que por um instante."""
    with transaction.atomic():
        _destituir(perfil.unidade, exceto=perfil)
        perfil.e_titular = True
        # Depois da destituição: validate_constraints enxerga a transação e acusaria o anterior.
        perfil.full_clean()
        perfil.save(update_fields=["e_titular"])


def destituir_titular(unidade: Unidade) -> None:
    """Abre a vaga: a unidade fica sem titular, e é a tela que cobra a nomeação."""
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
    # update() em massa fura a validação, mas desmarcar nunca produz titular inválido.
    titulares = Perfil.objects.filter(unidade=unidade, e_titular=True)
    if exceto is not None and exceto.pk is not None:
        titulares = titulares.exclude(pk=exceto.pk)
    titulares.update(e_titular=False)
