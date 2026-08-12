"""
Atos de titularidade (SPEC user_admin/014): definir e destituir titular, em transação — o caminho
único que a tela (SPEC 016) e os fictícios chamam para essa escrita.
"""

from django.db import transaction

from apps.user_admin.models import Perfil, Unidade


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


def _destituir(unidade: Unidade, exceto: Perfil | None = None) -> None:
    # update() em massa fura a validação, mas desmarcar nunca produz titular inválido.
    titulares = Perfil.objects.filter(unidade=unidade, e_titular=True)
    if exceto is not None and exceto.pk is not None:
        titulares = titulares.exclude(pk=exceto.pk)
    titulares.update(e_titular=False)
