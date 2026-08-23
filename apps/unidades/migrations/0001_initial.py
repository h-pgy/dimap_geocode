"""
`TipoUnidade` e `Unidade` mudam de app, não de tabela: as duas nascem aqui apenas no ESTADO das
migrações, apontando para os nomes que `user_admin` já criou. Nenhum DDL roda — quem renomeia as
tabelas de verdade é a 0002, depois que `user_admin` soltar os models do estado dele.
"""

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    # As tabelas adotadas aqui são as que `user_admin` criou até a 0009.
    dependencies = [
        ("user_admin", "0009_alter_perfil_rf_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="TipoUnidade",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("nome", models.CharField(max_length=60, unique=True)),
                        ("nivel", models.PositiveSmallIntegerField()),
                        ("pode_ser_raiz", models.BooleanField(default=False)),
                        ("exige_alta_administracao", models.BooleanField(default=False)),
                        (
                            "nivel_minimo_titular",
                            models.PositiveSmallIntegerField(
                                blank=True,
                                null=True,
                                validators=[
                                    django.core.validators.MinValueValidator(1),
                                    django.core.validators.MaxValueValidator(6),
                                ],
                            ),
                        ),
                        (
                            "tipos_filhos_vedados",
                            models.ManyToManyField(
                                blank=True,
                                related_name="vedado_como_filho_em",
                                to="unidades.tipounidade",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Tipo de unidade",
                        "verbose_name_plural": "Tipos de unidade",
                        # A tabela de origem, e com ela a do M2M, que o Django deriva desta.
                        "db_table": "user_admin_tipounidade",
                    },
                ),
                migrations.CreateModel(
                    name="Unidade",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("nome", models.CharField(max_length=120, unique=True)),
                        ("sigla", models.CharField(max_length=20, unique=True)),
                        (
                            "cor",
                            models.CharField(
                                choices=[
                                    ("agua-700", "Água 700"),
                                    ("agua-800", "Água 800"),
                                    ("rocha-700", "Rocha 700"),
                                    ("rocha-900", "Rocha 900"),
                                    ("madeira-600", "Madeira 600"),
                                    ("madeira-700", "Madeira 700"),
                                    ("sakura-600", "Sakura 600"),
                                    ("sakura-700", "Sakura 700"),
                                ],
                                default="agua-700",
                                max_length=20,
                            ),
                        ),
                        (
                            "pai",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="filhas",
                                to="unidades.unidade",
                            ),
                        ),
                        (
                            "tipo",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="unidades",
                                to="unidades.tipounidade",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Unidade",
                        "verbose_name_plural": "Unidades",
                        "db_table": "user_admin_unidade",
                    },
                ),
                migrations.AddConstraint(
                    model_name="tipounidade",
                    constraint=models.CheckConstraint(
                        condition=models.Q(
                            models.Q(
                                ("exige_alta_administracao", True),
                                ("nivel_minimo_titular__isnull", True),
                            ),
                            models.Q(
                                ("exige_alta_administracao", False),
                                ("nivel_minimo_titular__gte", 1),
                                ("nivel_minimo_titular__lte", 6),
                            ),
                            _connector="OR",
                        ),
                        name="tipo_unidade_minimo_conforme_alta_administracao",
                    ),
                ),
                migrations.AddConstraint(
                    model_name="unidade",
                    constraint=models.CheckConstraint(
                        condition=models.Q(("pai", models.F("id")), _negated=True),
                        name="unidade_nao_e_pai_de_si_mesma",
                    ),
                ),
            ],
        ),
    ]
