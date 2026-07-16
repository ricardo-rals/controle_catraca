"""Testes do app acessos (HU-023: filtros da tela /acessos/)."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.acessos.filters import RegistroAcessoFilter
from apps.acessos.models import PontoAcesso, RegistroAcesso
from apps.importacoes.models import Importacao
from apps.importacoes.utils.pseudonimizacao import criptografar_valor


def test_ambiente_de_testes_funciona():
    assert 1 + 1 == 2


@pytest.mark.django_db
def test_filter_combina_tipo_e_intervalo_de_datas():
    user = get_user_model().objects.create_user(username="t", password="x")
    imp = Importacao.objects.create(nome_arquivo="t.csv", usuario=user)
    ponto = PontoAcesso.objects.create(nome="P1", localizacao="L1")
    agora = timezone.now()

    alvo = RegistroAcesso.objects.create(
        credencial_cifrada="cred-a",
        ponto_acesso=ponto,
        tipo_acesso="Entrada",
        timestamp=agora,
        importacao=imp,
    )
    RegistroAcesso.objects.create(
        credencial_cifrada="cred-b",
        ponto_acesso=ponto,
        tipo_acesso="Saída",
        timestamp=agora,
        importacao=imp,
    )
    RegistroAcesso.objects.create(
        credencial_cifrada="cred-c",
        ponto_acesso=ponto,
        tipo_acesso="Entrada",
        timestamp=agora - timedelta(days=10),
        importacao=imp,
    )

    hoje = timezone.localtime(agora).date().isoformat()
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
        credencial_cifrada="cred-a",
        ponto_acesso=ponto,
        tipo_acesso="Entrada",
        timestamp=agora,
        importacao=imp,
    )
    antigo = RegistroAcesso.objects.create(
        credencial_cifrada="cred-b",
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


# --- Regras de Horário (CRUD admin-only) -----------------------------------


@pytest.mark.django_db
def test_regras_horario_so_admin(client):
    User = get_user_model()
    admin = User.objects.create_user(username="adm", password="x", perfil="admin")
    gestor = User.objects.create_user(username="ges", password="x", perfil="gestor")

    client.force_login(gestor)
    assert client.get("/acessos/regras/").status_code == 403

    client.force_login(admin)
    assert client.get("/acessos/regras/").status_code == 200


@pytest.mark.django_db
def test_regra_horario_criacao(client):
    admin = get_user_model().objects.create_user(
        username="adm", password="x", perfil="admin"
    )
    client.force_login(admin)
    resp = client.post(
        "/acessos/regras/nova/",
        {
            "grupo_equipamento": "PORTARIA",
            "dia_semana": "2",
            "horario_inicio": "07:00",
            "horario_fim": "22:00",
        },
    )
    assert resp.status_code == 302
    from apps.acessos.models import RegraHorario

    assert RegraHorario.objects.filter(grupo_equipamento="PORTARIA").exists()


@pytest.mark.django_db
def test_regra_horario_fim_antes_do_inicio_invalida(client):
    admin = get_user_model().objects.create_user(
        username="adm", password="x", perfil="admin"
    )
    client.force_login(admin)
    resp = client.post(
        "/acessos/regras/nova/",
        {
            "grupo_equipamento": "PORTARIA",
            "dia_semana": "2",
            "horario_inicio": "22:00",
            "horario_fim": "07:00",
        },
    )
    assert resp.status_code == 200  # re-renderiza com erro, não redireciona
    from apps.acessos.models import RegraHorario

    assert not RegraHorario.objects.exists()


# --- Visibilidade de dados por perfil (detalhe do acesso) ------------------


@pytest.mark.django_db
def test_detalhe_foto_e_identificador_por_perfil(client, settings):
    settings.PSEUDONIMIZACAO_SALT = "salt_teste"
    User = get_user_model()
    admin = User.objects.create_user(username="adm", password="x", perfil="admin")
    gestor = User.objects.create_user(username="ges", password="x", perfil="gestor")
    imp = Importacao.objects.create(nome_arquivo="t.csv", usuario=admin)
    ponto = PontoAcesso.objects.create(nome="P1", localizacao="L1")
    reg = RegistroAcesso.objects.create(
        credencial_cifrada=criptografar_valor("123456"),
        nome_cifrado=criptografar_valor("Maria Silva"),
        ponto_acesso=ponto,
        tipo_acesso="Entrada",
        timestamp=timezone.now(),
        importacao=imp,
    )

    client.force_login(admin)
    corpo_admin = client.get(f"/acessos/{reg.pk}/").content.decode()
    assert "123456" in corpo_admin
    assert "123456" in corpo_admin
    assert "Maria Silva" in corpo_admin
    assert "restrito ao administrador" not in corpo_admin

    client.force_login(gestor)
    corpo_gestor = client.get(f"/acessos/{reg.pk}/").content.decode()
    assert "123456" not in corpo_gestor
    assert "**3456" in corpo_gestor
    assert "123456" not in corpo_gestor
    assert "Maria Silva" not in corpo_gestor
    assert "restrito ao administrador" in corpo_gestor  # foto bloqueada
