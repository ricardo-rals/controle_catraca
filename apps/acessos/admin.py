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
        "nome_exibicao",
        "credencial_exibicao",
        "ponto_acesso",
        "tipo_acesso",
        "timestamp",
        "area_origem",
        "area_destino",
        "evento",
    )
    list_filter = ("tipo_acesso", "timestamp", "ponto_acesso")
    search_fields = ()
    date_hierarchy = "timestamp"
    readonly_fields = (
        "nome_exibicao",
        "credencial_exibicao",
    )

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        termo = (search_term or "").strip()
        if not termo:
            return queryset, use_distinct

        from apps.importacoes.utils.pseudonimizacao import criptografar_valor

        return queryset.filter(
            credencial_cifrada=criptografar_valor(termo, deterministico=True)
        ), use_distinct

    @admin.display(description="Nome")
    def nome_exibicao(self, obj):
        return obj.nome_descriptografado() or "—"

    @admin.display(description="Credencial")
    def credencial_exibicao(self, obj):
        return obj.credencial_descriptografada() or "—"


@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    list_display = ("numero_credencial", "nome", "estrutura_organizacional")
    search_fields = ("numero_credencial", "nome")


@admin.register(RegraHorario)
class RegraHorarioAdmin(admin.ModelAdmin):
    list_display = ("grupo_equipamento", "dia_semana", "horario_inicio", "horario_fim")
    list_filter = ("grupo_equipamento",)
