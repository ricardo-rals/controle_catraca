"""Testes do módulo analytics (HU-027 base; HUs 028-031 seguem este molde)."""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.acessos.models import PontoAcesso, RegistroAcesso
from apps.analytics.services import total_de_acessos
from apps.importacoes.models import Importacao
from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model
from apps.usuarios.models import UsuarioSistema
from datetime import timedelta
from django.utils import timezone


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
def test_dashboard_context_includes_fluxo(client):
    # cria dados
    user = get_user_model().objects.create_user(username='u1', password='pw')
    ponto = PontoAcesso.objects.create(nome='P2', localizacao='L2')
    imp = Importacao.objects.create(nome_arquivo='t2.csv', usuario=user)
    now = timezone.now()
    RegistroAcesso.objects.create(identificador_pseudonimizado='a', ponto_acesso=ponto, tipo_acesso='Entrada', timestamp=now, importacao=imp)

    # autentica e requisita dashboard
    c = Client()
    c.login(username='u1', password='pw')
    resp = c.get(reverse('dashboard'))
    assert resp.status_code == 200
    assert 'fluxo_tipo' in resp.context
    assert 'fluxo_ponto' in resp.context
    assert isinstance(resp.context['fluxo_tipo'], list)
    assert isinstance(resp.context['fluxo_ponto'], list)


@pytest.mark.django_db
def test_dashboard_date_filter_applies(client):
    user = get_user_model().objects.create_user(username='u2', password='pw')
    ponto = PontoAcesso.objects.create(nome='P3', localizacao='L3')
    imp = Importacao.objects.create(nome_arquivo='t3.csv', usuario=user)
    now = timezone.now()
    RegistroAcesso.objects.create(identificador_pseudonimizado='b', ponto_acesso=ponto, tipo_acesso='Entrada', timestamp=now - timedelta(days=10), importacao=imp)
    RegistroAcesso.objects.create(identificador_pseudonimizado='c', ponto_acesso=ponto, tipo_acesso='Entrada', timestamp=now, importacao=imp)

    c = Client()
    c.login(username='u2', password='pw')
    # filtra para período que inclui apenas o registro mais recente
    data_inicio = (now - timedelta(days=1)).date().isoformat()
    data_fim = now.date().isoformat()
    resp = c.get(reverse('dashboard'), {'data_inicio': data_inicio, 'data_fim': data_fim})
    assert resp.status_code == 200
    fluxo_ponto = resp.context['fluxo_ponto']
    # deve conter apenas um ponto com total 1
    total = sum(item['total'] for item in fluxo_ponto)
    assert total == 1


@pytest.mark.django_db
def test_total_de_acessos_conta_o_queryset_recebido():
    _cria_registros(3)
    assert total_de_acessos(RegistroAcesso.objects.all()) == 3


@pytest.mark.django_db
def test_total_de_acessos_respeita_filtro_do_chamador():
    _cria_registros(3)
    filtrado = RegistroAcesso.objects.filter(tipo_acesso="Saída")
    assert total_de_acessos(filtrado) == 0
