from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("usuarios/", views.listar_usuarios, name="listar_usuarios"),
    path("usuarios/novo/", views.criar_usuario, name="criar_usuario"),
    path(
        "usuarios/<int:usuario_id>/desativar/",
        views.desativar_usuario,
        name="desativar_usuario",
    ),
    # Endpoints de Autenticação JWT
    path(
        "api/token/",
        views.CustomTokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Rota dummy protegida
    path("api/dummy/", views.DummyProtectedView.as_view(), name="dummy_protected"),
]
