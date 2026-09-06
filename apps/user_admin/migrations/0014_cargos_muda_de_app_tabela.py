"""
`CargoBase` e `CargoComissao` são renomeados para as tabelas que `apps.cargos` (SPEC
user_admin/028) vai assumir. É a única operação de banco de todo o porte — dali em diante, só
estado: o model continua morando aqui até a 0015 soltá-lo.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("user_admin", "0013_perfil_exonerado_tem_data"),
    ]

    operations = [
        migrations.AlterModelTable(name="cargobase", table="cargos_cargobase"),
        migrations.AlterModelTable(name="cargocomissao", table="cargos_cargocomissao"),
    ]
