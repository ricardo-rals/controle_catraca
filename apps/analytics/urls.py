from django.urls import path
from .views import VolumePorPeriodoView
from .views import PicosAnalyticsView, FluxoTipoView, FluxoPontoView

app_name = "analytics"

urlpatterns = [
    path("volume/", VolumePorPeriodoView.as_view(), name="volume"),
    path("picos/", PicosAnalyticsView.as_view(), name="picos"),
    path("fluxo-tipo/", FluxoTipoView.as_view()),
    path("fluxo-ponto/", FluxoPontoView.as_view()),
]
