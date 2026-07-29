"""Testes do módulo analytics (HU-027 base; HUs 028-031 seguem este molde)."""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.acessos.models import PontoAcesso, RegistroAcesso, RegraHorario
from apps.analytics.management.commands.detectar_anomalias import detectar_e_gravar
from apps.analytics.models import Alerta
from apps.analytics.services import (
    detectar_acesso_repetido,
    detectar_fora_de_horario,
    detectar_volume_atipico,
    serie_diaria_completa,
    total_de_acessos,
    volume_por_periodo,
)
from apps.importacoes.models import Importacao
from django.urls import reverse
from django.test import Client
from datetime import date, datetime, time, timedelta


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
# Base da detecção de anomalias por volume (HU-053).


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

    Quem calcula média móvel em cima disso (HU-053) precisa preencher os
    buracos antes, senão trata 01/03 e 05/03 como consecutivos.
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


# --- serie_diaria_completa / HU-053 -----------------------------------------


def _serie(**dias):
    """Atalho: _serie(d1=10, d2=12) -> [{'dia': date, 'total': n}, ...]."""
    base = date(2026, 3, 1)
    return [
        {"dia": base + timedelta(days=i), "total": total}
        for i, total in enumerate(dias.values())
    ]


@pytest.mark.django_db
def test_serie_diaria_completa_preenche_buracos_com_zero():
    _cria_registros_em({date(2026, 3, 1): 1, date(2026, 3, 4): 2})

    serie = serie_diaria_completa(RegistroAcesso.objects.all())

    assert [ponto["total"] for ponto in serie] == [1, 0, 0, 2]
    assert serie[0]["dia"] == date(2026, 3, 1)
    assert serie[-1]["dia"] == date(2026, 3, 4)


@pytest.mark.django_db
def test_serie_diaria_completa_vazia_sem_registros():
    assert serie_diaria_completa(RegistroAcesso.objects.none()) == []


def test_volume_atipico_sinaliza_dia_fora_da_curva():
    serie = [
        {"dia": date(2026, 3, 1) + timedelta(days=i), "total": 100 + (i % 3)}
        for i in range(30)
    ]
    serie.append({"dia": date(2026, 3, 31), "total": 400})

    achados = detectar_volume_atipico(serie, janela=30)

    assert len(achados) == 1
    assert achados[0]["dia"] == date(2026, 3, 31)
    assert achados[0]["total"] == 400


def test_volume_atipico_ignora_dia_dentro_do_padrao():
    serie = [
        {"dia": date(2026, 3, 1) + timedelta(days=i), "total": 100 + (i % 3)}
        for i in range(30)
    ]
    serie.append({"dia": date(2026, 3, 31), "total": 101})

    assert detectar_volume_atipico(serie, janela=30) == []


def test_volume_atipico_sem_historico_suficiente_nao_alerta():
    serie = _serie(a=1, b=500, c=2)

    assert detectar_volume_atipico(serie, janela=30) == []


def test_volume_atipico_serie_constante_nao_alerta():
    """Desvio zero: qualquer variação daria infinitos σ. Não é sinal."""
    serie = [
        {"dia": date(2026, 3, 1) + timedelta(days=i), "total": 10} for i in range(30)
    ]
    serie.append({"dia": date(2026, 3, 31), "total": 11})

    assert detectar_volume_atipico(serie, janela=30) == []


def _cria_ponto_com_grupo(grupo="PORTARIA"):
    return PontoAcesso.objects.create(
        nome=f"Catraca {grupo}", localizacao=grupo, grupo_equipamento=grupo
    )


def _registro_em(ponto, momento, credencial="c1"):
    user, _ = get_user_model().objects.get_or_create(username="fh")
    imp, _ = Importacao.objects.get_or_create(nome_arquivo="fh.csv", usuario=user)
    return RegistroAcesso.objects.create(
        credencial_cifrada=credencial,
        ponto_acesso=ponto,
        tipo_acesso="Entrada",
        timestamp=timezone.make_aware(momento),
        importacao=imp,
    )


