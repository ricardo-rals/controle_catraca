"""Endpoints da API pública (HU-055).

Só dados **agregados**. Nada aqui devolve credencial, nome ou qualquer valor
por pessoa — nem em texto claro, nem cifrado: como a cifra da credencial é
determinística, publicá-la daria um identificador estável por pessoa a
qualquer portador de chave, permitindo rastrear a mesma pessoa entre
respostas. Por isso `usuarios_frequentes` ficou de fora desta API.
"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.acessos.models import RegistroAcesso

from .permissions import TemChaveAPIValida
from .services import (
    fluxo_por_ponto,
    fluxo_por_tipo,
    picos_por_hora,
    top_dias,
    volume_por_periodo,
)
from .views import _aplicar_filtros_de_data

PARAMS_DATA = [
    OpenApiParameter(
        "data_inicio", str, description="Filtro inicial no formato YYYY-MM-DD."
    ),
    OpenApiParameter(
        "data_fim", str, description="Filtro final no formato YYYY-MM-DD."
    ),
]


class _APIPublica(APIView):
    """Base dos endpoints públicos: sem sessão/JWT, só chave + rate limit."""

    authentication_classes = []
    permission_classes = [TemChaveAPIValida]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "api_publica"


class VolumePublicoView(_APIPublica):
    @extend_schema(
        summary="Volume de acessos por período",
        description="Total de acessos agregado por dia, semana ou mês.",
        parameters=PARAMS_DATA
        + [
            OpenApiParameter(
                "granularidade",
                str,
                description="dia (padrão), semana ou mes.",
            )
        ],
    )
    def get(self, request):
        granularidade = request.query_params.get("granularidade", "dia")
        queryset = _aplicar_filtros_de_data(request, RegistroAcesso.objects.all())
        try:
            dados = volume_por_periodo(queryset, granularidade)
        except ValueError as exc:
            return Response({"erro": str(exc)}, status=400)
        return Response({"resultados": dados})


class PicosPublicoView(_APIPublica):
    @extend_schema(
        summary="Distribuição por hora e dias de maior volume",
        description="Acessos por hora do dia (24 posições) e os dias de pico.",
        parameters=PARAMS_DATA,
    )
    def get(self, request):
        queryset = _aplicar_filtros_de_data(request, RegistroAcesso.objects.all())
        return Response(
            {"picos_hora": picos_por_hora(queryset), "top_dias": top_dias(queryset)}
        )


class FluxoPublicoView(_APIPublica):
    @extend_schema(
        summary="Fluxo por tipo e por ponto de acesso",
        description="Composição entre entradas e saídas e total por catraca.",
        parameters=PARAMS_DATA,
    )
    def get(self, request):
        queryset = _aplicar_filtros_de_data(
            request, RegistroAcesso.objects.select_related("ponto_acesso").all()
        )
        return Response(
            {
                "por_tipo": fluxo_por_tipo(queryset),
                "por_ponto": fluxo_por_ponto(queryset),
            }
        )
