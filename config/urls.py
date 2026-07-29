"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from apps.usuarios.views import dashboard
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

# Urlconf isolado do schema público (HU-055): o Swagger de fora só documenta
# o que está sob /api/public/, nunca as rotas internas.
URLS_PUBLICAS = [path("api/public/", include("apps.analytics.public_urls"))]


urlpatterns = [
    path("", dashboard, name="home"),  # rota raiz
    path(
        "privacidade/",
        TemplateView.as_view(template_name="privacidade.html"),
        name="privacidade",
    ),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("importacoes/", include("apps.importacoes.urls")),
    path("acessos/", include("apps.acessos.urls")),
    path("relatorios/", include("apps.relatorios.urls")),
    path("anomalias/", include("apps.analytics.web_urls")),
    path("api/analytics/", include("apps.analytics.urls")),
    path("api/", include("apps.acessos.api_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # API pública (HU-055): endpoints + doc navegável, ambos sem login.
    path("api/public/", include("apps.analytics.public_urls")),
    path(
        "api/public/schema/",
        SpectacularAPIView.as_view(
            urlconf=URLS_PUBLICAS,
            permission_classes=[AllowAny],
            authentication_classes=[],
        ),
        name="schema-publico",
    ),
    path(
        "api/public/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema-publico",
            permission_classes=[AllowAny],
            authentication_classes=[],
        ),
        name="swagger-publico",
    ),
    path("dashboard/", dashboard, name="dashboard"),
    path("", include("apps.usuarios.urls")),
]
