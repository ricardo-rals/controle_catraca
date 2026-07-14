from django.urls import path
from .views import RelatoriosView, relatorio_pdf, relatorio_excel

app_name = "relatorios"

urlpatterns = [
    path("", RelatoriosView.as_view(), name="relatorios"),
    path("pdf/", relatorio_pdf, name="relatorio_pdf"),
    path("excel/", relatorio_excel, name="relatorio_excel"),
]
