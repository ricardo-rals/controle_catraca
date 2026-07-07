from django.urls import path

from .views import RegistroAcessoListAPIView

urlpatterns = [
    path(
        "acessos/",
        RegistroAcessoListAPIView.as_view(),
        name="api-acessos",
    )
]