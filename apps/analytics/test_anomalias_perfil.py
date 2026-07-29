"""Visibilidade das anomalias por perfil e cache do período (HU-057).

O detalhe de anomalia identifica pessoas: admin vê a lista, gestor recebe só
a contagem e a orientação de escalar. É a regra mais sensível da tela.
"""

import re
from datetime import date, datetime, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.acessos.models import PontoAcesso, RegistroAcesso
from apps.analytics.management.commands.detectar_anomalias import detectar_e_gravar
from apps.analytics.models import Alerta
from apps.analytics.views import agrupar_por_pessoa_e_data, filtrar_alertas
from apps.importacoes.models import Importacao

CREDENCIAL = "siv:credencial-de-teste"


def _usuario(perfil):
    return get_user_model().objects.create_user(
        username=f"u_{perfil}", password="Senha@2026", perfil=perfil
    )


@pytest.fixture
def com_anomalia(db):
    user = _usuario("admin")
    imp = Importacao.objects.create(nome_arquivo="a.csv", usuario=user)
    ponto = PontoAcesso.objects.create(
        nome="Catraca 1", localizacao="PORTARIA", grupo_equipamento="PORTARIA"
    )
    for segundos in (0, 10):
        RegistroAcesso.objects.create(
            credencial_cifrada=CREDENCIAL,
            ponto_acesso=ponto,
            tipo_acesso="Entrada",
            timestamp=timezone.make_aware(datetime(2026, 3, 2, 8, 0, segundos)),
            importacao=imp,
        )
    detectar_e_gravar()
    return Alerta.objects.get(tipo=Alerta.Tipo.ACESSO_REPETIDO)


def test_admin_ve_a_lista_de_anomalias(client, com_anomalia):
    client.login(username="u_admin", password="Senha@2026")

    resposta = client.get(reverse("anomalias:lista"))
    corpo = resposta.content.decode()

    assert resposta.status_code == 200
    assert resposta.context["pode_ver_detalhe"] is True
    assert len(resposta.context["grupos"]) == 1
    assert "Acesso repetido" in corpo


def test_gestor_ve_contagem_mas_nao_a_lista(client, com_anomalia):
    _usuario("gestor")
    client.login(username="u_gestor", password="Senha@2026")

    resposta = client.get(reverse("anomalias:lista"))
    corpo = resposta.content.decode()

    assert resposta.status_code == 200
    assert resposta.context["pode_ver_detalhe"] is False
    assert len(resposta.context["grupos"]) == 0
    # Sabe que existe e é orientado a escalar…
    assert resposta.context["total_anomalias"] == 1
    assert "Comunique o administrador" in corpo
    # …mas a credencial não sai no HTML de forma alguma.
    assert CREDENCIAL not in corpo


def test_anomalias_exige_login(client, com_anomalia):
    resposta = client.get(reverse("anomalias:lista"))

    assert resposta.status_code == 302
    assert "/accounts/login/" in resposta.url


def test_filtro_por_tipo(client, com_anomalia):
    client.login(username="u_admin", password="Senha@2026")

    com = client.get(reverse("anomalias:lista"), {"tipo": "acesso_repetido"})
    sem = client.get(reverse("anomalias:lista"), {"tipo": "volume_atipico"})

    assert len(com.context["grupos"]) == 1
    assert len(sem.context["grupos"]) == 0


def test_filtro_por_periodo(client, com_anomalia):
    client.login(username="u_admin", password="Senha@2026")

    fora = client.get(
        reverse("anomalias:lista"),
        {"data_inicio": "2026-04-01", "data_fim": "2026-04-30"},
    )

    assert fora.context["total_anomalias"] == 0


# --- agrupamento por pessoa e data ------------------------------------------


def _sequencia(credencial, ponto, segundos):
    """Cria uma sequência de passagens da mesma credencial no mesmo ponto."""
    user = get_user_model().objects.filter(username="u_admin").first() or _usuario(
        "admin"
    )
    imp, _ = Importacao.objects.get_or_create(nome_arquivo="seq.csv", usuario=user)
    for s in segundos:
        RegistroAcesso.objects.create(
            credencial_cifrada=credencial,
            ponto_acesso=ponto,
            tipo_acesso="Entrada",
            timestamp=timezone.make_aware(datetime(2026, 3, 2, 8, 0, s)),
            importacao=imp,
        )


