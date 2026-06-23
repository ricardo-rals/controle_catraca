from django.shortcuts import render
from .models import UsuarioSistema
from django.shortcuts import redirect
from .forms import UsuarioSistemaForm
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required


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
