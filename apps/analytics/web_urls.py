"""Rotas de tela do analytics (HU-057), separadas das rotas de API."""

from django.urls import path

from .views import ListaAnomaliasView

app_name = "anomalias"

urlpatterns = [
    path("", ListaAnomaliasView.as_view(), name="lista"),
]
