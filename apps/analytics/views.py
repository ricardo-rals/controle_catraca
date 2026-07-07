# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_datetime
from apps.acessos.models import RegistroAcesso
from .services import volume_por_periodo

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