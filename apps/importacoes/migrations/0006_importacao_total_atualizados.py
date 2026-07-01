from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("importacoes", "0005_falhaimportacao"),
    ]

    operations = [
        migrations.AddField(
            model_name="importacao",
            name="total_atualizados",
            field=models.IntegerField(default=0),
        ),
    ]
