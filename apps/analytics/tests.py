"""Testes do módulo analytics (HU-027 base; HUs 028-031 seguem este molde)."""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.acessos.models import PontoAcesso, RegistroAcesso
from apps.analytics.services import total_de_acessos, volume_por_periodo
from apps.importacoes.models import Importacao
from django.urls import reverse
from django.test import Client
from datetime import date, datetime, timedelta


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


def _cria_registros_em(dias):
    """Cria registros em datas fixas. `dias` = {date: quantidade}.

    Meio-dia local para o TruncDay não escorregar de dia por causa do fuso.
    """
    user = get_user_model().objects.create_user(username="vol", password="x")
    imp = Importacao.objects.create(nome_arquivo="vol.csv", usuario=user)
    ponto = PontoAcesso.objects.create(nome="PV", localizacao="LV")
    for dia, quantidade in dias.items():
        momento = timezone.make_aware(datetime(dia.year, dia.month, dia.day, 12, 0))
        for i in range(quantidade):
            RegistroAcesso.objects.create(
                credencial_cifrada=f"cred-{dia}-{i}",
                ponto_acesso=ponto,
                tipo_acesso="Entrada",
                timestamp=momento,
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


# --- volume_por_periodo (HU-028) -------------------------------------------
# Base das HU-053 (alertas por anomalia) e HU-054 (previsão de fluxo).


@pytest.mark.django_db
def test_volume_por_dia_agrupa_e_ordena():
    _cria_registros_em({date(2026, 3, 2): 3, date(2026, 3, 1): 1})

    resultado = volume_por_periodo(RegistroAcesso.objects.all(), "dia")

    assert [linha["total"] for linha in resultado] == [1, 3]
    assert [linha["periodo"].date() for linha in resultado] == [
        date(2026, 3, 1),
        date(2026, 3, 2),
    ]


@pytest.mark.django_db
def test_volume_por_dia_omite_dias_sem_registro():
    """Contrato explícito: a série é esparsa, não tem os dias zerados.

    Quem calcula média móvel ou previsão em cima disso (HU-053/054) precisa
    preencher os buracos antes, senão trata 01/03 e 05/03 como consecutivos.
    """
    _cria_registros_em({date(2026, 3, 1): 1, date(2026, 3, 5): 2})

    resultado = volume_por_periodo(RegistroAcesso.objects.all(), "dia")

    assert len(resultado) == 2
    assert [linha["periodo"].date() for linha in resultado] == [
        date(2026, 3, 1),
        date(2026, 3, 5),
    ]


@pytest.mark.django_db
def test_volume_por_mes_agrupa_dias_do_mesmo_mes():
    _cria_registros_em({date(2026, 3, 1): 1, date(2026, 3, 5): 2, date(2026, 4, 1): 4})

    resultado = volume_por_periodo(RegistroAcesso.objects.all(), "mes")

    assert [linha["total"] for linha in resultado] == [3, 4]


@pytest.mark.django_db
def test_volume_respeita_o_queryset_recebido():
    _cria_registros_em({date(2026, 3, 1): 2})
    filtrado = RegistroAcesso.objects.filter(tipo_acesso="Saída")

    assert volume_por_periodo(filtrado, "dia") == []


def test_volume_granularidade_invalida_levanta_erro():
    with pytest.raises(ValueError):
        volume_por_periodo(RegistroAcesso.objects.none(), "trimestre")
