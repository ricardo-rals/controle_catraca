from rest_framework import serializers

from .models import RegistroAcesso


class RegistroAcessoSerializer(serializers.ModelSerializer):

    ponto_acesso = serializers.StringRelatedField()

    class Meta:
        model = RegistroAcesso

        fields = [
            "identificador_pseudonimizado",
            "ponto_acesso",
            "tipo_acesso",
            "timestamp",
            "evento",
            "area_origem",
            "area_destino",
        ]