@pytest.mark.django_db
def test_fora_de_horario_sinaliza_acesso_de_madrugada():
    ponto = _cria_ponto_com_grupo()
    # 02/03/2026 é uma segunda-feira; DiaSemana.SEGUNDA == 2 == ExtractWeekDay.
    RegraHorario.objects.create(
        grupo_equipamento="PORTARIA",
        dia_semana=RegraHorario.DiaSemana.SEGUNDA,
        horario_inicio=time(7, 0),
        horario_fim=time(22, 0),
    )
    fora = _registro_em(ponto, datetime(2026, 3, 2, 3, 30))
    _registro_em(ponto, datetime(2026, 3, 2, 9, 0), credencial="c2")  # dentro

    achados = detectar_fora_de_horario(RegistroAcesso.objects.all())

    assert achados == [
        {"registro_id": fora.id, "dia": date(2026, 3, 2), "horario": "03:30"}
    ]


@pytest.mark.django_db
def test_fora_de_horario_ignora_grupo_sem_regra():
    ponto = _cria_ponto_com_grupo("BIBLIOTECA")
    RegraHorario.objects.create(
        grupo_equipamento="PORTARIA",
        dia_semana=RegraHorario.DiaSemana.SEGUNDA,
        horario_inicio=time(7, 0),
        horario_fim=time(22, 0),
    )
    _registro_em(ponto, datetime(2026, 3, 2, 3, 30))

    assert detectar_fora_de_horario(RegistroAcesso.objects.all()) == []


@pytest.mark.django_db
def test_fora_de_horario_sem_regras_cadastradas():
    ponto = _cria_ponto_com_grupo()
    _registro_em(ponto, datetime(2026, 3, 2, 3, 30))

    assert detectar_fora_de_horario(RegistroAcesso.objects.all()) == []


@pytest.mark.django_db
def test_detectar_e_gravar_e_idempotente():
    ponto = _cria_ponto_com_grupo()
    RegraHorario.objects.create(
        grupo_equipamento="PORTARIA",
        dia_semana=RegraHorario.DiaSemana.SEGUNDA,
        horario_inicio=time(7, 0),
        horario_fim=time(22, 0),
    )
    _registro_em(ponto, datetime(2026, 3, 2, 3, 30))

    detectar_e_gravar()
    detectar_e_gravar()

    assert Alerta.objects.count() == 1
    alerta = Alerta.objects.get()
    assert alerta.tipo == Alerta.Tipo.FORA_DE_HORARIO
    assert alerta.data == date(2026, 3, 2)


# --- HU-056 · acesso repetido ----------------------------------------------


@pytest.mark.django_db
def test_acesso_repetido_dentro_da_janela():
    ponto = _cria_ponto_com_grupo()
    primeiro = _registro_em(ponto, datetime(2026, 3, 2, 8, 0, 0))
    segundo = _registro_em(ponto, datetime(2026, 3, 2, 8, 0, 40))

    achados = detectar_acesso_repetido(RegistroAcesso.objects.all(), janela_segundos=60)

    assert achados == [
        {
            "registro_id": segundo.id,
            "registro_anterior_id": primeiro.id,
            "dia": date(2026, 3, 2),
            "segundos": 40,
        }
    ]


@pytest.mark.django_db
def test_escopo_equipamento_ignora_catracas_do_mesmo_local():
    """Leitor facial seguido da catraca é UMA passagem registrada duas vezes.

    Com escopo 'equipamento' (padrão) isso não é anomalia; com 'grupo', é.
    """
    facial = _cria_ponto_com_grupo("REFEITORIO")
    catraca = PontoAcesso.objects.create(
        nome="CATRACA REFEITORIO",
        localizacao="REFEITORIO",
        grupo_equipamento="REFEITORIO",
    )
    _registro_em(facial, datetime(2026, 3, 2, 12, 0, 0))
    _registro_em(catraca, datetime(2026, 3, 2, 12, 0, 3))

    qs = RegistroAcesso.objects.all()
    assert detectar_acesso_repetido(qs, 60, escopo="equipamento") == []
    assert len(detectar_acesso_repetido(qs, 60, escopo="grupo")) == 1


