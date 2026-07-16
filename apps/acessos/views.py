from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.usuarios.mixins import PerfilRequeridoMixin

from .filters import RegistroAcessoFilter
from .forms import RegraHorarioForm
from .models import RegistroAcesso, RegraHorario

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.generics import ListAPIView

from .serializers import RegistroAcessoSerializer


class ListaAcessosView(LoginRequiredMixin, ListView):
    """Listagem de RegistroAcesso com filtros combináveis (HU-023)."""

    model = RegistroAcesso
    template_name = "acessos/lista_acessos.html"
    context_object_name = "registros"
    paginate_by = 50

    def get_queryset(self):
        qs = RegistroAcesso.objects.select_related("ponto_acesso").order_by(
            "-timestamp"
        )
        self.filterset = RegistroAcessoFilter(self.request.GET or None, queryset=qs)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter"] = self.filterset
        # Query string sem o "page", para os links de paginação preservarem
        # os filtros sem acumular páginas anteriores na URL.
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        return ctx


class RegistroAcessoListAPIView(ListAPIView):

    queryset = RegistroAcesso.objects.select_related("ponto_acesso").order_by(
        "-timestamp"
    )

    serializer_class = RegistroAcessoSerializer

    filter_backends = [DjangoFilterBackend]
    filterset_class = RegistroAcessoFilter


class DetalheAcessoView(LoginRequiredMixin, DetailView):
    """
    HU-025 — Exibe os detalhes completos de um único registro de acesso.

    Acessada via /acessos/<pk>/, busca o RegistroAcesso pela chave primária
    (padrão do DetailView: procura no banco usando o <int:pk> vindo da URL)
    e renderiza o template com todos os campos.
    """

    model = RegistroAcesso
    template_name = "acessos/detalhe_acesso.html"
    context_object_name = "registro"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # HTTP_REFERER = URL da página que fez a requisição (a listagem,
        # com os filtros que o usuário tinha aplicado antes de clicar).
        # Se não vier (ex: acesso direto pela URL), cai para a home "/".
        context["voltar_url"] = self.request.META.get("HTTP_REFERER", "/")
        return context


# --- Regras de Horário (CRUD, restrito ao perfil admin) --------------------
# Horário de funcionamento por grupo de equipamento/dia; acessos fora dessas
# faixas serão sinalizados como atípicos (consumido pela HU-053, Sprint 8).


class _RegraAdminMixin(LoginRequiredMixin, PerfilRequeridoMixin):
    perfil_requerido = "admin"
    model = RegraHorario


class RegraHorarioListView(_RegraAdminMixin, ListView):
    template_name = "acessos/regras_lista.html"
    context_object_name = "regras"


class RegraHorarioCreateView(_RegraAdminMixin, CreateView):
    form_class = RegraHorarioForm
    template_name = "acessos/regras_form.html"
    success_url = reverse_lazy("acessos:regras_lista")


class RegraHorarioUpdateView(_RegraAdminMixin, UpdateView):
    form_class = RegraHorarioForm
    template_name = "acessos/regras_form.html"
    success_url = reverse_lazy("acessos:regras_lista")


class RegraHorarioDeleteView(_RegraAdminMixin, DeleteView):
    template_name = "acessos/regras_confirmar_remocao.html"
    success_url = reverse_lazy("acessos:regras_lista")
