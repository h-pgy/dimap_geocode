"""
`CargoBase` e `CargoComissao` somem do estado deste app: `Perfil` passa a apontar para
`apps.cargos` (SPEC user_admin/028). Só estado — a coluna `cargo_base_id`/`cargo_comissao_id`
continua a mesma, e a tabela já foi renomeada pela 0014. Depende de `competencias` já ter soltado
as FKs de `Concessao`/`ExecucaoAcao`: apagar o model daqui antes deixaria o estado dele apontando
para um model inexistente.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cargos", "0001_initial"),
        ("competencias", "0006_cargos_muda_de_app"),
        ("user_admin", "0014_cargos_muda_de_app_tabela"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="perfil",
                    name="cargo_base",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="perfis",
                        to="cargos.cargobase",
                    ),
                ),
                migrations.AlterField(
                    model_name="perfil",
                    name="cargo_comissao",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="perfis",
                        to="cargos.cargocomissao",
                    ),
                ),
                migrations.DeleteModel(name="CargoBase"),
                migrations.DeleteModel(name="CargoComissao"),
            ],
            database_operations=[],
        ),
    ]
