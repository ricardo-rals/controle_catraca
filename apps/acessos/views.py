from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView

from .models import RegistroAcesso

# TODO: a class ListaAcessos referenciava "Acesso", mas esse model
# não existe em apps/acessos/models.py (o model é RegistroAcesso).
# Comentei pra conseguir subir o projeto e testar a HU-025.
# class ListaAcessos(LoginRequiredMixin, ListView):
#     model = Acesso
#     template_name = "acessos/lista.html"


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
