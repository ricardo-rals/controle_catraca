from django.urls import path
from .views import PicosAnalyticsView

app_name = "analytics"

urlpatterns = [
    path("picos/", PicosAnalyticsView.as_view(), name="picos"),
]
