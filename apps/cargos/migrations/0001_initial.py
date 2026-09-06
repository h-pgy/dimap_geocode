"""
`CargoBase` e `CargoComissao` nascem aqui só no ESTADO (SPEC user_admin/028): a tabela já existe,
renomeada pela 0014 de `user_admin`. `CreateModel` de verdade tentaria criar por cima dela.
"""

import django.core.validators
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("user_admin", "0014_cargos_muda_de_app_tabela"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="CargoBase",
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
                    ],
                    options={
                        "verbose_name": "Cargo base",
                        "verbose_name_plural": "Cargos base",
                    },
                ),
                migrations.CreateModel(
                    name="CargoComissao",
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
                        ("sigla", models.CharField(max_length=20)),
                        (
                            "nivel",
                            models.PositiveSmallIntegerField(
                                blank=True,
                                null=True,
                                validators=[
                                    django.core.validators.MinValueValidator(1),
                                    django.core.validators.MaxValueValidator(6),
                                ],
                            ),
                        ),
                        ("e_chefia", models.BooleanField()),
                        ("alta_administracao", models.BooleanField(default=False)),
                        ("nome", models.CharField(max_length=200, unique=True)),
                    ],
                    options={
                        "verbose_name": "Cargo em comissão",
                        "verbose_name_plural": "Cargos em comissão",
                        "constraints": [
                            models.CheckConstraint(
                                condition=(
                                    Q(alta_administracao=True, nivel__isnull=True)
                                    | Q(alta_administracao=False, nivel__gte=1, nivel__lte=6)
                                ),
                                name="cargo_comissao_nivel_conforme_alta_administracao",
                            ),
                            models.CheckConstraint(
                                condition=Q(alta_administracao=False) | Q(e_chefia=True),
                                name="cargo_comissao_alta_administracao_e_chefia",
                            ),
                        ],
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
