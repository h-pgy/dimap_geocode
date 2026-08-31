"""
Migração de dados (SPEC user_admin/027, Caveats): preenche `exonerado_em` de quem já está com
`is_active=False`, antes da `CheckConstraint` da migração seguinte tornar a discordância entre os
dois campos impossível de gravar. A data real do ato não é conhecida — usa-se o dia da migração
como marca de "já estava fora do quadro antes desta SPEC", não a data verdadeira de exoneração.
"""

from django.db import migrations
from django.utils import timezone


def preencher_exonerado_em(apps, schema_editor):
    Perfil = apps.get_model("user_admin", "Perfil")
    Perfil.objects.filter(is_active=False, exonerado_em__isnull=True).update(
        exonerado_em=timezone.localdate()
    )


def reverter(apps, schema_editor):
    # Não desfaz o preenchimento: apagar a data reabriria a mesma discordância que esta migração
    # existe para fechar, e a constraint da migração seguinte já teria sido removida antes dela.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('user_admin', '0011_exonerado_em'),
    ]

    operations = [
        migrations.RunPython(preencher_exonerado_em, reverter),
    ]
