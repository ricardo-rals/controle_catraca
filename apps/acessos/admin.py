# Register your models here.
from django.contrib import admin
from .models import PontoAcesso, RegistroAcesso

@admin.register(PontoAcesso)
class PontoAcessoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'localizacao')
    search_fields = ('nome', 'localizacao')

@admin.register(RegistroAcesso)
class RegistroAcessoAdmin(admin.ModelAdmin):
    list_display = ('id', 'identificador_pseudonimizado', 'ponto_acesso', 'tipo_acesso', 'timestamp', 'importacao')
    list_filter = ('tipo_acesso', 'ponto_acesso', 'timestamp')
    search_fields = ('identificador_pseudonimizado',)