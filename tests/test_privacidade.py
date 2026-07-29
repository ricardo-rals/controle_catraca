from django.urls import reverse


def test_privacidade_abre_sem_login(client):
    resposta = client.get(reverse("privacidade"))

    assert resposta.status_code == 200
    assert "privacidade.html" in [t.name for t in resposta.templates]
