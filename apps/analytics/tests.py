"""Testes do módulo analytics (HU-027 base; HUs 028-031 seguem este molde)."""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.acessos.models import PontoAcesso, RegistroAcesso
from apps.analytics.services import total_de_acessos
from apps.importacoes.models import Importacao
from django.urls import reverse
from django.test import Client
from datetime import timedelta


def _cria_registros(quantidade):
    user = get_user_model().objects.create_user(username="t", password="x")
    imp = Importacao.objects.create(nome_arquivo="t.csv", usuario=user)
    ponto = PontoAcesso.objects.create(nome="P1", localizacao="L1")
    agora = timezone.now()
    for i in range(quantidade):
        RegistroAcesso.objects.create(
            credencial_cifrada=f"cred-{i}",
            ponto_acesso=ponto,
            tipo_acesso="Entrada",
            timestamp=agora,
            importacao=imp,
        )


@pytest.mark.django_db
def test_dashboard_date_filter_applies(client):
    user = get_user_model().objects.create_user(username="u2", password="pw")
    ponto = PontoAcesso.objects.create(nome="P3", localizacao="L3")
    imp = Importacao.objects.create(nome_arquivo="t3.csv", usuario=user)
    now = timezone.now()
    RegistroAcesso.objects.create(
        credencial_cifrada="cred-b",
        ponto_acesso=ponto,
        tipo_acesso="Entrada",
        timestamp=now - timedelta(days=10),
        importacao=imp,
    )
    RegistroAcesso.objects.create(
        credencial_cifrada="cred-c",
        ponto_acesso=ponto,
        tipo_acesso="Entrada",
        timestamp=now,
        importacao=imp,
    )

    c = Client()
    c.login(username="u2", password="pw")
    # filtra para período que inclui apenas o registro mais recente
    data_inicio = (now - timedelta(days=1)).date().isoformat()
    data_fim = now.date().isoformat()
    resp = c.get(
        reverse("dashboard"), {"data_inicio": data_inicio, "data_fim": data_fim}
    )
    assert resp.status_code == 200
    assert resp.context["total_acessos"] == 1


@pytest.mark.django_db
def test_total_de_acessos_conta_o_queryset_recebido():
    _cria_registros(3)
    assert total_de_acessos(RegistroAcesso.objects.all()) == 3


@pytest.mark.django_db
def test_total_de_acessos_respeita_filtro_do_chamador():
    _cria_registros(3)
    filtrado = RegistroAcesso.objects.filter(tipo_acesso="Saída")
    assert total_de_acessos(filtrado) == 0
