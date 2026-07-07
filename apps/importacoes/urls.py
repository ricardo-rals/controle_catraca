from django.urls import path

from .views import importar_csv, dashboard_importacoes_view, exportar_erros_csv_view

urlpatterns = [
    path("", importar_csv, name="importar_csv"),
    path("dashboard/", dashboard_importacoes_view, name="dashboard"),
    path(
        "dashboard/<int:importacao_id>/",
        dashboard_importacoes_view,
        name="dashboard_detalhe",
    ),
    path(
        "<int:importacao_id>/exportar-erros/",
        exportar_erros_csv_view,
        name="exportar_erros_csv",
    ),
]
