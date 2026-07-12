from django.shortcuts import render
from datetime import date, timedelta
from .services import volume_por_periodo


def dashboard_volume(request):
    # Intervalo padrão: últimos 30 dias
    fim = date.today()
    inicio = fim - timedelta(days=30)

    # Permite período customizado via querystring
    inicio_param = request.GET.get("inicio")
    fim_param = request.GET.get("fim")
    if inicio_param and fim_param:
        inicio = date.fromisoformat(inicio_param)
        fim = date.fromisoformat(fim_param)

    # Granularidade automática baseada no tamanho do intervalo
    dias_intervalo = (fim - inicio).days
    if dias_intervalo <= 31:
        granularidade = "dia"
    elif dias_intervalo <= 180:
        granularidade = "semana"
    else:
        granularidade = "mes"

    dados = volume_por_periodo(inicio, fim, granularidade)
    # Formato esperado: [{"periodo": "2026-06-01", "total": 152}, ...]

    context = {
        "dados_volume": dados,
        "granularidade": granularidade,
    }
    return render(request, "dashboard/volume.html", context)
