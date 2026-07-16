from django import forms

from .models import RegraHorario


class RegraHorarioForm(forms.ModelForm):
    class Meta:
        model = RegraHorario
        fields = ["grupo_equipamento", "dia_semana", "horario_inicio", "horario_fim"]
        widgets = {
            "horario_inicio": forms.TimeInput(attrs={"type": "time"}),
            "horario_fim": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        cleaned = super().clean()
        inicio, fim = cleaned.get("horario_inicio"), cleaned.get("horario_fim")
        if inicio and fim and fim <= inicio:
            raise forms.ValidationError(
                "O horário de fim deve ser posterior ao horário de início."
            )
        return cleaned
