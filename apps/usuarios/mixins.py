from functools import wraps

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


def perfil_requerido(perfil):
    """Versão decorator do PerfilRequeridoMixin, para views de função (HU-013/014)."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Você precisa estar logado.")
            if request.user.perfil != perfil:
                return render(request, "usuarios/403.html", status=403)
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
