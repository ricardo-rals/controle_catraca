from django.urls import path

from . import views

app_name = "acessos"

urlpatterns = [
    path("", views.ListaAcessosView.as_view(), name="lista"),
    # Regras de horário (admin) — antes de <int:pk> por clareza.
    path("regras/", views.RegraHorarioListView.as_view(), name="regras_lista"),
    path("regras/nova/", views.RegraHorarioCreateView.as_view(), name="regras_nova"),
    path(
        "regras/<int:pk>/editar/",
        views.RegraHorarioUpdateView.as_view(),
        name="regras_editar",
    ),
    path(
        "regras/<int:pk>/remover/",
        views.RegraHorarioDeleteView.as_view(),
        name="regras_remover",
    ),
    path("<int:pk>/", views.DetalheAcessoView.as_view(), name="detalhe"),
]
