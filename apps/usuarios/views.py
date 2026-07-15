from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date
from .models import UsuarioSistema
from django.shortcuts import redirect
from .forms import UsuarioSistemaForm
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.acessos.models import RegistroAcesso
from django.views.generic import ListView
from .mixins import PerfilRequeridoMixin, perfil_requerido
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import CustomTokenObtainPairSerializer
from apps.analytics import services as analytics_service


# classe resposnsavel por listar os usuarios do sistema, apenas para o perfil admin.
class ListarUsuariosView(LoginRequiredMixin, PerfilRequeridoMixin, ListView):
    model = UsuarioSistema
    template_name = "usuarios/listar_usuarios.html"
    context_object_name = "usuarios"
    perfil_requerido = "admin"

    def get_queryset(self):
        return UsuarioSistema.objects.all().defer("password")


# classe responsavel por gerar o relatorio do gestor, apenas para o perfil gestor.
class RelatorioGestorView(LoginRequiredMixin, PerfilRequeridoMixin, ListView):
    model = UsuarioSistema  # ou outro modelo de dados que gestores precisam
    template_name = "usuarios/dashboard.html"
    context_object_name = "dados"
    perfil_requerido = "gestor"


# login view personalizada para redirecionar os usuários com base em seu perfil após o login.
class CustomLoginView(LoginView):
    template_name = "usuarios/login.html"

    redirect_authenticated_user = True

    def get_success_url(self):
        perfil = getattr(self.request.user, "perfil", None)
        if perfil == "admin":
            return reverse_lazy("listar_usuarios")
        elif perfil == "gestor":
            return reverse_lazy("relatorio_gestor")
        return reverse_lazy("dashboard")


@login_required
@perfil_requerido("admin")
def criar_usuario(request):

    if request.method == "POST":

        form = UsuarioSistemaForm(request.POST)

        if form.is_valid():

            usuario = form.save(commit=False)

            usuario.set_password(form.cleaned_data["senha"])

            usuario.save()
            return redirect("listar_usuarios")

    else:

        form = UsuarioSistemaForm()

    return render(request, "usuarios/criar_usuario.html", {"form": form})


@login_required
@perfil_requerido("admin")
def desativar_usuario(request, usuario_id):

    usuario = get_object_or_404(UsuarioSistema, id=usuario_id)

    usuario.is_active = False

    usuario.save()

    return redirect("listar_usuarios")


@login_required
@perfil_requerido("admin")
def reativar_usuario(request, usuario_id):

    usuario = get_object_or_404(UsuarioSistema, id=usuario_id)

    usuario.is_active = True

    usuario.save()

    return redirect("listar_usuarios")


def _intervalo_do_periodo(request):
    """Lê data_inicio/data_fim (YYYY-MM-DD) da querystring → (data_inicio, data_fim).

    Os presets (7 dias, 30 dias, mês atual) são atalhos no front que só
    preenchem esses dois campos; o servidor sempre filtra por intervalo de datas.
    Sem nenhum dos dois (primeira visita) → últimos 30 dias, para o dashboard
    já abrir com um recorte útil e os campos preenchidos.
    """
    hoje = timezone.localdate()
    data_inicio = parse_date(request.GET.get("data_inicio") or "")
    data_fim = parse_date(request.GET.get("data_fim") or "")
    if not data_inicio and not data_fim:
        return hoje - timedelta(days=29), hoje
    # Nunca depois de hoje (protege contra datas futuras vindas da URL).
    if data_inicio and data_inicio > hoje:
        data_inicio = hoje
    if data_fim and data_fim > hoje:
        data_fim = hoje
    return data_inicio, data_fim


def _contexto_dashboard(request):
    """Contexto compartilhado pelo dashboard (carga inicial) e pelo fragmento
    HTMX. Aplica o filtro de período e deixa as chaves de KPI/gráfico prontas
    (None) para as HUs 033–036 preencherem — elas calculam a partir de
    `queryset`, que já vem recortado pelo período.

    Contrato de contexto (preencha a sua chave, não renomeie as outras):
      - total_acessos, media_diaria, horario_pico, pessoas_unicas  → KPIs (HU-033)
      - serie_volume  → gráfico de acessos ao longo do tempo (HU-034)
      - picos_hora    → gráfico de horários de pico (HU-035)
      - fluxo_tipo, fluxo_ponto  → gráficos de fluxo (HU-036)
    """
    data_inicio, data_fim = _intervalo_do_periodo(request)

    queryset = RegistroAcesso.objects.all()
    if data_inicio:
        queryset = queryset.filter(timestamp__date__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(timestamp__date__lte=data_fim)

    return {
        "queryset": queryset,  # base já filtrada para as HUs 033–036
        "data_inicio": data_inicio.isoformat() if data_inicio else "",
        "data_fim": data_fim.isoformat() if data_fim else "",
        "hoje": timezone.localdate().isoformat(),  # limite máximo dos campos de data
        "total_acessos": None,
        "media_diaria": None,
        "horario_pico": None,
        "pessoas_unicas": None,
        "serie_volume": None,
        "picos_hora": None,
        "fluxo_tipo": None,
        "fluxo_ponto": None,
    }


@login_required
def dashboard(request):
    """Dashboard - primeira tela após login (HU-032/037/033)."""
    
    from apps.analytics.services import picos_por_hora, total_de_acessos, volume_por_periodo
    from apps.acessos.models import RegistroAcesso
    
    contexto = _contexto_dashboard(request)
    
    queryset = contexto.get("queryset", RegistroAcesso.objects.all())
    
    
    try:
        total_acessos = total_de_acessos(queryset)
    except Exception:
        total_acessos = queryset.count() if queryset else None

    try:
        volumes = volume_por_periodo(queryset, "dia") 
        media_diaria = sum(volumes) / len(volumes) if volumes else None
    except Exception:
        media_diaria = None

    try:
        horario_pico = picos_por_hora(queryset)
    except Exception:
        horario_pico = None

    try:
        pessoas_unicas = queryset.values("identificador_pseudonimizado").distinct().count()
    except Exception:
        pessoas_unicas = None

    contexto.update({
        "kpi_total_acessos": total_acessos,
        "kpi_media_diaria": media_diaria,
        "kpi_horario_pico": horario_pico,
        "kpi_pessoas_unicas": pessoas_unicas,
    })

    if request.headers.get("HX-Request"):
        return render(request, "partials/dashboard_widgets.html", contexto)
        
    return render(request, "dashboard.html", contexto)


@login_required
def upload_arquivo(request):
    pass  # ... código existente da view ...


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    View customizada para obtenção de token JWT.
    """

    serializer_class = CustomTokenObtainPairSerializer


class DummyProtectedView(APIView):
    """
    View de teste para validar a proteção de endpoints.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {"message": "Acesso autorizado!", "user": request.user.username}
        )
