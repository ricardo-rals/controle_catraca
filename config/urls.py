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
from apps.usuarios.views import dashboard
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


urlpatterns = [
    path("", dashboard, name="home"),  # rota raiz
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("importacoes/", include("apps.importacoes.urls")),
    path("acessos/", include("apps.acessos.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
    path("api/", include("apps.acessos.api_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("dashboard/", dashboard, name="dashboard"),
    path("", include("apps.usuarios.urls")),
]
