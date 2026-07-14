from django.urls import path

from . import views

app_name = "relatorios"

urlpatterns = [
    path("pdf/", views.relatorio_pdf, name="pdf"),
    path("excel/", views.relatorio_excel,name="excel"),
]
