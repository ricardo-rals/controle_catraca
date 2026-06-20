from django import forms


class UploadCSVForm(forms.Form):
    """
    Formulário simples para receber um arquivo CSV.
    """

    arquivo = forms.FileField(
        label="Selecione um arquivo CSV"
    )