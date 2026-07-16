import pytest
from datetime import datetime
from django.contrib.auth import get_user_model
from apps.acessos.models import RegistroAcesso
from apps.importacoes.models import Importacao
from apps.analytics.services import picos_por_hora

User = get_user_model()


def _setup_importacao():
    user = User.objects.create_user(
        username=f"user_{User.objects.count()}", password="password123"
    )
    return Importacao.objects.create(nome_arquivo="dummy.csv", usuario=user)


@pytest.mark.django_db
def test_picos_por_hora_banco_vazio():
    # Teste 1 (Banco Vazio):
    queryset = RegistroAcesso.objects.none()
    resultado = picos_por_hora(queryset)

    assert len(resultado) == 24
    for item in resultado:
        assert item["total"] == 0


@pytest.mark.django_db
def test_picos_por_hora_dados_esparsos():
    # Teste 2 (Dados Esparsos):
    from django.utils import timezone

    imp = _setup_importacao()
    # Inserir apenas 1 registro às 08h
    RegistroAcesso.objects.create(
        credencial_cifrada="cred-08h",
        tipo_acesso="Entrada",
        timestamp=timezone.make_aware(datetime(2026, 6, 2, 8, 30, 0)),
        importacao=imp,
    )

    queryset = RegistroAcesso.objects.all()
    resultado = picos_por_hora(queryset)

    assert len(resultado) == 24
    assert resultado[8]["total"] == 1

    for item in resultado:
        if item["hora"] != 8:
            assert item["total"] == 0
