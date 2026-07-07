"""Testes do módulo analytics (HU-027 base; HUs 028-031 seguem este molde)."""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.acessos.models import PontoAcesso, RegistroAcesso
from apps.analytics.services import total_de_acessos
from apps.importacoes.models import Importacao


def _cria_registros(quantidade):
    user = get_user_model().objects.create_user(username="t", password="x")
    imp = Importacao.objects.create(nome_arquivo="t.csv", usuario=user)
    ponto = PontoAcesso.objects.create(nome="P1", localizacao="L1")
    agora = timezone.now()
    for i in range(quantidade):
        RegistroAcesso.objects.create(
            identificador_pseudonimizado=f"{i:0>32}",
            ponto_acesso=ponto,
            tipo_acesso="Entrada",
            timestamp=agora,
            importacao=imp,
        )


@pytest.mark.django_db
def test_total_de_acessos_conta_o_queryset_recebido():
    _cria_registros(3)
    assert total_de_acessos(RegistroAcesso.objects.all()) == 3


@pytest.mark.django_db
def test_total_de_acessos_respeita_filtro_do_chamador():
    _cria_registros(3)
    filtrado = RegistroAcesso.objects.filter(tipo_acesso="Saída")
    assert total_de_acessos(filtrado) == 0
