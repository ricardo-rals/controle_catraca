from django.urls import path

from .views import ListaAcessosView

app_name = "acessos"

urlpatterns = [
    path("", ListaAcessosView.as_view(), name="lista"),
]
