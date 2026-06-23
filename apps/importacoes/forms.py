from django import forms


class UploadCSVForm(forms.Form):
    """
    Formulário para receber arquivo de dados da catraca (CSV ou XLSX).
    """

    arquivo = forms.FileField(
        label="Selecione um arquivo CSV ou XLSX",
        widget=forms.FileInput(
            attrs={"accept": ".csv,.xlsx,.xls"}
        ),
    )
