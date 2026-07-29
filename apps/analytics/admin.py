from django.contrib import admin, messages

from .models import Alerta, ChaveAPI


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ("data", "tipo", "valor", "detalhe", "criado_em")
    list_filter = ("tipo", "data")
    date_hierarchy = "data"
    readonly_fields = ("criado_em",)


@admin.register(ChaveAPI)
class ChaveAPIAdmin(admin.ModelAdmin):
    """Geração de chaves da API pública (HU-055).

    A chave em claro aparece UMA vez, na mensagem de confirmação da criação.
    Depois disso só existe o hash — não há como recuperá-la, só revogar e
    gerar outra.
    """

    list_display = ("nome", "prefixo", "ativa", "criado_em", "ultimo_uso")
    list_filter = ("ativa",)
    readonly_fields = ("prefixo", "criado_em", "ultimo_uso")

    def get_fields(self, request, obj=None):
        if obj is None:
            return ("nome",)
        return ("nome", "prefixo", "ativa", "criado_em", "ultimo_uso")

    def save_model(self, request, obj, form, change):
        if change:
            super().save_model(request, obj, form, change)
            return

        criada, chave_em_claro = ChaveAPI.criar(obj.nome)
        obj.pk = criada.pk
        self.message_user(
            request,
            f"Chave criada. Copie agora, ela não será exibida de novo: {chave_em_claro}",
            level=messages.WARNING,
        )
