from django.urls import path

from .views import (
    FluxoPontoView,
    FluxoTipoView,
    FrequentesView,
    PicosAnalyticsView,
    VolumePorPeriodoView,
)

app_name = "analytics"

urlpatterns = [
    path("volume/", VolumePorPeriodoView.as_view(), name="volume"),
    path("picos/", PicosAnalyticsView.as_view(), name="picos"),
    path("frequentes/", FrequentesView.as_view(), name="frequentes"),
    path("fluxo-tipo/", FluxoTipoView.as_view(), name="fluxo-tipo"),
    path("fluxo-ponto/", FluxoPontoView.as_view(), name="fluxo-ponto"),
]
