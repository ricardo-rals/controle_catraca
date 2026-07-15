"""Testes da central de relatórios (HU-040): lista, detalhe e exportação."""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.acessos.models import PontoAcesso, RegistroAcesso
from apps.importacoes.models import Importacao


def _login(client):
    user = get_user_model().objects.create_user(username="r", password="x")
    imp = Importacao.objects.create(nome_arquivo="t.csv", usuario=user)
    ponto = PontoAcesso.objects.create(nome="P1", localizacao="L1")
    RegistroAcesso.objects.create(
        identificador_pseudonimizado="a" * 32,
        ponto_acesso=ponto,
        tipo_acesso="Entrada",
        timestamp=timezone.now(),
        importacao=imp,
    )
    client.force_login(user)


@pytest.mark.django_db
def test_lista_relatorios(client):
    _login(client)
    resp = client.get("/relatorios/")
    assert resp.status_code == 200
    assert b"Registros de acesso" in resp.content


@pytest.mark.django_db
def test_detalhe_nao_busca_ao_abrir(client):
    _login(client)
    resp = client.get("/relatorios/acessos/")
    assert resp.status_code == 200
    assert b"id_data_inicio" in resp.content  # filtros renderizados
    assert b"Buscar todos os dados" in resp.content
    assert b'class="tabela-relatorio"' not in resp.content  # sem prévia


@pytest.mark.django_db
def test_detalhe_busca_mostra_previa(client):
    _login(client)
    resp = client.get("/relatorios/acessos/?buscar=1")
    assert resp.status_code == 200
    assert b'class="tabela-relatorio"' in resp.content  # prévia após buscar


@pytest.mark.django_db
def test_gestor_ve_identificador_truncado(client):
    gestor = get_user_model().objects.create_user(
        username="g", password="x", perfil="gestor"
    )
    imp = Importacao.objects.create(nome_arquivo="t.csv", usuario=gestor)
    ponto = PontoAcesso.objects.create(nome="P1", localizacao="L1")
    RegistroAcesso.objects.create(
        identificador_pseudonimizado="a" * 64,
        ponto_acesso=ponto,
        tipo_acesso="Entrada",
        timestamp=timezone.now(),
        importacao=imp,
    )
    client.force_login(gestor)
    conteudo = client.get("/relatorios/acessos/?buscar=1").content.decode()
    assert "aaaaaaaaaa..." in conteudo  # 10 chars + reticências
    assert "a" * 64 not in conteudo  # hash completo não aparece p/ gestor


@pytest.mark.django_db
def test_detalhe_slug_inexistente_404(client):
    _login(client)
    assert client.get("/relatorios/naoexiste/").status_code == 404


@pytest.mark.django_db
def test_export_pdf(client):
    _login(client)
    resp = client.get("/relatorios/acessos/export/pdf/")
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


@pytest.mark.django_db
def test_export_excel(client):
    _login(client)
    resp = client.get("/relatorios/acessos/export/excel/")
    assert resp.status_code == 200
    assert "spreadsheetml" in resp["Content-Type"]
    assert resp.content[:2] == b"PK"


@pytest.mark.django_db
def test_export_csv(client):
    _login(client)
    resp = client.get("/relatorios/acessos/export/csv/")
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
    assert b"Data e hora" in resp.content  # cabeçalho


@pytest.mark.django_db
def test_export_formato_invalido_404(client):
    _login(client)
    assert client.get("/relatorios/acessos/export/txt/").status_code == 404


@pytest.mark.django_db
def test_relatorios_exige_login(client):
    assert client.get("/relatorios/").status_code == 302


@pytest.mark.django_db
@pytest.mark.parametrize("slug", ["volume", "frequentes", "picos", "fluxo"])
def test_novos_relatorios_detalhe_e_exportacao(client, slug):
    _login(client)
    assert client.get(f"/relatorios/{slug}/").status_code == 200
    for formato in ("pdf", "excel", "csv"):
        resp = client.get(f"/relatorios/{slug}/export/{formato}/")
        assert resp.status_code == 200