@pytest.mark.django_db
def test_grupo_conta_passagens_e_nao_so_ocorrencias():
    """4 passagens em sequência geram 3 alertas.

    Ler "3" sem contexto dá a impressão de faltar registro — foi exatamente a
    dúvida que motivou o agrupamento. O grupo mostra as 4 passagens.
    """
    ponto = PontoAcesso.objects.create(
        nome="FACIAL 1", localizacao="PORTARIA", grupo_equipamento="PORTARIA"
    )
    _sequencia(CREDENCIAL, ponto, [0, 5, 10, 15])
    detectar_e_gravar()

    grupos = agrupar_por_pessoa_e_data(
        filtrar_alertas({}).order_by("-data", "tipo", "id")
    )

    assert len(grupos) == 1
    assert grupos[0]["total_ocorrencias"] == 3
    assert grupos[0]["total_passagens"] == 4
    assert grupos[0]["menor_intervalo"] == 5


@pytest.mark.django_db
def test_detalhe_lista_todas_as_passagens_e_nao_so_as_sinalizadas():
    """A 1ª passagem nunca dispara alerta, mas precisa aparecer no detalhe."""
    ponto = PontoAcesso.objects.create(
        nome="FACIAL 1", localizacao="PORTARIA", grupo_equipamento="PORTARIA"
    )
    _sequencia(CREDENCIAL, ponto, [0, 45])
    detectar_e_gravar()

    grupo = agrupar_por_pessoa_e_data(filtrar_alertas({}))[0]
    passagens = grupo["passagens"]

    assert len(passagens) == 2 == grupo["total_passagens"]
    # Primeira: sem intervalo e sem alerta, mas presente.
    assert passagens[0]["segundos_da_anterior"] is None
    assert passagens[0]["anomala"] is False
    # Segunda: a que disparou.
    assert passagens[1]["segundos_da_anterior"] == 45
    assert passagens[1]["anomala"] is True


@pytest.mark.django_db
def test_detalhe_ordena_passagens_por_horario():
    ponto = PontoAcesso.objects.create(
        nome="FACIAL 1", localizacao="PORTARIA", grupo_equipamento="PORTARIA"
    )
    _sequencia(CREDENCIAL, ponto, [0, 5, 10, 15])
    detectar_e_gravar()

    passagens = agrupar_por_pessoa_e_data(filtrar_alertas({}))[0]["passagens"]

    assert [p["segundos_da_anterior"] for p in passagens] == [None, 5, 5, 5]
    assert [p["horario"] for p in passagens] == sorted(p["horario"] for p in passagens)


@pytest.mark.django_db
def test_anomalia_do_dia_inteiro_nao_tem_passagens():
    Alerta.objects.create(
        data=date(2026, 3, 2), tipo=Alerta.Tipo.VOLUME_ATIPICO, valor=400
    )

    grupo = agrupar_por_pessoa_e_data(filtrar_alertas({}))[0]

    assert grupo["passagens"] == []
    assert grupo["total_ocorrencias"] == 1


@pytest.mark.django_db
def test_grupo_separa_pessoas_diferentes():
    ponto = PontoAcesso.objects.create(
        nome="FACIAL 1", localizacao="PORTARIA", grupo_equipamento="PORTARIA"
    )
    _sequencia("siv:pessoa-a", ponto, [0, 5])
    _sequencia("siv:pessoa-b", ponto, [30, 35])
    detectar_e_gravar()

    grupos = agrupar_por_pessoa_e_data(filtrar_alertas({}))

    assert len(grupos) == 2
    assert {g["total_passagens"] for g in grupos} == {2}


@pytest.mark.django_db
def test_grupo_reune_pontos_envolvidos():
    portaria = PontoAcesso.objects.create(
        nome="FACIAL 1", localizacao="PORTARIA", grupo_equipamento="PORTARIA"
    )
    outro = PontoAcesso.objects.create(
        nome="FACIAL 2", localizacao="PORTARIA", grupo_equipamento="PORTARIA"
    )
    _sequencia(CREDENCIAL, portaria, [0, 5])
    _sequencia(CREDENCIAL, outro, [40, 45])
    detectar_e_gravar()

    grupos = agrupar_por_pessoa_e_data(filtrar_alertas({}))

    assert len(grupos) == 1  # mesma pessoa, mesmo dia
    assert grupos[0]["pontos"] == ["FACIAL 1", "FACIAL 2"]
    assert grupos[0]["total_passagens"] == 4


@pytest.mark.django_db
def test_anomalia_do_dia_inteiro_fica_em_grupo_sem_pessoa():
    Alerta.objects.create(
        data=date(2026, 3, 2), tipo=Alerta.Tipo.VOLUME_ATIPICO, valor=400
    )

    grupos = agrupar_por_pessoa_e_data(filtrar_alertas({}))

    assert grupos[0]["credencial_cifrada"] == ""
    assert grupos[0]["total_passagens"] == 0


