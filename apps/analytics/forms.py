"""Filtros da tela de anomalias (HU-057).

Definido aqui e reaproveitado pelo relatório de anomalias, para tela e
exportação nunca divergirem nos campos aceitos.
"""

from django import forms

from .models import Alerta

_DATE = forms.DateInput(attrs={"type": "date"})


class AnomaliasFiltroForm(forms.Form):
    tipo = forms.ChoiceField(
        required=False,
        label="Tipo de anomalia",
        choices=[("", "Todos")] + list(Alerta.Tipo.choices),
    )
    data_inicio = forms.DateField(required=False, label="Data início", widget=_DATE)
    data_fim = forms.DateField(required=False, label="Data fim", widget=_DATE)
