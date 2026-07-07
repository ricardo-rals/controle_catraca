from django.http import JsonResponse
from django.views import View
from django.utils.dateparse import parse_date
from apps.acessos.models import RegistroAcesso
from apps.analytics.services import (
    picos_por_hora,
    top_dias,
    fluxo_por_tipo,
    fluxo_por_ponto,
)


class PicosAnalyticsView(View):
    def get(self, request, *args, **kwargs):
        queryset = RegistroAcesso.objects.all()

        data_inicio_str = request.GET.get("data_inicio")
        data_fim_str = request.GET.get("data_fim")

        if data_inicio_str:
            data_inicio = parse_date(data_inicio_str)
            if data_inicio:
                queryset = queryset.filter(timestamp__date__gte=data_inicio)

        if data_fim_str:
            data_fim = parse_date(data_fim_str)
            if data_fim:
                queryset = queryset.filter(timestamp__date__lte=data_fim)

        picos_hora_data = picos_por_hora(queryset)
        top_dias_data = top_dias(queryset)

        return JsonResponse({"picos_hora": picos_hora_data, "top_dias": top_dias_data})


def _aplicar_filtros_de_data(request, queryset):
    """Aplica data_inicio e data_fim do query param ao queryset.

    Extraído como função auxiliar para não duplicar a lógica
    entre FluxoTipoView e FluxoPontoView.
    """
    data_inicio_str = request.GET.get("data_inicio")
    data_fim_str = request.GET.get("data_fim")

    if data_inicio_str:
        data_inicio = parse_date(data_inicio_str)
        if data_inicio:
            queryset = queryset.filter(timestamp__date__gte=data_inicio)

    if data_fim_str:
        data_fim = parse_date(data_fim_str)
        if data_fim:
            queryset = queryset.filter(timestamp__date__lte=data_fim)

    return queryset


class FluxoTipoView(View):
    def get(self, request, *args, **kwargs):
        queryset = RegistroAcesso.objects.all()
        queryset = _aplicar_filtros_de_data(request, queryset)
        return JsonResponse(fluxo_por_tipo(queryset), safe=False)


class FluxoPontoView(View):
    def get(self, request, *args, **kwargs):
        queryset = RegistroAcesso.objects.select_related("ponto_acesso").all()
        queryset = _aplicar_filtros_de_data(request, queryset)
        return JsonResponse(fluxo_por_ponto(queryset), safe=False)
