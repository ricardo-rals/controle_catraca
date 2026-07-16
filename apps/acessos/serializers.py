from rest_framework import serializers

from apps.usuarios.perfis import credencial_para, is_admin

from .models import RegistroAcesso


class RegistroAcessoSerializer(serializers.ModelSerializer):

    ponto_acesso = serializers.StringRelatedField()
    credencial = serializers.SerializerMethodField()
    nome = serializers.SerializerMethodField()

    class Meta:
        model = RegistroAcesso

        fields = [
            "credencial",
            "nome",
            "ponto_acesso",
            "tipo_acesso",
            "timestamp",
            "evento",
            "area_origem",
            "area_destino",
        ]

    def get_credencial(self, obj):
        request = self.context.get("request")
        if request:
            return credencial_para(request.user, obj.credencial_cifrada)
        return None

    def get_nome(self, obj):
        request = self.context.get("request")
        if request and is_admin(request.user):
            return obj.nome_descriptografado() or None
        return None
