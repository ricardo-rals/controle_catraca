from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from .filters import RegistroAcessoFilter
from .models import RegistroAcesso

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.generics import ListAPIView

from .filters import RegistroAcessoFilter
from .models import RegistroAcesso
from .serializers import RegistroAcessoSerializer

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
    

class RegistroAcessoListAPIView(ListAPIView):

    queryset = RegistroAcesso.objects.select_related("ponto_acesso").order_by("-timestamp")

    serializer_class = RegistroAcessoSerializer

    filter_backends = [DjangoFilterBackend]
    filterset_class = RegistroAcessoFilter
