from django.urls import path

from . import views

app_name = "relatorios"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("<slug:slug>/", views.detalhe, name="detalhe"),
    path("<slug:slug>/export/<str:formato>/", views.exportar, name="exportar"),
]
