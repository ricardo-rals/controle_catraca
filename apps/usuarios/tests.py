import pytest
import jwt
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_user(db):
    user = User.objects.create_user(
        username="testuser", password="testpassword123", email="test@example.com"
    )
    return user


@pytest.mark.django_db
class TestJWTAuthentication:

    def test_obtain_token_success(self, api_client, test_user):
        """1. Valida geração de access e refresh tokens."""
        url = reverse("token_obtain_pair")
        data = {"username": test_user.username, "password": "testpassword123"}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_obtain_token_invalid_credentials(self, api_client, test_user):
        """1.1. Valida recusa com credenciais inválidas."""
        url = reverse("token_obtain_pair")
        data = {"username": test_user.username, "password": "wrongpassword"}

        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_contains_custom_claims(self, api_client, test_user):
        """2. Valida custom claims (username, email, is_staff) dentro do payload."""
        url = reverse("token_obtain_pair")
        data = {"username": test_user.username, "password": "testpassword123"}
        response = api_client.post(url, data, format="json")

        access_token = response.data["access"]

        # Decode bypassando signature checks apenas para validar claims estruturais
        payload = jwt.decode(access_token, options={"verify_signature": False})

        assert payload.get("username") == test_user.username
        assert payload.get("email") == test_user.email
        assert payload.get("is_staff") == test_user.is_staff

    def test_token_refresh(self, api_client, test_user):
        """3. Valida a rota de refresh gerando um novo access."""
        url_obtain = reverse("token_obtain_pair")
        response_obtain = api_client.post(
            url_obtain,
            {"username": test_user.username, "password": "testpassword123"},
            format="json",
        )

        refresh_token = response_obtain.data["refresh"]

        url_refresh = reverse("token_refresh")
        response_refresh = api_client.post(
            url_refresh, {"refresh": refresh_token}, format="json"
        )

        assert response_refresh.status_code == status.HTTP_200_OK
        assert "access" in response_refresh.data

    def test_dummy_route_without_token(self, api_client):
        """4. Sem token -> 401 Unauthorized."""
        url = reverse("dummy_protected")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_dummy_route_with_token(self, api_client, test_user):
        """4. Com token Bearer -> 200 OK."""
        url_token = reverse("token_obtain_pair")
        response_token = api_client.post(
            url_token,
            {"username": test_user.username, "password": "testpassword123"},
            format="json",
        )

        access_token = response_token.data["access"]

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        url_dummy = reverse("dummy_protected")
        response_dummy = api_client.get(url_dummy)

        assert response_dummy.status_code == status.HTTP_200_OK
        assert response_dummy.data["message"] == "Acesso autorizado!"

    def test_auth_service_inactive_user(self, api_client, test_user):
        """Testa isoladamente a camada de serviço (não emitir se usuário inativo)."""
        test_user.is_active = False
        test_user.save()

        url = reverse("token_obtain_pair")
        data = {"username": test_user.username, "password": "testpassword123"}
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAutenticacaoSessao:
    """Login de sessão e controle de acesso por perfil (HU-060)."""

    def _criar(self, perfil="gestor", ativo=True):
        return User.objects.create_user(
            username=f"{perfil}{User.objects.count()}",
            password="Senha12345",
            email=f"{perfil}@ex.com",
            perfil=perfil,
            is_active=ativo,
        )

    def test_login_valido_cria_sessao(self, client):
        self._criar()
        assert client.login(
            username=User.objects.first().username, password="Senha12345"
        )

    def test_senha_errada_nao_loga(self, client):
        self._criar()
        assert not client.login(
            username=User.objects.first().username, password="errada"
        )

    def test_usuario_desativado_nao_loga(self, client):
        self._criar(ativo=False)
        assert not client.login(
            username=User.objects.first().username, password="Senha12345"
        )

    def test_rota_interna_sem_sessao_redireciona(self, client):
        resp = client.get(reverse("dashboard"))
        assert resp.status_code == 302
        assert "/accounts/login/" in resp.url
        assert "next=" in resp.url

    def test_gestor_barrado_em_rota_admin(self, client):
        gestor = self._criar(perfil="gestor")
        client.force_login(gestor)
        resp = client.get(reverse("listar_usuarios"))
        assert resp.status_code == 403

    def test_admin_acessa_rota_admin(self, client):
        admin = self._criar(perfil="admin")
        client.force_login(admin)
        resp = client.get(reverse("listar_usuarios"))
        assert resp.status_code == 200

    def test_perfil_define_acesso_ao_django_admin(self):
        """HU-013: perfil admin → is_staff; gestor → não."""
        admin = self._criar(perfil="admin")
        gestor = self._criar(perfil="gestor")
        assert admin.is_staff is True
        assert gestor.is_staff is False
