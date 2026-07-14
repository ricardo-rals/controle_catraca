import django_filters
from django import forms
from django.utils import timezone

from .models import PontoAcesso, RegistroAcesso

_DATE_WIDGET = forms.DateInput(attrs={"type": "date"})


class RegistroAcessoFilter(django_filters.FilterSet):
    """Filtros combináveis da tela /acessos/ (HU-023).

    Reutilizado pelo endpoint REST da HU-026 — não duplicar a lógica lá.
    """

    identificador = django_filters.CharFilter(
        field_name="identificador_pseudonimizado",
        lookup_expr="icontains",
        label="Identificador",
    )
    data_inicio = django_filters.DateFilter(
        field_name="timestamp",
        lookup_expr="date__gte",
        label="Data início",
        widget=_DATE_WIDGET,
    )
    data_fim = django_filters.DateFilter(
        field_name="timestamp",
        lookup_expr="date__lte",
        label="Data fim",
        widget=_DATE_WIDGET,
    )
    ponto_acesso = django_filters.ModelChoiceFilter(
        queryset=PontoAcesso.objects.all(),
        label="Ponto de acesso",
        empty_label="Todos",
    )
    tipo_acesso = django_filters.ChoiceFilter(
        choices=RegistroAcesso.DirecaoEvento.choices,
        label="Tipo de acesso",
        empty_label="Todos",
    )

    class Meta:
        model = RegistroAcesso
        fields = [
            "identificador",
            "data_inicio",
            "data_fim",
            "ponto_acesso",
            "tipo_acesso",
        ]

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        cleaned = self.form.cleaned_data
        if cleaned.get("data_inicio") and not cleaned.get("data_fim"):
            queryset = queryset.filter(timestamp__date__lte=timezone.localdate())
        return queryset
