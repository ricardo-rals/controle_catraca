from django.shortcuts import render
from .models import UsuarioSistema
from django.shortcuts import redirect
from .forms import UsuarioSistemaForm
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView
from .mixins import PerfilRequeridoMixin
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy


class ListarUsuariosView(PerfilRequeridoMixin, ListView):
    model = UsuarioSistema
    template_name = "usuarios/listar_usuarios.html"
    context_object_name = "usuarios"
    perfil_requerido = "admin"


class RelatorioGestorView(PerfilRequeridoMixin, ListView):
    model = UsuarioSistema  # ou outro modelo de dados que gestores precisam
    template_name = "usuarios/dashboard.html"
    context_object_name = "dados"
    perfil_requerido = "gestor"


class CustomLoginView(LoginView):
    template_name = "usuarios/login.html"

    def get_success_url(self):
        perfil = self.request.user.perfil
        if perfil == "admin":
            return reverse_lazy("listar_usuarios")
        elif perfil == "gestor":
            return reverse_lazy("relatorio_gestor")
        return reverse_lazy("dashboard")


@login_required
def listar_usuarios(request):
    usuarios = UsuarioSistema.objects.all()
    return render(request, "usuarios/listar_usuarios.html", {"usuarios": usuarios})


@login_required
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
def desativar_usuario(request, usuario_id):

    usuario = get_object_or_404(UsuarioSistema, id=usuario_id)

    usuario.is_active = False

    usuario.save()

    return redirect("listar_usuarios")


@login_required
def dashboard(request):
    return render(request, "dashboard.html")


@login_required
def upload_arquivo(request):
    pass  # ... código existente da view ...
