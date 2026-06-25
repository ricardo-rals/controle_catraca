from django.http import HttpResponseForbidden
from django.shortcuts import render


class PerfilRequeridoMixin:
    perfil_requerido = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Você precisa estar logado.")
        if self.perfil_requerido and request.user.perfil != self.perfil_requerido:
            return render(request, "usuarios/403.html", status=403)
        return super().dispatch(request, *args, **kwargs)
