# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import UsuarioSistema

@admin.register(UsuarioSistema)
class UsuarioSistemaAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Permissões Customizadas', {'fields': ('perfil',)}),
    )
    list_display = ['username', 'email', 'first_name', 'last_name', 'perfil', 'is_active']