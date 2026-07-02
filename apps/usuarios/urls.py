from django.urls import path
from . import views
from .views import FrequentesView

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("frequentes/", FrequentesView.as_view(), name="frequentes"),
]
