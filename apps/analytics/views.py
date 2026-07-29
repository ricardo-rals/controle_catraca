from collections import defaultdict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.generic import ListView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.acessos.models import RegistroAcesso
from apps.usuarios.perfis import is_admin

from .forms import AnomaliasFiltroForm
from .models import Alerta
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

    Data ausente ou invalida e ignorada silenciosamente - o endpoint
    responde com o periodo completo.
    """
    data_inicio = parse_date(request.query_params.get("data_inicio") or "")
    data_fim = parse_date(request.query_params.get("data_fim") or "")

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


# ---------------------------------------------------------------------------
# HU-057 — tela de anomalias
# ---------------------------------------------------------------------------


def filtrar_alertas(params):
    """QuerySet de Alerta recortado por tipo e período (dict tipo request.GET)."""
    alertas = Alerta.objects.select_related(
        "registro",
        "registro__ponto_acesso",
        "registro_anterior",
        "registro_anterior__ponto_acesso",
    )

    tipo = params.get("tipo")
    if tipo in Alerta.Tipo.values:
        alertas = alertas.filter(tipo=tipo)

    data_inicio = parse_date(params.get("data_inicio") or "")
    data_fim = parse_date(params.get("data_fim") or "")
    if data_inicio:
        alertas = alertas.filter(data__gte=data_inicio)
    if data_fim:
        alertas = alertas.filter(data__lte=data_fim)

    return alertas


def resumir_por_tipo(alertas):
    """[(rótulo, total)] por tipo, do mais frequente para o menos."""
    contagem = alertas.values("tipo").annotate(total=Count("id")).order_by("-total")
    return [
        {
            "tipo": linha["tipo"],
            "rotulo": Alerta.Tipo(linha["tipo"]).label,
            "total": linha["total"],
        }
        for linha in contagem
    ]


def _montar_passagens(registros, tipos_por_registro):
    """Linha do tempo das passagens do grupo, com o intervalo entre elas.

    O detalhe mostra TODAS as passagens da sequência, não só as que dispararam
    alerta: uma sequência de N passagens gera N-1 alertas, e ver só os alertas
    esconde justamente a primeira passagem — a que dá sentido ao resto.
    """
    ordenados = sorted(registros.values(), key=lambda r: r.timestamp)
    passagens = []
    anterior = None

    for registro in ordenados:
        segundos = None
        if anterior is not None:
            segundos = int((registro.timestamp - anterior.timestamp).total_seconds())

        tipos = sorted(tipos_por_registro.get(registro.id, ()))
        passagens.append(
            {
                "registro": registro,
                "horario": timezone.localtime(registro.timestamp),
                "ponto": registro.ponto_acesso.nome if registro.ponto_acesso else "",
                "tipo_acesso": registro.get_tipo_acesso_display(),
                "segundos_da_anterior": segundos,
                "tipos": tipos,
                "anomala": bool(tipos),
            }
        )
        anterior = registro

    return passagens


def agrupar_por_pessoa_e_data(alertas):
    """Uma linha por (pessoa, data), com a sequência de passagens dentro (HU-057).

    Uma sequência de N passagens gera N-1 alertas, o que lido cru dá a
    impressão de faltar registro. Agrupado, a linha diz "4 passagens em 12s" e
    o detalhe abre a linha do tempo completa.

    Anomalia de dia inteiro (volume atípico) não tem pessoa: cai num grupo
    próprio, com credencial nula e sem passagens.
    """
    grupos = {}

    for alerta in alertas:
        registro = alerta.registro
        credencial = registro.credencial_cifrada if registro else ""
        chave = (alerta.data, credencial)

        grupo = grupos.get(chave)
        if grupo is None:
            grupo = grupos[chave] = {
                "data": alerta.data,
                "credencial_cifrada": credencial,
                "ocorrencias": [],
                "tipos": set(),
                "pontos": set(),
                "_registros": {},
                "_tipos_por_registro": defaultdict(set),
                "menor_intervalo": None,
            }

        grupo["ocorrencias"].append(alerta)
        grupo["tipos"].add(alerta.get_tipo_display())

        # O acesso sinalizado E o anterior entram na linha do tempo. Sem o
        # anterior, o detalhe mostraria 1 linha para "2 passagens".
        for envolvido in (alerta.registro, alerta.registro_anterior):
            if envolvido is not None:
                grupo["_registros"].setdefault(envolvido.id, envolvido)
                if envolvido.ponto_acesso:
                    grupo["pontos"].add(envolvido.ponto_acesso.nome)
        if registro is not None:
            grupo["_tipos_por_registro"][registro.id].add(alerta.get_tipo_display())

        if alerta.tipo == Alerta.Tipo.ACESSO_REPETIDO:
            atual = grupo["menor_intervalo"]
            if atual is None or alerta.valor < atual:
                grupo["menor_intervalo"] = alerta.valor

    for grupo in grupos.values():
        grupo["passagens"] = _montar_passagens(
            grupo.pop("_registros"), grupo.pop("_tipos_por_registro")
        )
        grupo["total_ocorrencias"] = len(grupo["ocorrencias"])
        grupo["total_passagens"] = len(grupo["passagens"])
        grupo["tipos"] = sorted(grupo["tipos"])
        grupo["pontos"] = sorted(grupo["pontos"])

    return sorted(
        grupos.values(), key=lambda g: (g["data"], g["total_ocorrencias"]), reverse=True
    )


class ListaAnomaliasView(LoginRequiredMixin, ListView):
    """Anomalias detectadas, agrupadas por pessoa e data (HU-057).

    O detalhe identifica pessoas, então só o **admin** recebe a lista. Outros
    perfis veem a contagem e a orientação de procurar o administrador — sem
    403, porque saber que existe anomalia é justamente o que o gestor precisa
    para escalar.
    """

    template_name = "analytics/anomalias.html"
    context_object_name = "grupos"
    paginate_by = 25

    def get_queryset(self):
        if not is_admin(self.request.user):
            return []
        alertas = filtrar_alertas(self.request.GET).order_by("-data", "tipo", "id")
        return agrupar_por_pessoa_e_data(alertas)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # A contagem é calculada sem o recorte por perfil: o gestor precisa
        # saber QUANTAS anomalias existem, só não vê quem as gerou.
        ctx["pode_ver_detalhe"] = is_admin(self.request.user)
        ctx["total_anomalias"] = filtrar_alertas(self.request.GET).count()
        ctx["form"] = AnomaliasFiltroForm(self.request.GET or None)

        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        return ctx
