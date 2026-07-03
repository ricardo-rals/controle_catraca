from django.urls import path

<<<<<<< HEAD
from . import views
=======
from .views import ListaAcessosView
>>>>>>> develop

app_name = "acessos"

urlpatterns = [
<<<<<<< HEAD
    path("<int:pk>/", views.DetalheAcessoView.as_view(), name="detalhe"),
    # path("", views.ListaAcessos.as_view(), name="lista"),  # reativar junto com a view acima
=======
    path("", ListaAcessosView.as_view(), name="lista"),
>>>>>>> develop
]
