from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView

from .filters import RegistroAcessoFilter
from .models import RegistroAcesso


class ListaAcessosView(LoginRequiredMixin, ListView):
    """Listagem de RegistroAcesso com filtros combináveis (HU-023)."""

    model = RegistroAcesso
    template_name = "acessos/lista_acessos.html"
    context_object_name = "registros"

    def get_queryset(self):
        qs = RegistroAcesso.objects.select_related("ponto_acesso").order_by(
            "-timestamp"
        )
        self.filterset = RegistroAcessoFilter(self.request.GET or None, queryset=qs)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter"] = self.filterset
        return ctx


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
