# SPEC user_admin/006: nome e sobrenome separados (a inicial do avatar exige a separação) e foto
# opcional. `sobrenome` nasce nulo para caber a carga já existente, é repartido a partir do
# `nome` atual e só então vira obrigatório — mesmo padrão de migração de dados da 0003.

from django.db import migrations, models


def repartir_nome_em_nome_e_sobrenome(apps, schema_editor):
    Perfil = apps.get_model("user_admin", "Perfil")
    for perfil in Perfil.objects.filter(sobrenome__isnull=True):
        termos = perfil.nome.split(maxsplit=1)
        perfil.nome = termos[0] if termos else ""
        perfil.sobrenome = termos[1] if len(termos) > 1 else ""
        perfil.save(update_fields=["nome", "sobrenome"])


class Migration(migrations.Migration):

    dependencies = [
        ("user_admin", "0004_unidade_cor"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfil",
            name="foto",
            field=models.ImageField(blank=True, null=True, upload_to="perfis/fotos/"),
        ),
        migrations.AddField(
            model_name="perfil",
            name="sobrenome",
            field=models.CharField(max_length=150, null=True),
        ),
        migrations.RunPython(
            repartir_nome_em_nome_e_sobrenome,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="perfil",
            name="sobrenome",
            field=models.CharField(max_length=150),
        ),
        migrations.AlterField(
            model_name="perfil",
            name="nome",
            field=models.CharField(max_length=100),
        ),
    ]
