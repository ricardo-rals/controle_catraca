from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("acessos", "0005_remove_registroacesso_nome_cifrado"),
    ]

    operations = [
        migrations.AddField(
            model_name="registroacesso",
            name="credencial_cifrada",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="registroacesso",
            name="nome_cifrado",
            field=models.TextField(blank=True, default=""),
        ),
    ]
