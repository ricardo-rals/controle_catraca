"""Testes do app relatorios (HU-038: geração de PDF)."""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.acessos.models import PontoAcesso, RegistroAcesso
from apps.importacoes.models import Importacao


@pytest.mark.django_db
def test_relatorio_pdf_retorna_um_pdf(client):
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
    resp = client.get("/relatorios/pdf/")

    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"
    assert resp["Content-Disposition"].startswith("attachment;")
    assert resp.content[:4] == b"%PDF"  # assinatura do arquivo PDF


@pytest.mark.django_db
def test_relatorio_pdf_exige_login(client):
    resp = client.get("/relatorios/pdf/")
    assert resp.status_code == 302  # redireciona para o login
