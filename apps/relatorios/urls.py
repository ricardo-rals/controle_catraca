from django.urls import path
from .views import lista, detalhe, exportar

app_name = "relatorios"

urlpatterns = [
    path("", lista, name="lista"),
    path("<slug:slug>/", detalhe, name="detalhe"),
    path("<slug:slug>/export/<str:formato>/", exportar, name="exportar"),
]
