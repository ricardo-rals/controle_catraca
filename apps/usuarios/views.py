from django.shortcuts import render
from .models import UsuarioSistema
from django.shortcuts import render, redirect
from .forms import UsuarioSistemaForm
from django.shortcuts import get_object_or_404

def listar_usuarios(request):
    usuarios = UsuarioSistema.objects.all()
    return render( request, "usuarios/listar_usuarios.html", {"usuarios": usuarios})


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

    return render( request, "usuarios/criar_usuario.html",{"form": form})



def desativar_usuario(request, usuario_id):

    usuario = get_object_or_404(UsuarioSistema, id=usuario_id)

    usuario.is_active = False

    usuario.save()

    return redirect("listar_usuarios")# Create your views here.
