"""Testes da API pública (HU-055)."""

import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.analytics.models import ChaveAPI, hash_chave_api
from apps.analytics.permissions import HEADER_CHAVE

# O header vira HTTP_X_API_KEY no client de teste do Django.
HEADER_CLIENT = "HTTP_X_API_KEY"


@pytest.fixture(autouse=True)
def _limpa_throttle():
    """O ScopedRateThrottle guarda contagem no cache, que sobrevive entre
    testes no mesmo processo e derrubaria os seguintes com 429."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def chave(db):
    return ChaveAPI.criar("Painel de testes")


@pytest.mark.django_db
def test_sem_chave_bloqueia(client):
    resposta = client.get(reverse("publica:volume"))

    assert resposta.status_code == 403


@pytest.mark.django_db
def test_chave_desconhecida_bloqueia(client):
    resposta = client.get(reverse("publica:volume"), **{HEADER_CLIENT: "cac_naoexiste"})

    assert resposta.status_code == 403


def test_chave_valida_libera(client, chave):
    _, em_claro = chave

    resposta = client.get(reverse("publica:volume"), **{HEADER_CLIENT: em_claro})

    assert resposta.status_code == 200
    assert "resultados" in resposta.json()


def test_chave_revogada_bloqueia(client, chave):
    objeto, em_claro = chave
    objeto.ativa = False
    objeto.save()

    resposta = client.get(reverse("publica:volume"), **{HEADER_CLIENT: em_claro})

    assert resposta.status_code == 403


def test_chave_nao_e_persistida_em_claro(chave):
    objeto, em_claro = chave
    objeto.refresh_from_db()

    assert objeto.chave_hash == hash_chave_api(em_claro)
    assert em_claro not in objeto.chave_hash
    assert objeto.prefixo == em_claro[:12]


def test_uso_carimba_ultimo_uso(client, chave):
    objeto, em_claro = chave
    assert objeto.ultimo_uso is None

    client.get(reverse("publica:picos"), **{HEADER_CLIENT: em_claro})
    objeto.refresh_from_db()

    assert objeto.ultimo_uso is not None


@pytest.mark.parametrize("rota", ["publica:volume", "publica:picos", "publica:fluxo"])
def test_endpoints_publicos_respondem_com_chave(client, chave, rota):
    _, em_claro = chave

    resposta = client.get(reverse(rota), **{HEADER_CLIENT: em_claro})

    assert resposta.status_code == 200


def test_resposta_publica_nao_expoe_dado_por_pessoa(client, chave):
    """A cifra da credencial é determinística: publicá-la daria um
    identificador estável por pessoa. Nenhuma rota pública pode devolvê-la."""
    _, em_claro = chave

    for rota in ("publica:volume", "publica:picos", "publica:fluxo"):
        corpo = client.get(reverse(rota), **{HEADER_CLIENT: em_claro}).content.decode()
        assert "credencial" not in corpo.lower()
        assert "nome_cifrado" not in corpo


@pytest.mark.django_db
def test_schema_publico_abre_sem_login_e_sem_chave(client):
    resposta = client.get(reverse("schema-publico"))

    assert resposta.status_code == 200


@pytest.mark.django_db
def test_swagger_publico_abre_sem_login(client):
    resposta = client.get(reverse("swagger-publico"))

    assert resposta.status_code == 200


@pytest.mark.django_db
def test_schema_publico_nao_documenta_rotas_internas(client):
    corpo = client.get(reverse("schema-publico")).content.decode()

    assert "/api/public/volume/" in corpo
    assert "/api/analytics/" not in corpo
    assert "/api/token/" not in corpo


@pytest.mark.django_db
def test_header_esperado_e_o_documentado():
    assert HEADER_CHAVE == "X-API-Key"
