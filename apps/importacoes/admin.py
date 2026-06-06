from django.contrib import admin
from .models import Importacao


@admin.register(Importacao)
class ImportacaoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome_arquivo",
        "data_tentativa",
        "linha_arquivo",
        "motivo_erro",
    )
    list_filter = ("data_tentativa",)
    search_fields = ("nome_arquivo", "motivo_erro")
