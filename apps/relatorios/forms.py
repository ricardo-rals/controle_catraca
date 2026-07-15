"""Forms de filtro dos relatórios de analytics (HU-040).

O relatório de `acessos` usa o RegistroAcessoFilter (django-filter). Os
relatórios de agregação usam estes forms simples de período + o parâmetro
específico de cada um.
"""

from django import forms

_DATE = forms.DateInput(attrs={"type": "date"})


class PeriodoForm(forms.Form):
    data_inicio = forms.DateField(required=False, label="Data início", widget=_DATE)
    data_fim = forms.DateField(required=False, label="Data fim", widget=_DATE)


class VolumeForm(PeriodoForm):
    granularidade = forms.ChoiceField(
        required=False,
        label="Granularidade",
        choices=[("dia", "Dia"), ("semana", "Semana"), ("mes", "Mês")],
        initial="dia",
    )


class FrequentesForm(PeriodoForm):
    limite = forms.IntegerField(
        required=False, min_value=1, initial=20, label="Limite (top N)"
    )
