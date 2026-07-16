"""Teste do comando seed_usuarios (idempotente)."""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command


@pytest.mark.django_db
def test_seed_usuarios_cria_admin_e_gestor_idempotente():
    call_command("seed_usuarios")
    call_command("seed_usuarios")  # rodar de novo não pode duplicar

    User = get_user_model()
    assert User.objects.filter(username="admin", perfil="admin").count() == 1
    assert User.objects.filter(username="gestor", perfil="gestor").count() == 1
    assert User.objects.get(username="admin").check_password("Portaria@2026")
