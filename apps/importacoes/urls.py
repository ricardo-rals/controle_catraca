from django.urls import path

from .views import importar_csv

urlpatterns = [path("", importar_csv, name="importar_csv")]
