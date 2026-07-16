from django.db import migrations, models


def recifrar_credenciais(apps, schema_editor):
    from apps.importacoes.utils.pseudonimizacao import (
        criptografar_valor,
        descriptografar_valor,
    )

    RegistroAcesso = apps.get_model("acessos", "RegistroAcesso")
    for registro in RegistroAcesso.objects.exclude(credencial_cifrada="").iterator():
        credencial_original = descriptografar_valor(registro.credencial_cifrada)
        registro.credencial_cifrada = criptografar_valor(
            credencial_original,
            deterministico=True,
        )
        registro.save(update_fields=["credencial_cifrada"])


class Migration(migrations.Migration):
    dependencies = [
        ("acessos", "0006_registroacesso_campos_cifrados"),
    ]

    operations = [
        migrations.RunPython(recifrar_credenciais, migrations.RunPython.noop),
        migrations.RemoveIndex(
            model_name="registroacesso",
            name="idx_ident_timestamp",
        ),
        migrations.RemoveField(
            model_name="registroacesso",
            name="identificador_pseudonimizado",
        ),
        migrations.AddIndex(
            model_name="registroacesso",
            index=models.Index(
                fields=["credencial_cifrada", "timestamp"],
                name="idx_cred_timestamp",
            ),
        ),
    ]
