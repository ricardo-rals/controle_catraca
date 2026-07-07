from django.urls import path

from . import views

app_name = "acessos"

urlpatterns = [
    path("", views.ListaAcessosView.as_view(), name="lista"),
    path("<int:pk>/", views.DetalheAcessoView.as_view(), name="detalhe"),
]
