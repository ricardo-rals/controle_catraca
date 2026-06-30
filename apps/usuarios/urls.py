from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("usuarios/novo/", views.criar_usuario, name="criar_usuario"),
    path(
        "usuarios/<int:usuario_id>/desativar/",
        views.desativar_usuario,
        name="desativar_usuario",
    ),
    path("usuarios/", views.ListarUsuariosView.as_view(), name="listar_usuarios"),
]
