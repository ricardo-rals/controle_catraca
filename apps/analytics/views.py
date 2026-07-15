# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_datetime
from apps.acessos.models import RegistroAcesso
from .services import volume_por_periodo

from datetime import datetime

from django.http import JsonResponse
from django.views import View

# from .models import Evento  # ajuste para o modelo real usado no queryset
from .services import usuarios_frequentes

from django.utils.dateparse import parse_date

from apps.analytics.services import (
    picos_por_hora,
    top_dias,
    fluxo_por_tipo,
    fluxo_por_ponto,
)


class VolumePorPeriodoView(APIView):
    def get(self, request):
        granularidade = request.query_params.get("granularidade", "dia")
        data_inicio = request.query_params.get("data_inicio")
        data_fim = request.query_params.get("data_fim")

        queryset = RegistroAcesso.objects.all()

        if data_inicio:
            inicio_parsed = parse_datetime(data_inicio)
            if inicio_parsed:
                queryset = queryset.filter(timestamp__gte=inicio_parsed)

        if data_fim:
            fim_parsed = parse_datetime(data_fim)
            if fim_parsed:
                queryset = queryset.filter(timestamp__lte=fim_parsed)

        try:
            dados = volume_por_periodo(queryset, granularidade)
            return Response(dados, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"erro": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FrequentesView(View):
    def get(self, request, *args, **kwargs):
        data_inicio = request.GET.get("data_inicio")
        data_fim = request.GET.get("data_fim")
        limite_raw = request.GET.get("limite", "20")

        try:
            limite = int(limite_raw)
            if limite <= 0:
                raise ValueError
        except ValueError:
            return JsonResponse(
                {"erro": "Parametro 'limite' deve ser um inteiro positivo."},
                status=400,
            )

        queryset = Evento.objects.all()

        if data_inicio:
            dt_inicio = self._parse_data(data_inicio)
            if dt_inicio is None:
                return JsonResponse(
                    {"erro": "Parametro 'data_inicio' invalido. Use YYYY-MM-DD."},
                    status=400,
                )
            queryset = queryset.filter(criado_em__date__gte=dt_inicio)

        if data_fim:
            dt_fim = self._parse_data(data_fim)
            if dt_fim is None:
                return JsonResponse(
                    {"erro": "Parametro 'data_fim' invalido. Use YYYY-MM-DD."},
                    status=400,
                )
            queryset = queryset.filter(criado_em__date__lte=dt_fim)

        resultado = usuarios_frequentes(queryset, limite=limite)

        return JsonResponse({"resultados": resultado}, status=200)

    @staticmethod
    def _parse_data(valor: str):
        try:
            return datetime.strptime(valor, "%Y-%m-%d").date()
        except ValueError:
            return None


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


from rest_framework.views import APIView


from .services import (
    fluxo_por_ponto,
    fluxo_por_tipo,
    picos_por_hora,
    top_dias,
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