# --- menu lateral -----------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_nome, esperado",
    [
        ("dashboard", "Dashboard"),
        ("acessos:lista", "Consultas"),
        ("acessos:regras_lista", "Regras de Horário"),
        ("relatorios:lista", "Relatórios"),
        ("anomalias:lista", "Anomalias"),
    ],
)
def test_menu_marca_exatamente_um_item(client, url_nome, esperado):
    """acessos:lista, relatorios:lista e anomalias:lista têm o mesmo url_name.

    Comparar só url_name marcava três itens de uma vez; o namespace é o que
    distingue.
    """
    _usuario("admin")
    client.login(username="u_admin", password="Senha@2026")

    corpo = client.get(reverse(url_nome)).content.decode()
    ativos = re.findall(
        r'<a href="[^"]*"\s+class="ativo">\s*<span class="ic">[^<]*</span>\s*([^<\n]+)',
        corpo,
    )

    assert [item.strip() for item in ativos] == [esperado]


# --- relatório de anomalias -------------------------------------------------


def test_relatorio_de_anomalias_e_restrito_ao_admin(client, com_anomalia):
    _usuario("gestor")
    client.login(username="u_gestor", password="Senha@2026")

    detalhe = client.get(reverse("relatorios:detalhe", args=["anomalias"]))
    export = client.get(
        reverse("relatorios:exportar", args=["anomalias", "csv"]), {"buscar": "1"}
    )

    assert detalhe.status_code == 403
    assert export.status_code == 403


def test_relatorio_de_anomalias_nao_aparece_na_lista_do_gestor(client, com_anomalia):
    _usuario("gestor")
    client.login(username="u_gestor", password="Senha@2026")

    corpo = client.get(reverse("relatorios:lista")).content.decode()

    assert "Anomalias detectadas" not in corpo


def test_admin_exporta_relatorio_de_anomalias(client, com_anomalia):
    client.login(username="u_admin", password="Senha@2026")

    resposta = client.get(
        reverse("relatorios:exportar", args=["anomalias", "csv"]), {"buscar": "1"}
    )

    assert resposta.status_code == 200
    assert "Acesso repetido" in resposta.content.decode("utf-8-sig")


# --- HU-037 · memória do período no dashboard -------------------------------


@pytest.mark.django_db
def test_dashboard_lembra_do_ultimo_periodo(client):
    _usuario("admin")
    client.login(username="u_admin", password="Senha@2026")

    client.get(
        reverse("dashboard"), {"data_inicio": "2026-03-01", "data_fim": "2026-03-31"}
    )
    # Volta pelo menu, sem querystring.
    resposta = client.get(reverse("dashboard"))

    assert resposta.context["data_inicio"] == "2026-03-01"
    assert resposta.context["data_fim"] == "2026-03-31"


@pytest.mark.django_db
def test_dashboard_sem_historico_abre_nos_ultimos_30_dias(client):
    _usuario("admin")
    client.login(username="u_admin", password="Senha@2026")

    resposta = client.get(reverse("dashboard"))

    hoje = timezone.localdate()
    assert resposta.context["data_fim"] == hoje.isoformat()
    assert resposta.context["data_inicio"] == (hoje - timedelta(days=29)).isoformat()


@pytest.mark.django_db
def test_limpar_o_filtro_esquece_o_periodo_salvo(client):
    _usuario("admin")
    client.login(username="u_admin", password="Senha@2026")
    client.get(
        reverse("dashboard"), {"data_inicio": "2026-03-01", "data_fim": "2026-03-31"}
    )

    # Aplicar com os dois campos vazios = reset explícito.
    client.get(reverse("dashboard"), {"data_inicio": "", "data_fim": ""})
    resposta = client.get(reverse("dashboard"))

    assert resposta.context["data_fim"] == timezone.localdate().isoformat()


@pytest.mark.django_db
def test_dashboard_mostra_resumo_e_nao_a_lista_de_anomalias(client, com_anomalia):
    client.login(username="u_admin", password="Senha@2026")

    resposta = client.get(
        reverse("dashboard"),
        {"data_inicio": "2026-03-01", "data_fim": "2026-03-31"},
    )
    corpo = resposta.content.decode()

    assert resposta.context["total_anomalias"] == 1
    assert (
        resposta.context["resumo_anomalias"][0]["rotulo"]
        == "Acesso repetido em sequência"
    )
    # O dashboard nunca expõe credencial: o detalhe fica na tela restrita.
    assert CREDENCIAL not in corpo
    assert "Ver detalhes das anomalias" in corpo


@pytest.mark.django_db
def test_alerta_diario_nao_tem_registro_associado():
    """Volume atípico é propriedade do dia, não de uma pessoa."""
    alerta = Alerta.objects.create(
        data=date(2026, 3, 2), tipo=Alerta.Tipo.VOLUME_ATIPICO, valor=400
    )

    assert alerta.registro_id is None
    assert alerta.por_ocorrencia is False
