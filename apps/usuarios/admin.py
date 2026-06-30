# Register your models here.
from django.contrib import admin
from .models import UsuarioSistema


@admin.register(UsuarioSistema)
class UsuarioSistemaAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        # só permite se o usuário estiver logado e for admin
        return (
            request.user.is_authenticated
            and getattr(request.user, "perfil", None) == "admin"
        )

    list_display = [
        "username",
        "email",
        "first_name",
        "last_name",
        "perfil",
        "is_active",
    ]
