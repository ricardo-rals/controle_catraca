from django import forms
from .models import UsuarioSistema
import re


class UsuarioSistemaForm(forms.ModelForm):

    senha = forms.CharField(widget=forms.PasswordInput)

    confirmar_senha = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = UsuarioSistema

        fields = [
            "username",
            "email",
            "perfil",
        ]

    def clean(self):

        dados = super().clean()

        senha = dados.get("senha")
        confirmar = dados.get("confirmar_senha")

        if not senha:
            raise forms.ValidationError("Informe a senha.")

        if senha != confirmar:
            raise forms.ValidationError("As senhas não coincidem.")

        if len(senha) < 8:
            raise forms.ValidationError("A senha deve ter pelo menos 8 caracteres.")

        if not re.search(r"\d", senha):
            raise forms.ValidationError("A senha deve conter um número.")

        if not re.search(r"[A-Z]", senha):
            raise forms.ValidationError("A senha deve conter uma letra maiúscula.")

        return dados
