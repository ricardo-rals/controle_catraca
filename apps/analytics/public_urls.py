"""Rotas da API pública (HU-055), montadas em /api/public/.

Módulo separado de propósito: é ele que o schema público enxerga, então nada
que não deva sair para fora pode entrar aqui.
"""

from django.urls import path

from .public_views import FluxoPublicoView, PicosPublicoView, VolumePublicoView

app_name = "publica"

urlpatterns = [
    path("volume/", VolumePublicoView.as_view(), name="volume"),
    path("picos/", PicosPublicoView.as_view(), name="picos"),
    path("fluxo/", FluxoPublicoView.as_view(), name="fluxo"),
]
