from django.contrib.auth.models import AbstractUser
from django.db import models


class UsuarioSistema(AbstractUser):
    PERFIL_CHOICES = (
        ("admin", "Administrador"),
        ("gestor", "Gestor"),
    )
    perfil = models.CharField(
        "Perfil", max_length=20, choices=PERFIL_CHOICES, default="gestor"
    )
    # perguntar o perfil do usuario
    REQUIRED_FIELDS = ["email", "perfil"]

    class Meta:
        verbose_name = "Usuário do Sistema"
        verbose_name_plural = "Usuários do Sistema"

    def save(self, *args, **kwargs):
        # HU-013: perfil "admin" acessa o Django Admin; "gestor" não.
        # Superusuários mantêm acesso sempre.
        if not self.is_superuser:
            self.is_staff = self.perfil == "admin"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_perfil_display()})"
