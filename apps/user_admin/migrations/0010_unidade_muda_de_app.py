"""
`TipoUnidade` e `Unidade` saem do estado deste app — as tabelas continuam onde estão, e agora
respondem por `unidades` (0001). Só estado: nenhum DDL roda aqui.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        # Depois que competências e unidades já apontam para o app novo.
        ("competencias", "0003_unidade_muda_de_app"),
        ("unidades", "0001_initial"),
        ("user_admin", "0009_alter_perfil_rf_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="tipounidade",
                    name="tipo_unidade_minimo_conforme_alta_administracao",
                ),
                migrations.RemoveConstraint(
                    model_name="unidade",
                    name="unidade_nao_e_pai_de_si_mesma",
                ),
                migrations.AlterField(
                    model_name="perfil",
                    name="unidade",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="perfis",
                        to="unidades.unidade",
                    ),
                ),
                migrations.RemoveField(
                    model_name="unidade",
                    name="pai",
                ),
                migrations.RemoveField(
                    model_name="unidade",
                    name="tipo",
                ),
                migrations.DeleteModel(name="TipoUnidade"),
                migrations.DeleteModel(name="Unidade"),
            ],
        ),
    ]
