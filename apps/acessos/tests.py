"""Testes do app acessos (HU-023: filtros da tela /acessos/)."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.acessos.filters import RegistroAcessoFilter
from apps.acessos.models import PontoAcesso, RegistroAcesso
from apps.importacoes.models import Importacao


def test_ambiente_de_testes_funciona():
    assert 1 + 1 == 2


@pytest.mark.django_db
def test_filter_combina_tipo_e_intervalo_de_datas():
    user = get_user_model().objects.create_user(username="t", password="x")
    imp = Importacao.objects.create(nome_arquivo="t.csv", usuario=user)
    ponto = PontoAcesso.objects.create(nome="P1", localizacao="L1")
    agora = timezone.now()

    alvo = RegistroAcesso.objects.create(
        identificador_pseudonimizado="a" * 32,
        ponto_acesso=ponto,
        tipo_acesso="Entrada",
        timestamp=agora,
        importacao=imp,
    )
    RegistroAcesso.objects.create(
        identificador_pseudonimizado="b" * 32,
        ponto_acesso=ponto,
        tipo_acesso="Saída",
        timestamp=agora,
        importacao=imp,
    )
    RegistroAcesso.objects.create(
        identificador_pseudonimizado="c" * 32,
        ponto_acesso=ponto,
        tipo_acesso="Entrada",
        timestamp=agora - timedelta(days=10),
        importacao=imp,
    )

    hoje = agora.date().isoformat()
    fs = RegistroAcessoFilter(
        {"tipo_acesso": "Entrada", "data_inicio": hoje, "data_fim": hoje},
        queryset=RegistroAcesso.objects.all(),
    )

    assert list(fs.qs) == [alvo]


@pytest.mark.django_db
def test_data_fim_vazia_assume_hoje():
    user = get_user_model().objects.create_user(username="t2", password="x")
    imp = Importacao.objects.create(nome_arquivo="t.csv", usuario=user)
    ponto = PontoAcesso.objects.create(nome="P1", localizacao="L1")
    agora = timezone.now()

    de_hoje = RegistroAcesso.objects.create(
        identificador_pseudonimizado="a" * 32,
        ponto_acesso=ponto,
        tipo_acesso="Entrada",
        timestamp=agora,
        importacao=imp,
    )
    antigo = RegistroAcesso.objects.create(
        identificador_pseudonimizado="b" * 32,
        ponto_acesso=ponto,
        tipo_acesso="Entrada",
        timestamp=agora - timedelta(days=30),
        importacao=imp,
    )

    inicio = (agora - timedelta(days=7)).date().isoformat()
    fs = RegistroAcessoFilter(
        {"data_inicio": inicio},
        queryset=RegistroAcesso.objects.all(),
    )
    resultado = set(fs.qs)

    assert de_hoje in resultado
    assert antigo not in resultado
