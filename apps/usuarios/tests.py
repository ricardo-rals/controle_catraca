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
