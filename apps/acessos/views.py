# Create your views here.
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from .models import Acesso


class ListaAcessos(LoginRequiredMixin, ListView):
    model = Acesso
    template_name = "acessos/lista.html"
