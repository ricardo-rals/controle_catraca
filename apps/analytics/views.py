from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.acessos.models import RegistroAcesso

from .services import (
    fluxo_por_ponto,
    fluxo_por_tipo,
    picos_por_hora,
    top_dias,
    usuarios_frequentes,
    volume_por_periodo,
)


def _aplicar_filtros_de_data(request, queryset):
    """Aplica data_inicio e data_fim (YYYY-MM-DD) do query param ao queryset.

    Data ausente ou inválida é ignorada silenciosamente — o endpoint
    responde com o período completo.
    """
    data_inicio = parse_date(request.GET.get("data_inicio") or "")
    data_fim = parse_date(request.GET.get("data_fim") or "")

    if data_inicio:
        queryset = queryset.filter(timestamp__date__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(timestamp__date__lte=data_fim)

    return queryset


class VolumePorPeriodoView(APIView):
    def get(self, request):
        granularidade = request.query_params.get("granularidade", "dia")
        queryset = _aplicar_filtros_de_data(request, RegistroAcesso.objects.all())

        try:
            dados = volume_por_periodo(queryset, granularidade)
        except ValueError as e:
            return Response({"erro": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(dados)


class FrequentesView(APIView):
    def get(self, request):
        try:
            limite = int(request.query_params.get("limite", "20"))
            if limite <= 0:
                raise ValueError
        except ValueError:
            return Response(
                {"erro": "Parametro 'limite' deve ser um inteiro positivo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = _aplicar_filtros_de_data(request, RegistroAcesso.objects.all())
        return Response({"resultados": usuarios_frequentes(queryset, limite=limite)})


class PicosAnalyticsView(APIView):
    def get(self, request):
        queryset = _aplicar_filtros_de_data(request, RegistroAcesso.objects.all())
        return Response(
            {"picos_hora": picos_por_hora(queryset), "top_dias": top_dias(queryset)}
        )


class FluxoTipoView(APIView):
    def get(self, request):
        queryset = _aplicar_filtros_de_data(request, RegistroAcesso.objects.all())
        return Response(fluxo_por_tipo(queryset))


class FluxoPontoView(APIView):
    def get(self, request):
        queryset = _aplicar_filtros_de_data(
            request, RegistroAcesso.objects.select_related("ponto_acesso").all()
        )
        return Response(fluxo_por_ponto(queryset))
