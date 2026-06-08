from django.contrib import admin
from .models import PontoAcesso, RegistroAcesso, Pessoa, RegraHorario


@admin.register(PontoAcesso)
class PontoAcessoAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "localizacao", "grupo_equipamento")
    search_fields = ("nome", "localizacao")


@admin.register(RegistroAcesso)
class RegistroAcessoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "identificador_pseudonimizado",
        "ponto_acesso",
        "tipo_acesso",
        "timestamp",
        "area_origem",
        "area_destino",
        "evento",
    )
    list_filter = ("tipo_acesso", "timestamp", "ponto_acesso")
    search_fields = ("identificador_pseudonimizado",)
    date_hierarchy = "timestamp"


@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    list_display = ("numero_credencial", "nome", "estrutura_organizacional")
    search_fields = ("numero_credencial", "nome")


@admin.register(RegraHorario)
class RegraHorarioAdmin(admin.ModelAdmin):
    list_display = ("grupo_equipamento", "dia_semana", "horario_inicio", "horario_fim")
    list_filter = ("grupo_equipamento",)