def test_escopo_invalido_levanta_erro():
    with pytest.raises(ValueError):
        detectar_acesso_repetido(RegistroAcesso.objects.none(), 60, escopo="predio")


@pytest.mark.django_db
def test_acesso_repetido_fora_da_janela_nao_alerta():
    ponto = _cria_ponto_com_grupo()
    _registro_em(ponto, datetime(2026, 3, 2, 8, 0, 0))
    _registro_em(ponto, datetime(2026, 3, 2, 8, 5, 0))

    assert detectar_acesso_repetido(RegistroAcesso.objects.all(), 60) == []


@pytest.mark.django_db
def test_acesso_repetido_ignora_credenciais_diferentes():
    """Duas pessoas passando em sequência é fila, não anomalia."""
    ponto = _cria_ponto_com_grupo()
    _registro_em(ponto, datetime(2026, 3, 2, 8, 0, 0), credencial="pessoa-a")
    _registro_em(ponto, datetime(2026, 3, 2, 8, 0, 5), credencial="pessoa-b")

    assert detectar_acesso_repetido(RegistroAcesso.objects.all(), 60) == []


@pytest.mark.django_db
def test_acesso_repetido_ignora_pontos_diferentes():
    """A mesma pessoa em catracas distintas é deslocamento normal."""
    portaria = _cria_ponto_com_grupo("PORTARIA")
    biblioteca = _cria_ponto_com_grupo("BIBLIOTECA")
    _registro_em(portaria, datetime(2026, 3, 2, 8, 0, 0))
    _registro_em(biblioteca, datetime(2026, 3, 2, 8, 0, 30))

    assert detectar_acesso_repetido(RegistroAcesso.objects.all(), 60) == []


@pytest.mark.django_db
def test_acesso_repetido_encadeado_gera_um_alerta_por_ocorrencia():
    ponto = _cria_ponto_com_grupo()
    _registro_em(ponto, datetime(2026, 3, 2, 8, 0, 0))
    _registro_em(ponto, datetime(2026, 3, 2, 8, 0, 10))
    _registro_em(ponto, datetime(2026, 3, 2, 8, 0, 20))

    achados = detectar_acesso_repetido(RegistroAcesso.objects.all(), 60)

    assert len(achados) == 2
    assert [a["segundos"] for a in achados] == [10, 10]


@pytest.mark.django_db
def test_alerta_por_ocorrencia_aponta_para_a_pessoa():
    ponto = _cria_ponto_com_grupo()
    _registro_em(ponto, datetime(2026, 3, 2, 8, 0, 0), credencial="siv:abc")
    _registro_em(ponto, datetime(2026, 3, 2, 8, 0, 10), credencial="siv:abc")

    detectar_e_gravar()

    alerta = Alerta.objects.get(tipo=Alerta.Tipo.ACESSO_REPETIDO)
    assert alerta.registro is not None
    assert alerta.registro.credencial_cifrada == "siv:abc"
    assert alerta.por_ocorrencia is True


@pytest.mark.django_db
def test_alerta_some_quando_o_registro_e_apagado():
    """Cascata do RegistroAcesso: pedido de remoção de titular limpa junto."""
    ponto = _cria_ponto_com_grupo()
    _registro_em(ponto, datetime(2026, 3, 2, 8, 0, 0))
    segundo = _registro_em(ponto, datetime(2026, 3, 2, 8, 0, 10))
    detectar_e_gravar()
    assert Alerta.objects.filter(tipo=Alerta.Tipo.ACESSO_REPETIDO).exists()

    segundo.delete()

    assert not Alerta.objects.filter(tipo=Alerta.Tipo.ACESSO_REPETIDO).exists()
