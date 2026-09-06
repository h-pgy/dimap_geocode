"""
As FKs de `Concessao` e `ExecucaoAcao` para cargo passam a nomear o app `cargos` (SPEC
user_admin/028). A tabela apontada é a mesma de sempre — renomeada pela 0014 de `user_admin` — e
só o estado muda.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cargos", "0001_initial"),
        ("competencias", "0005_atribuicaounidade_extinta_em_concessao_extinta_em"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="concessao",
                    name="cargo_base",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="concessoes",
                        to="cargos.cargobase",
                    ),
                ),
                migrations.AlterField(
                    model_name="concessao",
                    name="cargo_comissao",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="concessoes",
                        to="cargos.cargocomissao",
                    ),
                ),
                migrations.AlterField(
                    model_name="execucaoacao",
                    name="cargo_base",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="acoes_executadas",
                        to="cargos.cargobase",
                    ),
                ),
                migrations.AlterField(
                    model_name="execucaoacao",
                    name="cargo_comissao",
                    field=models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="acoes_executadas",
                        to="cargos.cargocomissao",
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
