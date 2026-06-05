# Register your models here.
from django.contrib import admin
from .models import Importacao

@admin.register(Importacao)
class ImportacaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'arquivo', 'data_importacao', 'status')