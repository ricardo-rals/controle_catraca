"""Autenticação da API pública por chave (HU-055)."""

from django.utils import timezone
from rest_framework.permissions import BasePermission

from .models import ChaveAPI, hash_chave_api

HEADER_CHAVE = "X-API-Key"


class TemChaveAPIValida(BasePermission):
    """Libera o acesso a quem enviar uma chave ativa no header X-API-Key.

    A chave enviada é comparada pelo hash — o valor em claro não existe no
    banco. Chave ausente, desconhecida ou revogada resulta em 403.
    """

    message = f"Envie uma chave de API válida no header {HEADER_CHAVE}."

    def has_permission(self, request, view):
        enviada = (request.headers.get(HEADER_CHAVE) or "").strip()
        if not enviada:
            return False

        chave = ChaveAPI.objects.filter(
            chave_hash=hash_chave_api(enviada),
            ativa=True,
        ).first()
        if chave is None:
            return False

        # update() direto: não precisa carregar/salvar o objeto inteiro só
        # para carimbar a data, e evita disparar signals a cada requisição.
        ChaveAPI.objects.filter(pk=chave.pk).update(ultimo_uso=timezone.now())
        request.chave_api = chave
        return True
