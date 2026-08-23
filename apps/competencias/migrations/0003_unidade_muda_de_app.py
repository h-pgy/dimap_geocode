"""
As três FKs para `Unidade` passam a nomear o app `unidades`. A tabela apontada é a mesma, e por
isso nada roda no banco: só o estado das migrações muda.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("competencias", "0002_execucaoacao"),
        ("unidades", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="atribuicaounidade",
                    name="unidade",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="atribuicoes",
                        to="unidades.unidade",
                    ),
                ),
                migrations.AlterField(
                    model_name="execucaoacao",
                    name="unidade",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="acoes_executadas",
                        to="unidades.unidade",
                    ),
                ),
            ],
        ),
    ]
