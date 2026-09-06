"""
Fecha a mudança de app: as duas tabelas passam a se chamar pelo app que agora as declara, e as
linhas de `django_content_type` acompanham — sem isso o `migrate` seguinte criaria um content type
novo, e as `Permission` já emitidas continuariam penduradas no `app_label` velho.
"""

from django.db import migrations

MODELOS = ("tipounidade", "unidade")
APP_ANTIGO = "user_admin"
APP_NOVO = "unidades"


def _mover_content_types(de: str, para: str):
    def operacao(apps, schema_editor) -> None:  # type: ignore[no-untyped-def]
        ContentType = apps.get_model("contenttypes", "ContentType")
        for modelo in MODELOS:
            # Linha já criada por um migrate anterior tornaria o UPDATE violação de unicidade.
            if ContentType.objects.filter(app_label=para, model=modelo).exists():
                continue
            ContentType.objects.filter(app_label=de, model=modelo).update(app_label=para)

    return operacao


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        # Depois que user_admin soltou os models: renomear antes deixaria o estado dele apontando
        # para uma tabela que não existe mais.
        ("user_admin", "0010_unidade_muda_de_app"),
        ("unidades", "0001_initial"),
    ]

    operations = [
        # O Postgres leva as FKs junto: constraint segue a tabela, não o nome dela.
        migrations.AlterModelTable(name="tipounidade", table=None),
        migrations.AlterModelTable(name="unidade", table=None),
        migrations.RunPython(
            _mover_content_types(APP_ANTIGO, APP_NOVO),
            _mover_content_types(APP_NOVO, APP_ANTIGO),
        ),
    ]
