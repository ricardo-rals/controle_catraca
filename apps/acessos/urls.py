from django.urls import path

from . import views

app_name = "acessos"

urlpatterns = [
    path("<int:pk>/", views.DetalheAcessoView.as_view(), name="detalhe"),
    # path("", views.ListaAcessos.as_view(), name="lista"),  # reativar junto com a view acima
]
