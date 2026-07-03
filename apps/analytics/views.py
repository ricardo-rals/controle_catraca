from datetime import datetime

from django.http import JsonResponse
from django.views import View
from .models import Evento  # ajuste para o modelo real usado no queryset
from .services import usuarios_frequentes


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
