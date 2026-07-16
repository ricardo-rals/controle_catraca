"""Seed de usuários de desenvolvimento: um admin e um gestor.

Idempotente — rodar de novo não duplica nem sobrescreve senha de usuário
existente. As senhas seguem os validadores do projeto (AUTH_PASSWORD_VALIDATORS);
podem ser trocadas por variável de ambiente.

Uso: python manage.py seed_usuarios
"""

import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()

USUARIOS = [
    {
        "username": "admin",
        "email": "admin@ifba.edu.br",
        "perfil": "admin",
        "env_senha": "SEED_ADMIN_PASSWORD",
        "senha_padrao": "Portaria@2026",
    },
    {
        "username": "gestor",
        "email": "gestor@ifba.edu.br",
        "perfil": "gestor",
        "env_senha": "SEED_GESTOR_PASSWORD",
        "senha_padrao": "Catraca@2026",
    },
]


class Command(BaseCommand):
    help = "Cria os usuários admin e gestor de desenvolvimento (idempotente)."

    def handle(self, *args, **options):
        for dados in USUARIOS:
            usuario, criado = User.objects.get_or_create(
                username=dados["username"],
                defaults={"email": dados["email"], "perfil": dados["perfil"]},
            )
            if not criado:
                self.stdout.write(f"já existe (inalterado): {dados['username']}")
                continue

            senha = os.environ.get(dados["env_senha"], dados["senha_padrao"])
            try:
                validate_password(senha, usuario)  # respeita os validadores do projeto
            except ValidationError as e:
                usuario.delete()
                raise CommandError(
                    f"Senha de '{dados['username']}' não passa nos validadores: "
                    + "; ".join(e.messages)
                )
            usuario.set_password(senha)
            usuario.save()
            self.stdout.write(
                self.style.SUCCESS(f"criado: {dados['username']} ({dados['perfil']})")
            )
