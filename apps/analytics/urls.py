from django.urls import path
from .views import VolumePorPeriodoView

urlpatterns = [
    path("volume/", VolumePorPeriodoView.as_view(), name="volume"),
]